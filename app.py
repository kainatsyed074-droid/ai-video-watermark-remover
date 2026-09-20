import os
import sys
import uuid
import time
import threading
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file
from werkzeug.utils import secure_filename

from core.video_processor import VideoProcessor
from core.presets import PRESETS, get_preset_coordinates

import tempfile

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # Up to 1GB video upload support


def get_data_dir():
    # If on serverless platforms (Vercel, AWS Lambda) or read-only filesystem, use /tmp
    if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        d = Path(tempfile.gettempdir()) / "video_watermark_remover"
        d.mkdir(parents=True, exist_ok=True)
        return d

    base_dir = Path(__file__).resolve().parent
    try:
        test_file = base_dir / ".write_test"
        test_file.touch()
        test_file.unlink()
        return base_dir
    except OSError:
        d = Path(tempfile.gettempdir()) / "video_watermark_remover"
        d.mkdir(parents=True, exist_ok=True)
        return d


DATA_DIR = get_data_dir()
UPLOAD_DIR = DATA_DIR / "uploads"
PREVIEW_DIR = DATA_DIR / "previews"
OUTPUT_DIR = DATA_DIR / "outputs"

for directory in (UPLOAD_DIR, PREVIEW_DIR, OUTPUT_DIR):
    directory.mkdir(parents=True, exist_ok=True)

processor = VideoProcessor()


@app.errorhandler(500)
def handle_500_error(e):
    return jsonify({"error": f"Internal server error: {getattr(e, 'description', str(e))}"}), 500


@app.errorhandler(413)
def handle_413_error(e):
    return jsonify({"error": "File size exceeds server upload limit."}), 413

# In-memory store for tasks and videos
TASKS = {}
VIDEOS = {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/presets", methods=["GET"])
def get_presets():
    w = request.args.get("w", type=int)
    h = request.args.get("h", type=int)
    
    result = {}
    for key, val in PRESETS.items():
        coords = None
        if w and h and val.get("type") == "relative":
            coords = get_preset_coordinates(key, w, h)
        result[key] = {
            "name": val["name"],
            "description": val["description"],
            "coords": coords
        }
    return jsonify(result)


@app.route("/api/upload", methods=["POST"])
def upload_video():
    try:
        if "video" not in request.files:
            return jsonify({"error": "No video file provided"}), 400

        file = request.files["video"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        video_id = str(uuid.uuid4())[:8]
        saved_filename = f"{video_id}_{secure_filename(file.filename)}"
        video_path = str(UPLOAD_DIR / saved_filename)
        file.save(video_path)

        try:
            info = processor.get_video_info(video_path)
        except Exception as e:
            return jsonify({"error": f"Failed to analyze video: {str(e)}"}), 400

        # Extract first frame at 0.5s or 0s
        first_frame_path = str(PREVIEW_DIR / f"{video_id}_frame_0.jpg")
        try:
            processor.extract_frame(video_path, min(0.5, info["duration"] / 2 if info["duration"] > 0 else 0), first_frame_path)
        except Exception:
            pass

        # Generate web-friendly faststart MP4 preview to guarantee smooth playback and seeking in all browsers
        web_filename = f"web_{video_id}.mp4"
        web_path = str(UPLOAD_DIR / web_filename)
        faststart_cmd = [
            processor.ffmpeg_path, "-y",
            "-i", video_path,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "ultrafast",
            "-movflags", "+faststart",
            "-c:a", "aac",
            web_path
        ]
        try:
            subprocess.run(faststart_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            display_video_url = f"/uploads/{web_filename}"
        except Exception:
            display_video_url = f"/uploads/{saved_filename}"

        has_frame = os.path.exists(first_frame_path)
        frame_url = f"/previews/{os.path.basename(first_frame_path)}" if has_frame else ""

        VIDEOS[video_id] = {
            "id": video_id,
            "original_filename": file.filename,
            "path": video_path,
            "info": info,
            "first_frame": frame_url
        }

        return jsonify({
            "status": "success",
            "video_id": video_id,
            "filename": file.filename,
            "info": info,
            "preview_frame": frame_url,
            "video_url": display_video_url
        })
    except Exception as exc:
        return jsonify({"error": f"Upload failed: {str(exc)}"}), 500



@app.route("/api/preview_frame", methods=["POST"])
def preview_frame():
    data = request.json or {}
    video_id = data.get("video_id")
    if not video_id or video_id not in VIDEOS:
        return jsonify({"error": "Invalid video_id"}), 404

    video_info = VIDEOS[video_id]
    video_path = video_info["path"]
    timestamp = float(data.get("timestamp", 0.5))
    method = data.get("method", "delogo")
    feather = int(data.get("feather", 5))

    boxes = data.get("boxes")
    if not boxes:
        boxes = [{
            "x": int(data.get("x", 0)),
            "y": int(data.get("y", 0)),
            "w": int(data.get("w", 100)),
            "h": int(data.get("h", 50))
        }]

    frame_id = f"{video_id}_{int(timestamp * 100)}"
    orig_frame_path = str(PREVIEW_DIR / f"{frame_id}_orig.jpg")
    cleaned_frame_path = str(PREVIEW_DIR / f"{frame_id}_clean_{method}.jpg")

    try:
        processor.extract_frame(video_path, timestamp, orig_frame_path)
        processor.preview_removal(
            frame_path=orig_frame_path,
            method=method,
            feather=feather,
            output_path=cleaned_frame_path,
            boxes=boxes,
            timestamp=timestamp
        )
    except Exception as e:
        return jsonify({"error": f"Preview generation failed: {str(e)}"}), 500

    return jsonify({
        "original_url": f"/previews/{os.path.basename(orig_frame_path)}?t={time.time()}",
        "cleaned_url": f"/previews/{os.path.basename(cleaned_frame_path)}?t={time.time()}"
    })


def run_processing_task(task_id: str, video_id: str, boxes: list, method: str, feather: int):
    video_info = VIDEOS[video_id]
    video_path = video_info["path"]
    orig_name = video_info["original_filename"]
    clean_name = f"clean_{Path(orig_name).stem}_{task_id}.mp4"
    output_path = str(OUTPUT_DIR / clean_name)

    TASKS[task_id]["status"] = "processing"
    TASKS[task_id]["progress"] = 0.0
    TASKS[task_id]["message"] = "Initializing HD video processing..."

    def progress_callback(pct, msg):
        TASKS[task_id]["progress"] = pct
        TASKS[task_id]["message"] = msg

    try:
        start_time = time.time()
        processor.remove_watermark(
            video_path=video_path,
            boxes=boxes,
            method=method,
            feather=feather,
            output_path=output_path,
            progress_callback=progress_callback
        )
        elapsed = round(time.time() - start_time, 1)
        TASKS[task_id]["status"] = "completed"
        TASKS[task_id]["progress"] = 100.0
        TASKS[task_id]["message"] = f"Finished in {elapsed}s!"
        TASKS[task_id]["output_path"] = output_path
        TASKS[task_id]["download_url"] = f"/api/download/{task_id}"
        TASKS[task_id]["video_url"] = f"/outputs/{clean_name}"
    except Exception as e:
        TASKS[task_id]["status"] = "error"
        TASKS[task_id]["message"] = f"Processing error: {str(e)}"


@app.route("/api/process", methods=["POST"])
def start_processing():
    data = request.json or {}
    video_id = data.get("video_id")
    if not video_id or video_id not in VIDEOS:
        return jsonify({"error": "Invalid video_id"}), 404

    boxes = data.get("boxes")
    if not boxes:
        boxes = [{
            "x": int(data.get("x", 0)),
            "y": int(data.get("y", 0)),
            "w": int(data.get("w", 100)),
            "h": int(data.get("h", 50)),
            "start_time": None,
            "end_time": None
        }]

    method = data.get("method", "delogo")
    feather = int(data.get("feather", 5))

    task_id = str(uuid.uuid4())[:8]
    TASKS[task_id] = {
        "id": task_id,
        "video_id": video_id,
        "status": "pending",
        "progress": 0.0,
        "message": "Queued...",
        "created_at": time.time()
    }

    worker = threading.Thread(
        target=run_processing_task,
        args=(task_id, video_id, boxes, method, feather),
        daemon=True
    )
    worker.start()

    return jsonify({"status": "started", "task_id": task_id})



@app.route("/api/progress/<task_id>", methods=["GET"])
def get_progress(task_id):
    if task_id not in TASKS:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(TASKS[task_id])


@app.route("/api/download/<task_id>", methods=["GET"])
def download_result(task_id):
    if task_id not in TASKS or TASKS[task_id].get("status") != "completed":
        return jsonify({"error": "Video not ready or task not found"}), 404

    output_path = TASKS[task_id]["output_path"]
    orig_name = VIDEOS[TASKS[task_id]["video_id"]]["original_filename"]
    stem = Path(orig_name).stem
    download_filename = f"{stem}_nowatermark.mp4"

    return send_file(
        output_path,
        as_attachment=True,
        download_name=download_filename,
        mimetype="video/mp4",
        conditional=True
    )


@app.route("/uploads/<path:filename>")
def serve_uploads(filename):
    return send_from_directory(str(UPLOAD_DIR), filename, conditional=True)


@app.route("/previews/<path:filename>")
def serve_previews(filename):
    return send_from_directory(str(PREVIEW_DIR), filename, conditional=True)


@app.route("/outputs/<path:filename>")
def serve_outputs(filename):
    return send_from_directory(str(OUTPUT_DIR), filename, conditional=True)



if __name__ == "__main__":
    print("==================================================")
    print("   AI Video Watermark Remover Server Running")
    print("   Open your browser at: http://localhost:5000")
    print("==================================================")
    app.run(host="0.0.0.0", port=5000, debug=False)

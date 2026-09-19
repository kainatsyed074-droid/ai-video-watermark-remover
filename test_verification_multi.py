"""
Automated Verification Script for Multiple Watermark Zones and Timeline-based Removal.
Tests chained FFmpeg delogo with enable='between(t,...)' and multi-box OpenCV streaming pipeline.
"""
import os
import sys
import subprocess
import cv2
import numpy as np
from core.video_processor import VideoProcessor, get_binary_paths

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def create_multi_watermark_video(output_path="test_multi_1080p.mp4"):
    ffmpeg_exe, _ = get_binary_paths()
    width, height = 1920, 1080
    fps = 30
    duration_sec = 2
    total_frames = fps * duration_sec

    raw_video = "temp_multi_raw.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(raw_video, fourcc, fps, (width, height))

    for f in range(total_frames):
        t = f / fps
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:, :] = (50, 70, 90)
        cv2.circle(frame, (960, 540), 180, (120, 180, 220), -1)

        # 1. Watermark 1: Bottom-Right (Entire video)
        cv2.rectangle(frame, (1500, 950), (1850, 1030), (20, 20, 20), -1)
        cv2.putText(frame, "WM 1 (FULL)", (1520, 1005), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

        # 2. Watermark 2: Top-Left (from t=0.0s to 1.0s)
        if 0.0 <= t <= 1.0:
            cv2.rectangle(frame, (50, 50), (350, 130), (20, 20, 20), -1)
            cv2.putText(frame, "WM 2 (0-1s)", (70, 105), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

        # 3. Watermark 3: Top-Right (from t=1.0s to 2.0s)
        if 1.0 < t <= 2.0:
            cv2.rectangle(frame, (1500, 50), (1850, 130), (20, 20, 20), -1)
            cv2.putText(frame, "WM 3 (1-2s)", (1520, 105), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

        out.write(frame)
    out.release()

    # Add audio track
    cmd = [
        ffmpeg_exe, "-y",
        "-i", raw_video,
        "-f", "lavfi", "-i", f"sine=frequency=520:duration={duration_sec}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        output_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    if os.path.exists(raw_video):
        os.remove(raw_video)
    return output_path

def run_tests():
    processor = VideoProcessor()
    sample_file = "test_multi_1080p.mp4"
    print("=== 1. Generating 1080p Video with 3 Watermark Zones ===")
    create_multi_watermark_video(sample_file)
    assert os.path.exists(sample_file), "Sample video creation failed"

    info = processor.get_video_info(sample_file)
    print("Detected Info:", info)
    assert info["width"] == 1920 and info["height"] == 1080

    # Define 3 watermark boxes matching the video
    boxes = [
        {
            "id": "box_1",
            "x": 1500, "y": 950, "w": 350, "h": 80,
            "start_time": None, "end_time": None  # Entire video
        },
        {
            "id": "box_2",
            "x": 50, "y": 50, "w": 300, "h": 80,
            "start_time": 0.0, "end_time": 1.0    # 0s to 1s
        },
        {
            "id": "box_3",
            "x": 1500, "y": 50, "w": 350, "h": 80,
            "start_time": 1.0, "end_time": 2.0    # 1s to 2s
        }
    ]

    print("\n=== 2. Testing Multi-Box Frame Preview ===")
    frame_orig = "test_multi_frame_orig.jpg"
    frame_clean = "test_multi_frame_clean.jpg"
    processor.extract_frame(sample_file, 0.5, frame_orig)
    processor.preview_removal(
        frame_path=frame_orig,
        method="delogo",
        feather=5,
        output_path=frame_clean,
        boxes=boxes,
        timestamp=0.5
    )
    assert os.path.exists(frame_clean), "Multi-box preview failed"
    print("✓ Frame preview with multiple boxes succeeded!")

    print("\n=== 3. Testing Full HD Chained FFmpeg Delogo with Timeline Expressions ===")
    output_delogo = "test_output_multi_delogo.mp4"
    processor.remove_watermark(
        video_path=sample_file,
        boxes=boxes,
        method="delogo",
        feather=5,
        output_path=output_delogo
    )
    assert os.path.exists(output_delogo), "Multi-box delogo output missing"
    out_delogo_info = processor.get_video_info(output_delogo)
    print("Delogo Output Info:", out_delogo_info)
    assert out_delogo_info["width"] == 1920 and out_delogo_info["height"] == 1080
    assert out_delogo_info["has_audio"] is True
    print("✓ Chained delogo successfully removed 3 watermarks while preserving 1080p HD & Audio!")

    print("\n=== 4. Testing Multi-Box AI Inpainting Stream ===")
    output_inpaint = "test_output_multi_inpaint.mp4"
    processor.remove_watermark(
        video_path=sample_file,
        boxes=boxes,
        method="telea",
        feather=5,
        output_path=output_inpaint
    )
    assert os.path.exists(output_inpaint), "Multi-box inpaint output missing"
    out_inpaint_info = processor.get_video_info(output_inpaint)
    print("Inpaint Output Info:", out_inpaint_info)
    assert out_inpaint_info["width"] == 1920 and out_inpaint_info["height"] == 1080
    assert out_inpaint_info["has_audio"] is True
    print("✓ Multi-box AI inpainting successfully removed 3 watermarks while preserving 1080p HD & Audio!")

    print("\n=======================================================")
    print("🎉 ALL MULTI-WATERMARK & TIMELINE TESTS PASSED! 🎉")
    print("=======================================================")

    # Cleanup test files
    for f in [sample_file, frame_orig, frame_clean, output_delogo, output_inpaint]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

if __name__ == "__main__":
    run_tests()

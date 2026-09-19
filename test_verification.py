"""
Automated Verification Script for Video Watermark Remover.
Creates a sample 1080p HD video with a simulated AI watermark,
processes it using VideoProcessor, and verifies resolution, audio, and output integrity.
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


def create_sample_watermarked_video(output_path="test_sample_1080p.mp4"):
    ffmpeg_exe, _ = get_binary_paths()
    width, height = 1920, 1080
    fps = 30
    duration_sec = 2
    total_frames = fps * duration_sec

    # Step 1: Generate video frames with a dynamic background and watermark
    raw_video = "temp_raw.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(raw_video, fourcc, fps, (width, height))

    for f in range(total_frames):
        # Colorful gradient background
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        # Create subtle gradient pattern
        color_val = int((f / total_frames) * 120) + 40
        frame[:, :] = (color_val, 80, 120)
        
        # Add some shapes/textures
        cv2.circle(frame, (960 + f * 5, 540), 150, (200, 150, 50), -1)

        # Draw a simulated "Gemini AI" or "Dola AI" watermark at bottom right
        # Watermark box: x=1550, y=970, w=320, h=80
        wx, wy, ww, wh = 1550, 970, 320, 80
        cv2.rectangle(frame, (wx, wy), (wx + ww, wy + wh), (30, 30, 30), -1)
        cv2.putText(frame, "AI WATERMARK", (wx + 20, wy + 52), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)

        out.write(frame)
    out.release()

    # Step 2: Add an audio sine wave using ffmpeg to test audio passthrough
    cmd = [
        ffmpeg_exe, "-y",
        "-i", raw_video,
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration_sec}",
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
    print("=== 1. Checking Binary Paths ===")
    processor = VideoProcessor()
    print("FFmpeg:", processor.ffmpeg_path)
    print("FFprobe:", processor.ffprobe_path)
    assert os.path.exists(processor.ffmpeg_path), "FFmpeg binary does not exist"
    assert os.path.exists(processor.ffprobe_path), "FFprobe binary does not exist"

    print("\n=== 2. Creating 1080p HD Test Video ===")
    sample_file = "test_sample_1080p.mp4"
    create_sample_watermarked_video(sample_file)
    assert os.path.exists(sample_file), "Sample video creation failed"

    print("\n=== 3. Testing Video Info Extraction ===")
    info = processor.get_video_info(sample_file)
    print("Detected Info:", info)
    assert info["width"] == 1920, f"Expected width 1920, got {info['width']}"
    assert info["height"] == 1080, f"Expected height 1080, got {info['height']}"
    assert info["has_audio"] is True, "Expected has_audio to be True"
    print("✓ Video info matches 1080p HD with audio!")

    print("\n=== 4. Testing Single Frame Extraction & Inpainting Preview ===")
    frame_orig = "test_frame_orig.jpg"
    frame_clean = "test_frame_clean.jpg"
    processor.extract_frame(sample_file, 0.5, frame_orig)
    assert os.path.exists(frame_orig), "Frame extraction failed"

    # Watermark coordinates: x=1550, y=970, w=320, h=80
    processor.preview_removal(frame_orig, 1550, 970, 320, 80, method="telea", feather=5, output_path=frame_clean)
    assert os.path.exists(frame_clean), "Preview inpainting failed"
    print("✓ Single frame preview inpainting succeeded!")

    print("\n=== 5. Testing Full HD Video Watermark Removal (FFmpeg Delogo) ===")
    output_delogo = "test_output_delogo.mp4"
    progress_calls = []
    def on_progress(pct, msg):
        progress_calls.append(pct)

    processor.remove_watermark(
        sample_file,
        x=1550, y=970, w=320, h=80,
        method="delogo",
        feather=5,
        output_path=output_delogo,
        progress_callback=on_progress
    )
    assert os.path.exists(output_delogo), "Delogo video output missing"
    out_info = processor.get_video_info(output_delogo)
    print("Delogo Output Info:", out_info)
    assert out_info["width"] == 1920, "Output width changed!"
    assert out_info["height"] == 1080, "Output height changed!"
    assert out_info["has_audio"] is True, "Audio was lost!"
    print(f"✓ Delogo HD processing completed with {len(progress_calls)} progress reports!")

    print("\n=== 6. Testing Full HD Video Watermark Removal (AI Inpaint Stream) ===")
    output_inpaint = "test_output_inpaint.mp4"
    processor.remove_watermark(
        sample_file,
        x=1550, y=970, w=320, h=80,
        method="telea",
        feather=5,
        output_path=output_inpaint,
        progress_callback=None
    )
    assert os.path.exists(output_inpaint), "Inpaint video output missing"
    inpaint_info = processor.get_video_info(output_inpaint)
    print("Inpaint Output Info:", inpaint_info)
    assert inpaint_info["width"] == 1920, "Inpaint output width changed!"
    assert inpaint_info["height"] == 1080, "Inpaint output height changed!"
    assert inpaint_info["has_audio"] is True, "Inpaint audio was lost!"
    print("✓ AI Inpaint HD processing completed successfully!")

    print("\n=======================================================")
    print("🎉 ALL TESTS PASSED SUCCESSFULLY! FULL HD PRESERVED! 🎉")
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

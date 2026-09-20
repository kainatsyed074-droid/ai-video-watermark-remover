import os
import sys
import json
import re
import shutil
import subprocess
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, Callable


def get_binary_paths():
    """
    Find paths for ffmpeg and ffprobe binaries.
    Checks:
    1. Local bin/ folder
    2. System PATH
    3. Common Windows locations (WinGet, LocalAppData, Program Files)
    """
    base_dir = Path(__file__).resolve().parent.parent
    local_bin = base_dir / "bin"
    
    ffmpeg_local = local_bin / "ffmpeg.exe"
    ffprobe_local = local_bin / "ffprobe.exe"
    if ffmpeg_local.exists() and ffprobe_local.exists():
        return str(ffmpeg_local), str(ffprobe_local)
        
    # Check PATH
    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    if ffmpeg_path and ffprobe_path:
        return ffmpeg_path, ffprobe_path

    # Check common WinGet / LocalAppData locations
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
    
    search_dirs = [
        Path(local_app_data) / "Microsoft" / "WinGet" / "Packages",
        Path(local_app_data) / "Programs",
        Path(program_files),
        Path("C:/ffmpeg/bin"),
    ]
    
    found_ffmpeg = None
    found_ffprobe = None
    for s_dir in search_dirs:
        if s_dir.exists():
            for p in s_dir.glob("**/ffmpeg.exe"):
                found_ffmpeg = str(p)
                break
            for p in s_dir.glob("**/ffprobe.exe"):
                found_ffprobe = str(p)
                break
        if found_ffmpeg and found_ffprobe:
            return found_ffmpeg, found_ffprobe

    # Check imageio_ffmpeg for bundled static binary (e.g. on Linux, Vercel, Docker)
    if not found_ffmpeg:
        try:
            import imageio_ffmpeg
            imgio_exe = imageio_ffmpeg.get_ffmpeg_exe()
            if imgio_exe and os.path.exists(imgio_exe):
                found_ffmpeg = imgio_exe
        except Exception:
            pass

    return found_ffmpeg or "ffmpeg", found_ffprobe or "ffprobe"


class VideoProcessor:
    def __init__(self):
        self.ffmpeg_path, self.ffprobe_path = get_binary_paths()

    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """
        Extract video metadata using ffprobe.
        """
        cmd = [
            self.ffprobe_path,
            "-v", "error",
            "-show_entries", "stream=width,height,r_frame_rate,duration,nb_frames,codec_type,codec_name:format=duration,size,bit_rate",
            "-of", "json",
            video_path
        ]
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            data = json.loads(result.stdout)
            
            video_stream = None
            has_audio = False
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video" and not video_stream:
                    video_stream = stream
                elif stream.get("codec_type") == "audio":
                    has_audio = True

            if not video_stream:
                raise ValueError("No video stream found in file.")

            # Frame rate
            r_fps = video_stream.get("r_frame_rate", "30/1")
            if "/" in r_fps:
                num, den = r_fps.split("/")
                fps = round(float(num) / float(den), 2) if float(den) != 0 else 30.0
            else:
                fps = float(r_fps)

            # Duration
            duration = float(video_stream.get("duration") or data.get("format", {}).get("duration", 0))

            # Total frames calculation
            nb_frames = video_stream.get("nb_frames")
            if nb_frames and nb_frames.isdigit():
                total_frames = int(nb_frames)
            else:
                total_frames = int(duration * fps) if duration > 0 else 0

            width = int(video_stream.get("width", 0))
            height = int(video_stream.get("height", 0))

            return {
                "width": width,
                "height": height,
                "fps": fps,
                "duration": duration,
                "total_frames": total_frames,
                "has_audio": has_audio,
                "codec": video_stream.get("codec_name", "unknown"),
                "size_bytes": int(data.get("format", {}).get("size", 0))
            }
        except Exception as e:
            # Fallback using OpenCV if ffprobe fails
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise RuntimeError(f"Failed to open video {video_path}: {e}")
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = float(cap.get(cv2.CAP_PROP_FPS)) or 30.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            cap.release()
            return {
                "width": width,
                "height": height,
                "fps": round(fps, 2),
                "duration": round(duration, 2),
                "total_frames": total_frames,
                "has_audio": True,
                "codec": "unknown",
                "size_bytes": os.path.getsize(video_path) if os.path.exists(video_path) else 0
            }

    def extract_frame(self, video_path: str, timestamp_sec: float, output_path: str) -> str:
        """
        Extracts a single high-quality frame at the specified timestamp.
        """
        dir_name = os.path.dirname(output_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-ss", str(timestamp_sec),
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",
            output_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0 or not os.path.exists(output_path):
            # Fallback with OpenCV
            cap = cv2.VideoCapture(video_path)
            cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_sec * 1000)
            ret, frame = cap.read()
            if ret:
                cv2.imwrite(output_path, frame)
            cap.release()

        return output_path

    @staticmethod
    def apply_watermark_removal_to_image(
        img: np.ndarray,
        x: int,
        y: int,
        w: int,
        h: int,
        method: str = "telea",
        feather: int = 4
    ) -> np.ndarray:
        """
        Applies watermark removal on a single BGR image using ultra-fast ROI patch inpainting.
        Methods:
        - 'telea': Fast marching method (cv2.INPAINT_TELEA) with smooth blending
        - 'ns': Navier-Stokes based inpainting (cv2.INPAINT_NS)
        - 'blur': Feathered edge Gaussian blur (smooth region blend)
        - 'delogo': Delogo edge-interpolation style inpainting
        """
        H, W = img.shape[:2]
        
        # Clamp coordinates within bounds
        x = max(0, min(x, W - 1))
        y = max(0, min(y, H - 1))
        w = max(1, min(w, W - x))
        h = max(1, min(h, H - y))

        result = img.copy()

        # ROI sub-patch bounds around the watermark box with safety margin
        pad = max(16, feather * 2 + 8)
        x0 = max(0, x - pad)
        y0 = max(0, y - pad)
        x1 = min(W, x + w + pad)
        y1 = min(H, y + h + pad)

        pw = x1 - x0
        ph = y1 - y0
        if pw <= 0 or ph <= 0:
            return result

        sub_patch = result[y0:y1, x0:x1]
        bx0 = x - x0
        by0 = y - y0

        if method in ("telea", "ns"):
            flags = cv2.INPAINT_TELEA if method == "telea" else cv2.INPAINT_NS
            
            # Local mask for the sub-patch only (orders of magnitude faster than full-frame)
            local_mask = np.zeros((ph, pw), dtype=np.uint8)
            local_mask[by0:by0+h, bx0:bx0+w] = 255
            
            radius = max(3, min(feather, 7))
            inpainted_patch = cv2.inpaint(sub_patch, local_mask, inpaintRadius=radius, flags=flags)
            
            # Feathered alpha blend around the border of the sub-patch
            if feather > 0:
                soft_mask = np.zeros((ph, pw), dtype=np.float32)
                soft_mask[by0:by0+h, bx0:bx0+w] = 1.0
                ksize = max(3, (feather * 2) + 1)
                soft_mask = cv2.GaussianBlur(soft_mask, (ksize, ksize), 0)[:, :, np.newaxis]
                
                result[y0:y1, x0:x1] = (inpainted_patch.astype(np.float32) * soft_mask + 
                                       sub_patch.astype(np.float32) * (1.0 - soft_mask)).astype(np.uint8)
            else:
                result[y0:y1, x0:x1] = inpainted_patch

        elif method == "blur":
            patch = result[y:y+h, x:x+w]
            kw = max(15, (w // 6) | 1)
            kh = max(15, (h // 6) | 1)
            blurred_patch = cv2.GaussianBlur(patch, (kw, kh), 0)

            if feather > 0:
                mask_2d = np.ones((h, w), dtype=np.float32)
                ksize = max(3, (feather * 2) + 1)
                mask_2d = cv2.GaussianBlur(mask_2d, (ksize, ksize), 0)
                alpha = mask_2d[:, :, np.newaxis]
                result[y:y+h, x:x+w] = (blurred_patch.astype(np.float32) * alpha + 
                                       patch.astype(np.float32) * (1.0 - alpha)).astype(np.uint8)
            else:
                result[y:y+h, x:x+w] = blurred_patch

        elif method == "delogo":
            local_mask = np.zeros((ph, pw), dtype=np.uint8)
            local_mask[by0:by0+h, bx0:bx0+w] = 255
            inpainted_patch = cv2.inpaint(sub_patch, local_mask, inpaintRadius=max(feather, 4), flags=cv2.INPAINT_TELEA)
            result[y0:y1, x0:x1] = inpainted_patch

        return result

    def preview_removal(
        self,
        frame_path: str,
        x: int = 0,
        y: int = 0,
        w: int = 0,
        h: int = 0,
        method: str = "delogo",
        feather: int = 5,
        output_path: str = "preview_clean.jpg",
        boxes: Optional[list] = None,
        timestamp: float = 0.0
    ) -> str:
        """
        Removes watermark on a single frame and writes output image for UI comparison.
        Supports single box (x,y,w,h) or multiple boxes list with time filtering.
        """
        img = cv2.imread(frame_path)
        if img is None:
            raise FileNotFoundError(f"Could not load image at {frame_path}")

        if not boxes:
            box_list = [{"x": x, "y": y, "w": w, "h": h}]
        else:
            # Filter boxes active at current timestamp
            active = []
            for b in boxes:
                st = b.get("start_time")
                et = b.get("end_time")
                if st is not None and et is not None and float(et) > float(st):
                    if float(st) <= timestamp <= float(et):
                        active.append(b)
                else:
                    active.append(b)
            box_list = active if active else boxes

        cleaned = img.copy()
        for b in box_list:
            bx = int(b.get("x", 0))
            by = int(b.get("y", 0))
            bw = int(b.get("w", 10))
            bh = int(b.get("h", 10))
            cleaned = self.apply_watermark_removal_to_image(cleaned, bx, by, bw, bh, method, feather)

        dir_name = os.path.dirname(output_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        cv2.imwrite(output_path, cleaned)
        return output_path

    def process_video_ffmpeg_delogo(
        self,
        video_path: str,
        boxes: list,
        feather: int,
        output_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ):
        """
        Uses FFmpeg's native delogo filter for maximum speed and exact quality retention.
        Chains multiple delogo filters together for all watermark boxes with timeline support.
        """
        info = self.get_video_info(video_path)
        total_duration = info["duration"] if info["duration"] > 0 else 1.0
        W, H = info["width"], info["height"]

        delogo_parts = []
        for b in boxes:
            # FFmpeg delogo strictly requires at least 1 pixel border on all 4 edges:
            # 1 <= x, 1 <= y, x + w <= W - 1, y + h <= H - 1
            raw_x = int(b.get("x", 1))
            raw_y = int(b.get("y", 1))
            raw_w = max(2, int(b.get("w", 10)))
            raw_h = max(2, int(b.get("h", 10)))

            bx = max(1, min(raw_x, W - 3))
            by = max(1, min(raw_y, H - 3))
            bw = max(2, min(raw_w, (W - 1) - bx))
            bh = max(2, min(raw_h, (H - 1) - by))

            st = b.get("start_time")
            et = b.get("end_time")
            if st is not None and et is not None and float(et) > float(st):
                delogo_parts.append(f"delogo=x={bx}:y={by}:w={bw}:h={bh}:show=0:enable='between(t,{float(st):.2f},{float(et):.2f})'")
            else:
                delogo_parts.append(f"delogo=x={bx}:y={by}:w={bw}:h={bh}:show=0")

        delogo_filter = ",".join(delogo_parts) if delogo_parts else "null"

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", video_path,
            "-vf", delogo_filter,
            "-c:v", "libx264",
            "-crf", "18",               # Visually lossless HD quality
            "-preset", "veryfast",       # Ultra-fast parallel encoding
            "-threads", "0",            # Use all available CPU cores
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",   # Fast playback and download streaming
        ]

        if info.get("has_audio"):
            cmd.extend(["-c:a", "copy"])  # Direct copy of audio without loss
        else:
            cmd.extend(["-an"])

        cmd.append(output_path)

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            universal_newlines=True,
            bufsize=1
        )

        time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")
        all_stderr = []

        while True:
            line = process.stderr.readline()
            if not line and process.poll() is not None:
                break
            if line:
                all_stderr.append(line)
                match = time_pattern.search(line)
                if match and progress_callback:
                    hours, mins, secs = match.groups()
                    current_time = int(hours) * 3600 + int(mins) * 60 + float(secs)
                    pct = min(99.0, max(0.0, (current_time / total_duration) * 100.0))
                    progress_callback(pct, f"Removing watermark... {pct:.0f}%")

        if process.returncode != 0:
            remaining = process.stderr.read()
            if remaining:
                all_stderr.append(remaining)
            err = "".join(all_stderr[-15:])
            raise RuntimeError(f"FFmpeg delogo failed (code {process.returncode}): {err}")

        if progress_callback:
            progress_callback(100.0, "Completed!")

    def process_video_cv2_pipe(
        self,
        video_path: str,
        boxes: list,
        method: str,
        feather: int,
        output_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ):
        """
        High-performance streaming pipe for OpenCV Inpainting (Telea / Navier-Stokes / Blur).
        Supports multiple active boxes per frame based on timeline ranges.
        """
        info = self.get_video_info(video_path)
        W, H = info["width"], info["height"]
        fps = info["fps"] if info["fps"] > 0 else 30.0
        total_frames = info["total_frames"] if info["total_frames"] > 0 else 1
        has_audio = info.get("has_audio", False)
        frame_size = W * H * 3

        read_cmd = [
            self.ffmpeg_path,
            "-i", video_path,
            "-f", "rawvideo",
            "-pix_fmt", "bgr24",
            "-"
        ]

        write_cmd = [
            self.ffmpeg_path,
            "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{W}x{H}",
            "-pix_fmt", "bgr24",
            "-r", str(fps),
            "-i", "-",               # video from pipe
        ]

        if has_audio:
            write_cmd.extend([
                "-i", video_path,    # second input for audio
                "-map", "0:v:0",
                "-map", "1:a:0?",
                "-c:a", "copy",
                "-shortest"
            ])
        else:
            write_cmd.extend(["-an"])

        write_cmd.extend([
            "-c:v", "libx264",
            "-crf", "18",            # Visually lossless HD quality
            "-preset", "veryfast",   # Ultra-fast parallel encoding
            "-threads", "0",         # All CPU cores
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", # Fast streaming & instant download playback
            output_path
        ])

        reader = subprocess.Popen(read_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=frame_size * 2)
        writer = subprocess.Popen(write_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=frame_size * 2)

        radius = max(3, min(feather, 7))
        flags = cv2.INPAINT_TELEA if method == "telea" else cv2.INPAINT_NS

        # Parse box coordinates, timeline ranges, and precalculate ROI sub-patch masks
        parsed_boxes = []
        for b in boxes:
            bx = max(0, min(int(b.get("x", 0)), W - 1))
            by = max(0, min(int(b.get("y", 0)), H - 1))
            bw = max(1, min(max(1, int(b.get("w", 10))), W - bx))
            bh = max(1, min(max(1, int(b.get("h", 10))), H - by))
            st = float(b["start_time"]) if b.get("start_time") is not None else None
            et = float(b["end_time"]) if b.get("end_time") is not None else None

            # Sub-patch ROI bounds with padding
            pad = max(16, feather * 2 + 8)
            x0 = max(0, bx - pad)
            y0 = max(0, by - pad)
            x1 = min(W, bx + bw + pad)
            y1 = min(H, by + bh + pad)
            pw = x1 - x0
            ph = y1 - y0

            local_mask = np.zeros((ph, pw), dtype=np.uint8)
            local_mask[by - y0 : by - y0 + bh, bx - x0 : bx - x0 + bw] = 255

            if feather > 0:
                soft_mask = np.zeros((ph, pw), dtype=np.float32)
                soft_mask[by - y0 : by - y0 + bh, bx - x0 : bx - x0 + bw] = 1.0
                ksize = max(3, (feather * 2) + 1)
                soft_mask = cv2.GaussianBlur(soft_mask, (ksize, ksize), 0)[:, :, np.newaxis]
                inv_soft = 1.0 - soft_mask
            else:
                soft_mask = None
                inv_soft = None

            kw = max(15, (bw // 6) | 1)
            kh = max(15, (bh // 6) | 1)

            parsed_boxes.append({
                "x": bx, "y": by, "w": bw, "h": bh,
                "st": st, "et": et,
                "x0": x0, "y0": y0, "x1": x1, "y1": y1,
                "mask": local_mask,
                "soft": soft_mask,
                "inv_soft": inv_soft,
                "kw": kw, "kh": kh
            })

        frame_count = 0
        try:
            while True:
                raw_frame = reader.stdout.read(frame_size)
                if not raw_frame or len(raw_frame) < frame_size:
                    break

                frame = np.frombuffer(raw_frame, dtype=np.uint8).copy().reshape((H, W, 3))
                cur_time = frame_count / fps

                # Find active boxes at this timestamp
                active = []
                for b in parsed_boxes:
                    if b["st"] is not None and b["et"] is not None and b["et"] > b["st"]:
                        if b["st"] <= cur_time <= b["et"]:
                            active.append(b)
                    else:
                        active.append(b)

                if active:
                    for b in active:
                        x0, y0, x1, y1 = b["x0"], b["y0"], b["x1"], b["y1"]
                        sub_img = frame[y0:y1, x0:x1]
                        if method in ("telea", "ns"):
                            sub_inp = cv2.inpaint(sub_img, b["mask"], inpaintRadius=radius, flags=flags)
                            if b["soft"] is not None:
                                frame[y0:y1, x0:x1] = (sub_inp.astype(np.float32) * b["soft"] + 
                                                       sub_img.astype(np.float32) * b["inv_soft"]).astype(np.uint8)
                            else:
                                frame[y0:y1, x0:x1] = sub_inp
                        elif method == "blur":
                            bx, by, bw, bh = b["x"], b["y"], b["w"], b["h"]
                            patch = frame[by:by+bh, bx:bx+bw]
                            blurred = cv2.GaussianBlur(patch, (b["kw"], b["kh"]), 0)
                            if b["soft"] is not None:
                                m = np.ones((bh, bw), dtype=np.float32)
                                ksize = max(3, (feather * 2) + 1)
                                m = cv2.GaussianBlur(m, (ksize, ksize), 0)[:, :, np.newaxis]
                                frame[by:by+bh, bx:bx+bw] = (blurred.astype(np.float32) * m + patch.astype(np.float32) * (1.0 - m)).astype(np.uint8)
                            else:
                                frame[by:by+bh, bx:bx+bw] = blurred
                        else:  # fallback delogo
                            sub_inp = cv2.inpaint(sub_img, b["mask"], inpaintRadius=max(feather, 4), flags=cv2.INPAINT_TELEA)
                            frame[y0:y1, x0:x1] = sub_inp

                writer.stdin.write(frame.tobytes())
                frame_count += 1

                if progress_callback and frame_count % 15 == 0:
                    pct = min(99.0, max(0.0, (frame_count / total_frames) * 100.0))
                    progress_callback(pct, f"Removing watermark... {pct:.0f}%")

        finally:
            if reader.stdout:
                reader.stdout.close()
            reader.wait()

            if writer.stdin:
                writer.stdin.close()
            writer.wait()

        if progress_callback:
            progress_callback(100.0, "Complete!")

    def process_video_pure_cv2(
        self,
        video_path: str,
        boxes: list,
        method: str,
        feather: int,
        output_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ):
        """
        Pure OpenCV frame-by-frame video watermark removal without external ffmpeg binary.
        Provides 100% reliable execution in serverless/cloud environments where ffmpeg is absent.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video file with OpenCV: {video_path}")

        W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS)) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        writer = cv2.VideoWriter(output_path, fourcc, fps, (W, H))

        parsed_boxes = []
        for b in boxes:
            bx = max(0, min(int(b.get("x", 0)), W - 1))
            by = max(0, min(int(b.get("y", 0)), H - 1))
            bw = max(1, min(max(1, int(b.get("w", 10))), W - bx))
            bh = max(1, min(max(1, int(b.get("h", 10))), H - by))
            st = float(b["start_time"]) if b.get("start_time") is not None else None
            et = float(b["end_time"]) if b.get("end_time") is not None else None
            parsed_boxes.append({"x": bx, "y": by, "w": bw, "h": bh, "st": st, "et": et})

        frame_count = 0
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                cur_time = frame_count / fps
                active = []
                for b in parsed_boxes:
                    if b["st"] is not None and b["et"] is not None and b["et"] > b["st"]:
                        if b["st"] <= cur_time <= b["et"]:
                            active.append(b)
                    else:
                        active.append(b)

                for b in active:
                    frame = self.apply_watermark_removal_to_image(
                        frame, b["x"], b["y"], b["w"], b["h"],
                        method=method if method in ("telea", "ns", "blur") else "telea",
                        feather=feather
                    )

                writer.write(frame)
                frame_count += 1

                if progress_callback and frame_count % 10 == 0:
                    pct = min(99.0, max(0.0, (frame_count / total_frames) * 100.0))
                    progress_callback(pct, f"Removing watermark... {pct:.0f}%")
        finally:
            cap.release()
            writer.release()

        if progress_callback:
            progress_callback(100.0, "Complete!")

    def remove_watermark(
        self,
        video_path: str,
        x: int = 0,
        y: int = 0,
        w: int = 0,
        h: int = 0,
        method: str = "delogo",
        feather: int = 5,
        output_path: str = "output.mp4",
        progress_callback: Optional[Callable[[float, str], None]] = None,
        boxes: Optional[list] = None
    ):
        """
        Main entry point for watermark removal with 3-tier fallback architecture:
        1. Native FFmpeg Delogo (fastest, lossless)
        2. Streaming FFmpeg Pipe + OpenCV inpaint (custom algorithms + audio passthrough)
        3. Pure OpenCV Video Engine (zero binary dependencies, runs anywhere)
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        if not boxes:
            boxes = [{"x": x, "y": y, "w": w, "h": h, "start_time": None, "end_time": None}]

        # Tier 1: FFmpeg Delogo
        if method == "delogo":
            try:
                self.process_video_ffmpeg_delogo(
                    video_path=video_path,
                    boxes=boxes,
                    feather=feather,
                    output_path=output_path,
                    progress_callback=progress_callback
                )
                return output_path
            except Exception as e:
                print(f"[Tier 1 Fallback] FFmpeg delogo unavailable or failed: {e}. Trying FFmpeg AI pipe...")

        # Tier 2: FFmpeg Pipe with OpenCV inpainting & audio copy
        try:
            if progress_callback:
                progress_callback(12.0, "Removing watermark...")
            self.process_video_cv2_pipe(
                video_path=video_path,
                boxes=boxes,
                method=method if method in ("telea", "ns", "blur") else "telea",
                feather=feather,
                output_path=output_path,
                progress_callback=progress_callback
            )
            return output_path
        except Exception as e:
            print(f"[Tier 2 Fallback] FFmpeg pipe unavailable or failed: {e}. Falling back to pure OpenCV engine...")

        # Tier 3: Pure OpenCV processing (Zero external binaries required)
        if progress_callback:
            progress_callback(20.0, "Removing watermark...")
        self.process_video_pure_cv2(
            video_path=video_path,
            boxes=boxes,
            method=method if method in ("telea", "ns", "blur") else "telea",
            feather=feather,
            output_path=output_path,
            progress_callback=progress_callback
        )
        return output_path


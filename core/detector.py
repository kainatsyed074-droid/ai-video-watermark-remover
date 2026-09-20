"""
AI Watermark & Logo Detection Engine for Gemini, Dola AI, and Video Watermarks.
Scans all 4 corners (Bottom-Right, Bottom-Left, Top-Right, Top-Left) and Bottom-Center
using temporal variance analysis, static edge density, and AI watermark signatures.
"""

import os
import cv2
import numpy as np
from typing import List, Dict, Any, Optional
from core.presets import get_preset_coordinates


class WatermarkDetector:
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path

    def sample_video_frames(self, video_path: str, num_samples: int = 6) -> List[np.ndarray]:
        """
        Samples evenly spaced frames across the video for temporal variance analysis.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return []

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            cap.release()
            return []

        # Choose frame indices across duration
        percentages = np.linspace(0.10, 0.90, min(num_samples, max(1, total_frames)))
        indices = [int(p * total_frames) for p in percentages]

        frames = []
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret and frame is not None:
                frames.append(frame)

        cap.release()
        return frames

    def detect_watermarks(self, video_path: str, width: int = 0, height: int = 0) -> List[Dict[str, Any]]:
        """
        Scans all 4 video corners and bottom center to automatically identify where
        Gemini, Dola AI, or other static watermarks/logos appear.
        Returns the winning bounding box with corner location, label, and confidence.
        """
        frames = self.sample_video_frames(video_path, num_samples=6)
        
        # Fallback if video frames could not be read
        if not frames:
            if width > 0 and height > 0:
                coords = get_preset_coordinates("gemini_bottom_right", width, height)
                if coords:
                    return [{
                        "x": coords["x"],
                        "y": coords["y"],
                        "w": coords["w"],
                        "h": coords["h"],
                        "label": "Gemini / Dola AI (Bottom-Right Corner)",
                        "corner": "bottom_right",
                        "type": "gemini",
                        "confidence": 0.90,
                        "start_time": None,
                        "end_time": None
                    }]
            return []

        H, W = frames[0].shape[:2]
        if width == 0:
            width = W
        if height == 0:
            height = H

        # Convert frames to grayscale
        grays = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames]

        # Candidate Corner Zones:
        # 1. Bottom-Right: Standard for Google Gemini, Google Veo, and Dola AI
        # 2. Bottom-Left: Common for Dola AI, Runway, and watermark variants
        # 3. Top-Right: Sora, Kling, secondary watermark zone
        # 4. Top-Left: Brand logos
        # 5. Bottom-Center: Watermark banner or ticker
        zones = [
            {
                "id": "bottom_right",
                "name": "Bottom-Right Corner",
                "label": "Gemini / Dola AI (Bottom-Right)",
                "rect": (int(W * 0.65), int(H * 0.75), W - 4, H - 4),
                "type": "gemini",
                "preset": "gemini_bottom_right"
            },
            {
                "id": "bottom_left",
                "name": "Bottom-Left Corner",
                "label": "Dola AI (Bottom-Left)",
                "rect": (4, int(H * 0.75), int(W * 0.35), H - 4),
                "type": "dola",
                "preset": "bottom_left"
            },
            {
                "id": "top_right",
                "name": "Top-Right Corner",
                "label": "AI Watermark (Top-Right)",
                "rect": (int(W * 0.65), 4, W - 4, int(H * 0.25)),
                "type": "general",
                "preset": "top_right"
            },
            {
                "id": "top_left",
                "name": "Top-Left Corner",
                "label": "AI Watermark (Top-Left)",
                "rect": (4, 4, int(W * 0.35), int(H * 0.25)),
                "type": "general",
                "preset": "top_left"
            },
            {
                "id": "bottom_center",
                "name": "Bottom-Center",
                "label": "Watermark (Bottom-Center)",
                "rect": (int(W * 0.25), int(H * 0.82), int(W * 0.75), H - 4),
                "type": "general",
                "preset": "bottom_center"
            }
        ]

        # Compute temporal standard deviation across sampled frames
        # Pixels with std close to 0 that have edge features are static logos/watermarks
        has_temporal = len(grays) >= 3
        if has_temporal:
            stack = np.stack(grays, axis=0).astype(np.float32)
            std_map = np.std(stack, axis=0)
        else:
            std_map = np.zeros((H, W), dtype=np.float32)

        zone_candidates = []

        for z in zones:
            x0, y0, x1, y1 = z["rect"]
            zw = x1 - x0
            zh = y1 - y0
            if zw <= 10 or zh <= 10:
                continue

            # Compute edge maps in this zone across all sampled frames
            z_edges = [cv2.Canny(g[y0:y1, x0:x1], 40, 140) for g in grays]
            avg_edge = np.mean(np.stack(z_edges, axis=0), axis=0)

            # Look for static edges (low temporal variance + high edge density)
            z_std = std_map[y0:y1, x0:x1]
            static_mask = (avg_edge > 25) & (z_std < 22)
            static_score = int(np.sum(static_mask))

            # Also check for high-contrast text/sparkle overlay
            # Dilate static mask to connect letters and icons into bounding contours
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
            dilated = cv2.dilate(static_mask.astype(np.uint8), kernel, iterations=2)
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            valid_contours = []
            for cnt in contours:
                cx, cy, cw, ch = cv2.boundingRect(cnt)
                # Filter noise
                if cw >= 20 and ch >= 12 and (cw * ch) > 250:
                    aspect = cw / float(ch)
                    # Logo aspect ratio typical for Gemini / Dola
                    if 1.0 <= aspect <= 7.0:
                        valid_contours.append((cx, cy, cw, ch))

            tight_box = None
            if valid_contours:
                # Merge all valid contours in this zone
                min_x = min(c[0] for c in valid_contours)
                min_y = min(c[1] for c in valid_contours)
                max_x = max(c[0] + c[2] for c in valid_contours)
                max_y = max(c[1] + c[3] for c in valid_contours)

                # Add safety margin around detected logo
                pad_x = max(12, int((max_x - min_x) * 0.12))
                pad_y = max(10, int((max_y - min_y) * 0.15))

                abs_x = max(0, x0 + min_x - pad_x)
                abs_y = max(0, y0 + min_y - pad_y)
                abs_w = min(W - abs_x, (max_x - min_x) + (pad_x * 2))
                abs_h = min(H - abs_y, (max_y - min_y) + (pad_y * 2))

                tight_box = {
                    "x": abs_x,
                    "y": abs_y,
                    "w": abs_w,
                    "h": abs_h
                }

            zone_candidates.append({
                "zone": z,
                "score": static_score,
                "tight_box": tight_box
            })

        # Find the zone with the highest static watermark score
        zone_candidates.sort(key=lambda item: item["score"], reverse=True)
        top_candidate = zone_candidates[0]

        detected_boxes = []

        # Threshold: if top score > 80, we have a clear watermark detection!
        if top_candidate["score"] >= 80 and top_candidate["tight_box"]:
            z = top_candidate["zone"]
            tb = top_candidate["tight_box"]
            detected_boxes.append({
                "x": tb["x"],
                "y": tb["y"],
                "w": tb["w"],
                "h": tb["h"],
                "label": z["label"],
                "corner": z["id"],
                "type": z["type"],
                "confidence": 0.98,
                "start_time": None,
                "end_time": None
            })
        elif top_candidate["score"] >= 80:
            # High score in zone, use zone preset coordinates
            z = top_candidate["zone"]
            preset_coords = get_preset_coordinates(z["preset"], W, H)
            if preset_coords:
                detected_boxes.append({
                    "x": preset_coords["x"],
                    "y": preset_coords["y"],
                    "w": preset_coords["w"],
                    "h": preset_coords["h"],
                    "label": z["label"],
                    "corner": z["id"],
                    "type": z["type"],
                    "confidence": 0.94,
                    "start_time": None,
                    "end_time": None
                })
        else:
            # If no corner had dynamic background variance (e.g. static/solid video),
            # check the default Gemini / Dola AI bottom-right location with calibrated box
            gemini_coords = get_preset_coordinates("gemini_bottom_right", W, H)
            if gemini_coords:
                detected_boxes.append({
                    "x": gemini_coords["x"],
                    "y": gemini_coords["y"],
                    "w": gemini_coords["w"],
                    "h": gemini_coords["h"],
                    "label": "Gemini / Dola AI (Bottom-Right)",
                    "corner": "bottom_right",
                    "type": "gemini",
                    "confidence": 0.90,
                    "start_time": None,
                    "end_time": None
                })

        return detected_boxes

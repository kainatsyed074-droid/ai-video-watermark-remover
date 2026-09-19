"""
Watermark presets for popular AI video generation platforms and standard corner layouts.
Coordinates can be calculated dynamically based on video width and height.
"""

PRESETS = {
    "custom": {
        "name": "Custom Selection (Select on Video)",
        "description": "Click and drag directly on the video to select any watermark.",
        "type": "custom"
    },
    "gemini_bottom_right": {
        "name": "Gemini / Veo (Bottom-Right)",
        "description": "Standard watermark placement for Google Gemini & Veo generated videos.",
        "type": "relative",
        # Percentage of width and height: (x_pct, y_pct, w_pct, h_pct)
        "calc": lambda w, h: {
            "x": int(w * 0.81),
            "y": int(h * 0.90),
            "w": int(w * 0.17),
            "h": int(h * 0.08)
        }
    },
    "dola_bottom_right": {
        "name": "Dola AI (Bottom-Right)",
        "description": "Standard logo watermark for Dola AI video generator.",
        "type": "relative",
        "calc": lambda w, h: {
            "x": int(w * 0.78),
            "y": int(h * 0.88),
            "w": int(w * 0.20),
            "h": int(h * 0.10)
        }
    },
    "bottom_right": {
        "name": "Bottom-Right Corner (General)",
        "description": "General bottom-right watermark area (Runway, Kling, Sora, etc.)",
        "type": "relative",
        "calc": lambda w, h: {
            "x": int(w * 0.78),
            "y": int(h * 0.88),
            "w": int(w * 0.20),
            "h": int(h * 0.10)
        }
    },
    "bottom_left": {
        "name": "Bottom-Left Corner",
        "description": "General bottom-left watermark placement.",
        "type": "relative",
        "calc": lambda w, h: {
            "x": int(w * 0.02),
            "y": int(h * 0.88),
            "w": int(w * 0.20),
            "h": int(h * 0.10)
        }
    },
    "top_right": {
        "name": "Top-Right Corner",
        "description": "General top-right watermark placement.",
        "type": "relative",
        "calc": lambda w, h: {
            "x": int(w * 0.78),
            "y": int(h * 0.02),
            "w": int(w * 0.20),
            "h": int(h * 0.10)
        }
    },
    "top_left": {
        "name": "Top-Left Corner",
        "description": "General top-left watermark placement.",
        "type": "relative",
        "calc": lambda w, h: {
            "x": int(w * 0.02),
            "y": int(h * 0.02),
            "w": int(w * 0.20),
            "h": int(h * 0.10)
        }
    },
    "bottom_center": {
        "name": "Bottom-Center Banner",
        "description": "Watermark or ticker in bottom center.",
        "type": "relative",
        "calc": lambda w, h: {
            "x": int(w * 0.25),
            "y": int(h * 0.90),
            "w": int(w * 0.50),
            "h": int(h * 0.08)
        }
    }
}


def get_preset_coordinates(preset_id: str, width: int, height: int):
    """
    Returns calculated pixel coordinates (x, y, w, h) for a given preset and video dimension.
    """
    preset = PRESETS.get(preset_id)
    if not preset or preset.get("type") == "custom":
        return None
    
    coords = preset["calc"](width, height)
    # Ensure bounds
    coords["x"] = max(0, min(coords["x"], width - 1))
    coords["y"] = max(0, min(coords["y"], height - 1))
    coords["w"] = max(1, min(coords["w"], width - coords["x"]))
    coords["h"] = max(1, min(coords["h"], height - coords["y"]))
    return coords

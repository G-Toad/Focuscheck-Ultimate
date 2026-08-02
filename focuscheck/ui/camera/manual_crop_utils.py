"""Shared helper functions for manual camera cropping.

These utilities are pure functions to keep UI classes smaller and easier
for code editors/AI tools to navigate.
"""
from typing import Tuple

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    np = None


def _clamp(val: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, val))


def calculate_crop_region(settings: dict, frame_width: int, frame_height: int) -> Tuple[int, int, int, int]:
    """Compute the crop rectangle based on manual crop settings.

    Returns (x1, y1, x2, y2) in frame coordinates.
    """
    anchor_mode = settings.get("manual_crop_anchor_mode", "center")
    zoom = float(settings.get("manual_crop_zoom", 1.0))
    box_width = int(settings.get("manual_crop_box_width", 400))
    box_height = int(settings.get("manual_crop_box_height", 300))

    crop_width = min(int(box_width / max(zoom, 0.0001)), frame_width)
    crop_height = min(int(box_height / max(zoom, 0.0001)), frame_height)

    if anchor_mode == "center":
        offset_x = float(settings.get("manual_crop_center_offset_x", 0.0))
        offset_y = float(settings.get("manual_crop_center_offset_y", 0.0))
        center_x = frame_width // 2 + int(offset_x * frame_width)
        center_y = frame_height // 2 + int(offset_y * frame_height)
        x1 = center_x - crop_width // 2
        y1 = center_y - crop_height // 2

    elif anchor_mode == "edge":
        edge = settings.get("manual_crop_edge", "top")
        offset = float(settings.get("manual_crop_edge_offset", 0.0))
        if edge == "top":
            x1 = int((frame_width - crop_width) / 2 + offset * frame_width)
            y1 = 0
        elif edge == "bottom":
            x1 = int((frame_width - crop_width) / 2 + offset * frame_width)
            y1 = frame_height - crop_height
        elif edge == "left":
            x1 = 0
            y1 = int((frame_height - crop_height) / 2 + offset * frame_height)
        else:  # right
            x1 = frame_width - crop_width
            y1 = int((frame_height - crop_height) / 2 + offset * frame_height)

    elif anchor_mode == "corner":
        corner = settings.get("manual_crop_corner", "top_left")
        expand_x = float(settings.get("manual_crop_corner_expand_x", 1.0))
        expand_y = float(settings.get("manual_crop_corner_expand_y", 1.0))
        if corner == "top_left":
            x1, y1 = 0, 0
        elif corner == "top_right":
            x1, y1 = frame_width - int(crop_width * expand_x), 0
        elif corner == "bottom_left":
            x1, y1 = 0, frame_height - int(crop_height * expand_y)
        else:  # bottom_right
            x1 = frame_width - int(crop_width * expand_x)
            y1 = frame_height - int(crop_height * expand_y)
    else:
        x1 = (frame_width - crop_width) // 2
        y1 = (frame_height - crop_height) // 2

    x2 = x1 + crop_width
    y2 = y1 + crop_height

    x1 = _clamp(x1, 0, frame_width)
    y1 = _clamp(y1, 0, frame_height)
    x2 = _clamp(x2, 0, frame_width)
    y2 = _clamp(y2, 0, frame_height)

    if x2 <= x1 or y2 <= y1:
        return 0, 0, frame_width, frame_height
    return x1, y1, x2, y2


def process_manual_crop_frame(frame, settings: dict):
    """Crop and resize a frame using manual crop settings.

    Returns a frame of the target box size. On failure returns resized full frame.
    """
    if not CV2_AVAILABLE or frame is None:
        return frame

    if frame.size == 0:
        return frame

    frame_height, frame_width = frame.shape[:2]
    box_width = int(settings.get("manual_crop_box_width", 400))
    box_height = int(settings.get("manual_crop_box_height", 300))

    x1, y1, x2, y2 = calculate_crop_region(settings, frame_width, frame_height)

    if x2 <= x1 or y2 <= y1:
        return cv2.resize(frame, (box_width, box_height), interpolation=cv2.INTER_LINEAR)

    cropped = frame[y1:y2, x1:x2]
    return cv2.resize(cropped, (box_width, box_height), interpolation=cv2.INTER_LINEAR)

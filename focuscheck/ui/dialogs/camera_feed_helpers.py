"""Helpers for camera feed mixin to reduce class size."""

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    np = None

from ...utils import get_logger  # type: ignore


def resize_maintain_aspect(frame, max_width, max_height):
    if not CV2_AVAILABLE or frame is None:
        return None
    if frame.size == 0:
        return None
    frame_height, frame_width = frame.shape[:2]
    aspect_ratio = frame_width / frame_height if frame_height else 1.0
    if frame_width > frame_height:
        new_width = min(max_width, frame_width)
        new_height = int(new_width / max(aspect_ratio, 0.0001))
        if new_height > max_height:
            new_height = max_height
            new_width = int(new_height * aspect_ratio)
    else:
        new_height = min(max_height, frame_height)
        new_width = int(new_height * aspect_ratio)
        if new_width > max_width:
            new_width = max_width
            new_height = int(new_width / max(aspect_ratio, 0.0001))
    return cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)


def resize_fixed(frame, width, height):
    if not CV2_AVAILABLE or frame is None:
        return None
    if frame.size == 0:
        return None
    return cv2.resize(frame, (int(width), int(height)), interpolation=cv2.INTER_LANCZOS4)


def pad_frame_to_display(self, frame):
    """Pad/center a frame to fit the fixed display size (overlay aware)."""
    if not CV2_AVAILABLE:
        return None
    if frame is None or frame.size == 0:
        return np.zeros((self._camera_display_height, self._camera_display_width, 3), dtype=np.uint8)

    frame_h, frame_w = frame.shape[:2]
    display_w = self._camera_display_width
    display_h = self._camera_display_height

    if frame_w == display_w and frame_h == display_h:
        return frame

    maximize = bool(self.settings.get("camera_face_maximize_in_display", True))

    if maximize and self._camera_sizing_mode == "face_tracking":
        scale_w = display_w / frame_w
        scale_h = display_h / frame_h
        scale = max(scale_w, scale_h)
        new_w = int(frame_w * scale)
        new_h = int(frame_h * scale)
        scaled_frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

        if new_w > display_w:
            crop_x = (new_w - display_w) // 2
            scaled_frame = scaled_frame[:, crop_x:crop_x + display_w]
        elif new_w < display_w:
            pad_left = (display_w - new_w) // 2
            pad_right = display_w - new_w - pad_left
            scaled_frame = cv2.copyMakeBorder(scaled_frame, 0, 0, pad_left, pad_right,
                                              cv2.BORDER_CONSTANT, value=(0, 0, 0))

        if new_h > display_h:
            crop_y = (new_h - display_h) // 2
            scaled_frame = scaled_frame[crop_y:crop_y + display_h, :]
        elif new_h < display_h:
            pad_top = (display_h - new_h) // 2
            pad_bottom = display_h - new_h - pad_top
            scaled_frame = cv2.copyMakeBorder(scaled_frame, pad_top, pad_bottom, 0, 0,
                                              cv2.BORDER_CONSTANT, value=(0, 0, 0))
        return scaled_frame

    pad_top = max(0, (display_h - frame_h) // 2)
    pad_bottom = max(0, display_h - frame_h - pad_top)
    pad_left = max(0, (display_w - frame_w) // 2)
    pad_right = max(0, display_w - frame_w - pad_left)
    return cv2.copyMakeBorder(frame, pad_top, pad_bottom, pad_left, pad_right,
                              cv2.BORDER_CONSTANT, value=(0, 0, 0))


def log_error(msg):
    try:
        get_logger().error(msg)
    except Exception:
        pass

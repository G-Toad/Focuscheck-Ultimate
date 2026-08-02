"""Shared helpers for camera adjustment windows.

Centralizes image processing so UI classes stay lean.
"""

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import numpy as np
except ImportError:
    np = None

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None


def _camera_processing_available():
    return cv2 is not None and np is not None


def resize_for_display(frame, target_width=400):
    """Resize frame for display keeping aspect ratio around target_width."""
    if frame is None or frame.size == 0:
        return frame
    if cv2 is None:
        return frame
    height, width = frame.shape[:2]
    aspect_ratio = width / max(1, height)
    target_height = int(target_width / aspect_ratio)
    return cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_LANCZOS4)


def auto_adapt_settings(frame, brightness, contrast):
    """Scale brightness/contrast based on environment brightness."""
    try:
        if not _camera_processing_available():
            return brightness, contrast
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)
        normalized = mean_brightness / 255.0

        if normalized < 0.3:
            brightness_scale = 1.5
        elif normalized > 0.7:
            brightness_scale = 0.7
        else:
            brightness_scale = 1.0

        adapted_brightness = np.clip(0.5 + ((brightness - 0.5) * brightness_scale), 0.0, 1.0)

        std_brightness = np.std(gray)
        contrast_scale = 1.3 if std_brightness < 30 else 1.0
        adapted_contrast = np.clip(0.5 + ((contrast - 0.5) * contrast_scale), 0.0, 1.0)

        return adapted_brightness, adapted_contrast
    except Exception:
        return brightness, contrast


def apply_manual_adjustments(frame, params):
    """Apply brightness/contrast/saturation/sharpness/gamma/tint adjustments."""
    if frame is None or frame.size == 0:
        return frame
    if not _camera_processing_available():
        return frame

    try:
        enhanced = frame.copy()

        brightness = params.get("brightness", 0.5)
        contrast = params.get("contrast", 0.5)
        saturation = params.get("saturation", 0.5)
        sharpness = params.get("sharpness", 0.5)
        gamma = params.get("gamma", 0.5)
        tint = params.get("tint", 0.5)
        auto_adapt = params.get("auto_adapt", False)

        if auto_adapt:
            brightness, contrast = auto_adapt_settings(enhanced, brightness, contrast)

        brightness_amount = int((brightness - 0.5) * 200)
        if brightness_amount:
            enhanced = cv2.convertScaleAbs(enhanced, alpha=1.0, beta=brightness_amount)

        contrast_amount = 0.5 + (contrast * 1.5)
        if contrast_amount != 1.0:
            enhanced = cv2.convertScaleAbs(enhanced, alpha=contrast_amount, beta=0)

        saturation_amount = saturation * 2.0
        hsv = cv2.cvtColor(enhanced, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation_amount, 0, 255)
        enhanced = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        if sharpness > 0.5:
            sharp_amount = (sharpness - 0.5) * 4.0
            gaussian = cv2.GaussianBlur(enhanced, (0, 0), 3)
            enhanced = cv2.addWeighted(enhanced, 1.0 + sharp_amount, gaussian, -sharp_amount, 0)
            enhanced = np.clip(enhanced, 0, 255).astype(np.uint8)
        elif sharpness < 0.5:
            blur_amount = int((0.5 - sharpness) * 20) + 1
            if blur_amount % 2 == 0:
                blur_amount += 1
            enhanced = cv2.GaussianBlur(enhanced, (blur_amount, blur_amount), 0)

        gamma_value = 0.5 + (gamma * 1.5)
        if gamma_value != 1.0:
            inv_gamma = 1.0 / gamma_value
            gamma_table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype("uint8")
            enhanced = cv2.LUT(enhanced, gamma_table)

        if tint != 0.5:
            tint_amount = (tint - 0.5) * 2.0
            if tint_amount > 0:
                enhanced[:, :, 0] = np.clip(enhanced[:, :, 0] * (1.0 - tint_amount * 0.3), 0, 255)
                enhanced[:, :, 2] = np.clip(enhanced[:, :, 2] * (1.0 + tint_amount * 0.2), 0, 255)
            else:
                tint_amount = abs(tint_amount)
                enhanced[:, :, 0] = np.clip(enhanced[:, :, 0] * (1.0 + tint_amount * 0.3), 0, 255)
                enhanced[:, :, 2] = np.clip(enhanced[:, :, 2] * (1.0 - tint_amount * 0.2), 0, 255)
            enhanced = enhanced.astype(np.uint8)

        return enhanced
    except Exception:
        return frame


def frame_to_photo(frame):
    """Convert BGR frame to ImageTk.PhotoImage for Tk labels."""
    if cv2 is None or Image is None or ImageTk is None:
        raise RuntimeError("Camera display requires opencv-python and Pillow")
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(rgb)
    return ImageTk.PhotoImage(image=pil_image)

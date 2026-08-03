"""
Camera feed mixin for PromptDialog.

This mixin provides camera feed functionality for self-reflection,
including live feed display and photo capture for accountability logs.
"""

import tkinter as tk
from tkinter import messagebox
from datetime import datetime
import os
import sys
import tempfile
from pathlib import Path

from ...camera.manual_crop_utils import process_manual_crop_frame
from ...camera.capability import build_camera_capability, camera_capability_message
from ..camera_feed_helpers import (
    resize_maintain_aspect,
    resize_fixed,
    pad_frame_to_display,
    log_error,
)

try:
    from ....utils import get_logger
except ImportError:
    def get_logger():
        import logging
        return logging.getLogger(__name__)

# Try to import cv2 (OpenCV) for camera access
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    np = None

# Try to import PIL for image conversion
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    ImageTk = None


class CameraFeedMixin:
    """
    Mixin that adds camera feed functionality to PromptDialog.

    Features:
    - Live camera feed display
    - Static snapshot mode
    - Photo capture on button clicks
    - Configurable sizing and positioning
    """

    def _init_camera_feed(self):
        """
        Initialize camera feed components.

        Must be called during PromptDialog initialization.
        Sets up camera capture, feed display, and related state.
        """
        self._camera_enabled = bool(self.settings.get("camera_feed_enabled", False))
        self._camera_feed_container = None
        self._camera_label = None
        self._camera_capture = None
        self._camera_update_timer = None
        self._biodata_pulse_timer_ids = set()
        self._camera_generation = 0
        self._camera_static_image = None
        self._camera_mode = self.settings.get("camera_feed_mode", "live")
        self._camera_sizing_mode = self.settings.get("camera_sizing_mode", "aspect_ratio")
        self._camera_face_cascade = None
        self._camera_last_face_rect = None  # Cache last detected face position
        self._camera_frame_count = 0  # For face detection throttling (performance)
        self._camera_face_miss_count = 0  # Track consecutive frames without face detection
        self._camera_capability = build_camera_capability(
            enabled=self._camera_enabled,
            opencv_available=CV2_AVAILABLE,
            pillow_available=PIL_AVAILABLE,
        )

        # Apply UI scaling to camera dimensions
        scale = getattr(self, '_ui_scale', 1.0)
        self._camera_display_width = int(320 * scale)  # Will be set properly when widget created
        self._camera_display_height = int(240 * scale)

        if not self._camera_enabled:
            return

        # Check if required libraries are available
        if not CV2_AVAILABLE:
            try:
                get_logger().warning("Camera feed enabled but cv2 (OpenCV) not available. Install with: pip install opencv-python")
            except Exception:
                pass
            return

        if not PIL_AVAILABLE:
            try:
                get_logger().warning("Camera feed enabled but PIL (Pillow) not available. Install with: pip install pillow")
            except Exception:
                pass
            return

        try:
            # Initialize camera
            camera_index = int(self.settings.get("camera_device_index", 0))
            self._camera_capture = cv2.VideoCapture(camera_index)

            if not self._camera_capture.isOpened():
                try:
                    get_logger().warning(f"Could not open camera at index {camera_index}")
                except Exception:
                    pass
                self._camera_capture = None
                self._camera_capability = build_camera_capability(
                    enabled=True,
                    opencv_available=CV2_AVAILABLE,
                    pillow_available=PIL_AVAILABLE,
                    device_open=False,
                )
                return

            # Set high camera resolution to allow for cropping/zooming
            self._camera_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self._camera_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

            # Load face detection model if face tracking is enabled
            if self._camera_sizing_mode == "face_tracking":
                detection_method = self.settings.get("camera_face_detection_method", "haar")

                if detection_method == "dnn":
                    # Try to load DNN face detector (more accurate but slower)
                    try:
                        # Use OpenCV's DNN face detector
                        model_file = cv2.data.haarcascades.replace("haarcascades", "")
                        # This is a placeholder - DNN models need to be downloaded separately
                        # For now, fall back to Haar if DNN not available
                        try:
                            get_logger().info("DNN detection selected but not yet fully implemented, falling back to Haar")
                        except Exception:
                            pass
                        detection_method = "haar"
                    except Exception:
                        detection_method = "haar"

                if detection_method == "haar":
                    # Load Haar Cascade for face detection (fast and reliable)
                    try:
                        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                        self._camera_face_cascade = cv2.CascadeClassifier(cascade_path)

                        if self._camera_face_cascade.empty():
                            try:
                                get_logger().warning("Failed to load face detection cascade, falling back to aspect_ratio mode")
                            except Exception:
                                pass
                            self._camera_face_cascade = None
                            self._camera_sizing_mode = "aspect_ratio"
                    except Exception as e:
                        try:
                            get_logger().error(f"Face detection initialization failed: {e}")
                        except Exception:
                            pass
                        self._camera_face_cascade = None
                        self._camera_sizing_mode = "aspect_ratio"

            try:
                get_logger().info(f"Camera initialized successfully in {self._camera_mode} mode with {self._camera_sizing_mode} sizing")
            except Exception:
                pass
            self._camera_capability = build_camera_capability(
                enabled=True,
                opencv_available=CV2_AVAILABLE,
                pillow_available=PIL_AVAILABLE,
                device_open=True,
                access="granted",
            )

        except Exception as e:
            try:
                get_logger().error(f"Failed to initialize camera: {e}")
            except Exception:
                pass
            self._camera_capture = None
            self._camera_capability = build_camera_capability(
                enabled=True,
                opencv_available=CV2_AVAILABLE,
                pillow_available=PIL_AVAILABLE,
                device_open=False,
                access="failed",
                error=e,
            )

    def _create_camera_feed_widget(self, parent_container):
        """
        Create the camera feed display widget.

        Args:
            parent_container: Parent tkinter container to add camera feed to

        Returns:
            Frame containing the camera feed or an unavailable-capability notice.
        """
        if not self._camera_enabled:
            return None

        if self._camera_capture is None:
            # Keep the prompt usable while making an opted-in unavailable
            # capability explicit instead of silently removing the section.
            self._camera_feed_container = tk.Frame(parent_container, bg="#111")
            tk.Label(
                self._camera_feed_container,
                text=camera_capability_message(getattr(self, "_camera_capability", {})),
                fg="#d9c98c",
                bg="#111",
                justify="left",
                anchor="w",
                wraplength=420,
                padx=8,
                pady=6,
            ).pack(fill="x")
            return self._camera_feed_container

        try:
            # Determine the fixed display size based on sizing mode
            scale = getattr(self, '_ui_scale', 1.0)
            if self._camera_sizing_mode == "face_tracking":
                # Use face tracking max dimensions as display size
                display_width = int(self.settings.get("camera_face_max_width", 400) * scale)
                display_height = int(self.settings.get("camera_face_max_height", 300) * scale)
            else:
                # Use fixed size / aspect ratio max dimensions
                display_width = int(self.settings.get("camera_feed_width", 320) * scale)
                display_height = int(self.settings.get("camera_feed_height", 240) * scale)

            # Store display dimensions for padding later
            self._camera_display_width = display_width
            self._camera_display_height = display_height

            # Create container frame for camera feed with PIXEL dimensions
            self._camera_feed_container = tk.Frame(
                parent_container,
                bg="#000",
                highlightthickness=2,
                highlightbackground="#444",
                width=display_width + 4,
                height=display_height + 4
            )
            self._camera_feed_container.pack_propagate(False)  # Lock to pixel size

            # Create label to fill the frame (no width/height - those are in characters!)
            self._camera_label = tk.Label(
                self._camera_feed_container,
                bg="#000"
            )
            self._camera_label.pack(fill="both", expand=True, padx=2, pady=2)

            # Start camera feed based on mode
            if self._camera_mode == "static":
                # Capture a single frame and display it
                self._capture_and_display_static_frame()
            else:
                # Start live feed updates
                self._start_camera_feed_updates()

            self._camera_capability = build_camera_capability(
                enabled=True,
                opencv_available=CV2_AVAILABLE,
                pillow_available=PIL_AVAILABLE,
                device_open=True,
                stream_active=True,
                access="granted",
            )

            return self._camera_feed_container

        except Exception as e:
            try:
                get_logger().error(f"Failed to create camera feed widget: {e}")
            except Exception:
                pass
            return None

    def _capture_and_display_static_frame(self):
        """
        Capture a single frame from camera and display it statically.

        Used when camera_feed_mode is "static".
        """
        if self._camera_capture is None:
            return

        try:
            ret, frame = self._camera_capture.read()
            if ret:
                # Store the frame for later use (e.g., saving on button click)
                self._camera_static_image = frame.copy()

                # Convert and display
                self._display_camera_frame(frame)
            else:
                try:
                    get_logger().warning("Failed to capture static camera frame")
                except Exception:
                    pass
        except Exception as e:
            try:
                get_logger().error(f"Error capturing static frame: {e}")
            except Exception:
                pass

    def _start_camera_feed_updates(self, generation=None):
        """
        Start the live camera feed update loop.

        Updates camera frames at the configured FPS rate.
        """
        current_generation = getattr(self, "_camera_generation", 0)
        if generation is None:
            generation = current_generation
        if generation != current_generation or self._camera_capture is None or getattr(self, "_closed", False):
            return

        try:
            ret, frame = self._camera_capture.read()
            if ret:
                self._display_camera_frame(frame)
            else:
                self._camera_capability = build_camera_capability(
                    enabled=True,
                    opencv_available=CV2_AVAILABLE,
                    pillow_available=PIL_AVAILABLE,
                    device_open=True,
                    stream_active=True,
                    access="granted",
                    degraded=True,
                )

            # Schedule next update
            fps = int(self.settings.get("camera_fps", 30))
            update_interval_ms = max(16, int(1000 / fps))  # Minimum 16ms (60 FPS max)

            # Replace the named timer so dialog cleanup owns the next frame.
            if self._camera_update_timer is not None:
                if hasattr(self, "_cancel_timer"):
                    self._cancel_timer(self._camera_update_timer)
                else:
                    try:
                        self.after_cancel(self._camera_update_timer)
                    except Exception:
                        pass
            if hasattr(self, "_schedule_timer"):
                self._camera_update_timer = self._schedule_timer(
                    update_interval_ms,
                    lambda: self._start_camera_feed_updates(generation),
                )
            else:
                self._camera_update_timer = self.after(
                    update_interval_ms,
                    self._start_camera_feed_updates,
                    generation,
                )

        except Exception as e:
            try:
                get_logger().error(f"Error in camera feed update: {e}")
            except Exception:
                pass

    def _validate_face_rect(self, rect, frame_width, frame_height):
        """
        Validate if a detected rectangle is likely a real face.

        Args:
            rect: Tuple (x, y, w, h) of detected face rectangle
            frame_width: Width of the camera frame
            frame_height: Height of the camera frame

        Returns:
            True if rectangle passes validation, False otherwise
        """
        x, y, w, h = rect

        # Check minimum size (proportional to frame height)
        min_face_height = int(frame_height * 0.1)  # Face should be at least 10% of frame height
        if h < min_face_height or w < min_face_height:
            return False

        # Check aspect ratio (faces should be roughly square to slightly tall)
        aspect_ratio = w / h
        if aspect_ratio < 0.5 or aspect_ratio > 1.5:
            return False

        # Check if rectangle is within frame bounds
        if x < 0 or y < 0 or x + w > frame_width or y + h > frame_height:
            return False

        # Check if rectangle isn't too large (likely not a face if it's >60% of frame)
        max_face_area = frame_width * frame_height * 0.6
        face_area = w * h
        if face_area > max_face_area:
            return False

        return True

    def _process_camera_frame(self, frame):
        """
        Process camera frame based on sizing mode (aspect ratio, fixed size, or face tracking).

        Args:
            frame: OpenCV frame (BGR format)

        Returns:
            Processed frame ready for display, or None if processing failed
        """
        if frame is None:
            return None

        try:
            frame_height, frame_width = frame.shape[:2]

            # Mode 1: Face Tracking
            if self._camera_sizing_mode == "face_tracking" and self._camera_face_cascade is not None:
                # PERFORMANCE: Only run face detection every N frames to reduce CPU usage
                # On low-end CPUs (1.3 GHz), face detection is VERY expensive
                self._camera_frame_count += 1
                face_detection_interval = self.settings.get("camera_face_detection_interval", 10)  # Default: every 10 frames

                should_detect_face = (
                    self._camera_frame_count % face_detection_interval == 0 or  # Regular interval
                    self._camera_last_face_rect is None  # Or no face cached yet
                )

                if should_detect_face:
                    # Detect faces with saner parameters to avoid false positives
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                    # Calculate proportional minimum face size (8% of frame height)
                    min_face_size = int(frame_height * 0.08)

                    faces = self._camera_face_cascade.detectMultiScale(
                        gray,
                        scaleFactor=1.1,              # More conservative than 1.05
                        minNeighbors=5,               # Higher threshold to reduce false positives
                        minSize=(min_face_size, min_face_size)  # Proportional to frame size
                    )

                    # Find valid face (largest that passes validation)
                    valid_face = None
                    if len(faces) > 0:
                        # Sort by size (largest first)
                        sorted_faces = sorted(faces, key=lambda r: r[2] * r[3], reverse=True)

                        # Find first valid face
                        for face_rect in sorted_faces:
                            if self._validate_face_rect(face_rect, frame_width, frame_height):
                                valid_face = face_rect
                                break

                    if valid_face is not None:
                        # Valid face detected - update cache and reset miss counter
                        self._camera_last_face_rect = valid_face
                        self._camera_face_miss_count = 0
                    else:
                        # No valid face detected - increment miss counter
                        self._camera_face_miss_count += 1

                        # Expire cached face after too many consecutive misses
                        max_misses = self.settings.get("camera_face_max_misses", 5)
                        if self._camera_face_miss_count >= max_misses:
                            self._camera_last_face_rect = None

                # Use cached face rect (either just detected or from previous frames)
                if self._camera_last_face_rect is not None:
                    x, y, w, h = self._camera_last_face_rect

                    # Calculate face center with configurable vertical bias
                    # Higher bias = more chin/neck visible (0.5=middle, 0.65=recommended, 1.0=bottom)
                    vertical_bias = float(self.settings.get("camera_face_center_vertical_bias", 0.65))
                    face_center_x = x + w // 2
                    face_center_y = y + int(h * vertical_bias)

                    # Apply zoom factor to include context around face
                    zoom_factor = float(self.settings.get("camera_face_zoom_factor", 1.5))

                    # Calculate desired crop size with configurable multipliers
                    # These expand the crop beyond the detected face box to ensure full face + chin
                    width_mult = float(self.settings.get("camera_face_crop_width_multiplier", 1.4))
                    height_mult = float(self.settings.get("camera_face_crop_height_multiplier", 1.6))

                    # EDGE-AWARE ZOOM: Check if face is near frame edges
                    edge_aware = self.settings.get("camera_face_edge_aware_zoom", True)
                    if edge_aware:
                        edge_threshold = float(self.settings.get("camera_face_edge_threshold", 0.25))  # Increased from 0.15
                        # Calculate distance from edges (normalized 0-1)
                        dist_left = face_center_x / frame_width
                        dist_right = 1.0 - (face_center_x / frame_width)
                        dist_top = face_center_y / frame_height
                        dist_bottom = 1.0 - (face_center_y / frame_height)

                        # Check if any edge is close
                        min_dist = min(dist_left, dist_right, dist_top, dist_bottom)
                        if min_dist < edge_threshold:
                            # Apply edge zoom multiplier to zoom out and prevent cutoff
                            edge_mult = float(self.settings.get("camera_face_edge_zoom_multiplier", 1.5))  # Increased from 1.3
                            width_mult *= edge_mult
                            height_mult *= edge_mult

                        # Extra protection for bottom edge (chin area) - be more aggressive
                        if dist_bottom < edge_threshold * 1.5:  # Trigger even earlier for bottom
                            height_mult *= 1.2  # Extra vertical space

                    crop_w = int(w * zoom_factor * width_mult)
                    crop_h = int(h * zoom_factor * height_mult)

                    # Calculate crop region - now centered on the adjusted (lower) center point
                    x1 = face_center_x - crop_w // 2
                    y1 = face_center_y - crop_h // 2
                    x2 = x1 + crop_w
                    y2 = y1 + crop_h

                    # Adjust if crop goes out of bounds while maintaining size
                    if x1 < 0:
                        x2 = min(frame_width, x2 - x1)
                        x1 = 0
                    if y1 < 0:
                        y2 = min(frame_height, y2 - y1)
                        y1 = 0
                    if x2 > frame_width:
                        x1 = max(0, x1 - (x2 - frame_width))
                        x2 = frame_width
                    if y2 > frame_height:
                        y1 = max(0, y1 - (y2 - frame_height))
                        y2 = frame_height

                    # Crop to face region - now includes full face + chin + context
                    face_frame = frame[y1:y2, x1:x2]

                    # Get max dimensions for face tracking
                    max_width = int(self.settings.get("camera_face_max_width", 400))
                    max_height = int(self.settings.get("camera_face_max_height", 300))

                    # Resize maintaining aspect ratio to fit within max dimensions
                    return self._resize_maintain_aspect(face_frame, max_width, max_height)

                else:
                    # No valid cached face - honor the configured fallback mode.
                    # This prevents using stale/bogus face rectangles (like curtains)
                    if str(self.settings.get("camera_face_fallback_mode", "aspect_ratio")).strip().lower() == "fixed_size":
                        return self._resize_fixed_size(frame)
                    max_width = int(self.settings.get("camera_face_max_width", 400))
                    max_height = int(self.settings.get("camera_face_max_height", 300))
                    return self._resize_maintain_aspect(frame, max_width, max_height)

            # Mode 2: Fixed Size (may distort)
            elif self._camera_sizing_mode == "fixed_size":
                return self._resize_fixed_size(frame)

            # Mode 3: Manual Crop (custom crop with user-defined parameters)
            elif self._camera_sizing_mode == "manual_crop":
                return self._process_manual_crop(frame)

            # Mode 4: Aspect Ratio (default)
            else:
                width = int(self.settings.get("camera_feed_width", 320))
                height = int(self.settings.get("camera_feed_height", 240))
                return self._resize_maintain_aspect(frame, width, height)

        except Exception as e:
            try:
                get_logger().error(f"Error processing camera frame: {e}")
            except Exception:
                pass
            return frame  # Return original frame on error

    def _resize_maintain_aspect(self, frame, max_width, max_height):
        return resize_maintain_aspect(frame, max_width, max_height)

    def _resize_fixed_size(self, frame):
        width = int(self.settings.get("camera_feed_width", 320))
        height = int(self.settings.get("camera_feed_height", 240))
        return resize_fixed(frame, width, height)

    def _process_manual_crop(self, frame):
        """Process frame with manual crop settings using shared helper."""
        try:
            return process_manual_crop_frame(frame, self.settings)
        except Exception as e:
            try:
                get_logger().error(f"Error in manual crop processing: {e}")
            except Exception:
                pass
            return frame

    def _pad_frame_to_display_size(self, frame):
        return pad_frame_to_display(self, frame)


    def _apply_camera_effects(self, frame):
        """
        Apply visual effects and enhancements to camera frame.

        Features:
        - Face detection visualization (markers and lines)
        - B&W color inversion
        - Adaptive brightness/contrast for overexposed or dim environments

        Args:
            frame: OpenCV frame (BGR format)

        Returns:
            Enhanced frame with applied effects
        """
        if frame is None or frame.size == 0:
            return frame

        enhanced_frame = frame.copy()

        try:
            # 1. ADAPTIVE BRIGHTNESS/CONTRAST (apply first, before overlays)
            brightness_result = self._apply_adaptive_brightness(enhanced_frame)
            # Safety check: if brightness adjustment resulted in a black/corrupt frame, skip it
            if brightness_result is not None and brightness_result.size > 0 and np.max(brightness_result) > 0:
                enhanced_frame = brightness_result

            # 2. B&W INVERSION
            if self.settings.get("camera_invert_colors", False):
                enhanced_frame = cv2.bitwise_not(enhanced_frame)

            # 3. FACE DETECTION VISUALIZATION (apply last, on top of everything)
            if self.settings.get("camera_show_face_detection", False):
                enhanced_frame = self._draw_face_detection_overlay(enhanced_frame)

            # Final safety check: if frame is completely black, return original
            if np.max(enhanced_frame) == 0:
                return frame

            return enhanced_frame

        except Exception as e:
            try:
                get_logger().error(f"Error applying camera effects: {e}")
            except Exception:
                pass
            return frame  # Return original on error

    def _apply_adaptive_brightness(self, frame):
        """
        Apply manual camera adjustments with optional auto-adapt.

        Uses saved manual settings (brightness, contrast, saturation, etc.)
        with intelligent auto-adaptation based on lighting conditions.

        Args:
            frame: OpenCV frame (BGR format)

        Returns:
            Enhanced frame
        """
        if frame is None or frame.size == 0:
            return frame

        try:
            # Check if manual adjustments are enabled
            if not self.settings.get("camera_manual_adjustments_enabled", False):
                return frame  # Nothing to do

            enhanced = frame.copy()

            # Get saved manual settings
            brightness = float(self.settings.get("camera_manual_brightness", 0.5))  # 0.0-1.0
            contrast = float(self.settings.get("camera_manual_contrast", 0.5))
            saturation = float(self.settings.get("camera_manual_saturation", 0.5))
            sharpness = float(self.settings.get("camera_manual_sharpness", 0.5))
            gamma = float(self.settings.get("camera_manual_gamma", 0.5))
            tint = float(self.settings.get("camera_manual_tint", 0.5))

            # If auto-adapt is enabled, scale settings based on environment
            if self.settings.get("camera_auto_adapt", False):
                gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
                mean_brightness = np.mean(gray) / 255.0  # Normalize to 0-1

                # Adapt brightness based on environment
                if mean_brightness < 0.3:  # Dark environment
                    brightness = 0.5 + ((brightness - 0.5) * 1.5)
                elif mean_brightness > 0.7:  # Bright environment
                    brightness = 0.5 + ((brightness - 0.5) * 0.7)

                # Adapt contrast based on scene variance
                std_brightness = np.std(gray)
                if std_brightness < 30:  # Low contrast scene
                    contrast = 0.5 + ((contrast - 0.5) * 1.3)

                brightness = np.clip(brightness, 0.0, 1.0)
                contrast = np.clip(contrast, 0.0, 1.0)

            # Apply adjustments
            # 1. BRIGHTNESS: -100 to +100
            brightness_amount = int((brightness - 0.5) * 200)
            if brightness_amount != 0:
                enhanced = cv2.convertScaleAbs(enhanced, alpha=1.0, beta=brightness_amount)

            # 2. CONTRAST: 0.5x to 2.0x
            contrast_amount = 0.5 + (contrast * 1.5)
            if contrast_amount != 1.0:
                enhanced = cv2.convertScaleAbs(enhanced, alpha=contrast_amount, beta=0)

            # 3. SATURATION: 0.0 (grayscale) to 2.0 (very vibrant)
            saturation_amount = saturation * 2.0
            hsv = cv2.cvtColor(enhanced, cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation_amount, 0, 255)
            enhanced = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

            # 4. SHARPNESS: Blur to sharp
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

            # 5. GAMMA: Lift shadows to crush blacks
            gamma_value = 0.5 + (gamma * 1.5)
            if gamma_value != 1.0:
                inv_gamma = 1.0 / gamma_value
                gamma_table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype("uint8")
                enhanced = cv2.LUT(enhanced, gamma_table)

            # 6. TINT: Cool (blue) to warm (orange)
            if tint != 0.5:
                tint_amount = (tint - 0.5) * 2.0

                if tint_amount > 0:  # Warm
                    enhanced[:, :, 0] = np.clip(enhanced[:, :, 0] * (1.0 - tint_amount * 0.3), 0, 255)
                    enhanced[:, :, 2] = np.clip(enhanced[:, :, 2] * (1.0 + tint_amount * 0.2), 0, 255)
                else:  # Cool
                    tint_amount = abs(tint_amount)
                    enhanced[:, :, 0] = np.clip(enhanced[:, :, 0] * (1.0 + tint_amount * 0.3), 0, 255)
                    enhanced[:, :, 2] = np.clip(enhanced[:, :, 2] * (1.0 - tint_amount * 0.2), 0, 255)

                enhanced = enhanced.astype(np.uint8)

            return enhanced

        except Exception as e:
            try:
                get_logger().error(f"Error in adaptive brightness: {e}")
            except Exception:
                pass
            return frame

    def _draw_face_detection_overlay(self, frame):
        """
        Draw face detection markers and neural network visualization lines.

        Shows:
        - Rectangle around detected face
        - Center point marker
        - Crop region preview
        - Detection confidence (if available)

        Args:
            frame: OpenCV frame (BGR format)

        Returns:
            Frame with face detection overlay
        """
        if frame is None or frame.size == 0 or self._camera_face_cascade is None:
            return frame

        try:
            frame_with_overlay = frame.copy()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Detect faces
            faces = self._camera_face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.05,
                minNeighbors=3,
                minSize=(20, 20)
            )

            # Draw all detected faces
            for i, (x, y, w, h) in enumerate(faces):
                # Determine if this is the primary face (largest)
                is_primary = (i == 0 and len(faces) > 0)

                # Color: Green for primary face, yellow for others
                color = (0, 255, 0) if is_primary else (0, 255, 255)
                thickness = 2 if is_primary else 1

                # Draw face bounding box
                cv2.rectangle(frame_with_overlay, (x, y), (x + w, y + h), color, thickness)

                # Calculate face center with vertical bias
                vertical_bias = float(self.settings.get("camera_face_center_vertical_bias", 0.65))
                center_x = x + w // 2
                center_y = y + int(h * vertical_bias)

                # Draw center point
                cv2.circle(frame_with_overlay, (center_x, center_y), 5, color, -1)
                cv2.circle(frame_with_overlay, (center_x, center_y), 7, (255, 255, 255), 1)

                # Draw crosshair at center
                crosshair_size = 15
                cv2.line(frame_with_overlay,
                        (center_x - crosshair_size, center_y),
                        (center_x + crosshair_size, center_y),
                        color, 1)
                cv2.line(frame_with_overlay,
                        (center_x, center_y - crosshair_size),
                        (center_x, center_y + crosshair_size),
                        color, 1)

                if is_primary:
                    # Draw crop region preview for primary face
                    zoom_factor = float(self.settings.get("camera_face_zoom_factor", 1.5))
                    width_mult = float(self.settings.get("camera_face_crop_width_multiplier", 1.4))
                    height_mult = float(self.settings.get("camera_face_crop_height_multiplier", 1.6))

                    crop_w = int(w * zoom_factor * width_mult)
                    crop_h = int(h * zoom_factor * height_mult)

                    crop_x1 = center_x - crop_w // 2
                    crop_y1 = center_y - crop_h // 2
                    crop_x2 = crop_x1 + crop_w
                    crop_y2 = crop_y1 + crop_h

                    # Draw crop region (dashed lines)
                    self._draw_dashed_rectangle(frame_with_overlay,
                                                (crop_x1, crop_y1),
                                                (crop_x2, crop_y2),
                                                (255, 0, 255), 2)

                    # Draw detection info text
                    text = f"Face {w}x{h}"
                    cv2.putText(frame_with_overlay, text,
                               (x, y - 10),
                               cv2.FONT_HERSHEY_SIMPLEX,
                               0.5, color, 1, cv2.LINE_AA)

            # If no faces detected but we have cached face, show cache indicator
            if len(faces) == 0 and self._camera_last_face_rect is not None:
                x, y, w, h = self._camera_last_face_rect
                # Draw in orange to indicate cached detection
                cv2.rectangle(frame_with_overlay, (x, y), (x + w, y + h), (0, 165, 255), 1)
                cv2.putText(frame_with_overlay, "CACHED",
                           (x, y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX,
                           0.5, (0, 165, 255), 1, cv2.LINE_AA)

            return frame_with_overlay

        except Exception as e:
            try:
                get_logger().error(f"Error drawing face detection overlay: {e}")
            except Exception:
                pass
            return frame

    def _draw_dashed_rectangle(self, img, pt1, pt2, color, thickness):
        """Draw a dashed rectangle."""
        x1, y1 = pt1
        x2, y2 = pt2

        # Horizontal lines
        dash_length = 10
        gap_length = 5

        # Top line
        x = x1
        while x < x2:
            cv2.line(img, (x, y1), (min(x + dash_length, x2), y1), color, thickness)
            x += dash_length + gap_length

        # Bottom line
        x = x1
        while x < x2:
            cv2.line(img, (x, y2), (min(x + dash_length, x2), y2), color, thickness)
            x += dash_length + gap_length

        # Left line
        y = y1
        while y < y2:
            cv2.line(img, (x1, y), (x1, min(y + dash_length, y2)), color, thickness)
            y += dash_length + gap_length

        # Right line
        y = y1
        while y < y2:
            cv2.line(img, (x2, y), (x2, min(y + dash_length, y2)), color, thickness)
            y += dash_length + gap_length

    def _display_camera_frame(self, frame):
        """
        Convert OpenCV frame to PhotoImage and display in label.

        Args:
            frame: OpenCV frame (BGR format)
        """
        if self._camera_label is None or frame is None:
            return

        try:
            # Process frame based on sizing mode
            processed_frame = self._process_camera_frame(frame)
            if processed_frame is None:
                return

            # Pad/center to fixed display size to prevent window resizing
            display_frame = self._pad_frame_to_display_size(processed_frame)

            # Apply visual effects and enhancements
            display_frame = self._apply_camera_effects(display_frame)

            # Apply horizontal flip if enabled (mirror effect)
            if self.settings.get("camera_flip_horizontal", True):
                display_frame = cv2.flip(display_frame, 1)  # 1 = horizontal flip

            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)

            # Convert to PIL Image
            pil_image = Image.fromarray(rgb_frame)

            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(image=pil_image)

            # Update label
            self._camera_label.configure(image=photo)
            self._camera_label.image = photo  # Keep a reference to prevent garbage collection

        except Exception as e:
            try:
                get_logger().error(f"Error displaying camera frame: {e}")
            except Exception:
                pass

    def _capture_photo_for_logs(self, choice):
        """
        Capture a photo from the camera feed and save it to logs.

        Args:
            choice: String indicating user's choice ("Studying" or "Wasting time")

        Returns:
            str: Path to saved photo, or None if capture failed
        """
        if not bool(self.settings.get("camera_capture_on_click", False)):
            return None

        if self._camera_capture is None:
            return None

        try:
            # Determine which frame to save
            if self._camera_mode == "static" and self._camera_static_image is not None:
                # Use the static snapshot taken at popup start
                frame = self._camera_static_image
            else:
                # Capture current frame from live feed
                ret, frame = self._camera_capture.read()
                if not ret:
                    try:
                        get_logger().warning("Failed to capture photo for logs")
                    except Exception:
                        pass
                    return None

            # Create photos directory structure
            photos_dir = self._get_camera_photos_directory()
            photos_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename with timestamp and choice
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            choice_slug = choice.replace(" ", "_").lower()
            filename = f"{timestamp}_{choice_slug}.jpg"
            photo_path = photos_dir / filename

            # Save the photo
            if not cv2.imwrite(str(photo_path), frame):
                try:
                    photo_path.unlink(missing_ok=True)
                except OSError:
                    pass
                try:
                    get_logger().warning("Camera photo encoder did not write a file")
                except Exception:
                    pass
                return None

            try:
                get_logger().info(f"Captured photo saved to: {photo_path}")
            except Exception:
                pass

            return str(photo_path)

        except Exception as e:
            try:
                get_logger().error(f"Error capturing photo for logs: {e}")
            except Exception:
                pass
            return None

    def _get_camera_photos_directory(self):
        """
        Get the directory path for storing camera photos.

        Returns:
            Path: Directory path for camera photos
        """
        try:
            from ....utils.paths import get_app_paths
            app_data_dir = get_app_paths().root
            return Path(app_data_dir) / "camera_photos"
        except Exception:
            # Never fall back to the source/install directory for personal data.
            return Path(tempfile.gettempdir()) / "FocusCheck" / "camera_photos"

    def _create_biodata_label(self, parent_container):
        """
        Create biodata identity display - highly visible and attention-grabbing.

        Supports multiple visual styles:
        - dramatic: Red border, dark background, pulsing warning icons
        - simple: Clean bordered box with high contrast
        - minimal: Just bold text with subtle styling

        Args:
            parent_container: Parent tkinter container

        Returns:
            Frame widget with enhanced biodata display, or None if disabled/empty
        """
        if not self.settings.get("biodata_enabled", False):
            return None

        try:
            biodata_text = self._build_biodata_text()
            if not biodata_text:
                return None

            style = self.settings.get("biodata_style", "dramatic")
            font_size = int(self.settings.get("biodata_font_size", 14))
            pulse_enabled = bool(self.settings.get("biodata_pulse_animation", True))

            if style == "minimal":
                # Minimal style: just bold text
                biodata_lbl = tk.Label(
                    parent_container,
                    text=biodata_text,
                    fg="#ff0000",
                    bg="#111",
                    font=("Segoe UI", font_size, "bold"),
                    justify="center"
                )
                return biodata_lbl

            elif style == "simple":
                # Simple style: clean box with border
                outer_frame = tk.Frame(
                    parent_container,
                    bg="#ff0000",
                    highlightthickness=0
                )

                inner_frame = tk.Frame(
                    outer_frame,
                    bg="#222",
                    padx=12,
                    pady=10
                )
                inner_frame.pack(padx=2, pady=2)

                biodata_lbl = tk.Label(
                    inner_frame,
                    text=biodata_text,
                    fg="#ffffff",
                    bg="#222",
                    font=("Segoe UI", font_size, "bold"),
                    justify="center"
                )
                biodata_lbl.pack()

                return outer_frame

            else:  # "dramatic" style (default)
                # Dramatic style: Full attention-grabbing design
                outer_frame = tk.Frame(
                    parent_container,
                    bg="#ff0000",  # Red border
                    highlightthickness=0
                )

                # Inner frame with dark background
                inner_frame = tk.Frame(
                    outer_frame,
                    bg="#1a0000",  # Very dark red background
                    padx=15,
                    pady=12
                )
                inner_frame.pack(padx=3, pady=3)  # Creates the border effect

                # Warning icon at top
                icon_label = tk.Label(
                    inner_frame,
                    text="⚠️ IDENTITY REMINDER ⚠️",
                    fg="#ffff00",  # Yellow for high visibility
                    bg="#1a0000",
                    font=("Segoe UI", 11, "bold"),
                    justify="center"
                )
                icon_label.pack(pady=(0, 8))

                # Main biodata text - large and bold
                biodata_lbl = tk.Label(
                    inner_frame,
                    text=biodata_text,
                    fg="#ffffff",  # White text on dark background
                    bg="#1a0000",
                    font=("Segoe UI", font_size, "bold"),
                    justify="center"
                )
                biodata_lbl.pack()

                # Bottom warning line
                bottom_label = tk.Label(
                    inner_frame,
                    text="═══════════════════════════════",
                    fg="#ff0000",
                    bg="#1a0000",
                    font=("Segoe UI", 8),
                    justify="center"
                )
                bottom_label.pack(pady=(8, 0))

                # Add pulsing animation effect if enabled
                if pulse_enabled:
                    self._animate_biodata_pulse(inner_frame, icon_label)

                return outer_frame

        except Exception as e:
            try:
                get_logger().error(f"Error creating biodata label: {e}")
            except Exception:
                pass
            return None

    def _animate_biodata_pulse(self, frame, icon_label):
        """
        Create a subtle pulsing animation on the biodata display.

        Args:
            frame: The frame to animate
            icon_label: The icon label to pulse
        """
        pulse_state = {
            "brightness": 0,
            "direction": 1,
            "generation": getattr(self, "_camera_generation", 0),
        }

        def pulse():
            timer_id = pulse_state.get("timer_id")
            if timer_id is not None:
                self._biodata_pulse_timer_ids.discard(timer_id)
            try:
                if (
                    (hasattr(self, '_closed') and self._closed)
                    or pulse_state["generation"] != getattr(self, "_camera_generation", 0)
                ):
                    return

                # Pulse the icon between yellow and red
                pulse_state["brightness"] += pulse_state["direction"] * 15

                if pulse_state["brightness"] >= 255:
                    pulse_state["brightness"] = 255
                    pulse_state["direction"] = -1
                elif pulse_state["brightness"] <= 100:
                    pulse_state["brightness"] = 100
                    pulse_state["direction"] = 1

                # Calculate color (from dark yellow to bright yellow)
                brightness = pulse_state["brightness"]
                color = f"#{brightness:02x}{brightness:02x}00"

                try:
                    icon_label.configure(fg=color)
                except Exception:
                    return  # Widget destroyed

                # Schedule next pulse
                schedule_timer = getattr(self, "_schedule_timer", None)
                if callable(schedule_timer):
                    timer_id = schedule_timer(50, pulse)
                else:
                    timer_id = self.after(50, pulse)
                pulse_state["timer_id"] = timer_id
                if timer_id is not None:
                    self._biodata_pulse_timer_ids.add(timer_id)

            except Exception:
                pass  # Silently stop animation if there's an error

        # Start the pulse animation
        pulse()

    def _build_biodata_text(self):
        """
        Build the biodata text string from settings.

        Returns:
            Formatted multi-line string with biodata information, or empty string
        """
        lines = []

        try:
            # Full name with title
            if self.settings.get("biodata_show_full_name", True):
                title = self.settings.get("biodata_title", "").strip()
                first = self.settings.get("biodata_first_name", "").strip()
                last = self.settings.get("biodata_last_name", "").strip()

                name_parts = []
                if title:
                    name_parts.append(title)
                if first:
                    name_parts.append(first)
                if last:
                    name_parts.append(last)

                if name_parts:
                    lines.append(" ".join(name_parts))

            # Age calculation
            birthdate_str = self.settings.get("biodata_birthdate", "2005-01-01")
            age_format = self.settings.get("biodata_age_format", "simple")

            try:
                # Parse birthdate
                parts = birthdate_str.split('-')
                birth_year = int(parts[0])
                birth_month = int(parts[1])
                birth_day = int(parts[2])

                # Get current date
                now = datetime.now()
                current_year = now.year
                current_month = now.month
                current_day = now.day

                # Calculate age components
                years = current_year - birth_year
                months = current_month - birth_month
                days = current_day - birth_day

                # Adjust for negative months/days
                if days < 0:
                    months -= 1
                    # Approximate days in previous month
                    if current_month == 1:
                        days += 31
                    elif current_month in [5, 7, 10, 12]:
                        days += 30
                    elif current_month in [2, 4, 6, 8, 9, 11]:
                        days += 31
                    else:  # March
                        # Check leap year for February
                        if (current_year - 1) % 4 == 0 and ((current_year - 1) % 100 != 0 or (current_year - 1) % 400 == 0):
                            days += 29
                        else:
                            days += 28

                if months < 0:
                    years -= 1
                    months += 12

                # Format based on preference
                if age_format == "simple":
                    lines.append(f"{years} years old")
                elif age_format == "precise":
                    lines.append(f"{years} years, {months} months, {days} days old")
                elif age_format == "decimal":
                    # Calculate decimal age
                    decimal_age = years + (months / 12.0) + (days / 365.25)
                    lines.append(f"{decimal_age:.1f} years old")

            except Exception as e:
                try:
                    get_logger().error(f"Age calculation failed: {e}")
                except Exception:
                    pass

            # Days lived
            if self.settings.get("biodata_show_days_lived", False):
                try:
                    # Calculate total days lived
                    parts = birthdate_str.split('-')
                    birth_year = int(parts[0])
                    birth_month = int(parts[1])
                    birth_day = int(parts[2])

                    birth_date = datetime(birth_year, birth_month, birth_day)
                    now = datetime.now()
                    days_lived = (now - birth_date).days

                    lines.append(f"{days_lived:,} days lived")
                except Exception as e:
                    try:
                        get_logger().error(f"Days lived calculation failed: {e}")
                    except Exception:
                        pass

            # Lineage
            if self.settings.get("biodata_show_lineage", False):
                lineage_text = self.settings.get("biodata_lineage_text", "").strip()
                if lineage_text:
                    lines.append(lineage_text)

            # Role
            if self.settings.get("biodata_show_role", False):
                role_text = self.settings.get("biodata_role_text", "").strip()
                if role_text:
                    lines.append(role_text)

            # Custom text
            custom_text = self.settings.get("biodata_custom_text", "").strip()
            if custom_text:
                lines.append(custom_text)

        except Exception as e:
            try:
                get_logger().error(f"Error building biodata text: {e}")
            except Exception:
                pass

        return "\n".join(lines)

    def _cleanup_camera_feed(self):
        """
        Clean up camera resources.

        Should be called when dialog is closing.
        """
        # Invalidate callbacks before cancelling the Tk handle. A callback
        # already dequeued by Tk must still become a no-op after cleanup.
        self._camera_generation = getattr(self, "_camera_generation", 0) + 1
        if getattr(self, "_camera_capability", None) is not None:
            capability = dict(self._camera_capability)
            capability["stream"] = "inactive"
            capability["state"] = "stopped"
            self._camera_capability = capability

        # Cancel camera update timer
        if self._camera_update_timer:
            if hasattr(self, "_cancel_timer"):
                self._cancel_timer(self._camera_update_timer)
            else:
                try:
                    self.after_cancel(self._camera_update_timer)
                except Exception:
                    pass
            self._camera_update_timer = None

        # Cancel biodata animation callbacks as well as camera frame updates.
        cancel_timer = getattr(self, "_cancel_timer", None)
        for timer_id in list(getattr(self, "_biodata_pulse_timer_ids", ())):
            if callable(cancel_timer):
                cancel_timer(timer_id)
            else:
                try:
                    self.after_cancel(timer_id)
                except Exception:
                    pass
        if hasattr(self, "_biodata_pulse_timer_ids"):
            self._biodata_pulse_timer_ids.clear()

        # Release camera
        if self._camera_capture is not None:
            try:
                self._camera_capture.release()
            except Exception as e:
                try:
                    get_logger().error(f"Error releasing camera: {e}")
                except Exception:
                    pass
            self._camera_capture = None

        # Clear references
        self._camera_label = None
        self._camera_feed_container = None
        self._camera_static_image = None

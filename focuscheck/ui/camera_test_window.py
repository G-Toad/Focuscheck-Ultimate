"""
Camera test preview window for testing camera settings before applying.
"""

import tkinter as tk
from tkinter import ttk
import time
from ..utils.timers import TimerRegistry

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    ImageTk = None


class CameraTestWindow(tk.Toplevel):
    """
    Camera preview utility opened from settings.
    """

    def __init__(self, parent, camera_settings):
        """
        Initialize camera test window.

        Args:
            parent: Parent settings window
            camera_settings: Dictionary of camera settings to test
        """
        super().__init__(parent)

        self.camera_settings = camera_settings
        self.parent_window = parent
        self._closed = False
        self._camera_capture = None
        self._camera_update_timer = None
        self._timers = TimerRegistry(self)
        self._camera_generation = 0
        self._camera_label = None
        self._camera_last_face_rect = None
        self._camera_face_cascade = None

        # Import camera mixin methods dynamically
        from .dialogs.prompt_dialog_mixins.camera_feed import CameraFeedMixin

        # Temporarily inherit methods from CameraFeedMixin
        # Copy necessary methods
        self._process_camera_frame = CameraFeedMixin._process_camera_frame.__get__(self, CameraTestWindow)
        self._resize_maintain_aspect = CameraFeedMixin._resize_maintain_aspect.__get__(self, CameraTestWindow)
        self._resize_fixed_size = CameraFeedMixin._resize_fixed_size.__get__(self, CameraTestWindow)
        self._pad_frame_to_display_size = CameraFeedMixin._pad_frame_to_display_size.__get__(self, CameraTestWindow)
        self._apply_camera_effects = CameraFeedMixin._apply_camera_effects.__get__(self, CameraTestWindow)
        self._apply_adaptive_brightness = CameraFeedMixin._apply_adaptive_brightness.__get__(self, CameraTestWindow)
        self._draw_face_detection_overlay = CameraFeedMixin._draw_face_detection_overlay.__get__(self, CameraTestWindow)
        self._draw_dashed_rectangle = CameraFeedMixin._draw_dashed_rectangle.__get__(self, CameraTestWindow)

        # Setup window
        self.title("Camera Test Preview")
        self.configure(bg="#111")
        self.resizable(False, False)

        # Make it stay on top
        self.attributes("-topmost", True)

        # Bind close event
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Build UI
        self._build_ui()

        # Start camera
        self._init_camera()

    def _build_ui(self):
        """Build the test window UI."""
        container = tk.Frame(self, bg="#111")
        container.pack(padx=20, pady=20)

        # Title
        title = tk.Label(container, text="Camera Test Preview", fg="#eaeaea", bg="#111",
                        font=("Segoe UI", 14, "bold"))
        title.pack(pady=(0, 10))

        # Info label
        info = tk.Label(container, text="Adjust settings in main window and see changes here in real-time",
                       fg="#aaa", bg="#111", font=("Segoe UI", 9))
        info.pack(pady=(0, 10))

        # Camera display
        self._camera_display_width = self.camera_settings.get("camera_face_max_width", 400)
        self._camera_display_height = self.camera_settings.get("camera_face_max_height", 300)
        self._camera_sizing_mode = self.camera_settings.get("camera_sizing_mode", "face_tracking")

        camera_frame = tk.Frame(container, bg="#000", highlightthickness=2, highlightbackground="#444",
                               width=self._camera_display_width + 4,
                               height=self._camera_display_height + 4)
        camera_frame.pack()
        camera_frame.pack_propagate(False)  # Prevent frame from shrinking

        self._camera_label = tk.Label(camera_frame, bg="#000", fg="#fff",
                                      text="Initializing camera...",
                                      font=("Segoe UI", 10),
                                      compound="center",  # Allow text even with image
                                      anchor="center",
                                      justify="center")
        self._camera_label.pack(fill="both", expand=True, padx=2, pady=2)

        # Close button
        close_btn = ttk.Button(container, text="Close Preview", command=self._on_close)
        close_btn.pack(pady=(10, 0))

        # Note
        note = tk.Label(container, text="Close this preview manually before returning to Settings.",
                       fg="#888", bg="#111", font=("Segoe UI", 8, "italic"))
        note.pack(pady=(5, 0))

    def _init_camera(self):
        """Initialize camera for preview."""
        device_index = self.camera_settings.get("camera_device_index", 0)

        try:
            self._camera_capture = cv2.VideoCapture(device_index)
            if not self._camera_capture.isOpened():
                self._show_error("Could not open camera!")
                return

            # Set high resolution for better face detection
            self._camera_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self._camera_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

            # Load face detection cascade
            detection_method = self.camera_settings.get("camera_face_detection_method", "haar")
            if detection_method == "haar":
                try:
                    self._camera_face_cascade = cv2.CascadeClassifier(
                        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                    )
                except Exception:
                    pass

            # Start update loop
            self._update_camera_feed(self._camera_generation)

        except Exception as e:
            self._show_error(f"Camera initialization failed: {e}")

    def _update_camera_feed(self, generation=None):
        """Update camera feed display."""
        current_generation = getattr(self, "_camera_generation", 0)
        if generation is None:
            generation = current_generation
        if generation != current_generation or self._closed or self._camera_capture is None:
            if self._camera_capture is None:
                self._camera_label.configure(text="Camera not initialized", fg="#f00")
            return

        try:
            ret, frame = self._camera_capture.read()
            if not ret or frame is None:
                self._camera_label.configure(text="No camera frame available", fg="#f00")
                self._schedule_camera_update(33, generation)
                return

            # Process frame using camera feed mixin logic
            # Use settings from camera_settings
            self.settings = self.camera_settings
            processed_frame = self._process_camera_frame(frame)

            if processed_frame is None:
                self._schedule_camera_update(33, generation)
                return

            # Pad to display size
            display_frame = self._pad_frame_to_display_size(processed_frame)

            # Apply visual effects and enhancements
            display_frame = self._apply_camera_effects(display_frame)

            # Apply horizontal flip if enabled
            if self.camera_settings.get("camera_flip_horizontal", True):
                display_frame = cv2.flip(display_frame, 1)

            # Convert to RGB
            rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_frame)
            photo = ImageTk.PhotoImage(image=pil_image)

            # Update label
            self._camera_label.configure(image=photo, text="")
            self._camera_label.image = photo

            # Schedule next update
            fps = self.camera_settings.get("camera_fps", 30)
            delay_ms = int(1000 / fps)
            self._schedule_camera_update(delay_ms, generation)

        except Exception as e:
            self._camera_label.configure(text=f"Error: {e}")
            self._schedule_camera_update(100, generation)

    def _schedule_camera_update(self, delay_ms, generation):
        if self._closed:
            return
        self._timers.schedule(
            "camera-feed",
            delay_ms,
            lambda: self._update_camera_feed(generation),
        )
        self._camera_update_timer = self._timers.callback_id("camera-feed")

    def _show_error(self, message):
        """Show error message in camera display."""
        self._camera_label.configure(text=message, fg="#f00")

    def _on_close(self):
        """Handle window close."""
        self._closed = True
        self._camera_generation = getattr(self, "_camera_generation", 0) + 1

        timers = getattr(self, "_timers", None)
        if timers is not None:
            timers.close()
        elif self._camera_update_timer is not None:
            try:
                self.after_cancel(self._camera_update_timer)
            except Exception:
                pass
        self._camera_update_timer = None

        # Release camera
        if self._camera_capture is not None:
            try:
                self._camera_capture.release()
            except Exception:
                pass

        # Destroy window
        self.destroy()

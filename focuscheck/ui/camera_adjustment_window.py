"""
Live camera adjustment window with manual controls and auto-adapt.

Shows side-by-side original vs enhanced view with real-time adjustments.
"""

import tkinter as tk
from tkinter import ttk
try:
    import cv2
except ImportError:
    cv2 = None
from .camera.adjustment_helpers import (
    resize_for_display,
    apply_manual_adjustments,
    frame_to_photo,
)
from ..utils.timers import TimerRegistry


class CameraAdjustmentWindow(tk.Toplevel):
    """
    Live camera feed window with manual adjustment controls.

    Features:
    - Side-by-side original vs enhanced view
    - Manual sliders: brightness, contrast, saturation, sharpness, tint
    - Auto-adapt toggle: intelligently scales user settings based on environment
    - Save settings permanently
    """

    def __init__(self, parent, camera_index=0, current_settings=None):
        super().__init__(parent)

        self.camera_index = camera_index
        self.settings = current_settings or {}
        self._closed = False
        self._camera_capture = None
        self._update_timer = None
        self._save_feedback_timer = None
        self._save_feedback_label = None
        self._camera_generation = 0
        self._timers = TimerRegistry(self)

        # Manual adjustment values (0.0 - 1.0 range for all)
        self.brightness_var = tk.DoubleVar(value=self.settings.get("camera_manual_brightness", 0.5))
        self.contrast_var = tk.DoubleVar(value=self.settings.get("camera_manual_contrast", 0.5))
        self.saturation_var = tk.DoubleVar(value=self.settings.get("camera_manual_saturation", 0.5))
        self.sharpness_var = tk.DoubleVar(value=self.settings.get("camera_manual_sharpness", 0.5))
        self.tint_var = tk.DoubleVar(value=self.settings.get("camera_manual_tint", 0.5))
        self.gamma_var = tk.DoubleVar(value=self.settings.get("camera_manual_gamma", 0.5))

        # Auto-adapt toggle
        self.auto_adapt_var = tk.BooleanVar(value=self.settings.get("camera_auto_adapt", False))

        self.title("Camera Adjustment - Live Preview")
        self.configure(bg="#111")
        self.resizable(True, True)
        # Give plenty of space by default; still resizable
        self.geometry("1100x750")
        self.minsize(950, 650)
        self.attributes("-topmost", True)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self._init_camera()

    def _build_ui(self):
        """Build the UI with side-by-side preview and controls."""
        main_container = tk.Frame(self, bg="#111")
        main_container.pack(fill="both", expand=True, padx=15, pady=15)

        # Title
        title = tk.Label(main_container, text="Live Camera Adjustment",
                        fg="#eaeaea", bg="#111", font=("Segoe UI", 14, "bold"))
        title.pack(pady=(0, 10))

        # Video container - side by side
        video_container = tk.Frame(main_container, bg="#111")
        video_container.pack(fill="both", expand=True, pady=(0, 15))

        # Left side - Original
        left_frame = tk.Frame(video_container, bg="#222", highlightthickness=2,
                             highlightbackground="#444")
        left_frame.pack(side="left", padx=(0, 10), fill="both", expand=True)

        left_label = tk.Label(left_frame, text="ORIGINAL", fg="#888", bg="#222",
                             font=("Segoe UI", 10, "bold"))
        left_label.pack(pady=(5, 5))

        self.original_label = tk.Label(left_frame, bg="#000")
        self.original_label.pack(padx=5, pady=(0, 5), fill="both", expand=True)

        # Right side - Enhanced
        right_frame = tk.Frame(video_container, bg="#222", highlightthickness=2,
                              highlightbackground="#444")
        right_frame.pack(side="left", fill="both", expand=True)

        right_label = tk.Label(right_frame, text="ENHANCED", fg="#0f0", bg="#222",
                              font=("Segoe UI", 10, "bold"))
        right_label.pack(pady=(5, 5))

        self.enhanced_label = tk.Label(right_frame, bg="#000")
        self.enhanced_label.pack(padx=5, pady=(0, 5), fill="both", expand=True)

        # Controls container
        controls_container = tk.Frame(main_container, bg="#1a1a1a",
                                     highlightthickness=2, highlightbackground="#333")
        controls_container.pack(fill="both", expand=True, pady=(0, 10))

        # Scrollable wrapper so smaller screens don't hide controls
        controls_canvas = tk.Canvas(controls_container, bg="#1a1a1a", highlightthickness=0)
        controls_scroll = ttk.Scrollbar(controls_container, orient="vertical",
                                       command=controls_canvas.yview)
        controls_canvas.configure(yscrollcommand=controls_scroll.set)
        controls_scroll.pack(side="right", fill="y")
        controls_canvas.pack(side="left", fill="both", expand=True)

        controls_inner = tk.Frame(controls_canvas, bg="#1a1a1a")
        controls_canvas.create_window((0, 0), window=controls_inner, anchor="nw")

        def _on_frame_config(event):
            controls_canvas.configure(scrollregion=controls_canvas.bbox("all"))

        def _on_mousewheel(event):
            controls_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        controls_inner.bind("<Configure>", _on_frame_config)
        controls_canvas.bind("<Enter>", lambda e: controls_canvas.bind_all("<MouseWheel>", _on_mousewheel))
        controls_canvas.bind("<Leave>", lambda e: controls_canvas.unbind_all("<MouseWheel>"))

        # Auto-adapt toggle at top
        auto_adapt_frame = tk.Frame(controls_inner, bg="#1a1a1a")
        auto_adapt_frame.pack(fill="x", pady=(0, 10))

        auto_adapt_check = tk.Checkbutton(
            auto_adapt_frame,
            text="Auto-adapt: Intelligently scale my settings based on lighting conditions",
            variable=self.auto_adapt_var,
            fg="#00ff00",
            bg="#1a1a1a",
            selectcolor="#000",
            font=("Segoe UI", 10, "bold"),
            activebackground="#1a1a1a",
            activeforeground="#00ff00"
        )
        auto_adapt_check.pack(side="left")

        ttk.Label(auto_adapt_frame, text="(Analyzes brightness and adapts your manual settings)",
                 foreground="gray", background="#1a1a1a", font=("Segoe UI", 8)).pack(side="left", padx=(10, 0))

        # Sliders - two columns
        sliders_frame = tk.Frame(controls_inner, bg="#1a1a1a")
        sliders_frame.pack(fill="x")

        left_sliders = tk.Frame(sliders_frame, bg="#1a1a1a")
        left_sliders.pack(side="left", fill="both", expand=True, padx=(0, 10))

        right_sliders = tk.Frame(sliders_frame, bg="#1a1a1a")
        right_sliders.pack(side="left", fill="both", expand=True)

        # Left column sliders
        self._create_slider(left_sliders, "Brightness", self.brightness_var,
                           "Darker ← → Brighter")
        self._create_slider(left_sliders, "Contrast", self.contrast_var,
                           "Flat ← → Punchy")
        self._create_slider(left_sliders, "Saturation", self.saturation_var,
                           "Grayscale ← → Vibrant")

        # Right column sliders
        self._create_slider(right_sliders, "Sharpness", self.sharpness_var,
                           "Soft ← → Sharp")
        self._create_slider(right_sliders, "Gamma", self.gamma_var,
                           "Lift Shadows ← → Crush Blacks")
        self._create_slider(right_sliders, "Tint", self.tint_var,
                           "Cool (Blue) ← → Warm (Orange)")

        # Buttons at bottom
        button_frame = tk.Frame(main_container, bg="#111")
        button_frame.pack(fill="x")

        reset_btn = tk.Button(button_frame, text="Reset to Defaults",
                             command=self._reset_defaults,
                             bg="#444", fg="#fff", font=("Segoe UI", 10),
                             relief="flat", padx=15, pady=8)
        reset_btn.pack(side="left", padx=(0, 10))

        save_btn = tk.Button(button_frame, text="💾 Save Settings",
                            command=self._save_settings,
                            bg="#0066ff", fg="#fff", font=("Segoe UI", 10, "bold"),
                            relief="flat", padx=20, pady=8)
        save_btn.pack(side="left", padx=(0, 10))

        close_btn = tk.Button(button_frame, text="Close",
                             command=self._on_close,
                             bg="#666", fg="#fff", font=("Segoe UI", 10),
                             relief="flat", padx=15, pady=8)
        close_btn.pack(side="right")

    def _create_slider(self, parent, label_text, variable, hint_text):
        """Create a labeled slider with hint text."""
        frame = tk.Frame(parent, bg="#1a1a1a")
        frame.pack(fill="x", pady=8)

        label = tk.Label(frame, text=label_text, fg="#fff", bg="#1a1a1a",
                        font=("Segoe UI", 9, "bold"))
        label.pack(anchor="w")

        slider = tk.Scale(frame, from_=0.0, to=1.0, resolution=0.01,
                         orient="horizontal", variable=variable,
                         bg="#2a2a2a", fg="#fff", troughcolor="#000",
                         highlightthickness=0, sliderlength=30,
                         length=300, width=20,
                         font=("Segoe UI", 8))
        slider.pack(fill="x", pady=(2, 0), ipady=5)

        hint = tk.Label(frame, text=hint_text, fg="#666", bg="#1a1a1a",
                       font=("Segoe UI", 7, "italic"))
        hint.pack(anchor="w")

    def _init_camera(self):
        """Initialize camera capture."""
        if cv2 is None:
            self._show_error("Camera adjustment requires opencv-python")
            return
        try:
            self._camera_capture = cv2.VideoCapture(self.camera_index)

            if not self._camera_capture.isOpened():
                self._show_error("Could not open camera")
                return

            # Set resolution
            self._camera_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self._camera_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

            # Start update loop
            self._update_feed(self._camera_generation)

        except Exception as e:
            self._show_error(f"Camera error: {e}")

    def _update_feed(self, generation=None):
        """Update both original and enhanced camera feeds."""
        current_generation = getattr(self, "_camera_generation", 0)
        if generation is None:
            generation = current_generation
        if generation != current_generation or self._closed or self._camera_capture is None:
            return

        try:
            ret, frame = self._camera_capture.read()

            if not ret or frame is None:
                self._schedule_update(33, generation)
                return

            # Resize for display (maintain aspect ratio)
            display_frame = resize_for_display(frame)

            # Show original
            self._display_frame(display_frame, self.original_label)

            # Apply enhancements
            params = {
                "brightness": self.brightness_var.get(),
                "contrast": self.contrast_var.get(),
                "saturation": self.saturation_var.get(),
                "sharpness": self.sharpness_var.get(),
                "gamma": self.gamma_var.get(),
                "tint": self.tint_var.get(),
                "auto_adapt": self.auto_adapt_var.get(),
            }
            enhanced = apply_manual_adjustments(display_frame.copy(), params)

            # Show enhanced
            self._display_frame(enhanced, self.enhanced_label)

            # Schedule next update
            self._schedule_update(33, generation)

        except Exception as e:
            print(f"Update error: {e}")
            self._schedule_update(100, generation)

    def _schedule_update(self, delay_ms, generation):
        if self._closed:
            return
        self._timers.schedule(
            "camera-feed",
            delay_ms,
            lambda: self._update_feed(generation),
        )
        self._update_timer = self._timers.callback_id("camera-feed")

    def _display_frame(self, frame, label):
        """Display frame in the given label."""
        try:
            photo = frame_to_photo(frame)
            label.configure(image=photo)
            label.image = photo
        except Exception as e:
            print(f"Display error: {e}")

    def _reset_defaults(self):
        """Reset all sliders to default (0.5 = neutral)."""
        self.brightness_var.set(0.5)
        self.contrast_var.set(0.5)
        self.saturation_var.set(0.5)
        self.sharpness_var.set(0.5)
        self.gamma_var.set(0.5)
        self.tint_var.set(0.5)
        self.auto_adapt_var.set(False)

    def _save_settings(self):
        """Save current settings."""
        try:
            # Return settings to parent
            settings = {
                "camera_manual_brightness": self.brightness_var.get(),
                "camera_manual_contrast": self.contrast_var.get(),
                "camera_manual_saturation": self.saturation_var.get(),
                "camera_manual_sharpness": self.sharpness_var.get(),
                "camera_manual_gamma": self.gamma_var.get(),
                "camera_manual_tint": self.tint_var.get(),
                "camera_auto_adapt": self.auto_adapt_var.get(),
            }

            # Call parent's save method if it exists
            if hasattr(self.master, '_save_camera_adjustment_settings'):
                self.master._save_camera_adjustment_settings(settings)

            # Show confirmation
            self._timers.cancel("save-feedback")
            self._save_feedback_timer = None
            if self._save_feedback_label is not None:
                try:
                    self._save_feedback_label.destroy()
                except Exception:
                    pass
            self._save_feedback_label = tk.Label(self, text="✓ Settings saved!",
                                                 fg="#0f0", bg="#111", font=("Segoe UI", 10, "bold"))
            self._save_feedback_label.place(relx=0.5, rely=0.5, anchor="center")
            self._timers.schedule("save-feedback", 1500, self._clear_save_feedback)
            self._save_feedback_timer = self._timers.callback_id("save-feedback")

        except Exception as e:
            print(f"Save error: {e}")

    def _clear_save_feedback(self):
        label = self._save_feedback_label
        self._save_feedback_label = None
        self._save_feedback_timer = None
        if label is not None:
            try:
                label.destroy()
            except Exception:
                pass

    def _show_error(self, message):
        """Show error message."""
        error_label = tk.Label(self.original_label, text=message,
                              fg="#f00", bg="#000", font=("Segoe UI", 10))
        error_label.pack(expand=True)

    def _on_close(self):
        """Clean up and close window."""
        self._closed = True
        self._camera_generation = getattr(self, "_camera_generation", 0) + 1

        feedback_timer = getattr(self, "_save_feedback_timer", None)
        timers = getattr(self, "_timers", None)
        if timers is not None:
            timers.close()
        elif feedback_timer is not None:
            try:
                self.after_cancel(feedback_timer)
            except Exception:
                pass
        self._save_feedback_timer = None
        self._save_feedback_label = None

        self._update_timer = None

        if self._camera_capture is not None:
            try:
                self._camera_capture.release()
            except Exception:
                pass

        self.destroy()

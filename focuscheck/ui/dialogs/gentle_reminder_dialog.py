"""
Gentle Reminder Dialog - Non-intrusive reminder with camera + biodata.

A draggable reminder that shows camera feed and biodata, but never forces
a response. After a customizable time, it gradually drifts back to center
to gently remind the user without being annoying.

Perfect for users who pause to do something else and forget to come back.
"""

import tkinter as tk
import time

try:
    from ...utils import get_logger
except ImportError:
    def get_logger():
        import logging
        return logging.getLogger(__name__)

# Import camera feed mixin
try:
    from .prompt_dialog_mixins.camera_feed import CameraFeedMixin
except ImportError:
    CameraFeedMixin = object  # Fallback if not available


class GentleReminderDialog(tk.Toplevel, CameraFeedMixin):
    """
    Gentle, non-intrusive reminder with camera feed and biodata.

    Features:
    - Shows camera feed (if enabled)
    - Shows biodata identity information
    - Fully draggable - stays where you put it
    - After X minutes (customizable), gradually drifts back to center
    - NO punishment for ignoring
    - No forced response required
    - Dismissable at any time

    The idea: Never make the user want to exit the app. Just a gentle nudge.
    """

    def __init__(self, master, settings, on_dismiss=None):
        """
        Initialize the gentle reminder dialog.

        Args:
            master: Parent tkinter widget
            settings: Settings dictionary
            on_dismiss: Optional callback when dialog is dismissed
        """
        tk.Toplevel.__init__(self, master)
        self.settings = settings
        self.on_dismiss = on_dismiss
        self._closed = False

        # Initialize camera feed state through the mixin contract.
        if CameraFeedMixin != object:
            self._init_camera_feed()

        # Drag state
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._was_dragged = False
        self._last_drag_time = time.time()

        # Drift-back state
        self._active_timers = set()
        self._drift_timer = None

        # Window setup
        self.title("Gentle Reminder")
        self.configure(bg="#111")
        self.resizable(False, False)

        # Always on top but not modal
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self._on_dismiss)

        # Build UI
        self._build_ui()

        # Center initially and save center position
        self.update_idletasks()
        self._center_on_screen()
        self._save_center_position()

        # Setup drag handlers
        self._setup_drag_handlers()

        # Start drift-back timer
        self._start_drift_timer()

    def _build_ui(self):
        """Build the reminder UI with camera and biodata."""
        main_container = tk.Frame(self, bg="#111", padx=10, pady=10)
        main_container.pack(fill="both", expand=True)

        # Title bar (draggable)
        title_bar = tk.Frame(main_container, bg="#333", cursor="fleur")
        title_bar.pack(fill="x", pady=(0, 10))

        title_label = tk.Label(
            title_bar,
            text="⏰ Gentle Reminder",
            fg="#ffcc00",
            bg="#333",
            font=("Segoe UI", 11, "bold"),
            cursor="fleur",
            padx=10,
            pady=5
        )
        title_label.pack(side="left")

        dismiss_btn = tk.Button(
            title_bar,
            text="✕",
            fg="#fff",
            bg="#333",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self._on_dismiss,
            padx=8,
            pady=2
        )
        dismiss_btn.pack(side="right")

        # Camera feed (if enabled)
        if self.settings.get("camera_feed_enabled", False):
            try:
                camera_widget = self._create_camera_feed_widget(main_container)
                if camera_widget:
                    camera_widget.pack(fill="x", pady=(0, 10))
            except Exception as e:
                try:
                    get_logger().error(f"Failed to create camera widget: {e}")
                except Exception:
                    pass

        # Biodata (if enabled)
        if self.settings.get("biodata_enabled", False):
            try:
                biodata_label = self._create_biodata_label(main_container)
                if biodata_label:
                    biodata_label.pack(fill="x", pady=(0, 10))
            except Exception as e:
                try:
                    get_logger().error(f"Failed to create biodata: {e}")
                except Exception:
                    pass

        # Message
        message_frame = tk.Frame(main_container, bg="#222", padx=15, pady=12)
        message_frame.pack(fill="x", pady=(0, 10))

        message = tk.Label(
            message_frame,
            text="Just a gentle reminder - you can drag me away,\nbut I'll slowly drift back to remind you. 😊",
            fg="#ddd",
            bg="#222",
            font=("Segoe UI", 9),
            justify="center"
        )
        message.pack()

        # Dismiss button
        dismiss_large = tk.Button(
            main_container,
            text="Got it, thanks!",
            font=("Segoe UI", 10, "bold"),
            bg="#28a745",
            fg="white",
            activebackground="#218838",
            activeforeground="white",
            relief="flat",
            bd=0,
            padx=25,
            pady=8,
            cursor="hand2",
            command=self._on_dismiss
        )
        dismiss_large.pack()

        # Info label about drift-back
        drift_time = self.settings.get("gentle_reminder_drift_delay", 5)
        info = tk.Label(
            main_container,
            text=f"(Will drift back to center after {drift_time} min)",
            fg="#666",
            bg="#111",
            font=("Segoe UI", 7, "italic")
        )
        info.pack(pady=(5, 0))

    def _setup_drag_handlers(self):
        """Setup drag handlers for making window draggable."""
        def start_drag(event):
            self._drag_start_x = event.x
            self._drag_start_y = event.y
            self._was_dragged = False

        def on_drag(event):
            # Calculate new position
            x = self.winfo_x() + (event.x - self._drag_start_x)
            y = self.winfo_y() + (event.y - self._drag_start_y)

            # Move window
            self.geometry(f"+{x}+{y}")
            self._was_dragged = True
            self._last_drag_time = time.time()

        def stop_drag(event):
            if self._was_dragged:
                # User dragged the window - reset drift timer
                self._restart_drift_timer()

        # Bind to window and all widgets that should be draggable
        for widget in self.winfo_children():
            if isinstance(widget, tk.Frame):
                self._bind_drag_recursive(widget, start_drag, on_drag, stop_drag)

        self.bind("<Button-1>", start_drag)
        self.bind("<B1-Motion>", on_drag)
        self.bind("<ButtonRelease-1>", stop_drag)

    def _bind_drag_recursive(self, widget, start_drag, on_drag, stop_drag):
        """Recursively bind drag handlers to all child widgets."""
        try:
            # Skip buttons and interactive elements
            if isinstance(widget, tk.Button):
                return

            widget.bind("<Button-1>", start_drag)
            widget.bind("<B1-Motion>", on_drag)
            widget.bind("<ButtonRelease-1>", stop_drag)

            for child in widget.winfo_children():
                self._bind_drag_recursive(child, start_drag, on_drag, stop_drag)
        except Exception:
            pass

    def _center_on_screen(self):
        """Center the dialog on screen."""
        try:
            width = self.winfo_width()
            height = self.winfo_height()

            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()

            x = (screen_width - width) // 2
            y = (screen_height - height) // 2

            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def _save_center_position(self):
        """Save the center position to drift back to."""
        try:
            self._original_center_x = self.winfo_x()
            self._original_center_y = self.winfo_y()
        except Exception:
            pass

    def _schedule_timer(self, delay_ms, callback):
        if self._closed:
            return None
        timer_ref = {}

        def run_callback():
            timer_id = timer_ref.get("id")
            if timer_id is not None:
                self._active_timers.discard(timer_id)
                if self._drift_timer == timer_id:
                    self._drift_timer = None
            if not self._closed:
                callback()

        timer_id = self.after(delay_ms, run_callback)
        timer_ref["id"] = timer_id
        self._active_timers.add(timer_id)
        return timer_id

    def _cleanup_timers(self):
        for timer_id in list(self._active_timers):
            try:
                self.after_cancel(timer_id)
            except Exception:
                pass
        self._active_timers.clear()
        self._drift_timer = None

    def _start_drift_timer(self):
        """Start the timer for drifting back to center."""
        if not self.settings.get("gentle_reminder_drift_enabled", True):
            return

        drift_delay_minutes = self.settings.get("gentle_reminder_drift_delay", 5)
        drift_delay_ms = drift_delay_minutes * 60 * 1000

        # Schedule first drift check
        self._drift_timer = self._schedule_timer(drift_delay_ms, self._start_drift_back)

    def _restart_drift_timer(self):
        """Restart the drift timer (user just dragged the window)."""
        if self._drift_timer:
            self.after_cancel(self._drift_timer)
            self._drift_timer = None

        self._start_drift_timer()

    def _start_drift_back(self):
        """Start gradually drifting back to center."""
        if self._closed:
            return

        # Don't drift if disabled
        if not self.settings.get("gentle_reminder_drift_enabled", True):
            return

        # Start the drift animation
        self._animate_drift_back()

    def _animate_drift_back(self):
        """Animate the gradual drift back to center."""
        if self._closed:
            return

        if self._original_center_x is None or self._original_center_y is None:
            return

        try:
            # Get current position
            current_x = self.winfo_x()
            current_y = self.winfo_y()

            # Calculate difference
            diff_x = self._original_center_x - current_x
            diff_y = self._original_center_y - current_y

            # Check if we're close enough to center
            threshold = 5  # pixels
            if abs(diff_x) < threshold and abs(diff_y) < threshold:
                # We're at center, stop drifting
                return

            # Calculate drift speed (pixels per frame)
            drift_speed = self.settings.get("gentle_reminder_drift_speed", 1.0)  # 1.0 = 1 pixel per frame

            # Move towards center by drift_speed pixels
            move_x = min(abs(diff_x), drift_speed) * (1 if diff_x > 0 else -1)
            move_y = min(abs(diff_y), drift_speed) * (1 if diff_y > 0 else -1)

            new_x = current_x + int(move_x)
            new_y = current_y + int(move_y)

            self.geometry(f"+{new_x}+{new_y}")

            # Schedule next frame (30 FPS)
            self._schedule_timer(33, self._animate_drift_back)

        except Exception as e:
            try:
                get_logger().error(f"Drift animation error: {e}")
            except Exception:
                pass

    def _on_dismiss(self):
        """Handle dismiss - close the dialog."""
        if self._closed:
            return

        self._closed = True

        try:
            get_logger().info("Gentle reminder dismissed by user")
        except Exception:
            pass

        # Cancel drift timer
        self._cleanup_timers()

        # Clean up camera
        if hasattr(self, '_cleanup_camera_feed'):
            try:
                self._cleanup_camera_feed()
            except Exception:
                pass

        # Call callback
        if callable(self.on_dismiss):
            try:
                self.on_dismiss()
            except Exception:
                pass

        # Destroy window
        try:
            self.destroy()
        except Exception:
            pass


__all__ = ['GentleReminderDialog']

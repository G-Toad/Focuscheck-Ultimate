"""
Main PromptDialog class.

This module contains the PromptDialog class which inherits from all
the functional mixins to provide complete check-in dialog functionality.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import time
import sys
import random

from .prompt_dialog_mixins.button_handling import ButtonHandlingMixin
from .prompt_dialog_mixins.window_placement import WindowPlacementMixin
from .prompt_dialog_mixins.time_display import TimeDisplayMixin
from .prompt_dialog_mixins.anti_habit import AntiHabitMixin
from .prompt_dialog_mixins.intensification import IntensificationMixin
from .prompt_dialog_mixins.task_management import TaskManagementMixin
from .prompt_dialog_mixins.windows_integration import WindowsIntegrationMixin
from .prompt_dialog_mixins.camera_feed import CameraFeedMixin

try:
    from ...utils import get_logger
except ImportError:
    def get_logger():
        import logging
        return logging.getLogger(__name__)

try:
    from ...database import append_log
except ImportError:
    def append_log(**kwargs):
        pass


class PromptDialog(
    ButtonHandlingMixin,
    WindowPlacementMixin,
    TimeDisplayMixin,
    AntiHabitMixin,
    IntensificationMixin,
    TaskManagementMixin,
    WindowsIntegrationMixin,
    CameraFeedMixin,
    tk.Toplevel
):
    """
    Main check-in dialog for FocusCheck.

    Prompts user to categorize their current activity and applies
    progressive escalation if response is delayed.

    Inherits from multiple mixins to organize functionality:
    - ButtonHandlingMixin: Button configuration and event handling
    - WindowPlacementMixin: Multi-monitor window positioning
    - TimeDisplayMixin: Time information display
    - AntiHabitMixin: Anti-habit press-and-hold behavior
    - IntensificationMixin: Progressive escalation and overdrive
    - TaskManagementMixin: Task panel and analytics
    - WindowsIntegrationMixin: Windows-specific helpers
    - CameraFeedMixin: Camera feed and photo capture
    """

    def __init__(self, master, settings, on_submit, slot_start_dt, taskdb=None, app_ref=None):
        """
        Initialize the PromptDialog.

        Args:
            master: Parent tkinter widget
            settings: Settings dictionary
            on_submit: Callback function for submission
            slot_start_dt: Datetime when this check-in slot started
            taskdb: Optional task database instance
            app_ref: Optional reference to main app instance
        """
        super().__init__(master)
        self.settings = settings
        self.on_submit = on_submit
        self.slot_start_dt = slot_start_dt
        self.taskdb = taskdb
        self.app_ref = app_ref
        self.start_monotonic = time.monotonic()

        # Calculate UI scale factor
        scale_percent = self.settings.get("ui_scale_percent", 100)
        self._ui_scale = scale_percent / 100.0
        self.intensity_level = 0
        self._pulse_dir = 1
        self._pulse_val = 0
        self._shaking = False
        self._overdrive = False
        self._overdrive_stage4 = False
        self._closed = False
        self._hold_start = None
        # Timer registry for cleanup
        self._active_timers = set()
        self._time_lbl = None
        self._info_lbl = None
        self._task_panel = None
        self._task_change_form = None
        self._analytics_lbl = None
        self._task_timer_id = None
        self._action_buttons = []
        self._task_decision_required = False
        self._task_decision_task_id = None
        self._task_decision_can_fail = False
        self._focus_prompt_open = False

        # Button phrase tracking for sequential mode
        self._study_phrase_index = 0
        self._waste_phrase_index = 0

        self.title("Check-in")
        self.configure(bg="#111")
        self.resizable(False, False)
        if self.settings["always_on_top"]:
            self.attributes("-topmost", True)

        # Windows-specific: remove minimize button and start taskbar flashing
        try:
            self._disable_minimize_button()
            self._flash_taskbar_begin()
        except Exception:
            pass

        # Prevent minimize attempts by restoring immediately
        self.bind('<Unmap>', self._prevent_minimize)

        # Create main container
        container = tk.Frame(self, bg="#111")
        container.pack(padx=self._scale(14), pady=self._scale(14))

        # Build UI based on layout mode
        layout_mode = self.settings.get("popup_layout_mode", "vertical")
        if layout_mode == "horizontal":
            self._build_horizontal_layout(container)
        elif layout_mode == "compact":
            self._build_compact_layout(container)
        else:
            self._build_vertical_layout(container)

        # Common post-layout setup
        self._place_buttons_random()

        self.update_idletasks()
        if self.settings["center_on_show"]:
            # Center on the user's active monitor (cursor monitor on Windows)
            self._center_on_active_monitor()

        # Force window to be visible and grab focus immediately
        self.update()

        # Aggressively force window to front (Windows-specific)
        self._force_window_to_front()

        # Set initial button focus multiple times to ensure it works
        self._schedule_timer(100, self._sync_initial_button_focus)
        self._schedule_timer(200, self._sync_initial_button_focus)
        self._schedule_timer(300, self._sync_initial_button_focus)

        # Use timer registry for cleanup
        self._schedule_timer(self.settings["intensify_after_seconds"] * 1000, self._begin_intensify)
        self._schedule_timer(self.settings["overdrive_after_seconds"] * 1000, self._begin_overdrive)

        self.protocol("WM_DELETE_WINDOW", self._ignore_close)

        # Optionally track cursor monitor and recenter while open
        try:
            if bool(self.settings.get("follow_cursor_monitor", True)):
                self._schedule_timer(400, self._follow_cursor_center_loop)
        except Exception:
            pass

        # If a task is required and none is set, guide user to create one
        try:
            if bool(self.settings.get("require_active_task", False)) and self.taskdb:
                active = None
                try:
                    active = self.taskdb.get_active()
                except Exception:
                    active = None
                if not active:
                    try:
                        self._info_lbl.config(text="Set a task to proceed.")
                    except Exception:
                        pass
                    try:
                        self._ensure_task_entry_visible()
                    except Exception:
                        pass
        except Exception:
            pass

        # Overdrive stage 5 state (screen dim/blackout overlays)
        self._overdrive_stage5 = False
        self._stage5_overlays = []
        self._stage5_overlay_hwnd = None  # Native Windows overlay HWND for Z-order control
        self._stage5_dim_alpha = 0.0
        self._stage5_dim_dir = 1
        self._stage5_dim_timer = None
        self._stage5_start_mono = 0.0
        self._stage5_hold_engaged = False
        self._stage5_engine = 'overlay'  # Default engine, will be set from settings
        # Gamma engine state (Windows only)
        self._gamma_active = False
        self._gamma_hdc = None
        self._gamma_orig = None
        # Magnification engine state (Windows only)
        self._mag_active = False

    def _build_vertical_layout(self, container):
        """Build traditional vertical stacked layout (current default)."""
        # Title
        title = tk.Label(container, text="Right now - be honest:", fg="#eaeaea", bg="#111",
                        font=("Segoe UI", self._scale(14), "bold"))
        title.pack(anchor="w", pady=(0, self._scale(8)))

        # Button row
        self.button_row = tk.Frame(container, bg="#111")
        self.button_row.pack(fill="x")
        self._create_buttons(self.button_row)

        # Time info
        self._create_time_info(container)

        # Info label
        self._info_lbl = tk.Label(container, text="", fg="#ff9", bg="#111", font=("Segoe UI", self._scale(10)))
        self._info_lbl.pack(pady=(self._scale(6), 0))

        # Task panel
        if bool(self.settings.get("encouragement_enabled", True)):
            self._task_panel = tk.Frame(container, bg="#111", highlightthickness=1, highlightbackground="#333")
            self._task_panel.pack(fill="x", pady=(self._scale(6), 0))
            self._render_task_panel()
        else:
            self._task_panel = None

        # Camera feed
        self._create_camera_section(container)

        # Footer
        self._create_footer(container)

        # Analytics
        if bool(self.settings.get("encouragement_enabled", True)) and bool(self.settings.get("show_task_analytics", True)):
            self._analytics_lbl = tk.Label(container, text="", fg="#aaa", bg="#111", font=("Segoe UI", self._scale(10)))
            self._analytics_lbl.pack(pady=(self._scale(6), 0))
            self._refresh_analytics()
        else:
            self._analytics_lbl = None

    def _build_horizontal_layout(self, container):
        """Build horizontal side-by-side layout (camera left, controls right)."""
        # Create two-column layout
        left_panel = tk.Frame(container, bg="#111")
        left_panel.pack(side="left", fill="both", padx=(0, self._scale(12)))

        right_panel = tk.Frame(container, bg="#111")
        right_panel.pack(side="left", fill="both", expand=True)

        # LEFT: Camera feed
        self._create_camera_section(left_panel)

        # RIGHT: All controls
        # Title
        title = tk.Label(right_panel, text="Right now - be honest:", fg="#eaeaea", bg="#111",
                        font=("Segoe UI", self._scale(13), "bold"))
        title.pack(anchor="w", pady=(0, self._scale(6)))

        # Button row
        self.button_row = tk.Frame(right_panel, bg="#111")
        self.button_row.pack(fill="x")
        self._create_buttons(self.button_row)

        # Time info
        self._create_time_info(right_panel)

        # Info label
        self._info_lbl = tk.Label(right_panel, text="", fg="#ff9", bg="#111", font=("Segoe UI", self._scale(9)))
        self._info_lbl.pack(pady=(self._scale(5), 0))

        # Task panel
        if bool(self.settings.get("encouragement_enabled", True)):
            self._task_panel = tk.Frame(right_panel, bg="#111", highlightthickness=1, highlightbackground="#333")
            self._task_panel.pack(fill="x", pady=(self._scale(5), 0))
            self._render_task_panel()
        else:
            self._task_panel = None

        # Footer
        self._create_footer(right_panel)

        # Analytics
        if bool(self.settings.get("encouragement_enabled", True)) and bool(self.settings.get("show_task_analytics", True)):
            self._analytics_lbl = tk.Label(right_panel, text="", fg="#aaa", bg="#111", font=("Segoe UI", self._scale(9)))
            self._analytics_lbl.pack(pady=(self._scale(5), 0))
            self._refresh_analytics()
        else:
            self._analytics_lbl = None

    def _build_compact_layout(self, container):
        """Build compact minimal layout (small camera at top, tight everything)."""
        # Small camera at top center
        self._create_camera_section(container, compact=True)

        # Title - smaller
        title = tk.Label(container, text="Be honest:", fg="#eaeaea", bg="#111",
                        font=("Segoe UI", self._scale(12), "bold"))
        title.pack(pady=(self._scale(4), self._scale(4)))

        # Button row
        self.button_row = tk.Frame(container, bg="#111")
        self.button_row.pack()
        self._create_buttons(self.button_row, compact=True)

        # Time info
        self._create_time_info(container)

        # Info label - smaller
        self._info_lbl = tk.Label(container, text="", fg="#ff9", bg="#111", font=("Segoe UI", self._scale(9)))
        self._info_lbl.pack(pady=(self._scale(3), 0))

        # Task panel - compact
        if bool(self.settings.get("encouragement_enabled", True)):
            self._task_panel = tk.Frame(container, bg="#111", highlightthickness=1, highlightbackground="#333")
            self._task_panel.pack(fill="x", pady=(self._scale(3), 0))
            self._render_task_panel()
        else:
            self._task_panel = None

        # Footer - compact
        self._create_footer(container, compact=True)

        # No analytics in compact mode to save space
        self._analytics_lbl = None

    def _get_button_phrase(self, button_type):
        """
        Get phrase for button based on mode/list/override settings.

        Args:
            button_type: Either "study" or "waste"

        Returns:
            str: The phrase to display on the button
        """
        # Classic labels stay stable unless custom phrases are enabled
        if not self.settings.get("custom_button_phrases_enabled", False):
            return "Studying" if button_type == "study" else "Wasting time"

        # Keep the runtime setting contract explicit so inventory tooling can
        # prove that both persisted phrase families have a consumer.
        phrase_keys = {
            "study": {
                "mode": "study_phrase_mode",
                "override": "study_phrase_override",
                "list": "study_phrase_list",
            },
            "waste": {
                "mode": "waste_phrase_mode",
                "override": "waste_phrase_override",
                "list": "waste_phrase_list",
            },
        }[button_type]
        mode = self.settings.get(phrase_keys["mode"], "random")
        override = (self.settings.get(phrase_keys["override"], "") or "").strip()
        phrase_list = self.settings.get(phrase_keys["list"], [])

        # Override mode - use single phrase
        if mode == "override" and override:
            return override

        # Empty list fallback to defaults
        if not phrase_list:
            return "Studying" if button_type == "study" else "Wasting time"

        # Random mode
        if mode == "random":
            return random.choice(phrase_list)

        # Sequential mode - track index per dialog instance
        if button_type == "study":
            phrase = phrase_list[self._study_phrase_index % len(phrase_list)]
            self._study_phrase_index += 1
            return phrase
        else:  # waste
            phrase = phrase_list[self._waste_phrase_index % len(phrase_list)]
            self._waste_phrase_index += 1
            return phrase

    def _create_buttons(self, parent, compact=False):
        """Create action buttons (studying/wasting time)."""
        btn_font_size = self._scale(14 if compact else 16)
        btn_width = self._scale(12 if compact else 14)

        # Get dynamic button text from settings
        study_text = self._get_button_phrase("study")
        waste_text = self._get_button_phrase("waste")

        self.btn_study = tk.Button(parent, text=study_text, font=("Segoe UI", btn_font_size, "bold"),
                                   relief="solid", bd=2, width=btn_width)
        self.btn_waste = None
        if not bool(self.settings.get("hide_wasting_button", False)):
            self.btn_waste = tk.Button(parent, text=waste_text, font=("Segoe UI", btn_font_size, "bold"),
                                       relief="solid", bd=2, width=btn_width)

        # DON'T pack buttons here - _place_buttons_random() uses grid() to place them!

        self.btn_study.bind("<ButtonPress-1>", self._study_hold_start)
        self.btn_study.bind("<ButtonRelease-1>", self._study_hold_end)

        if self.btn_waste is not None:
            self.btn_waste.bind("<ButtonPress-1>", self._waste_hold_start)
            self.btn_waste.bind("<ButtonRelease-1>", self._waste_hold_end)

        self._action_buttons = [self.btn_study] + ([self.btn_waste] if self.btn_waste is not None else [])
        self._bound_action_buttons = []
        self._configure_action_buttons()
        self.bind("<Return>", self._handle_action_key, add=True)
        self.bind("<KP_Enter>", self._handle_action_key, add=True)

    def _create_time_info(self, parent):
        """Create optional time info label."""
        try:
            self._time_lbl = tk.Label(parent, text="", fg="#9fd", bg="#111", font=("Segoe UI", self._scale(10)))
            if self.settings.get("show_time_info", False):
                self._time_lbl.pack(pady=(self._scale(6), 0))
                self._start_time_info()
        except Exception:
            self._time_lbl = None

    def _create_camera_section(self, parent, compact=False):
        """Create camera feed and biodata section."""
        try:
            self._init_camera_feed()
            camera_widget = self._create_camera_feed_widget(parent)
            if camera_widget is not None:
                pady = (self._scale(4), 0) if compact else (self._scale(8), 0)
                camera_widget.pack(fill="x", pady=pady)

                # Biodata
                try:
                    biodata_label = self._create_biodata_label(parent)
                    if biodata_label is not None:
                        biodata_label.pack(fill="x", pady=(self._scale(3 if compact else 6), 0))
                except Exception as biodata_err:
                    try:
                        get_logger().error(f"Failed to create biodata label: {biodata_err}")
                    except Exception:
                        pass
        except Exception as e:
            try:
                get_logger().error(f"Failed to initialize camera feed: {e}")
            except Exception:
                pass

    def _create_footer(self, parent, compact=False):
        """Create footer with settings/task links."""
        font_size = self._scale(9 if compact else 10)
        pady = (self._scale(4), 0) if compact else (self._scale(8), 0)

        footer = tk.Frame(parent, bg="#111")
        footer.pack(fill="x", pady=pady)

        settings_link = tk.Label(footer, text="Settings", fg="#7fb7ff", bg="#111",
                                cursor="hand2", font=("Segoe UI", font_size, "underline"))
        settings_link.pack(side="left")
        settings_link.bind("<Button-1>", self._open_settings)

        if bool(self.settings.get("encouragement_enabled", True)):
            task_link = tk.Label(footer, text="Task", fg="#7fffb7", bg="#111",
                                cursor="hand2", font=("Segoe UI", font_size, "underline"))
            task_link.pack(side="left", padx=(self._scale(10), 0))
            task_link.bind("<Button-1>", self._toggle_task_entry)

    def _scale(self, value):
        """
        Scale a numeric value by the UI scale factor.

        Args:
            value: Integer or float to scale

        Returns:
            Scaled integer value
        """
        return int(value * self._ui_scale)

    def _open_settings(self, _evt=None):
        """
        Open the settings window.

        Args:
            _evt: Optional event object
        """
        def apply_and_refresh(new_settings):
            """
            Apply new settings and regenerate the popup.

            Instead of trying to update individual elements, we close this popup
            and immediately open a new one with the updated settings.
            """
            self.settings.update(new_settings)

            # If we have a reference to the app, close this dialog and trigger a new prompt immediately
            if self.app_ref is not None:
                try:
                    # Mark as closed to prevent scheduling issues
                    self._closed = True

                    # Clean up this dialog
                    try:
                        self._cleanup_camera_feed()
                    except Exception:
                        pass

                    try:
                        self._cleanup_all_timers()
                    except Exception:
                        pass

                    try:
                        self._destroy_stage5_overlays()
                    except Exception:
                        pass

                    # Destroy this dialog
                    self.destroy()

                    # Schedule immediate new prompt with updated settings
                    # Use after() to ensure the old dialog is fully destroyed first
                    self.app_ref.root.after(100, lambda: self.app_ref._schedule_next(0))

                    try:
                        get_logger().info("Settings changed - regenerating popup with new settings")
                    except Exception:
                        pass

                except Exception as e:
                    try:
                        get_logger().error(f"Failed to regenerate popup: {e}")
                    except Exception:
                        pass
            else:
                # Fallback: Apply what we can without regenerating (old behavior)
                if self.settings["always_on_top"]:
                    self.attributes("-topmost", True)
                else:
                    self.attributes("-topmost", False)

                # Try to update wasting button visibility
                try:
                    want_hide = bool(self.settings.get("hide_wasting_button", False))
                    have_btn = (self.btn_waste is not None)
                    if want_hide and have_btn:
                        try:
                            self.btn_waste.destroy()
                        except Exception:
                            pass
                        self.btn_waste = None
                        self._action_buttons = [self.btn_study]
                        self._configure_action_buttons()
                        self._place_buttons_random()
                    elif (not want_hide) and (not have_btn):
                        self.btn_waste = tk.Button(self.button_row, text="Wasting time", font=("Segoe UI", 16, "bold"),
                                                   relief="solid", bd=2, width=14)
                        self.btn_waste.bind("<ButtonPress-1>", self._waste_hold_start)
                        self.btn_waste.bind("<ButtonRelease-1>", self._waste_hold_end)
                        self._action_buttons = [self.btn_study, self.btn_waste]
                        self._configure_action_buttons()
                        self._place_buttons_random()
                except Exception:
                    pass

        from ..windows import SettingsWindow
        SettingsWindow(self, self.settings, on_save=apply_and_refresh)

    def _ignore_close(self):
        """
        Handle window close attempts by showing message instead of closing.

        Enforces that user must make a choice before dismissing dialog.
        """
        try:
            if bool(self.settings.get("require_active_task", False)) and self.taskdb:
                active = None
                try:
                    active = self.taskdb.get_active()
                except Exception:
                    active = None
                if not active:
                    messagebox.showinfo("Set Task", "You must set a task to continue.")
                    try:
                        self._ensure_task_entry_visible()
                    except Exception:
                        pass
                    return
        except Exception:
            pass
        if self.btn_waste is None:
            messagebox.showinfo("Decide", "Confirm you're Studying (hold if enabled).")
        else:
            messagebox.showinfo("Decide", "Pick one: Studying or Wasting time.")

    def _finish(self, choice):
        """
        Complete the dialog and submit the user's choice.

        Args:
            choice: String indicating user's choice ("Studying" or "Wasting time")
        """
        if self._closed: return
        # Enforce active task requirement (optional)
        try:
            if bool(self.settings.get("require_active_task", False)) and self.taskdb:
                active = None
                try:
                    active = self.taskdb.get_active()
                except Exception:
                    active = None
                if not active:
                    messagebox.showinfo("Set Task", "You must set a task before continuing.")
                    try:
                        self._ensure_task_entry_visible()
                    except Exception:
                        pass
                    return
        except Exception:
            pass
        # If a task decision is required and user bypasses with Studying/Wasting, count as failure
        try:
            if self._task_decision_required and self.taskdb and self._task_decision_task_id is not None:
                implies_fail = bool(self.settings.get("tasks_study_implies_fail_on_decision", True))
                if implies_fail and self._task_decision_can_fail and choice in ("Studying", "Wasting time"):
                    try:
                        self.taskdb.mark_failed(self._task_decision_task_id)
                    except Exception:
                        pass
                    self._task_decision_required = False
                    self._task_decision_task_id = None
                    self._task_decision_can_fail = False
                    # Refresh panel/analytics quickly
                    try:
                        self._render_task_panel(); self._refresh_analytics()
                    except Exception:
                        pass
        except Exception:
            pass
        latency_ms = int((time.monotonic() - self.start_monotonic) * 1000)
        try:
            try:
                get_logger().info(
                    "choice=%s latency_ms=%s intensity=%s overdrive=%s",
                    choice, latency_ms, self.intensity_level, self._overdrive
                )
            except Exception:
                pass
            append_log(
                response=choice,
                latency_ms=latency_ms,
                settings=self.settings,
                intensity_level_reached=self.intensity_level + (10 if self._overdrive else 0),
                slot_start_dt=self.slot_start_dt,
                overdrive_deadline_s=int(self.settings["overdrive_after_seconds"])
            )
        except Exception as e:
            try:
                get_logger().error("append_log failed: %s", e)
            except Exception:
                print(f"append_log failed: {e}", file=sys.stderr)
        # Capture photo for accountability logs if enabled
        try:
            photo_path = self._capture_photo_for_logs(choice)
            if photo_path:
                try:
                    get_logger().info(f"Accountability photo captured: {photo_path}")
                except Exception:
                    pass
        except Exception as e:
            try:
                get_logger().error(f"Photo capture failed: {e}")
            except Exception:
                pass
        try:
            self._flash_taskbar_stop()
        except Exception:
            pass
        # Tear down Stage 5 overlays if present
        try:
            self._destroy_stage5_overlays()
        except Exception:
            pass
        # Stop any continuous audio alarms
        try:
            from ...utils import get_audio_alarm
            get_audio_alarm().stop()
        except Exception:
            pass
        # Clean up camera feed
        try:
            self._cleanup_camera_feed()
        except Exception:
            pass
        # Reset overdrive flags on completion
        self._overdrive_stage4 = False
        self._closed = True
        # Clean up all timers before destroying
        self._cleanup_all_timers()
        self.destroy()

    def _schedule_timer(self, delay_ms, callback):
        """
        Schedule a timer and track it for cleanup.

        Args:
            delay_ms: Delay in milliseconds
            callback: Function to call after delay

        Returns:
            Timer ID or None if dialog is closed
        """
        if self._closed:
            return None
        timer_id_holder = {}

        def _run_once():
            timer_id = timer_id_holder.get("id")
            if timer_id is not None:
                self._active_timers.discard(timer_id)
            if self._closed:
                return
            callback()

        timer_id = self.after(delay_ms, _run_once)
        timer_id_holder["id"] = timer_id
        self._active_timers.add(timer_id)
        return timer_id

    def _cancel_timer(self, timer_id):
        """
        Cancel a specific timer and remove from tracking.

        Args:
            timer_id: Timer ID to cancel
        """
        if timer_id and timer_id in self._active_timers:
            try:
                self.after_cancel(timer_id)
            except Exception:
                pass
            self._active_timers.discard(timer_id)

    def _cleanup_all_timers(self):
        """
        Cancel all active timers.

        Called before destroying the dialog to ensure clean shutdown.
        """
        for timer_id in list(self._active_timers):
            try:
                self.after_cancel(timer_id)
            except Exception:
                pass
        self._active_timers.clear()

"""
Version 2 activity-aware prompt dialog.
"""

import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from .spam_detection import SpamDetector
from ...settings.gates import is_spam_detection_enabled
from .prompt_dialog_mixins.window_placement import WindowPlacementMixin
from .prompt_dialog_mixins.windows_integration import WindowsIntegrationMixin
from .prompt_dialog_mixins.task_management import TaskManagementMixin
from .prompt_dialog_mixins.time_display import TimeDisplayMixin
from .prompt_dialog_mixins.camera_feed import CameraFeedMixin
from .intervention_wizard import InterventionWizard
from ...platform_specific.icon_extract import get_app_icon_image

try:
    from PIL import ImageTk  # type: ignore
    PIL_TK_AVAILABLE = True
except Exception:
    ImageTk = None
    PIL_TK_AVAILABLE = False

try:
    from ...database import append_log
except Exception:  # pragma: no cover - fallback
    def append_log(**kwargs):
        pass

try:
    from ...utils import get_logger, privacy_summary
except Exception:  # pragma: no cover - fallback
    def get_logger():
        import logging
        return logging.getLogger(__name__)

    def privacy_summary(value):
        return {"type": type(value).__name__, "length": len(str(value or "")), "sha256": None}

from ...utils.timers import TimerRegistry


class V2PromptDialog(
    WindowPlacementMixin,
    WindowsIntegrationMixin,
    TaskManagementMixin,
    TimeDisplayMixin,
    CameraFeedMixin,
    tk.Toplevel
):
    """Activity-aware V2 prompt dialog."""

    def __init__(self, master, settings, on_submit, slot_start_dt, activity_info=None, app_ref=None, taskdb=None):
        super().__init__(master)
        self.settings = settings
        self.on_submit = on_submit
        self.slot_start_dt = slot_start_dt
        self.activity_info = activity_info or {}
        self.app_ref = app_ref
        self.taskdb = taskdb
        self._dialog_shown_at = time.time()
        self._closed = False
        self._submit_notified = False
        self._active_timers = set()
        self._timer_names = {}
        self._timer_sequence = 0
        self._timers = TimerRegistry(self)
        self._task_panel = None
        self._task_change_form = None
        self._task_timer_id = None
        self._analytics_lbl = None
        self._task_decision_required = False
        self._task_decision_task_id = None
        self._task_decision_can_fail = False
        self._focus_prompt_open = False
        self._focus_requires_enter = bool(self.settings.get("v2_focus_requires_enter", False))

        self.title("Activity Check-in")
        self.configure(bg="#111")
        self.resizable(False, False)
        if self.settings.get("always_on_top", True):
            self.attributes("-topmost", True)

        scale_percent = self.settings.get("ui_scale_percent", 100)
        self._ui_scale = scale_percent / 100.0

        try:
            self._disable_minimize_button()
        except Exception:
            pass
        try:
            self._flash_taskbar_begin()
        except Exception:
            pass
        try:
            self.bind("<Unmap>", self._prevent_minimize)
        except Exception:
            pass

        self._init_validation()
        self._build_ui()

        self.update_idletasks()
        if self.settings.get("center_on_show", True):
            self._center_on_active_monitor()
        self.update()
        self._force_window_to_front()

        try:
            if bool(self.settings.get("follow_cursor_monitor", True)):
                self._schedule_timer(400, self._follow_cursor_center_loop)
        except Exception:
            pass

        self.protocol("WM_DELETE_WINDOW", self._ignore_close)
        try:
            self.bind("<Escape>", self._ignore_close, add=True)
            if self._focus_requires_enter:
                self.bind("<Return>", self._focus_if_needed, add=True)
                self.bind("<KP_Enter>", self._focus_if_needed, add=True)
        except Exception:
            pass

    def _init_validation(self):
        self._effective_settings = self._get_effective_validation_settings()
        self._init_spam_detector()
        # V2 uses a fixed question; no challenge system.

    def _get_effective_validation_settings(self):
        if not bool(self.settings.get("v2_force_all_validations", True)):
            return self.settings
        s = dict(self.settings)
        if is_spam_detection_enabled(s):
            s["spam_gibberish_detection"] = True
            s["spam_repetition_check"] = True
            s["spam_spacing_check"] = True
            s["spam_keyboard_pattern_check"] = True
            s["spam_dictionary_check"] = True
            s["spam_timing_check"] = True
        s["challenge_system_enabled"] = True
        for key in list(s.keys()):
            if key.startswith("challenge_studying_") and key.endswith("_enabled"):
                s[key] = True
            if key.startswith("challenge_wasting_") and key.endswith("_enabled"):
                s[key] = True
        return s

    def _init_spam_detector(self):
        logger = get_logger()
        if not is_spam_detection_enabled(self._effective_settings):
            logger.info("spam_check: skipped because disabled")
            self.spam_detector = None
            return

        s = self._effective_settings
        logger.info("spam_check: running because enabled")
        config = {
            "enable_gibberish_detection": s.get("spam_gibberish_detection", True),
            "min_vowel_ratio": s.get("spam_min_vowel_ratio", 0.2),
            "max_vowel_ratio": s.get("spam_max_vowel_ratio", 0.7),
            "min_unique_char_ratio": s.get("spam_min_unique_char_ratio", 0.4),
            "enable_repetition_check": s.get("spam_repetition_check", True),
            "max_consecutive_chars": s.get("spam_max_consecutive_chars", 2),
            "max_pattern_repetition": s.get("spam_max_pattern_repetition", 3),
            "enable_spacing_check": s.get("spam_spacing_check", True),
            "min_length_require_spaces": s.get("spam_min_length_require_spaces", 15),
            "enable_keyboard_pattern_check": s.get("spam_keyboard_pattern_check", True),
            "min_keyboard_sequence_length": s.get("spam_min_keyboard_sequence_length", 4),
            "enable_dictionary_check": s.get("spam_dictionary_check", True),
            "min_real_word_ratio": s.get("spam_min_real_word_ratio", 0.6),
            "min_word_length": s.get("spam_min_word_length", 2),
            "enable_timing_check": s.get("spam_timing_check", True),
            "min_time_to_submit": s.get("spam_min_time_to_submit", 3),
            "flag_if_under": s.get("spam_flag_if_under", 2),
            "banned_words": s.get("spam_banned_words", ["idk", "dunno", "meh", "whatever"]),
            "vague_words": s.get("spam_vague_words", ["stuff", "things", "something", "nothing"]),
        }
        logger.info("spam_check: config=%s", config)
        self.spam_detector = SpamDetector(config)

    def _build_ui(self):
        container = tk.Frame(self, bg="#111")
        container.pack(padx=14, pady=14)

        title = tk.Label(container, text="Activity check-in", fg="#eaeaea", bg="#111",
                         font=("Segoe UI", 14, "bold"))
        title.pack(anchor="w", pady=(0, 8))

        activity_frame = tk.Frame(container, bg="#1a1a1a", highlightthickness=1, highlightbackground="#333")
        activity_frame.pack(fill="x", pady=(0, 12))

        app_name = self.activity_info.get("app_name") or "Desktop"
        window_title = self.activity_info.get("title") or "No active window"
        duration = self.activity_info.get("active_duration_s")
        duration_txt = self._format_duration(duration)
        url = self.activity_info.get("url")

        header = tk.Frame(activity_frame, bg="#1a1a1a")
        header.pack(fill="x", padx=10, pady=(8, 2))
        self._app_icon_img = None
        icon_label = None
        try:
            exe_path = self.activity_info.get("exe_path")
            if exe_path and PIL_TK_AVAILABLE:
                icon_image = get_app_icon_image(exe_path, size=20)
                if icon_image is not None:
                    self._app_icon_img = ImageTk.PhotoImage(icon_image)
                    icon_label = tk.Label(header, image=self._app_icon_img, bg="#1a1a1a")
                    icon_label.pack(side="left")
        except Exception:
            icon_label = None
        if icon_label is None:
            badge_text = (app_name[:1] or "?").upper()
            tk.Label(header, text=badge_text, fg="#ffffff", bg="#333333",
                     font=("Segoe UI", 9, "bold"), width=2).pack(side="left")
        tk.Label(header, text=f"App: {app_name}", fg="#eaeaea", bg="#1a1a1a",
                 font=("Segoe UI", 10, "bold")).pack(side="left", padx=(6, 0))
        tk.Label(activity_frame, text=f"Title: {window_title}", fg="#cccccc", bg="#1a1a1a",
                 font=("Segoe UI", 9), wraplength=520, justify="left").pack(anchor="w", padx=10)
        tk.Label(activity_frame, text=f"Active: {duration_txt}", fg="#cccccc", bg="#1a1a1a",
                 font=("Segoe UI", 9)).pack(anchor="w", padx=10, pady=(2, 6))
        if url:
            tk.Label(activity_frame, text=f"URL: {url}", fg="#cccccc", bg="#1a1a1a",
                     font=("Segoe UI", 9), wraplength=520, justify="left").pack(anchor="w", padx=10, pady=(0, 8))

        question_title = window_title if self.settings.get("v2_question_use_window_title", True) else app_name
        if not question_title:
            question_title = "this application"
        question1 = f"Why are you on {question_title}?"
        tk.Label(container, text=question1, fg="#eaeaea", bg="#111",
                 font=("Segoe UI", 10)).pack(anchor="w")
        self.answer_var = tk.StringVar()
        self.answer_entry = ttk.Entry(container, textvariable=self.answer_var, width=64)
        self.answer_entry.pack(fill="x", pady=(4, 10))
        try:
            self.answer_entry.bind("<Return>", self._on_answer_enter, add=True)
            self.answer_entry.bind("<KP_Enter>", self._on_answer_enter, add=True)
        except Exception:
            pass

        tk.Label(container, text="Do you need an intervention? (yes/no)", fg="#eaeaea",
                 bg="#111", font=("Segoe UI", 10)).pack(anchor="w")
        self.intervention_var = tk.StringVar()
        self.intervention_entry = ttk.Entry(container, textvariable=self.intervention_var, width=20)
        self.intervention_entry.pack(anchor="w", pady=(4, 6))
        try:
            self.intervention_entry.bind("<Return>", lambda _e: self._save(), add=True)
            self.intervention_entry.bind("<KP_Enter>", lambda _e: self._save(), add=True)
        except Exception:
            pass

        # Time info
        self._create_time_info(container)

        # Task panel
        if bool(self.settings.get("encouragement_enabled", True)):
            self._task_panel = tk.Frame(container, bg="#111", highlightthickness=1, highlightbackground="#333")
            self._task_panel.pack(fill="x", pady=(6, 0))
            try:
                self._render_task_panel()
            except Exception:
                pass

        # Camera + biodata
        self._create_camera_section(container)

        # Footer links
        self._create_footer(container)

        if not self._focus_requires_enter:
            try:
                self._schedule_timer(50, self._focus_primary_entry)
            except Exception:
                pass

    def _focus_primary_entry(self):
        try:
            self.answer_entry.focus_set()
        except Exception:
            pass

    def _focus_if_needed(self, _evt=None):
        try:
            current = self.focus_get()
            if current in (self.answer_entry, self.intervention_entry):
                return None
        except Exception:
            pass
        try:
            self.answer_entry.focus_set()
        except Exception:
            pass
        return "break"

    def _on_answer_enter(self, _evt=None):
        try:
            answer = (self.answer_var.get() or "").strip()
            decision = (self.intervention_var.get() or "").strip().lower()
            if answer and decision in ("yes", "no"):
                self._save()
                return "break"
            self.intervention_entry.focus_set()
            try:
                self.intervention_entry.select_range(0, "end")
            except Exception:
                pass
        except Exception:
            pass
        return "break"

    def _format_duration(self, duration_s):
        if duration_s is None:
            return "unknown"
        try:
            seconds = int(max(0, duration_s))
            m, s = divmod(seconds, 60)
            h, m = divmod(m, 60)
            if h:
                return f"{h}h {m}m {s}s"
            if m:
                return f"{m}m {s}s"
            return f"{s}s"
        except Exception:
            return "unknown"

    def _create_time_info(self, parent):
        try:
            self._time_lbl = tk.Label(parent, text="", fg="#9fd", bg="#111", font=("Segoe UI", self._scale(10)))
            if self.settings.get("show_time_info", False):
                self._time_lbl.pack(pady=(self._scale(6), 0))
                self._start_time_info()
        except Exception:
            self._time_lbl = None

    def _create_camera_section(self, parent, compact=False):
        try:
            self._init_camera_feed()
            camera_widget = self._create_camera_feed_widget(parent)
            if camera_widget is not None:
                pady = (self._scale(4), 0) if compact else (self._scale(8), 0)
                camera_widget.pack(fill="x", pady=pady)
                try:
                    biodata_label = self._create_biodata_label(parent)
                    if biodata_label is not None:
                        biodata_label.pack(fill="x", pady=(self._scale(3 if compact else 6), 0))
                except Exception:
                    pass
        except Exception:
            pass

    def _create_footer(self, parent, compact=False):
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
        return int(value * self._ui_scale)

    def _open_settings(self, _evt=None):
        from ..windows import SettingsWindow

        def apply_and_refresh(new_settings):
            self.settings.update(new_settings)
            if self.app_ref is not None:
                try:
                    self._closed = True
                    try:
                        self._cleanup_camera_feed()
                    except Exception:
                        pass
                    try:
                        self._cleanup_timers()
                    except Exception:
                        pass
                    self.destroy()
                    self.app_ref.root.after(100, lambda: self.app_ref._schedule_next(0))
                except Exception:
                    pass
        SettingsWindow(self, self.settings, on_save=apply_and_refresh)

    def _save(self):
        answer = (self.answer_var.get() or "").strip()
        if not answer:
            messagebox.showerror("Required", "Please answer what you're doing.")
            self.answer_entry.focus_set()
            return

        # Spam detection
        if self.spam_detector:
            time_elapsed = time.time() - self._dialog_shown_at
            is_valid, error_msg = self.spam_detector.is_valid_response(answer, time_elapsed)
            if not is_valid:
                get_logger().warning("spam_check: rejected | reason=%s", error_msg)
                messagebox.showerror("Invalid Response", error_msg)
                self.answer_entry.focus_set()
                return

        decision = (self.intervention_var.get() or "").strip().lower()
        if decision not in ("yes", "no"):
            messagebox.showerror("Required", "Please type yes or no for intervention.")
            self.intervention_entry.focus_set()
            return

        if decision == "yes":
            completed = self._start_intervention_stub()
            if not completed:
                return

        self._log_response(decision)
        self._close()

    def _start_intervention_stub(self):
        logger = None
        try:
            logger = get_logger()
        except Exception:
            logger = None

        def _run_intervention():
            try:
                if logger:
                    logger.info("V2 intervention requested | thread=%s", threading.current_thread().name)
            except Exception:
                pass
            parent = self.app_ref.root if self.app_ref is not None else self
            hide_prompt = bool(self.settings.get("v2_hide_prompt_during_intervention", True))
            preselect = self.activity_info.get("hwnd")
            title = self.activity_info.get("title")
            try:
                if logger:
                    logger.info(
                        "intervention wizard starting | hwnd=%s title_summary=%s hide_prompt=%s",
                        preselect,
                        privacy_summary(title),
                        hide_prompt,
                    )
            except Exception:
                pass
            result = False
            wizard = None
            app_runner = getattr(self.app_ref, "run_intervention", None) if self.app_ref is not None else None
            try:
                if callable(app_runner):
                    # The App owns the intervention lease and lifecycle. V2
                    # supplies context but does not mutate global state.
                    result = bool(app_runner(
                        self.settings,
                        preselect_hwnd=preselect,
                        preselect_title=title,
                        prompt_ref=self,
                        hide_prompt=hide_prompt,
                    ))
                else:
                    # Preserve standalone dialog compatibility for isolated
                    # consumers that do not provide the App composition root.
                    try:
                        wizard = InterventionWizard(parent, self.settings)
                    except TypeError:
                        wizard = InterventionWizard(parent)
                        try:
                            wizard.settings = self.settings
                        except Exception:
                            pass
                    result = bool(wizard.run(
                        preselect_hwnd=preselect,
                        preselect_title=title,
                        prompt_ref=self,
                        hide_prompt=hide_prompt,
                    ))
            except Exception:
                if logger:
                    logger.exception("intervention wizard run failed", exc_info=True)
                result = False
            if not result:
                try:
                    if logger:
                        logger.warning("intervention wizard ended without completion")
                except Exception:
                    pass
                try:
                    self.deiconify()
                    self.lift()
                    self._force_window_to_front()
                except Exception:
                    if logger:
                        logger.exception("intervention: failed to restore prompt after wizard", exc_info=True)
                try:
                    if not bool(getattr(wizard, "_error_shown", False)):
                        messagebox.showinfo("Intervention", "Intervention was cancelled or failed to start.")
                except Exception:
                    if logger:
                        logger.exception("intervention: failed to show cancellation info", exc_info=True)
            # Standalone dialogs have no App coordinator; restore their
            # prompt locally. App-owned runs restore through run_intervention.
            if not callable(app_runner):
                try:
                    if not self.winfo_viewable():
                        self.deiconify()
                    self.lift()
                    self._force_window_to_front()
                except Exception:
                    if logger:
                        logger.exception("intervention: failed to restore prompt in finally", exc_info=True)
            return result

        parent = self.app_ref.root if self.app_ref is not None else self
        tk_thread_id = None
        try:
            tk_thread_id = getattr(self.app_ref, "_tk_thread_id", None)
        except Exception:
            tk_thread_id = None
        if tk_thread_id is None:
            try:
                tk_thread_id = getattr(parent, "_focuscheck_tk_thread_id", None)
            except Exception:
                tk_thread_id = None
        if tk_thread_id is not None and threading.get_ident() != tk_thread_id:
            try:
                if logger:
                    logger.warning("intervention requested off Tk thread; marshaling to main loop")
            except Exception:
                pass
            done = threading.Event()
            outcome = {"completed": False}

            def _run_on_ui():
                try:
                    outcome["completed"] = bool(_run_intervention())
                finally:
                    done.set()

            try:
                parent.after(0, _run_on_ui)
            except Exception:
                if logger:
                    logger.exception("intervention: failed to marshal to Tk thread", exc_info=True)
                return False
            done.wait(timeout=60.0)
            return outcome["completed"]

        return _run_intervention()

    def _log_response(self, decision):
        try:
            latency_ms = int((time.monotonic() - (self.slot_start_dt.get("mono_start") if self.slot_start_dt else time.monotonic())) * 1000)
        except Exception:
            latency_ms = 0
        try:
            app_name = self.activity_info.get("app_name") or "Desktop"
            answer = (self.answer_var.get() or "").strip().replace("\n", " ")
            if len(answer) > 80:
                answer = answer[:77] + "..."
            response = f"V2:{decision}:{app_name}:{answer}"
        except Exception:
            response = f"V2:{decision}"
        try:
            append_log(
                response=response,
                latency_ms=latency_ms,
                settings=self.settings,
                intensity_level_reached=0,
                slot_start_dt=self.slot_start_dt,
                overdrive_deadline_s=int(self.settings.get("overdrive_after_seconds", 60)),
            )
        except Exception:
            pass

    def _ignore_close(self, _event=None):
        try:
            messagebox.showinfo("Required", "Please answer the activity check-in before closing.")
            self._focus_primary_entry()
        except Exception:
            pass
        return "break"

    def _close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self._cleanup_camera_feed()
        except Exception:
            pass
        try:
            self._flash_taskbar_stop()
        except Exception:
            pass
        self._cleanup_timers()
        try:
            self.destroy()
        except Exception:
            pass
        self._notify_submit()

    def _notify_submit(self):
        if self._submit_notified:
            return
        self._submit_notified = True
        try:
            if callable(self.on_submit):
                self.on_submit()
        except Exception:
            try:
                get_logger().exception("V2 prompt submit callback failed", exc_info=True)
            except Exception:
                pass

    def _schedule_timer(self, delay_ms, callback):
        if self._closed:
            return None

        timers = getattr(self, "_timers", None)
        if timers is not None:
            self._timer_sequence = getattr(self, "_timer_sequence", 0) + 1
            name = f"v2-prompt-{self._timer_sequence}"
            timer_id_holder = {}

            def run_once():
                timer_id = timer_id_holder.get("id")
                if timer_id is not None:
                    self._active_timers.discard(timer_id)
                    self._timer_names.pop(timer_id, None)
                if not self._closed:
                    callback()

            timers.schedule(name, delay_ms, run_once)
            timer_id = timers.callback_id(name)
            timer_id_holder["id"] = timer_id
            self._timer_names[timer_id] = name
            self._active_timers.add(timer_id)
            return timer_id

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

    def _cleanup_timers(self):
        timers = getattr(self, "_timers", None)
        if timers is not None:
            timers.close()
            self._timer_names.clear()
        else:
            for timer_id in list(self._active_timers):
                try:
                    self.after_cancel(timer_id)
                except Exception:
                    pass
        self._active_timers.clear()

    def _cleanup_all_timers(self):
        self._cleanup_timers()

    def _destroy_stage5_overlays(self):
        return None


__all__ = ["V2PromptDialog"]

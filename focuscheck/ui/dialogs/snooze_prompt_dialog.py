"""
Snooze Confirmation Dialog.

Single popup with two text boxes:
- Box 1: "Why are you snoozing?" (required with spam/quality checks)
- Box 2: Exact-typing confirmation from a sentence list (required if enabled)

Keyboard behavior:
- Focus starts in Box 1
- Tab moves to Box 2, then to buttons
- Enter submits only when focus is on the last box or the confirm button
- Escape cancels

Copy/paste prevention (optional) for the exact-typing field to encourage deliberate typing.
"""

import random
import tkinter as tk
from tkinter import ttk, messagebox
import time

from .spam_detection import SpamDetector
from ...settings.gates import is_spam_detection_enabled
from ...utils.timers import TimerRegistry

try:
    from ...utils import get_logger, privacy_summary
except ImportError:
    def get_logger():
        import logging
        return logging.getLogger(__name__)

    def privacy_summary(value):
        return {"type": type(value).__name__, "length": len(str(value or "")), "sha256": None}


class SnoozePromptDialog(tk.Toplevel):
    """Single snooze confirmation dialog with two required inputs."""

    def __init__(self, master, settings, on_submit=None, on_cancel=None, monotonic_clock=None):
        super().__init__(master)
        self.title("Confirm Snooze")
        self.configure(bg="#111")
        self.resizable(False, False)

        self.settings = settings or {}
        self.on_submit = on_submit
        self.on_cancel = on_cancel

        # Logger helper
        try:
            self._logger = get_logger()
        except Exception:
            self._logger = None

        # Track timing
        self._monotonic_clock = monotonic_clock if callable(monotonic_clock) else time.monotonic
        self._dialog_shown_at = self._monotonic_clock()
        self._focus_order = []
        self._prevent_paste = bool(self.settings.get("snooze_exact_prevent_paste", True))
        self._case_sensitive = bool(self.settings.get("snooze_sentence_case_sensitive", True))
        self._timers = TimerRegistry(self)

        self.reason_required = bool(self.settings.get("snooze_prompt_ask_reason", True))
        self.exact_required = bool(self.settings.get("snooze_prompt_exact_enabled", True))
        self.sentence_choices = self._normalize_sentence_list(
            self.settings.get("snooze_prompt_sentences", [])
        )

        self._log(f"init: reason_required={self.reason_required} exact_required={self.exact_required}"
                  f" prevent_paste={self._prevent_paste} case_sensitive={self._case_sensitive}")

        # Build UI container
        self.container = tk.Frame(self, bg="#111", padx=12, pady=10)
        self.container.pack(fill="both", expand=True)

        # Prepare validators
        self._init_spam_detector()

        # Build single-stage UI
        self._build_ui()
        self._center_on_screen()

        # Modal-ish behavior
        try:
            self.transient(master)
        except Exception:
            pass
        try:
            self.grab_set()
        except Exception:
            pass
        # Honor always_on_top setting
        if bool(self.settings.get("always_on_top", True)):
            try:
                self.attributes("-topmost", True)
            except Exception:
                pass
        self._ensure_visible_timer_id = self._schedule_owned_timer(
            "_ensure_visible_timer_id", 200, self._ensure_visible
        )

        # Key bindings
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Return>", self._on_return, add=True)
        self.bind("<KP_Enter>", self._on_return, add=True)
        self.bind("<Escape>", self._on_escape, add=True)

        # Center on parent
        self.update_idletasks()
        self._center_on_parent()

        # Initial focus
        self._initial_focus_timer_id = self._schedule_owned_timer(
            "_initial_focus_timer_id", 30, self._set_initial_focus
        )

    def _log(self, message):
        logger = getattr(self, "_logger", None)
        if not logger:
            return
        try:
            logger.info("snooze_prompt: %s", message)
        except Exception:
            pass

    def _schedule_owned_timer(self, attribute, delay_ms, callback):
        """Clear a one-shot timer handle before invoking its callback."""
        timers = getattr(self, "_timers", None)
        if timers is not None:
            timers.schedule(attribute, delay_ms, callback)
            return timers.callback_id(attribute)

        def run():
            setattr(self, attribute, None)
            callback()

        return self.after(delay_ms, run)

    # ----- UI building -----
    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}
        self.reason_var = tk.StringVar()

        title = tk.Label(self.container, text="Before snoozing...", fg="#ffcc00", bg="#111",
                         font=("Segoe UI", 12, "bold"))
        title.grid(row=0, column=0, columnspan=2, sticky="w", **pad)

        row = 1
        self.reason_entry = None
        if self.reason_required:
            prompt = "Why are you snoozing?"
            ttk.Label(self.container, text=prompt, wraplength=460).grid(row=row, column=0, columnspan=2, sticky="w", **pad)
            row += 1

            self.reason_entry = ttk.Entry(self.container, textvariable=self.reason_var, width=58)
            self.reason_entry.grid(row=row, column=0, columnspan=2, sticky="we", **pad)
            self._focus_order.append(self.reason_entry)
            row += 1
        self._log(f"build_ui: reason field enabled={self.reason_required}")

        # Only show exact-typing section if enabled
        self.target_sentence = None
        self.typed_var = tk.StringVar()
        # Typing heuristics tracking
        self._exact_started_at = None
        self._typed_prev_text = ""
        self._typed_key_count = 0
        self._typed_backspaces = 0
        self._typed_largest_jump = 0
        self._typed_had_focus = False
        if self.exact_required:
            ttk.Label(self.container, text="Type the following exactly to confirm snooze:",
                      wraplength=460).grid(row=row, column=0, columnspan=2, sticky="w", **pad)
            row += 1

            # Pick target sentence (respect required phrase if enabled)
            required_phrase_on = bool(self.settings.get("snooze_exact_require_phrase", False))
            required_phrase = str(self.settings.get("snooze_exact_required_phrase", "I am snoozing")).strip()
            choices = list(self.sentence_choices) if self.sentence_choices else []
            if required_phrase_on and choices:
                filtered = [c for c in choices if required_phrase in c]
                if filtered:
                    choices = filtered
            if choices:
                self.target_sentence = random.choice(choices)
            else:
                # Fallbacks
                self.target_sentence = required_phrase if required_phrase_on else "I am choosing to pause my reminders deliberately."
            self._log(f"build_ui: exact field enabled target_summary={privacy_summary(self.target_sentence)} choices={len(self.sentence_choices)} require_phrase={required_phrase_on}")

            self.sentence_label = tk.Label(self.container, text=self.target_sentence, fg="#ddd", bg="#111",
                                           wraplength=460, justify="left")
            self.sentence_label.grid(row=row, column=0, columnspan=2, sticky="w", **pad)
            row += 1

            self.typed_entry = ttk.Entry(self.container, textvariable=self.typed_var, width=58)
            self.typed_entry.grid(row=row, column=0, columnspan=2, sticky="we", **pad)
            self._focus_order.append(self.typed_entry)
            row += 1

            # Paste prevention (optional)
            if self._prevent_paste:
                for seq in ("<Control-v>", "<Control-V>", "<Button-2>", "<Button-3>"):
                    try:
                        self.typed_entry.bind(seq, lambda e: "break")
                    except Exception:
                        pass

            # Typing event tracking for heuristics
            def _on_focus_in(_e=None):
                if self._exact_started_at is None:
                    self._exact_started_at = self._monotonic_clock()
                self._typed_had_focus = True
            def _on_keypress(e=None):
                # Count only real key presses
                self._typed_key_count += 1
                try:
                    if getattr(e, 'keysym', '') in ('BackSpace', 'Delete'):
                        self._typed_backspaces += 1
                except Exception:
                    pass
            def _on_change(*_):
                try:
                    cur = self.typed_var.get() or ""
                    jump = abs(len(cur) - len(self._typed_prev_text))
                    if jump > self._typed_largest_jump:
                        self._typed_largest_jump = jump
                    self._typed_prev_text = cur
                except Exception:
                    pass
            try:
                self.typed_entry.bind('<FocusIn>', _on_focus_in, add=True)
                self.typed_entry.bind('<KeyPress>', _on_keypress, add=True)
                self.typed_var.trace_add('write', _on_change)
            except Exception:
                pass

            tk.Label(self.container, text="No copy-paste. Type the sentence manually.", fg="#888", bg="#111").grid(
                row=row, column=0, columnspan=2, sticky="w", **pad
            )
            row += 1

        else:
            self._log("build_ui: exact field disabled")

        # Buttons
        btns = ttk.Frame(self.container)
        btns.grid(row=row, column=0, columnspan=2, sticky="e", padx=8, pady=(8, 8))
        self.confirm_btn = ttk.Button(btns, text="Snooze", command=self._finish)
        self.confirm_btn.pack(side="right")
        self.cancel_btn = ttk.Button(btns, text="Cancel", command=self._cancel)
        self.cancel_btn.pack(side="right", padx=6)
        self._focus_order.extend([self.confirm_btn, self.cancel_btn])

    # ----- Helpers -----
    def _normalize_sentence_list(self, value):
        if not isinstance(value, list):
            return []
        out = []
        for s in value:
            try:
                t = str(s).strip()
                if t:
                    out.append(t)
            except Exception:
                continue
        return out

    def _init_spam_detector(self):
        logger = get_logger()
        force_all = bool(self.settings.get("snooze_exact_force_all_heuristics", False))
        if not is_spam_detection_enabled(self.settings) and not force_all:
            logger.info("spam_check: skipped because disabled")
            self.spam_detector = None
            return

        logger.info("spam_check: running because enabled")
        if force_all:
            config = {
                "enable_gibberish_detection": True,
                "min_vowel_ratio": self.settings.get("spam_min_vowel_ratio", 0.2),
                "max_vowel_ratio": self.settings.get("spam_max_vowel_ratio", 0.7),
                "min_unique_char_ratio": self.settings.get("spam_min_unique_char_ratio", 0.4),
                "enable_repetition_check": True,
                "max_consecutive_chars": self.settings.get("spam_max_consecutive_chars", 2),
                "max_pattern_repetition": self.settings.get("spam_max_pattern_repetition", 3),
                "enable_spacing_check": True,
                "min_length_require_spaces": self.settings.get("spam_min_length_require_spaces", 15),
                "enable_keyboard_pattern_check": True,
                "min_keyboard_sequence_length": self.settings.get("spam_min_keyboard_sequence_length", 4),
                "enable_dictionary_check": True,
                "min_real_word_ratio": self.settings.get("spam_min_real_word_ratio", 0.6),
                "min_word_length": self.settings.get("spam_min_word_length", 2),
                "enable_timing_check": True,
                "min_time_to_submit": self.settings.get("spam_min_time_to_submit", 3),
                "flag_if_under": self.settings.get("spam_flag_if_under", 2),
                "banned_words": self.settings.get("spam_banned_words", ["idk", "dunno", "meh", "whatever"]),
                "vague_words": self.settings.get("spam_vague_words", ["stuff", "things", "something", "nothing"]),
            }
        else:
            config = {
                "enable_gibberish_detection": self.settings.get("spam_gibberish_detection", True),
                "min_vowel_ratio": self.settings.get("spam_min_vowel_ratio", 0.2),
                "max_vowel_ratio": self.settings.get("spam_max_vowel_ratio", 0.7),
                "min_unique_char_ratio": self.settings.get("spam_min_unique_char_ratio", 0.4),
                "enable_repetition_check": self.settings.get("spam_repetition_check", True),
                "max_consecutive_chars": self.settings.get("spam_max_consecutive_chars", 2),
                "max_pattern_repetition": self.settings.get("spam_max_pattern_repetition", 3),
                "enable_spacing_check": self.settings.get("spam_spacing_check", True),
                "min_length_require_spaces": self.settings.get("spam_min_length_require_spaces", 15),
                "enable_keyboard_pattern_check": self.settings.get("spam_keyboard_pattern_check", True),
                "min_keyboard_sequence_length": self.settings.get("spam_min_keyboard_sequence_length", 4),
                "enable_dictionary_check": self.settings.get("spam_dictionary_check", True),
                "min_real_word_ratio": self.settings.get("spam_min_real_word_ratio", 0.6),
                "min_word_length": self.settings.get("spam_min_word_length", 2),
                "enable_timing_check": self.settings.get("spam_timing_check", True),
                "min_time_to_submit": self.settings.get("spam_min_time_to_submit", 3),
                "flag_if_under": self.settings.get("spam_flag_if_under", 2),
                "banned_words": self.settings.get("spam_banned_words", ["idk", "dunno", "meh", "whatever"]),
                "vague_words": self.settings.get("spam_vague_words", ["stuff", "things", "something", "nothing"]),
            }
        logger.info("spam_check: config=%s", config)
        self.spam_detector = SpamDetector(config)

    def _center_on_parent(self):
        try:
            self.update_idletasks()
            parent = self.master
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            w = self.winfo_width()
            h = self.winfo_height()
            x = px + max(0, (pw - w) // 2)
            y = py + max(0, (ph - h) // 2)
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def _center_on_screen(self):
        try:
            self.update_idletasks()
            width = self.winfo_width()
            height = self.winfo_height()
            if width <= 1 or height <= 1:
                width = max(width, 400)
                height = max(height, 240)
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            x = max(0, (screen_width - width) // 2)
            y = max(0, (screen_height - height) // 3)
            self.geometry(f"{width}x{height}+{x}+{y}")
            self._log(f"center_on_screen: width={width} height={height} x={x} y={y}")
        except Exception:
            pass

    def _set_initial_focus(self):
        try:
            self.lift()
            self.focus_force()
        except Exception:
            pass
        # Focus the first box (reason)
        try:
            if self.reason_entry and self.reason_entry.winfo_exists():
                self.reason_entry.focus_set()
                self.reason_entry.selection_range(0, tk.END)
        except Exception:
            pass

    def _ensure_visible(self):
        try:
            # Force window to be visible and on top
            self.deiconify()
            self.lift()
            self.focus_force()
            if bool(self.settings.get("always_on_top", True)):
                self.attributes("-topmost", True)

            # Center the window on the main screen
            self._center_on_screen()
            self.update_idletasks()

            # Log final state
            geom = self.winfo_geometry()
            visible = bool(self.winfo_viewable())
            self._log(f"ensure_visible: viewable={visible} geom={geom}")
        except Exception as e:
            self._log(f"ensure_visible: FAILED - {e}")

    def _cancel_pending_timers(self):
        timers = getattr(self, "_timers", None)
        if timers is not None:
            timers.close()
            for attr in ("_ensure_visible_timer_id", "_initial_focus_timer_id"):
                try:
                    setattr(self, attr, None)
                except Exception:
                    pass
            return

        for attr in ("_ensure_visible_timer_id", "_initial_focus_timer_id"):
            timer_id = getattr(self, attr, None)
            if timer_id is None:
                continue
            try:
                self.after_cancel(timer_id)
            except Exception:
                pass
            try:
                setattr(self, attr, None)
            except Exception:
                pass

    # ----- Validation -----
    def _validate_reason(self):
        reason = (self.reason_var.get() or "").strip()
        self._log(f"validate_reason: required={self.reason_required} len={len(reason)} text_summary={privacy_summary(reason)}")
        if self.reason_required and not reason:
            self._log("validate_reason: missing input while required")
            messagebox.showerror("Required", "Please answer why you're snoozing before continuing.")
            try:
                self.reason_entry.focus_set()
            except Exception:
                pass
            return False
        if self.spam_detector and self.settings.get("snooze_prompt_validation_enabled", True):
            elapsed = self._monotonic_clock() - self._dialog_shown_at
            ok, msg = self.spam_detector.is_valid_response(reason, elapsed)
            if not ok:
                self._log(f"validate_reason: spam detector rejection -> {privacy_summary(msg)}")
                get_logger().warning("spam_check: rejected | reason=%s", msg)
                messagebox.showerror("Invalid Response", msg)
                try:
                    self.reason_entry.focus_set()
                except Exception:
                    pass
                return False
        if bool(self.settings.get("snooze_exact_require_phrase", False)):
            phrase = str(self.settings.get("snooze_exact_required_phrase", "I am snoozing")).strip()
            comp_reason = reason if self._case_sensitive else reason.lower()
            comp_phrase = phrase if self._case_sensitive else phrase.lower()
            if comp_phrase and comp_phrase not in comp_reason:
                self._log(f"validate_reason: required phrase_summary={privacy_summary(phrase)} missing")
                messagebox.showerror("Phrase required", f"Please include '{phrase}' in your reason.")
                try:
                    if self.reason_entry and self.reason_entry.winfo_exists():
                        self.reason_entry.focus_set()
                except Exception:
                    pass
                return False
        self._log("validate_reason: passed")
        return True

    def _finish(self):
        self._log("finish: validating inputs")
        # Validate reason first
        if not self._validate_reason():
            self._log("finish: reason validation failed")
            return

        # Validate exact typing if enabled
        if self.exact_required:
            want = (self.target_sentence or "")
            have = (self.typed_var.get() or "")
            if not self._case_sensitive:
                want = want.lower()
                have = have.lower()
            if not want or have != want:
                self._log("finish: exact mismatch")
                messagebox.showerror("Doesn't match", "Please type the sentence exactly as shown.")
                try:
                    if hasattr(self, 'typed_entry') and self.typed_entry.winfo_exists():
                        self.typed_entry.focus_set()
                except Exception:
                    pass
                return

            # Heuristic checks: time, keypresses, jump size, focus
            try:
                elapsed = (self._monotonic_clock() - (self._exact_started_at or self._dialog_shown_at))
            except Exception:
                elapsed = 0.0
            # thresholds (hidden settings with sensible defaults)
            min_time_base = float(self.settings.get("snooze_exact_min_time_seconds", 2))
            time_per_char = float(self.settings.get("snooze_exact_time_per_char", 0.03))
            min_time_required = max(min_time_base, len(want) * time_per_char)
            if elapsed < min_time_required:
                self._log(f"finish: typing too fast elapsed={elapsed:.2f} min_required={min_time_required:.2f}")
                messagebox.showerror(
                    "Too fast",
                    "Slow down and type the sentence deliberately."
                )
                try:
                    if hasattr(self, 'typed_entry') and self.typed_entry.winfo_exists():
                        self.typed_entry.focus_set()
                except Exception:
                    pass
                return

            min_keypress_ratio = float(self.settings.get("snooze_exact_min_keypress_ratio", 0.8))
            min_keys = int(len(want) * min_keypress_ratio)
            if self._typed_key_count < max(1, min_keys):
                self._log(f"finish: insufficient keypresses count={self._typed_key_count} required={min_keys}")
                messagebox.showerror(
                    "Looks automated",
                    "Please type the sentence fully on your keyboard."
                )
                try:
                    if hasattr(self, 'typed_entry') and self.typed_entry.winfo_exists():
                        self.typed_entry.focus_set()
                except Exception:
                    pass
                return

            max_jump = int(self.settings.get("snooze_exact_max_jump_chars", 3))
            if self._typed_largest_jump > max_jump:
                self._log(f"finish: jump too large jump={self._typed_largest_jump} limit={max_jump}")
                messagebox.showerror(
                    "Entered too quickly",
                    "Too many characters appeared at once; please type normally."
                )
                try:
                    if hasattr(self, 'typed_entry') and self.typed_entry.winfo_exists():
                        self.typed_entry.focus_set()
                except Exception:
                    pass
                return

            if bool(self.settings.get("snooze_exact_require_focus_during_typing", True)) and not self._typed_had_focus:
                self._log("finish: typing field never had focus")
                messagebox.showerror(
                    "Not typed here",
                    "Please click the box and type the sentence here."
                )
                try:
                    if hasattr(self, 'typed_entry') and self.typed_entry.winfo_exists():
                        self.typed_entry.focus_set()
                except Exception:
                    pass
                return

        # Success
        self._cancel_pending_timers()
        try:
            self.grab_release()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
        self._log("finish: dialog completed successfully")
        try:
            if callable(self.on_submit):
                payload = {
                    "reason": (self.reason_var.get() or "").strip(),
                    "typed": (self.typed_var.get() or "").strip(),
                    "sentence": self.target_sentence or "",
                }
                self.on_submit(payload)
        except Exception:
            pass

    def _cancel(self):
        self._log("cancel: user dismissed dialog")
        self._cancel_pending_timers()
        try:
            self.grab_release()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
        try:
            if callable(self.on_cancel):
                self.on_cancel()
        except Exception:
            pass

    # ----- Key handlers -----
    def _on_return(self, _event):
        # Only submit if focus is on last entry (typed) or confirm button; else do nothing
        focused = self.focus_get()
        if self.exact_required:
            if focused == getattr(self, 'typed_entry', None) or focused == getattr(self, 'confirm_btn', None):
                self._finish()
                return "break"
        else:
            # If only reason field is shown, allow Enter on reason to submit.
            if focused == self.reason_entry or focused == getattr(self, 'confirm_btn', None) or not self.reason_required:
                self._finish()
                return "break"
        return None

    def _on_escape(self, _event):
        self._cancel()
        return "break"


__all__ = ["SnoozePromptDialog"]

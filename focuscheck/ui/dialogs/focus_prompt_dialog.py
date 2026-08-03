"""
Dialog shown when user confirms 'Studying' to capture focus details.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import time

from .spam_detection import SpamDetector
from ...settings.gates import is_spam_detection_enabled
from .challenge_system import create_challenge_system
from ...utils.timers import TimerRegistry

try:
    from ...utils import get_logger
except Exception:  # pragma: no cover - fallback
    def get_logger():
        import logging
        return logging.getLogger(__name__)


class FocusPromptDialog(tk.Toplevel):
    """Dialog shown when the user confirms 'Studying' if enabled.
    Captures what they're working on and optionally the benefits.
    Requires at least one field by default, with an option to require every prompt.
    """

    def __init__(self, master, ask_doing=True, ask_benefits=True, on_submit=None, on_cancel=None, auto_focus=True, require_all_fields=False, settings=None, monotonic_clock=None):
        super().__init__(master)
        self.title("Before you continue")
        self.configure(bg="#111")
        self.resizable(False, False)
        self.on_submit = on_submit
        self.on_cancel = on_cancel
        self.ask_doing = bool(ask_doing)
        self.ask_benefits = bool(ask_benefits)
        self._auto_focus = bool(auto_focus)
        self.require_all_fields = bool(require_all_fields)
        self._focus_order = []
        self._field_controls = []
        self._timers = TimerRegistry(self)
        self._monotonic_clock = monotonic_clock if callable(monotonic_clock) else time.monotonic
        self._dialog_shown_at = self._monotonic_clock()

        # Initialize spam detector with settings
        self.settings = settings or {}
        self._init_spam_detector()

        # Initialize challenge system
        self._init_challenge_system()

        try:
            self.transient(master)
        except Exception:
            pass

        pad = {"padx": 8, "pady": 4}
        self.doing_var = tk.StringVar()
        row = 0
        if self.ask_doing:
            # Check if we have a challenge
            if self.active_challenge:
                doing_prompt = self.active_challenge["question"]
            else:
                doing_prompt = "What are you doing right now?"

            ttk.Label(self, text=doing_prompt, wraplength=450).grid(row=row, column=0, columnspan=2, sticky="w", **pad)
            row += 1

            # Show hint if challenge present and hints enabled
            if self.active_challenge and self.settings.get("challenge_show_hints", True):
                hint = self.challenge_system.get_challenge_hint(self.active_challenge)
                if hint:
                    hint_label = ttk.Label(self, text=f"Hint: {hint}", foreground="gray", wraplength=450)
                    hint_label.grid(row=row, column=0, columnspan=2, sticky="w", **pad)
                    row += 1

            doing_entry = ttk.Entry(self, textvariable=self.doing_var, width=56)
            doing_entry.grid(row=row, column=0, columnspan=2, sticky="we", **pad)
            self._focus_order.append(doing_entry)
            self._field_controls.append({
                "key": "doing",
                "label": doing_prompt,
                "var": self.doing_var,
                "entry": doing_entry,
                "challenge": self.active_challenge,  # Store challenge with field
            })
            row += 1

        self.benefits_var = tk.StringVar()
        if self.ask_benefits:
            benefits_prompt = "What are the benefits of this?"
            ttk.Label(self, text=benefits_prompt).grid(row=row, column=0, sticky="w", **pad)
            benefits_entry = ttk.Entry(self, textvariable=self.benefits_var, width=56)
            benefits_entry.grid(row=row, column=1, sticky="we", **pad)
            self._focus_order.append(benefits_entry)
            self._field_controls.append({
                "key": "benefits",
                "label": benefits_prompt,
                "var": self.benefits_var,
                "entry": benefits_entry,
            })
            row += 1
        btn_row = row

        btns = ttk.Frame(self)
        btns.grid(row=btn_row, column=0, columnspan=2, sticky="e", padx=8, pady=(8, 8))
        self.continue_btn = ttk.Button(btns, text="Continue", command=self._save)
        self.continue_btn.pack(side="right")
        self.cancel_btn = ttk.Button(btns, text="Cancel", command=self._cancel)
        self.cancel_btn.pack(side="right", padx=6)

        self._focus_order.extend([self.continue_btn, self.cancel_btn])

        for widget in self._focus_order:
            try:
                widget.configure(takefocus=True)
            except tk.TclError:
                pass

        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Return>", self._on_return, add=True)
        self.bind("<KP_Enter>", self._on_return, add=True)
        self.bind("<Escape>", self._on_escape, add=True)

        if self._auto_focus:
            self._timers.schedule("initial-focus", 0, self._set_initial_focus)

    def destroy(self):
        timers = getattr(self, "_timers", None)
        if timers is not None:
            timers.close()
        return super().destroy()

    def close(self):
        """Close from an owning prompt interruption without notifying it."""
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def _init_spam_detector(self):
        """Initialize spam detector with settings configuration."""
        logger = get_logger()
        if not is_spam_detection_enabled(self.settings):
            logger.info("spam_check: skipped because disabled")
            self.spam_detector = None
            return

        logger.info("spam_check: running because enabled")
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

    def _init_challenge_system(self):
        """Initialize challenge system and select challenge if enabled."""
        if not self.settings.get("challenge_system_enabled", True):
            self.challenge_system = None
            self.active_challenge = None
            return

        self.challenge_system = create_challenge_system(self.settings)

        # Select a challenge for "studying" context
        self.active_challenge = self.challenge_system.get_challenge(context="studying")

    def _cancel(self):
        try:
            self.grab_release()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            try:
                get_logger().exception("focus prompt destruction failed", exc_info=True)
            except Exception:
                pass
        try:
            if self.on_cancel:
                self.on_cancel()
        except Exception:
            pass

    def _save(self):
        doing = (self.doing_var.get() or "").strip() if self.ask_doing else ""
        benefits = (self.benefits_var.get() or "").strip() if self.ask_benefits else ""

        # Validate fields based on require_all_fields setting and challenge requirements
        if self._field_controls:
            for ctrl in self._field_controls:
                value = (ctrl["var"].get() or "").strip()

                # Check if this field should be required:
                # - Always required if it has a challenge
                # - Otherwise required only if require_all_fields setting is True
                has_challenge = bool(ctrl.get("challenge"))
                should_require = has_challenge or self.require_all_fields

                if should_require and not value:
                    messagebox.showerror("Required", f"Please answer \"{ctrl['label']}\" before continuing.")
                    self._focus_widget(ctrl.get("entry"))
                    return

                # Skip remaining validation if field is empty and not required
                if not value:
                    continue

                # Challenge validation FIRST (if challenge present for this field)
                if ctrl.get("challenge") and self.challenge_system:
                    is_valid, error_msg = self.challenge_system.validate_challenge_response(
                        value, ctrl["challenge"]
                    )
                    if not is_valid:
                        messagebox.showerror("Challenge Requirement Not Met", error_msg)
                        self._focus_widget(ctrl.get("entry"))
                        return

                # Spam detection for each field
                if self.spam_detector:
                    time_elapsed = self._monotonic_clock() - self._dialog_shown_at
                    is_valid, error_msg = self.spam_detector.is_valid_response(value, time_elapsed)
                    if not is_valid:
                        get_logger().warning("spam_check: rejected | reason=%s", error_msg)
                        messagebox.showerror("Invalid Response", error_msg)
                        self._focus_widget(ctrl.get("entry"))
                        return

        payload = {"doing": doing, "benefits": benefits}
        try:
            self.grab_release()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            try:
                get_logger().exception("focus prompt destruction failed", exc_info=True)
            except Exception:
                pass
        try:
            if self.on_submit:
                self.on_submit(payload)
        except Exception:
            pass

    def _set_initial_focus(self):
        try:
            self.lift()
        except Exception:
            pass
        try:
            self.focus_force()
        except Exception:
            pass
        for widget in self._focus_order:
            try:
                if widget and widget.winfo_exists():
                    widget.focus_set()
                    if hasattr(widget, "selection_range"):
                        try:
                            widget.selection_range(0, tk.END)
                        except Exception:
                            pass
                    break
            except Exception:
                continue

    def _focus_widget(self, widget):
        try:
            self.lift()
        except Exception:
            pass
        try:
            self.focus_force()
        except Exception:
            pass
        try:
            if widget and widget.winfo_exists():
                widget.focus_set()
                if hasattr(widget, "selection_range"):
                    try:
                        widget.selection_range(0, tk.END)
                    except Exception:
                        pass
        except Exception:
            pass

    def _on_return(self, event):
        # Only trigger save if focus is on the last entry field or the continue button
        focused = self.focus_get()
        if focused == self.continue_btn:
            self._save()
            return "break"
        # Check if focus is on the last entry field
        if self._field_controls and focused == self._field_controls[-1].get("entry"):
            self._save()
            return "break"
        # Otherwise, let Tab navigation handle it (don't trigger save)
        return None

    def _on_escape(self, _event):
        self._cancel()
        return "break"

"""
Anti-habit mixin for PromptDialog.

Contains methods for implementing anti-habit behavior including
press-and-hold requirements for button confirmation.
"""

import time
import random

try:
    from ....utils import log_exception
except ImportError:
    def log_exception(msg):
        pass

try:
    from ....settings.manager import save_settings
except ImportError:
    save_settings = None  # Fallback if import fails

try:
    from ....database import append_focus_log, append_waste_log
except ImportError:
    def append_focus_log(**kwargs):
        pass
    def append_waste_log(**kwargs):
        pass


class AntiHabitMixin:
    """Mixin for anti-habit functionality in PromptDialog."""

    def _study_hold_start(self, _evt):
        """
        Handle press start for studying button.

        Args:
            _evt: Mouse button press event
        """
        if not self.settings["anti_habit_enabled"]:
            return
        self._hold_start = getattr(self, "_monotonic_now", time.monotonic)()
        try:
            self._info_lbl.config(text="Hold to confirm you're actively studying.")
        except Exception:
            pass
        self._info_lbl.config(text="Hold to confirm you're actively studying.")

    def _study_hold_end(self, _evt):
        """
        Handle press release for studying button.

        Validates hold duration and triggers studying choice if held long enough.

        Args:
            _evt: Mouse button release event
        """
        if not self.settings["anti_habit_enabled"]:
            self._trigger_studying_choice()
            return
        if self._hold_start is None:
            return
        held_ms = int((getattr(self, "_monotonic_now", time.monotonic)() - self._hold_start) * 1000)
        self._hold_start = None
        need = int(self.settings["studying_hold_ms"])
        if held_ms >= need:
            self._trigger_studying_choice()
        else:
            try:
                self._info_lbl.config(text="Too quick ({}ms). Hold for at least {}ms.".format(held_ms, need))
            except Exception:
                pass
            return

    def _trigger_studying_choice(self):
        """
        Trigger the studying choice flow.

        If phrase acronym challenge is enabled, shows that instead.
        Otherwise, if any focus questions are enabled, shows the focus prompt dialog.
        Otherwise, directly finishes with "Studying" choice.
        """
        # Check if acronym challenge is enabled
        if bool(self.settings.get("phrase_acronym_enabled", False)):
            self._show_acronym_challenge("study")
            return

        ask_doing = bool(self.settings.get("focus_prompt_ask_doing", True))
        ask_benefits = bool(self.settings.get("focus_prompt_ask_benefits", True))

        # Only show prompt if at least one question is enabled
        try:
            if not (ask_doing or ask_benefits):
                self._finish("Studying")
                return
        except Exception:
            self._finish("Studying")
            return

        def _on_submit(payload):
            self._focus_prompt_open = False
            try:
                doing = (payload or {}).get("doing", "").strip()
                benefits = (payload or {}).get("benefits", "").strip()
                active = None
                if self.taskdb:
                    try:
                        active = self.taskdb.get_active()
                    except Exception:
                        active = None
                try:
                    if self.taskdb:
                        self.taskdb.record_focus_event(
                            doing=doing,
                            benefits=benefits,
                            active_task_id=(active.get("id") if active else None)
                        )
                except Exception:
                    log_exception("focus prompt: DB record failed")
                try:
                    latency_ms = int((getattr(self, "_monotonic_now", time.monotonic)() - self.start_monotonic) * 1000)
                    append_focus_log(
                        slot_start_dt=self.slot_start_dt,
                        latency_ms=latency_ms,
                        doing=doing,
                        benefits=benefits,
                        active_task=active,
                        clock=getattr(self, "_task_clock", None),
                    )
                except Exception:
                    log_exception("focus prompt: CSV append failed")
            finally:
                self._finish("Studying")

        def _on_cancel():
            self._focus_prompt_open = False

        self._focus_prompt_open = True
        # Import FocusPromptDialog locally to avoid circular imports
        from ..focus_prompt_dialog import FocusPromptDialog
        FocusPromptDialog(
            self,
            ask_doing=ask_doing,
            ask_benefits=ask_benefits,
            on_submit=_on_submit,
            on_cancel=_on_cancel,
            auto_focus=self._modal_auto_focus_enabled(),
            require_all_fields=bool(self.settings.get("prompt_require_all_fields", False)),
            settings=self.settings,
        )

    def _waste_hold_start(self, _evt):
        """
        Handle press start for wasting button.

        Args:
            _evt: Mouse button press event
        """
        if not self.settings["anti_habit_enabled"]:
            self._on_wasting_clicked(); return
        self._hold_start = getattr(self, "_monotonic_now", time.monotonic)()
        try:
            self._info_lbl.config(text="Hold to confirm you're wasting time...")
        except Exception:
            pass

    def _waste_hold_end(self, _evt):
        """
        Handle press release for wasting button.

        Validates hold duration and triggers wasting choice if held long enough.

        Args:
            _evt: Mouse button release event
        """
        if not self.settings["anti_habit_enabled"]:
            self._on_wasting_clicked(); return
        if self._hold_start is None:
            return
        held_ms = int((getattr(self, "_monotonic_now", time.monotonic)() - self._hold_start) * 1000)
        self._hold_start = None
        need = int(self.settings["studying_hold_ms"])
        if held_ms >= need:
            self._on_wasting_clicked()
        else:
            # Inform user to hold longer
            try:
                self._info_lbl.config(text=f"Too quick ({held_ms}ms). Hold for at least {need}ms.")
            except Exception:
                pass

    def _on_wasting_clicked(self):
        """
        Handle wasting button click.

        If phrase acronym challenge is enabled, shows that instead.
        Otherwise, if any wasting questions are enabled, shows the waste prompt dialog.
        Otherwise, directly finishes with "Wasting time" choice.
        """
        # Check if acronym challenge is enabled
        if bool(self.settings.get("phrase_acronym_enabled", False)):
            self._show_acronym_challenge("waste")
            return

        # Get question settings
        try:
            ask_cons = bool(self.settings.get("wasting_prompt_ask_consequences", True))
        except Exception:
            ask_cons = True
        try:
            ask_what = bool(self.settings.get("wasting_prompt_ask_what", True))
        except Exception:
            ask_what = True

        # Only show prompt if at least one question is enabled
        try:
            if not (ask_what or ask_cons):
                self._finish("Wasting time")
                return
        except Exception:
            self._finish("Wasting time")
            return
        def _cb(payload):
            try:
                what = (payload or {}).get("what", "").strip()
                cons = (payload or {}).get("consequences", "").strip()
                active = None
                if self.taskdb:
                    try:
                        active = self.taskdb.get_active()
                    except Exception:
                        active = None
                # Persist to DB if available
                try:
                    if self.taskdb:
                        self.taskdb.record_waste_event(what=what, consequences=cons, active_task_id=(active.get("id") if active else None))
                except Exception:
                    log_exception("waste prompt: DB record failed")
                # Also record to CSV for quick export
                try:
                    latency_ms = int((getattr(self, "_monotonic_now", time.monotonic)() - self.start_monotonic) * 1000)
                    append_waste_log(
                        slot_start_dt=self.slot_start_dt,
                        latency_ms=latency_ms,
                        what=what,
                        consequences=cons,
                        active_task=active,
                        clock=getattr(self, "_task_clock", None),
                    )
                except Exception:
                    log_exception("waste prompt: CSV append failed")
            finally:
                self._finish("Wasting time")
        def _on_cancel():
            # Cancel just closes the waste prompt, returns to main dialog
            # Don't call _finish() - let user choose again
            pass
        # Import WastePromptDialog locally to avoid circular imports
        from ..waste_prompt_dialog import WastePromptDialog
        WastePromptDialog(
            self,
            ask_what=ask_what,
            ask_consequences=ask_cons,
            on_submit=_cb,
            on_cancel=_on_cancel,
            auto_focus=self._modal_auto_focus_enabled(),
            require_all_fields=bool(self.settings.get("prompt_require_all_fields", False)),
            settings=self.settings,
        )

    def _show_acronym_challenge(self, button_type):
        """
        Show the phrase acronym challenge dialog.

        Args:
            button_type: "study" or "waste" to determine which phrase list to use
        """
        # Get phrase for this button type
        phrase = self._get_phrase_for_button(button_type)

        if not phrase:
            # No phrase available - just finish directly
            choice = "Studying" if button_type == "study" else "Wasting time"
            self._finish(choice)
            return

        # Define completion callback
        def _on_complete():
            choice = "Studying" if button_type == "study" else "Wasting time"
            self._finish(choice)

        # Import and show acronym dialog
        from ..phrase_acronym_dialog import PhraseAcronymDialog
        PhraseAcronymDialog(
            self,
            phrase=phrase,
            on_complete=_on_complete,
            settings=self.settings
        )

    def _get_phrase_for_button(self, button_type):
        """
        Get phrase for button based on settings mode (random, sequential, or override).

        Args:
            button_type: "study" or "waste"

        Returns:
            Selected phrase string, or empty string if no phrases available
        """
        # Respect classic labels unless custom phrases explicitly enabled
        if not self.settings.get("custom_button_phrases_enabled", False):
            return "Studying" if button_type == "study" else "Wasting time"

        prefix = button_type  # "study" or "waste"
        mode = self.settings.get(f"{prefix}_phrase_mode", "random")

        # Override mode - use single phrase
        if mode == "override":
            override = self.settings.get(f"{prefix}_phrase_override", "")
            return override.strip()

        # Get phrase list
        phrase_list = self.settings.get(f"{prefix}_phrase_list", [])
        if not phrase_list:
            return ""

        # Random mode
        if mode == "random":
            return random.choice(phrase_list)

        # Sequential mode
        elif mode == "sequential":
            index = self.settings.get(f"{prefix}_phrase_index", 0)
            phrase = phrase_list[index % len(phrase_list)]

            next_index = (index + 1) % len(phrase_list)
            persist = getattr(self, "persist_settings", None)
            if callable(persist):
                # Keep the shared App snapshot unchanged until the durable
                # callback accepts the complete draft and returns committed state.
                candidate = dict(self.settings)
                candidate[f"{prefix}_phrase_index"] = next_index
                try:
                    result = persist(candidate)
                    committed = getattr(result, "committed_settings", None)
                    if result and isinstance(committed, dict):
                        self.settings.update(committed)
                except Exception:
                    pass
            else:
                # Standalone dialogs retain the historical compatibility path.
                self.settings[f"{prefix}_phrase_index"] = next_index
                try:
                    if save_settings:
                        save_settings(self.settings)
                except Exception:
                    pass

            return phrase

        # Fallback - return first phrase
        return phrase_list[0] if phrase_list else ""

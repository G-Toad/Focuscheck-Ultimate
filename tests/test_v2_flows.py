"""V2 prompt state transition regressions."""

from __future__ import annotations

import unittest
from unittest import mock
from datetime import datetime, timezone

from focuscheck.utils.clock import FakeClock


class Var:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class Entry:
    def __init__(self):
        self.focused = False

    def focus_set(self):
        self.focused = True


class AppRef:
    def __init__(self):
        self._intervention_active = False
        self.root = object()


class V2FlowTests(unittest.TestCase):
    def test_prompt_duration_uses_composed_monotonic_clock(self):
        from focuscheck.ui.dialogs.prompt_dialog import PromptDialog
        from focuscheck.ui.dialogs.v2_prompt_dialog import V2PromptDialog

        clock = FakeClock(datetime(2030, 1, 1, tzinfo=timezone.utc))
        v1 = PromptDialog.__new__(PromptDialog)
        v1._task_clock = clock
        v2 = V2PromptDialog.__new__(V2PromptDialog)
        v2._task_clock = clock

        self.assertEqual(0.0, v1._monotonic_now())
        self.assertEqual(0.0, v2._monotonic_now())
        clock.advance(2.5)
        self.assertEqual(2.5, v1._monotonic_now())
        self.assertEqual(2.5, v2._monotonic_now())

    def test_standalone_v2_suppresses_active_snooze_but_allows_expired_snooze(self):
        from focuscheck.monitoring.engine_v2 import EngineV2

        class App:
            _current_prompt = None
            _intervention_active = False
            guard = None
            settings = {}

        engine = EngineV2.__new__(EngineV2)
        engine.app = App()
        engine._subpopup_active = False
        engine._settings = {
            "snooze_until_utc": "2030-01-01T00:05:00+00:00",
            "pause_when_inactive_or_lid_closed": False,
        }
        engine._activity_clock = lambda: datetime(2030, 1, 1, tzinfo=timezone.utc)

        self.assertFalse(engine._should_check_subpopup())
        engine._settings["snooze_until_utc"] = "2029-12-31T23:55:00+00:00"
        self.assertTrue(engine._should_check_subpopup())

    def test_disabled_website_flags_do_not_query_activity_provider(self):
        from focuscheck.monitoring.engine_v2 import EngineV2

        engine = EngineV2.__new__(EngineV2)
        engine.app = AppRef()
        engine._settings = {
            "website_flags": [{"domain": "example.com", "enabled": False}],
        }
        engine._get_activity_info = mock.Mock()

        engine._maybe_show_subpopup()

        engine._get_activity_info.assert_not_called()

    def test_settings_disable_website_polling_cancels_existing_timer(self):
        from focuscheck.monitoring.engine_v2 import EngineV2

        engine = EngineV2.__new__(EngineV2)
        engine._settings = {}
        engine._timers = mock.Mock()
        engine.on_settings_updated({
            "website_flags": [{"domain": "example.com", "enabled": False}],
        })

        engine._timers.cancel.assert_called_once_with("website-subpopup")

    def test_pause_transition_cancels_and_resumes_website_polling(self):
        from focuscheck.monitoring.engine_v2 import EngineV2

        engine = EngineV2.__new__(EngineV2)
        engine._settings = {"website_flags": [{"domain": "example.com", "enabled": True}]}
        engine._timers = mock.Mock(closed=False)

        engine.on_pause_changed(True, source="manual_pause")
        engine._timers.cancel.assert_called_once_with("website-subpopup")

        engine.on_pause_changed(False, source="resume")
        engine._timers.schedule.assert_called_once_with(
            "website-subpopup", 3000, engine._subpopup_tick, interval_ms=3000
        )

    def test_intervention_transition_cancels_and_resumes_website_polling(self):
        from focuscheck.monitoring.engine_v2 import EngineV2

        engine = EngineV2.__new__(EngineV2)
        engine._settings = {"website_flags": [{"domain": "example.com", "enabled": True}]}
        engine._timers = mock.Mock(closed=False)

        engine.on_intervention_changed(True, source="intervention_started")
        engine._timers.cancel.assert_called_once_with("website-subpopup")

        engine.on_intervention_changed(False, source="intervention_ended")
        engine._timers.schedule.assert_called_once_with(
            "website-subpopup", 3000, engine._subpopup_tick, interval_ms=3000
        )

    def test_v1_anti_habit_hold_uses_composed_monotonic_clock(self):
        from focuscheck.ui.dialogs.prompt_dialog_mixins.anti_habit import AntiHabitMixin

        clock = FakeClock(datetime(2030, 1, 1, tzinfo=timezone.utc))

        class Prompt(AntiHabitMixin):
            def __init__(self):
                self.settings = {"anti_habit_enabled": True, "studying_hold_ms": 500}
                self._hold_start = None
                self._info_lbl = mock.Mock()
                self._trigger_studying_choice = mock.Mock()
                self._monotonic_now = clock.monotonic

        prompt = Prompt()
        prompt._study_hold_start(None)
        clock.advance(0.5)
        prompt._study_hold_end(None)

        prompt._trigger_studying_choice.assert_called_once_with()

    def test_child_response_dialogs_accept_injected_monotonic_clock(self):
        from focuscheck.ui.dialogs.focus_prompt_dialog import FocusPromptDialog
        from focuscheck.ui.dialogs.waste_prompt_dialog import WastePromptDialog
        from focuscheck.ui.dialogs.snooze_prompt_dialog import SnoozePromptDialog

        clock = FakeClock(datetime(2030, 1, 1, tzinfo=timezone.utc))
        for dialog_type in (FocusPromptDialog, WastePromptDialog, SnoozePromptDialog):
            dialog = dialog_type.__new__(dialog_type)
            dialog._monotonic_clock = clock.monotonic
            dialog._dialog_shown_at = dialog._monotonic_clock()
            clock.advance(1.25)
            self.assertEqual(1.25, dialog._monotonic_clock() - dialog._dialog_shown_at)

    def _dialog(self, answer="doing work", decision="yes"):
        from focuscheck.ui.dialogs.v2_prompt_dialog import V2PromptDialog

        dialog = V2PromptDialog.__new__(V2PromptDialog)
        dialog.settings = {"overdrive_after_seconds": 60, "v2_hide_prompt_during_intervention": True}
        dialog.answer_var = Var(answer)
        dialog.intervention_var = Var(decision)
        dialog.answer_entry = Entry()
        dialog.intervention_entry = Entry()
        dialog.spam_detector = None
        dialog.app_ref = AppRef()
        dialog.activity_info = {}
        dialog.slot_start_dt = None
        dialog._closed = False
        dialog._submit_notified = False
        dialog.on_submit = mock.Mock()
        return dialog

    def test_intervention_exception_resets_app_state(self):
        dialog = self._dialog()
        dialog.deiconify = lambda: None
        dialog.lift = lambda: None
        dialog._force_window_to_front = lambda: None
        dialog.winfo_viewable = lambda: True

        class Wizard:
            _error_shown = True

            def __init__(self, _parent):
                pass

            def run(self, **_kwargs):
                raise RuntimeError("boom")

        with mock.patch("focuscheck.ui.dialogs.v2_prompt_dialog.InterventionWizard", Wizard):
            self.assertFalse(dialog._start_intervention())

        self.assertFalse(dialog.app_ref._intervention_active)

    def test_app_owned_intervention_runner_receives_prompt_context(self):
        dialog = self._dialog()
        dialog.app_ref.run_intervention = mock.Mock(return_value=True)
        dialog.winfo_viewable = lambda: True
        dialog._force_window_to_front = lambda: None

        self.assertTrue(dialog._start_intervention())
        dialog.app_ref.run_intervention.assert_called_once_with(
            dialog.settings,
            preselect_hwnd=None,
            preselect_title=None,
            prompt_ref=dialog,
            hide_prompt=True,
        )

    def test_off_thread_intervention_timeout_invalidates_v2_dispatch(self):
        from focuscheck.ui.dialogs import v2_prompt_dialog

        class Root:
            def __init__(self):
                self.callbacks = []

            def after(self, _delay, callback):
                self.callbacks.append(callback)
                return "dispatch"

            def after_cancel(self, _timer_id):
                return None

        class App:
            def __init__(self, root):
                self.root = root
                self._tk_thread_id = -1
                self.run_intervention = mock.Mock(return_value=True)

        dialog = self._dialog()
        root = Root()
        dialog.app_ref = App(root)
        dialog._closed = False
        dialog.deiconify = lambda: None
        dialog.lift = lambda: None
        dialog._force_window_to_front = lambda: None

        cancelled = mock.Mock()
        cancelled.wait.return_value = False
        cancelled.is_set.return_value = False

        with mock.patch.object(v2_prompt_dialog.threading, "get_ident", return_value=456), \
                mock.patch.object(v2_prompt_dialog.threading, "Event", return_value=cancelled), \
                mock.patch.object(v2_prompt_dialog.messagebox, "showinfo"):
            self.assertFalse(dialog._start_intervention())

        self.assertGreaterEqual(cancelled.set.call_count, 1)
        cancelled.is_set.return_value = True
        root.callbacks[0]()
        dialog.app_ref.run_intervention.assert_not_called()

    def test_intervention_log_summarizes_active_window_title(self):
        dialog = self._dialog()
        dialog.activity_info = {"hwnd": 123, "title": "private.example/secret-token"}
        dialog.winfo_viewable = lambda: True
        dialog._force_window_to_front = lambda: None

        class Wizard:
            def __init__(self, _parent, _settings):
                pass

            def run(self, **_kwargs):
                return True

        logger = mock.Mock()
        with mock.patch("focuscheck.ui.dialogs.v2_prompt_dialog.InterventionWizard", Wizard), \
                mock.patch("focuscheck.ui.dialogs.v2_prompt_dialog.get_logger", return_value=logger):
            self.assertTrue(dialog._start_intervention())

        logged = " ".join(str(call) for call in logger.info.call_args_list)
        self.assertNotIn("private.example/secret-token", logged)
        self.assertIn("title_summary", logged)

    def test_cancelled_intervention_does_not_log_or_close(self):
        dialog = self._dialog(decision="yes")
        dialog._start_intervention = lambda: False
        dialog._log_response = mock.Mock()
        dialog._close = mock.Mock()

        dialog._save()

        dialog._log_response.assert_not_called()
        dialog._close.assert_not_called()

    def test_no_intervention_logs_then_closes(self):
        dialog = self._dialog(decision="no")
        dialog._log_response = mock.Mock()
        dialog._close = mock.Mock()

        dialog._save()

        dialog._log_response.assert_called_once_with("no")
        dialog._close.assert_called_once()

    def test_close_notifies_app_once_for_reschedule(self):
        dialog = self._dialog(decision="no")
        dialog._cleanup_camera_feed = mock.Mock()
        dialog._flash_taskbar_stop = mock.Mock()
        dialog._cleanup_timers = mock.Mock()
        dialog.destroy = mock.Mock()

        dialog._close()
        dialog._close()

        dialog.on_submit.assert_called_once_with()
        dialog.destroy.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()

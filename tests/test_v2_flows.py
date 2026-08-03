"""V2 prompt state transition regressions."""

from __future__ import annotations

import unittest
from unittest import mock


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
            self.assertFalse(dialog._start_intervention_stub())

        self.assertFalse(dialog.app_ref._intervention_active)

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
            self.assertTrue(dialog._start_intervention_stub())

        logged = " ".join(str(call) for call in logger.info.call_args_list)
        self.assertNotIn("private.example/secret-token", logged)
        self.assertIn("title_summary", logged)

    def test_cancelled_intervention_does_not_log_or_close(self):
        dialog = self._dialog(decision="yes")
        dialog._start_intervention_stub = lambda: False
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

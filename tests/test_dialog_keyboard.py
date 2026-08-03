"""Keyboard behavior smoke tests for small Tk dialogs."""

from __future__ import annotations

import tkinter as tk
import unittest
from unittest import mock


def _make_root():
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        raise unittest.SkipTest(f"Tk display unavailable: {exc}") from exc
    root.withdraw()
    return root


class DialogKeyboardTests(unittest.TestCase):
    def test_snooze_reminder_yes_and_no_close_cleanly(self):
        from focuscheck.ui.dialogs.snooze_reminder_dialog import SnoozeReminderDialog

        root = _make_root()
        events = []
        try:
            dialog = SnoozeReminderDialog(root, {"always_on_top": False}, on_yes=lambda: events.append("yes"))
            dialog.withdraw()
            dialog._on_yes()
            root.update()
            self.assertEqual(["yes"], events)
            self.assertFalse(dialog.winfo_exists())

            dialog = SnoozeReminderDialog(root, {"always_on_top": False}, on_no=lambda: events.append("no"))
            dialog.withdraw()
            dialog._on_no()
            root.update()
            self.assertEqual(["yes", "no"], events)
            self.assertFalse(dialog.winfo_exists())
        finally:
            root.destroy()

    def test_gentle_reminder_dismisses_without_camera_or_drift(self):
        from focuscheck.ui.dialogs.gentle_reminder_dialog import GentleReminderDialog

        root = _make_root()
        dismissed = []
        try:
            dialog = GentleReminderDialog(
                root,
                {
                    "always_on_top": False,
                    "camera_feed_enabled": False,
                    "biodata_enabled": False,
                    "gentle_reminder_drift_enabled": False,
                },
                on_dismiss=lambda: dismissed.append(True),
            )
            dialog.withdraw()
            dialog._on_dismiss()
            root.update()
            self.assertEqual([True], dismissed)
            self.assertFalse(dialog.winfo_exists())
        finally:
            root.destroy()

    def test_v1_prompt_notifies_owner_after_studying_choice(self):
        from datetime import datetime

        from focuscheck.settings.defaults import DEFAULT_SETTINGS
        from focuscheck.ui.dialogs.prompt_dialog import PromptDialog

        root = _make_root()
        submitted = []
        settings = DEFAULT_SETTINGS.copy()
        settings.update({
            "always_on_top": False,
            "anti_habit_enabled": False,
            "camera_feed_enabled": False,
            "encouragement_enabled": False,
            "focus_prompt_ask_doing": False,
            "focus_prompt_ask_benefits": False,
            "show_task_analytics": False,
        })
        try:
            with mock.patch("focuscheck.ui.dialogs.prompt_dialog.append_log"):
                dialog = PromptDialog(
                    root,
                    settings,
                    lambda: submitted.append(True),
                    datetime.now(),
                    taskdb=None,
                    app_ref=None,
                )
                dialog.withdraw()
                dialog._invoke_action_button(dialog.btn_study)
                root.update()

            self.assertEqual([True], submitted)
            self.assertFalse(dialog.winfo_exists())
        finally:
            root.destroy()

    def test_task_entry_enter_submits(self):
        from focuscheck.ui.dialogs.task_entry_dialog import TaskEntryDialog

        root = _make_root()
        submitted = []
        try:
            dialog = TaskEntryDialog(root, submitted.append)
            dialog.withdraw()
            dialog.title_var.set("Write tests")

            result = dialog._on_return()
            root.update()

            self.assertEqual("break", result)
            self.assertEqual("Write tests", submitted[0]["title"])
            self.assertFalse(dialog.winfo_exists())
        finally:
            root.destroy()

    def test_task_change_enter_submits(self):
        from focuscheck.ui.dialogs.task_change_dialog import TaskChangeDialog

        root = _make_root()
        submitted = []
        try:
            dialog = TaskChangeDialog(root, submitted.append)
            dialog.withdraw()
            dialog.reason_var.set("Scope changed")
            dialog.title_var.set("New task")

            result = dialog._on_return()
            root.update()

            self.assertEqual("break", result)
            self.assertEqual("Scope changed", submitted[0]["reason"])
            self.assertEqual("New task", submitted[0]["new_task"]["title"])
            self.assertFalse(dialog.winfo_exists())
        finally:
            root.destroy()

    def test_prompt_settings_entry_uses_app_persistence_boundary(self):
        from datetime import datetime
        from focuscheck.settings.defaults import DEFAULT_SETTINGS
        from focuscheck.ui.dialogs.prompt_dialog import PromptDialog
        from focuscheck.ui.dialogs.v2_prompt_dialog import V2PromptDialog

        class App:
            root = mock.Mock()
            _persist_settings_draft = mock.Mock()
            _schedule_next = mock.Mock()
            _schedule_prompt_regeneration = mock.Mock()

        root = _make_root()
        try:
            for dialog_type, kwargs in (
                (PromptDialog, {"slot_start_dt": datetime.now()}),
                (V2PromptDialog, {"slot_start_dt": datetime.now(), "activity_info": {}}),
            ):
                dialog = dialog_type.__new__(dialog_type)
                dialog.settings = dict(DEFAULT_SETTINGS)
                dialog.app_ref = App()
                dialog._closed = False
                dialog._cleanup_camera_feed = mock.Mock()
                dialog._cleanup_all_timers = mock.Mock()
                dialog._cleanup_timers = mock.Mock()
                dialog._destroy_stage5_overlays = mock.Mock()
                dialog.destroy = mock.Mock()
                with mock.patch("focuscheck.ui.windows.SettingsWindow") as settings_window:
                    dialog_type._open_settings(dialog)
                self.assertIs(settings_window.call_args.kwargs["persist_settings"], dialog.app_ref._persist_settings_draft)
                settings_window.call_args.kwargs["on_save"]({"example": True})
                dialog.app_ref._schedule_prompt_regeneration.assert_called_once_with()
                dialog.app_ref._schedule_prompt_regeneration.reset_mock()
        finally:
            root.destroy()

    def test_v1_prompt_finishes_when_timer_cleanup_raises(self):
        from datetime import datetime
        from focuscheck.ui.dialogs.prompt_dialog import PromptDialog

        submitted = []
        prompt = PromptDialog.__new__(PromptDialog)
        prompt._closed = False
        prompt._submit_notified = False
        prompt._overdrive_stage4 = True
        prompt._task_decision_required = False
        prompt._task_decision_task_id = None
        prompt._task_decision_can_fail = False
        prompt.taskdb = None
        prompt.settings = {"overdrive_after_seconds": 60}
        prompt.start_monotonic = 0.0
        prompt.intensity_level = 0
        prompt._overdrive = False
        prompt.slot_start_dt = datetime.now()
        prompt.on_submit = lambda: submitted.append(True)
        prompt._capture_photo_for_logs = lambda _choice: None
        prompt._flash_taskbar_stop = mock.Mock()
        prompt._destroy_stage5_overlays = mock.Mock()
        prompt._cleanup_camera_feed = mock.Mock()
        prompt._cleanup_all_timers = mock.Mock(side_effect=RuntimeError("timer cleanup"))
        prompt.destroy = mock.Mock()

        with mock.patch("focuscheck.ui.dialogs.prompt_dialog.append_log"), mock.patch(
            "focuscheck.ui.dialogs.prompt_dialog.get_logger"
        ):
            prompt._finish("Studying")

        self.assertTrue(prompt._closed)
        prompt.destroy.assert_called_once_with()
        self.assertEqual([True], submitted)

    def test_v2_prompt_closes_when_timer_cleanup_raises(self):
        from focuscheck.ui.dialogs.v2_prompt_dialog import V2PromptDialog

        submitted = []
        prompt = V2PromptDialog.__new__(V2PromptDialog)
        prompt._closed = False
        prompt._submit_notified = False
        prompt._cleanup_camera_feed = mock.Mock()
        prompt._flash_taskbar_stop = mock.Mock()
        prompt._cleanup_timers = mock.Mock(side_effect=RuntimeError("timer cleanup"))
        prompt.destroy = mock.Mock()
        prompt.on_submit = lambda: submitted.append(True)

        with mock.patch("focuscheck.ui.dialogs.v2_prompt_dialog.get_logger"):
            prompt._close()

        self.assertTrue(prompt._closed)
        prompt.destroy.assert_called_once_with()
        self.assertEqual([True], submitted)

    def test_follow_up_dialog_callbacks_survive_destroy_failures(self):
        from focuscheck.ui.dialogs.focus_prompt_dialog import FocusPromptDialog
        from focuscheck.ui.dialogs.waste_prompt_dialog import WastePromptDialog

        for dialog_type, method_name, callback_name in (
            (FocusPromptDialog, "_cancel", "on_cancel"),
            (WastePromptDialog, "_cancel", "on_cancel"),
        ):
            events = []
            dialog = dialog_type.__new__(dialog_type)
            dialog.grab_release = mock.Mock()
            dialog.destroy = mock.Mock(side_effect=RuntimeError("destroy"))
            setattr(dialog, callback_name, lambda events=events: events.append(callback_name))
            with mock.patch(f"{dialog_type.__module__}.get_logger"):
                getattr(dialog, method_name)()
            self.assertEqual([callback_name], events)

    def test_snooze_prompt_can_disable_reason_and_exact_fields(self):
        from focuscheck.ui.dialogs.snooze_prompt_dialog import SnoozePromptDialog

        root = _make_root()
        submitted = []
        try:
            dialog = SnoozePromptDialog(
                root,
                {
                    "always_on_top": False,
                    "snooze_prompt_ask_reason": False,
                    "snooze_prompt_exact_enabled": False,
                    "snooze_prompt_validation_enabled": False,
                },
                on_submit=submitted.append,
            )
            dialog.withdraw()

            result = dialog._on_return(None)
            root.update()

            self.assertEqual("break", result)
            self.assertEqual("", submitted[0]["reason"])
            self.assertEqual("", submitted[0]["typed"])
            self.assertFalse(dialog.winfo_exists())
        finally:
            root.destroy()

    def test_v2_subpopup_return_confirms_only_for_high_severity(self):
        from focuscheck.ui.dialogs import v2_subpopup_dialog

        root = _make_root()
        events = []
        try:
            with mock.patch.object(v2_subpopup_dialog, "_get_virtual_screen_rect", return_value=(0, 0, 800, 600)):
                dialog = v2_subpopup_dialog.V2SubPopupDialog(
                    root,
                    "example.com",
                    severity=2,
                    on_yes=lambda: events.append("yes"),
                    on_no=lambda: events.append("no"),
                )
                dialog.withdraw()
                result = dialog._on_return()
                root.update()

                self.assertEqual("break", result)
                self.assertEqual(["yes"], events)
                self.assertFalse(dialog.winfo_exists())

                events.clear()
                dialog = v2_subpopup_dialog.V2SubPopupDialog(
                    root,
                    "example.com",
                    severity=1,
                    on_yes=lambda: events.append("yes"),
                    on_no=lambda: events.append("no"),
                )
                dialog.withdraw()
                result = dialog._on_return()
                root.update()

                self.assertEqual("break", result)
                self.assertEqual(["no"], events)
                self.assertFalse(dialog.winfo_exists())
        finally:
            root.destroy()

    def test_v2_subpopup_escape_declines(self):
        from focuscheck.ui.dialogs import v2_subpopup_dialog

        root = _make_root()
        events = []
        try:
            with mock.patch.object(v2_subpopup_dialog, "_get_virtual_screen_rect", return_value=(0, 0, 800, 600)):
                dialog = v2_subpopup_dialog.V2SubPopupDialog(
                    root,
                    "example.com",
                    severity=2,
                    on_yes=lambda: events.append("yes"),
                    on_no=lambda: events.append("no"),
                )
                dialog.withdraw()

                result = dialog._on_escape()
                root.update()

                self.assertEqual("break", result)
                self.assertEqual(["no"], events)
                self.assertFalse(dialog.winfo_exists())
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()

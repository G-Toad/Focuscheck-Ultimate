from __future__ import annotations

import unittest
from unittest import mock


class InterventionCoordinatorTests(unittest.TestCase):
    def test_snooze_prompt_cancel_releases_deferred_callbacks_and_grab(self):
        from focuscheck.ui.dialogs.snooze_prompt_dialog import SnoozePromptDialog

        cancelled = []
        dialog = object.__new__(SnoozePromptDialog)
        dialog._logger = None
        dialog._ensure_visible_timer_id = "visible"
        dialog._initial_focus_timer_id = "focus"
        dialog.after_cancel = mock.Mock()
        dialog.grab_release = mock.Mock()
        dialog.destroy = mock.Mock()
        dialog.on_cancel = lambda: cancelled.append(True)

        dialog._cancel()

        self.assertEqual([mock.call("visible"), mock.call("focus")], dialog.after_cancel.call_args_list)
        self.assertIsNone(dialog._ensure_visible_timer_id)
        self.assertIsNone(dialog._initial_focus_timer_id)
        dialog.grab_release.assert_called_once_with()
        dialog.destroy.assert_called_once_with()
        self.assertEqual([True], cancelled)

    def test_snooze_prompt_owned_timer_clears_handle_before_callback(self):
        from focuscheck.ui.dialogs.snooze_prompt_dialog import SnoozePromptDialog

        dialog = object.__new__(SnoozePromptDialog)
        dialog._ensure_visible_timer_id = "old"
        scheduled = []
        events = []
        dialog.after = lambda delay, callback: (scheduled.append((delay, callback)) or "new")

        timer_id = dialog._schedule_owned_timer(
            "_ensure_visible_timer_id", 200, lambda: events.append(dialog._ensure_visible_timer_id)
        )
        dialog._ensure_visible_timer_id = timer_id
        scheduled[0][1]()

        self.assertEqual([None], events)
        self.assertIsNone(dialog._ensure_visible_timer_id)

    def test_snooze_prompt_registry_invalidates_callbacks_on_close(self):
        from focuscheck.ui.dialogs.snooze_prompt_dialog import SnoozePromptDialog
        from focuscheck.utils.timers import TimerRegistry

        dialog = object.__new__(SnoozePromptDialog)
        dialog._ensure_visible_timer_id = None
        dialog._initial_focus_timer_id = None
        scheduled = []
        events = []
        dialog.after = lambda delay, callback: (scheduled.append(callback) or f"timer-{len(scheduled)}")
        dialog.after_cancel = lambda _timer_id: None
        dialog._timers = TimerRegistry(dialog)

        dialog._ensure_visible_timer_id = dialog._schedule_owned_timer(
            "_ensure_visible_timer_id", 200, lambda: events.append("stale")
        )
        dialog._cancel_pending_timers()
        scheduled[0]()

        self.assertEqual([], events)
        self.assertIsNone(dialog._ensure_visible_timer_id)
        self.assertTrue(dialog._timers.closed)

    def test_snooze_reminder_close_cancels_focus_timer(self):
        from focuscheck.ui.dialogs.snooze_reminder_dialog import SnoozeReminderDialog

        dialog = object.__new__(SnoozeReminderDialog)
        dialog._closed = False
        dialog._focus_timer_id = "focus"
        dialog.after_cancel = mock.Mock()
        dialog.destroy = mock.Mock()
        dialog.on_yes = None
        dialog.on_no = None

        dialog._on_yes()

        dialog.after_cancel.assert_called_once_with("focus")
        self.assertIsNone(dialog._focus_timer_id)
        dialog.destroy.assert_called_once_with()

    def test_snooze_reminder_registry_invalidates_dequeued_focus_callback(self):
        from focuscheck.ui.dialogs.snooze_reminder_dialog import SnoozeReminderDialog
        from focuscheck.utils.timers import TimerRegistry

        dialog = object.__new__(SnoozeReminderDialog)
        dialog._closed = False
        dialog._focus_timer_id = None
        dialog.btn_yes = mock.Mock()
        scheduled = []
        dialog.after = lambda delay, callback: (scheduled.append(callback) or f"timer-{len(scheduled)}")
        dialog.after_cancel = lambda _timer_id: None
        dialog._timers = TimerRegistry(dialog)

        dialog._focus_timer_id = dialog._schedule_focus_timer()
        dialog._cancel_focus_timer()
        scheduled[0]()

        dialog.btn_yes.focus_set.assert_not_called()
        self.assertIsNone(dialog._focus_timer_id)
        self.assertTrue(dialog._timers.closed)

    def test_selection_dialog_cancels_recurring_callbacks(self):
        from focuscheck.ui.dialogs.intervention_wizard import WindowSelectionDialog

        dialog = object.__new__(WindowSelectionDialog)
        dialog._front_timer_id = "front"
        dialog._tab_scan_timer_id = "tabs"
        dialog._timers = mock.Mock()

        dialog._cancel_scheduled_callbacks()

        dialog._timers.close.assert_called_once_with()
        self.assertIsNone(dialog._front_timer_id)
        self.assertIsNone(dialog._tab_scan_timer_id)

    def test_selection_tab_scan_does_not_log_window_title(self):
        from focuscheck.ui.dialogs.intervention_wizard import WindowSelectionDialog

        dialog = object.__new__(WindowSelectionDialog)
        dialog._closed = False
        dialog._tab_queue = mock.Mock()
        dialog._tab_queue.get_nowait.side_effect = [
            ({"title": "private.example/secret-token", "process_name": "chrome.exe"}, [], ""),
            Exception("empty"),
        ]
        dialog._timers = mock.Mock()
        dialog._items = []
        with mock.patch("focuscheck.ui.dialogs.intervention_wizard.get_logger") as logger:
            dialog._drain_tab_queue()

        logged = " ".join(str(call) for call in logger.return_value.info.call_args_list)
        self.assertNotIn("private.example/secret-token", logged)
        self.assertIn("title_summary", logged)

    def test_app_intervention_lease_is_released_after_failure(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app.root = mock.Mock()
        app._runtime_state = mock.Mock()
        app._runtime_state.begin_intervention.return_value = True
        app._intervention_active = False
        with mock.patch("focuscheck.ui.dialogs.intervention_wizard.InterventionWizard", side_effect=RuntimeError("failed")):
            self.assertFalse(App.run_intervention(app, {}, preselect_hwnd=None, preselect_title=None))
            self.assertFalse(app._intervention_active)
        app._runtime_state.end_intervention.assert_called_once()

    def test_off_thread_intervention_timeout_invalidates_queued_tk_callback(self):
        from focuscheck.ui.dialogs import intervention_wizard

        class Parent:
            _focuscheck_tk_thread_id = -1

            def __init__(self):
                self.callbacks = []

            def after(self, _delay, callback):
                self.callbacks.append(callback)
                return "dispatch"

        parent = Parent()
        wizard = intervention_wizard.InterventionWizard(parent, {})
        wizard._run_internal = mock.Mock(return_value=True)
        done = mock.Mock()
        done.wait.return_value = False
        cancelled = mock.Mock()
        cancelled.is_set.return_value = False

        with mock.patch.object(
            intervention_wizard.threading,
            "Event",
            side_effect=[done, cancelled],
        ):
            self.assertFalse(wizard.run())

        cancelled.set.assert_called_once_with()
        cancelled.is_set.return_value = True
        parent.callbacks[0]()
        wizard._run_internal.assert_not_called()

    def test_reflection_timeout_invalidates_queued_tk_callback(self):
        from focuscheck.ui.dialogs import intervention_reflection_dialog

        class Parent:
            _focuscheck_tk_thread_id = -1

            def __init__(self):
                self.callbacks = []

            def after(self, _delay, callback):
                self.callbacks.append(callback)
                return "dispatch"

        parent = Parent()
        done = mock.Mock()
        done.wait.return_value = False
        cancelled = mock.Mock()
        cancelled.is_set.return_value = False

        with mock.patch.object(
            intervention_reflection_dialog.threading,
            "Event",
            side_effect=[done, cancelled],
        ):
            result = intervention_reflection_dialog.InterventionReflectionDialog.prompt(
                parent, "intervention-id"
            )

        self.assertIsNone(result)
        cancelled.set.assert_called_once_with()
        cancelled.is_set.return_value = True
        parent.callbacks[0]()

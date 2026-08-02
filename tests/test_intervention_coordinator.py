from __future__ import annotations

import unittest
from unittest import mock


class InterventionCoordinatorTests(unittest.TestCase):
    def test_selection_dialog_cancels_recurring_callbacks(self):
        from focuscheck.ui.dialogs.intervention_wizard import WindowSelectionDialog

        dialog = object.__new__(WindowSelectionDialog)
        dialog._front_timer_id = "front"
        dialog._tab_scan_timer_id = "tabs"
        dialog.after_cancel = mock.Mock()

        dialog._cancel_scheduled_callbacks()

        self.assertEqual([mock.call("front"), mock.call("tabs")], dialog.after_cancel.call_args_list)
        self.assertIsNone(dialog._front_timer_id)
        self.assertIsNone(dialog._tab_scan_timer_id)

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

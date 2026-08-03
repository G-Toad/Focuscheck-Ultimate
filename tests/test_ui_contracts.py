from __future__ import annotations

import threading
import unittest
from unittest import mock


class UiContractTests(unittest.TestCase):
    def test_dispatch_uses_recorded_tk_owner_thread(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app._tk_thread_id = 123
        app.root = mock.Mock()
        with mock.patch("focuscheck.app.threading.get_ident", return_value=456):
            self.assertTrue(App._call_on_ui_thread(app, lambda: None))
        app.root.after.assert_called_once()

    def test_composed_dispatch_uses_timer_registry_and_shutdown_cancels_it(self):
        from focuscheck.app import App
        from focuscheck.utils.timers import TimerRegistry

        class Root:
            def after(self, _delay, callback):
                self.callback = callback
                return "dispatch-1"

            def after_cancel(self, _timer_id):
                self.cancelled = True

        app = App.__new__(App)
        app._tk_thread_id = 123
        app.root = Root()
        app._timers = TimerRegistry(app.root)
        with mock.patch("focuscheck.app.threading.get_ident", return_value=456):
            self.assertTrue(App._call_on_ui_thread(app, lambda: None))

        app._timers.close()
        app.root.callback()
        self.assertTrue(app.root.cancelled)

    def test_tray_without_repository_does_not_write_config_fallback(self):
        from focuscheck.system_tray import SystemTray

        app = mock.Mock(settings={})
        tray = SystemTray(app=app, config_path="should-not-be-written.json")
        with mock.patch("builtins.open", mock.mock_open()) as open_mock:
            tray._set_setting("interval_seconds", 30)
        open_mock.assert_not_called()

    def test_tray_settings_fallback_uses_app_ui_dispatcher(self):
        from focuscheck.system_tray import SystemTray

        class App:
            settings = {}

            def __init__(self):
                self.root = mock.Mock()
                self.dispatches = []

            def _call_on_ui_thread(self, callback):
                self.dispatches.append(callback)
                return True

        app = App()
        tray = SystemTray(app=app, name="TestTray", config_path="missing-settings.json")
        with mock.patch("tkinter.messagebox.showinfo"):
            tray._open_settings()
            self.assertEqual(1, len(app.dispatches))
            app.dispatches[0]()

    def test_tray_task_dialog_is_created_only_on_tk_owner_thread(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app._tk_thread_id = 123
        app.taskdb = object()
        app.root = mock.Mock()
        scheduled = []
        app.root.after.side_effect = lambda _delay, callback: scheduled.append(callback)
        with mock.patch("focuscheck.app.threading.get_ident", return_value=456), mock.patch(
            "focuscheck.app.TaskEntryDialog"
        ) as dialog:
            self.assertTrue(App._open_task_dialog_from_tray(app))
            dialog.assert_not_called()
            self.assertEqual(1, len(scheduled))
            scheduled[0]()
            dialog.assert_called_once()

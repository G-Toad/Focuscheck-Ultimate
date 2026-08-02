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

    def test_tray_without_repository_does_not_write_config_fallback(self):
        from focuscheck.system_tray import SystemTray

        app = mock.Mock(settings={})
        tray = SystemTray(app=app, config_path="should-not-be-written.json")
        with mock.patch("builtins.open", mock.mock_open()) as open_mock:
            tray._set_setting("interval_seconds", 30)
        open_mock.assert_not_called()

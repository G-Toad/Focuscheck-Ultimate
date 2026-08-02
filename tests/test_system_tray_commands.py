"""Desktop-safe system tray command tests.

These tests call command handlers directly and never start pystray or native
Windows tray integration.
"""

from __future__ import annotations

import unittest
from unittest import mock


class FakeTrayApp:
    def __init__(self):
        self.calls = []
        self.settings = {
            "paused": False,
            "tray_start_stop_enabled": True,
            "tray_settings_button_enabled": True,
            "tray_exit_button_enabled": True,
        }
        self.startup_enabled = False

    def _tray_pause(self):
        self.calls.append("pause")
        self.settings["paused"] = True
        return True

    def _tray_resume(self):
        self.calls.append("resume")
        self.settings["paused"] = False
        return True

    def _tray_prompt_now(self):
        self.calls.append("prompt_now")
        return True

    def _tray_snooze(self, minutes):
        self.calls.append(("snooze", minutes))
        return True

    def _open_task_dialog_from_tray(self):
        self.calls.append("task")
        return True

    def _tray_open_data_folder(self):
        self.calls.append("data")
        return True

    def _tray_open_logs_folder(self):
        self.calls.append("logs")
        return True

    def _tray_export_data(self):
        self.calls.append("export")
        return True

    def _tray_show_data_inventory(self):
        self.calls.append("inventory")
        return True

    def _tray_clear_logs(self):
        self.calls.append("clear_logs")
        return True

    def _tray_clear_data(self):
        self.calls.append("clear_data")
        return True

    def _tray_retain_logs(self):
        self.calls.append("retain_logs")
        return True

    def _tray_diagnostic_bundle(self):
        self.calls.append("diagnostic")
        return True

    def _tray_show_status(self):
        self.calls.append("status")
        return True

    def _is_startup_enabled(self):
        return self.startup_enabled

    def _tray_install_startup(self):
        self.calls.append("install_startup")
        self.startup_enabled = True
        return True

    def _tray_uninstall_startup(self):
        self.calls.append("uninstall_startup")
        self.startup_enabled = False
        return True

    def _tray_exit(self):
        self.calls.append("exit")
        return True


class SystemTrayCommandTests(unittest.TestCase):
    def test_command_handlers_delegate_to_fake_app_without_starting_tray(self):
        from focuscheck.system_tray import SystemTray

        app = FakeTrayApp()
        tray = SystemTray(app=app, name="FocusCheckTest")

        tray._stop_reminders(None, None)
        tray._start_reminders(None, None)
        tray._prompt_now(None, None)
        tray._snooze(5)(None, None)
        tray._open_task(None, None)
        tray._open_data(None, None)
        tray._open_logs(None, None)
        tray._export_data(None, None)
        tray._show_data_inventory(None, None)
        tray._clear_logs(None, None)
        tray._clear_data(None, None)
        tray._retain_logs(None, None)
        tray._diagnostic_bundle(None, None)
        tray._show_status(None, None)

        self.assertEqual(
            ["pause", "resume", "prompt_now", ("snooze", 5), "task", "data", "logs", "export", "inventory", "clear_logs", "clear_data", "retain_logs", "diagnostic", "status"],
            app.calls,
        )

    def test_start_stop_and_exit_gates_block_handlers(self):
        from focuscheck.system_tray import SystemTray

        app = FakeTrayApp()
        app.settings["tray_start_stop_enabled"] = False
        app.settings["tray_exit_button_enabled"] = False
        tray = SystemTray(app=app, name="FocusCheckTest")

        with mock.patch("focuscheck.system_tray.sys.exit") as exit_mock:
            tray._stop_reminders(None, None)
            tray._start_reminders(None, None)
            tray._on_quit(None, None)

        self.assertEqual([], app.calls)
        exit_mock.assert_not_called()

    def test_toggle_startup_delegates_to_install_and_uninstall(self):
        from focuscheck.system_tray import SystemTray

        app = FakeTrayApp()
        tray = SystemTray(app=app, name="FocusCheckTest")

        tray._toggle_startup(None, None)
        tray._toggle_startup(None, None)

        self.assertEqual(["install_startup", "uninstall_startup"], app.calls)

    def test_enabled_exit_delegates_without_tray_thread_sys_exit(self):
        from focuscheck.system_tray import SystemTray

        class Icon:
            def __init__(self):
                self.visible = True
                self.stopped = False

            def stop(self):
                self.stopped = True

        app = FakeTrayApp()
        tray = SystemTray(app=app, name="FocusCheckTest")
        tray._icon = Icon()
        with mock.patch("focuscheck.system_tray.sys.exit") as exit_mock:
            tray._on_quit(None, None)
        self.assertEqual(["exit"], app.calls)
        self.assertTrue(tray._icon.stopped)
        exit_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()

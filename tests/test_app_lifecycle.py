"""Non-GUI lifecycle regression tests."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class AppLifecycleTests(unittest.TestCase):
    def test_prompt_done_is_idempotent(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app._current_prompt = object()
        calls = []
        app._schedule_next = lambda *args, **kwargs: calls.append((args, kwargs))

        App._on_prompt_done(app)
        App._on_prompt_done(app)

        self.assertIsNone(app._current_prompt)
        self.assertEqual(1, len(calls))

    def test_tray_exit_dispatches_quit_on_ui_thread_when_enabled(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app.settings = {"tray_exit_button_enabled": True}
        calls = []
        app._call_on_ui_thread = lambda callback: calls.append("dispatch") or callback()
        app._quit = lambda: calls.append("quit")

        result = App._tray_exit(app)

        self.assertTrue(result is None or result is True)
        self.assertEqual(["dispatch", "quit"], calls)

    def test_tray_exit_respects_disabled_exit_setting(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app.settings = {"tray_exit_button_enabled": False}
        calls = []
        app._call_on_ui_thread = lambda callback: calls.append("dispatch") or callback()
        app._quit = lambda: calls.append("quit")

        App._tray_exit(app)

        self.assertEqual(["dispatch"], calls)

    def test_quit_requests_supervisor_stop_before_cleanup_and_exit(self):
        from focuscheck.app import App

        events = []

        class Tray:
            def __init__(self, stop_file: Path):
                self.stop_file = stop_file

            def stop(self):
                self.stop_file.read_text(encoding="ascii")
                events.append("tray.stop")

        class Watcher:
            def close(self):
                events.append("watcher.close")

        class Root:
            def destroy(self):
                events.append("root.destroy")

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            stop_file = Path(temp_dir) / "supervisor.stop"
            app = App.__new__(App)
            app._tray = Tray(stop_file)
            app._winwatch = Watcher()
            app.root = Root()

            with (
                mock.patch.dict(
                    os.environ,
                    {"FOCUSCHECK_SUPERVISOR_STOP_FILE": str(stop_file)},
                ),
                mock.patch("focuscheck.app.sys.exit") as exit_mock,
            ):
                App._quit(app)

            self.assertTrue(stop_file.exists())
            self.assertEqual(["tray.stop", "watcher.close", "root.destroy"], events)
            exit_mock.assert_called_once_with(0)

    def test_quit_tolerates_cleanup_errors_and_still_exits(self):
        from focuscheck.app import App

        events = []

        class BrokenTray:
            def stop(self):
                events.append("tray.stop")
                raise RuntimeError("tray failed")

        class BrokenWatcher:
            def close(self):
                events.append("watcher.close")
                raise RuntimeError("watcher failed")

        class BrokenRoot:
            def destroy(self):
                events.append("root.destroy")
                raise RuntimeError("root failed")

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            app = App.__new__(App)
            app._tray = BrokenTray()
            app._winwatch = BrokenWatcher()
            app.root = BrokenRoot()
            stop_file = Path(temp_dir) / "supervisor.stop"

            with (
                mock.patch.dict(
                    os.environ,
                    {"FOCUSCHECK_SUPERVISOR_STOP_FILE": str(stop_file)},
                ),
                mock.patch("focuscheck.app.sys.exit") as exit_mock,
            ):
                App._quit(app)

            self.assertTrue(stop_file.exists())
            self.assertEqual(["tray.stop", "watcher.close", "root.destroy"], events)
            exit_mock.assert_called_once_with(0)


class V2PromptLifecycleTests(unittest.TestCase):
    def test_v2_prompt_exposes_app_cleanup_hooks(self):
        from focuscheck.ui.dialogs.v2_prompt_dialog import V2PromptDialog

        prompt = V2PromptDialog.__new__(V2PromptDialog)
        prompt._active_timers = set()

        self.assertIsNone(prompt._cleanup_all_timers())
        self.assertIsNone(prompt._destroy_stage5_overlays())


if __name__ == "__main__":
    unittest.main()

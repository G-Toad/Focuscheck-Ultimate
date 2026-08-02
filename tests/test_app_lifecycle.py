"""Non-GUI lifecycle regression tests."""

from __future__ import annotations

import os
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest import mock


class AppLifecycleTests(unittest.TestCase):
    def test_single_instance_mutex_handle_is_released(self):
        import focuscheck.utils.file_ops as file_ops

        class Api:
            def __init__(self, result=None):
                self.result = result
                self.argtypes = None
                self.restype = None
                self.calls = []

            def __call__(self, *args):
                self.calls.append(args)
                return self.result

        create_mutex = Api(123)
        get_last_error = Api(0)
        close_handle = Api(1)
        kernel32 = type("Kernel", (), {
            "CreateMutexW": create_mutex,
            "GetLastError": get_last_error,
            "CloseHandle": close_handle,
        })()
        with mock.patch.object(file_ops.platform, "system", return_value="Windows"), \
                mock.patch.object(file_ops.ctypes, "windll", type("Windll", (), {"kernel32": kernel32})()):
            file_ops._single_instance_handle = None
            self.assertTrue(file_ops.acquire_single_instance())
            self.assertTrue(file_ops.release_single_instance())

        self.assertEqual(123, close_handle.calls[0][0])
        self.assertIsNone(file_ops._single_instance_handle)
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

    def test_native_tray_fallback_stops_pystray_before_activation(self):
        from focuscheck.app import App

        events = []

        class Tray:
            def stop(self):
                events.append("pystray_stop")

        class Watcher:
            def _tray_add(self, tooltip):
                events.append(("native_add", tooltip))

        app = App.__new__(App)
        app._tray = Tray()
        app._winwatch = Watcher()
        app._pystray_started = True
        app._using_pystray = True
        app._native_tray_fallback_active = False
        app._activate_native_tray_fallback()
        app._activate_native_tray_fallback()

        self.assertEqual(["pystray_stop", ("native_add", "Focus Check")], events)
        self.assertFalse(app._pystray_started)
        self.assertFalse(app._using_pystray)
        self.assertTrue(app._native_tray_fallback_active)

    def test_tray_export_dispatches_ui_flow_and_requires_sensitive_confirmation(self):
        from focuscheck.app import App

        app = App.__new__(App)
        dispatches = []
        app._call_on_ui_thread = lambda callback: dispatches.append("dispatch") or callback()

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "export.zip"
            with (
                mock.patch("focuscheck.app.get_data_dir", return_value=temp_dir),
                mock.patch("tkinter.filedialog.asksaveasfilename", return_value=str(output)),
                mock.patch("focuscheck.app.messagebox.askyesno", return_value=True),
                mock.patch("focuscheck.app.messagebox.showinfo"),
                mock.patch("focuscheck.utils.data_export.export_data", return_value={"files": ["x"]}) as export_mock,
            ):
                result = App._tray_export_data(app)

        self.assertTrue(result)
        self.assertEqual(["dispatch"], dispatches)
        self.assertEqual(
            ("logs", "metadata", "settings", "tasks"),
            export_mock.call_args.kwargs["categories"],
        )

    def test_tray_clear_logs_dispatches_confirmation_and_allowlisted_service(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app._call_on_ui_thread = lambda callback: callback()
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                mock.patch("focuscheck.app.get_data_dir", return_value=temp_dir),
                mock.patch("focuscheck.app.messagebox.askyesno", return_value=True),
                mock.patch("focuscheck.app.messagebox.showinfo"),
                mock.patch("focuscheck.utils.data_export.clear_data", return_value={"files": [{"deleted": True}]}) as clear_mock,
            ):
                result = App._tray_clear_logs(app)

        self.assertTrue(result)
        self.assertEqual(("logs",), clear_mock.call_args.kwargs["categories"])
        self.assertTrue(clear_mock.call_args.kwargs["confirmed"])

    def test_tray_retention_dispatches_selected_duration_to_service(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app._call_on_ui_thread = lambda callback: callback()
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                mock.patch("focuscheck.app.get_data_dir", return_value=temp_dir),
                mock.patch("tkinter.simpledialog.askinteger", return_value=30),
                mock.patch("focuscheck.app.messagebox.showinfo"),
                mock.patch("focuscheck.utils.data_retention.apply_retention", return_value=[{"deleted": True}]) as retain_mock,
            ):
                result = App._tray_retain_logs(app)

        self.assertTrue(result)
        self.assertEqual(30, retain_mock.call_args.kwargs["max_age_days"])
        self.assertTrue(retain_mock.call_args.kwargs["apply"])

    def test_tray_diagnostic_bundle_previews_before_saving(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app._call_on_ui_thread = lambda callback: callback()
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "diagnostic.zip"
            with (
                mock.patch("focuscheck.app.get_data_dir", return_value=temp_dir),
                mock.patch("focuscheck.app.messagebox.askyesno", return_value=True),
                mock.patch("focuscheck.app.messagebox.showinfo"),
                mock.patch("tkinter.filedialog.asksaveasfilename", return_value=str(output)),
                mock.patch("focuscheck.utils.diagnostics.preview_bundle", return_value={"files": [], "excluded": []}),
                mock.patch("focuscheck.utils.diagnostics.create_bundle") as create_mock,
            ):
                result = App._tray_diagnostic_bundle(app)

        self.assertTrue(result)
        create_mock.assert_called_once()
        self.assertEqual(Path(temp_dir), create_mock.call_args.args[0])
        self.assertEqual(output, Path(create_mock.call_args.args[1]))

    def test_app_data_controls_use_frozen_path_snapshot(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app.paths = type("Paths", (), {"root": Path("C:/frozen-focuscheck-root")})()
        with mock.patch("focuscheck.app.get_data_dir", return_value="C:/different-root"):
            self.assertEqual(Path("C:/frozen-focuscheck-root"), App._data_root(app))

    def test_engine_shutdown_is_idempotent(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app._engine_shutdown = False
        engine = mock.Mock()
        app._engine = engine

        App._shutdown_engine(app)
        App._shutdown_engine(app)

        engine.shutdown.assert_called_once_with()
        self.assertIsNone(app._engine)

    def test_engine_switch_closes_prompt_before_old_engine_shutdown(self):
        from focuscheck.app import App

        events = []

        class NewEngine:
            name = "new"

            def __init__(self, _app):
                events.append("new_engine")

            def on_settings_updated(self, _settings):
                events.append("settings")

        class OldEngine:
            def shutdown(self):
                events.append("old_shutdown")

        class Prompt:
            _closed = False

            def winfo_exists(self):
                return True

            def _cleanup_camera_feed(self):
                events.append("camera")

            def _cleanup_all_timers(self):
                events.append("timers")

            def destroy(self):
                events.append("destroy")

        app = App.__new__(App)
        app.settings = {"monitoring_mode": "v2"}
        app._engine = OldEngine()
        app._current_prompt = Prompt()

        with mock.patch.object(App, "_get_engine_class", return_value=NewEngine):
            App._ensure_engine(app)

        self.assertEqual(["camera", "timers", "destroy", "old_shutdown", "new_engine", "settings"], events)
        self.assertIsInstance(app._engine, NewEngine)
        self.assertIsNone(app._current_prompt)

    def test_prompt_cleanup_runs_before_shutdown_destroy(self):
        from focuscheck.app import App

        events = []

        class Prompt:
            def _cleanup_camera_feed(self):
                events.append("camera")

            def _cleanup_all_timers(self):
                events.append("timers")

            def _destroy_stage5_overlays(self):
                events.append("overlays")

            def destroy(self):
                events.append("destroy")

        app = App.__new__(App)
        app._current_prompt = Prompt()
        App._close_current_prompt_for_shutdown(app)

        self.assertEqual(["camera", "timers", "overlays", "destroy"], events)
        self.assertIsNone(app._current_prompt)

    def test_refresh_guard_samples_guard_once_and_publishes_state(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app.guard = mock.Mock()
        app.guard.should_pause.return_value = True
        app._runtime_state = mock.Mock()

        self.assertTrue(App._refresh_guard_state(app))
        app.guard.should_pause.assert_called_once_with()
        app._runtime_state.set_guard_reason.assert_called_once_with("system_guard", True)

    def test_prompt_tick_uses_in_memory_settings_snapshot(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app.settings = {"paused": True, "pause_poll_interval_seconds": 5}
        app._runtime_state = mock.Mock()
        app._runtime_state.snapshot = SimpleNamespace(effectively_paused=True)
        app._refresh_guard_state = mock.Mock(return_value=False)
        app._schedule_next = mock.Mock()

        with mock.patch("focuscheck.app.load_settings", side_effect=AssertionError("hot-path reload")):
            App._maybe_show_prompt(app)

        app._runtime_state.refresh_from_settings.assert_called_once_with(app.settings)
        app._schedule_next.assert_called_once_with(5000)

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

    def test_windows_shutdown_query_prepares_without_exiting(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app._windows_shutdown_query = False
        with mock.patch("focuscheck.app.get_logger") as logger:
            App._handle_system_shutdown(app, "query_end_session")

        self.assertTrue(app._windows_shutdown_query)
        logger.return_value.info.assert_called_once()

    def test_windows_end_session_uses_normal_cleanup_coordinator(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app._shutdown_requested = False
        calls = []
        app._quit = lambda **kwargs: calls.append(kwargs)

        App._handle_system_shutdown(app, "end_session")

        self.assertEqual([{"reason": "windows_end_session"}], calls)

    def test_run_preserves_mainloop_exception_after_cleanup(self):
        from focuscheck.app import App

        class Root:
            def mainloop(self):
                raise RuntimeError("mainloop failed")

        app = App.__new__(App)
        app.root = Root()
        app._winwatch = None
        with self.assertRaisesRegex(RuntimeError, "mainloop failed"):
            App.run(app)


class V2PromptLifecycleTests(unittest.TestCase):
    def test_v2_prompt_exposes_app_cleanup_hooks(self):
        from focuscheck.ui.dialogs.v2_prompt_dialog import V2PromptDialog

        prompt = V2PromptDialog.__new__(V2PromptDialog)
        prompt._active_timers = set()

        self.assertIsNone(prompt._cleanup_all_timers())
        self.assertIsNone(prompt._destroy_stage5_overlays())


if __name__ == "__main__":
    unittest.main()

"""Non-GUI lifecycle regression tests."""

from __future__ import annotations

import ast
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock


class AppLifecycleTests(unittest.TestCase):
    def test_initial_monitoring_failure_is_re_raised_from_composition(self):
        source = Path(__file__).resolve().parents[1] / "focuscheck" / "app.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        app_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "App")
        initialize = next(node for node in app_class.body if isinstance(node, ast.FunctionDef) and node.name == "_initialize")
        guarded = []
        for node in ast.walk(initialize):
            if not isinstance(node, ast.Try):
                continue
            if any(
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == "_apply_initial_monitoring_state"
                for call in ast.walk(node)
            ):
                guarded.extend(node.handlers)
        self.assertTrue(guarded)
        self.assertTrue(any(isinstance(stmt, ast.Raise) for handler in guarded for stmt in handler.body))

    def test_prompt_regeneration_uses_timer_registry_and_cancels_on_shutdown(self):
        from focuscheck.app import App
        from focuscheck.utils.timers import TimerRegistry

        class Root:
            def after(self, _delay, callback):
                self.callback = callback
                return "regenerate-1"

            def after_cancel(self, _timer_id):
                self.cancelled = True

        app = App.__new__(App)
        app.root = Root()
        app._timers = TimerRegistry(app.root)
        app._schedule_next = mock.Mock()

        self.assertTrue(app._schedule_prompt_regeneration())
        app._timers.close()
        app.root.callback()

        app._schedule_next.assert_not_called()
        self.assertTrue(app.root.cancelled)

    def test_slot_start_info_uses_app_owned_clock(self):
        from focuscheck.app import App
        from focuscheck.utils.clock import FakeClock

        clock = FakeClock(datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc), current_monotonic=42.0)
        app = App.__new__(App)
        app._runtime_clock = clock

        slot = app._slot_start_info()

        self.assertEqual(clock.now_utc(), slot["utc_start"])
        self.assertEqual(42.0, slot["mono_start"])

    def test_composed_v2_engine_receives_clock_and_activity_provider(self):
        from focuscheck.app import App
        from focuscheck.utils.clock import FakeClock

        clock = FakeClock(datetime(2030, 1, 1, tzinfo=timezone.utc))
        provider = lambda: {"title": "test"}
        received = {}

        class Engine:
            name = "v2"

            def __init__(self, _app, activity_provider=None, clock=None):
                received["provider"] = activity_provider
                received["clock"] = clock

            def on_settings_updated(self, _settings):
                return None

            def shutdown(self):
                return None

        app = App.__new__(App)
        app.settings = {"monitoring_mode": "v2"}
        app._engine = None
        app._current_prompt = None
        app._activity_provider = provider
        app._runtime_clock = clock

        with mock.patch("focuscheck.app.EngineV2", Engine), mock.patch.object(App, "_get_engine_class", return_value=Engine):
            App._ensure_engine(app)

        self.assertIs(provider, received["provider"])
        self.assertIs(clock, received["clock"])

    def test_app_constructor_retains_injected_composition_dependencies(self):
        from focuscheck.app import App
        from focuscheck.utils.clock import FakeClock

        clock = FakeClock(datetime(2030, 1, 1, tzinfo=timezone.utc))
        provider = lambda: None
        captured = {}

        def initialize(instance, *, force_start=False):
            captured["app"] = instance

        with mock.patch.object(App, "_initialize", initialize):
            App(clock=clock, activity_provider=provider)

        self.assertIs(clock, captured["app"]._clock_override)
        self.assertIs(provider, captured["app"]._activity_provider)

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

    def test_gentle_reminder_uses_configured_interval_and_closes(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app.settings = {"gentle_reminder_enabled": True, "gentle_reminder_interval": 3}
        app._gentle_reminder_next_mono = 0.0
        app._gentle_reminder_dialog = None
        app._current_prompt = None

        with mock.patch("focuscheck.app.time.monotonic", return_value=100.0):
            App._maybe_show_gentle_reminder(app)
        self.assertEqual(280.0, app._gentle_reminder_next_mono)
        self.assertIsNone(app._gentle_reminder_dialog)

        events = []

        class Dialog:
            def __init__(self, _root, _settings, on_dismiss):
                self.on_dismiss = on_dismiss

            def _on_dismiss(self):
                events.append("dismiss")

            def destroy(self):
                events.append("destroy")

        app.root = object()
        app._gentle_reminder_next_mono = 99.0
        with mock.patch("focuscheck.app.time.monotonic", return_value=100.0), \
                mock.patch("focuscheck.app.GentleReminderDialog", Dialog):
            App._maybe_show_gentle_reminder(app)
        self.assertIsInstance(app._gentle_reminder_dialog, Dialog)
        App._close_gentle_reminder(app)
        self.assertEqual(["dismiss"], events)
        self.assertIsNone(app._gentle_reminder_dialog)

    def test_gentle_reminder_uses_effective_runtime_pause(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app.settings = {
            "gentle_reminder_enabled": True,
            "gentle_reminder_interval": 1,
            "paused": False,
        }
        app._runtime_state = mock.Mock()
        app._runtime_state.is_effectively_paused.return_value = True
        app._gentle_reminder_next_mono = 99.0
        app._gentle_reminder_dialog = None
        app._current_prompt = None

        with mock.patch("focuscheck.app.time.monotonic", return_value=100.0), mock.patch(
            "focuscheck.app.GentleReminderDialog"
        ) as dialog:
            App._maybe_show_gentle_reminder(app)

        app._runtime_state.is_effectively_paused.assert_called_once_with()
        dialog.assert_not_called()

    def test_tray_toggle_uses_manual_pause_not_effective_guard_pause(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app.settings = {"tray_start_stop_enabled": True, "paused": True}
        app._runtime_state = mock.Mock()
        app._runtime_state.snapshot.manual_paused = False
        app._tray_pause = mock.Mock(return_value=True)
        app._tray_resume = mock.Mock(return_value=True)

        self.assertTrue(App._tray_toggle_pause(app))

        app._tray_pause.assert_called_once_with()
        app._tray_resume.assert_not_called()

    def test_manual_pause_intent_uses_coordinator_before_compatibility_settings(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app.settings = {"manual_paused": True, "paused": True}
        app._runtime_state = mock.Mock()
        app._runtime_state.snapshot.manual_paused = False

        self.assertFalse(App._manual_pause_intent(app))

    def test_manual_pause_intent_falls_back_to_compatibility_settings(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app.settings = {"manual_paused": True, "paused": False}
        app._runtime_state = None

        self.assertTrue(App._manual_pause_intent(app))

    def test_diagnostic_status_uses_effective_runtime_pause(self):
        from types import SimpleNamespace
        from focuscheck.app import App

        app = App.__new__(App)
        app.settings = {"paused": False}
        app.guard = mock.Mock()
        app.guard.diagnostics.return_value = {"healthy": True}
        app.lifecycle = mock.Mock()
        app.lifecycle.phase = "ready"
        runtime_view = SimpleNamespace(
            effective_pause=True,
            snooze_active=True,
            guard_reasons=frozenset({"lock"}),
            revision=4,
            effective_pause_reason="snooze",
            transition_sink_failures=0,
        )
        class RuntimeState:
            def snapshot_view(self):
                return runtime_view

        app._runtime_state = RuntimeState()
        app._engine = object()
        app._engine_shutdown = False
        app._current_prompt = None
        app._using_pystray = False
        app._native_tray_fallback_active = False

        with mock.patch("focuscheck.doctor.get_anomalies", return_value=[]), mock.patch(
            "focuscheck.settings.schema.get_settings_schema", return_value={"x": object()}
        ), mock.patch.object(App, "_data_root", return_value="<runtime-root>"):
            snapshot = App._diagnostic_status_snapshot(app)

        self.assertTrue(snapshot["paused"])
        self.assertTrue(snapshot["effective_paused"])
        self.assertEqual("snooze", snapshot["pause_reason"])

    def test_snooze_reminder_ignores_manual_pause_without_snooze_expiry(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app.settings = {
            "snooze_reminder_enabled": True,
            "paused": True,
            "snooze_until_utc": "",
        }
        app._snooze_reminder_next_mono = 0.0
        app._snooze_reminder_dialog = None

        with mock.patch("focuscheck.app.SnoozeReminderDialog") as dialog_cls:
            App._maybe_show_snooze_reminder(app)

        self.assertEqual(0.0, app._snooze_reminder_next_mono)
        dialog_cls.assert_not_called()

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

    def test_tray_clear_logs_warns_when_audit_is_not_durable(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app._call_on_ui_thread = lambda callback: callback()
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                mock.patch("focuscheck.app.get_data_dir", return_value=temp_dir),
                mock.patch("focuscheck.app.messagebox.askyesno", return_value=True),
                mock.patch("focuscheck.app.messagebox.showwarning") as warning,
                mock.patch("focuscheck.utils.data_export.clear_data", return_value={
                    "files": [{"deleted": True}], "audit_written": False,
                }),
            ):
                self.assertTrue(App._tray_clear_logs(app))
        warning.assert_called_once()

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

    def test_tray_retention_warns_when_audit_is_not_durable(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app._call_on_ui_thread = lambda callback: callback()
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                mock.patch("focuscheck.app.get_data_dir", return_value=temp_dir),
                mock.patch("tkinter.simpledialog.askinteger", return_value=30),
                mock.patch("focuscheck.app.messagebox.showwarning") as warning,
                mock.patch("focuscheck.utils.data_retention.apply_retention", return_value=[{
                    "deleted": True, "audit_written": False,
                }]),
            ):
                self.assertTrue(App._tray_retain_logs(app))
        warning.assert_called_once()

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

    def test_operational_event_recording_is_failure_isolated(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app._event_ledger = mock.Mock()
        App._record_operational_event(app, "prompt", event="opened", outcome="started")
        app._event_ledger.append.assert_called_once_with(
            "prompt", {"event": "opened", "outcome": "started"}
        )

        app._event_ledger.append.side_effect = RuntimeError("ledger unavailable")
        App._record_operational_event(app, "prompt", event="closed", outcome="failed")

    def test_mainloop_failure_runs_full_cleanup_without_supervisor_stop(self):
        from focuscheck.app import App
        from focuscheck.runtime.lifecycle import LifecycleCoordinator, LifecyclePhase

        app = App.__new__(App)
        app.lifecycle = LifecycleCoordinator()
        app.lifecycle.transition(LifecyclePhase.STARTING)
        app.lifecycle.transition(LifecyclePhase.READY)
        app.root = mock.Mock()
        app.root.mainloop.side_effect = RuntimeError("mainloop failed")
        app._shutdown_cleanup_complete = False
        app._shutdown_requested = False
        app._runtime_state = mock.Mock()
        app._current_prompt = None
        app._gentle_reminder_dialog = None
        app._engine_shutdown = False
        engine = mock.Mock()
        app._engine = engine
        app._timers = mock.Mock()
        app._tray = mock.Mock()
        app._winwatch = mock.Mock()
        app._request_supervisor_stop = mock.Mock()

        with self.assertRaisesRegex(RuntimeError, "mainloop failed"):
            app.run()

        app._runtime_state.request_shutdown.assert_called_once_with()
        engine.shutdown.assert_called_once_with()
        app._timers.close.assert_called_once_with()
        app._tray.stop.assert_called_once_with()
        app._winwatch.close.assert_called_once_with()
        app.root.destroy.assert_called_once_with()
        app._request_supervisor_stop.assert_not_called()
        snapshot = app.lifecycle.snapshot()
        self.assertEqual("stopped", snapshot["phase"])
        self.assertEqual("RuntimeError", snapshot["error_type"])

    def test_cleanup_continues_after_failure_in_each_owned_stage(self):
        from focuscheck.app import App

        stages = ("runtime", "prompt", "gentle", "engine", "timers", "tray", "watcher", "root")
        for failed_stage in stages:
            with self.subTest(failed_stage=failed_stage):
                app = App.__new__(App)
                app._shutdown_cleanup_complete = False
                app._runtime_state = mock.Mock()
                app._current_prompt = None
                app._gentle_reminder_dialog = None
                app._engine_shutdown = False
                app._engine = mock.Mock()
                app._timers = mock.Mock()
                app._tray = mock.Mock()
                app._winwatch = mock.Mock()
                app.root = mock.Mock()
                methods = {
                    "prompt": "_close_current_prompt_for_shutdown",
                    "gentle": "_close_gentle_reminder",
                    "engine": "_shutdown_engine",
                }
                for stage, method_name in methods.items():
                    setattr(app, method_name, mock.Mock(side_effect=RuntimeError(stage) if stage == failed_stage else None))
                if failed_stage == "runtime":
                    app._runtime_state.request_shutdown.side_effect = RuntimeError("runtime")
                if failed_stage == "timers":
                    app._timers.close.side_effect = RuntimeError("timers")
                if failed_stage == "tray":
                    app._tray.stop.side_effect = RuntimeError("tray")
                if failed_stage == "watcher":
                    app._winwatch.close.side_effect = RuntimeError("watcher")
                if failed_stage == "root":
                    app.root.destroy.side_effect = RuntimeError("root")

                App._cleanup_runtime(app, reason="failure_injection", request_supervisor=False)

                app._runtime_state.request_shutdown.assert_called_once_with()
                app._close_current_prompt_for_shutdown.assert_called_once_with()
                app._close_gentle_reminder.assert_called_once_with()
                app._shutdown_engine.assert_called_once_with()
                app._timers.close.assert_called_once_with()
                app._tray.stop.assert_called_once_with()
                app._winwatch.close.assert_called_once_with()
                app.root.destroy.assert_called_once_with()

    def test_constructor_failure_cleans_partial_resources_and_reraises(self):
        from focuscheck.app import App
        from focuscheck.runtime.lifecycle import LifecycleCoordinator, LifecyclePhase

        partial = {}

        def fail_after_partial_setup(instance, *, force_start=False):
            instance.lifecycle = LifecycleCoordinator()
            instance.lifecycle.transition(LifecyclePhase.STARTING, reason="test")
            instance.root = mock.Mock()
            instance._timers = mock.Mock()
            instance._runtime_state = mock.Mock()
            instance._engine = mock.Mock()
            instance._engine_shutdown = False
            instance._current_prompt = None
            instance._gentle_reminder_dialog = None
            instance._tray = mock.Mock()
            instance._winwatch = mock.Mock()
            instance._request_supervisor_stop = mock.Mock()
            partial["app"] = instance
            partial["engine"] = instance._engine
            raise RuntimeError("startup dependency failed")

        with mock.patch.object(App, "_initialize", fail_after_partial_setup):
            with self.assertRaisesRegex(RuntimeError, "startup dependency failed"):
                App()

        partial["engine"].shutdown.assert_called_once_with()
        # The remaining owned services are cleaned despite the constructor
        # raising, and startup failure is not reported as intentional exit.
        app = partial["app"]
        app._runtime_state.request_shutdown.assert_called_once_with()
        app._timers.close.assert_called_once_with()
        app._tray.stop.assert_called_once_with()
        app._winwatch.close.assert_called_once_with()
        app.root.destroy.assert_called_once_with()
        app._request_supervisor_stop.assert_not_called()
        snapshot = app.lifecycle.snapshot()
        self.assertEqual("stopped", snapshot["phase"])
        self.assertEqual("RuntimeError", snapshot["error_type"])

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

    def test_shutdown_closes_snooze_reminder_before_root_destroy(self):
        from focuscheck.app import App

        events = []
        app = App.__new__(App)
        app._shutdown_cleanup_complete = False
        app.lifecycle = None
        app._runtime_state = None
        app._close_current_prompt_for_shutdown = lambda: events.append("prompt")
        app._close_snooze_confirmation = lambda: events.append("snooze_confirmation")
        app._close_snooze_reminder = lambda: events.append("snooze")
        app._close_gentle_reminder = lambda: events.append("gentle")
        app._close_diagnostic_status_window = lambda: events.append("diagnostic_status")
        app._shutdown_engine = lambda: events.append("engine")
        app._timers = mock.Mock()
        app._tray = None
        app._winwatch = None
        app.root = mock.Mock()
        App._cleanup_runtime(app, reason="test", request_supervisor=False)

        self.assertEqual(
            ["prompt", "snooze_confirmation", "snooze", "gentle", "diagnostic_status", "engine"],
            events,
        )
        app.root.destroy.assert_called_once_with()

    def test_direct_cleanup_does_not_warn_about_missing_supervisor(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app._shutdown_cleanup_complete = False
        app.lifecycle = None
        app._runtime_state = None
        app._close_current_prompt_for_shutdown = mock.Mock()
        app._close_snooze_confirmation = mock.Mock()
        app._close_snooze_reminder = mock.Mock()
        app._close_gentle_reminder = mock.Mock()
        app._close_diagnostic_status_window = mock.Mock()
        app._shutdown_engine = mock.Mock()
        app._timers = mock.Mock()
        app._tray = None
        app._winwatch = None
        app.root = mock.Mock()

        with mock.patch.dict(os.environ, {}, clear=True), mock.patch(
            "focuscheck.app.get_logger"
        ) as logger:
            App._cleanup_runtime(app, reason="direct_exit", request_supervisor=True)

        logger.return_value.warning.assert_not_called()
        app.root.destroy.assert_called_once_with()

    def test_diagnostic_status_close_clears_reference(self):
        from focuscheck.app import App

        app = App.__new__(App)
        window = mock.Mock()
        app._diagnostic_status_window = window

        App._close_diagnostic_status_window(app)

        window.destroy.assert_called_once_with()
        self.assertIsNone(app._diagnostic_status_window)

    def test_prompt_visibility_recovery_close_uses_full_cleanup_contract(self):
        from focuscheck.app import App

        events = []

        class Prompt:
            _closed = False

            def winfo_exists(self):
                return True

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

        App._close_current_prompt(app, source="visibility_recovery")

        self.assertEqual(["camera", "timers", "overlays", "destroy"], events)
        self.assertIsNone(app._current_prompt)

    def test_prompt_completion_cancels_owned_observer_timers(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app._current_prompt = None
        app._timers = mock.Mock()
        app._prompt_visibility_timer_id = None
        app._prompt_closed_timer_id = None

        App._on_prompt_done(app)

        app._timers.cancel.assert_any_call("prompt-visible")
        app._timers.cancel.assert_any_call("prompt-closed")

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
        app._runtime_state.is_effectively_paused.return_value = True
        app._refresh_guard_state = mock.Mock(return_value=False)
        app._schedule_next = mock.Mock()

        with mock.patch("focuscheck.app.load_settings", side_effect=AssertionError("hot-path reload")):
            App._maybe_show_prompt(app)

        app._runtime_state.refresh_from_settings.assert_called_once_with(app.settings)
        app._runtime_state.is_effectively_paused.assert_called_once_with()
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

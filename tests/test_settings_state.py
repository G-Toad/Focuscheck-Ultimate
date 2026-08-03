"""Settings and state semantics tests."""

from __future__ import annotations

import unittest
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock


class SettingsValidationTests(unittest.TestCase):
    def test_validate_settings_clamps_and_preserves_unknown_keys(self):
        from focuscheck.settings.manager import validate_settings

        settings = validate_settings(
            {
                "interval_seconds": 1,
                "max_intensity_level": 99,
                "monitoring_mode": "bad",
                "ui_scale_percent": 500,
                "future_plugin_key": "kept",
            }
        )

        self.assertEqual(10, settings["interval_seconds"])
        self.assertEqual(3, settings["max_intensity_level"])
        self.assertEqual("v1", settings["monitoring_mode"])
        self.assertEqual(150, settings["ui_scale_percent"])
        self.assertEqual("kept", settings["future_plugin_key"])

    def test_validate_settings_rejects_impossible_calendar_dates(self):
        from focuscheck.settings.manager import validate_settings

        settings = validate_settings({"biodata_birthdate": "2024-02-31"})
        self.assertEqual("2005-01-01", settings["biodata_birthdate"])

    def test_validate_settings_parses_string_booleans(self):
        from focuscheck.settings.manager import validate_settings

        settings = validate_settings({"paused": "false", "force_always_on": "false", "tray_exit_button_enabled": "no", "overlays_enabled": "off"})

        self.assertFalse(settings["paused"])
        self.assertFalse(settings["force_always_on"])
        self.assertFalse(settings["tray_exit_button_enabled"])
        self.assertFalse(settings["overlays_enabled"])

    def test_legacy_pause_state_migrates_manual_intent_separately_from_snooze(self):
        from focuscheck.settings.manager import validate_settings

        legacy_manual = validate_settings({"paused": True, "snooze_until_utc": ""})
        legacy_snooze = validate_settings({"paused": True, "snooze_until_utc": "2030-01-01T00:05:00+00:00"})

        self.assertTrue(legacy_manual["manual_paused"])
        self.assertFalse(legacy_snooze["manual_paused"])
        self.assertTrue(legacy_snooze["paused"])

    def test_validate_settings_parses_every_boolean_default(self):
        from focuscheck.settings.defaults import DEFAULT_SETTINGS
        from focuscheck.settings.manager import validate_settings
        boolean_keys = [key for key, value in DEFAULT_SETTINGS.items() if isinstance(value, bool)]
        false_values = validate_settings({key: "false" for key in boolean_keys})
        true_values = validate_settings({key: "true" for key in boolean_keys})
        self.assertTrue(all(false_values[key] is False for key in boolean_keys), false_values)
        self.assertTrue(all(true_values[key] is True for key in boolean_keys), true_values)

    def test_website_flags_use_canonical_domains_and_boolean_coercion(self):
        from focuscheck.settings.manager import validate_settings

        settings = validate_settings({
            "website_flags": [
                {"domain": " HTTPS://Bücher.Example./ ", "enabled": "false", "allow_once": "true"},
                {"domain": "example.com:443"},
                {"domain": "*.example.com"},
                {"domain": "https://example.com/path"},
                {"domain": "2001:db8::1"},
            ]
        })

        self.assertEqual(
            [{
                "domain": "xn--bcher-kva.example",
                "enabled": False,
                "severity": 1,
                "cooldown_minutes": 5,
                "allow_once": True,
                "last_dismissed": None,
            }, {
                "domain": "2001:db8::1",
                "enabled": True,
                "severity": 1,
                "cooldown_minutes": 5,
                "allow_once": False,
                "last_dismissed": None,
            }],
            settings["website_flags"],
        )

    def test_default_settings_are_registered(self):
        from focuscheck.settings.defaults import DEFAULT_SETTINGS
        from focuscheck.settings.registry import SETTINGS_REGISTRY

        missing = sorted(set(DEFAULT_SETTINGS) - set(SETTINGS_REGISTRY))
        self.assertEqual([], missing)

    def test_legacy_settings_are_migrated_to_current_schema(self):
        from focuscheck.settings.migrations import CURRENT_SETTINGS_SCHEMA_VERSION, migrate_settings

        migrated = migrate_settings({"settings_schema_version": 1, "snooze_until": "2030-01-01T00:00:00+00:00"})
        self.assertEqual(CURRENT_SETTINGS_SCHEMA_VERSION, migrated["settings_schema_version"])
        self.assertEqual(migrated["snooze_until"], migrated["snooze_until_utc"])

    def test_validate_settings_clamps_stage5_timing_alpha_and_engine(self):
        from focuscheck.settings.defaults import DEFAULT_SETTINGS
        from focuscheck.settings.manager import validate_settings

        settings = validate_settings(
            {
                "overdrive_stage5_after_seconds": "0",
                "overdrive_stage5_hold_after_seconds": "-10",
                "overdrive_stage5_slow_dim_seconds": "0",
                "overdrive_stage5_dim_max_alpha": "2.0",
                "overdrive_stage5_engine": "invalid",
            }
        )

        self.assertEqual(5, settings["overdrive_stage5_after_seconds"])
        self.assertEqual(0, settings["overdrive_stage5_hold_after_seconds"])
        self.assertEqual(1, settings["overdrive_stage5_slow_dim_seconds"])
        self.assertEqual(DEFAULT_SETTINGS["overdrive_stage5_dim_max_alpha"], settings["overdrive_stage5_dim_max_alpha"])
        self.assertEqual("overlay", settings["overdrive_stage5_engine"])

        settings = validate_settings(
            {
                "overdrive_stage5_dim_max_alpha": "0.5",
                "overdrive_stage5_engine": "GAMMA",
            }
        )

        self.assertEqual(0.5, settings["overdrive_stage5_dim_max_alpha"])
        self.assertEqual("gamma", settings["overdrive_stage5_engine"])


class FeatureGateTests(unittest.TestCase):
    def test_pause_gate_respects_force_always_on(self):
        from focuscheck.settings.gates import is_pause_enabled

        self.assertFalse(is_pause_enabled({"force_always_on": True, "pause_when_inactive_or_lid_closed": True}))
        self.assertTrue(is_pause_enabled({"force_always_on": False, "pause_when_inactive_or_lid_closed": True}))
        self.assertTrue(is_pause_enabled({"force_always_on": False, "pause_when_inactive_or_lid_closed": False, "pause_on_lock": True}))
        self.assertFalse(is_pause_enabled({"force_always_on": False, "pause_when_inactive_or_lid_closed": False, "pause_on_lock": False, "pause_on_idle": False, "pause_on_lid_closed": False, "pause_on_sleep": False}))

    def test_exit_gate_respects_tray_setting(self):
        from focuscheck.settings.gates import is_exit_enabled

        self.assertTrue(is_exit_enabled({}))
        self.assertFalse(is_exit_enabled({"tray_exit_button_enabled": False}))

    def test_overlay_gate_has_default_setting(self):
        from focuscheck.settings.defaults import DEFAULT_SETTINGS
        from focuscheck.settings.gates import are_overlays_enabled

        self.assertIn("overlays_enabled", DEFAULT_SETTINGS)
        self.assertTrue(are_overlays_enabled(DEFAULT_SETTINGS))
        self.assertFalse(are_overlays_enabled({"overlays_enabled": False}))

    def test_pause_guard_respects_fake_windows_lock_and_sleep_events(self):
        from focuscheck.ui.guards import PauseGuard

        settings = {
            "force_always_on": False,
            "pause_when_inactive_or_lid_closed": False,
            "pause_on_idle": False,
            "pause_on_lid_closed": False,
            "pause_on_lock": True,
            "pause_on_sleep": True,
        }
        guard = PauseGuard(lambda: settings)
        guard._os = "windows"

        self.assertFalse(guard.should_pause())

        guard.set_locked(True)
        self.assertTrue(guard.should_pause())

        guard.set_locked(False)
        self.assertFalse(guard.should_pause())

        guard.set_sleeping(True)
        self.assertTrue(guard.should_pause())

        guard.set_sleeping(False)
        self.assertFalse(guard.should_pause())

    def test_windows_idle_guard_declares_pointer_width_and_wrap_safe_ticks(self):
        import ctypes
        from focuscheck.ui.guards import PauseGuard

        class Api:
            def __init__(self, result):
                self.result = result
                self.argtypes = None
                self.restype = None

            def __call__(self, pointer=None):
                if pointer is not None:
                    pointer._obj.dwTime = self.result
                return 1

        get_last_input = Api(0xFFFFFFF0)
        get_tick_count = Api(0x00000010)
        kernel32 = type("Kernel", (), {"GetTickCount64": get_tick_count})()
        user32 = type("User", (), {"GetLastInputInfo": get_last_input})()
        windll = type("Windll", (), {"user32": user32, "kernel32": kernel32})()
        settings = {"pause_on_idle": True, "inactive_as_sleep_seconds": 0}
        guard = PauseGuard(lambda: settings)
        guard._os = "windows"
        with mock.patch("focuscheck.ui.guards.platform.system", return_value="Windows"), mock.patch(
            "focuscheck.ui.guards.ctypes.windll", windll
        ):
            self.assertTrue(guard._looks_inactive_by_idle())
        self.assertEqual([], get_tick_count.argtypes)
        self.assertIs(ctypes.c_ulonglong, get_tick_count.restype)

    def test_windows_idle_guard_exposes_native_api_failure_diagnostics(self):
        from focuscheck.ui.guards import PauseGuard

        class User32:
            def GetLastInputInfo(self, _info):
                return 0

        class Kernel32:
            GetTickCount64 = lambda self: 100

        class Windll:
            user32 = User32()
            kernel32 = Kernel32()

        guard = PauseGuard(lambda: {"pause_on_idle": True, "inactive_as_sleep_seconds": 45})
        guard._os = "windows"
        with mock.patch("focuscheck.ui.guards.platform.system", return_value="Windows"), \
                mock.patch("focuscheck.ui.guards.ctypes.windll", Windll()):
            self.assertFalse(guard._looks_inactive_by_idle())

        diagnostics = guard.diagnostics()
        self.assertFalse(diagnostics["healthy"])
        self.assertIn(diagnostics["last_source"], {"windows.last_input_info", "windows.idle"})


class StartupStateTests(unittest.TestCase):
    def test_resolve_initial_monitoring_state_requires_explicit_force_start(self):
        import os
        from unittest import mock
        from focuscheck.app import resolve_initial_monitoring_state

        with mock.patch.dict(os.environ, {"FOCUSCHECK_START_STOP_MODE": "paused"}, clear=False):
            self.assertEqual((False, "env_mode_stopped"), resolve_initial_monitoring_state({}))

        with mock.patch.dict(os.environ, {"FOCUSCHECK_FORCE_STARTED": "1"}, clear=False):
            self.assertEqual((True, "default_force_started"), resolve_initial_monitoring_state({}))
            self.assertEqual((False, "persisted_paused"), resolve_initial_monitoring_state({"paused": True}))

        self.assertEqual(
            (True, "explicit_force_start"),
            resolve_initial_monitoring_state({"paused": True}, force_start=True),
        )

    def test_resolve_initial_monitoring_state_preserves_persisted_pause(self):
        import os
        from unittest import mock
        from focuscheck.app import resolve_initial_monitoring_state

        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual((False, "persisted_paused"), resolve_initial_monitoring_state({"paused": True}))

    def test_resolve_initial_monitoring_state_prefers_explicit_manual_intent(self):
        import os
        from unittest import mock
        from focuscheck.app import resolve_initial_monitoring_state

        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                (True, "default_force_started"),
                resolve_initial_monitoring_state({"paused": True, "manual_paused": False}),
            )


class FakeRoot:
    def __init__(self):
        self.cancelled = []
        self.scheduled = []
        self.next_id = 1

    def after(self, delay_ms, callback):
        self.next_id += 1
        self.scheduled.append((delay_ms, callback))
        return f"timer-{self.next_id}"

    def after_cancel(self, timer_id):
        self.cancelled.append(timer_id)


class SnoozeStateTests(unittest.TestCase):
    def test_app_persistence_boundary_applies_committed_settings_to_runtime(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app.settings = {"interval_seconds": 60, "settings_revision": 1}
        app._runtime_state = mock.Mock()
        committed = {"interval_seconds": 120, "settings_revision": 2}
        result = type(
            "Result", (), {"durable_write": True, "committed_settings": committed}
        )()

        with mock.patch("focuscheck.app.save_settings", return_value=result) as save:
            returned = App._persist_settings_draft(app, {"interval_seconds": 999})

        self.assertIs(returned, result)
        save.assert_called_once_with({"interval_seconds": 999})
        self.assertEqual(committed, app.settings)
        app._runtime_state.refresh_from_settings.assert_called_once_with(committed)

    def test_app_persistence_boundary_uses_composed_settings_saver(self):
        from focuscheck.app import App
        from focuscheck.runtime.dependencies import AppDependencies

        app = App.__new__(App)
        app.settings = {"interval_seconds": 60, "settings_revision": 1}
        app._runtime_state = mock.Mock()
        committed = {"interval_seconds": 120, "settings_revision": 2}
        result = type(
            "Result", (), {"durable_write": True, "committed_settings": committed}
        )()
        saver = mock.Mock(return_value=result)
        app._dependencies = AppDependencies(settings_saver=saver)

        returned = App._persist_settings_draft(app, {"interval_seconds": 999})

        self.assertIs(result, returned)
        saver.assert_called_once_with({"interval_seconds": 999})
        self.assertEqual(committed, app.settings)
        app._runtime_state.refresh_from_settings.assert_called_once_with(committed)

    def test_schedule_next_survives_expired_timer_id(self):
        from focuscheck.app import App

        class Root(FakeRoot):
            def after_cancel(self, _timer_id):
                raise RuntimeError("expired timer")

        app = App.__new__(App)
        app.root = Root()
        app.settings = {"interval_seconds": 60}
        app._scheduled = "expired"
        app._next_total_s = None
        app._next_due_mono = None

        App._schedule_next(app, 1234)

        self.assertEqual(1, len(app.root.scheduled))
        self.assertEqual(1234, app.root.scheduled[0][0])
        self.assertEqual("timer-2", app._scheduled)

    def test_cancel_snooze_clears_timer_and_persisted_expiry(self):
        from focuscheck.app import App
        with mock.patch("focuscheck.app.save_settings") as save_settings:
            app = App.__new__(App)
            app.root = FakeRoot()
            app._snooze_unpause_timer_id = "timer-1"
            app.settings = {"snooze_until_utc": "2026-07-20T10:00:00+00:00"}

            App._cancel_snooze(app)

            self.assertEqual(["timer-1"], app.root.cancelled)
            self.assertIsNone(app._snooze_unpause_timer_id)
            self.assertEqual("", app.settings["snooze_until_utc"])
            save_settings.assert_called_once()

    def test_startup_snooze_expiry_uses_timer_registry(self):
        from focuscheck.app import App
        app = App.__new__(App)
        app.root = FakeRoot()
        app._timers = mock.Mock()
        app._timers.callback_id.return_value = "registry-timer-1"
        app.settings = {
            "snooze_until_utc": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
            "paused": False,
        }
        app._snooze_unpause_timer_id = None
        app._set_paused = mock.Mock()
        app._schedule_next = mock.Mock()

        with mock.patch("focuscheck.app.save_settings"):
            App._reconcile_snooze_state_on_startup(app)

        self.assertIsNotNone(app._snooze_unpause_timer_id)
        app._timers.schedule.assert_called_once()
        self.assertEqual("snooze-expiry", app._timers.schedule.call_args.args[0])
        self.assertIsNotNone(app._timers.callback_id("snooze-expiry"))
        self.assertEqual([], app.root.scheduled)

    def test_startup_snooze_reconciliation_uses_injected_clock(self):
        from focuscheck.app import App
        from focuscheck.runtime.state import RuntimeStateCoordinator
        from focuscheck.utils.clock import FakeClock

        clock = FakeClock(datetime(2030, 1, 1, tzinfo=timezone.utc))
        app = App.__new__(App)
        app.root = FakeRoot()
        app._timers = mock.Mock()
        app._timers.callback_id.return_value = "registry-timer-2"
        app._runtime_state = RuntimeStateCoordinator(
            {"paused": False, "snooze_until_utc": ""}, clock=clock
        )
        app.settings = {
            "snooze_until_utc": (clock.now_utc() + timedelta(minutes=5)).isoformat(),
            "paused": False,
        }
        app._snooze_unpause_timer_id = None
        app._set_paused = mock.Mock()
        app._schedule_next = mock.Mock()

        with mock.patch("focuscheck.app.save_settings"):
            App._reconcile_snooze_state_on_startup(app)

        self.assertEqual(300000, app._timers.schedule.call_args.args[1])

    def test_expired_startup_snooze_preserves_manual_pause(self):
        from focuscheck.app import App
        from focuscheck.runtime.state import RuntimeStateCoordinator
        from focuscheck.utils.clock import FakeClock

        clock = FakeClock(datetime(2030, 1, 1, tzinfo=timezone.utc))
        settings = {
            "paused": True,
            "snooze_until_utc": (clock.now_utc() - timedelta(minutes=1)).isoformat(),
        }
        app = App.__new__(App)
        app.settings = settings
        app._runtime_state = RuntimeStateCoordinator(settings, clock=clock)
        app._snooze_unpause_timer_id = None

        with mock.patch("focuscheck.app.save_settings"):
            App._reconcile_snooze_state_on_startup(app)

        self.assertTrue(app._runtime_state.snapshot.manual_paused)
        self.assertEqual("", settings["snooze_until_utc"])
        self.assertTrue(settings["paused"])

    def test_expired_startup_snooze_does_not_create_manual_pause(self):
        from focuscheck.app import App
        from focuscheck.runtime.state import RuntimeStateCoordinator
        from focuscheck.utils.clock import FakeClock

        clock = FakeClock(datetime(2030, 1, 1, tzinfo=timezone.utc))
        settings = {
            "paused": True,
            "manual_paused": False,
            "snooze_until_utc": (clock.now_utc() - timedelta(minutes=1)).isoformat(),
        }
        app = App.__new__(App)
        app.settings = settings
        app._force_start = False
        app._runtime_state = RuntimeStateCoordinator(settings, clock=clock)
        app._snooze_unpause_timer_id = None
        app._set_paused = mock.Mock()

        with mock.patch("focuscheck.app.save_settings"):
            App._apply_initial_monitoring_state(app)

        app._set_paused.assert_called_once_with(False, source="startup_default_force_started")
        self.assertFalse(app._runtime_state.snapshot.manual_paused)
        self.assertFalse(settings["paused"])

    def test_expired_startup_snooze_fallback_preserves_manual_pause(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app.settings = {
            "paused": True,
            "snooze_until_utc": "2000-01-01T00:00:00+00:00",
        }
        app._snooze_unpause_timer_id = None

        with mock.patch("focuscheck.app.save_settings") as save_settings:
            App._reconcile_snooze_state_on_startup(app)

        self.assertTrue(app.settings["paused"])
        self.assertEqual("", app.settings["snooze_until_utc"])
        save_settings.assert_called_once()

    def test_cancel_snooze_timer_cancels_registry_without_legacy_id(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app._timers = mock.Mock()
        app._snooze_unpause_timer_id = None

        App._cancel_snooze_timer(app)

        app._timers.cancel.assert_called_once_with("snooze-expiry")
        self.assertIsNone(app._snooze_unpause_timer_id)

    def test_snooze_expiry_callback_preserves_manual_pause(self):
        from focuscheck.app import App
        from focuscheck.runtime.state import RuntimeStateCoordinator

        settings = {"paused": True, "snooze_until_utc": "2030-01-01T00:05:00+00:00"}
        app = App.__new__(App)
        app.settings = settings
        app._runtime_state = RuntimeStateCoordinator(settings)
        app._snooze_unpause_timer_id = "timer-1"
        app._schedule_next = mock.Mock()

        with mock.patch("focuscheck.app.save_settings"):
            App._expire_snooze(app)

        self.assertTrue(app._runtime_state.snapshot.manual_paused)
        self.assertTrue(settings["paused"])
        self.assertEqual("", settings["snooze_until_utc"])
        app._schedule_next.assert_called_once_with(0)

    def test_snooze_expiry_fallback_preserves_manual_pause(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app.settings = {
            "paused": True,
            "snooze_until_utc": "2030-01-01T00:05:00+00:00",
        }
        app._snooze_unpause_timer_id = "timer-1"
        app._schedule_next = mock.Mock()

        with mock.patch("focuscheck.app.save_settings") as save_settings:
            App._expire_snooze(app)

        self.assertTrue(app.settings["paused"])
        self.assertEqual("", app.settings["snooze_until_utc"])
        save_settings.assert_called_once()

    def test_snooze_state_preserves_manual_pause_and_expires_without_clearing_it(self):
        from focuscheck.runtime.state import RuntimeStateCoordinator

        settings = {"paused": True, "snooze_until_utc": ""}
        state = RuntimeStateCoordinator(settings)
        until = datetime.now(timezone.utc) + timedelta(minutes=5)
        self.assertTrue(state.set_snooze_until(until))
        self.assertTrue(state.snapshot.manual_paused)
        self.assertTrue(state.snapshot.snooze_active())
        self.assertTrue(state.clear_snooze())
        self.assertTrue(state.snapshot.manual_paused)
        self.assertTrue(settings["paused"])
        self.assertEqual("", settings["snooze_until_utc"])

    def test_expired_snooze_does_not_persist_as_paused(self):
        from focuscheck.runtime.state import RuntimeStateCoordinator
        from focuscheck.utils.clock import FakeClock

        clock = FakeClock(datetime(2030, 1, 1, tzinfo=timezone.utc))
        settings = {"paused": False, "snooze_until_utc": ""}
        state = RuntimeStateCoordinator(settings, clock=clock)

        self.assertTrue(state.set_snooze_until(clock.now_utc() + timedelta(seconds=1)))
        clock.advance(2)
        self.assertTrue(state.set_manual_paused(True))
        self.assertTrue(state.set_manual_paused(False))
        self.assertFalse(settings["paused"])

    def test_heartbeat_reports_manual_pause(self):
        import json
        import tempfile
        from pathlib import Path
        from focuscheck.app import App

        class Guard:
            def should_pause(self):
                return False

        with tempfile.TemporaryDirectory() as temp_dir, mock.patch("focuscheck.app.HEARTBEAT_PATH", str(Path(temp_dir) / "heartbeat.json")):
            app = App.__new__(App)
            app.settings = {"paused": True, "pause_when_inactive_or_lid_closed": True, "interval_seconds": 60}
            app.guard = Guard()

            App._write_heartbeat(app)
            payload = json.loads(Path(temp_dir, "heartbeat.json").read_text(encoding="utf-8"))

        self.assertTrue(payload["paused"])
        self.assertTrue(payload["manual_paused"])
        self.assertFalse(payload["guard_paused"])
        self.assertEqual("manual", payload["pause_reason"])

    def test_app_fake_lock_sleep_resume_events_update_guard_and_schedule(self):
        from focuscheck.app import App

        class Guard:
            def __init__(self):
                self.locked = None
                self.sleeping = None

            def set_locked(self, value):
                self.locked = bool(value)

            def set_sleeping(self, value):
                self.sleeping = bool(value)

        app = App.__new__(App)
        app.guard = Guard()
        app.settings = {"pause_poll_interval_seconds": 5}
        app._last_resume_mono = 0.0
        scheduled = []
        app._schedule_next = lambda delay_ms=None: scheduled.append(delay_ms)

        App._on_pause_event(app, "lock")
        self.assertTrue(app.guard.locked)
        self.assertEqual(5000, scheduled[-1])

        App._on_pause_event(app, "sleep")
        self.assertTrue(app.guard.sleeping)
        self.assertEqual(5000, scheduled[-1])

        App._on_resume_event(app)
        self.assertFalse(app.guard.locked)
        self.assertFalse(app.guard.sleeping)
        self.assertEqual(0, scheduled[-1])

    def test_lock_event_closes_active_prompt_before_polling(self):
        from focuscheck.app import App

        class Guard:
            def set_locked(self, value):
                self.locked = bool(value)

            def set_sleeping(self, value):
                self.sleeping = bool(value)

        class Prompt:
            _closed = False

            def __init__(self):
                self.events = []

            def winfo_exists(self):
                return True

            def _cleanup_camera_feed(self):
                self.events.append("camera")

            def _cleanup_all_timers(self):
                self.events.append("timers")

            def destroy(self):
                self.events.append("destroy")

        app = App.__new__(App)
        app.guard = Guard()
        app.settings = {"pause_poll_interval_seconds": 5}
        prompt = Prompt()
        app._current_prompt = prompt
        app._schedule_next = lambda _delay_ms=None: None

        App._on_pause_event(app, "lock")

        self.assertTrue(app._current_prompt is None)
        self.assertEqual(["camera", "timers", "destroy"], prompt.events)


if __name__ == "__main__":
    unittest.main()

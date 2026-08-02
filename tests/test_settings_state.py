"""Settings and state semantics tests."""

from __future__ import annotations

import unittest
import tempfile
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


class StartupStateTests(unittest.TestCase):
    def test_resolve_initial_monitoring_state_env_overrides(self):
        import os
        from unittest import mock
        from focuscheck.app import resolve_initial_monitoring_state

        with mock.patch.dict(os.environ, {"FOCUSCHECK_START_STOP_MODE": "paused"}, clear=False):
            self.assertEqual((False, "env_mode_stopped"), resolve_initial_monitoring_state({}))

        with mock.patch.dict(os.environ, {"FOCUSCHECK_FORCE_STARTED": "1"}, clear=False):
            self.assertEqual((True, "env_force_started"), resolve_initial_monitoring_state({}))

        with mock.patch.dict(os.environ, {"FOCUSCHECK_START_STOP_MODE": "paused", "FOCUSCHECK_FORCE_STARTED": "1"}, clear=False):
            self.assertEqual((True, "env_force_started"), resolve_initial_monitoring_state({"paused": True}))

    def test_resolve_initial_monitoring_state_preserves_persisted_pause(self):
        import os
        from unittest import mock
        from focuscheck.app import resolve_initial_monitoring_state

        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual((False, "persisted_paused"), resolve_initial_monitoring_state({"paused": True}))


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


if __name__ == "__main__":
    unittest.main()

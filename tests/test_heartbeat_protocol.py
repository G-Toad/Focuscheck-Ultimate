from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class HeartbeatProtocolTests(unittest.TestCase):
    def test_supervisor_rejects_wrong_generation_and_protocol(self):
        from focuscheck_supervisor import FocusCheckSupervisor

        with tempfile.TemporaryDirectory() as temp_dir:
            heartbeat = Path(temp_dir) / "hb.txt"
            supervisor = FocusCheckSupervisor.__new__(FocusCheckSupervisor)
            supervisor.heartbeat_path = heartbeat
            supervisor.child_generation = "current"
            supervisor._heartbeat_grace_deadline = 0.0
            supervisor.child = mock.Mock(pid=123, poll=lambda: None)
            now = "2030-01-01T00:00:00+00:00"
            heartbeat.write_text(json.dumps({
                "protocol_version": 1, "readiness": "ready", "generation": "old",
                "utc": now, "pid": 123,
            }), encoding="utf-8")
            with mock.patch("focuscheck_supervisor.time.time", return_value=1893456000.0):
                self.assertTrue(supervisor._heartbeat_stale())

    def test_app_heartbeat_contains_generation_and_sequence(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app.settings = {"paused": False, "interval_seconds": 60}
        app.guard = mock.Mock()
        app.guard.should_pause.return_value = False
        app._heartbeat_sequence = 0
        app._process_start_utc = "2030-01-01T00:00:00+00:00"
        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.dict(
            "os.environ",
            {"FOCUSCHECK_SUPERVISOR_ID": "sup", "FOCUSCHECK_CHILD_GENERATION": "gen"},
        ), mock.patch("focuscheck.app.HEARTBEAT_PATH", str(Path(temp_dir) / "hb.txt")):
            app._write_heartbeat()
            payload = json.loads((Path(temp_dir) / "hb.txt").read_text(encoding="utf-8"))
        self.assertEqual(1, payload["protocol_version"])
        self.assertEqual("gen", payload["generation"])
        self.assertEqual(1, payload["sequence"])
        self.assertEqual(60, payload["heartbeat_interval_seconds"])
        self.assertEqual("ready", payload["readiness"])

    def test_app_heartbeat_uses_frozen_app_paths_snapshot(self):
        from focuscheck.app import App
        from focuscheck.utils.paths import get_app_paths

        with tempfile.TemporaryDirectory() as app_dir, tempfile.TemporaryDirectory() as other_dir:
            app = App.__new__(App)
            app.paths = get_app_paths(app_dir)
            app.settings = {"paused": False, "interval_seconds": 60}
            app.guard = mock.Mock()
            app.guard.should_pause.return_value = False
            app._heartbeat_sequence = 0
            app._process_start_utc = "2030-01-01T00:00:00+00:00"
            with mock.patch.dict(
                "os.environ",
                {"FOCUSCHECK_SUPERVISOR_ID": "sup", "FOCUSCHECK_CHILD_GENERATION": "gen"},
            ), mock.patch("focuscheck.app.HEARTBEAT_PATH", str(Path(other_dir) / "wrong-hb.txt")):
                app._write_heartbeat()

            self.assertTrue(app.paths.heartbeat.exists())
            self.assertFalse((Path(other_dir) / "wrong-hb.txt").exists())

    def test_supervisor_uses_sequence_receipt_time_not_wall_clock_age(self):
        from focuscheck_supervisor import FocusCheckSupervisor

        with tempfile.TemporaryDirectory() as temp_dir:
            heartbeat = Path(temp_dir) / "hb.txt"
            supervisor = FocusCheckSupervisor.__new__(FocusCheckSupervisor)
            supervisor.heartbeat_path = heartbeat
            supervisor.child_generation = "current"
            supervisor._heartbeat_grace_deadline = 0.0
            supervisor.child = mock.Mock(pid=123, poll=lambda: None)
            payload = {
                "protocol_version": 1,
                "readiness": "ready",
                "generation": "current",
                "utc": "2000-01-01T00:00:00+00:00",
                "pid": 123,
                "process_start_utc": "2030-01-01T00:00:00+00:00",
                "sequence": 1,
                "heartbeat_interval_seconds": 1,
            }
            heartbeat.write_text(json.dumps(payload), encoding="utf-8")
            with mock.patch("focuscheck_supervisor.time.monotonic", side_effect=[0.0, 0.0, 13.0, 13.0]):
                self.assertFalse(supervisor._heartbeat_stale())
                self.assertTrue(supervisor._heartbeat_stale())

    def test_app_heartbeat_write_failure_is_counted_and_throttled(self):
        from focuscheck.app import App

        app = App.__new__(App)
        app.settings = {"paused": False, "interval_seconds": 60}
        app.guard = mock.Mock()
        app.guard.should_pause.return_value = False
        app._heartbeat_sequence = 0
        app._heartbeat_write_failures = 0
        app._last_heartbeat_failure_log_mono = 0.0
        with tempfile.TemporaryDirectory() as temp_dir, mock.patch(
            "focuscheck.app.HEARTBEAT_PATH", str(Path(temp_dir) / "hb.txt")
        ), mock.patch("focuscheck.app.os.replace", side_effect=OSError("disk full")), mock.patch(
            "focuscheck.app.get_logger"
        ) as logger_factory:
            app._write_heartbeat()
            app._write_heartbeat()
            logger = logger_factory.return_value
        self.assertEqual(2, app._heartbeat_write_failures)
        self.assertEqual(2, logger.warning.call_count)

    def test_app_heartbeat_uses_runtime_coordinator_pause_truth(self):
        from focuscheck.app import App
        from focuscheck.utils.clock import FakeClock
        from datetime import datetime, timezone

        clock = FakeClock(datetime(2030, 1, 1, tzinfo=timezone.utc))
        app = App.__new__(App)
        app.settings = {"paused": False, "interval_seconds": 60}
        app.guard = mock.Mock()
        app._runtime_state = mock.Mock()
        app._runtime_state.snapshot.manual_paused = False
        app._runtime_state.snapshot.guard_reasons = {"lock"}
        app._runtime_state.snapshot.snooze_active.return_value = True
        app._runtime_state.clock = clock
        app._runtime_state.is_effectively_paused.return_value = True
        app._heartbeat_sequence = 0
        app._process_start_utc = "2030-01-01T00:00:00+00:00"
        with tempfile.TemporaryDirectory() as temp_dir, mock.patch(
            "focuscheck.app.HEARTBEAT_PATH", str(Path(temp_dir) / "hb.txt")
        ):
            app._write_heartbeat()
            payload = json.loads((Path(temp_dir) / "hb.txt").read_text(encoding="utf-8"))

        app.guard.should_pause.assert_not_called()
        self.assertTrue(payload["effective_paused"])
        self.assertTrue(payload["snooze_active"])
        self.assertEqual(["lock"], payload["guard_reasons"])

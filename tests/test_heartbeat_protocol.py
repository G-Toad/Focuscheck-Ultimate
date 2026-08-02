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
        self.assertEqual("ready", payload["readiness"])

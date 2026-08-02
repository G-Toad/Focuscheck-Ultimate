"""Contracts for the packaged supervisor readiness/stop harness."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class PackagedSupervisorSelfTestTests(unittest.TestCase):
    def test_stop_request_is_generation_bound_and_atomically_written(self):
        from tools.packaged_supervisor_selftest import _write_stop_request

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "supervisor.stop"
            heartbeat = {
                "supervisor_id": "sup-1",
                "generation": "gen-1",
                "process_start_utc": "2030-01-01T00:00:00+00:00",
            }
            with mock.patch("tools.packaged_supervisor_selftest.uuid.uuid4") as uuid4:
                uuid4.return_value.hex = "request-1"
                request_id = _write_stop_request(path, heartbeat, 1234)

            self.assertEqual("request-1", request_id)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(1, payload["protocol_version"])
            self.assertEqual("sup-1", payload["supervisor_id"])
            self.assertEqual("gen-1", payload["generation"])
            self.assertEqual(1234, payload["pid"])
            self.assertFalse(list(path.parent.glob("*.tmp")))


if __name__ == "__main__":
    unittest.main()

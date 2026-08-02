"""Path and CSV logging tests."""

from __future__ import annotations

import csv
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock


class PathHelperTests(unittest.TestCase):
    def test_focus_data_dir_wins_and_choose_path_prefers_legacy(self):
        from focuscheck.utils import paths

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = str(Path(temp_dir) / "data")
            legacy = Path(temp_dir) / "legacy.txt"
            legacy.write_text("legacy", encoding="utf-8")

            with mock.patch.dict(paths.os.environ, {"FOCUS_DATA_DIR": data_dir}), mock.patch.object(paths, "get_base_dir", return_value=temp_dir):
                self.assertEqual(data_dir, paths.get_data_dir())
                self.assertEqual(str(legacy), paths.choose_path("legacy.txt"))
                self.assertEqual(str(Path(data_dir) / "new.txt"), paths.choose_path("new.txt"))

    def test_resource_path_uses_meipass_then_base_dir(self):
        from focuscheck.utils import paths

        with mock.patch.object(paths.sys, "_MEIPASS", "C:\\Bundle", create=True):
            self.assertEqual("C:\\Bundle\\asset.png", paths.resource_path("asset.png"))

        with mock.patch.object(paths.sys, "_MEIPASS", None, create=True), mock.patch.object(paths, "get_base_dir", return_value="C:\\Project"):
            self.assertEqual("C:\\Project\\asset.png", paths.resource_path("asset.png"))


class CsvLoggerTests(unittest.TestCase):
    def test_csv_headers_and_append_rows(self):
        import focuscheck.database.csv_logger as logger

        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = str(Path(temp_dir) / "focus.csv")
            waste_path = str(Path(temp_dir) / "waste.csv")
            focus_path = str(Path(temp_dir) / "study.csv")
            slot = {"utc_start": datetime.now(timezone.utc), "local_minute": "10:00", "mono_start": 0}

            with mock.patch.object(logger, "LOG_PATH", log_path), mock.patch.object(logger, "WASTE_LOG_PATH", waste_path), mock.patch.object(logger, "FOCUS_LOG_PATH", focus_path), mock.patch.object(logger.time, "monotonic", return_value=1):
                self.assertTrue(logger.append_log(response="OK", latency_ms=10, settings={"interval_seconds": 60, "intensify_after_seconds": 15, "overdrive_after_seconds": 60}, intensity_level_reached=1, slot_start_dt=slot, overdrive_deadline_s=60))
                self.assertTrue(logger.append_waste_log(slot_start_dt=slot, latency_ms=20, what="scroll", consequences="", active_task={"id": 1, "title": "Task"}))
                self.assertTrue(logger.append_focus_log(slot_start_dt=slot, latency_ms=30, doing="work", benefits="done", active_task=None))

            with open(log_path, newline="", encoding="utf-8") as f:
                self.assertEqual(2, len(list(csv.reader(f))))
            with open(waste_path, newline="", encoding="utf-8") as f:
                self.assertEqual(2, len(list(csv.reader(f))))
            with open(focus_path, newline="", encoding="utf-8") as f:
                self.assertEqual(2, len(list(csv.reader(f))))

    def test_safe_csv_write_reports_failure_without_raising(self):
        import focuscheck.database.csv_logger as logger

        self.assertFalse(logger._safe_csv_write("bad.csv", lambda: (_ for _ in ()).throw(OSError("boom"))))


if __name__ == "__main__":
    unittest.main()

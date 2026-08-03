"""Path and CSV logging tests."""

from __future__ import annotations

import csv
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock


class PathHelperTests(unittest.TestCase):
    def test_focus_data_dir_wins_over_legacy_files(self):
        from focuscheck.utils import paths

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = str(Path(temp_dir) / "data")
            legacy = Path(temp_dir) / "legacy.txt"
            legacy.write_text("legacy", encoding="utf-8")

            with mock.patch.dict(paths.os.environ, {"FOCUS_DATA_DIR": data_dir}), mock.patch.object(paths, "get_base_dir", return_value=temp_dir):
                self.assertEqual(data_dir, paths.get_data_dir())
                self.assertEqual(str(Path(data_dir) / "legacy.txt"), paths.choose_path("legacy.txt"))
                self.assertEqual(str(Path(data_dir) / "new.txt"), paths.choose_path("new.txt"))

    def test_package_legacy_file_does_not_change_runtime_path(self):
        from focuscheck.utils import paths

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / "data"
            base_dir = Path(temp_dir) / "package"
            base_dir.mkdir()
            (base_dir / "focus_settings.json").write_text("{}", encoding="utf-8")
            with mock.patch.dict(paths.os.environ, {"FOCUS_DATA_DIR": ""}, clear=False), \
                    mock.patch.object(paths, "get_base_dir", return_value=str(base_dir)), \
                    mock.patch.object(paths, "get_data_dir", return_value=str(data_dir)):
                self.assertEqual(str(data_dir / "focus_settings.json"), paths.choose_path("focus_settings.json"))

    def test_resource_path_uses_meipass_then_base_dir(self):
        from focuscheck.utils import paths

        with mock.patch.object(paths.sys, "_MEIPASS", "C:\\Bundle", create=True):
            self.assertEqual("C:\\Bundle\\asset.png", paths.resource_path("asset.png"))

        with mock.patch.object(paths.sys, "_MEIPASS", None, create=True), mock.patch.object(paths, "get_base_dir", return_value="C:\\Project"):
            self.assertEqual("C:\\Project\\asset.png", paths.resource_path("asset.png"))

    def test_data_dir_never_falls_back_to_package_directory(self):
        from focuscheck.utils import paths

        with mock.patch.dict(paths.os.environ, {"FOCUS_DATA_DIR": "", "APPDATA": ""}, clear=False), \
                mock.patch.object(paths, "get_base_dir", return_value="C:\\Installed\\FocusCheck"), \
                mock.patch.object(paths.platform, "system", return_value="Windows"), \
                mock.patch.object(paths.os, "makedirs", side_effect=OSError("read-only")):
            data_dir = paths.get_data_dir()

        self.assertNotEqual("C:\\Installed\\FocusCheck", data_dir)
        self.assertTrue(data_dir.endswith("FocusCheck"))


class CsvLoggerTests(unittest.TestCase):
    def test_logger_uses_composition_root_path_before_first_use(self):
        import focuscheck.utils.logging_utils as logging_utils

        logger = mock.Mock()
        logger.handlers = []
        handler = mock.Mock()
        with tempfile.TemporaryDirectory() as temp_dir, \
                mock.patch.object(logging_utils, "_logger", None), \
                mock.patch.object(logging_utils, "_configured_log_path", None), \
                mock.patch.object(logging_utils.logging, "getLogger", return_value=logger), \
                mock.patch.object(logging_utils, "SafeRotatingFileHandler", return_value=handler) as handler_factory:
            target = Path(temp_dir) / "composed" / "focus_app.log"
            self.assertTrue(logging_utils.configure_log_path(target))
            logging_utils.get_logger()

        handler_factory.assert_called_once()
        self.assertEqual(str(target), handler_factory.call_args.args[0])

    def test_diagnostic_logging_redacts_user_response(self):
        import focuscheck.database.csv_logger as logger

        slot = {"utc_start": datetime.now(timezone.utc), "local_minute": "10:00", "mono_start": 0}
        sink = mock.Mock()
        with mock.patch.object(logger, "get_logger", return_value=sink), \
                mock.patch.object(logger, "LOG_PATH", str(Path(tempfile.gettempdir()) / "focus-privacy-test.csv")), \
                mock.patch.object(logger, "_safe_csv_write", return_value=True):
            logger.append_log(
                response="private response that must not be logged",
                latency_ms=10,
                settings={"interval_seconds": 60, "intensify_after_seconds": 15, "overdrive_after_seconds": 60},
                intensity_level_reached=1,
                slot_start_dt=slot,
                overdrive_deadline_s=60,
            )

        logged = " ".join(str(call) for call in sink.info.call_args_list)
        self.assertNotIn("private response that must not be logged", logged)
        self.assertIn("response_summary", logged)

    def test_log_filter_redacts_rendered_private_fields_and_paths(self):
        import logging
        from focuscheck.utils.logging_utils import PrivacyLogFilter

        record = logging.LogRecord(
            "focuscheck", logging.INFO, __file__, 1,
            "title=%s url=%s path=%s", ("private title", "https://example.test/secret", "C:\\Users\\singh\\private"), None,
        )
        self.assertTrue(PrivacyLogFilter().filter(record))
        rendered = record.getMessage()
        self.assertNotIn("private title", rendered)
        self.assertNotIn("example.test", rendered)
        self.assertNotIn("C:\\Users\\singh", rendered)
        self.assertIn("<redacted>", rendered)

        contextual = logging.LogRecord(
            "focuscheck", logging.INFO, __file__, 1,
            "reason 'private reason' phrase=\"private phrase\"", (), None,
        )
        PrivacyLogFilter().filter(contextual)
        self.assertNotIn("private reason", contextual.getMessage())
        self.assertNotIn("private phrase", contextual.getMessage())

    def test_csv_text_is_safe_from_spreadsheet_formulas(self):
        from focuscheck.database.csv_logger import _excel_safe

        self.assertEqual("'=SUM(A1)", _excel_safe("=SUM(A1)"))
        self.assertEqual("'@cmd", _excel_safe("@cmd"))
        self.assertEqual("normal", _excel_safe("normal"))

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

    def test_jsonl_reflections_bound_records_rotate_and_skip_corrupt_lines(self):
        import focuscheck.database.csv_logger as logger

        with tempfile.TemporaryDirectory() as temp_dir:
            path = str(Path(temp_dir) / "reflections.jsonl")
            with mock.patch.object(logger, "INTERVENTION_REFLECTION_PATH", path), \
                    mock.patch.object(logger, "MAX_JSONL_RECORD_BYTES", 64):
                self.assertFalse(logger.append_intervention_reflection({"text": "x" * 100}))
                self.assertTrue(logger.append_intervention_reflection({"text": "ok"}))
                with open(path, "ab") as handle:
                    handle.write(b"not-json\n")
                    handle.write(b"{\"valid\": true}\n")
                records = list(logger.iter_jsonl_records(path, max_record_bytes=64))

            self.assertEqual([{"text": "ok"}, {"valid": True}], records)

    def test_jsonl_rotation_keeps_bounded_backups(self):
        import focuscheck.database.csv_logger as logger

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "reflections.jsonl"
            path.write_text("x" * 20, encoding="utf-8")
            logger._rotate_jsonl_if_needed(str(path), max_bytes=10, backups=2)
            self.assertFalse(path.exists())
            self.assertTrue(Path(f"{path}.1").exists())


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
import time
import unittest
from unittest import mock
from pathlib import Path

from tools.retention import apply_retention, retention_plan


class RetentionTests(unittest.TestCase):
    def test_plan_selects_old_logs_but_never_settings_or_tasks(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            old = root / "focus_app.log.1"
            old.write_text("old", encoding="utf-8")
            old_time = time.time() - 10 * 86400
            import os
            os.utime(old, (old_time, old_time))
            (root / "focus_settings.json").write_text("{}", encoding="utf-8")
            (root / "focus_tasks.sqlite3").write_text("db", encoding="utf-8")
            plan = retention_plan(root, max_age_days=1, now=time.time())
            self.assertEqual([str(old)], [item["path"] for item in plan])

    def test_dry_run_does_not_delete(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            old = root / "focus_log.csv.1"
            old.write_text("old", encoding="utf-8")
            import os
            old_time = time.time() - 10 * 86400
            os.utime(old, (old_time, old_time))
            apply_retention(root, max_age_days=1, apply=False)
            self.assertTrue(old.exists())

    def test_symlinked_old_log_is_not_selected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "outside.log"
            target.write_text("outside", encoding="utf-8")
            link = root / "focus_app.log.1"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            self.assertEqual([], retention_plan(root, max_age_days=1, now=time.time() + 20 * 86400))
            self.assertTrue(target.exists())

    def test_apply_retention_uses_injected_time_and_writes_metadata_only_audit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            old = root / "focus_log.csv.1"
            old.write_text("private response", encoding="utf-8")
            old_time = 100.0
            import os
            os.utime(old, (old_time, old_time))
            result = apply_retention(root, max_age_days=1, now=old_time + 2 * 86400, apply=True)
            self.assertTrue(result[0]["deleted"])
            audit = (root / "retention_audit.jsonl").read_text(encoding="utf-8")
            self.assertNotIn("private response", audit)
            self.assertIn('"operation":"retention_delete"', audit)
            self.assertIn('"format_version":1', audit)
            self.assertIn('"audit_written":true', audit)

    def test_apply_retention_does_not_delete_file_changed_after_planning(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            old = root / "focus_log.csv.1"
            old.write_text("old", encoding="utf-8")
            import os
            old_time = time.time() - 10 * 86400
            os.utime(old, (old_time, old_time))

            plan = retention_plan(root, max_age_days=1, now=time.time())
            old.write_text("replacement", encoding="utf-8")
            with mock.patch("focuscheck.utils.data_retention.retention_plan", return_value=plan):
                result = apply_retention(root, max_age_days=1, now=time.time(), apply=True)

            self.assertFalse(result[0]["deleted"])
            self.assertEqual("changed_since_plan", result[0]["error"])
            self.assertTrue(old.exists())
            self.assertEqual(plan[0]["size"], 3)

    def test_apply_retention_reports_audit_write_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            old = root / "focus_log.csv.1"
            old.write_text("old", encoding="utf-8")
            import os
            old_time = time.time() - 10 * 86400
            os.utime(old, (old_time, old_time))
            with mock.patch("pathlib.Path.open", side_effect=OSError("disk full")):
                result = apply_retention(root, max_age_days=1, apply=True)
            self.assertTrue(result[0]["deleted"])
            self.assertFalse(result[0]["audit_written"])
            self.assertEqual("OSError", result[0]["audit_error"])

    def test_apply_retention_rejects_symlinked_audit_destination(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            root = Path(temp_dir)
            old = root / "focus_log.csv.1"
            old.write_text("old", encoding="utf-8")
            outside = root / "outside-audit.jsonl"
            outside.write_text("outside", encoding="utf-8")
            import os
            old_time = time.time() - 10 * 86400
            os.utime(old, (old_time, old_time))
            try:
                (root / "retention_audit.jsonl").symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            result = apply_retention(root, max_age_days=1, apply=True)
            self.assertTrue(result[0]["deleted"])
            self.assertFalse(result[0]["audit_written"])
            self.assertEqual("OSError", result[0]["audit_error"])
            self.assertEqual("outside", outside.read_text(encoding="utf-8"))

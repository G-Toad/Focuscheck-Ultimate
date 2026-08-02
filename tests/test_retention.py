from __future__ import annotations

import tempfile
import time
import unittest
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

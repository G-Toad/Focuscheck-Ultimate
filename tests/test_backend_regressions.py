"""Regression tests for backend/runtime hardening fixes."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock


class SettingsSaveTests(unittest.TestCase):
    def test_save_settings_uses_atomic_replace(self):
        import focuscheck.settings.manager as manager

        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = str(Path(temp_dir) / "focus_settings.json")
            with mock.patch.object(manager, "choose_path", return_value=settings_path), mock.patch.object(manager.os, "replace", wraps=manager.os.replace) as replace_mock:
                manager.save_settings({"interval_seconds": 120})

            replace_mock.assert_called_once()
            self.assertTrue(Path(settings_path).exists())


class TaskDbTests(unittest.TestCase):
    def test_overdue_naive_datetime_is_treated_as_utc(self):
        from focuscheck.database.task_db import TaskDB

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            db = TaskDB(str(Path(temp_dir) / "tasks.sqlite3"))
            due = (datetime.now(timezone.utc) - timedelta(minutes=5)).replace(tzinfo=None).isoformat()
            task_id = db.start_task(title="Write tests", due_utc=due, why="", consequences="")

            affected = db.overdue_active_to_failed()

            self.assertEqual([task_id], affected)
            self.assertIsNone(db.get_active())


class ImportHardeningTests(unittest.TestCase):
    def test_camera_modules_import_without_opencv(self):
        import focuscheck.ui.camera.adjustment_helpers as helpers
        import focuscheck.ui.camera_adjustment_window as window

        self.assertTrue(hasattr(helpers, "apply_manual_adjustments"))
        self.assertTrue(hasattr(window, "CameraAdjustmentWindow"))


if __name__ == "__main__":
    unittest.main()

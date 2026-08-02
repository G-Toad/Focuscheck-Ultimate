from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path


class TaskDbRecoveryTests(unittest.TestCase):
    def test_schema_version_journal_and_backup_restore(self):
        from focuscheck.database.task_db import TaskDB

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            root = Path(temp_dir)
            path = root / "tasks.sqlite3"
            backup = root / "backup.sqlite3"
            restored = root / "restored.sqlite3"
            db = TaskDB(str(path))
            task_id = db.start_task(title="Persist", due_utc=None, why="", consequences="")
            db.backup_to(backup)
            with sqlite3.connect(path) as con:
                self.assertEqual(2, con.execute("PRAGMA user_version").fetchone()[0])
                self.assertEqual(2, con.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0])
            TaskDB.restore_from(backup, restored)
            restored_db = TaskDB(str(restored))
            self.assertEqual(task_id, restored_db.get_active()["id"])

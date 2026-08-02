from __future__ import annotations

import sqlite3
import tempfile
import unittest
import threading
from pathlib import Path


class TaskDbRecoveryTests(unittest.TestCase):
    def test_concurrent_writers_preserve_one_active_task(self):
        from focuscheck.database.task_db import TaskDB

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            path = str(Path(temp_dir) / "tasks.sqlite3")
            errors = []

            def writer(index):
                try:
                    TaskDB(path).start_task(title=f"Task {index}", due_utc=None, why="", consequences="")
                except Exception as exc:
                    errors.append(exc)

            threads = [threading.Thread(target=writer, args=(index,)) for index in range(4)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            self.assertFalse(errors)
            rows = TaskDB(path).list_history(limit=20)
            self.assertEqual(1, sum(row["status"] == "active" for row in rows))

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

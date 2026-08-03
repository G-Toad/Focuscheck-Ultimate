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
                self.assertEqual(3, con.execute("PRAGMA user_version").fetchone()[0])
                self.assertEqual(3, con.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0])
            TaskDB.restore_from(backup, restored)
            restored_db = TaskDB(str(restored))
            self.assertEqual(task_id, restored_db.get_active()["id"])

    def test_legacy_fixture_normalizes_timestamps_and_flags_invalid_due_date(self):
        from focuscheck.database.task_db import TaskDB

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            path = Path(temp_dir) / "legacy.sqlite3"
            fixture = Path(__file__).parent / "fixtures" / "legacy_tasks_v1.sql"
            with sqlite3.connect(path) as con:
                con.executescript(fixture.read_text(encoding="utf-8"))
                con.commit()

            db = TaskDB(str(path))
            self.assertTrue(db.integrity_check())
            history = {row["id"]: row for row in db.list_history(limit=10)}
            self.assertEqual("2026-08-03T00:00:00+00:00", history[1]["created_utc"])
            self.assertIsNone(history[1]["due_utc"])
            self.assertIn("legacy invalid due_utc cleared", history[1]["change_reason"])
            self.assertEqual("active", history[2]["status"])
            self.assertIn("reconciled duplicate active task", history[1]["change_reason"])
            self.assertIsNotNone(db.pre_migration_backup)
            self.assertTrue(Path(db.pre_migration_backup).exists())
            with sqlite3.connect(db.pre_migration_backup) as backup:
                self.assertEqual(1, backup.execute("PRAGMA user_version").fetchone()[0])

    def test_corrupt_existing_database_is_rejected_without_replacement(self):
        from focuscheck.database.task_db import TaskDB

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            path = Path(temp_dir) / "corrupt.sqlite3"
            original = b"not a sqlite database"
            path.write_bytes(original)
            with self.assertRaises(RuntimeError):
                TaskDB(str(path))
            self.assertEqual(original, path.read_bytes())
            self.assertEqual([], list(path.parent.glob("corrupt.sqlite3.pre-migration-*.bak")))

    def test_restore_rejects_corrupt_backup_without_replacing_destination(self):
        from focuscheck.database.task_db import TaskDB

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            root = Path(temp_dir)
            source = root / "backup.sqlite3"
            destination = root / "restored.sqlite3"
            source.write_bytes(b"not sqlite")
            destination.write_bytes(b"keep existing")

            with self.assertRaises(RuntimeError):
                TaskDB.restore_from(source, destination)

            self.assertEqual(b"keep existing", destination.read_bytes())

    def test_restore_rejects_symlink_source(self):
        from focuscheck.database.task_db import TaskDB

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            root = Path(temp_dir)
            source = root / "backup.sqlite3"
            target = root / "target.sqlite3"
            target.write_bytes(b"not sqlite")
            try:
                source.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")

            with self.assertRaises(ValueError):
                TaskDB.restore_from(source, root / "restored.sqlite3")

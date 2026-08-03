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
                self.assertEqual(4, con.execute("PRAGMA user_version").fetchone()[0])
                self.assertEqual(4, con.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0])
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

    def test_legacy_unknown_status_is_reconciled_before_validation_triggers(self):
        from focuscheck.database.task_db import TaskDB

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            path = Path(temp_dir) / "legacy.sqlite3"
            with sqlite3.connect(path) as con:
                con.executescript(
                    """
                    PRAGMA user_version = 3;
                    CREATE TABLE tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_utc TEXT NOT NULL,
                        title TEXT NOT NULL,
                        why TEXT,
                        consequences TEXT,
                        due_utc TEXT,
                        status TEXT NOT NULL,
                        completed_utc TEXT,
                        change_reason TEXT,
                        timed_out INTEGER NOT NULL DEFAULT 0
                    );
                    INSERT INTO tasks(created_utc, title, status)
                    VALUES ('2026-08-03T00:00:00+00:00', 'legacy', 'mystery');
                    """
                )
                con.commit()

            db = TaskDB(str(path))
            row = db.list_history(limit=1)[0]
            self.assertEqual("changed", row["status"])
            self.assertIn("reconciled invalid legacy task status", row["change_reason"])
            with sqlite3.connect(path) as con:
                self.assertEqual(4, con.execute("PRAGMA user_version").fetchone()[0])

    def test_task_schema_rejects_invalid_future_rows(self):
        from focuscheck.database.task_db import TaskDB, MAX_TASK_TEXT_LENGTH

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            path = Path(temp_dir) / "tasks.sqlite3"
            TaskDB(str(path))
            with sqlite3.connect(path) as con:
                with self.assertRaises(sqlite3.IntegrityError):
                    con.execute(
                        "INSERT INTO tasks(created_utc, title, status) VALUES (?, ?, ?)",
                        ("2026-08-03T00:00:00+00:00", "bad", "mystery"),
                    )
                with self.assertRaises(sqlite3.IntegrityError):
                    con.execute(
                        "INSERT INTO tasks(created_utc, title, status) VALUES (?, ?, ?)",
                        ("2026-08-03T00:00:00+00:00", "x" * (MAX_TASK_TEXT_LENGTH + 1), "active"),
                    )

            db = TaskDB(str(path))
            with self.assertRaises(ValueError):
                db.start_task(title="x" * (MAX_TASK_TEXT_LENGTH + 1), due_utc=None, why="", consequences="")

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

    def test_restore_rejects_future_schema_without_replacing_destination(self):
        from focuscheck.database.task_db import TaskDB

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            root = Path(temp_dir)
            source = root / "future.sqlite3"
            destination = root / "restored.sqlite3"
            with sqlite3.connect(source) as con:
                con.execute("PRAGMA user_version = 99")
                con.commit()
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

    def test_restore_rejects_symlinked_source_parent(self):
        from focuscheck.database.task_db import TaskDB

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            root = Path(temp_dir)
            real_source = root / "real-source"
            real_source.mkdir()
            (real_source / "backup.sqlite3").write_bytes(b"not sqlite")
            linked_source = root / "linked-source"
            try:
                linked_source.symlink_to(real_source, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("directory symlinks unavailable")

            with self.assertRaises(ValueError):
                TaskDB.restore_from(linked_source / "backup.sqlite3", root / "restored.sqlite3")

    def test_restore_rejects_symlinked_destination_without_touching_target(self):
        from focuscheck.database.task_db import TaskDB

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            root = Path(temp_dir)
            source = root / "backup.sqlite3"
            source.write_bytes(b"not sqlite")
            external = root / "external.sqlite3"
            external.write_bytes(b"keep")
            destination = root / "restored.sqlite3"
            try:
                destination.symlink_to(external)
            except (OSError, NotImplementedError):
                self.skipTest("file symlinks unavailable")

            with self.assertRaises(ValueError):
                TaskDB.restore_from(source, destination)
            self.assertEqual(b"keep", external.read_bytes())

    def test_restore_rejects_symlinked_destination_parent(self):
        from focuscheck.database.task_db import TaskDB

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            root = Path(temp_dir)
            source = root / "backup.sqlite3"
            source.write_bytes(b"not sqlite")
            external = root / "external"
            external.mkdir()
            linked_destination = root / "linked-destination"
            try:
                linked_destination.symlink_to(external, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("directory symlinks unavailable")

            with self.assertRaises(ValueError):
                TaskDB.restore_from(source, linked_destination / "restored.sqlite3")
            self.assertEqual([], list(external.iterdir()))

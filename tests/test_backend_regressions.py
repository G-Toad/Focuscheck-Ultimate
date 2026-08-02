"""Regression tests for backend/runtime hardening fixes."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock


class SettingsSaveTests(unittest.TestCase):
    def test_valid_legacy_settings_are_imported_atomically(self):
        import json
        import focuscheck.settings.manager as manager

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            legacy = root / "legacy" / "focus_settings.json"
            canonical = root / "data" / "focus_settings.json"
            legacy.parent.mkdir()
            legacy.write_text(json.dumps({"settings_schema_version": 1, "interval_seconds": 42}), encoding="utf-8")
            with mock.patch.dict(manager.os.environ, {"FOCUS_DATA_DIR": ""}, clear=False), \
                    mock.patch.object(manager, "legacy_path", return_value=str(legacy)):
                manager._migrate_legacy_settings(str(canonical))

            self.assertEqual(42, json.loads(canonical.read_text(encoding="utf-8"))["interval_seconds"])
            self.assertTrue(legacy.exists())
            event = json.loads((root / "data" / "focus_settings.json.migration.jsonl").read_text(encoding="utf-8").splitlines()[-1])
            self.assertEqual("imported", event["outcome"])
            self.assertNotIn("interval_seconds", event["detail"])

    def test_canonical_settings_win_and_legacy_conflict_is_preserved_by_hash(self):
        import json
        import focuscheck.settings.manager as manager

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            legacy = root / "legacy" / "focus_settings.json"
            canonical = root / "data" / "focus_settings.json"
            legacy.parent.mkdir()
            canonical.parent.mkdir()
            legacy.write_text(json.dumps({"interval_seconds": 42}), encoding="utf-8")
            canonical.write_text(json.dumps({"interval_seconds": 99}), encoding="utf-8")
            with mock.patch.dict(manager.os.environ, {"FOCUS_DATA_DIR": ""}, clear=False), \
                    mock.patch.object(manager, "legacy_path", return_value=str(legacy)):
                manager._migrate_legacy_settings(str(canonical))

            self.assertEqual(99, json.loads(canonical.read_text(encoding="utf-8"))["interval_seconds"])
            conflicts = list(canonical.parent.glob("focus_settings.json.legacy-conflict-*.json"))
            self.assertEqual(1, len(conflicts))
            self.assertEqual(42, json.loads(conflicts[0].read_text(encoding="utf-8"))["interval_seconds"])
    def test_settings_input_budget_rejects_large_collections_and_strings(self):
        from focuscheck.settings.manager import validate_settings

        with self.assertRaises(ValueError):
            validate_settings({"future_values": ["x"] * 501})
        with self.assertRaises(ValueError):
            validate_settings({"future_value": "x" * 8193})

    def test_settings_file_lock_serializes_same_process_access(self):
        from focuscheck.settings.file_lock import settings_file_lock

        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = str(Path(temp_dir) / "focus_settings.json")
            with settings_file_lock(settings_path):
                with self.assertRaises(TimeoutError):
                    with settings_file_lock(settings_path, timeout=0.1):
                        pass

    def test_save_settings_uses_atomic_replace(self):
        import focuscheck.settings.manager as manager

        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = str(Path(temp_dir) / "focus_settings.json")
            with mock.patch.object(manager, "choose_path", return_value=settings_path), mock.patch.object(manager.os, "replace", wraps=manager.os.replace) as replace_mock:
                result = manager.save_settings({"interval_seconds": 120})

            replace_mock.assert_called_once()
            self.assertTrue(Path(settings_path).exists())
            self.assertTrue(result)
            self.assertTrue(result.durable_write)
            self.assertEqual(1, result.revision)
            self.assertTrue(result.validation_passed)
            self.assertFalse(result.backup_created)

    def test_save_settings_result_reports_backup_and_failure_details(self):
        import focuscheck.settings.manager as manager

        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = str(Path(temp_dir) / "focus_settings.json")
            with mock.patch.object(manager, "choose_path", return_value=settings_path):
                first = manager.save_settings({"interval_seconds": 120})
                second = manager.save_settings({"interval_seconds": 121})
            self.assertTrue(first)
            self.assertTrue(second)
            self.assertTrue(second.backup_created)
            self.assertEqual(2, second.revision)

            with mock.patch.object(manager, "choose_path", return_value=settings_path), mock.patch.object(manager.os, "replace", side_effect=OSError("disk full")):
                failed = manager.save_settings({"interval_seconds": 30})
            self.assertFalse(failed)
            self.assertFalse(failed.durable_write)
            self.assertTrue(failed.validation_passed)
            self.assertIn("disk full", failed.error)

    def test_save_settings_returns_false_and_keeps_existing_file_on_write_failure(self):
        import focuscheck.settings.manager as manager

        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = str(Path(temp_dir) / "focus_settings.json")
            Path(settings_path).write_text('{"interval_seconds": 120}', encoding="utf-8")
            with mock.patch.object(manager, "choose_path", return_value=settings_path), mock.patch.object(manager.os, "replace", side_effect=OSError("disk full")):
                self.assertFalse(manager.save_settings({"interval_seconds": 30}))
            self.assertEqual('{"interval_seconds": 120}', Path(settings_path).read_text(encoding="utf-8"))

    def test_malformed_settings_are_quarantined_and_backup_is_recovered(self):
        import focuscheck.settings.manager as manager

        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "focus_settings.json"
            settings_path.write_text("{not-json", encoding="utf-8")
            Path(f"{settings_path}.bak").write_text('{"interval_seconds": 90}', encoding="utf-8")
            with mock.patch.object(manager, "choose_path", return_value=str(settings_path)):
                loaded = manager.load_settings()
            self.assertEqual(90, loaded["interval_seconds"])
            self.assertFalse(settings_path.exists())
            self.assertTrue(list(Path(temp_dir).glob("focus_settings.json.corrupt-*")))

    def test_settings_backups_rotate_and_migration_is_journaled(self):
        import json
        import focuscheck.settings.manager as manager

        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "focus_settings.json"
            with mock.patch.object(manager, "choose_path", return_value=str(settings_path)):
                self.assertTrue(manager.save_settings({"interval_seconds": 30}))
                first = manager.load_settings()
                self.assertTrue(manager.save_settings({**first, "interval_seconds": 40}))
                second = manager.load_settings()
                self.assertTrue(manager.save_settings({**second, "interval_seconds": 50}))
                third = manager.load_settings()
                self.assertTrue(manager.save_settings({**third, "interval_seconds": 60}))

            self.assertTrue(Path(f"{settings_path}.bak").exists())
            self.assertTrue(Path(f"{settings_path}.bak.1").exists())
            self.assertTrue(Path(f"{settings_path}.bak.2").exists())

            # A legacy load records migration metadata but never stores values.
            settings_path.write_text(json.dumps({"settings_schema_version": 1, "snooze_until": "2030-01-01T00:00:00+00:00"}), encoding="utf-8")
            with mock.patch.object(manager, "choose_path", return_value=str(settings_path)):
                loaded = manager.load_settings()
            self.assertEqual("2030-01-01T00:00:00+00:00", loaded["snooze_until_utc"])
            journal = Path(f"{settings_path}.migration.jsonl")
            self.assertTrue(journal.exists())
            events = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]
            self.assertEqual("loaded", events[-1]["outcome"])
            self.assertNotIn("snooze_until", events[-1])

    def test_recovery_tries_rotated_backup_when_primary_backup_is_invalid(self):
        import focuscheck.settings.manager as manager

        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "focus_settings.json"
            settings_path.write_text("{broken", encoding="utf-8")
            Path(f"{settings_path}.bak").write_text("{also-broken", encoding="utf-8")
            Path(f"{settings_path}.bak.1").write_text('{"interval_seconds": 77}', encoding="utf-8")
            with mock.patch.object(manager, "choose_path", return_value=str(settings_path)):
                loaded = manager.load_settings()
            self.assertEqual(77, loaded["interval_seconds"])


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

    def test_camera_photo_capture_is_opt_in_and_path_is_not_cwd(self):
        from focuscheck.ui.dialogs.prompt_dialog_mixins.camera_feed import CameraFeedMixin

        mixin = CameraFeedMixin.__new__(CameraFeedMixin)
        mixin.settings = {"camera_capture_on_click": False}
        mixin._camera_capture = None
        self.assertIsNone(mixin._capture_photo_for_logs("Studying"))
        self.assertNotEqual(Path.cwd() / "camera_photos", mixin._get_camera_photos_directory())

    def test_native_overlay_destroy_releases_handles_once(self):
        from focuscheck.platform_specific import windows

        calls = {"brush": 0, "window": 0}
        class FakeGdi:
            def DeleteObject(self, handle):
                calls["brush"] += 1
        class FakeUser:
            def DestroyWindow(self, handle):
                calls["window"] += 1
        overlay = windows.WinClickThroughOverlay.__new__(windows.WinClickThroughOverlay)
        overlay._brush = 11
        overlay.hwnd = 22
        with mock.patch.object(windows, "_gdi32", return_value=FakeGdi()), mock.patch.object(windows, "_user32", return_value=FakeUser()):
            overlay.destroy()
            overlay.destroy()
        self.assertEqual({"brush": 1, "window": 1}, calls)


if __name__ == "__main__":
    unittest.main()

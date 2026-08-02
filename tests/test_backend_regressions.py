"""Regression tests for backend/runtime hardening fixes."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock


class SettingsSaveTests(unittest.TestCase):
    def test_settings_migration_fixture_matrix_covers_plan_inputs(self):
        from focuscheck.settings.manager import validate_settings
        from focuscheck.settings.migrations import CURRENT_SETTINGS_SCHEMA_VERSION, migrate_settings

        fixture_root = Path(__file__).parent / "fixtures"
        manifest = json.loads((fixture_root / "settings_migration_fixture_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(1, manifest["schema_version"])
        cases = {item["name"]: item for item in manifest["fixtures"]}

        self.assertEqual(
            {
                "missing_file", "empty_file", "malformed_json", "non_dict_json",
                "old_keys", "unknown_keys", "string_booleans", "impossible_dates",
                "malformed_website_flags", "huge_lists", "partial_write", "future_schema",
            },
            set(cases),
        )

        for name in ("empty_file", "malformed_json", "non_dict_json"):
            raw = (fixture_root / cases[name]["file"]).read_text(encoding="utf-8")
            with self.subTest(name=name):
                with self.assertRaises((ValueError, TypeError, json.JSONDecodeError)):
                    parsed = json.loads(raw)
                    validate_settings(parsed)

        old = json.loads((fixture_root / cases["old_keys"]["file"]).read_text(encoding="utf-8"))
        migrated = migrate_settings(old)
        self.assertEqual(CURRENT_SETTINGS_SCHEMA_VERSION, migrated["settings_schema_version"])
        self.assertEqual(migrated["snooze_until"], migrated["snooze_until_utc"])
        self.assertIsInstance(validate_settings(migrated)["website_flags"], list)

        unknown = json.loads((fixture_root / cases["unknown_keys"]["file"]).read_text(encoding="utf-8"))
        self.assertEqual("preserve-me", validate_settings(unknown)["future_plugin_setting"])

        booleans = json.loads((fixture_root / cases["string_booleans"]["file"]).read_text(encoding="utf-8"))
        normalized = validate_settings(booleans)
        self.assertFalse(normalized["paused"])
        self.assertTrue(normalized["force_always_on"])

        dates = json.loads((fixture_root / cases["impossible_dates"]["file"]).read_text(encoding="utf-8"))
        self.assertEqual("2005-01-01", validate_settings(dates)["biodata_birthdate"])

        website_flags = json.loads((fixture_root / cases["malformed_website_flags"]["file"]).read_text(encoding="utf-8"))
        self.assertEqual([], validate_settings(website_flags)["website_flags"])

        huge = json.loads((fixture_root / cases["huge_lists"]["file"]).read_text(encoding="utf-8"))
        with self.assertRaises(ValueError):
            validate_settings(huge)

        future = json.loads((fixture_root / cases["future_schema"]["file"]).read_text(encoding="utf-8"))
        with self.assertRaises(ValueError):
            migrate_settings(future)

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

    def test_legacy_task_and_log_data_migrates_without_destroying_conflicts(self):
        from focuscheck.utils.paths import get_app_paths, migrate_legacy_data

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            canonical = get_app_paths(root / "canonical")
            legacy = root / "legacy"
            legacy.mkdir()
            (legacy / "focus_tasks.sqlite3").write_bytes(b"legacy-db")
            (legacy / "focus_log.csv").write_text("legacy-log", encoding="utf-8")
            canonical.focus_log.write_text("canonical-log", encoding="utf-8")

            events = migrate_legacy_data(canonical, legacy_root=legacy)

            self.assertEqual(b"legacy-db", canonical.task_db.read_bytes())
            self.assertEqual("canonical-log", canonical.focus_log.read_text(encoding="utf-8"))
            self.assertTrue(list(canonical.root.glob("focus_log.csv.legacy-conflict-*")))
            self.assertEqual({"imported", "conflict_preserved"}, {event["outcome"] for event in events})
            self.assertTrue((canonical.root / "data_migration.jsonl").exists())

    def test_legacy_data_manifest_covers_every_durable_task_and_log_artifact(self):
        from focuscheck.utils.paths import get_app_paths, migrate_legacy_data

        fixture_root = Path(__file__).parent / "fixtures"
        manifest = json.loads((fixture_root / "migration_fixture_manifest.json").read_text(encoding="utf-8"))
        durable_artifacts = {
            item["target"]: (fixture_root / item["fixture"]).read_bytes()
            for item in manifest["artifacts"]
        }
        self.assertEqual(
            {"focus_tasks.sqlite3", "focus_log.csv", "focus_waste_log.csv", "focus_study_log.csv", "focus_intervention_reflections.jsonl"},
            set(durable_artifacts),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            canonical = get_app_paths(root / "canonical")
            legacy = root / "legacy"
            legacy.mkdir()
            for name, payload in durable_artifacts.items():
                (legacy / name).write_bytes(payload)

            # A byte-identical target is retained as a duplicate, while a
            # different target keeps the legacy bytes in a hash-addressed copy.
            canonical.task_db.write_bytes(durable_artifacts["focus_tasks.sqlite3"])
            canonical.focus_log.write_bytes(b"canonical-focus-log")

            events = migrate_legacy_data(canonical, legacy_root=legacy)
            outcomes = {event["file"]: event["outcome"] for event in events}

            self.assertEqual("duplicate_preserved", outcomes["focus_tasks.sqlite3"])
            self.assertEqual("conflict_preserved", outcomes["focus_log.csv"])
            self.assertEqual(
                {"imported", "duplicate_preserved", "conflict_preserved"},
                set(outcomes.values()),
            )
            for name in (
                "focus_waste_log.csv",
                "focus_study_log.csv",
                "focus_intervention_reflections.jsonl",
            ):
                self.assertEqual(durable_artifacts[name], (canonical.root / name).read_bytes())

            journal = canonical.root / "data_migration.jsonl"
            journal_events = [
                json.loads(line)
                for line in journal.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(set(durable_artifacts), {event["file"] for event in journal_events})
            self.assertTrue(list(canonical.root.glob("focus_log.csv.legacy-conflict-*")))

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
    def test_gentle_reminder_timer_ownership_releases_fired_and_cancelled_ids(self):
        from focuscheck.ui.dialogs.gentle_reminder_dialog import GentleReminderDialog

        dialog = GentleReminderDialog.__new__(GentleReminderDialog)
        dialog._closed = False
        dialog._active_timers = set()
        dialog._drift_timer = None
        scheduled = []
        cancelled = []
        callbacks = []
        dialog.after = lambda delay, callback: (scheduled.append((delay, callback)) or f"timer-{len(scheduled)}")
        dialog.after_cancel = cancelled.append

        first = dialog._schedule_timer(100, lambda: callbacks.append("fired"))
        dialog._drift_timer = first
        self.assertIn(first, dialog._active_timers)

        scheduled[0][1]()
        self.assertEqual(["fired"], callbacks)
        self.assertNotIn(first, dialog._active_timers)
        self.assertIsNone(dialog._drift_timer)

        second = dialog._schedule_timer(200, lambda: callbacks.append("cancelled"))
        dialog._drift_timer = second
        dialog._cleanup_timers()
        self.assertEqual([second], cancelled)
        self.assertEqual(set(), dialog._active_timers)
        self.assertIsNone(dialog._drift_timer)

        dialog._closed = True
        self.assertIsNone(dialog._schedule_timer(300, lambda: callbacks.append("closed")))

    def test_gentle_reminder_registry_invalidates_dequeued_callbacks(self):
        from focuscheck.ui.dialogs.gentle_reminder_dialog import GentleReminderDialog
        from focuscheck.utils.timers import TimerRegistry

        dialog = GentleReminderDialog.__new__(GentleReminderDialog)
        dialog._closed = False
        dialog._active_timers = set()
        dialog._drift_timer = None
        dialog._timer_names = {}
        dialog._timer_sequence = 0
        scheduled = []
        events = []
        dialog.after = lambda delay, callback: (scheduled.append(callback) or f"timer-{len(scheduled)}")
        dialog.after_cancel = lambda _timer_id: None
        dialog._timers = TimerRegistry(dialog)

        dialog._schedule_timer(100, lambda: events.append("stale"))
        dialog._cleanup_timers()
        scheduled[0]()

        self.assertEqual([], events)
        self.assertEqual(set(), dialog._active_timers)
        self.assertTrue(dialog._timers.closed)

    def test_camera_capability_reports_bounded_states(self):
        from focuscheck.ui.camera.capability import build_camera_capability

        self.assertEqual(
            "disabled",
            build_camera_capability(
                enabled=False,
                opencv_available=False,
                pillow_available=False,
            )["state"],
        )
        self.assertEqual(
            "dependency_missing",
            build_camera_capability(
                enabled=True,
                opencv_available=False,
                pillow_available=True,
            )["state"],
        )
        self.assertEqual(
            "device_unavailable",
            build_camera_capability(
                enabled=True,
                opencv_available=True,
                pillow_available=True,
                device_open=False,
            )["state"],
        )
        active = build_camera_capability(
            enabled=True,
            opencv_available=True,
            pillow_available=True,
            device_open=True,
            stream_active=True,
        )
        self.assertEqual("active", active["state"])
        self.assertEqual("granted", active["access"])

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

    def test_camera_feed_generation_invalidates_dequeued_callbacks(self):
        from focuscheck.ui.dialogs.prompt_dialog_mixins.camera_feed import CameraFeedMixin

        class Capture:
            def __init__(self):
                self.reads = 0
                self.releases = 0

            def read(self):
                self.reads += 1
                return True, object()

            def release(self):
                self.releases += 1

        mixin = CameraFeedMixin.__new__(CameraFeedMixin)
        mixin.settings = {"camera_fps": 30}
        capture = Capture()
        mixin._camera_capture = capture
        mixin._camera_update_timer = None
        mixin._camera_generation = 7
        mixin._closed = False
        scheduled = []
        mixin.after = lambda delay, callback, *args: scheduled.append((delay, callback, args)) or "camera-timer"
        mixin.after_cancel = mock.Mock()
        mixin._display_camera_frame = mock.Mock()

        mixin._start_camera_feed_updates(7)
        self.assertEqual(1, capture.reads)
        self.assertEqual((7,), scheduled[0][2])

        mixin._cleanup_camera_feed()
        scheduled[0][1](*scheduled[0][2])

        self.assertEqual(1, capture.reads)
        self.assertEqual(1, capture.releases)

    def test_biodata_pulse_callbacks_are_cancelled_with_camera_cleanup(self):
        from focuscheck.ui.dialogs.prompt_dialog_mixins.camera_feed import CameraFeedMixin

        mixin = CameraFeedMixin.__new__(CameraFeedMixin)
        mixin._closed = False
        mixin._camera_generation = 2
        mixin._camera_update_timer = None
        mixin._camera_capture = None
        mixin._camera_capability = {}
        mixin._biodata_pulse_timer_ids = set()
        mixin._active_timers = set()
        scheduled = []
        cancelled = []

        class Label:
            def configure(self, **_kwargs):
                return None

        mixin.after = lambda delay, callback: (scheduled.append((delay, callback)) or "pulse-timer")
        mixin.after_cancel = cancelled.append
        mixin._animate_biodata_pulse(object(), Label())

        self.assertEqual({"pulse-timer"}, mixin._biodata_pulse_timer_ids)
        mixin._cleanup_camera_feed()
        self.assertEqual(["pulse-timer"], cancelled)
        self.assertEqual(set(), mixin._biodata_pulse_timer_ids)

        # A callback already dequeued by Tk must not reschedule after cleanup.
        scheduled[0][1]()
        self.assertEqual(1, len(scheduled))

    def test_biodata_pulse_uses_prompt_timer_owner_when_available(self):
        from focuscheck.ui.dialogs.prompt_dialog import PromptDialog
        from focuscheck.ui.dialogs.prompt_dialog_mixins.camera_feed import CameraFeedMixin
        from focuscheck.utils.timers import TimerRegistry

        class Scheduler:
            def __init__(self):
                self.callbacks = {}
                self.next_id = 0

            def after(self, _delay, callback):
                self.next_id += 1
                self.callbacks[self.next_id] = callback
                return self.next_id

            def after_cancel(self, timer_id):
                self.callbacks.pop(timer_id, None)

        scheduler = Scheduler()
        mixin = CameraFeedMixin.__new__(CameraFeedMixin)
        mixin._closed = False
        mixin._camera_generation = 2
        mixin._camera_update_timer = None
        mixin._camera_capture = None
        mixin._camera_capability = {}
        mixin._biodata_pulse_timer_ids = set()
        mixin._timer_names = {}
        mixin._active_timers = set()
        mixin._timer_sequence = 0
        mixin._timers = TimerRegistry(scheduler)
        mixin._schedule_timer = PromptDialog._schedule_timer.__get__(mixin, CameraFeedMixin)
        mixin._cancel_timer = PromptDialog._cancel_timer.__get__(mixin, CameraFeedMixin)

        class Label:
            def configure(self, **_kwargs):
                return None

        mixin._animate_biodata_pulse(object(), Label())
        self.assertEqual({1}, mixin._biodata_pulse_timer_ids)
        self.assertIn(1, scheduler.callbacks)

        mixin._cleanup_camera_feed()
        self.assertEqual(set(), mixin._biodata_pulse_timer_ids)
        self.assertEqual({}, scheduler.callbacks)

    def test_camera_preview_windows_ignore_stale_callbacks_after_close(self):
        from focuscheck.ui.camera_adjustment_window import CameraAdjustmentWindow
        from focuscheck.ui.camera_test_window import CameraTestWindow
        from focuscheck.ui.crop_adjustment_window import CropAdjustmentWindow

        class Capture:
            def __init__(self):
                self.reads = 0
                self.releases = 0

            def read(self):
                self.reads += 1
                return True, object()

            def release(self):
                self.releases += 1

            def isOpened(self):
                return True

        for window_class, update_name, cleanup_name in (
            (CameraTestWindow, "_update_camera_feed", "_on_close"),
            (CameraAdjustmentWindow, "_update_feed", "_on_close"),
        ):
            window = window_class.__new__(window_class)
            capture = Capture()
            window._camera_capture = capture
            window._camera_generation = 4
            window._closed = False
            window._camera_update_timer = None
            window._update_timer = None
            window.after_cancel = mock.Mock()
            window.destroy = mock.Mock()

            getattr(window, update_name)(3)
            getattr(window, cleanup_name)()

            self.assertEqual(0, capture.reads)
            self.assertEqual(1, capture.releases)

        window = CropAdjustmentWindow.__new__(CropAdjustmentWindow)
        capture = Capture()
        window.camera = capture
        window._camera_generation = 4
        window._camera_init_timer = None
        window.camera_update_timer = None
        window.after_cancel = mock.Mock()

        window._update_camera_feed(3)
        window._cleanup()

        self.assertEqual(0, capture.reads)
        self.assertEqual(1, capture.releases)

    def test_camera_adjustment_close_cancels_save_feedback_timer(self):
        from focuscheck.ui.camera_adjustment_window import CameraAdjustmentWindow

        window = CameraAdjustmentWindow.__new__(CameraAdjustmentWindow)
        window._closed = False
        window._camera_generation = 2
        window._save_feedback_timer = "feedback-timer"
        window._save_feedback_label = object()
        window._update_timer = None
        window._camera_capture = None
        window.after_cancel = mock.Mock()
        window.destroy = mock.Mock()

        window._on_close()

        window.after_cancel.assert_called_once_with("feedback-timer")
        self.assertIsNone(window._save_feedback_timer)
        self.assertIsNone(window._save_feedback_label)
        window.destroy.assert_called_once_with()

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

    def test_native_overlay_declares_lifecycle_signatures(self):
        import ctypes
        from ctypes import wintypes
        from focuscheck.platform_specific import windows

        class Api:
            def __init__(self):
                self.argtypes = None
                self.restype = None

        names = (
            "RegisterClassExW", "CreateWindowExW", "DefWindowProcW", "BeginPaint",
            "GetClientRect", "EndPaint", "FillRect", "GetClassLongPtrW", "SetClassLongPtrW",
            "ShowWindow", "SetWindowPos", "RedrawWindow", "SetLayeredWindowAttributes",
            "DestroyWindow",
        )
        user32 = type("User32", (), {name: Api() for name in names})()
        gdi32 = type("Gdi32", (), {
            name: Api() for name in ("CreateSolidBrush", "FillRect", "DeleteObject")
        })()
        kernel32 = type("Kernel32", (), {"GetModuleHandleW": Api()})()

        windows._configure_overlay_api(user32, gdi32, kernel32)

        self.assertEqual([wintypes.HWND], user32.DestroyWindow.argtypes)
        self.assertEqual(
            [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
             ctypes.c_int, ctypes.c_int, wintypes.UINT],
            user32.SetWindowPos.argtypes,
        )
        self.assertEqual(
            [wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.HBRUSH],
            user32.FillRect.argtypes,
        )
        self.assertEqual([wintypes.LPCWSTR], kernel32.GetModuleHandleW.argtypes)

    def test_dialog_overlay_declares_lifecycle_signatures(self):
        import ctypes
        from ctypes import wintypes
        from focuscheck.ui.dialogs import windows_utils

        class Api:
            def __init__(self):
                self.argtypes = None
                self.restype = None

        user32 = type("User32", (), {
            name: Api() for name in (
                "RegisterClassExW", "CreateWindowExW", "DefWindowProcW",
                "SetLayeredWindowAttributes", "SetWindowPos", "ShowWindow", "DestroyWindow",
            )
        })()
        gdi32 = type("Gdi32", (), {name: Api() for name in ("CreateSolidBrush", "DeleteObject")})()
        kernel32 = type("Kernel32", (), {"GetModuleHandleW": Api()})()

        windows_utils._configure_overlay_api(user32, gdi32, kernel32)

        self.assertEqual([wintypes.HWND], user32.DestroyWindow.argtypes)
        self.assertEqual(
            [wintypes.HWND, wintypes.COLORREF, wintypes.BYTE, wintypes.DWORD],
            user32.SetLayeredWindowAttributes.argtypes,
        )
        self.assertEqual([wintypes.COLORREF], gdi32.CreateSolidBrush.argtypes)
        self.assertEqual([wintypes.LPCWSTR], kernel32.GetModuleHandleW.argtypes)

    def test_spotlight_region_declares_native_signatures(self):
        import ctypes
        from ctypes import wintypes
        from focuscheck.ui.dialogs import intervention_wizard

        class Api:
            def __init__(self):
                self.argtypes = None
                self.restype = None

        user32 = type("User32", (), {
            name: Api() for name in ("SetWindowRgn", "GetCursorPos", "GetSystemMetrics", "SetWindowPos")
        })()
        gdi32 = type("Gdi32", (), {
            name: Api() for name in ("CreateRectRgn", "CreateEllipticRgn", "CombineRgn", "DeleteObject")
        })()
        intervention_wizard._configure_spotlight_region_api(user32, gdi32)

        self.assertEqual(
            [ctypes.c_int] * 4,
            gdi32.CreateRectRgn.argtypes,
        )
        self.assertEqual(
            [wintypes.HWND, wintypes.HANDLE, wintypes.BOOL],
            user32.SetWindowRgn.argtypes,
        )
        intervention_wizard._configure_window_position_api(user32)
        self.assertEqual([ctypes.c_int], user32.GetSystemMetrics.argtypes)
        self.assertEqual(
            [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
             ctypes.c_int, ctypes.c_int, wintypes.UINT],
            user32.SetWindowPos.argtypes,
        )


if __name__ == "__main__":
    unittest.main()

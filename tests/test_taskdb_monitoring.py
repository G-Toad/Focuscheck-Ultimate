"""Persistence, due-time, monitoring, and startup tests."""

from __future__ import annotations

import tempfile
import unittest
import os
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock


class DueTimeTests(unittest.TestCase):
    def test_parse_due_time_minutes_and_invalid(self):
        from focuscheck.utils.due_time import parse_due_time

        now = datetime(2026, 7, 20, 10, 0, tzinfo=timezone.utc)
        self.assertEqual((now + timedelta(minutes=5)).isoformat(), parse_due_time("5", now=now))
        self.assertIsNone(parse_due_time(""))
        self.assertIsNone(parse_due_time("not a time"))
        self.assertIsNone(parse_due_time("25:99"))

    def test_parse_due_time_hhmm_rolls_to_tomorrow_if_past(self):
        from focuscheck.utils.due_time import parse_due_time

        now = datetime(2026, 7, 20, 10, 0, tzinfo=timezone.utc)
        parsed = datetime.fromisoformat(parse_due_time("09:30", now=now))

        self.assertEqual(21, parsed.day)
        self.assertEqual(9, parsed.hour)
        self.assertEqual(30, parsed.minute)

    def test_build_task_payload_trims_fields_and_uses_shared_due_parser(self):
        from focuscheck.utils.task_payload import build_task_payload

        now = datetime(2026, 7, 20, 10, 0, tzinfo=timezone.utc)
        payload = build_task_payload("  Write tests  ", " quality ", " regressions ", "5", now=now)

        self.assertEqual("Write tests", payload["title"])
        self.assertEqual("quality", payload["why"])
        self.assertEqual("regressions", payload["consequences"])
        self.assertEqual((now + timedelta(minutes=5)).isoformat(), payload["due_utc"])

    def test_build_task_payload_keeps_invalid_due_empty(self):
        from focuscheck.utils.task_payload import build_task_payload

        payload = build_task_payload("Task", due_text="not a due time")

        self.assertEqual("Task", payload["title"])
        self.assertIsNone(payload["due_utc"])


class TaskDbLifecycleTests(unittest.TestCase):
    def test_task_timestamps_are_persisted_as_utc(self):
        from focuscheck.database.task_db import TaskDB

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            db = TaskDB(str(Path(temp_dir) / "tasks.sqlite3"))
            task_id = db.start_task(
                title="UTC contract",
                due_utc="2030-01-01T12:00:00+08:00",
                why="",
                consequences="",
            )
            self.assertEqual("2030-01-01T04:00:00+00:00", db.get_active()["due_utc"])
            self.assertTrue(db.mark_completed(task_id, "2030-01-01T13:00:00+08:00"))
            self.assertEqual("2030-01-01T05:00:00+00:00", db.list_history(limit=1)[0]["completed_utc"])

    def test_invalid_task_timestamp_is_rejected_at_persistence_boundary(self):
        from focuscheck.database.task_db import TaskDB

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            db = TaskDB(str(Path(temp_dir) / "tasks.sqlite3"))
            with self.assertRaises(ValueError):
                db.start_task(title="bad", due_utc="not-a-date", why="", consequences="")

    def test_task_lifecycle_history_analytics_and_events(self):
        from focuscheck.database.task_db import TaskDB

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            db = TaskDB(str(Path(temp_dir) / "tasks.sqlite3"))
            task_id = db.start_task(title="Build tests", due_utc=None, why="quality", consequences="bugs")

            self.assertEqual(task_id, db.get_active()["id"])
            self.assertIsNotNone(db.record_focus_event(doing="coding", benefits="stability", active_task_id=task_id))
            self.assertIsNotNone(db.record_waste_event(what="scrolling", consequences="lost time", active_task_id=task_id))

            db.mark_completed(task_id)
            self.assertIsNone(db.get_active())
            history = db.list_history(limit=10, include_active=False)
            self.assertEqual("completed", history[0]["status"])

            stats = db.analytics_counts()
            self.assertEqual(1, stats["completed"])
            self.assertEqual(0, stats["failed"])

            self.assertFalse(db.mark_failed(task_id))

    def test_changed_counts_as_failed_when_configured(self):
        from focuscheck.database.task_db import TaskDB

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            db = TaskDB(str(Path(temp_dir) / "tasks.sqlite3"))
            task_id = db.start_task(title="Old task", due_utc=None, why="", consequences="")
            db.mark_changed(task_id, "scope changed")

            self.assertEqual(1, db.analytics_counts(treat_changed_as_fail=True)["failed"])
            self.assertEqual(0, db.analytics_counts(treat_changed_as_fail=False)["failed"])

    def test_start_task_replaces_existing_active_task(self):
        from focuscheck.database.task_db import TaskDB

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            db = TaskDB(str(Path(temp_dir) / "tasks.sqlite3"))
            first_id = db.start_task(title="First", due_utc=None, why="", consequences="")
            second_id = db.start_task(title="Second", due_utc=None, why="", consequences="")
            history = db.list_history(limit=10, include_active=True)

            active = [row for row in history if row["status"] == "active"]
            changed = [row for row in history if row["status"] == "changed"]

            self.assertEqual(second_id, db.get_active()["id"])
            self.assertEqual([second_id], [row["id"] for row in active])
            self.assertIn(first_id, [row["id"] for row in changed])


class EngineV2MatchingTests(unittest.TestCase):
    def test_domain_matching_exact_subdomain_and_disabled_flags(self):
        from focuscheck.monitoring.engine_v2 import EngineV2

        engine = EngineV2.__new__(EngineV2)

        self.assertTrue(engine._domain_matches("reddit.com", "www.reddit.com"))
        self.assertTrue(engine._domain_matches("reddit.com", "reddit.com"))
        self.assertFalse(engine._domain_matches("reddit.com", "notreddit.com"))

        flags = [
            {"domain": "blocked.com", "enabled": False},
            {"domain": "reddit.com", "enabled": True, "cooldown_minutes": 0, "severity": 2},
        ]
        match = engine._match_flag({"url": "https://www.reddit.com/r/test", "title": ""}, flags)

        self.assertIsNotNone(match)
        self.assertEqual("reddit.com", match[1])

    def test_match_flag_respects_cooldown(self):
        from focuscheck.monitoring.engine_v2 import EngineV2

        engine = EngineV2.__new__(EngineV2)
        flags = [{"domain": "reddit.com", "enabled": True, "cooldown_minutes": 10, "last_dismissed": datetime.now().timestamp()}]

        self.assertIsNone(engine._match_flag({"url": "https://reddit.com", "title": ""}, flags))

    def test_cancelled_intervention_does_not_start_cooldown(self):
        from focuscheck.monitoring.engine_v2 import EngineV2

        class Root:
            def after(self, _delay, callback):
                return callback()

            def after_cancel(self, _timer):
                return None

        class App:
            root = Root()
            _current_prompt = None
            _intervention_active = False
            settings = {"website_flags": [{"domain": "reddit.com", "severity": 3, "cooldown_minutes": 5}]}

        engine = EngineV2.__new__(EngineV2)
        engine.app = App()
        engine._last_hwnd = None
        engine._last_switch_mono = 0.0
        engine._settings = App.settings
        engine._subpopup_active = False
        engine._activity_provider = lambda: {"hwnd": 10, "title": "Reddit", "url": "https://reddit.com"}

        class CancelledWizard:
            def __init__(self, *_args):
                pass

            def run(self, **_kwargs):
                return False

        with mock.patch("focuscheck.monitoring.engine_v2.InterventionWizard", CancelledWizard), mock.patch("focuscheck.monitoring.engine_v2.save_settings") as save:
            engine._maybe_show_subpopup()
        save.assert_not_called()

    def test_match_flag_rejects_suffix_attack_when_host_parsed(self):
        from focuscheck.monitoring.engine_v2 import EngineV2

        engine = EngineV2.__new__(EngineV2)
        flags = [{"domain": "reddit.com", "enabled": True, "cooldown_minutes": 0}]

        self.assertIsNone(engine._match_flag({"url": "https://badreddit.com", "title": ""}, flags))

    def test_match_flag_does_not_use_title_when_host_is_authoritative(self):
        from focuscheck.monitoring.engine_v2 import EngineV2

        engine = EngineV2.__new__(EngineV2)
        flags = [{"domain": "reddit.com", "enabled": True, "cooldown_minutes": 0}]

        self.assertIsNone(engine._match_flag({"url": "https://example.com", "title": "Reddit"}, flags))

    def test_match_flag_normalizes_idn_and_ipv6_domains(self):
        from focuscheck.monitoring.engine_v2 import EngineV2

        engine = EngineV2.__new__(EngineV2)
        self.assertIsNotNone(engine._match_flag(
            {"url": "https://xn--bcher-kva.example/", "title": ""},
            [{"domain": "bücher.example", "enabled": True, "cooldown_minutes": 0}],
        ))
        self.assertIsNotNone(engine._match_flag(
            {"url": "http://[2001:db8::1]/", "title": ""},
            [{"domain": "2001:db8::1", "enabled": True, "cooldown_minutes": 0}],
        ))

    def test_active_window_flag_triggers_severity_three_intervention(self):
        from focuscheck.monitoring.engine_v2 import EngineV2

        app = mock.Mock()
        app.root = mock.Mock()
        app.settings = {
            "paused": False,
            "pause_when_inactive_or_lid_closed": False,
            "website_flags": [
                {"domain": "reddit.com", "enabled": True, "cooldown_minutes": 0, "severity": 3}
            ],
        }
        engine = EngineV2(app, activity_provider=lambda: {"url": "https://reddit.com/r/all", "title": "Reddit", "hwnd": 123})

        with mock.patch("focuscheck.monitoring.engine_v2.save_settings") as save_settings, mock.patch("focuscheck.monitoring.engine_v2.InterventionWizard") as wizard_cls:
            engine._maybe_show_subpopup()

        wizard_cls.assert_called_once_with(app.root, app.settings)
        wizard_cls.return_value.run.assert_called_once_with(preselect_hwnd=123, preselect_title="Reddit")
        save_settings.assert_called_once()

    def test_active_window_flag_triggers_severity_two_subpopup_with_fake_activity(self):
        from focuscheck.monitoring.engine_v2 import EngineV2

        app = mock.Mock()
        app.root = mock.Mock()
        app.settings = {
            "paused": False,
            "pause_when_inactive_or_lid_closed": False,
            "website_flags": [
                {"domain": "reddit.com", "enabled": True, "cooldown_minutes": 0, "severity": 2}
            ],
        }
        engine = EngineV2(app, activity_provider=lambda: {"url": "https://old.reddit.com/r/all", "title": "Reddit", "hwnd": 456})

        with mock.patch("focuscheck.monitoring.engine_v2.V2SubPopupDialog") as dialog_cls:
            engine._maybe_show_subpopup()

        dialog_cls.assert_called_once()
        kwargs = dialog_cls.call_args.kwargs
        self.assertEqual("reddit.com", kwargs["domain"])
        self.assertEqual(2, kwargs["severity"])
        dialog_cls.return_value.grab_set.assert_called_once()
        self.assertTrue(engine._subpopup_active)

    def test_activity_provider_tracks_active_window_duration_without_real_browser(self):
        from focuscheck.monitoring.engine_v2 import EngineV2

        provider = mock.Mock(side_effect=lambda: {"url": "https://example.com", "title": "Example", "hwnd": 99})
        engine = EngineV2(mock.Mock(), activity_provider=provider)

        first = engine._get_activity_info()
        second = engine._get_activity_info()

        self.assertEqual(0.0, first["active_duration_s"])
        self.assertGreaterEqual(second["active_duration_s"], 0.0)
        self.assertEqual(2, provider.call_count)

    def test_activity_provider_sequence_resets_duration_on_window_switch(self):
        from focuscheck.monitoring.engine_v2 import EngineV2

        provider = mock.Mock(
            side_effect=[
                {"url": "https://example.com", "title": "Example", "hwnd": 99},
                {"url": "https://example.com/page", "title": "Example", "hwnd": 99},
                {"url": "https://docs.python.org", "title": "Python", "hwnd": 100},
            ]
        )
        engine = EngineV2(mock.Mock(), activity_provider=provider)

        first = engine._get_activity_info()
        second = engine._get_activity_info()
        third = engine._get_activity_info()

        self.assertEqual(0.0, first["active_duration_s"])
        self.assertGreaterEqual(second["active_duration_s"], 0.0)
        self.assertEqual(0.0, third["active_duration_s"])
        self.assertEqual(3, provider.call_count)


class StartupCommandTests(unittest.TestCase):
    def test_compose_startup_command_targets_supervisor_entrypoint(self):
        from focuscheck.platform_specific import startup

        with mock.patch.object(startup.sys, "frozen", False, create=True), mock.patch.object(startup.sys, "executable", "C:\\Python\\python.exe"), mock.patch.object(startup.sys, "argv", ["C:\\Temp\\test_runner.py"]):
            command = startup.compose_startup_command()

        self.assertIn('"C:\\Python\\python.exe"', command)
        self.assertIn("focuscheck_supervisor.py", command)
        self.assertIn("--run", command)
        self.assertIn("--base-dir", command)
        self.assertNotIn("test_runner.py", command)

    def test_install_startup_writes_registry_command(self):
        from focuscheck.platform_specific import startup

        calls = {}
        fake_winreg = types.SimpleNamespace(
            HKEY_CURRENT_USER=object(),
            KEY_SET_VALUE=1,
            REG_SZ=1,
            OpenKey=lambda *args: "key",
            CreateKey=lambda *args: "key",
            SetValueEx=lambda key, name, _reserved, typ, value: calls.update({"name": name, "value": value, "typ": typ}),
            CloseKey=lambda key: calls.update({"closed": key}),
        )

        with mock.patch.dict(sys.modules, {"winreg": fake_winreg}), mock.patch.object(startup._platform, "system", return_value="Windows"):
            ok = startup.install_startup("FocusCheckTest")

        self.assertTrue(ok)
        self.assertEqual("FocusCheckTest", calls["name"])
        self.assertIn("focuscheck_supervisor.py", calls["value"])

    def test_uninstall_startup_removes_same_registry_name(self):
        from focuscheck.platform_specific import startup

        calls = {"values": {"FocusCheckTest": "command"}}

        def delete_value(_key, name):
            if name not in calls["values"]:
                raise FileNotFoundError(name)
            calls["deleted"] = name
            del calls["values"][name]

        fake_winreg = types.SimpleNamespace(
            HKEY_CURRENT_USER=object(),
            KEY_SET_VALUE=1,
            OpenKey=lambda *args: "key",
            DeleteValue=delete_value,
            CloseKey=lambda key: calls.update({"closed": key}),
        )

        with mock.patch.dict(sys.modules, {"winreg": fake_winreg}), mock.patch.object(startup._platform, "system", return_value="Windows"):
            ok = startup.uninstall_startup("FocusCheckTest")

        self.assertTrue(ok)
        self.assertEqual("FocusCheckTest", calls["deleted"])
        self.assertNotIn("FocusCheckTest", calls["values"])
        self.assertEqual("key", calls["closed"])

    def test_is_startup_installed_queries_registry_safely(self):
        from focuscheck.platform_specific import startup

        calls = {}

        def query_value(_key, name):
            calls["queried"] = name
            if name == "FocusCheckTest":
                return ("command", 1)
            raise FileNotFoundError(name)

        fake_winreg = types.SimpleNamespace(
            HKEY_CURRENT_USER=object(),
            KEY_READ=2,
            OpenKey=lambda *args: "key",
            QueryValueEx=query_value,
            CloseKey=lambda key: calls.update({"closed": key}),
        )

        with mock.patch.dict(sys.modules, {"winreg": fake_winreg}), mock.patch.object(startup._platform, "system", return_value="Windows"):
            installed = startup.is_startup_installed("FocusCheckTest")
            missing = startup.is_startup_installed("MissingFocusCheck")

        self.assertTrue(installed)
        self.assertFalse(missing)
        self.assertEqual("key", calls["closed"])

    def test_inspect_startup_classifies_stale_command(self):
        from focuscheck.platform_specific import startup

        fake_winreg = types.SimpleNamespace(
            HKEY_CURRENT_USER=object(),
            KEY_READ=2,
            OpenKey=lambda *args: "key",
            QueryValueEx=lambda *_args: ('"C:\\Old\\FocusCheck.exe"', 1),
            CloseKey=lambda _key: None,
        )
        with mock.patch.dict(sys.modules, {"winreg": fake_winreg}), \
                mock.patch.object(startup._platform, "system", return_value="Windows"), \
                mock.patch.object(startup, "compose_startup_command", return_value='"C:\\New\\FocusCheck.exe"'):
            inspection = startup.inspect_startup("FocusCheckTest")

        self.assertEqual("stale", inspection.status)
        self.assertTrue(inspection.present)
        self.assertTrue(inspection.repairable)

    def test_inspect_startup_normalizes_slashes_for_valid_command(self):
        from focuscheck.platform_specific import startup

        command = '"C:/FocusCheck/focuscheck_supervisor.py" --run'
        fake_winreg = types.SimpleNamespace(
            HKEY_CURRENT_USER=object(),
            KEY_READ=2,
            OpenKey=lambda *args: "key",
            QueryValueEx=lambda *_args: (command, 1),
            CloseKey=lambda _key: None,
        )
        with mock.patch.dict(sys.modules, {"winreg": fake_winreg}), \
                mock.patch.object(startup._platform, "system", return_value="Windows"), \
                mock.patch.object(startup, "compose_startup_command", return_value='"C:\\FocusCheck\\focuscheck_supervisor.py" --run'):
            inspection = startup.inspect_startup("FocusCheckTest")

        self.assertEqual("valid", inspection.status)
        self.assertFalse(inspection.repairable)


class SupervisorLifecycleTests(unittest.TestCase):
    def test_supervisor_lock_rejects_duplicate_and_cleans_up(self):
        from focuscheck_supervisor import SupervisorLock

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            path = Path(temp_dir) / "supervisor.lock"
            first = SupervisorLock(path)
            second = SupervisorLock(path)
            self.assertTrue(first.acquire())
            try:
                self.assertFalse(second.acquire())
            finally:
                first.release()
            self.assertFalse(path.exists())

    def test_supervisor_lock_recovers_stale_lock(self):
        from focuscheck_supervisor import SupervisorLock

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            path = Path(temp_dir) / "supervisor.lock"
            path.write_text("0", encoding="ascii")
            lock = SupervisorLock(path)
            self.assertTrue(lock.acquire())
            lock.release()

    def test_app_quit_writes_supervisor_stop_request(self):
        from focuscheck.app import App

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            stop_file = Path(temp_dir) / "stop.flag"
            app = App.__new__(App)
            with mock.patch.dict(os.environ, {"FOCUSCHECK_SUPERVISOR_STOP_FILE": str(stop_file)}):
                app._request_supervisor_stop()

            self.assertTrue(stop_file.exists())


if __name__ == "__main__":
    unittest.main()

"""Persistence, due-time, monitoring, and startup tests."""

from __future__ import annotations

import tempfile
import unittest
import sqlite3
import json
import os
import sys
import types
import copy
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

    def test_task_transitions_and_overdue_use_injected_utc_clock(self):
        from focuscheck.database.task_db import TaskDB

        now = datetime(2026, 7, 20, 10, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            db = TaskDB(str(Path(temp_dir) / "tasks.sqlite3"), clock=lambda: now)
            task_id = db.start_task(
                title="Clocked task",
                due_utc="2026-07-20T09:59:00+00:00",
                why="",
                consequences="",
            )
            self.assertEqual(now.isoformat(), db.get_active()["created_utc"])
            self.assertEqual([task_id], db.overdue_active_to_failed())
            self.assertEqual(now.isoformat(), db.list_history(limit=1)[0]["completed_utc"])
            self.assertEqual(1, db.list_history(limit=1)[0]["timed_out"])
            self.assertEqual("task deadline overdue", db.list_history(limit=1)[0]["change_reason"])

            second_id = db.start_task(title="Completed task", due_utc=None, why="", consequences="")
            self.assertTrue(db.mark_completed(second_id))
            self.assertEqual(now.isoformat(), db.list_history(limit=1)[0]["completed_utc"])

    def test_overdue_transition_is_inclusive_at_exact_deadline(self):
        from focuscheck.database.task_db import TaskDB

        now = datetime(2026, 7, 20, 10, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            db = TaskDB(str(Path(temp_dir) / "tasks.sqlite3"), clock=lambda: now)
            task_id = db.start_task(
                title="Exact deadline",
                due_utc=now.isoformat(),
                why="",
                consequences="",
            )

            self.assertEqual([task_id], db.overdue_active_to_failed())
            self.assertIsNone(db.get_active())
            self.assertEqual(1, db.list_history(limit=1)[0]["timed_out"])

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

    def test_prompt_task_done_marks_overdue_task_as_timed_out(self):
        from focuscheck.ui.dialogs.prompt_dialog_mixins.task_management import TaskManagementMixin

        taskdb = mock.Mock()
        prompt = TaskManagementMixin.__new__(TaskManagementMixin)
        prompt.taskdb = taskdb
        prompt._task_decision_required = True
        prompt._task_decision_task_id = 42
        prompt._focus_prompt_open = True
        prompt._render_task_panel = mock.Mock()
        prompt._refresh_analytics = mock.Mock()

        overdue = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        prompt._task_mark_done(42, overdue)

        taskdb.mark_failed.assert_called_once_with(42, timed_out=True)
        taskdb.mark_completed.assert_not_called()
        self.assertFalse(prompt._task_decision_required)
        self.assertFalse(prompt._focus_prompt_open)

    def test_prompt_task_deadline_uses_injected_clock(self):
        from focuscheck.ui.dialogs.prompt_dialog_mixins.task_management import TaskManagementMixin
        from focuscheck.utils.clock import FakeClock

        clock = FakeClock(datetime(2030, 1, 1, tzinfo=timezone.utc))
        taskdb = mock.Mock()
        prompt = TaskManagementMixin.__new__(TaskManagementMixin)
        prompt.taskdb = taskdb
        prompt._task_clock = clock
        prompt._task_decision_required = False
        prompt._task_decision_task_id = None
        prompt._focus_prompt_open = False
        prompt._render_task_panel = mock.Mock()
        prompt._refresh_analytics = mock.Mock()

        due = (clock.now_utc() + timedelta(seconds=5)).isoformat()
        prompt._task_mark_done(42, due)
        taskdb.mark_completed.assert_called_once_with(42)

        taskdb.reset_mock()
        clock.advance(5)
        prompt._task_mark_done(42, due)
        taskdb.mark_failed.assert_called_once_with(42, timed_out=True)
        taskdb.mark_completed.assert_not_called()

    def test_render_task_panel_restarts_after_automatic_timeout(self):
        from focuscheck.ui.dialogs.prompt_dialog_mixins import task_management
        from focuscheck.ui.dialogs.prompt_dialog_mixins.task_management import TaskManagementMixin

        class FakeWidget:
            def __init__(self, *args, **kwargs):
                self.children = []

            def pack(self, *args, **kwargs):
                return None

            def bind(self, *args, **kwargs):
                return None

            def winfo_children(self):
                return list(self.children)

            def destroy(self):
                return None

        taskdb = mock.Mock()
        taskdb.get_active.side_effect = [
            {
                "id": 7,
                "status": "active",
                "title": "Overdue",
                "why": "",
                "consequences": "",
                "due_utc": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
            },
            None,
        ]
        taskdb.mark_failed.return_value = True
        prompt = TaskManagementMixin.__new__(TaskManagementMixin)
        prompt.taskdb = taskdb
        prompt.settings = {"tasks_decision_window_minutes": 10, "tasks_decision_prompt_enabled": True,
                           "tasks_evaluation_mode": "before"}
        prompt._task_panel = FakeWidget()
        prompt._task_timer_id = None
        prompt._open_task_history = mock.Mock()

        with mock.patch.object(task_management.tk, "Frame", FakeWidget), \
             mock.patch.object(task_management.tk, "Label", FakeWidget):
            prompt._render_task_panel()

        taskdb.mark_failed.assert_called_once_with(7, timed_out=True)
        self.assertEqual(2, taskdb.get_active.call_count)

    def test_analytics_today_uses_explicit_timezone_at_dst_boundary(self):
        from focuscheck.database.task_db import TaskDB

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            path = Path(temp_dir) / "tasks.sqlite3"
            db = TaskDB(str(path))
            with sqlite3.connect(path) as con:
                con.executemany(
                    "INSERT INTO tasks(created_utc, title, why, consequences, status, completed_utc) "
                    "VALUES (?, ?, '', '', 'completed', ?)",
                    [
                        ("2026-03-08T04:30:00+00:00", "previous local day", "2026-03-08T04:31:00+00:00"),
                        ("2026-03-08T05:30:00+00:00", "current local day", "2026-03-08T05:31:00+00:00"),
                    ],
                )
                con.commit()

            counts = db.analytics_counts(
                timescale="today",
                user_timezone="America/New_York",
                now=datetime(2026, 3, 8, 7, 30, tzinfo=timezone.utc),
            )
            self.assertEqual(1, counts["completed"])

    def test_analytics_rejects_unknown_timezone_instead_of_using_machine_zone(self):
        from focuscheck.database.task_db import TaskDB

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            db = TaskDB(str(Path(temp_dir) / "tasks.sqlite3"))
            with self.assertRaises(ValueError):
                db.analytics_counts(timescale="today", user_timezone="Not/AZone")


class EngineV2MatchingTests(unittest.TestCase):
    def test_subpopup_uses_runtime_coordinator_effective_pause(self):
        from focuscheck.monitoring.engine_v2 import EngineV2

        app = mock.Mock()
        app._current_prompt = None
        app._intervention_active = False
        app.settings = {"paused": False, "pause_when_inactive_or_lid_closed": False}
        app._runtime_state.is_effectively_paused.return_value = True
        engine = EngineV2.__new__(EngineV2)
        engine.app = app
        engine._settings = app.settings
        engine._subpopup_active = False

        self.assertFalse(engine._should_check_subpopup())
        app._runtime_state.is_effectively_paused.assert_called_once_with()

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

    def test_match_flag_cooldown_uses_injected_clock_at_expiry_boundary(self):
        from focuscheck.monitoring.engine_v2 import EngineV2

        engine = EngineV2.__new__(EngineV2)
        engine._now = lambda: 1_600_000_600.0
        flags = [{"domain": "reddit.com", "enabled": True, "cooldown_minutes": 10, "last_dismissed": 1_600_000_000.0}]

        self.assertIsNotNone(engine._match_flag({"url": "https://reddit.com", "title": ""}, flags))
        engine._now = lambda: 1_600_000_599.999
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

    def test_allow_once_dismissal_is_persisted_without_starting_cooldown(self):
        from focuscheck.monitoring.engine_v2 import EngineV2

        app = mock.Mock()
        app.root = mock.Mock()
        app.settings = {
            "paused": False,
            "pause_when_inactive_or_lid_closed": False,
            "website_flags": [{
                "domain": "reddit.com",
                "enabled": True,
                "severity": 2,
                "cooldown_minutes": 5,
                "allow_once": True,
                "last_dismissed": None,
            }],
        }
        engine = EngineV2(app, activity_provider=lambda: {"url": "https://reddit.com", "title": "Reddit"})

        with mock.patch("focuscheck.monitoring.engine_v2.V2SubPopupDialog") as dialog_cls, mock.patch("focuscheck.monitoring.engine_v2.save_settings", return_value=True) as save:
            engine._maybe_show_subpopup()
            on_no = dialog_cls.call_args.kwargs["on_no"]
            on_no()

        entry = app.settings["website_flags"][0]
        self.assertFalse(entry["allow_once"])
        self.assertIsNone(entry["last_dismissed"])
        save.assert_called_once_with(app.settings)

    def test_allow_once_dismissal_uses_app_persistence_and_committed_state(self):
        from focuscheck.monitoring.engine_v2 import EngineV2

        class ComposedApp:
            def __init__(self):
                self.root = mock.Mock()
                self.settings = {
                    "paused": False,
                    "pause_when_inactive_or_lid_closed": False,
                    "website_flags": [{
                        "domain": "reddit.com",
                        "enabled": True,
                        "severity": 2,
                        "cooldown_minutes": 5,
                        "allow_once": True,
                        "last_dismissed": None,
                    }],
                }
                self.drafts = []

            def _persist_settings_draft(self, draft):
                self.drafts.append(draft)
                committed = copy.deepcopy(draft)
                self.settings = committed
                return type(
                    "Result", (), {"durable_write": True, "committed_settings": committed}
                )()

        app = ComposedApp()
        engine = EngineV2(app, activity_provider=lambda: {"url": "https://reddit.com", "title": "Reddit"})

        with mock.patch("focuscheck.monitoring.engine_v2.V2SubPopupDialog") as dialog_cls, \
                mock.patch("focuscheck.monitoring.engine_v2.save_settings", side_effect=AssertionError("repository bypass")):
            engine._maybe_show_subpopup()
            dialog_cls.call_args.kwargs["on_no"]()

        entry = app.settings["website_flags"][0]
        self.assertFalse(entry["allow_once"])
        self.assertIsNone(entry["last_dismissed"])
        self.assertEqual(1, len(app.drafts))
        self.assertFalse(app.drafts[0]["website_flags"][0]["allow_once"])

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

    def test_severity_three_title_only_activity_does_not_intervene(self):
        from focuscheck.monitoring.engine_v2 import EngineV2

        app = mock.Mock()
        app.root = mock.Mock()
        app.settings = {
            "paused": False,
            "pause_when_inactive_or_lid_closed": False,
            "website_flags": [{"domain": "reddit.com", "enabled": True, "cooldown_minutes": 0, "severity": 3}],
        }
        engine = EngineV2(app, activity_provider=lambda: {"hwnd": 123, "title": "Reddit", "url": None})

        with mock.patch("focuscheck.monitoring.engine_v2.InterventionWizard") as wizard_cls:
            engine._maybe_show_subpopup()

        wizard_cls.assert_not_called()

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

    def test_subpopup_construction_failure_releases_active_latch(self):
        from focuscheck.monitoring.engine_v2 import EngineV2

        app = mock.Mock()
        app.root = mock.Mock()
        app._runtime_state = None
        app.settings = {
            "paused": False,
            "pause_when_inactive_or_lid_closed": False,
            "website_flags": [{"domain": "reddit.com", "enabled": True, "cooldown_minutes": 0, "severity": 2}],
        }
        engine = EngineV2(app, activity_provider=lambda: {"url": "https://reddit.com", "title": "Reddit", "hwnd": 456})

        with mock.patch(
            "focuscheck.monitoring.engine_v2.V2SubPopupDialog",
            side_effect=RuntimeError("construction failed"),
        ):
            engine._maybe_show_subpopup()

        self.assertFalse(engine._subpopup_active)
        self.assertIsNone(engine._subpopup_dialog)

    def test_subpopup_shutdown_closes_owned_dialog(self):
        from focuscheck.monitoring.engine_v2 import EngineV2

        engine = EngineV2.__new__(EngineV2)
        engine._subpopup_generation = 4
        engine._subpopup_active = True
        dialog = mock.Mock()
        engine._subpopup_dialog = dialog
        engine._timers = mock.Mock()

        engine.shutdown()

        dialog.destroy.assert_called_once_with()
        engine._timers.close.assert_called_once_with()
        self.assertFalse(engine._subpopup_active)
        self.assertIsNone(engine._subpopup_dialog)

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

    def test_activity_duration_uses_injected_clock(self):
        from datetime import datetime, timezone
        from focuscheck.monitoring.engine_v2 import EngineV2
        from focuscheck.utils.clock import FakeClock

        clock = FakeClock(datetime(2030, 1, 1, tzinfo=timezone.utc))
        provider = mock.Mock(return_value={"title": "Example", "hwnd": 99})
        engine = EngineV2(mock.Mock(), activity_provider=provider, clock=clock)

        first = engine._get_activity_info()
        clock.advance(7)
        second = engine._get_activity_info()

        self.assertEqual(0.0, first["active_duration_s"])
        self.assertEqual(7.0, second["active_duration_s"])

    def test_activity_capture_uses_injected_clock(self):
        from datetime import datetime, timezone
        from focuscheck.monitoring.engine_v2 import EngineV2
        from focuscheck.utils.clock import FakeClock

        captured = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)
        clock = FakeClock(captured)
        engine = EngineV2(mock.Mock(), activity_provider=lambda: {"title": "Example"}, clock=clock)

        info = engine._get_activity_info()

        self.assertEqual(captured.isoformat(), info["captured_utc"])

    def test_activity_provider_error_is_not_usable_for_website_intervention(self):
        from focuscheck.monitoring.engine_v2 import EngineV2

        class App:
            root = mock.Mock()
            _current_prompt = None
            _intervention_active = False
            settings = {
                "paused": False,
                "pause_when_inactive_or_lid_closed": False,
                "website_flags": [{"domain": "reddit.com", "severity": 2, "cooldown_minutes": 0}],
            }

        engine = EngineV2(App(), activity_provider=lambda: (_ for _ in ()).throw(RuntimeError("provider")))
        with mock.patch("focuscheck.monitoring.engine_v2.V2SubPopupDialog") as dialog_cls:
            engine._maybe_show_subpopup()

        dialog_cls.assert_not_called()

    def test_stale_activity_is_not_usable_for_website_intervention(self):
        from focuscheck.monitoring.engine_v2 import EngineV2
        from focuscheck.utils.clock import FakeClock

        captured = datetime(2030, 1, 1, tzinfo=timezone.utc)
        clock = FakeClock(captured + timedelta(seconds=10))

        class App:
            root = mock.Mock()
            _current_prompt = None
            _intervention_active = False
            settings = {
                "paused": False,
                "pause_when_inactive_or_lid_closed": False,
                "website_flags": [{"domain": "reddit.com", "severity": 2, "cooldown_minutes": 0}],
            }

        engine = EngineV2(
            App(),
            activity_provider=lambda: {
                "hwnd": 1,
                "title": "Reddit",
                "url": "https://reddit.com",
                "captured_utc": captured.isoformat(),
            },
            clock=clock,
        )
        with mock.patch("focuscheck.monitoring.engine_v2.V2SubPopupDialog") as dialog_cls:
            engine._maybe_show_subpopup()

        dialog_cls.assert_not_called()


class StartupCommandTests(unittest.TestCase):
    def test_frozen_startup_command_targets_packaged_supervisor(self):
        from focuscheck.platform_specific import startup

        with mock.patch.object(startup.sys, "frozen", True, create=True), \
                mock.patch.object(startup.sys, "executable", "C:\\FocusCheck\\app\\FocusCheck.exe"):
            command = startup.compose_startup_command()

        self.assertIn('"C:\\FocusCheck\\app\\FocusCheckSupervisor.exe"', command)
        self.assertIn("--run", command)
        self.assertIn('--base-dir "C:\\FocusCheck\\app"', command)

    def test_compose_startup_command_targets_supervisor_entrypoint(self):
        from focuscheck.platform_specific import startup

        with mock.patch.object(startup.sys, "frozen", False, create=True), mock.patch.object(startup.sys, "executable", "C:\\Python\\python.exe"), mock.patch.object(startup.sys, "argv", ["C:\\Temp\\test_runner.py"]):
            command = startup.compose_startup_command()

        self.assertIn('"C:\\Python\\python.exe"', command)
        self.assertIn("focuscheck_supervisor.py", command)
        self.assertIn("--run", command)
        self.assertIn("--base-dir", command)
        self.assertNotIn("test_runner.py", command)

    def test_explicit_startup_entrypoint_keeps_supervisor_arguments(self):
        from focuscheck.platform_specific import startup

        with mock.patch.object(startup.sys, "frozen", False, create=True), \
                mock.patch.object(startup.sys, "executable", "C:\\Python\\python.exe"):
            command = startup.compose_startup_command("C:\\FocusCheck\\focuscheck_supervisor.py")

        self.assertIn('"C:\\FocusCheck\\focuscheck_supervisor.py"', command)
        self.assertIn('--run --base-dir "C:\\FocusCheck"', command)

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

    def test_install_startup_closes_registry_handle_when_write_fails(self):
        from focuscheck.platform_specific import startup

        calls = {"closed": 0}

        def close_key(_key):
            calls["closed"] += 1

        fake_winreg = types.SimpleNamespace(
            HKEY_CURRENT_USER=object(),
            KEY_SET_VALUE=1,
            REG_SZ=1,
            OpenKey=lambda *_args: "key",
            SetValueEx=lambda *_args: (_ for _ in ()).throw(OSError("registry write failed")),
            CloseKey=close_key,
        )

        with mock.patch.dict(sys.modules, {"winreg": fake_winreg}), mock.patch.object(
            startup._platform, "system", return_value="Windows"
        ):
            self.assertFalse(startup.install_startup("FocusCheckTest"))

        self.assertEqual(1, calls["closed"])

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

    def test_inspect_startup_classifies_legacy_startup_folder_launcher(self):
        from focuscheck.platform_specific import startup

        fake_winreg = types.SimpleNamespace(
            HKEY_CURRENT_USER=object(),
            KEY_READ=2,
            OpenKey=lambda *_args: (_ for _ in ()).throw(FileNotFoundError()),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            launcher = Path(temp_dir) / "RunFocusCheckSupervisor.cmd"
            launcher.write_text("@echo off", encoding="ascii")
            with mock.patch.dict(sys.modules, {"winreg": fake_winreg}), \
                    mock.patch.object(startup._platform, "system", return_value="Windows"), \
                    mock.patch.object(startup, "_startup_launcher_path", return_value=launcher):
                inspection = startup.inspect_startup("FocusCheckTest")

        self.assertEqual("legacy", inspection.status)
        self.assertTrue(inspection.launcher_present)
        self.assertTrue(inspection.repairable)

    def test_inspect_startup_classifies_registry_and_folder_duplicate(self):
        from focuscheck.platform_specific import startup

        fake_winreg = types.SimpleNamespace(
            HKEY_CURRENT_USER=object(),
            KEY_READ=2,
            OpenKey=lambda *_args: "key",
            QueryValueEx=lambda *_args: ('"C:\\FocusCheck\\focuscheck_supervisor.py" --run', 1),
            CloseKey=lambda _key: None,
        )
        launcher = Path("C:/FocusCheck/RunFocusCheckSupervisor.cmd")
        with mock.patch.dict(sys.modules, {"winreg": fake_winreg}), \
                mock.patch.object(startup._platform, "system", return_value="Windows"), \
                mock.patch.object(startup, "compose_startup_command", return_value='"C:\\FocusCheck\\focuscheck_supervisor.py" --run'), \
                mock.patch.object(startup, "_startup_launcher_path", return_value=launcher), \
                mock.patch.object(Path, "exists", return_value=True):
            inspection = startup.inspect_startup("FocusCheckTest")

        self.assertEqual("duplicate", inspection.status)
        self.assertTrue(inspection.launcher_present)
        self.assertTrue(inspection.repairable)

    def test_repair_startup_promotes_registry_route_and_removes_legacy_launcher(self):
        from focuscheck.platform_specific import startup

        calls = {}
        fake_winreg = types.SimpleNamespace(
            HKEY_CURRENT_USER=object(),
            KEY_READ=2,
            KEY_SET_VALUE=4,
            REG_SZ=1,
            OpenKey=lambda *_args: (_ for _ in ()).throw(FileNotFoundError()),
            CreateKey=lambda *_args: "key",
            SetValueEx=lambda _key, name, _reserved, _typ, value: calls.update({"name": name, "value": value}),
            CloseKey=lambda _key: None,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            launcher = Path(temp_dir) / "RunFocusCheckSupervisor.cmd"
            launcher.write_text("@echo off", encoding="ascii")
            with mock.patch.dict(sys.modules, {"winreg": fake_winreg}), \
                    mock.patch.object(startup._platform, "system", return_value="Windows"), \
                    mock.patch.object(startup, "_startup_launcher_path", return_value=launcher):
                self.assertTrue(startup.repair_startup("FocusCheckTest"))

            self.assertEqual("FocusCheckTest", calls["name"])
            self.assertFalse(launcher.exists())


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
                self.assertTrue(app._request_supervisor_stop())

            self.assertTrue(stop_file.exists())
            payload = json.loads(stop_file.read_text(encoding="ascii"))
            self.assertEqual(1, payload["protocol_version"])
            self.assertTrue(payload["request_id"])

    def test_app_supervisor_stop_request_without_supervisor_is_explicit_failure(self):
        from focuscheck.app import App

        app = App.__new__(App)
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(app._request_supervisor_stop())


if __name__ == "__main__":
    unittest.main()

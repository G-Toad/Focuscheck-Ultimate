"""Run non-disruptive FocusCheck QA scenarios in an isolated data container.

The runner avoids the user's live FocusCheck profile by forcing FOCUS_DATA_DIR
to ``_qa_runtime/data`` before importing application modules. GUI smoke cases
withdraw their windows immediately and call handlers directly.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import shutil
import sys
import time
import traceback
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = ROOT / "_qa_runtime"
DATA_DIR = RUNTIME_DIR / "data"
EVENTS_PATH = RUNTIME_DIR / "events.jsonl"
REPORT_PATH = RUNTIME_DIR / "report.html"

MANUAL_ONLY_CHECKS = [
    {
        "area": "Windows startup",
        "check": "Enable and disable startup, then inspect HKCU Run for focuscheck_supervisor.py --run --base-dir. Save screenshot/log evidence.",
    },
    {
        "area": "Tray shell",
        "check": "Use the live tray menu for Prompt Now, Snooze, Settings, folders, startup toggle, and Exit. Confirm disabled tray gates are reflected visually.",
    },
    {
        "area": "Supervisor",
        "check": "Start supervised, kill the child to confirm restart, then exit from tray and confirm the supervisor does not restart it.",
    },
    {
        "area": "Power/session",
        "check": "Lock, unlock, sleep, and resume Windows with pause toggles on/off; confirm heartbeat, pause reason, and next prompt scheduling stay coherent.",
    },
    {
        "area": "Browser flags",
        "check": "Run reddit.com/example flagged domains across supported real browsers; confirm exact, subdomain, cooldown, severity 1/2/3, and suffix-attack behaviour.",
    },
    {
        "area": "Overlays",
        "check": "Verify V2 intervention, spotlight, blackout, stage5 dimming, click-through, Escape/Enter, and cancel paths across the real monitor layout.",
    },
]


class QaLog:
    def __init__(self, path: Path):
        self.path = path
        self.events: list[dict] = []

    def event(self, scenario: str, state: str, ok: bool, **details):
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "scenario": scenario,
            "state": state,
            "ok": bool(ok),
            "details": details,
        }
        self.events.append(payload)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, sort_keys=True) + "\n")


@contextmanager
def scenario(log: QaLog, name: str):
    start = time.monotonic()
    log.event(name, "start", True)
    try:
        yield
    except Exception as exc:
        log.event(
            name,
            "error",
            False,
            error_type=type(exc).__name__,
            error=str(exc),
            traceback=traceback.format_exc(limit=8),
        )
    else:
        log.event(name, "complete", True, elapsed_ms=int((time.monotonic() - start) * 1000))


def prepare_runtime(reset: bool):
    if reset and RUNTIME_DIR.exists():
        shutil.rmtree(RUNTIME_DIR)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    EVENTS_PATH.write_text("", encoding="utf-8")
    os.environ["FOCUS_DATA_DIR"] = str(DATA_DIR)


def run_settings_scenarios(log: QaLog):
    from focuscheck.settings.defaults import DEFAULT_SETTINGS
    from focuscheck.settings.manager import validate_settings
    from focuscheck.settings.registry import SETTINGS_REGISTRY
    from focuscheck.settings import gates

    with scenario(log, "settings.registry.default_coverage"):
        missing = sorted(set(DEFAULT_SETTINGS) - set(SETTINGS_REGISTRY))
        log.event("settings.registry.default_coverage", "assert_missing_defaults", not missing, missing=missing)
        assert not missing

    with scenario(log, "settings.validation.boolean_strings"):
        settings = validate_settings(
            {
                "paused": "false",
                "force_always_on": "false",
                "tray_exit_button_enabled": "no",
                "overlays_enabled": "off",
            }
        )
        checks = {
            "paused": settings["paused"] is False,
            "force_always_on": settings["force_always_on"] is False,
            "tray_exit_button_enabled": settings["tray_exit_button_enabled"] is False,
            "overlays_enabled": settings["overlays_enabled"] is False,
        }
        log.event("settings.validation.boolean_strings", "assert_bool_coercion", all(checks.values()), checks=checks)
        assert all(checks.values())

    with scenario(log, "settings.gates.pause_overlay_exit"):
        checks = {
            "pause_force_blocks": gates.is_pause_enabled({"force_always_on": True, "pause_on_lock": True}) is False,
            "pause_granular_enables": gates.is_pause_enabled({"force_always_on": False, "pause_on_lock": True}) is True,
            "overlay_off": gates.are_overlays_enabled({"overlays_enabled": False}) is False,
            "exit_off": gates.is_exit_enabled({"tray_exit_button_enabled": False}) is False,
        }
        log.event("settings.gates.pause_overlay_exit", "assert_gates", all(checks.values()), checks=checks)
        assert all(checks.values())


def run_state_scenarios(log: QaLog):
    import unittest.mock as mock
    from focuscheck.app import resolve_initial_monitoring_state

    with scenario(log, "startup.state.precedence"):
        with mock.patch.dict(os.environ, {"FOCUSCHECK_FORCE_STARTED": "1", "FOCUSCHECK_START_STOP_MODE": "paused"}, clear=False):
            force_result = resolve_initial_monitoring_state({"paused": True})
        with mock.patch.dict(os.environ, {}, clear=True):
            persisted_result = resolve_initial_monitoring_state({"paused": True})
        checks = {
            "force_wins": force_result == (True, "env_force_started"),
            "persisted_pause": persisted_result == (False, "persisted_paused"),
        }
        log.event("startup.state.precedence", "assert_startup_state", all(checks.values()), checks=checks, force_result=force_result, persisted_result=persisted_result)
        assert all(checks.values())

    with scenario(log, "app.schedule_next.expired_timer"):
        from focuscheck.app import App

        class Root:
            def __init__(self):
                self.scheduled = []

            def after_cancel(self, _timer_id):
                raise RuntimeError("expired timer")

            def after(self, delay_ms, callback):
                self.scheduled.append((delay_ms, callback))
                return "new-timer"

        app = App.__new__(App)
        app.root = Root()
        app.settings = {"interval_seconds": 60}
        app._scheduled = "old-expired-timer"
        app._next_total_s = None
        app._next_due_mono = None

        App._schedule_next(app, 1500)
        checks = {"scheduled": len(app.root.scheduled) == 1, "delay": app.root.scheduled[0][0] == 1500, "timer_replaced": app._scheduled == "new-timer"}
        log.event("app.schedule_next.expired_timer", "assert_rescheduled", all(checks.values()), checks=checks)
        assert all(checks.values())

    with scenario(log, "guard.fake_lock_sleep_resume"):
        from focuscheck.app import App
        from focuscheck.ui.guards import PauseGuard

        settings = {
            "force_always_on": False,
            "pause_when_inactive_or_lid_closed": False,
            "pause_on_idle": False,
            "pause_on_lid_closed": False,
            "pause_on_lock": True,
            "pause_on_sleep": True,
            "pause_poll_interval_seconds": 5,
        }
        guard = PauseGuard(lambda: settings)
        guard._os = "windows"

        app = App.__new__(App)
        app.guard = guard
        app.settings = settings
        app._last_resume_mono = 0.0
        scheduled = []
        app._schedule_next = lambda delay_ms=None: scheduled.append(delay_ms)

        App._on_pause_event(app, "lock")
        locked_pause = guard.should_pause()
        App._on_pause_event(app, "sleep")
        sleep_pause = guard.should_pause()
        App._on_resume_event(app)
        resumed_pause = guard.should_pause()

        checks = {
            "lock_pauses": locked_pause is True,
            "sleep_pauses": sleep_pause is True,
            "resume_clears": resumed_pause is False,
            "pause_poll_scheduled": scheduled[:2] == [5000, 5000],
            "resume_prompt_scheduled": scheduled[-1] == 0,
        }
        log.event("guard.fake_lock_sleep_resume", "assert_guard_events", all(checks.values()), checks=checks, scheduled=scheduled)
        assert all(checks.values())


def run_tray_scenarios(log: QaLog):
    from focuscheck.system_tray import SystemTray

    class FakeTrayApp:
        def __init__(self):
            self.calls = []
            self.settings = {
                "paused": False,
                "tray_start_stop_enabled": True,
                "tray_settings_button_enabled": True,
                "tray_exit_button_enabled": True,
            }
            self.startup_enabled = False

        def _tray_pause(self):
            self.calls.append("pause")
            self.settings["paused"] = True
            return True

        def _tray_resume(self):
            self.calls.append("resume")
            self.settings["paused"] = False
            return True

        def _tray_prompt_now(self):
            self.calls.append("prompt_now")
            return True

        def _tray_snooze(self, minutes):
            self.calls.append(("snooze", minutes))
            return True

        def _open_task_dialog_from_tray(self):
            self.calls.append("task")
            return True

        def _tray_open_data_folder(self):
            self.calls.append("data")
            return True

        def _tray_open_logs_folder(self):
            self.calls.append("logs")
            return True

        def _is_startup_enabled(self):
            return self.startup_enabled

        def _tray_install_startup(self):
            self.calls.append("install_startup")
            self.startup_enabled = True
            return True

        def _tray_uninstall_startup(self):
            self.calls.append("uninstall_startup")
            self.startup_enabled = False
            return True

        def _tray_exit(self):
            self.calls.append("exit")
            return True

    with scenario(log, "tray.command_handlers.delegate_without_native_tray"):
        app = FakeTrayApp()
        tray = SystemTray(app=app, name="FocusCheckQA")

        tray._stop_reminders(None, None)
        tray._start_reminders(None, None)
        tray._prompt_now(None, None)
        tray._snooze(5)(None, None)
        tray._open_task(None, None)
        tray._open_data(None, None)
        tray._open_logs(None, None)
        tray._toggle_startup(None, None)
        tray._toggle_startup(None, None)

        expected = [
            "pause",
            "resume",
            "prompt_now",
            ("snooze", 5),
            "task",
            "data",
            "logs",
            "install_startup",
            "uninstall_startup",
        ]
        log.event("tray.command_handlers.delegate_without_native_tray", "assert_delegation", app.calls == expected, calls=app.calls)
        assert app.calls == expected

    with scenario(log, "tray.gates.block_disabled_start_stop_exit"):
        import unittest.mock as mock

        app = FakeTrayApp()
        app.settings["tray_start_stop_enabled"] = False
        app.settings["tray_exit_button_enabled"] = False
        tray = SystemTray(app=app, name="FocusCheckQA")

        with mock.patch("focuscheck.system_tray.sys.exit") as exit_mock:
            tray._stop_reminders(None, None)
            tray._start_reminders(None, None)
            tray._on_quit(None, None)

        checks = {"no_app_calls": app.calls == [], "no_process_exit": exit_mock.call_count == 0}
        log.event("tray.gates.block_disabled_start_stop_exit", "assert_gated", all(checks.values()), checks=checks)
        assert all(checks.values())


def run_supervisor_scenarios(log: QaLog):
    import tempfile
    from pathlib import Path

    from focuscheck_supervisor import FocusCheckSupervisor

    class MemoryLogger:
        def __init__(self):
            self.lines = []

        def log(self, message):
            self.lines.append(message)

    class FakeEvent:
        def __init__(self):
            self._set = False
            self.waits = []

        def set(self):
            self._set = True

        def is_set(self):
            return self._set

        def wait(self, timeout=None):
            self.waits.append(timeout)
            return self._set

    class FakeProcess:
        def __init__(self, pid, exit_code=None):
            self.pid = pid
            self.exit_code = exit_code
            self.terminated = False

        def poll(self):
            return self.exit_code

        def terminate(self):
            self.terminated = True
            self.exit_code = 0

        def kill(self):
            self.exit_code = -9

        def wait(self, timeout=None):
            return self.exit_code

    class HarnessSupervisor(FocusCheckSupervisor):
        def _setup_signal_handlers(self):
            return None

    def make_supervisor(temp_dir, plan):
        logger = MemoryLogger()
        supervisor = HarnessSupervisor(
            target_script=Path(temp_dir) / "main.py",
            python_executable="python",
            logger=logger,
            check_interval=1,
            resume_gap=10,
            restart_delay=1,
            stop_file=Path(temp_dir) / "supervisor.stop",
        )
        supervisor.stop_event = FakeEvent()
        supervisor.launches = []
        supervisor.stop_after_last_launch = False

        def fake_launch():
            if not plan:
                supervisor.stop_event.set()
                return
            item = plan.pop(0)
            if item == "intentional-exit":
                proc = FakeProcess(500 + len(supervisor.launches), exit_code=0)
                supervisor.stop_file.write_text(json.dumps({
                    "protocol_version": 1,
                    "request_id": "qa-intentional-exit",
                    "supervisor_id": supervisor.supervisor_id,
                    "generation": supervisor.child_generation,
                    "pid": proc.pid,
                    "process_start_utc": "",
                    "utc": datetime.now(timezone.utc).isoformat(),
                    "reason": "user_exit",
                }), encoding="ascii")
            elif item == "crash":
                proc = FakeProcess(500 + len(supervisor.launches), exit_code=7)
            else:
                proc = FakeProcess(500 + len(supervisor.launches), exit_code=None)
            supervisor.child = proc
            supervisor.launches.append(proc)
            logger.log(f"fake launch pid={proc.pid} state={item}")
            if not plan and item != "intentional-exit":
                supervisor.stop_after_last_launch = True
                supervisor.stop_event.set()

        supervisor._launch_focuscheck = fake_launch
        return supervisor, logger

    with scenario(log, "supervisor.child_crash_restarts"):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            supervisor, logger = make_supervisor(temp_dir, ["crash", "running"])
            supervisor.run()
            checks = {
                "two_launches": len(supervisor.launches) == 2,
                "exit_logged": any("FocusCheck exited with 7" in line for line in logger.lines),
                "restart_logged": any("Restarting in" in line for line in logger.lines),
            }
            log.event("supervisor.child_crash_restarts", "assert_restart", all(checks.values()), checks=checks, logs=logger.lines)
            assert all(checks.values())

    with scenario(log, "supervisor.intentional_exit_no_restart"):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            supervisor, logger = make_supervisor(temp_dir, ["intentional-exit"])
            supervisor.run()
            checks = {
                "one_launch": len(supervisor.launches) == 1,
                "intentional_logged": any("Intentional FocusCheck stop requested" in line for line in logger.lines),
                "stop_file_cleared": not supervisor.stop_file.exists(),
            }
            log.event("supervisor.intentional_exit_no_restart", "assert_no_restart", all(checks.values()), checks=checks, logs=logger.lines)
            assert all(checks.values())


def run_prompt_flow_scenarios(log: QaLog):
    import unittest.mock as mock
    from focuscheck.app import App
    from focuscheck.ui.dialogs.v2_prompt_dialog import V2PromptDialog

    class Var:
        def __init__(self, value):
            self.value = value

        def get(self):
            return self.value

    class Entry:
        def __init__(self):
            self.focused = False

        def focus_set(self):
            self.focused = True

    class AppRef:
        def __init__(self):
            self._intervention_active = False
            self.root = object()

    def make_dialog(answer="doing work", decision="yes"):
        dialog = V2PromptDialog.__new__(V2PromptDialog)
        dialog.settings = {"overdrive_after_seconds": 60, "v2_hide_prompt_during_intervention": True}
        dialog.answer_var = Var(answer)
        dialog.intervention_var = Var(decision)
        dialog.answer_entry = Entry()
        dialog.intervention_entry = Entry()
        dialog.spam_detector = None
        dialog.app_ref = AppRef()
        dialog.activity_info = {}
        dialog.slot_start_dt = None
        dialog._closed = False
        return dialog

    with scenario(log, "v2.intervention_exception_resets_state"):
        dialog = make_dialog()
        dialog.deiconify = lambda: None
        dialog.lift = lambda: None
        dialog._force_window_to_front = lambda: None
        dialog.winfo_viewable = lambda: True

        class Wizard:
            _error_shown = True

            def __init__(self, _parent):
                pass

            def run(self, **_kwargs):
                raise RuntimeError("boom")

        with mock.patch("focuscheck.ui.dialogs.v2_prompt_dialog.InterventionWizard", Wizard):
            result = dialog._start_intervention_stub()
        checks = {"result_false": result is False, "active_reset": dialog.app_ref._intervention_active is False}
        log.event("v2.intervention_exception_resets_state", "assert_reset", all(checks.values()), checks=checks)
        assert all(checks.values())

    with scenario(log, "v2.cancelled_intervention_no_success_log"):
        dialog = make_dialog(decision="yes")
        dialog._start_intervention_stub = lambda: False
        dialog._log_response = mock.Mock()
        dialog._close = mock.Mock()

        dialog._save()
        checks = {"no_log": dialog._log_response.call_count == 0, "no_close": dialog._close.call_count == 0}
        log.event("v2.cancelled_intervention_no_success_log", "assert_no_completion", all(checks.values()), checks=checks)
        assert all(checks.values())

    with scenario(log, "v2.no_intervention_logs_and_closes"):
        dialog = make_dialog(decision="no")
        dialog._log_response = mock.Mock()
        dialog._close = mock.Mock()

        dialog._save()
        checks = {"logged_once": dialog._log_response.call_count == 1, "closed_once": dialog._close.call_count == 1}
        log.event("v2.no_intervention_logs_and_closes", "assert_completion", all(checks.values()), checks=checks)
        assert all(checks.values())

    with scenario(log, "app.presenter.intervention_active_defers_without_dialog"):
        class Root:
            def grab_current(self):
                return None

        class Guard:
            def should_pause(self):
                raise AssertionError("guard should not be consulted while intervention is active")

        app = App.__new__(App)
        app.root = Root()
        app.guard = Guard()
        app.settings = {
            "paused": False,
            "pause_poll_interval_seconds": 5,
            "interval_seconds": 60,
        }
        app._intervention_active = True
        app._current_prompt = None
        app._engine = mock.Mock()
        app._ensure_engine = mock.Mock()
        scheduled = []
        app._schedule_next = lambda delay_ms=None: scheduled.append(delay_ms)

        with mock.patch("focuscheck.app.load_settings", return_value=app.settings):
            App._maybe_show_prompt(app)

        checks = {
            "deferred": scheduled == [1500],
            "engine_not_ensured": app._ensure_engine.call_count == 0,
            "dialog_not_created": app._engine.create_prompt.call_count == 0,
            "prompt_still_empty": app._current_prompt is None,
        }
        log.event("app.presenter.intervention_active_defers_without_dialog", "assert_deferred", all(checks.values()), checks=checks, scheduled=scheduled)
        assert all(checks.values())


def run_persistence_scenarios(log: QaLog):
    from focuscheck.database.task_db import TaskDB
    from focuscheck.database import csv_logger

    with scenario(log, "taskdb.lifecycle"):
        db = TaskDB(str(DATA_DIR / "qa_tasks.sqlite3"))
        task_id = db.start_task(title="QA task", due_utc=None, why="verify", consequences="regression")
        active = db.get_active()
        db.mark_completed(task_id)
        history = db.list_history()
        checks = {
            "task_id": isinstance(task_id, int),
            "active_title": active and active["title"] == "QA task",
            "history_completed": any(row["status"] == "completed" for row in history),
        }
        log.event("taskdb.lifecycle", "assert_taskdb", all(checks.values()), checks=checks)
        assert all(checks.values())

    with scenario(log, "csv_logger.append"):
        log_path = DATA_DIR / "qa_focus_log.csv"
        original_path = csv_logger.LOG_PATH
        csv_logger.LOG_PATH = str(log_path)
        try:
            ok_header = csv_logger.ensure_log_header()
            slot_utc = datetime.now(timezone.utc)
            ok_append = csv_logger.append_log(
                response="QA",
                latency_ms=10,
                settings={"interval_seconds": 60, "intensify_after_seconds": 30, "overdrive_after_seconds": 120},
                intensity_level_reached=0,
                slot_start_dt={
                    "mono_start": time.monotonic(),
                    "utc_start": slot_utc,
                    "local_minute": slot_utc.astimezone().strftime("%Y-%m-%d %H:%M"),
                },
                overdrive_deadline_s=120,
            )
        finally:
            csv_logger.LOG_PATH = original_path
        rows = log_path.read_text(encoding="utf-8").splitlines()
        checks = {"header": ok_header, "append": ok_append, "row_count": len(rows) >= 2}
        log.event("csv_logger.append", "assert_csv", all(checks.values()), checks=checks, path=str(log_path))
        assert all(checks.values())


def run_monitoring_scenarios(log: QaLog):
    from focuscheck.monitoring.engine_v2 import EngineV2

    with scenario(log, "monitoring.website_flags"):
        settings = {
            "website_flags": [
                {"domain": "reddit.com", "enabled": True, "severity": 2, "cooldown_minutes": 0},
                {"domain": "example.com", "enabled": False, "severity": 1, "cooldown_minutes": 0},
            ]
        }
        engine = EngineV2(None)
        match = engine._match_flag({"url": "https://www.reddit.com/r/python", "title": "Reddit"}, settings["website_flags"])
        suffix_attack = engine._match_flag({"url": "https://badreddit.com", "title": "badreddit"}, settings["website_flags"])
        disabled = engine._match_flag({"url": "https://example.com", "title": "example"}, settings["website_flags"])
        checks = {"match": match is not None, "suffix_attack_blocked": suffix_attack is None, "disabled_blocked": disabled is None}
        log.event("monitoring.website_flags", "assert_matching", all(checks.values()), checks=checks)
        assert all(checks.values())

    with scenario(log, "monitoring.website_flags.fake_activity_provider"):
        import unittest.mock as mock

        app = mock.Mock()
        app.root = mock.Mock()
        app.settings = {
            "paused": False,
            "pause_when_inactive_or_lid_closed": False,
            "website_flags": [
                {"domain": "reddit.com", "enabled": True, "severity": 3, "cooldown_minutes": 0},
            ],
        }
        engine = EngineV2(
            app,
            activity_provider=lambda: {
                "url": "https://www.reddit.com/r/python",
                "title": "Reddit",
                "hwnd": 789,
            },
        )

        with mock.patch("focuscheck.monitoring.engine_v2.save_settings") as save_settings, mock.patch("focuscheck.monitoring.engine_v2.InterventionWizard") as wizard_cls:
            engine._maybe_show_subpopup()

        checks = {
            "wizard_started": wizard_cls.call_count == 1,
            "preselected_window": wizard_cls.return_value.run.call_args.kwargs.get("preselect_hwnd") == 789,
            "cooldown_saved": save_settings.call_count == 1,
            "active_reset": engine._subpopup_active is False,
        }
        log.event("monitoring.website_flags.fake_activity_provider", "assert_fake_activity", all(checks.values()), checks=checks)
        assert all(checks.values())


def run_gui_scenarios(log: QaLog):
    import tkinter as tk
    from focuscheck.ui.dialogs.task_change_dialog import TaskChangeDialog
    from focuscheck.ui.dialogs.task_entry_dialog import TaskEntryDialog
    from focuscheck.ui.dialogs.snooze_prompt_dialog import SnoozePromptDialog

    with scenario(log, "gui.task_entry.enter_submit"):
        root = tk.Tk()
        root.withdraw()
        submitted = []
        try:
            dialog = TaskEntryDialog(root, submitted.append)
            dialog.withdraw()
            dialog.title_var.set("QA entered task")
            result = dialog._on_return()
            root.update()
            checks = {"break": result == "break", "submitted": bool(submitted), "destroyed": not bool(dialog.winfo_exists())}
            log.event("gui.task_entry.enter_submit", "assert_enter", all(checks.values()), checks=checks, payload=submitted[0] if submitted else None)
            assert all(checks.values())
        finally:
            root.destroy()

    with scenario(log, "gui.snooze.optional_fields"):
        root = tk.Tk()
        root.withdraw()
        submitted = []
        try:
            dialog = SnoozePromptDialog(
                root,
                {
                    "always_on_top": False,
                    "snooze_prompt_ask_reason": False,
                    "snooze_prompt_exact_enabled": False,
                    "snooze_prompt_validation_enabled": False,
                },
                on_submit=submitted.append,
            )
            dialog.withdraw()
            result = dialog._on_return(None)
            root.update()
            checks = {"break": result == "break", "submitted": bool(submitted), "destroyed": not bool(dialog.winfo_exists())}
            log.event("gui.snooze.optional_fields", "assert_optional_submit", all(checks.values()), checks=checks, payload=submitted[0] if submitted else None)
            assert all(checks.values())
        finally:
            root.destroy()

    with scenario(log, "gui.task_change.enter_submit"):
        root = tk.Tk()
        root.withdraw()
        submitted = []
        try:
            dialog = TaskChangeDialog(root, submitted.append)
            dialog.withdraw()
            dialog.reason_var.set("QA changed scope")
            dialog.title_var.set("QA replacement")
            result = dialog._on_return()
            root.update()
            checks = {"break": result == "break", "submitted": bool(submitted), "destroyed": not bool(dialog.winfo_exists())}
            log.event("gui.task_change.enter_submit", "assert_enter", all(checks.values()), checks=checks, payload=submitted[0] if submitted else None)
            assert all(checks.values())
        finally:
            root.destroy()


def write_report(log: QaLog):
    grouped: dict[str, list[dict]] = {}
    for event in log.events:
        grouped.setdefault(event["scenario"], []).append(event)
    failures = [event for event in log.events if not event["ok"]]
    cards = []
    for name, events in grouped.items():
        ok = all(event["ok"] for event in events)
        cls = "pass" if ok else "fail"
        rows = []
        for event in events:
            detail = html.escape(json.dumps(event.get("details", {}), indent=2, sort_keys=True))
            rows.append(f"<tr><td>{html.escape(event['state'])}</td><td>{event['ok']}</td><td><pre>{detail}</pre></td></tr>")
        cards.append(
            f"<section class='card {cls}'><h2>{html.escape(name)}</h2>"
            f"<table><thead><tr><th>State</th><th>OK</th><th>Details</th></tr></thead><tbody>{''.join(rows)}</tbody></table></section>"
        )
    manual_rows = []
    for item in MANUAL_ONLY_CHECKS:
        manual_rows.append(
            "<tr>"
            f"<td>{html.escape(item['area'])}</td>"
            "<td>manual</td>"
            f"<td><pre>{html.escape(item['check'])}</pre></td>"
            "</tr>"
        )
    cards.append(
        "<section class='card manual'><h2>Manual Windows Gates</h2>"
        "<table><thead><tr><th>Area</th><th>Status</th><th>Required Check</th></tr></thead>"
        f"<tbody>{''.join(manual_rows)}</tbody></table></section>"
    )

    report = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>FocusCheck QA Report</title>
  <style>
    body {{ margin: 0; font-family: Consolas, monospace; background: #101412; color: #e7efe9; }}
    header {{ padding: 24px; background: linear-gradient(135deg, #18352c, #111); border-bottom: 1px solid #38564a; }}
    main {{ padding: 18px; display: grid; gap: 14px; }}
    .summary {{ display: flex; gap: 16px; flex-wrap: wrap; }}
    .pill {{ padding: 10px 14px; border: 1px solid #38564a; background: #16201c; border-radius: 999px; }}
    .card {{ border: 1px solid #38564a; border-left-width: 8px; background: #151a18; border-radius: 10px; overflow: hidden; }}
    .card.pass {{ border-left-color: #3ddc84; }}
    .card.fail {{ border-left-color: #ff5c5c; }}
    .card.manual {{ border-left-color: #ffd166; }}
    h1, h2 {{ margin: 0; }}
    h2 {{ padding: 14px; font-size: 16px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; vertical-align: top; border-top: 1px solid #26332e; padding: 8px; }}
    pre {{ white-space: pre-wrap; margin: 0; color: #b7c9be; }}
  </style>
</head>
<body>
  <header>
    <h1>FocusCheck QA Report</h1>
    <p>Isolated data container: {html.escape(str(DATA_DIR))}</p>
    <div class="summary">
      <div class="pill">Scenarios: {len(grouped)}</div>
      <div class="pill">Events: {len(log.events)}</div>
      <div class="pill">Failures: {len(failures)}</div>
    </div>
  </header>
  <main>{''.join(cards)}</main>
</body>
</html>
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run isolated FocusCheck QA scenarios.")
    parser.add_argument("--reset", action="store_true", help="Delete _qa_runtime before running.")
    parser.add_argument("--skip-gui", action="store_true", help="Skip withdrawn Tk smoke scenarios.")
    args = parser.parse_args(argv)

    prepare_runtime(reset=args.reset)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    log = QaLog(EVENTS_PATH)
    log.event("runner", "prepared", True, root=str(ROOT), data_dir=str(DATA_DIR), report=str(REPORT_PATH))

    run_settings_scenarios(log)
    run_state_scenarios(log)
    run_tray_scenarios(log)
    run_supervisor_scenarios(log)
    run_prompt_flow_scenarios(log)
    run_persistence_scenarios(log)
    run_monitoring_scenarios(log)
    if not args.skip_gui:
        run_gui_scenarios(log)

    write_report(log)
    failures = [event for event in log.events if not event["ok"]]
    print(f"qa_report={REPORT_PATH}")
    print(f"qa_events={EVENTS_PATH}")
    print(f"qa_failures={len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

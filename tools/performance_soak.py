"""Bounded resource-stability smoke test for core non-UI services."""

from __future__ import annotations

import gc
import json
import sys
import tempfile
import threading
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from focuscheck.database.task_db import TaskDB
from focuscheck.monitoring.activity import safe_activity_snapshot
from focuscheck.runtime.state import RuntimeStateCoordinator
from focuscheck.utils.timers import TimerRegistry


class Scheduler:
    def __init__(self):
        self.callbacks = {}
        self.next_id = 0

    def after(self, _delay, callback):
        self.next_id += 1
        self.callbacks[self.next_id] = callback
        return self.next_id

    def after_cancel(self, callback_id):
        self.callbacks.pop(callback_id, None)


def main() -> int:
    started = time.perf_counter()
    tracemalloc.start()
    non_daemon_before = {
        thread.ident for thread in threading.enumerate()
        if not thread.daemon and thread.ident != threading.get_ident()
    }
    scheduler = Scheduler()
    timers = TimerRegistry(scheduler)
    for index in range(5000):
        timers.schedule("soak", index % 17, lambda: None)
        timers.cancel("soak")
    timers.close()

    state = RuntimeStateCoordinator({}, persist=lambda _settings: True)
    for index in range(10000):
        state.set_manual_paused(index % 2 == 0)
        state.set_manual_paused(False)
    state.request_shutdown()

    # Exercise the bounded provider boundary repeatedly. A fast provider must
    # not leave worker threads behind or accumulate stale activity state.
    activity_calls = 0

    def provider():
        nonlocal activity_calls
        activity_calls += 1
        return {
            "title": "soak",
            "process_name": "FocusCheckSoak",
            "captured_utc": "2030-01-01T00:00:00+00:00",
        }

    for _ in range(500):
        snapshot = safe_activity_snapshot(provider, timeout_seconds=0.25)
        if snapshot.errors:
            raise RuntimeError(f"activity provider soak failed: {snapshot.errors}")

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "tasks.sqlite3"
        db = TaskDB(str(db_path))
        for index in range(250):
            task_id = db.start_task(title=f"soak-{index}", due_utc=None, why="", consequences="")
            db.mark_completed(task_id)
        db_size = db_path.stat().st_size

    gc.collect()
    time.sleep(0.05)
    non_daemon_after = {
        thread.ident for thread in threading.enumerate()
        if not thread.daemon and thread.ident != threading.get_ident()
    }
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    elapsed = time.perf_counter() - started
    result = {
        "timer_callbacks_remaining": len(scheduler.callbacks),
        "activity_calls": activity_calls,
        "non_daemon_thread_leaks": len(non_daemon_after - non_daemon_before),
        "db_bytes": db_size,
        "peak_bytes": peak,
        "elapsed_seconds": round(elapsed, 3),
        "budgets": {
            "max_callbacks": 0,
            "min_activity_calls": 500,
            "max_non_daemon_thread_leaks": 0,
            "max_db_bytes": 2_000_000,
            "max_peak_bytes": 64_000_000,
            "max_elapsed_seconds": 15.0,
        },
    }
    result["passed"] = (
        result["timer_callbacks_remaining"] == 0
        and result["activity_calls"] == result["budgets"]["min_activity_calls"]
        and result["non_daemon_thread_leaks"] <= result["budgets"]["max_non_daemon_thread_leaks"]
        and db_size <= result["budgets"]["max_db_bytes"]
        and peak <= result["budgets"]["max_peak_bytes"]
        and elapsed <= result["budgets"]["max_elapsed_seconds"]
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

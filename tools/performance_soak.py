"""Bounded resource-stability smoke test for core non-UI services."""

from __future__ import annotations

import gc
import json
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from focuscheck.database.task_db import TaskDB
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

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "tasks.sqlite3"
        db = TaskDB(str(db_path))
        for index in range(250):
            task_id = db.start_task(title=f"soak-{index}", due_utc=None, why="", consequences="")
            db.mark_completed(task_id)
        db_size = db_path.stat().st_size

    gc.collect()
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    elapsed = time.perf_counter() - started
    result = {
        "timer_callbacks_remaining": len(scheduler.callbacks),
        "db_bytes": db_size,
        "peak_bytes": peak,
        "elapsed_seconds": round(elapsed, 3),
        "budgets": {"max_callbacks": 0, "max_db_bytes": 2_000_000, "max_peak_bytes": 64_000_000, "max_elapsed_seconds": 15.0},
    }
    result["passed"] = (
        result["timer_callbacks_remaining"] == 0
        and db_size <= result["budgets"]["max_db_bytes"]
        and peak <= result["budgets"]["max_peak_bytes"]
        and elapsed <= result["budgets"]["max_elapsed_seconds"]
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

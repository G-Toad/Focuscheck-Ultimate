"""Bounded mutation checks for selected high-risk pure contracts.

Mutations are applied only to temporary copies of the ``focuscheck`` package.
The stage passes when each targeted assertion kills its mutant.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Mutation:
    name: str
    source: str
    original: str
    replacement: str
    assertion: str


MUTATIONS = (
    Mutation(
        "domain_exact_match",
        "focuscheck/monitoring/engine_v2.py",
        "if host == domain:\n            return True",
        "if False and host == domain:\n            return True",
        """
from focuscheck.monitoring.engine_v2 import EngineV2
engine = EngineV2.__new__(EngineV2)
assert engine._domain_matches("example.com", "example.com")
""",
    ),
    Mutation(
        "prompt_pause_guard",
        "focuscheck/runtime/state.py",
        "or self.is_effectively_paused()",
        "or False",
        """
from focuscheck.runtime.state import RuntimeStateCoordinator
state = RuntimeStateCoordinator({"paused": True, "snooze_until_utc": ""})
assert not state.begin_prompt()
""",
    ),
    Mutation(
        "settings_schema_migration",
        "focuscheck/settings/migrations.py",
        'data["settings_schema_version"] = 2',
        'data["settings_schema_version"] = 1',
        """
from focuscheck.settings.migrations import migrate_settings
        assert migrate_settings({"settings_schema_version": 1})["settings_schema_version"] == 2
""",
    ),
    Mutation(
        "task_completion_requires_active_transition",
        "focuscheck/database/task_db.py",
        "UPDATE tasks SET status='completed', completed_utc=? WHERE id=? AND status='active'",
        "UPDATE tasks SET status='completed', completed_utc=? WHERE id=? AND status='completed'",
        """
import tempfile
from pathlib import Path
from focuscheck.database.task_db import TaskDB
with tempfile.TemporaryDirectory() as directory:
    db = TaskDB(Path(directory) / "tasks.db")
    task_id = db.start_task(title="task", due_utc=None, why="why", consequences="consequences")
    assert db.mark_completed(task_id)
""",
    ),
    Mutation(
        "supervisor_stable_ready_backoff",
        "focuscheck_supervisor.py",
        "if now - self._ready_since_mono < STABLE_RUNTIME_SECONDS:\n            return",
        "if False:\n            return",
        """
from unittest import mock
import focuscheck_supervisor as module
supervisor = module.FocusCheckSupervisor.__new__(module.FocusCheckSupervisor)
supervisor.restart_delay = 1.0
supervisor.current_delay = 8.0
supervisor._restart_history = [1.0]
supervisor._degraded_until = 99.0
supervisor._ready_since_mono = 10.0
supervisor.logger = type("Logger", (), {"log": lambda *_args: None})()
with mock.patch.object(module.time, "monotonic", return_value=39.9):
    supervisor._maybe_reset_after_stable()
assert supervisor.current_delay == 8.0
""",
    ),
    Mutation(
        "tray_post_start_timer_ownership",
        "focuscheck/system_tray.py",
        'if self._post_start_timer is timer_holder.get("timer"):',
        'if self._post_start_timer is timer:',
        """
from unittest.mock import patch
from focuscheck.system_tray import SystemTray

class App:
    settings = {}

class Icon:
    title = "FocusCheck"

class Timer:
    def __init__(self, _delay, callback):
        self.callback = callback
        self.daemon = False
    def start(self):
        return None
    def cancel(self):
        return None

alive = []
tray = SystemTray(app=App(), name="FocusCheck", on_alive=lambda: alive.append(True))
tray._icon = Icon()
with patch("focuscheck.system_tray.threading.Timer", Timer):
    tray._schedule_post_start_check()
    tray._post_start_timer.callback()
assert alive == [True]
assert tray._post_start_timer is None
""",
    ),
)


def _run_mutation(mutation: Mutation) -> None:
    with tempfile.TemporaryDirectory(prefix="focuscheck-mutation-") as temp_dir:
        root = Path(temp_dir)
        shutil.copytree(ROOT / "focuscheck", root / "focuscheck")
        source = root / mutation.source
        if not source.exists():
            source.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / mutation.source, source)
        text = source.read_text(encoding="utf-8")
        if mutation.original not in text:
            raise RuntimeError(f"mutation anchor missing: {mutation.name}")
        source.write_text(text.replace(mutation.original, mutation.replacement, 1), encoding="utf-8")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(root)
        env["FOCUS_DATA_DIR"] = str(root / "data")
        result = subprocess.run(
            [sys.executable, "-c", mutation.assertion],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if result.returncode == 0:
            raise RuntimeError(f"mutation survived: {mutation.name}")
        print(f"killed {mutation.name}")


def main() -> int:
    for mutation in MUTATIONS:
        _run_mutation(mutation)
    print(f"mutation_smoke_passed={len(MUTATIONS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

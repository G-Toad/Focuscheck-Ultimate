"""Exercise persisted pause and snooze state through real entrypoint restarts."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _save(root: Path, *, paused: bool, snooze_until_utc: str) -> None:
    os.environ["FOCUS_DATA_DIR"] = str(root)
    from focuscheck.settings import save_settings

    result = save_settings({"paused": paused, "snooze_until_utc": snooze_until_utc})
    assert result.durable_write, result


def _load(root: Path) -> dict:
    os.environ["FOCUS_DATA_DIR"] = str(root)
    from focuscheck.settings import load_settings

    return load_settings()


def _run_entrypoint(root: Path, label: str) -> None:
    env = os.environ.copy()
    env["FOCUS_DATA_DIR"] = str(root)
    env.pop("FOCUSCHECK_FORCE_STARTED", None)
    completed = subprocess.run(
        [sys.executable, str(ROOT / "main.py"), "--run-seconds=1"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert completed.returncode == 0, f"{label} failed: {completed.stdout}\n{completed.stderr}"


def _heartbeat(root: Path) -> dict:
    return json.loads((root / "hb.txt").read_text(encoding="utf-8"))


def main() -> int:
    original_environment = os.environ.copy()
    try:
        with tempfile.TemporaryDirectory(prefix="FocusCheck-state-restart-") as temp_dir:
            root = Path(temp_dir)
            try:
                _save(root, paused=True, snooze_until_utc="")
                _run_entrypoint(root, "manual pause restart")
                paused_after_restart = _load(root)
                assert paused_after_restart["paused"] is True
                assert paused_after_restart["snooze_until_utc"] == ""

                future = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
                _save(root, paused=False, snooze_until_utc=future)
                _run_entrypoint(root, "active snooze restart")
                snoozed_after_restart = _load(root)
                assert snoozed_after_restart["paused"] is True
                assert snoozed_after_restart["snooze_until_utc"]
                heartbeat = _heartbeat(root)
                assert heartbeat["effective_paused"] is True
                assert heartbeat["snooze_active"] is True
                assert heartbeat["pause_reason"] == "snooze"

                _save(root, paused=True, snooze_until_utc="2000-01-01T00:00:00+00:00")
                _run_entrypoint(root, "expired snooze restart")
                expired_after_restart = _load(root)
                # An expired legacy snooze is not durable manual intent.
                assert expired_after_restart["paused"] is False
                assert expired_after_restart["manual_paused"] is False
                assert expired_after_restart["snooze_until_utc"] == ""
                assert (root / "runtime_state.jsonl").exists()
                print("state restart pause/snooze integration passed")
                return 0
            finally:
                logging.shutdown()
    finally:
        os.environ.clear()
        os.environ.update(original_environment)


if __name__ == "__main__":
    raise SystemExit(main())

"""Exercise the source supervisor against a real disposable child process."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from focuscheck_supervisor import FileLogger, FocusCheckSupervisor, _pid_is_alive


CHILD_SOURCE = r'''
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

root = Path(os.environ["SUPERVISOR_TEST_ROOT"])
heartbeat = root / "hb.txt"
attempt_file = root / "attempts.txt"
try:
    attempt = int(attempt_file.read_text(encoding="ascii")) + 1
except (FileNotFoundError, ValueError):
    attempt = 1
attempt_file.write_text(str(attempt), encoding="ascii")
sequence = 0
process_start = datetime.now(timezone.utc).isoformat()
while True:
    payload = {
        "protocol_version": 1,
        "readiness": "ready",
        "generation": os.environ["FOCUSCHECK_CHILD_GENERATION"],
        "supervisor_id": os.environ["FOCUSCHECK_SUPERVISOR_ID"],
        "pid": os.getpid(),
        "process_start_utc": process_start,
        "sequence": sequence,
        "heartbeat_interval_seconds": 1,
        "utc": datetime.now(timezone.utc).isoformat(),
    }
    temporary = heartbeat.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload), encoding="ascii")
    os.replace(temporary, heartbeat)
    if attempt == 1:
        raise SystemExit(7)
    sequence += 1
    time.sleep(0.1)
'''


def _wait_for(path: Path, predicate, timeout: float) -> Any:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            try:
                value = predicate(path)
            except (OSError, ValueError, json.JSONDecodeError):
                value = None
            if value:
                return value
        time.sleep(0.05)
    raise AssertionError(f"Timed out waiting for {path}")


def _current_heartbeat(path: Path, generation: str | None) -> dict[str, Any] | None:
    candidate = json.loads(path.read_text(encoding="ascii"))
    return candidate if candidate.get("generation") == generation else None


def _attempt_count(path: Path) -> int | None:
    count = int(path.read_text(encoding="ascii"))
    return count if count >= 2 else None


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="FocusCheck-supervisor-") as temp_dir:
        root = Path(temp_dir)
        child = root / "child.py"
        child.write_text(CHILD_SOURCE, encoding="ascii")
        heartbeat = root / "hb.txt"
        stop_file = root / "supervisor.stop"
        ack_file = root / "supervisor.stop.ack"
        log_path = root / "supervisor.log"
        logger = FileLogger(log_path)
        supervisor = FocusCheckSupervisor(
            target_script=child,
            python_executable=sys.executable,
            logger=logger,
            check_interval=1,
            resume_gap=30,
            restart_delay=1,
            stop_file=stop_file,
            stop_ack_file=ack_file,
            heartbeat_path=heartbeat,
        )
        original_environment = os.environ.copy()
        os.environ.update({"SUPERVISOR_TEST_ROOT": str(root)})
        errors: list[BaseException] = []
        thread = threading.Thread(target=lambda: _run(supervisor, errors), daemon=True)
        try:
            thread.start()
            attempts = _wait_for(root / "attempts.txt", _attempt_count, 15)
            payload = _wait_for(
                heartbeat,
                lambda path: _current_heartbeat(path, supervisor.child_generation),
                5,
            )
            assert attempts >= 2
            assert payload["readiness"] == "ready"
            assert payload["generation"] == supervisor.child_generation
            assert payload["pid"] == supervisor.child.pid
            stop_file.write_text(json.dumps({
                "protocol_version": 1,
                "request_id": "source-selftest",
                "supervisor_id": supervisor.supervisor_id,
                "generation": payload["generation"],
                "pid": payload["pid"],
                "process_start_utc": payload["process_start_utc"],
                "utc": datetime.now(timezone.utc).isoformat(),
                "reason": "source_selftest",
            }), encoding="ascii")
            thread.join(15)
            assert not thread.is_alive(), "supervisor did not stop after acknowledged request"
            assert not errors, errors
            ack = json.loads(ack_file.read_text(encoding="ascii"))
            assert ack["request_id"] == "source-selftest"
            assert ack["generation"] == payload["generation"]
            assert ack["status"] == "acknowledged"
            assert ack["termination"] == "graceful"
            assert not _pid_is_alive(payload["pid"]), f"child process leaked: {payload['pid']}"
            print(f"source supervisor restart/stop passed (attempts={attempts}, child_pid={payload['pid']})")
            return 0
        finally:
            if thread.is_alive():
                supervisor.stop()
                thread.join(5)
            if supervisor.child is not None and supervisor.child.poll() is None:
                supervisor._terminate_child()
            os.environ.clear()
            os.environ.update(original_environment)


def _run(supervisor: FocusCheckSupervisor, errors: list[BaseException]) -> None:
    try:
        supervisor.run()
    except BaseException as exc:
        errors.append(exc)


if __name__ == "__main__":
    raise SystemExit(main())

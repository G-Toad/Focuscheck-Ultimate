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

import focuscheck_supervisor as supervisor_module
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
mode = os.environ.get("SUPERVISOR_TEST_MODE", "crash_stop")
while True:
    payload = {
        "protocol_version": 1,
        "readiness": "ready",
        "generation": os.environ["FOCUSCHECK_CHILD_GENERATION"],
        "supervisor_id": os.environ["FOCUSCHECK_SUPERVISOR_ID"],
        "pid": os.getpid(),
        "process_start_utc": process_start,
        "sequence": sequence,
        "heartbeat_interval_seconds": 0 if mode == "hang" else 1,
        "utc": datetime.now(timezone.utc).isoformat(),
    }
    temporary = heartbeat.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload), encoding="ascii")
    os.replace(temporary, heartbeat)
    if mode == "circuit" or (mode == "crash_stop" and attempt == 1):
        raise SystemExit(7)
    if mode == "hang" and attempt == 1:
        time.sleep(60)
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


def _wait_for_text(path: Path, text: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if text in path.read_text(encoding="utf-8"):
                return
        except OSError:
            pass
        time.sleep(0.05)
    raise AssertionError(f"Timed out waiting for {text!r} in {path}")


def _new_supervisor(root: Path, child: Path) -> FocusCheckSupervisor:
    return FocusCheckSupervisor(
        target_script=child,
        python_executable=sys.executable,
        logger=FileLogger(root / "supervisor.log"),
        check_interval=1,
        resume_gap=30,
        restart_delay=1,
        stop_file=root / "supervisor.stop",
        stop_ack_file=root / "supervisor.stop.ack",
        heartbeat_path=root / "hb.txt",
    )


def _run_thread(supervisor: FocusCheckSupervisor) -> tuple[threading.Thread, list[BaseException]]:
    errors: list[BaseException] = []
    thread = threading.Thread(target=lambda: _run(supervisor, errors), daemon=True)
    thread.start()
    return thread, errors


def _run_crash_and_stop(root: Path, child: Path) -> None:
    supervisor = _new_supervisor(root, child)
    thread, errors = _run_thread(supervisor)
    try:
        attempts = _wait_for(root / "attempts.txt", _attempt_count, 15)
        payload = _wait_for(
            root / "hb.txt",
            lambda path: _current_heartbeat(path, supervisor.child_generation),
            5,
        )
        assert attempts >= 2
        assert payload["readiness"] == "ready"
        assert payload["generation"] == supervisor.child_generation
        assert payload["pid"] == supervisor.child.pid
        (root / "supervisor.stop").write_text(json.dumps({
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
        ack = json.loads((root / "supervisor.stop.ack").read_text(encoding="ascii"))
        assert ack["request_id"] == "source-selftest"
        assert ack["generation"] == payload["generation"]
        assert ack["status"] == "acknowledged"
        assert ack["termination"] == "graceful"
        assert not _pid_is_alive(payload["pid"]), f"child process leaked: {payload['pid']}"
        print(f"source supervisor crash/restart/stop passed (attempts={attempts}, child_pid={payload['pid']})")
    finally:
        _cleanup_supervisor(supervisor, thread)


def _run_hang_restart(root: Path, child: Path) -> None:
    old_grace = supervisor_module.HEARTBEAT_GRACE_PERIOD
    old_max_age = supervisor_module.HEARTBEAT_MAX_AGE
    supervisor_module.HEARTBEAT_GRACE_PERIOD = 0.2
    supervisor_module.HEARTBEAT_MAX_AGE = 0.2
    supervisor = _new_supervisor(root, child)
    thread, errors = _run_thread(supervisor)
    first_pid = None
    try:
        first_payload = _wait_for(
            root / "hb.txt",
            lambda path: _current_heartbeat(path, supervisor.child_generation),
            5,
        )
        first_pid = int(first_payload["pid"])
        _wait_for(root / "attempts.txt", _attempt_count, 15)
        _wait_for_text(root / "supervisor.log", "Heartbeat stale; FocusCheck unresponsive; forcing restart", 15)
        assert supervisor.child is not None
        assert supervisor.child.pid != first_pid
        assert not _pid_is_alive(first_pid), f"hung child leaked: {first_pid}"
        assert not errors, errors
        print(f"source supervisor hang recovery passed (old_child_pid={first_pid})")
    finally:
        _cleanup_supervisor(supervisor, thread)
        supervisor_module.HEARTBEAT_GRACE_PERIOD = old_grace
        supervisor_module.HEARTBEAT_MAX_AGE = old_max_age


def _run_circuit_breaker(root: Path, child: Path) -> None:
    old_limit = supervisor_module.MAX_RESTARTS_IN_WINDOW
    supervisor_module.MAX_RESTARTS_IN_WINDOW = 2
    supervisor = _new_supervisor(root, child)
    thread, errors = _run_thread(supervisor)
    try:
        _wait_for_text(root / "supervisor.log", "Circuit breaker open", 15)
        assert not errors, errors
        assert supervisor.child is None or supervisor.child.poll() is not None
        print("source supervisor circuit breaker passed")
    finally:
        _cleanup_supervisor(supervisor, thread)
        supervisor_module.MAX_RESTARTS_IN_WINDOW = old_limit


def _cleanup_supervisor(supervisor: FocusCheckSupervisor, thread: threading.Thread) -> None:
    if thread.is_alive():
        supervisor.stop()
        thread.join(8)
    if supervisor.child is not None and supervisor.child.poll() is None:
        supervisor._terminate_child()
    assert not thread.is_alive(), "supervisor thread leaked"


def _run_scenario(mode: str, runner) -> None:
    with tempfile.TemporaryDirectory(prefix="FocusCheck-supervisor-") as temp_dir:
        root = Path(temp_dir)
        child = root / "child.py"
        child.write_text(CHILD_SOURCE, encoding="ascii")
        original_environment = os.environ.copy()
        try:
            os.environ.update({"SUPERVISOR_TEST_ROOT": str(root), "SUPERVISOR_TEST_MODE": mode})
            runner(root, child)
        finally:
            os.environ.clear()
            os.environ.update(original_environment)


def main() -> int:
    _run_scenario("crash_stop", _run_crash_and_stop)
    _run_scenario("hang", _run_hang_restart)
    _run_scenario("circuit", _run_circuit_breaker)
    return 0


def _run(supervisor: FocusCheckSupervisor, errors: list[BaseException]) -> None:
    try:
        supervisor.run()
    except BaseException as exc:
        errors.append(exc)


if __name__ == "__main__":
    raise SystemExit(main())

"""Bounded self-test for a frozen supervisor and its packaged child."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path


def _terminate_process_tree(pid: int) -> None:
    """Stop only the requested test process tree."""
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return
    try:
        os.kill(pid, 15)
    except OSError:
        pass


def _write_stop_request(path: Path, heartbeat: dict, child_pid: int) -> str:
    """Write the same generation-bound stop contract used by the App."""
    request_id = uuid.uuid4().hex
    payload = {
        "protocol_version": 1,
        "request_id": request_id,
        "supervisor_id": str(heartbeat.get("supervisor_id", "")),
        "generation": str(heartbeat.get("generation", "")),
        "pid": int(child_pid),
        "process_start_utc": str(heartbeat.get("process_start_utc", "")),
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "reason": "packaged_selftest",
    }
    temporary = path.with_name(f"{path.name}.{os.getpid()}.{request_id}.tmp")
    try:
        with temporary.open("w", encoding="ascii") as handle:
            json.dump(payload, handle, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except OSError:
            pass
    return request_id


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=25.0)
    args = parser.parse_args()

    package = args.package_dir.resolve()
    data = args.data_dir.resolve()
    supervisor_path = package / "FocusCheckSupervisor.exe"
    if not supervisor_path.is_file() or not (package / "FocusCheck.exe").is_file():
        raise FileNotFoundError("package must contain FocusCheck.exe and FocusCheckSupervisor.exe")
    data.mkdir(parents=True, exist_ok=True)
    heartbeat = data / "hb.txt"
    stop_file = data / "supervisor.stop"
    stop_ack_file = data / "supervisor.stop.ack"
    log_file = data / "frozen-supervisor.log"
    for path in (heartbeat, stop_file, stop_ack_file):
        try:
            path.unlink()
        except FileNotFoundError:
            pass

    env = os.environ.copy()
    env.update({
        "FOCUS_DATA_DIR": str(data),
        "FOCUSCHECK_SUPERVISOR_LOCK_FILE": str(data / "supervisor.lock"),
        "FOCUSCHECK_SUPERVISOR_STOP_FILE": str(stop_file),
        "FOCUSCHECK_SUPERVISOR_STOP_ACK_FILE": str(stop_ack_file),
    })
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    process = subprocess.Popen(
        [str(supervisor_path), "--run", "--base-dir", str(package), "--check-interval", "1", "--resume-gap", "10", "--restart-delay", "1", "--log-file", str(log_file)],
        cwd=str(package),
        env=env,
        creationflags=creationflags,
    )
    child_pid = None
    try:
        deadline = time.monotonic() + max(1.0, args.timeout)
        payload = None
        while time.monotonic() < deadline:
            if heartbeat.exists():
                try:
                    candidate = json.loads(heartbeat.read_text(encoding="utf-8"))
                    if candidate.get("protocol_version") == 1 and candidate.get("readiness") == "ready":
                        payload = candidate
                        break
                except (OSError, ValueError, TypeError):
                    pass
            if process.poll() is not None:
                break
            time.sleep(0.25)
        if payload is None:
            detail = log_file.read_text(encoding="utf-8", errors="replace")[-2000:] if log_file.exists() else ""
            raise RuntimeError(f"packaged supervisor did not reach ready heartbeat: {detail}")
        child_pid = int(payload["pid"])
        if child_pid <= 0:
            raise RuntimeError("packaged supervisor reported an invalid child PID")
        # Request an intentional stop. The supervisor must validate the
        # request, terminate its owned child, and publish its durable ack.
        request_id = _write_stop_request(stop_file, payload, child_pid)
        process.wait(timeout=15)
        if process.returncode != 0:
            raise RuntimeError(f"packaged supervisor exited with {process.returncode}")
        if not stop_ack_file.exists():
            raise RuntimeError("packaged supervisor exited without a stop acknowledgement")
        acknowledgement = json.loads(stop_ack_file.read_text(encoding="utf-8"))
        if acknowledgement.get("status") != "acknowledged" or acknowledgement.get("request_id") != request_id:
            raise RuntimeError(f"invalid stop acknowledgement: {acknowledgement}")
        print(f"packaged_supervisor_ready pid={process.pid} child_pid={child_pid} acknowledged={request_id}")
        return 0
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"packaged_supervisor_selftest_failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)

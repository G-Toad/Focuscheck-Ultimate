"""Bounded self-test for a frozen supervisor and its packaged child."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def _terminate_process_tree(pid: int) -> None:
    """Stop only the supervisor process launched by this test."""
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
    log_file = data / "frozen-supervisor.log"
    for path in (heartbeat, stop_file):
        try:
            path.unlink()
        except FileNotFoundError:
            pass

    env = os.environ.copy()
    env.update({
        "FOCUS_DATA_DIR": str(data),
        "FOCUSCHECK_SUPERVISOR_LOCK_FILE": str(data / "supervisor.lock"),
        "FOCUSCHECK_SUPERVISOR_STOP_FILE": str(stop_file),
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
        # The packaged app has no deterministic UI exit action in a headless
        # test. Kill only this test's supervisor tree after readiness and
        # verify that the supervisor process is reaped within the bound.
        _terminate_process_tree(process.pid)
        process.wait(timeout=15)
        expected_forced_exit = os.name == "nt" and process.returncode == 1
        if process.returncode != 0 and not expected_forced_exit:
            raise RuntimeError(f"packaged supervisor exited with {process.returncode}")
        print(f"packaged_supervisor_ready pid={process.pid} child_pid={child_pid} exit={process.returncode}")
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

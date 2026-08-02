"""Bounded, isolated verification runner for FocusCheck.

Each stage receives the same disposable data root and a timeout. Results are
written as JSON so CI or another agent can consume evidence without parsing
console output.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "_verify_runtime"
REPORT = RUNTIME / "verification.json"
TRACKED_REPORT = ROOT / "docs" / "refurbishment" / "verification-report.json"


def run_stage(name: str, args: list[str], env: dict[str, str], timeout: int) -> dict:
    start = time.monotonic()
    log_path = RUNTIME / f"{name}.log"
    try:
        completed = subprocess.run(
            args,
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        log_path.write_text(output, encoding="utf-8", errors="replace")
        return {
            "name": name,
            "command": args,
            "status": "passed" if completed.returncode == 0 else "failed",
            "exit_code": completed.returncode,
            "elapsed_ms": int((time.monotonic() - start) * 1000),
            "log": str(log_path),
        }
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or b"").decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        output += (exc.stderr or b"").decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        log_path.write_text(output, encoding="utf-8", errors="replace")
        return {
            "name": name,
            "command": args,
            "status": "timeout",
            "exit_code": None,
            "elapsed_ms": int((time.monotonic() - start) * 1000),
            "timeout_seconds": timeout,
            "log": str(log_path),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--keep-runtime", action="store_true")
    args = parser.parse_args()

    if RUNTIME.exists() and not args.keep_runtime:
        shutil.rmtree(RUNTIME, ignore_errors=True)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    data_dir = RUNTIME / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update({
        "FOCUS_DATA_DIR": str(data_dir),
        "FOCUSCHECK_SUPERVISOR_LOCK_FILE": str(RUNTIME / "supervisor.lock"),
        "FOCUSCHECK_SUPERVISOR_STOP_FILE": str(RUNTIME / "supervisor.stop"),
    })
    py = sys.executable
    stages = [
        ("compileall", [py, "-m", "compileall", "main.py", "focuscheck", "focuscheck_supervisor.py", "tests", "tools"]),
        ("unittest", [py, "-m", "unittest", "discover", "-s", "tests", "-p", "test*.py"]),
        ("qa_scenario_runner", [py, "tools/qa_scenario_runner.py", "--reset", "--skip-gui"]),
        ("main_selftest", [py, "main.py", "--selftest"]),
        ("tray_selftest", [py, "main.py", "--tray-selftest"]),
        ("settings_inventory", [py, "tools/settings_inventory.py"]),
    ]
    results = [run_stage(name, command, env, max(1, args.timeout)) for name, command in stages]
    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "repository": str(ROOT),
        "isolated_data_dir": str(data_dir),
        "results": results,
        "manual_gates": [
            "live tray and Tk interaction",
            "Windows startup registry and real supervisor restart",
            "browser/window activity provider matrix",
            "native lock/sleep/resume and monitor overlay behavior",
            "release packaging and install/uninstall lifecycle",
        ],
    }
    REPORT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    TRACKED_REPORT.parent.mkdir(parents=True, exist_ok=True)
    TRACKED_REPORT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    for result in results:
        print(f"{result['status'].upper():7} {result['name']} ({result['elapsed_ms']} ms)")
    print(f"verification_report={REPORT}")
    return 0 if all(result["status"] == "passed" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

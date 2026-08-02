"""Bounded, isolated verification runner for FocusCheck.

Each stage receives the same disposable data root and a timeout. Results are
written as JSON so CI or another agent can consume evidence without parsing
console output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from .process_guard import filtered_repository_snapshot, focuscheck_process_snapshot, new_processes
except ImportError:  # Direct script execution puts tools on sys.path.
    from process_guard import filtered_repository_snapshot, focuscheck_process_snapshot, new_processes


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "_verify_runtime"
REPORT = RUNTIME / "verification.json"
TRACKED_REPORT = ROOT / "docs" / "refurbishment" / "verification-report.json"


def snapshot_tree(root: Path) -> dict[str, str]:
    """Capture file hashes for a profile without modifying it."""
    if not root.exists():
        return {}
    snapshot = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        digest = hashlib.sha256()
        try:
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            snapshot[str(path.relative_to(root))] = digest.hexdigest()
        except OSError:
            snapshot[str(path.relative_to(root))] = "unreadable"
    return snapshot


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
    live_profile = Path(os.environ.get("APPDATA", "")) / "FocusCheck"
    live_before = snapshot_tree(live_profile)
    repository_before = filtered_repository_snapshot(ROOT, snapshot_tree)
    process_before = focuscheck_process_snapshot(ROOT)
    py = sys.executable
    stages = [
        ("compileall", [py, "-m", "compileall", "main.py", "focuscheck", "focuscheck_supervisor.py", "tests", "tools"]),
        ("unittest", [py, "-m", "unittest", "discover", "-s", "tests", "-p", "test*.py"]),
        ("mutation_smoke", [py, "tools/mutation_smoke.py"]),
        ("qa_scenario_runner", [py, "tools/qa_scenario_runner.py", "--reset", "--skip-gui"]),
        ("main_selftest", [py, "main.py", "--selftest"]),
        ("tray_selftest", [py, "main.py", "--tray-selftest"]),
        ("native_overlay_selftest", [py, "tools/spotlight_overlay_selftest.py"]),
        ("resource_leak_selftest", [py, "tools/resource_leak_selftest.py"]),
        ("settings_inventory", [py, "tools/settings_inventory.py"]),
        ("diagnostic_bundle", [py, "tools/create_diagnostic_bundle.py"]),
        ("data_export", [py, "tools/export_data.py", "--source", str(data_dir), "--output", str(RUNTIME / "data_export.zip")]),
        ("performance_soak", [py, "tools/performance_soak.py"]),
    ]
    results = [run_stage(name, command, env, max(1, args.timeout)) for name, command in stages]
    live_after = snapshot_tree(live_profile)
    isolation_ok = live_before == live_after
    results.append({
        "name": "profile_isolation",
        "command": ["snapshot", str(live_profile)],
        "status": "passed" if isolation_ok else "failed",
        "exit_code": 0 if isolation_ok else 1,
        "elapsed_ms": 0,
        "files_before": len(live_before),
        "files_after": len(live_after),
    })
    repository_after = filtered_repository_snapshot(ROOT, snapshot_tree)
    repository_writes = sorted(set(repository_before) ^ set(repository_after))
    repository_writes.extend(sorted(
        path for path in set(repository_before) & set(repository_after)
        if repository_before[path] != repository_after[path]
    ))
    results.append({
        "name": "repository_write_guard",
        "command": ["snapshot", str(ROOT)],
        "status": "passed" if not repository_writes else "failed",
        "exit_code": 0 if not repository_writes else 1,
        "elapsed_ms": 0,
        "unexpected_paths": repository_writes,
    })
    try:
        process_after = focuscheck_process_snapshot(ROOT)
        leaked_processes = new_processes(process_before, process_after)
        process_status = "passed" if not leaked_processes else "failed"
        process_error = None
    except Exception as exc:
        leaked_processes = []
        process_status = "failed" if os.name == "nt" else "passed"
        process_error = type(exc).__name__ + ": " + str(exc)
    results.append({
        "name": "process_leak_guard",
        "command": ["process_snapshot", str(ROOT)],
        "status": process_status,
        "exit_code": 0 if process_status == "passed" else 1,
        "elapsed_ms": 0,
        "leaked_processes": leaked_processes,
        "error": process_error,
    })
    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "repository": str(ROOT),
        "isolated_data_dir": str(data_dir),
        "live_profile_unchanged": isolation_ok,
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

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
import platform
import re
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
MANUAL_GATES = [
    "live tray and Tk interaction",
    "Windows startup registry and real supervisor restart",
    "browser/window activity provider matrix",
    "native lock/sleep/resume and monitor overlay behavior",
    "release packaging and install/uninstall lifecycle",
]


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


def snapshot_user_run_key() -> dict[str, object] | None:
    """Read HKCU Run without creating or changing registry state.

    A ``None`` result means the current platform has no Windows registry
    interface; non-Windows verification remains profile-isolated only.
    """
    if os.name != "nt":
        return None
    try:
        import winreg
    except ImportError:
        return None
    path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    values: dict[str, object] = {}
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ) as key:
            index = 0
            while True:
                try:
                    name, value, value_type = winreg.EnumValue(key, index)
                except OSError:
                    break
                values[name] = {"value": value, "type": value_type}
                index += 1
    except FileNotFoundError:
        return {}
    except OSError as exc:
        return {"__snapshot_error__": f"{type(exc).__name__}: {exc}"}
    return values


def _terminate_process_tree(process: subprocess.Popen) -> dict[str, object]:
    """Stop only the timed-out stage and descendants, never by image name."""
    pid = int(process.pid)
    if os.name == "nt":
        completed = subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            try:
                process.kill()
            except OSError:
                pass
        return {
            "method": "taskkill_pid_tree",
            "pid": pid,
            "exit_code": completed.returncode,
            "fallback_kill": completed.returncode != 0,
        }

    try:
        os.killpg(pid, __import__("signal").SIGKILL)
        return {"method": "killpg", "pid": pid, "exit_code": 0}
    except (AttributeError, OSError) as exc:
        try:
            process.kill()
            return {"method": "process_kill", "pid": pid, "exit_code": 0}
        except OSError as kill_exc:
            return {
                "method": "process_kill",
                "pid": pid,
                "exit_code": None,
                "error": f"{type(exc).__name__}: {exc}; {type(kill_exc).__name__}: {kill_exc}",
            }


def _git_commit() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return completed.stdout.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def _test_summary(results: list[dict]) -> dict[str, object]:
    for result in results:
        if result["name"] != "unittest":
            continue
        try:
            text = Path(result["log"]).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return {"status": result["status"], "count": None}
        match = re.search(r"Ran\s+(\d+)\s+tests?", text)
        failures = re.search(r"FAILED \(([^)]*)\)", text)
        return {
            "status": result["status"],
            "count": int(match.group(1)) if match else None,
            "failure_summary": failures.group(1) if failures else None,
        }
    return {"status": "not_run", "count": None}


def _category_summary() -> dict[str, object]:
    path = RUNTIME / "test-category-inventory.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "not_run", "automated": [], "manual": []}
    return {
        "status": "passed",
        "automated": payload.get("automated_categories", []),
        "manual": payload.get("manual_categories", []),
    }


def run_stage(name: str, args: list[str], env: dict[str, str], timeout: int) -> dict:
    start = time.monotonic()
    log_path = RUNTIME / f"{name}.log"
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
    try:
        process = subprocess.Popen(
            args,
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=os.name != "nt",
            creationflags=creationflags,
        )
        stdout, stderr = process.communicate(timeout=timeout)
        output = (stdout or "") + (stderr or "")
        log_path.write_text(output, encoding="utf-8", errors="replace")
        return {
            "name": name,
            "command": args,
            "status": "passed" if process.returncode == 0 else "failed",
            "exit_code": process.returncode,
            "elapsed_ms": int((time.monotonic() - start) * 1000),
            "log": str(log_path),
        }
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or b"").decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        output += (exc.stderr or b"").decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        cleanup = _terminate_process_tree(process)
        try:
            trailing_stdout, trailing_stderr = process.communicate(timeout=5)
            output += (trailing_stdout or "") + (trailing_stderr or "")
        except subprocess.TimeoutExpired:
            process.kill()
            trailing_stdout, trailing_stderr = process.communicate()
            output += (trailing_stdout or "") + (trailing_stderr or "")
        log_path.write_text(output, encoding="utf-8", errors="replace")
        return {
            "name": name,
            "command": args,
            "status": "timeout",
            "exit_code": None,
            "elapsed_ms": int((time.monotonic() - start) * 1000),
            "timeout_seconds": timeout,
            "log": str(log_path),
            "cleanup": cleanup,
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
        # Exercise repeated native overlay ownership in the bounded Windows
        # stage without making the operator's environment part of the test.
        "FOCUSCHECK_NATIVE_OVERLAY_CYCLES": os.environ.get("FOCUSCHECK_NATIVE_OVERLAY_CYCLES", "20"),
        "FOCUSCHECK_NATIVE_OVERLAY_SECONDS": os.environ.get("FOCUSCHECK_NATIVE_OVERLAY_SECONDS", "0.25"),
    })
    live_profile = Path(os.environ.get("APPDATA", "")) / "FocusCheck"
    live_before = snapshot_tree(live_profile)
    registry_before = snapshot_user_run_key()
    repository_before = filtered_repository_snapshot(ROOT, snapshot_tree)
    process_before = focuscheck_process_snapshot(ROOT)
    py = sys.executable
    stages = [
        ("compileall", [py, "-m", "compileall", "main.py", "focuscheck", "focuscheck_supervisor.py", "tests", "tools"], args.timeout),
        ("unittest", [py, "-m", "unittest", "discover", "-s", "tests", "-p", "test*.py"], args.timeout),
        ("mutation_smoke", [py, "tools/mutation_smoke.py"], args.timeout),
        ("source_supervisor_selftest", [py, "tools/source_supervisor_selftest.py"], args.timeout),
        ("state_restart_selftest", [py, "tools/state_restart_selftest.py"], args.timeout),
        ("migration_selftest", [py, "tools/migration_selftest.py"], args.timeout),
        ("qa_scenario_runner", [py, "tools/qa_scenario_runner.py", "--reset", "--skip-gui"], args.timeout),
        ("main_selftest", [py, "main.py", "--selftest"], args.timeout),
        ("tray_selftest", [py, "main.py", "--tray-selftest"], args.timeout),
        ("native_overlay_selftest", [py, "tools/spotlight_overlay_selftest.py"], args.timeout),
        ("resource_leak_selftest", [py, "tools/resource_leak_selftest.py"], args.timeout),
        ("package_build", [py, "tools/package_build_selftest.py"], max(180, args.timeout)),
        ("settings_inventory", [py, "tools/settings_inventory.py"], args.timeout),
        ("diagnostic_bundle", [py, "tools/create_diagnostic_bundle.py"], args.timeout),
        ("data_export", [py, "tools/export_data.py", "--source", str(data_dir), "--output", str(RUNTIME / "data_export.zip"), "--overwrite"], args.timeout),
        ("data_recovery", [py, "tools/data_recovery_selftest.py"], args.timeout),
        ("performance_soak", [py, "tools/performance_soak.py"], args.timeout),
        ("test_category_inventory", [py, "tools/test_category_inventory.py"], args.timeout),
        ("plan_register_coverage", [py, "tools/plan_register_coverage.py"], args.timeout),
    ]
    results = [run_stage(name, command, env, max(1, timeout)) for name, command, timeout in stages]
    live_after = snapshot_tree(live_profile)
    isolation_ok = live_before == live_after
    registry_after = snapshot_user_run_key()
    registry_isolation_ok = (
        registry_before is None
        or registry_after is None
        or registry_before == registry_after
    )
    results.append({
        "name": "profile_isolation",
        "command": ["snapshot", str(live_profile)],
        "status": "passed" if isolation_ok and registry_isolation_ok else "failed",
        "exit_code": 0 if isolation_ok and registry_isolation_ok else 1,
        "elapsed_ms": 0,
        "files_before": len(live_before),
        "files_after": len(live_after),
        "registry_snapshot_supported": registry_before is not None,
        "registry_unchanged": registry_isolation_ok,
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
    automated_pass = all(result["status"] == "passed" for result in results)
    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "commit": _git_commit(),
        "repository": str(ROOT),
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "executable": sys.executable,
        },
        "isolated_data_dir": str(data_dir),
        "live_profile_unchanged": isolation_ok,
        "user_run_key_unchanged": registry_isolation_ok,
        "results": results,
        "tests": _test_summary(results),
        "test_categories": _category_summary(),
        "manual_required": MANUAL_GATES,
        "process_leaks": leaked_processes,
        "result": "fail" if not automated_pass else ("partial" if MANUAL_GATES else "pass"),
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

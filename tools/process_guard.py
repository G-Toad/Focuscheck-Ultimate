"""Small, non-destructive process and repository-write guards for verification."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def _query_windows_processes() -> list[dict]:
    command = (
        "$items = @(Get-CimInstance Win32_Process | "
        "Select-Object ProcessId,ParentProcessId,Name,CommandLine); "
        "$items | ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    payload = json.loads(completed.stdout or "[]")
    return payload if isinstance(payload, list) else [payload]


def focuscheck_process_snapshot(root: Path) -> dict[int, dict]:
    """Return currently running processes attributable to this checkout.

    The guard is deliberately narrow: it looks for the checkout path or the
    two FocusCheck entry-point names in command lines, rather than treating all
    Python processes owned by the user as leaks.
    """
    if os.name != "nt":
        return {}
    records = _query_windows_processes()
    root_text = str(root.resolve()).replace("/", "\\").lower().rstrip("\\")
    owned = {}
    for record in records:
        try:
            pid = int(record.get("ProcessId"))
        except (TypeError, ValueError):
            continue
        command_line = str(record.get("CommandLine") or "")
        normalized = command_line.replace("/", "\\").lower()
        if root_text in normalized or " main.py" in normalized or " focuscheck_supervisor.py" in normalized:
            owned[pid] = {
                "pid": pid,
                "parent_pid": record.get("ParentProcessId"),
                "name": record.get("Name"),
                "command_line": command_line,
            }
    return owned


def new_processes(before: dict[int, dict], after: dict[int, dict]) -> list[dict]:
    """Return surviving owned processes whose PID was absent from baseline."""
    return [after[pid] for pid in sorted(set(after) - set(before))]


def filtered_repository_snapshot(root: Path, snapshot_tree) -> dict[str, str]:
    """Hash repository files while excluding verifier-owned/generated paths."""
    ignored = (
        "_verify_runtime/",
        "_qa_runtime/",
        ".git/",
        "__pycache__",
        ".pytest_cache/",
        "docs/refurbishment/verification-report.json",
    )
    snapshot = snapshot_tree(root)
    return {
        relative: digest
        for relative, digest in snapshot.items()
        if not any(
            prefix in relative.replace("\\", "/").split("/")
            or relative.replace("\\", "/").startswith(prefix)
            for prefix in ignored
        )
    }

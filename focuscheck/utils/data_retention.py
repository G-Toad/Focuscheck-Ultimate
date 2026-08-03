"""Privacy-safe retention planning and application for known log artifacts."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path


RETENTION_PATTERNS = (
    "focus_log.csv*",
    "focus_waste_log.csv*",
    "focus_study_log.csv*",
    "focus_intervention_reflections.jsonl*",
    "focus_app.log*",
    "focuscheck_supervisor.log*",
)
RETENTION_AUDIT_FORMAT_VERSION = 1


def _retention_root(root: Path) -> Path:
    supplied = Path(root)
    if supplied.is_symlink():
        raise ValueError("refusing symlink retention root")
    return supplied.resolve()


def retention_plan(root: Path, *, max_age_days: int, now: float | None = None) -> list[dict]:
    """Return old, non-symlink log candidates without changing the root."""
    root = _retention_root(root)
    if not root.is_dir():
        return []
    cutoff = (now if now is not None else time.time()) - max(1, int(max_age_days)) * 86400
    seen: set[Path] = set()
    candidates = []
    for pattern in RETENTION_PATTERNS:
        for path in root.glob(pattern):
            if path in seen or path.is_symlink() or not path.is_file():
                continue
            seen.add(path)
            stat = path.stat()
            if stat.st_mtime < cutoff:
                candidates.append({
                    "path": str(path),
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                    "mtime_ns": stat.st_mtime_ns,
                })
    return sorted(candidates, key=lambda item: item["path"])


def apply_retention(
    root: Path,
    *,
    max_age_days: int,
    apply: bool = False,
    now: float | None = None,
) -> list[dict]:
    """Plan or apply retention; applied deletions record metadata only."""
    root = _retention_root(root)
    candidates = retention_plan(root, max_age_days=max_age_days, now=now)
    if apply:
        audit_path = root / "retention_audit.jsonl"
        for item in candidates:
            candidate = Path(item["path"])
            deleted = False
            error = None
            try:
                current = candidate.stat()
                if candidate.is_symlink():
                    raise OSError("symlink candidate rejected")
                if current.st_size != int(item["size"]) or current.st_mtime_ns != int(item["mtime_ns"]):
                    raise OSError("candidate changed since retention plan")
                candidate.unlink()
                deleted = True
            except OSError as exc:
                error = "changed_since_plan" if "changed since" in str(exc) else type(exc).__name__
            item["deleted"] = deleted
            if error:
                item["error"] = error
            item["audit_written"] = False
            try:
                audit = {
                    "format_version": RETENTION_AUDIT_FORMAT_VERSION,
                    "utc": datetime.now(timezone.utc).isoformat(),
                    "operation": "retention_delete",
                    "path_name": candidate.name,
                    "size": int(item["size"]),
                    "deleted": deleted,
                    "error": error,
                }
                with audit_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(audit, separators=(",", ":")) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                item["audit_written"] = True
            except OSError as exc:
                item["audit_error"] = type(exc).__name__
    return candidates


__all__ = [
    "RETENTION_AUDIT_FORMAT_VERSION",
    "RETENTION_PATTERNS",
    "apply_retention",
    "retention_plan",
]

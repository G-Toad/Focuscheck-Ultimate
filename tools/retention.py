"""Plan and optionally apply retention to known FocusCheck artifacts."""

from __future__ import annotations

import argparse
import json
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


def retention_plan(root: Path, *, max_age_days: int, now: float | None = None) -> list[dict]:
    root = root.resolve()
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
                candidates.append({"path": str(path), "size": stat.st_size, "mtime": stat.st_mtime})
    return sorted(candidates, key=lambda item: item["path"])


def apply_retention(
    root: Path,
    *,
    max_age_days: int,
    apply: bool = False,
    now: float | None = None,
) -> list[dict]:
    root = root.resolve()
    candidates = retention_plan(root, max_age_days=max_age_days, now=now)
    if apply:
        audit_path = root / "retention_audit.jsonl"
        for item in candidates:
            try:
                Path(item["path"]).unlink()
                item["deleted"] = True
            except OSError as exc:
                item["deleted"] = False
                item["error"] = type(exc).__name__
            try:
                audit = {
                    "utc": datetime.now(timezone.utc).isoformat(),
                    "operation": "retention_delete",
                    "path_name": Path(item["path"]).name,
                    "size": int(item["size"]),
                    "deleted": bool(item.get("deleted", False)),
                    "error": item.get("error"),
                }
                with audit_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(audit, separators=(",", ":")) + "\n")
            except OSError:
                pass
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--max-age-days", type=int, default=90)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(apply_retention(args.root, max_age_days=args.max_age_days, apply=args.apply), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

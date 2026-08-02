"""Export selected FocusCheck data files into a manifest-backed ZIP archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path


CATEGORIES = ("logs", "metadata", "settings", "tasks", "camera")
_CATEGORY_PATTERNS = {
    "logs": ("focus_log.csv", "focus_log.csv.*", "focus_waste_log.csv", "focus_waste_log.csv.*",
             "focus_study_log.csv", "focus_study_log.csv.*", "focus_intervention_reflections.jsonl",
             "focus_intervention_reflections.jsonl.*"),
    "metadata": ("structured_events.jsonl", "structured_events.jsonl.*", "runtime_state.jsonl",
                 "runtime_state.jsonl.*", "data_migration.jsonl"),
    "settings": ("focus_settings.json", "focus_settings.json.bak", "focus_settings.json.bak.*"),
    "tasks": ("focus_tasks.sqlite3", "focus_tasks.sqlite3.*"),
    "camera": ("camera_*.png", "camera_*.jpg", "camera_*.jpeg"),
}
_SENSITIVE_CATEGORIES = {"settings", "tasks", "camera"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _files_for_categories(root: Path, categories: set[str]) -> list[tuple[Path, str]]:
    files: dict[str, tuple[Path, str]] = {}
    for category in sorted(categories):
        for pattern in _CATEGORY_PATTERNS[category]:
            for path in root.glob(pattern):
                if not path.is_file():
                    continue
                if path.is_symlink():
                    raise ValueError(f"refusing symlink export source: {path.name}")
                relative = path.relative_to(root).as_posix()
                files[relative] = (path, category)
    return [files[name] for name in sorted(files)]


def export_data(source_root, destination, *, categories=("logs", "metadata"), overwrite=False) -> dict:
    """Create an atomic ZIP export; sensitive categories are never implicit."""
    root = Path(source_root).resolve()
    output = Path(destination).resolve()
    selected = {str(category).strip().lower() for category in categories}
    unknown = selected - set(CATEGORIES)
    if unknown:
        raise ValueError(f"unknown export categories: {', '.join(sorted(unknown))}")
    if not root.is_dir():
        raise NotADirectoryError(root)
    if output.exists() and not overwrite:
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    sources = _files_for_categories(root, selected)
    manifest = {
        "format_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "categories": sorted(selected),
        "files": [],
    }
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{output.name}.", suffix=".tmp", dir=output.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path, category in sources:
                relative = path.relative_to(root).as_posix()
                manifest["files"].append({
                    "path": relative,
                    "category": category,
                    "size": path.stat().st_size,
                    "sha256": _sha256(path),
                    "sensitive": category in _SENSITIVE_CATEGORIES,
                })
                archive.write(path, arcname=relative)
            archive.writestr("EXPORT_MANIFEST.json", json.dumps(manifest, indent=2, sort_keys=True))
        os.replace(temporary, output)
        return manifest
    finally:
        if temporary is not None and temporary.exists():
            try:
                temporary.unlink()
            except OSError:
                pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--include", nargs="+", choices=CATEGORIES, default=("logs", "metadata"))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    manifest = export_data(args.source, args.output, categories=args.include, overwrite=args.overwrite)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Allowlisted, privacy-aware user data export service."""

from __future__ import annotations

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
             "focus_intervention_reflections.jsonl.*", "focus_app.log", "focus_app.log.*",
             "focuscheck_supervisor.log", "focuscheck_supervisor.log.*"),
    "metadata": ("structured_events.jsonl", "structured_events.jsonl.*", "runtime_state.jsonl",
                 "runtime_state.jsonl.*", "data_migration.jsonl", "retention_audit.jsonl",
                 "data_clear_audit.jsonl", "hb.txt", "supervisor.stop", "supervisor.stop.ack",
                 "diagnostic_bundle.zip", "diagnostic_bundle.zip.*"),
    "settings": ("focus_settings.json", "focus_settings.json.bak", "focus_settings.json.bak.*",
                 "focus_settings.json.corrupt-*", "focus_settings.json.migration.jsonl"),
    "tasks": ("focus_tasks.sqlite3", "focus_tasks.sqlite3.*"),
    "camera": ("camera_*.png", "camera_*.jpg", "camera_*.jpeg"),
}
_SENSITIVE_CATEGORIES = {"settings", "tasks", "camera"}
EXPORT_FORMAT_VERSION = 1
DATA_CLEAR_AUDIT_FORMAT_VERSION = 1


def _data_root(source_root) -> Path:
    """Keep data operations scoped to the explicitly supplied directory."""
    supplied = Path(source_root)
    if supplied.is_symlink():
        raise ValueError("refusing symlink data root")
    return supplied.resolve()


def _selected_categories(categories) -> set[str]:
    selected = {str(category).strip().lower() for category in categories}
    unknown = selected - set(CATEGORIES)
    if unknown:
        raise ValueError(f"unknown export categories: {', '.join(sorted(unknown))}")
    return selected


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
                files[path.relative_to(root).as_posix()] = (path, category)
    return [files[name] for name in sorted(files)]


def export_data(source_root, destination, *, categories=("logs", "metadata"), overwrite=False) -> dict:
    """Create an atomic ZIP export; sensitive categories are never implicit."""
    root = _data_root(source_root)
    output = Path(destination).resolve()
    selected = _selected_categories(categories)
    if not root.is_dir():
        raise NotADirectoryError(root)
    if output.exists() and not overwrite:
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    manifest = {
        "format_version": EXPORT_FORMAT_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "categories": sorted(selected),
        "files": [],
    }
    temporary = None
    try:
        sources = _files_for_categories(root, selected)
        if output.is_symlink() or any(path.resolve() == output for path, _category in sources):
            raise ValueError("export destination collides with an input or is a symlink")
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
        # Hashing and ZIP writing are separate filesystem reads. Validate the
        # completed temporary archive so a concurrent source mutation cannot
        # produce a promoted export whose manifest lies about its contents.
        validate_export(temporary)
        os.replace(temporary, output)
        return manifest
    finally:
        if temporary is not None and temporary.exists():
            try:
                temporary.unlink()
            except OSError:
                pass


def validate_export(archive_path) -> dict:
    """Validate an export archive and return its trusted embedded manifest."""
    archive_path = Path(archive_path).resolve()
    if not archive_path.is_file():
        raise FileNotFoundError(archive_path)
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            names = archive.namelist()
            if names.count("EXPORT_MANIFEST.json") != 1 or len(names) != len(set(names)):
                raise ValueError("export archive has duplicate or missing manifest entries")
            try:
                manifest = json.loads(archive.read("EXPORT_MANIFEST.json"))
            except (KeyError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
                raise ValueError("export manifest is invalid") from exc
            if (
                not isinstance(manifest, dict)
                or type(manifest.get("format_version")) is not int
                or manifest.get("format_version") != EXPORT_FORMAT_VERSION
            ):
                raise ValueError("unsupported export manifest version")
            categories = manifest.get("categories")
            files = manifest.get("files")
            if not isinstance(categories, list) or not all(
                isinstance(item, str) and item in CATEGORIES for item in categories
            ):
                raise ValueError("export manifest categories are invalid")
            if len(categories) != len(set(categories)):
                raise ValueError("export manifest categories are duplicated")
            if not isinstance(files, list):
                raise ValueError("export manifest files are invalid")

            expected = {"EXPORT_MANIFEST.json"}
            listed = set()
            for entry in files:
                if not isinstance(entry, dict):
                    raise ValueError("export manifest file entry is invalid")
                relative = entry.get("path")
                category = entry.get("category")
                size = entry.get("size")
                digest_value = entry.get("sha256")
                sensitive = entry.get("sensitive")
                if not isinstance(relative, str) or not relative or "\\" in relative:
                    raise ValueError("export manifest path is invalid")
                if not isinstance(category, str) or category not in categories:
                    raise ValueError("export manifest entry is duplicated or uncategorized")
                if type(size) is not int or size < 0:
                    raise ValueError(f"export member size is invalid: {relative}")
                if not isinstance(digest_value, str) or len(digest_value) != 64 or any(
                    character not in "0123456789abcdefABCDEF" for character in digest_value
                ):
                    raise ValueError(f"export member hash is invalid: {relative}")
                if type(sensitive) is not bool:
                    raise ValueError("export manifest sensitivity label is invalid")
                path = Path(relative)
                if path.is_absolute() or ".." in path.parts or relative == "EXPORT_MANIFEST.json":
                    raise ValueError("export manifest path escapes archive root")
                if relative in listed:
                    raise ValueError("export manifest entry is duplicated or uncategorized")
                if sensitive != (category in _SENSITIVE_CATEGORIES):
                    raise ValueError("export manifest sensitivity label is invalid")
                listed.add(relative)
                expected.add(relative)
                try:
                    info = archive.getinfo(relative)
                except KeyError as exc:
                    raise ValueError(f"export member is missing: {relative}") from exc
                if info.is_dir() or size != info.file_size:
                    raise ValueError(f"export member size is invalid: {relative}")
                digest = hashlib.sha256()
                with archive.open(info, "r") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
                if digest.hexdigest() != digest_value:
                    raise ValueError(f"export member hash is invalid: {relative}")
            if set(names) != expected:
                raise ValueError("export archive contains unexpected members")
            return manifest
    except zipfile.BadZipFile as exc:
        raise ValueError("export archive is not a valid ZIP") from exc


def inventory_data(source_root, *, categories=CATEGORIES) -> dict:
    """Return a metadata-only inventory suitable for a user preview."""
    root = _data_root(source_root)
    selected = _selected_categories(categories)
    if not root.is_dir():
        raise NotADirectoryError(root)
    files = []
    for path, category in _files_for_categories(root, selected):
        stat = path.stat()
        files.append({
            "path": path.relative_to(root).as_posix(),
            "category": category,
            "size": stat.st_size,
            "sensitive": category in _SENSITIVE_CATEGORIES,
        })
    return {"root": str(root), "categories": sorted(selected), "files": files}


def clear_data(source_root, *, categories, confirmed=False) -> dict:
    """Delete only allowlisted files after an explicit confirmation."""
    if not confirmed:
        raise PermissionError("clear_data requires explicit confirmation")
    root = _data_root(source_root)
    selected = _selected_categories(categories)
    if not root.is_dir():
        raise NotADirectoryError(root)
    records = []
    for path, category in _files_for_categories(root, selected):
        relative = path.relative_to(root).as_posix()
        try:
            initial_stat = path.stat()
        except OSError as exc:
            records.append({
                "path": relative,
                "category": category,
                "size": None,
                "sensitive": category in _SENSITIVE_CATEGORIES,
                "deleted": False,
                "error": type(exc).__name__,
            })
            continue
        record = {
            "path": relative,
            "category": category,
            "size": initial_stat.st_size,
            "sensitive": category in _SENSITIVE_CATEGORIES,
        }
        deleted = False
        error = None
        try:
            if path.is_symlink():
                raise OSError("symlink candidate rejected")
            current_stat = path.stat()
            if current_stat.st_size != initial_stat.st_size or current_stat.st_mtime_ns != initial_stat.st_mtime_ns:
                raise OSError("candidate changed during clear")
            path.unlink()
            deleted = True
        except OSError as exc:
            error = "changed_during_clear" if "changed during" in str(exc) else type(exc).__name__
        record["deleted"] = deleted
        if error:
            record["error"] = error
        records.append(record)

    audit = {
        "format_version": DATA_CLEAR_AUDIT_FORMAT_VERSION,
        "utc": datetime.now(timezone.utc).isoformat(),
        "operation": "clear_data",
        "categories": sorted(selected),
        "files": records,
        "audit_written": False,
    }
    audit_path = root / "data_clear_audit.jsonl"
    try:
        persisted_audit = dict(audit)
        persisted_audit["audit_written"] = True
        with audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(persisted_audit, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        audit["audit_written"] = True
    except OSError as exc:
        audit["audit_error"] = type(exc).__name__
    return audit


__all__ = [
    "CATEGORIES",
    "DATA_CLEAR_AUDIT_FORMAT_VERSION",
    "clear_data",
    "export_data",
    "inventory_data",
    "validate_export",
]

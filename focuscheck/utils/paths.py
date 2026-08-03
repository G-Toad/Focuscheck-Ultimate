"""
Path management utilities.

Handles application paths, data directory locations, and resource paths
for both development and PyInstaller-frozen environments.
"""

import os
import sys
import platform
import tempfile
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


def get_base_dir():
    """Get the base directory of the application (focuscheck package root)."""
    try:
        # Return focuscheck package root, not utils folder
        # __file__ is in focuscheck/utils/paths.py, so go up one level
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    except Exception:
        return os.getcwd()


def get_data_dir():
    """
    Get the data directory for storing application files.
    
    Priority:
    1. FOCUS_DATA_DIR environment variable
    2. Windows: %APPDATA%/FocusCheck
    3. Fallback: controlled temporary recovery directory
    """
    from ..config import APP_NAME
    
    # Allow override via env var
    env = os.environ.get("FOCUS_DATA_DIR")
    if env:
        try:
            os.makedirs(env, exist_ok=True)
            return env
        except Exception:
            pass
    
    # Windows: use APPDATA
    if platform.system().lower() == "windows":
        try:
            appdata = os.environ.get("APPDATA")
            if appdata:
                path = os.path.join(appdata, APP_NAME)
                os.makedirs(path, exist_ok=True)
                return path
        except Exception:
            pass
    
    # Never use the package/source directory for mutable user data.
    base = os.path.join(tempfile.gettempdir(), APP_NAME)
    try:
        os.makedirs(base, exist_ok=True)
    except Exception:
        pass
    return base


def resource_path(relative: str):
    """
    Return absolute path to a resource bundled with PyInstaller or next to the script.
    
    When frozen (PyInstaller), resources are in sys._MEIPASS; otherwise relative to this file.
    
    Args:
        relative: Relative path to the resource
        
    Returns:
        Absolute path to the resource
    """
    try:
        base = getattr(sys, "_MEIPASS", None)
        if base:
            return os.path.join(base, relative)
    except Exception:
        pass
    try:
        return os.path.join(get_base_dir(), relative)
    except Exception:
        return relative


def choose_path(filename):
    """
    Return a path in the canonical mutable data directory.

    Legacy package-directory files are migration inputs only. Runtime callers
    must not change their storage root because a stale file happens to exist
    beside the source or frozen executable.

    Args:
        filename: Name of the file

    Returns:
        Full path to the file
    """
    # An explicit root is used by verification, portable deployments, and
    # recovery tooling. It must not be bypassed by a stale file beside code.
    env = os.environ.get("FOCUS_DATA_DIR")
    if env:
        try:
            os.makedirs(env, exist_ok=True)
        except Exception:
            pass
        return os.path.join(env, filename)

    return os.path.join(get_data_dir(), filename)


def legacy_path(filename):
    """Return the historical package-directory location for migration only."""
    return os.path.join(get_base_dir(), filename)


_MIGRATABLE_DATA_FILES = (
    "focus_tasks.sqlite3",
    "focus_log.csv",
    "focus_waste_log.csv",
    "focus_study_log.csv",
    "focus_intervention_reflections.jsonl",
)
MIGRATION_JOURNAL_FORMAT_VERSION = 1
MIGRATION_FATAL_OUTCOMES = frozenset({"failed", "journal_failed"})


def migration_has_fatal_failure(events) -> bool:
    """Return whether migration left durable state incomplete or unjournaled."""
    return any(isinstance(event, dict) and event.get("outcome") in MIGRATION_FATAL_OUTCOMES for event in events)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def migrate_legacy_data(app_paths: "AppPaths | None" = None, *, legacy_root: str | os.PathLike[str] | None = None) -> list[dict]:
    """Import legacy task/log artifacts without deleting or merging silently."""
    if legacy_root is None and os.environ.get("FOCUS_DATA_DIR"):
        return []
    paths = app_paths or get_app_paths()
    source_root = Path(legacy_root) if legacy_root is not None else Path(get_base_dir())
    journal = paths.root / "data_migration.jsonl"
    events: list[dict] = []
    source_root_is_symlink = source_root.is_symlink()

    for name in _MIGRATABLE_DATA_FILES:
        source = source_root / name
        target = paths.root / name
        if source_root_is_symlink or source.is_symlink():
            events.append({"file": name, "outcome": "rejected_symlink"})
            continue
        if source.resolve() == target.resolve() or not source.is_file():
            continue
        try:
            source_hash = _file_sha256(source)
            if target.exists():
                target_hash = _file_sha256(target)
                if target_hash == source_hash:
                    outcome = "duplicate_preserved"
                else:
                    conflict = target.with_name(f"{target.name}.legacy-conflict-{source_hash[:12]}")
                    if not conflict.exists():
                        conflict.write_bytes(source.read_bytes())
                    outcome = "conflict_preserved"
                events.append({"file": name, "outcome": outcome, "sha256": source_hash[:12]})
                continue

            temp = target.with_name(f"{target.name}.{os.getpid()}.legacy.tmp")
            try:
                with source.open("rb") as source_handle, temp.open("wb") as target_handle:
                    for chunk in iter(lambda: source_handle.read(1024 * 1024), b""):
                        target_handle.write(chunk)
                    target_handle.flush()
                    os.fsync(target_handle.fileno())
                os.replace(temp, target)
            finally:
                try:
                    temp.unlink()
                except OSError:
                    pass
            events.append({"file": name, "outcome": "imported", "sha256": source_hash[:12]})
        except (OSError, ValueError) as exc:
            events.append({"file": name, "outcome": "failed", "error_type": type(exc).__name__})

    if events:
        try:
            with journal.open("a", encoding="utf-8") as handle:
                for event in events:
                    event["format_version"] = MIGRATION_JOURNAL_FORMAT_VERSION
                    event["utc"] = datetime.now(timezone.utc).isoformat()
                    handle.write(json.dumps(event, separators=(",", ":")) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            events.append({
                "file": journal.name,
                "outcome": "journal_failed",
                "error_type": type(exc).__name__,
            })
    return events


@dataclass(frozen=True)
class AppPaths:
    """Canonical paths for one FocusCheck data root.

    Keeping this object immutable prevents components from independently
    recomputing paths during a process lifetime. Legacy files remain available
    through ``choose_path`` for migration tooling, not for new runtime state.
    """

    root: Path
    settings: Path
    settings_backup: Path
    settings_quarantine_prefix: Path
    task_db: Path
    focus_log: Path
    waste_log: Path
    study_log: Path
    intervention_log: Path
    app_log: Path
    supervisor_log: Path
    heartbeat: Path
    stop_request: Path
    lock: Path
    diagnostic_bundle: Path
    runtime_state: Path
    structured_events: Path
    exports: Path
    cache: Path
    temp: Path


def get_app_paths(data_dir: str | os.PathLike[str] | None = None) -> AppPaths:
    """Return one canonical, created path set for the selected data root."""
    root = Path(data_dir) if data_dir is not None else Path(get_data_dir())
    root.mkdir(parents=True, exist_ok=True)
    return AppPaths(
        root=root,
        settings=root / "focus_settings.json",
        settings_backup=root / "focus_settings.json.bak",
        settings_quarantine_prefix=root / "focus_settings.json.corrupt-",
        task_db=root / "focus_tasks.sqlite3",
        focus_log=root / "focus_log.csv",
        waste_log=root / "focus_waste_log.csv",
        study_log=root / "focus_study_log.csv",
        intervention_log=root / "focus_intervention_reflections.jsonl",
        app_log=root / "focus_app.log",
        supervisor_log=root / "focuscheck_supervisor.log",
        heartbeat=root / "hb.txt",
        stop_request=root / "supervisor.stop",
        lock=root / "supervisor.lock",
        diagnostic_bundle=root / "diagnostic_bundle.zip",
        runtime_state=root / "runtime_state.jsonl",
        structured_events=root / "structured_events.jsonl",
        exports=root / "exports",
        cache=root / "cache",
        temp=root / "tmp",
    )


# -------------------- Path Constants --------------------
# These constants define the standard locations for application data files

_APP_PATHS = get_app_paths()
SETTINGS_PATH = str(_APP_PATHS.settings)
LOG_PATH = str(_APP_PATHS.focus_log)
# The application heartbeat and supervisor heartbeat are one protocol/file.
HEARTBEAT_PATH = str(_APP_PATHS.heartbeat)
TASK_DB_PATH = str(_APP_PATHS.task_db)
APP_LOG_PATH = str(_APP_PATHS.app_log)
WASTE_LOG_PATH = str(_APP_PATHS.waste_log)

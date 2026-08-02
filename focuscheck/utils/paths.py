"""
Path management utilities.

Handles application paths, data directory locations, and resource paths
for both development and PyInstaller-frozen environments.
"""

import os
import sys
import platform
import tempfile
from dataclasses import dataclass
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
    Prefer an explicit data directory; otherwise preserve legacy files.

    This allows for backward compatibility with existing installations.

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

    legacy = os.path.join(get_base_dir(), filename)
    if os.path.exists(legacy):
        return legacy
    return os.path.join(get_data_dir(), filename)


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

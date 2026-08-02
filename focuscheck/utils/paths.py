"""
Path management utilities.

Handles application paths, data directory locations, and resource paths
for both development and PyInstaller-frozen environments.
"""

import os
import sys
import platform


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
    3. Fallback: script directory
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
    
    # Fallback to script directory
    base = get_base_dir()
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


# -------------------- Path Constants --------------------
# These constants define the standard locations for application data files

SETTINGS_PATH = choose_path("focus_settings.json")
LOG_PATH = choose_path("focus_log.csv")
# The application heartbeat and supervisor heartbeat are one protocol/file.
HEARTBEAT_PATH = choose_path("hb.txt")
TASK_DB_PATH = choose_path("focus_tasks.sqlite3")
APP_LOG_PATH = choose_path("focus_app.log")
WASTE_LOG_PATH = choose_path("focus_waste_log.csv")

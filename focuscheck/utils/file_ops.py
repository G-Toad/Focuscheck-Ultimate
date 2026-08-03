"""
File operations and locking utilities.

Provides thread-safe file access and single-instance application management.
"""

import os
import platform
import ctypes
import threading
from pathlib import Path


# File locks for thread-safe access
_file_locks = {}
_file_locks_lock = threading.Lock()

# Single instance management
_single_instance_handle = None


class FileSystem:
    """Small injectable boundary for application-owned filesystem effects."""

    def mkdir(self, path, *, parents=True, exist_ok=True):
        Path(path).mkdir(parents=parents, exist_ok=exist_ok)


def get_file_lock(file_path):
    """
    Get a lock for the specified file path.
    
    Args:
        file_path: Path to the file to lock
        
    Returns:
        threading.Lock instance for the file
    """
    with _file_locks_lock:
        if file_path not in _file_locks:
            _file_locks[file_path] = threading.Lock()
        return _file_locks[file_path]


def acquire_single_instance():
    """
    Ensure only one instance of the application is running (Windows only).
    
    Uses a Windows mutex to prevent multiple instances. On non-Windows
    platforms, always returns True.
    
    Returns:
        True if this is the only instance, False if another instance is running
    """
    global _single_instance_handle
    
    if platform.system().lower() != "windows":
        return True

    if _single_instance_handle is not None:
        return True
    
    try:
        from .logging_utils import get_logger
        
        k32 = ctypes.windll.kernel32
        ERROR_ALREADY_EXISTS = 183
        create_mutex = k32.CreateMutexW
        create_mutex.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p)
        create_mutex.restype = ctypes.c_void_p
        get_last_error = k32.GetLastError
        get_last_error.argtypes = ()
        get_last_error.restype = ctypes.c_ulong
        close_handle = k32.CloseHandle
        close_handle.argtypes = (ctypes.c_void_p,)
        close_handle.restype = ctypes.c_int
        names = ["Global\\FocusCheck_Mutex", "Local\\FocusCheck_Mutex"]
        
        for name in names:
            handle = create_mutex(None, True, ctypes.c_wchar_p(name))
            if handle:
                last = get_last_error()
                if last == ERROR_ALREADY_EXISTS:
                    # Another instance already running - STOP immediately
                    close_handle(handle)
                    try:
                        get_logger().warning("single-instance: another instance detected via '%s'; exiting", name)
                    except Exception:
                        pass
                    return False  # FIX: Return False immediately instead of continuing

                # Successfully acquired this mutex - we are the only instance
                _single_instance_handle = handle
                try:
                    get_logger().info("single-instance acquired via mutex '%s'", name)
                except Exception:
                    pass
                return True

        # If we reach here, no mutex was successfully acquired
        try:
            get_logger().warning("single-instance check: failed to acquire any mutex; exiting")
        except Exception:
            pass
        return False
        
    except Exception:
        release_single_instance()
        # Fail-open rather than hard crash
        try:
            from .logging_utils import get_logger
            get_logger().warning("single-instance mutex failed; allowing start", exc_info=True)
        except Exception:
            pass
        return True


def release_single_instance():
    """Release the process-owned mutex handle, if one was acquired."""
    global _single_instance_handle
    handle = _single_instance_handle
    _single_instance_handle = None
    if handle is None or platform.system().lower() != "windows":
        return False
    try:
        close_handle = ctypes.windll.kernel32.CloseHandle
        close_handle.argtypes = (ctypes.c_void_p,)
        close_handle.restype = ctypes.c_int
        return bool(close_handle(handle))
    except Exception:
        return False


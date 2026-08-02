"""Windows top-level window enumeration and control."""

import ctypes
from ctypes import wintypes
import platform


def _get_window_text(hwnd):
    try:
        user32 = ctypes.windll.user32
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        return buff.value or ""
    except Exception:
        return ""


def _get_window_pid(hwnd):
    try:
        user32 = ctypes.windll.user32
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return int(pid.value) if pid.value else None
    except Exception:
        return None


def _get_process_name(pid):
    try:
        kernel32 = ctypes.windll.kernel32
        psapi = ctypes.windll.psapi
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        PROCESS_VM_READ = 0x0010
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ, False, pid)
        if not handle:
            return ""
        try:
            buff = ctypes.create_unicode_buffer(260)
            if psapi.GetModuleBaseNameW(handle, None, buff, 260) == 0:
                return ""
            return buff.value or ""
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        return ""


def list_top_level_windows():
    """Return a list of top-level visible windows on Windows."""
    if platform.system().lower() != "windows":
        return []
    user32 = ctypes.windll.user32
    windows = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def enum_proc(hwnd, lparam):
        try:
            if not user32.IsWindowVisible(hwnd):
                return True
            title = _get_window_text(hwnd)
            if not title:
                return True
            pid = _get_window_pid(hwnd)
            proc = _get_process_name(pid) if pid else ""
            windows.append({
                "hwnd": int(hwnd),
                "title": title,
                "pid": pid,
                "process_name": proc,
            })
        except Exception:
            pass
        return True

    try:
        user32.EnumWindows(enum_proc, 0)
    except Exception:
        pass
    return windows


def close_window(hwnd):
    """Attempt to close a window via WM_CLOSE."""
    try:
        user32 = ctypes.windll.user32
        WM_CLOSE = 0x0010
        user32.PostMessageW(wintypes.HWND(hwnd), WM_CLOSE, 0, 0)
        return True
    except Exception:
        return False


def is_window_open(hwnd):
    """Return True if the window handle is still valid."""
    try:
        user32 = ctypes.windll.user32
        return bool(user32.IsWindow(wintypes.HWND(hwnd)))
    except Exception:
        return False


__all__ = ["list_top_level_windows", "close_window", "is_window_open"]

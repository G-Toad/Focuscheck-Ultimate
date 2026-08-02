"""Activity probe utilities (Windows-focused)."""

import os
import platform
import ctypes
from ctypes import wintypes

from .browser_info import try_get_browser_url
from .cdp_browser import get_best_url_for_window


def _configure_process_api(kernel32):
    """Declare the process APIs before passing pointers across the Win32 boundary."""
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL


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


def _get_window_class(hwnd):
    try:
        user32 = ctypes.windll.user32
        buff = ctypes.create_unicode_buffer(256)
        if user32.GetClassNameW(hwnd, buff, 256) == 0:
            return ""
        return buff.value or ""
    except Exception:
        return ""


def _get_process_path(pid):
    try:
        kernel32 = ctypes.windll.kernel32
        _configure_process_api(kernel32)
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return ""
        try:
            size = wintypes.DWORD(1024)
            buff = ctypes.create_unicode_buffer(size.value)
            if kernel32.QueryFullProcessImageNameW(handle, 0, buff, ctypes.byref(size)) == 0:
                return ""
            return buff.value or ""
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        return ""


def get_active_window_info():
    """Return a dict describing the current foreground window (Windows only)."""
    if platform.system().lower() != "windows":
        return {
            "hwnd": None,
            "title": "",
            "pid": None,
            "process_name": "",
            "exe_path": "",
            "app_name": "Desktop",
            "class_name": "",
            "url": None,
        }
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return {
                "hwnd": None,
                "title": "",
                "pid": None,
                "process_name": "",
                "exe_path": "",
                "app_name": "Desktop",
                "class_name": "",
                "url": None,
            }
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        exe_path = _get_process_path(pid.value)
        process_name = os.path.basename(exe_path) if exe_path else ""
        app_name = os.path.splitext(process_name)[0] if process_name else "Desktop"
        title = _get_window_text(hwnd)
        class_name = _get_window_class(hwnd)
        info = {
            "hwnd": int(hwnd),
            "title": title or "",
            "pid": int(pid.value) if pid.value else None,
            "process_name": process_name,
            "exe_path": exe_path,
            "app_name": app_name or "Desktop",
            "class_name": class_name,
            "url": None,
        }
        try:
            url = None
            # Prefer CDP if available
            url = get_best_url_for_window(title) or None
            if not url:
                url = try_get_browser_url(hwnd, process_name)
            info["url"] = url
        except Exception:
            info["url"] = None
        return info
    except Exception:
        return {
            "hwnd": None,
            "title": "",
            "pid": None,
            "process_name": "",
            "exe_path": "",
            "app_name": "Desktop",
            "class_name": "",
            "url": None,
        }


__all__ = ["get_active_window_info"]

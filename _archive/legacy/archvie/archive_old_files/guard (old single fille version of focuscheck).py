import json
import os
import sys
import time
import csv
import random
import glob
import subprocess
import sqlite3
import tempfile
import threading
import logging
import uuid
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone, timedelta
from typing import Optional
import tkinter as tk
from tkinter import ttk, messagebox
import platform
import ctypes
from ctypes import wintypes
try:
    # Optional cross-platform tray integration
    from system_tray import SystemTray  # type: ignore
except (ImportError, ModuleNotFoundError):
    SystemTray = None  # type: ignore

# --- Windows session / power constants ---
WM_WTSSESSION_CHANGE = 0x02B1
WTS_SESSION_LOCK     = 0x7
WTS_SESSION_UNLOCK   = 0x8

WM_POWERBROADCAST        = 0x0218
PBT_APMSUSPEND           = 0x0004
PBT_APMRESUMESUSPEND     = 0x0007
PBT_APMRESUMESTANDBY     = 0x0008
PBT_APMRESUMEAUTOMATIC   = 0x0012

GWL_WNDPROC = -4
# Extended window styles (Windows)
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_POPUP = 0x80000000
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
HWND_TOPMOST = -1
SW_SHOWNOACTIVATE = 4
LWA_COLORKEY = 0x00000001
LWA_ALPHA = 0x00000002
# Hit-test constants
WM_NCHITTEST = 0x0084
HTTRANSPARENT = -1

WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205
WM_CONTEXTMENU = 0x007B

# Pointer-sized result type for window procedures on 32/64-bit
LRESULT = getattr(wintypes, 'LRESULT', ctypes.c_ssize_t)
WPARAM_T = getattr(wintypes, 'WPARAM', ctypes.c_size_t)
LPARAM_T = getattr(wintypes, 'LPARAM', ctypes.c_ssize_t)
LONG_PTR = ctypes.c_ssize_t

# Helper: reliably enable click-through on Windows (64-bit safe)
def _enable_click_through_windows(hwnd):
    try:
        user32 = ctypes.windll.user32
        # Prefer 64-bit aware APIs when available
        try:
            GetWindowLongPtrW = user32.GetWindowLongPtrW
            SetWindowLongPtrW = user32.SetWindowLongPtrW
            GetWindowLongPtrW.restype = LONG_PTR
            GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
            SetWindowLongPtrW.restype = LONG_PTR
            SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, LONG_PTR]
            exstyle = int(GetWindowLongPtrW(hwnd, GWL_EXSTYLE))
            exstyle |= (WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE)
            _ = SetWindowLongPtrW(hwnd, GWL_EXSTYLE, LONG_PTR(exstyle))
        except AttributeError:
            # Fallback for environments without *Ptr versions
            GetWindowLongW = user32.GetWindowLongW
            SetWindowLongW = user32.SetWindowLongW
            GetWindowLongW.restype = ctypes.c_long
            GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
            SetWindowLongW.restype = ctypes.c_long
            SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
            exstyle = int(GetWindowLongW(hwnd, GWL_EXSTYLE))
            exstyle |= (WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE)
            _ = SetWindowLongW(hwnd, GWL_EXSTYLE, ctypes.c_long(exstyle))
        # Nudge the window manager so the style takes effect immediately
        SWP_NOSIZE = 0x0001
        SWP_NOMOVE = 0x0002
        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        SWP_FRAMECHANGED = 0x0020
        user32.SetWindowPos(hwnd, None, 0, 0, 0, 0,
                            SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED)
        return True
    except Exception:
        return False

def _install_httransparent_wndproc(hwnd, owner_widget=None):
    """Subclass WNDPROC to make the window return HTTRANSPARENT on WM_NCHITTEST.
    Keeps references on owner_widget to avoid GC and restores on destroy.
    """
    try:
        user32 = ctypes.windll.user32
        CallWindowProcW = user32.CallWindowProcW
        try:
            CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, WPARAM_T, LPARAM_T]
            CallWindowProcW.restype = LRESULT
        except Exception:
            pass
        GetWindowLongPtrW = getattr(user32, "GetWindowLongPtrW", None) or user32.GetWindowLongW
        SetWindowLongPtrW = getattr(user32, "SetWindowLongPtrW", None) or user32.SetWindowLongW
        try:
            GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
            GetWindowLongPtrW.restype = ctypes.c_void_p
            SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
            SetWindowLongPtrW.restype = ctypes.c_void_p
        except Exception:
            pass
        old = GetWindowLongPtrW(hwnd, GWL_WNDPROC)
        WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, WPARAM_T, LPARAM_T)
        @WNDPROC
        def proc(h, msg, wParam, lParam):
            try:
                if msg == WM_NCHITTEST:
                    return LRESULT(HTTRANSPARENT)
            except Exception:
                pass
            try:
                return CallWindowProcW(ctypes.c_void_p(old), h, msg, wParam, lParam)
            except Exception:
                return ctypes.windll.user32.DefWindowProcW(h, msg, wParam, lParam)
        SetWindowLongPtrW(hwnd, GWL_WNDPROC, proc)
        # Keep references to avoid GC and to restore later
        if owner_widget is not None:
            try:
                setattr(owner_widget, "_ct_click_oldproc", old)
                setattr(owner_widget, "_ct_click_proc", proc)
                setattr(owner_widget, "_ct_click_setter", SetWindowLongPtrW)
            except Exception:
                pass
        return True
    except Exception:
        return False

# ---- Native Windows click-through overlay (robust for Windows 10/11) ----
_win_overlay_class_atom = None

def _parse_rgb_hex(s, default=(0,0,0)):
    try:
        t = str(s or "#000000").strip()
        if t.startswith('#') and len(t) == 7:
            # Validate hex characters before conversion
            hex_part = t[1:]
            if all(c in '0123456789abcdefABCDEF' for c in hex_part):
                r = int(t[1:3], 16); g = int(t[3:5], 16); b = int(t[5:7], 16)
                return (r,g,b)
    except (ValueError, TypeError):
        pass
    return default

class _WinClickThroughOverlay:
    def __init__(self, x, y, w, h, color_hex="#000000"):
        self.hwnd = None
        self._brush = None
        self._register_class()
        self._create_window(x, y, w, h, color_hex)

    def _register_class(self):
        global _win_overlay_class_atom
        if _win_overlay_class_atom is not None:
            self._atom = _win_overlay_class_atom
            return
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        class WNDCLASSEXW(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_uint),
                ("style", ctypes.c_uint),
                ("lpfnWndProc", ctypes.c_void_p),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HINSTANCE),
                ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HCURSOR),
                ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR),
                ("hIconSm", wintypes.HICON),
            ]
        WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, WPARAM_T, LPARAM_T)
        @WNDPROC
        def _proc(h, msg, wParam, lParam):
            # Always pass mouse through
            if msg == WM_NCHITTEST:
                return LRESULT(HTTRANSPARENT)
            # Minimal paint handler to keep window solid color
            if msg == 0x000F:  # WM_PAINT
                class PAINTSTRUCT(ctypes.Structure):
                    _fields_ = [
                        ("hdc", wintypes.HDC),
                        ("fErase", wintypes.BOOL),
                        ("rcPaint", wintypes.RECT),
                        ("fRestore", wintypes.BOOL),
                        ("fIncUpdate", wintypes.BOOL),
                        ("rgbReserved", ctypes.c_ubyte * 32),
                    ]
                ps = PAINTSTRUCT()
                hdc = user32.BeginPaint(h, ctypes.byref(ps))
                rect = wintypes.RECT()
                user32.GetClientRect(h, ctypes.byref(rect))
                # Fill with class background brush
                try:
                    hbr = ctypes.windll.user32.GetClassLongPtrW(h, -10)
                except Exception:
                    hbr = ctypes.windll.user32.GetClassLongW(h, -10)
                gdi32.FillRect(hdc, ctypes.byref(rect), hbr)
                user32.EndPaint(h, ctypes.byref(ps))
                return 0
            return ctypes.windll.user32.DefWindowProcW(h, msg, wParam, lParam)

        hinst = ctypes.windll.kernel32.GetModuleHandleW(None)
        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.style = 0
        wc.lpfnWndProc = ctypes.cast(_proc, ctypes.c_void_p)
        wc.cbClsExtra = 0
        wc.cbWndExtra = 0
        wc.hInstance = hinst
        wc.hIcon = None
        wc.hCursor = None
        wc.hbrBackground = None  # set later on window
        wc.lpszMenuName = None
        wc.lpszClassName = "FocusCheckOverlayClass"
        wc.hIconSm = None
        atom = user32.RegisterClassExW(ctypes.byref(wc))
        if not atom:
            # If already registered, proceed
            atom = user32.RegisterClassExW(ctypes.byref(wc))
        _win_overlay_class_atom = atom
        self._atom = atom
        self._proc = _proc  # keep ref

    def _create_window(self, x, y, w, h, color_hex):
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        hinst = ctypes.windll.kernel32.GetModuleHandleW(None)
        # Create popup layered transparent, topmost, no-activate toolwindow
        ex = (WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOPMOST | WS_EX_TOOLWINDOW)
        self.hwnd = user32.CreateWindowExW(
            ex,
            "FocusCheckOverlayClass",
            None,
            WS_POPUP,
            int(x), int(y), int(w), int(h),
            None, None, hinst, None
        )
        if not self.hwnd:
            raise RuntimeError("CreateWindowExW failed for overlay")
        # Set background brush color
        r,g,b = _parse_rgb_hex(color_hex)
        RGB = lambda R,G,B: R | (G << 8) | (B << 16)
        hbrush = gdi32.CreateSolidBrush(RGB(r,g,b))
        self._brush = hbrush
        GCLP_HBRBACKGROUND = -10
        try:
            ctypes.windll.user32.SetClassLongPtrW(self.hwnd, GCLP_HBRBACKGROUND, hbrush)
        except Exception:
            ctypes.windll.user32.SetClassLongW(self.hwnd, GCLP_HBRBACKGROUND, hbrush)
        # Show without activation
        user32.ShowWindow(self.hwnd, SW_SHOWNOACTIVATE)
        user32.SetWindowPos(self.hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)
        # Initial alpha 0
        self.set_alpha(0.0)

    def set_alpha(self, a):
        try:
            a = max(0.0, min(1.0, float(a)))
        except Exception:
            a = 0.0
        alpha = int(a * 255) & 0xFF
        ctypes.windll.user32.SetLayeredWindowAttributes(self.hwnd, 0, alpha, LWA_ALPHA)

    def destroy(self):
        try:
            if self._brush:
                ctypes.windll.gdi32.DeleteObject(self._brush)
        except Exception:
            pass
        try:
            if self.hwnd:
                ctypes.windll.user32.DestroyWindow(self.hwnd)
                self.hwnd = None
        except Exception:
            pass

# --- App data paths ---
APP_NAME = "FocusCheck"
APP_VERSION = "1.0.0"

def _get_base_dir():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except Exception:
        return os.getcwd()

def _get_data_dir():
    # Allow override via env var
    env = os.environ.get("FOCUS_DATA_DIR")
    if env:
        try:
            os.makedirs(env, exist_ok=True)
            return env
        except Exception:
            pass
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
    base = _get_base_dir()
    try:
        os.makedirs(base, exist_ok=True)
    except Exception:
        pass
    return base

def _resource_path(relative: str):
    """Return absolute path to a resource bundled with PyInstaller or next to the script.
    When frozen (PyInstaller), resources are in sys._MEIPASS; otherwise relative to this file.
    """
    try:
        base = getattr(sys, "_MEIPASS", None)
        if base:
            return os.path.join(base, relative)
    except Exception:
        pass
    try:
        return os.path.join(_get_base_dir(), relative)
    except Exception:
        return relative

# -------------------- Windows startup helpers --------------------
def _compose_startup_command():
    try:
        if getattr(sys, 'frozen', False):
            return f'"{sys.executable}"'
        return f'"{sys.executable}" "{os.path.abspath(__file__)}"'
    except Exception:
        return os.path.abspath(sys.argv[0] or __file__)

def install_startup(name: str = APP_NAME):
    if platform.system().lower() != 'windows':
        try: print("Startup install is supported on Windows only.")
        except Exception: pass
        return False
    try:
        import winreg  # type: ignore
    except Exception:
        try: print("winreg unavailable; cannot install startup entry.")
        except Exception: pass
        return False
    cmd = _compose_startup_command()
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        except FileNotFoundError:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        try: get_logger().info("installed startup: %s -> %s", name, cmd)
        except Exception: pass
        try: print(f"Installed startup entry: {name} -> {cmd}")
        except Exception: pass
        return True
    except Exception as e:
        try: get_logger().error("install_startup failed: %s", e)
        except Exception: pass
        try: print(f"Failed to install startup entry: {e}")
        except Exception: pass
        return False

def uninstall_startup(name: str = APP_NAME):
    if platform.system().lower() != 'windows':
        try: print("Startup uninstall is supported on Windows only.")
        except Exception: pass
        return False
    try:
        import winreg  # type: ignore
    except Exception:
        try: print("winreg unavailable; cannot uninstall startup entry.")
        except Exception: pass
        return False
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, name)
            try: print(f"Removed startup entry: {name}")
            except Exception: pass
        except FileNotFoundError:
            try: print(f"No startup entry named '{name}' found.")
            except Exception: pass
        finally:
            winreg.CloseKey(key)
        try: get_logger().info("uninstalled startup: %s", name)
        except Exception: pass
        return True
    except Exception as e:
        try: get_logger().error("uninstall_startup failed: %s", e)
        except Exception: pass
        try: print(f"Failed to uninstall startup entry: {e}")
        except Exception: pass
        return False

def is_startup_installed(name: str = APP_NAME) -> bool:
    if platform.system().lower() != 'windows':
        return False
    try:
        import winreg  # type: ignore
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        try:
            val, typ = winreg.QueryValueEx(key, name)
            return bool(val)
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False

def _choose_path(filename):
    """Prefer legacy file path in script dir if it exists; otherwise use data dir."""
    legacy = os.path.join(_get_base_dir(), filename)
    if os.path.exists(legacy):
        return legacy
    return os.path.join(_get_data_dir(), filename)

SETTINGS_PATH = _choose_path("focus_settings.json")
LOG_PATH = _choose_path("focus_log.csv")
HEARTBEAT_PATH = _choose_path("focus_heartbeat.json")
TASK_DB_PATH = _choose_path("focus_tasks.sqlite3")
APP_LOG_PATH = _choose_path("focus_app.log")
WASTE_LOG_PATH = _choose_path("focus_waste_log.csv")

# -------------------- Logging --------------------

_logger = None

def get_logger():
    global _logger
    if _logger is not None:
        return _logger
    try:
        os.makedirs(os.path.dirname(APP_LOG_PATH), exist_ok=True)
    except Exception:
        pass
    logger = logging.getLogger("focuscheck")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        try:
            handler = RotatingFileHandler(APP_LOG_PATH, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
            logger.addHandler(handler)
        except Exception:
            # Fallback to stderr-only
            sh = logging.StreamHandler()
            sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
            logger.addHandler(sh)
    _logger = logger
    return logger

def log_exception(msg):
    try:
        get_logger().exception(msg)
    except Exception:
        pass

# -------------------- Settings synchronization --------------------
_settings_lock = threading.Lock()
_file_locks = {}
_file_locks_lock = threading.Lock()

def _get_file_lock(file_path):
    """Get a lock for the specified file path."""
    with _file_locks_lock:
        if file_path not in _file_locks:
            _file_locks[file_path] = threading.Lock()
        return _file_locks[file_path]

# -------------------- Single-instance guard (Windows mutex) --------------------

_single_instance_handle = None

def acquire_single_instance():
    global _single_instance_handle
    if platform.system().lower() != "windows":
        return True
    try:
        k32 = ctypes.windll.kernel32
        ERROR_ALREADY_EXISTS = 183
        names = ["Global\\FocusCheck_Mutex", "Local\\FocusCheck_Mutex"]
        for name in names:
            handle = k32.CreateMutexW(None, True, ctypes.c_wchar_p(name))
            if handle:
                last = k32.GetLastError()
                if last == ERROR_ALREADY_EXISTS:
                    # Another instance already running
                    k32.CloseHandle(handle)
                    continue
                _single_instance_handle = handle
                try:
                    get_logger().info("single-instance acquired via mutex '%s'", name)
                except Exception:
                    pass
                return True
        try:
            get_logger().warning("single-instance check: another instance detected; exiting")
        except Exception:
            pass
        return False
    except Exception:
        # Fail-open rather than hard crash
        try:
            get_logger().warning("single-instance mutex failed; allowing start", exc_info=True)
        except Exception:
            pass
        return True

DEFAULT_SETTINGS = {
    "settings_schema_version": 1,
    "interval_seconds": 60,
    "intensify_after_seconds": 15,
    "overdrive_after_seconds": 60,
    "max_intensity_level": 3,
    "always_on_top": True,
    "center_on_show": True,
    # Recenter dialog to the monitor under the mouse cursor while open
    "follow_cursor_monitor": True,

    # Anti-habit
    "anti_habit_enabled": True,
    "randomize_buttons": True,
    "studying_hold_ms": 800,

    # Pause/disable controls
    # Hard override: never pause for any reason when True
    "force_always_on": True,
    # Master toggle for pausing logic (kept for backward compatibility)
    "pause_when_inactive_or_lid_closed": False,
    # Granular toggles
    "pause_on_idle": False,               # default OFF per request
    "pause_on_lid_closed": True,
    "pause_on_lock": True,               # Windows: pause while session locked
    "pause_on_sleep": True,              # Pause during system sleep
    # Idle threshold & poll cadence
    "inactive_as_sleep_seconds": 45,     # used only if pause_on_idle=True
    "pause_poll_interval_seconds": 5,    # how often to re-check while paused
    "paused": False,

    # Optional webhook
    "webhook_url": "",

    # Overdrive stage 4 (ultra-fast red flashing)
    "overdrive_stage4_enabled": True,
    "overdrive_stage4_after_seconds": 12,
    "overdrive_stage4_flash_ms": 60,
    # Overdrive stage 5 (multi-monitor dim/blackout)
    "overdrive_stage5_enabled": True,
    # Trigger stage 5 this many seconds after stage 4 begins
    "overdrive_stage5_after_seconds": 60,
    # Dimming behavior
    # Allow underlying apps to remain clickable while dimmed
    "overdrive_stage5_click_through": True,
    "overdrive_stage5_dim_pulse": True,
    "overdrive_stage5_dim_max_alpha": 0.92,
    "overdrive_stage5_dim_color": "#000000",
    # Stage 5 engine: overlay | gamma
    "overdrive_stage5_engine": "overlay",
    # Stage 5 optional: hold final black after N seconds (0 = off)
    "overdrive_stage5_hold_after_seconds": 0,
    # Stage 5 optional: one-way slow-dim to black over N seconds
    "overdrive_stage5_slow_dim_enabled": False,
    "overdrive_stage5_slow_dim_seconds": 30,

    # Time info label under buttons
    "show_time_info": False,
    "time_info_mode": "hour",          # hour | day | anchor | launch
    "time_info_anchor_hhmm": "09:00",
    "time_info_12h": False,
    "time_info_show_seconds": False,
    "time_info_refresh_ms": 1000,
    # Also show remaining time until current task due (if any)
    "time_info_show_task_remaining": False,

    # UI tweaks
    "hide_wasting_button": False,

    # Wasting-time prompt (optional)
    # When enabled, clicking 'Wasting time' asks for details to drive reflection
    "wasting_prompt_enabled": False,
    # When true and the prompt is enabled, ask for 'what'
    "wasting_prompt_ask_what": True,
    # When true and the prompt is enabled, also ask for consequences
    "wasting_prompt_ask_consequences": True,

    # Require an active task before closing the prompt (optional)
    "require_active_task": False,


    # Tray action controls
    "tray_start_stop_enabled": True,
    "tray_settings_button_enabled": True,
    "tray_exit_button_enabled": True,

    # Task encouragement feature (optional)
    "encouragement_enabled": True,
    "show_task_analytics": True,
    # lifetime | today | 7d | 30d
    "tasks_analytics_timescale": "lifetime",
    # Whether changing tasks should count as a failure for analytics
    "tasks_change_counts_as_fail": True,
    # Task deadline decision prompt
    "tasks_decision_prompt_enabled": True,
    "tasks_decision_threshold_minutes": 5,  # legacy (deprecated)
    "tasks_study_implies_fail_on_decision": True,
    # Evaluation timing: before = ask within threshold before due; after = ask after due + offset
    "tasks_evaluation_mode": "before",  # before | after
    "tasks_post_eval_minutes": 10,  # legacy (deprecated)
    # Unified decision window (minutes) applied depending on evaluation mode
    "tasks_decision_window_minutes": 10,

    # Alert/jiggle behavior controls
    "disable_jiggling": False,
    "enable_intensity_pulse": True,
    "enable_intensity_shake": True,
    "enable_intensity_arrows": True,
    "shake_lock_position": True,
    "enable_overdrive_flash_background": True,
    "enable_overdrive_shake_loop": True,
    "enable_overdrive_jiggle_buttons": True,
    # off | nudge | pulse
    "jiggle_style": "nudge"
}

def _validate_settings(data):
    """Coerce and clamp settings to safe ranges; fill defaults; preserve unknown keys."""
    s = DEFAULT_SETTINGS.copy()
    # Merge known keys with defaults
    for k in DEFAULT_SETTINGS:
        if k in data:
            s[k] = data[k]
    # Coercions and clamps
    def _int(v, d):
        try:
            result = int(v)
            # Prevent extremely large values that could cause issues
            if abs(result) > 2**31 - 1:
                return d
            return result
        except (ValueError, TypeError, OverflowError):
            return d
    s["settings_schema_version"] = 1
    s["interval_seconds"] = max(10, _int(s.get("interval_seconds"), DEFAULT_SETTINGS["interval_seconds"]))
    s["intensify_after_seconds"] = max(5, _int(s.get("intensify_after_seconds"), DEFAULT_SETTINGS["intensify_after_seconds"]))
    s["overdrive_after_seconds"] = max(20, _int(s.get("overdrive_after_seconds"), DEFAULT_SETTINGS["overdrive_after_seconds"]))
    s["max_intensity_level"] = min(3, max(1, _int(s.get("max_intensity_level"), DEFAULT_SETTINGS["max_intensity_level"])))
    s["studying_hold_ms"] = max(200, _int(s.get("studying_hold_ms"), DEFAULT_SETTINGS["studying_hold_ms"]))
    s["inactive_as_sleep_seconds"] = max(15, _int(s.get("inactive_as_sleep_seconds"), DEFAULT_SETTINGS["inactive_as_sleep_seconds"]))
    s["pause_poll_interval_seconds"] = max(2, _int(s.get("pause_poll_interval_seconds"), DEFAULT_SETTINGS["pause_poll_interval_seconds"]))
    s["overdrive_stage4_after_seconds"] = max(1, _int(s.get("overdrive_stage4_after_seconds"), DEFAULT_SETTINGS["overdrive_stage4_after_seconds"]))
    s["overdrive_stage4_flash_ms"] = max(20, _int(s.get("overdrive_stage4_flash_ms"), DEFAULT_SETTINGS["overdrive_stage4_flash_ms"]))
    # Stage 5 clamps
    s["overdrive_stage5_after_seconds"] = max(5, _int(s.get("overdrive_stage5_after_seconds"), DEFAULT_SETTINGS["overdrive_stage5_after_seconds"]))
    s["overdrive_stage5_hold_after_seconds"] = max(0, _int(s.get("overdrive_stage5_hold_after_seconds"), DEFAULT_SETTINGS["overdrive_stage5_hold_after_seconds"]))
    s["overdrive_stage5_slow_dim_seconds"] = max(1, _int(s.get("overdrive_stage5_slow_dim_seconds"), DEFAULT_SETTINGS["overdrive_stage5_slow_dim_seconds"]))
    try:
        a = float(s.get("overdrive_stage5_dim_max_alpha", DEFAULT_SETTINGS["overdrive_stage5_dim_max_alpha"]))
        if not (0.0 <= a <= 1.0):
            a = DEFAULT_SETTINGS["overdrive_stage5_dim_max_alpha"]
        s["overdrive_stage5_dim_max_alpha"] = a
    except Exception:
        s["overdrive_stage5_dim_max_alpha"] = DEFAULT_SETTINGS["overdrive_stage5_dim_max_alpha"]
    # Booleans
    for b in [
        "always_on_top", "center_on_show", "follow_cursor_monitor",
        "anti_habit_enabled", "randomize_buttons",
        "force_always_on", "paused", "pause_when_inactive_or_lid_closed", "pause_on_idle",
        "pause_on_lid_closed", "pause_on_lock", "pause_on_sleep",
        "overdrive_stage4_enabled",
        "overdrive_stage5_enabled",
        "show_time_info", "time_info_12h", "time_info_show_seconds",
        "time_info_show_task_remaining",
        "hide_wasting_button",
        "wasting_prompt_enabled", "wasting_prompt_ask_what", "wasting_prompt_ask_consequences",
        "require_active_task",
        "encouragement_enabled", "show_task_analytics", "tasks_change_counts_as_fail",
        "tasks_decision_prompt_enabled", "tasks_study_implies_fail_on_decision",
        "disable_jiggling", "enable_intensity_pulse", "enable_intensity_shake",
        "enable_intensity_arrows", "shake_lock_position",
        "enable_overdrive_flash_background", "enable_overdrive_shake_loop",
        "enable_overdrive_jiggle_buttons",
        "overdrive_stage5_dim_pulse",
        "tray_start_stop_enabled",
        "tray_settings_button_enabled",
        "tray_exit_button_enabled",
        "overdrive_stage5_click_through",
        "overdrive_stage5_slow_dim_enabled",
    ]:
        s[b] = bool(s.get(b, DEFAULT_SETTINGS[b]))
    # Strings
    s["webhook_url"] = str(s.get("webhook_url", "")).strip()
    s["overdrive_stage5_dim_color"] = str(s.get("overdrive_stage5_dim_color", DEFAULT_SETTINGS["overdrive_stage5_dim_color"]) or "#000000").strip()
    eng = str(data.get("overdrive_stage5_engine", DEFAULT_SETTINGS["overdrive_stage5_engine"])).strip().lower()
    if eng not in ("overlay", "gamma"):
        eng = "overlay"
    s["overdrive_stage5_engine"] = eng
    # Time info mode clamp
    mode = str(s.get("time_info_mode", "hour")).lower().strip()
    if mode not in ("hour", "day", "anchor", "launch"):
        mode = "hour"
    s["time_info_mode"] = mode
    # Analytics timescale clamp
    tscale = str(s.get("tasks_analytics_timescale", "lifetime")).lower().strip()
    if tscale not in ("lifetime", "today", "7d", "30d"):
        tscale = "lifetime"
    s["tasks_analytics_timescale"] = tscale
    # Unified decision window minutes (with legacy fallback)
    try:
        winm = s.get("tasks_decision_window_minutes", None)
        if winm is None:
            # Back-compat: derive from legacy per-mode settings
            emode_probe = str(s.get("tasks_evaluation_mode", "before")).strip().lower()
            if emode_probe == "before":
                winm = s.get("tasks_decision_threshold_minutes", 10)
            else:
                winm = s.get("tasks_post_eval_minutes", 10)
        s["tasks_decision_window_minutes"] = max(0, int(winm))
    except Exception:
        s["tasks_decision_window_minutes"] = 10
    # Evaluation timing clamp
    emode = str(s.get("tasks_evaluation_mode", "before")).strip().lower()
    if emode not in ("before", "after"):
        emode = "before"
    s["tasks_evaluation_mode"] = emode
    # Keep legacy keys sanitized but unused in UI
    try:
        s["tasks_decision_threshold_minutes"] = max(0, int(s.get("tasks_decision_threshold_minutes", 5)))
    except Exception:
        s["tasks_decision_threshold_minutes"] = 5
    try:
        s["tasks_post_eval_minutes"] = max(0, int(s.get("tasks_post_eval_minutes", 10)))
    except Exception:
        s["tasks_post_eval_minutes"] = 10
    # Jiggle style
    js = str(s.get("jiggle_style", "nudge")).strip().lower()
    if js not in ("off", "nudge", "pulse"):
        js = "nudge"
    s["jiggle_style"] = js
    # Anchor HH:MM sanitize
    def _sanitize_hhmm(val, default="09:00"):
        try:
            txt = str(val).strip()
            parts = txt.split(":")
            if len(parts) != 2: return default
            hh = int(parts[0]); mm = int(parts[1])
            if 0 <= hh <= 23 and 0 <= mm <= 59:
                return f"{hh:02d}:{mm:02d}"
            return default
        except Exception:
            return default
    s["time_info_anchor_hhmm"] = _sanitize_hhmm(s.get("time_info_anchor_hhmm", "09:00"), "09:00")
    # Refresh rate clamp
    s["time_info_refresh_ms"] = max(250, _int(s.get("time_info_refresh_ms"), DEFAULT_SETTINGS["time_info_refresh_ms"]))
    return s

def load_settings():
    with _settings_lock:
        if os.path.exists(SETTINGS_PATH):
            try:
                with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return _validate_settings(data)
            except Exception:
                log_exception("load_settings: failed to parse settings; using defaults")
        # Create data dir if needed
        try:
            os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        except Exception:
            pass
        return DEFAULT_SETTINGS.copy()

def save_settings(s):
    with _settings_lock:
        try:
            os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        except Exception:
            pass
        try:
            # Atomic write using temporary file
            temp_path = SETTINGS_PATH + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(_validate_settings(s), f, indent=2)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
            # Atomic rename
            if platform.system().lower() == "windows":
                # Windows requires remove before rename
                if os.path.exists(SETTINGS_PATH):
                    os.remove(SETTINGS_PATH)
            os.rename(temp_path, SETTINGS_PATH)
            get_logger().info("settings saved")
        except Exception:
            # Clean up temp file on failure
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass
            log_exception("save_settings: failed to write file")

# -------------------- Task DB --------------------

class TaskDB:
    def __init__(self, path):
        self.path = path
        self._ensure_schema()

    def _conn(self):
        con = sqlite3.connect(self.path, timeout=30)
        try:
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA synchronous=NORMAL")
        except Exception:
            pass
        return con

    def _ensure_schema(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
        except Exception:
            pass
        try:
            with self._conn() as con:
                cur = con.cursor()
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_utc TEXT NOT NULL,
                        title TEXT NOT NULL,
                        why TEXT,
                        consequences TEXT,
                        due_utc TEXT,
                        status TEXT NOT NULL,
                        completed_utc TEXT,
                        change_reason TEXT
                    )
                    """
                )
                cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_utc)")
                # Add timed_out column if missing
                try:
                    cur.execute("PRAGMA table_info(tasks)")
                    cols = [r[1] for r in cur.fetchall()]
                    if "timed_out" not in cols:
                        cur.execute("ALTER TABLE tasks ADD COLUMN timed_out INTEGER DEFAULT 0")
                except Exception:
                    pass
                # Waste events table (what the user was wasting time on)
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS waste_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_utc TEXT NOT NULL,
                        what TEXT,
                        consequences TEXT,
                        active_task_id INTEGER
                    )
                    """
                )
                cur.execute("CREATE INDEX IF NOT EXISTS idx_waste_created ON waste_events(created_utc)")
                con.commit()
        except Exception:
            log_exception("TaskDB: failed ensuring schema")

    def get_active(self):
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("SELECT id, created_utc, title, why, consequences, due_utc, status, completed_utc, change_reason FROM tasks WHERE status = 'active' ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            return self._row_to_dict(row) if row else None

    def start_task(self, *, title, due_utc, why, consequences):
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as con:
            cur = con.cursor()
            cur.execute(
                "INSERT INTO tasks(created_utc, title, why, consequences, due_utc, status) VALUES (?,?,?,?,?, 'active')",
                (now, title, why, consequences, due_utc)
            )
            con.commit()
            return cur.lastrowid

    def mark_completed(self, task_id, when_utc=None):
        if when_utc is None:
            when_utc = datetime.now(timezone.utc).isoformat()
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("UPDATE tasks SET status='completed', completed_utc=? WHERE id=? AND status='active'", (when_utc, task_id))
            con.commit()

    def mark_failed(self, task_id, when_utc=None, timed_out=False):
        if when_utc is None:
            when_utc = datetime.now(timezone.utc).isoformat()
        with self._conn() as con:
            cur = con.cursor()
            try:
                cur.execute("UPDATE tasks SET status='failed', completed_utc=?, timed_out=? WHERE id=? AND status IN ('active','completed')", (when_utc, 1 if timed_out else 0, task_id))
            except Exception:
                # Fallback for DBs without timed_out column
                cur.execute("UPDATE tasks SET status='failed', completed_utc=? WHERE id=? AND status IN ('active','completed')", (when_utc, task_id))
            con.commit()

    def mark_changed(self, task_id, reason):
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("UPDATE tasks SET status='changed', change_reason=? WHERE id=? AND status='active'", (reason, task_id))
            con.commit()

    def _row_to_dict(self, row):
        if not row:
            return None
        keys = ["id","created_utc","title","why","consequences","due_utc","status","completed_utc","change_reason"]
        return dict(zip(keys, row))

    def overdue_active_to_failed(self):
        now_iso = datetime.now(timezone.utc).isoformat()
        affected = []
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("SELECT id, due_utc FROM tasks WHERE status='active' AND due_utc IS NOT NULL")
            for tid, due_iso in cur.fetchall():
                try:
                    if not due_iso:
                        continue
                    due = datetime.fromisoformat(due_iso)
                    if datetime.now(timezone.utc) > due:
                        cur.execute("UPDATE tasks SET status='failed', completed_utc=? WHERE id=? AND status='active'", (now_iso, tid))
                        affected.append(tid)
                except Exception:
                    pass
            con.commit()
        return affected

    def analytics_counts(self, *, timescale="lifetime", treat_changed_as_fail=True):
        where = ""
        params = []
        now = datetime.now(timezone.utc)
        if timescale == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            where = "WHERE datetime(created_utc) >= datetime(?)"
            params = [start.isoformat()]
        elif timescale == "7d":
            start = now - timedelta(days=7)
            where = "WHERE datetime(created_utc) >= datetime(?)"
            params = [start.isoformat()]
        elif timescale == "30d":
            start = now - timedelta(days=30)
            where = "WHERE datetime(created_utc) >= datetime(?)"
            params = [start.isoformat()]

        q = f"SELECT status, COUNT(*) FROM tasks {where} GROUP BY status"
        stats = {"completed": 0, "failed": 0, "changed": 0}
        with self._conn() as con:
            cur = con.cursor()
            cur.execute(q, params)
            for status, cnt in cur.fetchall():
                status = status or ""
                if status in stats:
                    stats[status] = int(cnt)
            # timed_out count
            try:
                tq = f"SELECT COALESCE(SUM(timed_out),0) FROM tasks {where}"
                cur.execute(tq, params)
                timed_out = int(cur.fetchone()[0] or 0)
            except Exception:
                timed_out = 0
        total_failed = stats["failed"] + (stats["changed"] if treat_changed_as_fail else 0)
        return {"completed": stats["completed"], "failed": total_failed, "changed": stats["changed"], "timed_out": timed_out}

    def list_history(self, limit=100, include_active=True):
        """Return recent tasks as a list of dicts.
        Ordered by newest first. If include_active is False, exclude active tasks.
        """
        where = ""
        params = []
        if not include_active:
            where = "WHERE status != 'active'"
        q = (
            "SELECT id, created_utc, title, why, consequences, due_utc, status, "
            "completed_utc, change_reason, "
            "CASE WHEN typeof(timed_out) IS NULL THEN 0 ELSE COALESCE(timed_out,0) END as timed_out "
            f"FROM tasks {where} ORDER BY id DESC LIMIT ?"
        )
        params.append(int(limit))
        rows = []
        with self._conn() as con:
            cur = con.cursor()
            try:
                cur.execute(q, params)
            except Exception:
                # Fallback for DBs without timed_out column
                q2 = (
                    "SELECT id, created_utc, title, why, consequences, due_utc, status, "
                    "completed_utc, change_reason FROM tasks "
                    f"{where} ORDER BY id DESC LIMIT ?"
                )
                cur.execute(q2, params)
            cols = [c[0] for c in cur.description]
            for r in cur.fetchall():
                d = {k: r[i] for i, k in enumerate(cols)}
                # Normalize timed_out presence
                if "timed_out" not in d:
                    d["timed_out"] = 0
                rows.append(d)
        return rows

    def record_waste_event(self, *, what, consequences, active_task_id=None, when_utc=None):
        try:
            if when_utc is None:
                when_utc = datetime.now(timezone.utc).isoformat()
            with self._conn() as con:
                cur = con.cursor()
                cur.execute(
                    "INSERT INTO waste_events(created_utc, what, consequences, active_task_id) VALUES (?,?,?,?)",
                    (when_utc, (what or ""), (consequences or ""), active_task_id)
                )
                con.commit()
                return cur.lastrowid
        except Exception:
            log_exception("TaskDB: record_waste_event failed")
            return None

def _rotate_log_if_needed():
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    except Exception:
        pass
    try:
        max_bytes = 5_000_000
        if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) >= max_bytes:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_name = os.path.join(os.path.dirname(LOG_PATH), f"focus_log_{ts}.csv")
            try:
                os.replace(LOG_PATH, new_name)
                try:
                    get_logger().info("rotated CSV log to %s", new_name)
                except Exception:
                    pass
            except Exception:
                log_exception("log rotation failed")
    except Exception:
        log_exception("rotate_log_if_needed: unexpected error")

# CSV file locking to prevent corruption
_csv_locks = {}
_csv_locks_mutex = threading.Lock()

def _get_csv_lock(file_path):
    """Get or create a lock for a specific CSV file."""
    with _csv_locks_mutex:
        if file_path not in _csv_locks:
            _csv_locks[file_path] = threading.Lock()
        return _csv_locks[file_path]

def _safe_csv_write(file_path, write_func):
    """Thread-safe CSV writing with file locking."""
    lock = _get_csv_lock(file_path)
    with lock:
        try:
            write_func()
        except Exception:
            log_exception(f"CSV write failed for {file_path}")

def ensure_log_header():
    _rotate_log_if_needed()

    def _write_header():
        needs_header = True
        try:
            if os.path.exists(LOG_PATH):
                try:
                    needs_header = os.path.getsize(LOG_PATH) == 0
                except Exception:
                    needs_header = True
            with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if needs_header:
                    w.writerow([
                        "click_timestamp_utc", "click_local_time",
                        "slot_start_utc", "slot_start_local_minute",
                        "response", "on_time", "late_by_ms",
                        "response_latency_ms",
                        "interval_seconds", "intensify_after_seconds", "overdrive_after_seconds",
                        "intensity_level_reached"
                    ])
        except Exception:
            log_exception("ensure_log_header: failed to open/write")

    _safe_csv_write(LOG_PATH, _write_header)

def append_log(*, response, latency_ms, settings, intensity_level_reached,
               slot_start_dt, overdrive_deadline_s):
    now_utc = datetime.now(timezone.utc)
    elapsed_s = (time.monotonic() - slot_start_dt["mono_start"])
    late_by_ms = max(0, int((elapsed_s - overdrive_deadline_s) * 1000))
    on_time = "YES" if late_by_ms == 0 else "NO"

    def _write_log():
        ensure_log_header()
        with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                now_utc.isoformat(),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                slot_start_dt["utc_start"].isoformat(),
                slot_start_dt["local_minute"],
                response, on_time, late_by_ms,
                int(latency_ms),
                int(settings["interval_seconds"]),
                int(settings["intensify_after_seconds"]),
                int(settings["overdrive_after_seconds"]),
                int(intensity_level_reached)
            ])

    _safe_csv_write(LOG_PATH, _write_log)

    # Optional webhook placeholder
    if settings.get("webhook_url"):
        pass

def _rotate_csv_if_needed(path, max_bytes=5_000, backups=2):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except Exception:
        pass
    try:
        sz = os.path.getsize(path) if os.path.exists(path) else 0
        if sz < max_bytes:
            return
        # rotate: path -> path.1 -> path.2
        for i in range(backups, 0, -1):
            older = f"{path}.{i}"
            newer = f"{path}.{i+1}"
            try:
                if os.path.exists(older):
                    if i == backups:
                        try:
                            os.remove(older)
                        except Exception:
                            pass
                    else:
                        os.replace(older, newer)
            except Exception:
                pass
        try:
            if os.path.exists(path):
                os.replace(path, f"{path}.1")
        except Exception:
            pass
    except Exception:
        log_exception("rotate_csv_if_needed failed")

def ensure_waste_log_header():
    _rotate_csv_if_needed(WASTE_LOG_PATH)

    def _write_header():
        needs_header = True
        try:
            if os.path.exists(WASTE_LOG_PATH):
                try:
                    needs_header = os.path.getsize(WASTE_LOG_PATH) == 0
                except Exception:
                    needs_header = True
            with open(WASTE_LOG_PATH, "a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if needs_header:
                    w.writerow([
                        "event_utc", "event_local",
                        "slot_start_utc", "response_latency_ms",
                        "what", "consequences",
                        "active_task_id", "active_task_title"
                    ])
        except Exception:
            log_exception("ensure_waste_log_header failed")

    _safe_csv_write(WASTE_LOG_PATH, _write_header)

def append_waste_log(*, slot_start_dt, latency_ms, what, consequences, active_task):
    now_utc = datetime.now(timezone.utc)
    # Normalize slot_start_utc string from either dict or datetime
    try:
        if isinstance(slot_start_dt, dict):
            us = slot_start_dt.get("utc_start")
        else:
            us = slot_start_dt
        if isinstance(us, datetime):
            slot_start_utc = us.isoformat()
        else:
            slot_start_utc = str(us)
    except Exception:
        slot_start_utc = ""

    def _write_waste_log():
        ensure_waste_log_header()
        with open(WASTE_LOG_PATH, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                now_utc.isoformat(),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                slot_start_utc,
                int(latency_ms),
                what or "",
                consequences or "",
                (active_task.get("id") if active_task else None),
                (active_task.get("title") if active_task else "")
            ])

    _safe_csv_write(WASTE_LOG_PATH, _write_waste_log)

# -------------------- Pause Guard (asleep / lid-closed detection) --------------------

class PauseGuard:
    def __init__(self, settings_getter):
        self._get_settings = settings_getter
        self._os = platform.system().lower()
        # Event-driven pause flags (Windows lock/sleep)
        self._locked = False
        self._sleeping = False

    # Event hooks (called by platform watchers)
    def set_locked(self, is_locked: bool):
        self._locked = bool(is_locked)

    def set_sleeping(self, is_sleeping: bool):
        self._sleeping = bool(is_sleeping)

    def should_pause(self):
        s = self._get_settings()
        if s.get("force_always_on", False):
            return False
        if not s.get("pause_when_inactive_or_lid_closed", True):
            return False

        # If any enabled mechanism says "away", pause.
        if s.get("pause_on_idle", False) and self._looks_inactive_by_idle():
            return True
        if s.get("pause_on_lid_closed", True) and (self._looks_lid_closed_linux() or self._looks_lid_closed_macos()):
            return True
        if self._os == "windows":
            if s.get("pause_on_lock", True) and self._locked:
                return True
            if s.get("pause_on_sleep", True) and self._sleeping:
                return True
        return False

    # ---- Windows / general idle detection ----
    def _looks_inactive_by_idle(self):
        s = self._get_settings()
        thresh_ms = int(s.get("inactive_as_sleep_seconds", 45)) * 1000

        try:
            if platform.system().lower() == "windows":
                class LASTINPUTINFO(ctypes.Structure):
                    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
                plii = LASTINPUTINFO()
                plii.cbSize = ctypes.sizeof(LASTINPUTINFO)
                if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(plii)):
                    k32 = ctypes.windll.kernel32
                    # Prefer 64-bit tick count to avoid 49.7-day wrap
                    get64 = getattr(k32, 'GetTickCount64', None)
                    if get64:
                        tick_now = get64()
                        idle_ms = int(tick_now - plii.dwTime)
                    else:
                        tick_now = k32.GetTickCount()
                        # Handle wrap-around for 32-bit tick count (proper signed arithmetic)
                        diff = (int(tick_now) - int(plii.dwTime)) & 0xFFFFFFFF
                        if diff > 0x7FFFFFFF:
                            diff -= 0x100000000
                        idle_ms = abs(diff)
                    return idle_ms >= thresh_ms
                # If API fails, fall back to no-pause
                return False
            else:
                # On non-Windows, we don't have a clean idle API without deps.
                # Treat as not-inactive here; lid checks may still pause.
                return False
        except Exception:
            return False

    # ---- Linux laptop lid via ACPI ----
    def _looks_lid_closed_linux(self):
        if self._os != "linux":
            return False
        try:
            paths = glob.glob("/proc/acpi/button/lid/*/state")
            for p in paths:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    txt = f.read().lower()
                    if "closed" in txt:
                        return True
        except Exception:
            pass
        return False

    # ---- macOS clamshell ----
    def _looks_lid_closed_macos(self):
        if self._os != "darwin":
            return False
        try:
            # ioreg returns AppleClamshellState = Yes when lid is closed
            out = subprocess.check_output(
                ["ioreg", "-r", "-k", "AppleClamshellState", "-d", "1"],
                stderr=subprocess.DEVNULL, timeout=1.0
            ).decode("utf-8", "ignore").lower()
            if "appleclamshellstate" in out and ("= yes" in out or "yes" in out):
                return True
        except Exception:
            pass
        return False

# -------------------- UI: Settings --------------------

class SettingsWindow(tk.Toplevel):
    def __init__(self, master, settings, on_save):
        super().__init__(master)
        self.title("Settings")
        self.resizable(False, False)
        self.settings = settings.copy()
        self.on_save = on_save
        pad = {"padx": 8, "pady": 6}

        def add_row(r, label, var, suffix=""):
            ttk.Label(self, text=label).grid(row=r, column=0, sticky="w", **pad)
            e = ttk.Entry(self, textvariable=var, width=12)
            e.grid(row=r, column=1, sticky="w", **pad)
            ttk.Label(self, text=suffix).grid(row=r, column=2, sticky="w")

        # Core timings
        self.interval_var = tk.StringVar(value=str(self.settings["interval_seconds"]))
        self.intensify_var = tk.StringVar(value=str(self.settings["intensify_after_seconds"]))
        self.overdrive_var = tk.StringVar(value=str(self.settings["overdrive_after_seconds"]))
        self.max_intensity_var = tk.StringVar(value=str(self.settings["max_intensity_level"]))

        self.topmost_var = tk.BooleanVar(value=bool(self.settings["always_on_top"]))
        self.center_var = tk.BooleanVar(value=bool(self.settings["center_on_show"]))

        # Anti-habit
        self.anti_var = tk.BooleanVar(value=bool(self.settings["anti_habit_enabled"]))
        self.rand_btns_var = tk.BooleanVar(value=bool(self.settings["randomize_buttons"]))
        self.hold_ms_var = tk.StringVar(value=str(self.settings["studying_hold_ms"]))

        # Pause guard
        self.force_on_var = tk.BooleanVar(value=bool(self.settings.get("force_always_on", False)))
        self.pause_var = tk.BooleanVar(value=bool(self.settings["pause_when_inactive_or_lid_closed"]))
        self.pause_on_idle_var = tk.BooleanVar(value=bool(self.settings.get("pause_on_idle", False)))
        self.pause_on_lid_var = tk.BooleanVar(value=bool(self.settings.get("pause_on_lid_closed", True)))
        self.pause_on_lock_var = tk.BooleanVar(value=bool(self.settings.get("pause_on_lock", True)))
        self.pause_on_sleep_var = tk.BooleanVar(value=bool(self.settings.get("pause_on_sleep", True)))
        self.idle_secs_var = tk.StringVar(value=str(self.settings["inactive_as_sleep_seconds"]))
        self.pause_poll_var = tk.StringVar(value=str(self.settings["pause_poll_interval_seconds"]))

        self.webhook_var = tk.StringVar(value=str(self.settings.get("webhook_url", "")))
        # Stage 4 overdrive
        self.stage4_enabled_var = tk.BooleanVar(value=bool(self.settings.get("overdrive_stage4_enabled", True)))
        self.stage4_after_var = tk.StringVar(value=str(self.settings.get("overdrive_stage4_after_seconds", 12)))
        self.stage4_rate_var = tk.StringVar(value=str(self.settings.get("overdrive_stage4_flash_ms", 60)))

        # Stage 5 overdrive (screen blackout/dimming)
        self.stage5_enabled_var = tk.BooleanVar(value=bool(self.settings.get("overdrive_stage5_enabled", True)))
        self.stage5_after_var = tk.StringVar(value=str(self.settings.get("overdrive_stage5_after_seconds", 60)))
        self.stage5_pulse_var = tk.BooleanVar(value=bool(self.settings.get("overdrive_stage5_dim_pulse", True)))
        self.stage5_alpha_var = tk.StringVar(value=str(self.settings.get("overdrive_stage5_dim_max_alpha", 0.92)))
        self.stage5_color_var = tk.StringVar(value=str(self.settings.get("overdrive_stage5_dim_color", "#000000")))
        self.stage5_clickthrough_var = tk.BooleanVar(value=bool(self.settings.get("overdrive_stage5_click_through", True)))
        self.stage5_engine_var = tk.StringVar(value=str(self.settings.get("overdrive_stage5_engine", "overlay")))
        # New stage 5 features
        self.stage5_hold_after_var = tk.StringVar(value=str(self.settings.get("overdrive_stage5_hold_after_seconds", 0)))
        self.stage5_slow_dim_enabled_var = tk.BooleanVar(value=bool(self.settings.get("overdrive_stage5_slow_dim_enabled", False)))
        self.stage5_slow_dim_secs_var = tk.StringVar(value=str(self.settings.get("overdrive_stage5_slow_dim_seconds", 30)))

        # Time info settings
        self.show_time_info_var = tk.BooleanVar(value=bool(self.settings.get("show_time_info", False)))
        self.time_mode_var = tk.StringVar(value=str(self.settings.get("time_info_mode", "hour")))
        self.time_anchor_var = tk.StringVar(value=str(self.settings.get("time_info_anchor_hhmm", "09:00")))
        self.time_12h_var = tk.BooleanVar(value=bool(self.settings.get("time_info_12h", False)))
        self.time_secs_var = tk.BooleanVar(value=bool(self.settings.get("time_info_show_seconds", False)))
        self.time_refresh_var = tk.StringVar(value=str(self.settings.get("time_info_refresh_ms", 1000)))

        # Alert / jiggle behavior
        self.disable_jiggle_var = tk.BooleanVar(value=bool(self.settings.get("disable_jiggling", False)))
        self.intensity_pulse_var = tk.BooleanVar(value=bool(self.settings.get("enable_intensity_pulse", True)))
        self.intensity_shake_var = tk.BooleanVar(value=bool(self.settings.get("enable_intensity_shake", True)))
        self.intensity_arrows_var = tk.BooleanVar(value=bool(self.settings.get("enable_intensity_arrows", True)))

        # Task / wasting-time prompt toggles
        self.waste_prompt_enabled_var = tk.BooleanVar(value=bool(self.settings.get("wasting_prompt_enabled", False)))
        self.waste_prompt_what_var = tk.BooleanVar(value=bool(self.settings.get("wasting_prompt_ask_what", True)))
        self.waste_prompt_cons_var = tk.BooleanVar(value=bool(self.settings.get("wasting_prompt_ask_consequences", True)))
        self.shake_lock_var = tk.BooleanVar(value=bool(self.settings.get("shake_lock_position", True)))
        self.od_flash_bg_var = tk.BooleanVar(value=bool(self.settings.get("enable_overdrive_flash_background", True)))
        self.od_shake_loop_var = tk.BooleanVar(value=bool(self.settings.get("enable_overdrive_shake_loop", True)))
        self.od_jiggle_btns_var = tk.BooleanVar(value=bool(self.settings.get("enable_overdrive_jiggle_buttons", True)))
        self.jiggle_style_var = tk.StringVar(value=str(self.settings.get("jiggle_style", "nudge")))

        # Task / UI settings
        self.hide_waste_var = tk.BooleanVar(value=bool(self.settings.get("hide_wasting_button", False)))
        self.encourage_var = tk.BooleanVar(value=bool(self.settings.get("encouragement_enabled", True)))
        self.show_analytics_var = tk.BooleanVar(value=bool(self.settings.get("show_task_analytics", True)))
        self.change_as_fail_var = tk.BooleanVar(value=bool(self.settings.get("tasks_change_counts_as_fail", True)))
        self.require_task_var = tk.BooleanVar(value=bool(self.settings.get("require_active_task", False)))
        self.tasks_timescale_var = tk.StringVar(value=str(self.settings.get("tasks_analytics_timescale", "lifetime")))
        self.tasks_decision_enabled_var = tk.BooleanVar(value=bool(self.settings.get("tasks_decision_prompt_enabled", True)))
        # Unified window
        self.tasks_decision_window_var = tk.StringVar(value=str(self.settings.get("tasks_decision_window_minutes", 10)))
        self.tasks_study_implies_fail_var = tk.BooleanVar(value=bool(self.settings.get("tasks_study_implies_fail_on_decision", True)))
        self.tasks_eval_mode_var = tk.StringVar(value=str(self.settings.get("tasks_evaluation_mode", "before")))

        # New general/tray settings
        self.follow_cursor_var = tk.BooleanVar(value=bool(self.settings.get("follow_cursor_monitor", True)))
        self.tray_start_stop_enabled_var = tk.BooleanVar(value=bool(self.settings.get("tray_start_stop_enabled", True)))
        self.tray_settings_enabled_var = tk.BooleanVar(value=bool(self.settings.get("tray_settings_button_enabled", True)))
        self.tray_exit_enabled_var = tk.BooleanVar(value=bool(self.settings.get("tray_exit_button_enabled", True)))
        # New time info toggle for task remaining
        self.time_show_task_left_var = tk.BooleanVar(value=bool(self.settings.get("time_info_show_task_remaining", False)))

        # Tabbed notebook
        # Make main content scrollable (Notebook inside a Canvas)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        scroll_container = ttk.Frame(self)
        scroll_container.grid(row=0, column=0, sticky="nsew")
        scroll_container.grid_columnconfigure(0, weight=1)
        scroll_container.grid_rowconfigure(0, weight=1)
        cv = tk.Canvas(scroll_container, highlightthickness=0)
        vsb = ttk.Scrollbar(scroll_container, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=vsb.set)
        cv.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        nb = ttk.Notebook(cv)
        _nbw = cv.create_window((0, 0), window=nb, anchor="nw")
        def _sync_scroll(_evt=None):
            try:
                cv.configure(scrollregion=cv.bbox("all"))
                cv.itemconfigure(_nbw, width=cv.winfo_width())
            except Exception:
                pass
        nb.bind("<Configure>", _sync_scroll)
        cv.bind("<Configure>", _sync_scroll)

        tab_general = ttk.Frame(nb)
        tab_tray = ttk.Frame(nb)
        tab_antihabit = ttk.Frame(nb)
        tab_pause = ttk.Frame(nb)
        tab_overdrive = ttk.Frame(nb)
        tab_time = ttk.Frame(nb)
        tab_tasks = ttk.Frame(nb)

        nb.add(tab_general, text="General")
        nb.add(tab_tray, text="Tray")
        nb.add(tab_antihabit, text="Anti-Habit")
        nb.add(tab_pause, text="Pause")
        nb.add(tab_overdrive, text="Overdrive")
        nb.add(tab_time, text="Time Info")
        nb.add(tab_tasks, text="Tasks")

        # General
        def add_row_to(parent, r, label, var, suffix=""):
            ttk.Label(parent, text=label).grid(row=r, column=0, sticky="w", **pad)
            e = ttk.Entry(parent, textvariable=var, width=12)
            e.grid(row=r, column=1, sticky="w", **pad)
            ttk.Label(parent, text=suffix).grid(row=r, column=2, sticky="w")
        add_row_to(tab_general, 0, "Interval:", self.interval_var, "seconds")
        add_row_to(tab_general, 1, "Intensify after:", self.intensify_var, "seconds")
        add_row_to(tab_general, 2, "Overdrive after:", self.overdrive_var, "seconds")
        add_row_to(tab_general, 3, "Max intensity level:", self.max_intensity_var, "1–3")
        ttk.Checkbutton(tab_general, text="Always on top", variable=self.topmost_var).grid(row=4, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_general, text="Center on show", variable=self.center_var).grid(row=5, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_general, text="Recenter to cursor's monitor while open", variable=self.follow_cursor_var).grid(row=6, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(tab_general, text="Webhook URL (optional)").grid(row=7, column=0, columnspan=3, sticky="w", **pad)
        ttk.Entry(tab_general, textvariable=self.webhook_var, width=48).grid(row=8, column=0, columnspan=3, sticky="we", padx=8, pady=(0,8))

        # Tray
        ttk.Label(tab_tray, text="Tray Menu Buttons", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_tray, text="Show start/stop button", variable=self.tray_start_stop_enabled_var).grid(row=1, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_tray, text="Show settings button", variable=self.tray_settings_enabled_var).grid(row=2, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_tray, text="Show exit button", variable=self.tray_exit_enabled_var).grid(row=3, column=0, columnspan=3, sticky="w", **pad)

        # Anti-Habit
        ttk.Checkbutton(tab_antihabit, text="Anti-habit enabled", variable=self.anti_var).grid(row=0, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_antihabit, text="Randomize button positions", variable=self.rand_btns_var).grid(row=1, column=0, columnspan=3, sticky="w", **pad)
        add_row_to(tab_antihabit, 2, "Studying hold:", self.hold_ms_var, "ms")

        # Pause
        ttk.Checkbutton(tab_pause, text="Never pause (force always-on)", variable=self.force_on_var).grid(row=0, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_pause, text="Enable pausing when away/asleep", variable=self.pause_var).grid(row=1, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_pause, text="Pause on idle (no keyboard/mouse)", variable=self.pause_on_idle_var).grid(row=2, column=0, columnspan=3, sticky="w", **pad)
        add_row_to(tab_pause, 3, "Idle threshold:", self.idle_secs_var, "seconds")
        ttk.Checkbutton(tab_pause, text="Pause on Windows lock", variable=self.pause_on_lock_var).grid(row=4, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_pause, text="Pause on system sleep", variable=self.pause_on_sleep_var).grid(row=5, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_pause, text="Pause on lid closed (Linux/macOS)", variable=self.pause_on_lid_var).grid(row=6, column=0, columnspan=3, sticky="w", **pad)
        add_row_to(tab_pause, 7, "Pause poll interval:", self.pause_poll_var, "seconds")

        # Overdrive
        ttk.Checkbutton(tab_overdrive, text="Enable Stage 4 overdrive (ultra-fast red flash)", variable=self.stage4_enabled_var).grid(row=0, column=0, columnspan=3, sticky="w", **pad)
        add_row_to(tab_overdrive, 1, "Stage 4 after:", self.stage4_after_var, "seconds")
        add_row_to(tab_overdrive, 2, "Stage 4 flash rate:", self.stage4_rate_var, "ms")
        ttk.Separator(tab_overdrive).grid(row=3, column=0, columnspan=3, sticky="ew", padx=8, pady=(4,6))
        ttk.Checkbutton(tab_overdrive, text="Disable all jiggling/movement", variable=self.disable_jiggle_var).grid(row=4, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_overdrive, text="Intensity: pulse buttons", variable=self.intensity_pulse_var).grid(row=5, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_overdrive, text="Intensity: shake window", variable=self.intensity_shake_var).grid(row=6, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_overdrive, text="Keep window fixed (no movement)", variable=self.shake_lock_var).grid(row=7, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_overdrive, text="Intensity: flashing arrows", variable=self.intensity_arrows_var).grid(row=8, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_overdrive, text="Overdrive: flash background", variable=self.od_flash_bg_var).grid(row=9, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_overdrive, text="Overdrive: shake window loop", variable=self.od_shake_loop_var).grid(row=10, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_overdrive, text="Overdrive: jiggle buttons", variable=self.od_jiggle_btns_var).grid(row=11, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(tab_overdrive, text="Jiggle style").grid(row=12, column=0, sticky="w", **pad)
        ttk.Combobox(tab_overdrive, textvariable=self.jiggle_style_var, values=("off","nudge","pulse"), state="readonly", width=12).grid(row=12, column=1, sticky="w", **pad)

        # Stage 5 (multi-monitor dim/blackout)
        ttk.Separator(tab_overdrive).grid(row=19, column=0, columnspan=3, sticky="ew", padx=8, pady=(8,6))
        ttk.Checkbutton(tab_overdrive, text="Enable Stage 5 overdrive (dim/blackout)", variable=self.stage5_enabled_var).grid(row=20, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(tab_overdrive, text="Stage 5 after (sec after Stage 4)").grid(row=21, column=0, sticky="w", **pad)
        ttk.Entry(tab_overdrive, textvariable=self.stage5_after_var, width=12).grid(row=21, column=1, sticky="w", **pad)
        ttk.Checkbutton(tab_overdrive, text="Allow clicks through dimmer (no input blocking)", variable=self.stage5_clickthrough_var).grid(row=22, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_overdrive, text="Pulse dimming (fade in/out)", variable=self.stage5_pulse_var).grid(row=23, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(tab_overdrive, text="Max dim alpha (0-1)").grid(row=24, column=0, sticky="w", **pad)
        ttk.Entry(tab_overdrive, textvariable=self.stage5_alpha_var, width=12).grid(row=24, column=1, sticky="w", **pad)
        ttk.Label(tab_overdrive, text="Overlay color (#RRGGBB)").grid(row=25, column=0, sticky="w", **pad)
        ttk.Entry(tab_overdrive, textvariable=self.stage5_color_var, width=12).grid(row=25, column=1, sticky="w", **pad)
        ttk.Label(tab_overdrive, text="Dim engine").grid(row=26, column=0, sticky="w", **pad)
        ttk.Combobox(tab_overdrive, textvariable=self.stage5_engine_var, values=("overlay","gamma"), state="readonly", width=12).grid(row=26, column=1, sticky="w", **pad)
        ttk.Checkbutton(tab_overdrive, text="Slow-dim to black (one-way)", variable=self.stage5_slow_dim_enabled_var).grid(row=27, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(tab_overdrive, text="Slow-dim duration").grid(row=28, column=0, sticky="w", **pad)
        ttk.Entry(tab_overdrive, textvariable=self.stage5_slow_dim_secs_var, width=12).grid(row=28, column=1, sticky="w", **pad)
        ttk.Label(tab_overdrive, text="Hold black after").grid(row=29, column=0, sticky="w", **pad)
        ttk.Entry(tab_overdrive, textvariable=self.stage5_hold_after_var, width=12).grid(row=29, column=1, sticky="w", **pad)

        # Time Info
        ttk.Checkbutton(tab_time, text="Show time info under buttons", variable=self.show_time_info_var).grid(row=0, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(tab_time, text="Time info mode").grid(row=1, column=0, sticky="w", **pad)
        ttk.Combobox(tab_time, textvariable=self.time_mode_var, values=("hour","day","anchor","launch"), state="readonly", width=12).grid(row=1, column=1, sticky="w", **pad)
        add_row_to(tab_time, 2, "Anchor (HH:MM):", self.time_anchor_var)
        ttk.Checkbutton(tab_time, text="12-hour time (AM/PM)", variable=self.time_12h_var).grid(row=3, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_time, text="Show seconds", variable=self.time_secs_var).grid(row=4, column=0, columnspan=3, sticky="w", **pad)
        add_row_to(tab_time, 5, "Refresh interval:", self.time_refresh_var, "ms")
        ttk.Checkbutton(tab_time, text="Show time until current task due", variable=self.time_show_task_left_var).grid(row=6, column=0, columnspan=3, sticky="w", **pad)

        # Tasks
        ttk.Checkbutton(tab_tasks, text="Enable task encouragement panel", variable=self.encourage_var).grid(row=0, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_tasks, text="Hide 'Wasting time' button", variable=self.hide_waste_var).grid(row=1, column=0, columnspan=3, sticky="w", **pad)
        ttk.Separator(tab_tasks).grid(row=2, column=0, columnspan=3, sticky="ew", padx=8, pady=(4,6))
        ttk.Checkbutton(tab_tasks, text="Require pass/fail decision", variable=self.tasks_decision_enabled_var).grid(row=3, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(tab_tasks, text="Evaluation timing").grid(row=4, column=0, sticky="w", **pad)
        ttk.Combobox(tab_tasks, textvariable=self.tasks_eval_mode_var, values=("before","after"), state="readonly", width=12).grid(row=4, column=1, sticky="w", **pad)
        add_row_to(tab_tasks, 5, "Decision window:", self.tasks_decision_window_var, "minutes")
        ttk.Checkbutton(tab_tasks, text="Pressing 'Studying' counts as fail when decision required", variable=self.tasks_study_implies_fail_var).grid(row=6, column=0, columnspan=3, sticky="w", **pad)
        ttk.Separator(tab_tasks).grid(row=7, column=0, columnspan=3, sticky="ew", padx=8, pady=(4,6))
        ttk.Checkbutton(tab_tasks, text="Show task analytics in prompt", variable=self.show_analytics_var).grid(row=8, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_tasks, text="Treat changed tasks as failures", variable=self.change_as_fail_var).grid(row=9, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(tab_tasks, text="Analytics timescale").grid(row=10, column=0, sticky="w", **pad)
        ttk.Combobox(tab_tasks, textvariable=self.tasks_timescale_var, values=("lifetime","today","7d","30d"), state="readonly", width=12).grid(row=10, column=1, sticky="w", **pad)
        ttk.Separator(tab_tasks).grid(row=11, column=0, columnspan=3, sticky="ew", padx=8, pady=(4,6))
        ttk.Checkbutton(tab_tasks, text="Prompt for details on 'Wasting time'", variable=self.waste_prompt_enabled_var).grid(row=12, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_tasks, text="Ask what you're wasting time on", variable=self.waste_prompt_what_var).grid(row=13, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_tasks, text="Ask for consequences too", variable=self.waste_prompt_cons_var).grid(row=14, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_tasks, text="Require an active task to close prompt", variable=self.require_task_var).grid(row=15, column=0, columnspan=3, sticky="w", **pad)

        # Footer buttons
        btns = ttk.Frame(self)
        btns.grid(row=1, column=0, sticky="e", padx=8, pady=(0,8))
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right", padx=6)
        ttk.Button(btns, text="Save", command=self._save).pack(side="right")

        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _safe_int(self, var, default):
        """Safely convert StringVar to int with fallback."""
        try:
            return int((var.get() or str(default)).strip())
        except (ValueError, AttributeError):
            return default

    def _save(self):
        try:
            s = {
                "interval_seconds": max(10, self._safe_int(self.interval_var, 30)),
                "intensify_after_seconds": max(5, self._safe_int(self.intensify_var, 120)),
                "overdrive_after_seconds": max(20, self._safe_int(self.overdrive_var, 300)),
                "max_intensity_level": min(3, max(1, self._safe_int(self.max_intensity_var, 3))),
                "always_on_top": bool(self.topmost_var.get()),
                "center_on_show": bool(self.center_var.get()),

                "anti_habit_enabled": bool(self.anti_var.get()),
                "randomize_buttons": bool(self.rand_btns_var.get()),
                "studying_hold_ms": max(0, self._safe_int(self.hold_ms_var, 600)),

                "force_always_on": bool(self.force_on_var.get()),
                "pause_when_inactive_or_lid_closed": bool(self.pause_var.get()),
                "pause_on_idle": bool(self.pause_on_idle_var.get()),
                "pause_on_lid_closed": bool(self.pause_on_lid_var.get()),
                "pause_on_lock": bool(self.pause_on_lock_var.get()),
                "pause_on_sleep": bool(self.pause_on_sleep_var.get()),
                "inactive_as_sleep_seconds": max(15, self._safe_int(self.idle_secs_var, 300)),
                "pause_poll_interval_seconds": max(2, self._safe_int(self.pause_poll_var, 5)),

                "webhook_url": self.webhook_var.get().strip()
            }
            # Stage 4
            s.update({
                "overdrive_stage4_enabled": bool(self.stage4_enabled_var.get()),
                "overdrive_stage4_after_seconds": max(1, self._safe_int(self.stage4_after_var, 30)),
                "overdrive_stage4_flash_ms": max(20, self._safe_int(self.stage4_rate_var, 100)),
            })
            # Stage 5
            try:
                s5_alpha = float(self.stage5_alpha_var.get())
            except Exception:
                s5_alpha = 0.92
            s5_alpha = max(0.0, min(1.0, s5_alpha))
            s.update({
                "overdrive_stage5_enabled": bool(self.stage5_enabled_var.get()),
                "overdrive_stage5_after_seconds": max(5, self._safe_int(self.stage5_after_var, 60)),
                "overdrive_stage5_dim_pulse": bool(self.stage5_pulse_var.get()),
                "overdrive_stage5_dim_max_alpha": s5_alpha,
                "overdrive_stage5_dim_color": (self.stage5_color_var.get() or "#000000").strip(),
                "overdrive_stage5_click_through": bool(self.stage5_clickthrough_var.get()),
                "overdrive_stage5_hold_after_seconds": max(0, self._safe_int(self.stage5_hold_after_var, 0)),
                "overdrive_stage5_slow_dim_enabled": bool(self.stage5_slow_dim_enabled_var.get()),
                "overdrive_stage5_slow_dim_seconds": max(1, self._safe_int(self.stage5_slow_dim_secs_var, 30)),
                "overdrive_stage5_engine": (self.stage5_engine_var.get() or "overlay").strip().lower() if (self.stage5_engine_var.get() or "overlay").strip().lower() in ("overlay","gamma") else "overlay",
            })
            # Time info
            mode = self.time_mode_var.get().strip().lower()
            if mode not in ("hour","day","anchor","launch"):
                mode = "hour"
            # Sanitize HH:MM
            anc = self.time_anchor_var.get().strip()
            try:
                hh, mm = anc.split(":"); hh = int(hh); mm = int(mm)
                if not (0 <= hh <= 23 and 0 <= mm <= 59):
                    anc = "09:00"
                else:
                    anc = f"{hh:02d}:{mm:02d}"
            except Exception:
                anc = "09:00"
            s.update({
                "show_time_info": bool(self.show_time_info_var.get()),
                "time_info_mode": mode,
                "time_info_anchor_hhmm": anc,
                "time_info_12h": bool(self.time_12h_var.get()),
                "time_info_show_seconds": bool(self.time_secs_var.get()),
                "time_info_refresh_ms": max(250, self._safe_int(self.time_refresh_var, 1000)),
                "time_info_show_task_remaining": bool(self.time_show_task_left_var.get()),
                # New UI / Task settings
                "hide_wasting_button": bool(self.hide_waste_var.get()),
                "wasting_prompt_enabled": bool(self.waste_prompt_enabled_var.get()),
                "wasting_prompt_ask_what": bool(self.waste_prompt_what_var.get()),
                "wasting_prompt_ask_consequences": bool(self.waste_prompt_cons_var.get()),
                "require_active_task": bool(self.require_task_var.get()),
                "encouragement_enabled": bool(self.encourage_var.get()),
                "show_task_analytics": bool(self.show_analytics_var.get()),
                "tasks_change_counts_as_fail": bool(self.change_as_fail_var.get()),
                "tasks_analytics_timescale": str(self.tasks_timescale_var.get()).strip().lower(),
                "tasks_decision_prompt_enabled": bool(self.tasks_decision_enabled_var.get()),
                "tasks_study_implies_fail_on_decision": bool(self.tasks_study_implies_fail_var.get()),
                "tasks_evaluation_mode": str(self.tasks_eval_mode_var.get()).strip().lower(),
                "tasks_decision_window_minutes": max(0, self._safe_int(self.tasks_decision_window_var, 10)),
                # Alert / jiggle
                "disable_jiggling": bool(self.disable_jiggle_var.get()),
                "enable_intensity_pulse": bool(self.intensity_pulse_var.get()),
                "enable_intensity_shake": bool(self.intensity_shake_var.get()),
                "enable_intensity_arrows": bool(self.intensity_arrows_var.get()),
                "shake_lock_position": bool(self.shake_lock_var.get()),
                "enable_overdrive_flash_background": bool(self.od_flash_bg_var.get()),
                "enable_overdrive_shake_loop": bool(self.od_shake_loop_var.get()),
                "enable_overdrive_jiggle_buttons": bool(self.od_jiggle_btns_var.get()),
                "jiggle_style": str(self.jiggle_style_var.get()).strip().lower(),
                # Tray/general
                "follow_cursor_monitor": bool(self.follow_cursor_var.get()),
                "tray_start_stop_enabled": bool(self.tray_start_stop_enabled_var.get()),
                "tray_settings_button_enabled": bool(self.tray_settings_enabled_var.get()),
                "tray_exit_button_enabled": bool(self.tray_exit_enabled_var.get()),
            })
        except ValueError:
            messagebox.showerror("Invalid values", "Please enter whole numbers only.")
            return
        save_settings(s)
        self.on_save(s)
        self.destroy()

# -------------------- Prompt Dialog --------------------

class PromptDialog(tk.Toplevel):
    def __init__(self, master, settings, on_submit, slot_start_dt, taskdb=None, app_ref=None):
        super().__init__(master)
        self.settings = settings
        self.on_submit = on_submit
        self.slot_start_dt = slot_start_dt
        self.taskdb = taskdb
        self.app_ref = app_ref
        self.start_monotonic = time.monotonic()
        self.intensity_level = 0
        self._pulse_dir = 1
        self._pulse_val = 0
        self._shaking = False
        self._arrows_visible = False
        self._overdrive = False
        self._overdrive_stage4 = False
        self._closed = False
        self._hold_start = None
        # Timer registry for cleanup
        self._active_timers = set()
        self._time_lbl = None
        self._info_lbl = None
        self._task_panel = None
        self._task_change_form = None
        self._analytics_lbl = None
        self._task_timer_id = None
        self._action_buttons = []
        self._task_decision_required = False
        self._task_decision_task_id = None

        self.title("Check-in")
        self.configure(bg="#111")
        self.resizable(False, False)
        if self.settings["always_on_top"]:
            self.attributes("-topmost", True)

        # Windows-specific: remove minimize button and start taskbar flashing
        try:
            self._disable_minimize_button()
            self._flash_taskbar_begin()
        except Exception:
            pass

        # Prevent minimize attempts by restoring immediately
        self.bind('<Unmap>', self._prevent_minimize)

        container = tk.Frame(self, bg="#111")
        container.pack(padx=14, pady=14)

        title = tk.Label(container, text="Right now… be honest:", fg="#eaeaea", bg="#111", font=("Segoe UI", 14, "bold"))
        title.pack(anchor="w", pady=(0,8))
        # Ensure clean text in case of encoding hiccups
        try:
            title.configure(text="Right now — be honest:")
        except Exception:
            pass

        self.button_row = tk.Frame(container, bg="#111")
        self.button_row.pack(fill="x")

        self.btn_study = tk.Button(self.button_row, text="Studying", font=("Segoe UI", 16, "bold"),
                                   relief="solid", bd=2, width=14)
        self.btn_waste = None
        if not bool(self.settings.get("hide_wasting_button", False)):
            self.btn_waste = tk.Button(self.button_row, text="Wasting time", font=("Segoe UI", 16, "bold"),
                                       relief="solid", bd=2, width=14, command=self._on_wasting_clicked)

        self.btn_study.bind("<ButtonPress-1>", self._study_hold_start)
        self.btn_study.bind("<ButtonRelease-1>", self._study_hold_end)
        self._action_buttons = [self.btn_study] + ([self.btn_waste] if self.btn_waste is not None else [])

        # Optional time info label below buttons
        try:
            self._time_lbl = tk.Label(container, text="", fg="#9fd", bg="#111", font=("Segoe UI", 10))
            if self.settings.get("show_time_info", False):
                self._time_lbl.pack(pady=(6,0))
                self._start_time_info()
        except Exception:
            self._time_lbl = None

        self._info_lbl = tk.Label(container, text="", fg="#ff9", bg="#111", font=("Segoe UI", 10))
        self._info_lbl.pack(pady=(6,0))

        # Task encouragement panel
        if bool(self.settings.get("encouragement_enabled", True)):
            self._task_panel = tk.Frame(container, bg="#111", highlightthickness=1, highlightbackground="#333")
            self._task_panel.pack(fill="x", pady=(6, 0))
            self._render_task_panel()

        self.arrow_row = tk.Frame(container, bg="#111")
        self.arrow_left = tk.Label(self.arrow_row, text="⬆", font=("Segoe UI Emoji", 24), bg="#111", fg="#111")
        self.arrow_right = tk.Label(self.arrow_row, text="⬆", font=("Segoe UI Emoji", 24), bg="#111", fg="#111")
        self.arrow_left.grid(row=0, column=0, padx=60)
        self.arrow_right.grid(row=0, column=1, padx=60)
        self.arrow_row.pack(pady=(2,0))

        footer = tk.Frame(container, bg="#111")
        footer.pack(fill="x", pady=(8,0))
        settings_link = tk.Label(footer, text="⚙ Settings", fg="#7fb7ff", bg="#111",
                                 cursor="hand2", font=("Segoe UI", 10, "underline"))
        settings_link.pack(side="left")
        try:
            settings_link.configure(text="Settings")
        except Exception:
            pass
        settings_link.bind("<Button-1>", self._open_settings)

        # Task link
        if bool(self.settings.get("encouragement_enabled", True)):
            task_link = tk.Label(footer, text="✎ Task", fg="#7fffb7", bg="#111",
                                 cursor="hand2", font=("Segoe UI", 10, "underline"))
            task_link.pack(side="left", padx=(10,0))
            try:
                task_link.configure(text="Task")
            except Exception:
                pass
            task_link.bind("<Button-1>", self._toggle_task_entry)

        # Analytics at bottom
        if bool(self.settings.get("encouragement_enabled", True)) and bool(self.settings.get("show_task_analytics", True)):
            self._analytics_lbl = tk.Label(container, text="", fg="#aaa", bg="#111", font=("Segoe UI", 10))
            self._analytics_lbl.pack(pady=(6, 0))
            self._refresh_analytics()

        self._place_buttons_random()

        self.update_idletasks()
        if self.settings["center_on_show"]:
            # Center on the user's active monitor (cursor monitor on Windows)
            self._center_on_active_monitor()

        # Use timer registry for cleanup
        self._schedule_timer(self.settings["intensify_after_seconds"] * 1000, self._begin_intensify)
        self._schedule_timer(self.settings["overdrive_after_seconds"] * 1000, self._begin_overdrive)

        self.protocol("WM_DELETE_WINDOW", self._ignore_close)

        # Optionally track cursor monitor and recenter while open
        try:
            if bool(self.settings.get("follow_cursor_monitor", True)):
                self.after(400, self._follow_cursor_center_loop)
        except Exception:
            pass

        # If a task is required and none is set, guide user to create one
        try:
            if bool(self.settings.get("require_active_task", False)) and self.taskdb:
                active = None
                try:
                    active = self.taskdb.get_active()
                except Exception:
                    active = None
                if not active:
                    try:
                        self._info_lbl.config(text="Set a task to proceed.")
                    except Exception:
                        pass
                    try:
                        self._ensure_task_entry_visible()
                    except Exception:
                        pass
        except Exception:
            pass

        # Overdrive stage 5 state (screen dim/blackout overlays)
        self._overdrive_stage5 = False
        self._stage5_overlays = []
        self._stage5_dim_alpha = 0.0
        self._stage5_dim_dir = 1
        self._stage5_dim_timer = None
        self._stage5_start_mono = 0.0
        self._stage5_hold_engaged = False
        self._stage5_engine = 'overlay'  # Default engine, will be set from settings
        # Gamma engine state (Windows only)
        self._gamma_active = False
        self._gamma_hdc = None
        self._gamma_orig = None
        # Magnification engine state (Windows only)
        self._mag_active = False

    def _place_buttons_random(self):
        for w in self.button_row.winfo_children():
            w.grid_forget()
        left_first = True
        if self.settings["anti_habit_enabled"] and self.settings["randomize_buttons"] and self.btn_waste is not None:
            left_first = bool(random.getrandbits(1))
        pad_l = random.randint(0, 12) if self.settings["randomize_buttons"] else 6
        pad_r = random.randint(0, 12) if self.settings["randomize_buttons"] else 6
        pad_y = random.randint(0, 6) if self.settings["randomize_buttons"] else 4

        if self.btn_waste is None:
            pad = max(pad_l, pad_r)
            self.btn_study.grid(row=0, column=0, padx=(pad, pad), pady=pad_y)
        else:
            if left_first:
                self.btn_study.grid(row=0, column=0, padx=(pad_l, 6), pady=pad_y)
                self.btn_waste.grid(row=0, column=1, padx=(6, pad_r), pady=pad_y)
            else:
                self.btn_waste.grid(row=0, column=0, padx=(pad_l, 6), pady=pad_y)
                self.btn_study.grid(row=0, column=1, padx=(6, pad_r), pady=pad_y)

    # --- Window placement helpers ---
    def _get_active_monitor_workarea(self):
        """Return (l, t, r, b) work area for the monitor currently active.
        On Windows, picks the monitor under the cursor. Falls back to the
        primary screen bounds elsewhere.
        """
        try:
            if platform.system().lower() == "windows":
                user32 = ctypes.windll.user32
                # Structures
                class POINT(ctypes.Structure):
                    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
                class RECT(ctypes.Structure):
                    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
                class MONITORINFO(ctypes.Structure):
                    _fields_ = [("cbSize", ctypes.c_uint), ("rcMonitor", RECT), ("rcWork", RECT), ("dwFlags", ctypes.c_uint)]

                pt = POINT()
                if not user32.GetCursorPos(ctypes.byref(pt)):
                    raise RuntimeError("GetCursorPos failed")
                MONITOR_DEFAULTTONEAREST = 2
                hmon = user32.MonitorFromPoint(pt, MONITOR_DEFAULTTONEAREST)
                if not hmon:
                    raise RuntimeError("MonitorFromPoint failed")
                mi = MONITORINFO()
                mi.cbSize = ctypes.sizeof(MONITORINFO)
                if not user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                    raise RuntimeError("GetMonitorInfoW failed")
                return (mi.rcWork.left, mi.rcWork.top, mi.rcWork.right, mi.rcWork.bottom)
        except Exception:
            pass
        # Fallback: primary screen
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        return (0, 0, int(sw), int(sh))

    def _get_own_monitor_workarea(self):
        """Return (l, t, r, b) work area for the monitor containing this window.
        On Windows uses the window center to pick a monitor; fall back to
        the primary screen elsewhere.
        """
        try:
            if platform.system().lower() == "windows":
                user32 = ctypes.windll.user32
                # Structures
                class POINT(ctypes.Structure):
                    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
                class RECT(ctypes.Structure):
                    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
                class MONITORINFO(ctypes.Structure):
                    _fields_ = [("cbSize", ctypes.c_uint), ("rcMonitor", RECT), ("rcWork", RECT), ("dwFlags", ctypes.c_uint)]
                # Get current window rect
                rc = RECT()
                hwnd = wintypes.HWND(self.winfo_id())
                if not user32.GetWindowRect(hwnd, ctypes.byref(rc)):
                    raise RuntimeError("GetWindowRect failed")
                cx = int((rc.left + rc.right) / 2)
                cy = int((rc.top + rc.bottom) / 2)
                MONITOR_DEFAULTTONEAREST = 2
                hmon = user32.MonitorFromPoint(POINT(cx, cy), MONITOR_DEFAULTTONEAREST)
                if not hmon:
                    raise RuntimeError("MonitorFromPoint failed")
                mi = MONITORINFO()
                mi.cbSize = ctypes.sizeof(MONITORINFO)
                if not user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                    raise RuntimeError("GetMonitorInfoW failed")
                return (mi.rcWork.left, mi.rcWork.top, mi.rcWork.right, mi.rcWork.bottom)
        except Exception:
            pass
        # Fallback: primary screen
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        return (0, 0, int(sw), int(sh))

    def _clamp_to_rect(self, x, y, w, h, rect):
        l, t, r, b = rect
        min_x, max_x = l, max(l, r - w)
        min_y, max_y = t, max(t, b - h)
        cx = min(max(int(x), min_x), max_x)
        cy = min(max(int(y), min_y), max_y)
        return cx, cy

    def _center_on_active_monitor(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        l, t, r, b = self._get_active_monitor_workarea()
        avail_w, avail_h = (r - l), (b - t)
        x = l + int((avail_w - w) / 2)
        y = t + int((avail_h - h) / 3)
        x, y = self._clamp_to_rect(x, y, w, h, (l, t, r, b))
        self.geometry(f"+{x}+{y}")

    def _follow_cursor_center_loop(self):
        if self._closed:
            return
        try:
            # Compare monitor rectangles; if cursor monitor != window monitor, recenter
            l1, t1, r1, b1 = self._get_active_monitor_workarea()
            l2, t2, r2, b2 = self._get_own_monitor_workarea()
            if (l1, t1, r1, b1) != (l2, t2, r2, b2):
                self._center_on_active_monitor()
        except Exception:
            pass
        finally:
            try:
                self.after(400, self._follow_cursor_center_loop)
            except Exception:
                pass

    def ensure_on_screen(self):
        try:
            self.update_idletasks()
            w, h = self.winfo_width(), self.winfo_height()
            x, y = self.winfo_x(), self.winfo_y()
            rect = self._get_own_monitor_workarea()
            cx, cy = self._clamp_to_rect(x, y, w, h, rect)
            if (cx, cy) != (x, y):
                self.geometry(f"+{cx}+{cy}")
        except Exception:
            pass

    # --- Time info helpers ---
    def _format_now(self):
        now = datetime.now()
        show_secs = bool(self.settings.get("time_info_show_seconds", False))
        use_12h = bool(self.settings.get("time_info_12h", False))
        if use_12h:
            fmt = "%I:%M:%S %p" if show_secs else "%I:%M %p"
            s = now.strftime(fmt).lstrip("0")
        else:
            fmt = "%H:%M:%S" if show_secs else "%H:%M"
            s = now.strftime(fmt)
        return now, s

    def _minutes_passed(self, now):
        mode = str(self.settings.get("time_info_mode", "hour")).lower().strip()
        if mode == "day":
            return now.hour * 60 + now.minute
        if mode == "anchor":
            anc = str(self.settings.get("time_info_anchor_hhmm", "09:00"))
            try:
                hh, mm = anc.split(":"); hh = int(hh); mm = int(mm)
                anchor = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
                if now < anchor:
                    # use yesterday's anchor as most recent
                    anchor = anchor - timedelta(days=1)
                delta = now - anchor
                return max(0, int(delta.total_seconds() // 60))
            except Exception:
                return now.hour * 60 + now.minute
        if mode == "launch":
            try:
                if self.app_ref is not None and hasattr(self.app_ref, "_start_wall"):
                    delta = now - getattr(self.app_ref, "_start_wall")
                    return max(0, int(delta.total_seconds() // 60))
            except Exception:
                pass
            return now.minute
        # default hour mode
        return now.minute

    def _tick_time_info(self):
        if self._closed or self._time_lbl is None:
            return
        try:
            if not self.settings.get("show_time_info", False):
                if self._time_lbl.winfo_manager():
                    try:
                        self._time_lbl.pack_forget()
                    except Exception:
                        pass
            else:
                if not self._time_lbl.winfo_manager():
                    try:
                        self._time_lbl.pack(pady=(6,0))
                    except Exception:
                        pass
                now, cur = self._format_now()
                mins = self._minutes_passed(now)
                mode = str(self.settings.get("time_info_mode", "hour")).lower().strip()
                extra = ""
                if mode == "anchor":
                    extra = f" since {self.settings.get('time_info_anchor_hhmm','09:00')}"
                elif mode == "launch":
                    extra = " since launch"
                # Optional task remaining
                task_left_txt = ""
                try:
                    if bool(self.settings.get("time_info_show_task_remaining", False)) and self.taskdb:
                        active = self.taskdb.get_active()
                        due_iso = active.get("due_utc") if active else None
                        if due_iso:
                            due_dt = datetime.fromisoformat(due_iso)
                            now_utc = datetime.now(timezone.utc)
                            rem = int((due_dt - now_utc).total_seconds())
                            if rem > 0:
                                mm, ss = divmod(rem, 60)
                                hh, mm = divmod(mm, 60)
                                if hh:
                                    task_left_txt = f" | task left {hh}h{mm:02d}m"
                                else:
                                    task_left_txt = f" | task left {mm}m{ss:02d}s"
                except Exception:
                    pass
                self._time_lbl.config(text=f"{mins} minutes passed{extra} | {cur}{task_left_txt}")
        except Exception:
            pass
        finally:
            try:
                refresh = int(self.settings.get("time_info_refresh_ms", 1000))
            except Exception:
                refresh = 1000
            self.after(refresh, self._tick_time_info)

    def _start_time_info(self):
        # begin periodic updates
        self._tick_time_info()

    # Anti-habit: press-and-hold for Studying
    def _study_hold_start(self, _evt):
        if not self.settings["anti_habit_enabled"]:
            self._finish("Studying"); return
        self._hold_start = time.monotonic()
        try:
            self._info_lbl.config(text="Hold to confirm you're actively studying…")
        except Exception:
            pass
        self._info_lbl.config(text="Hold to confirm you’re actively studying…")

    def _study_hold_end(self, _evt):
        if not self.settings["anti_habit_enabled"]:
            self._finish("Studying"); return
        if self._hold_start is None:
            return
        held_ms = int((time.monotonic() - self._hold_start) * 1000)
        self._hold_start = None
        need = int(self.settings["studying_hold_ms"])
        if held_ms >= need:
            self._finish("Studying")
        else:
            # Inform user to hold longer with clean text
            try:
                self._info_lbl.config(text=f"Too quick ({held_ms}ms). Hold for at least {need}ms.")
            except Exception:
                pass
            # Skip legacy text below (unreachable)
            return
            # Ensure readable text (avoid mojibake)
            try:
                self._info_lbl.config(text=f"Too quick ({held_ms}ms). Hold for ≥ {need}ms.")
            except Exception:
                pass
            self._info_lbl.config(text=f"Too quick ({held_ms}ms). Hold for ≥ {need}ms.")

    def _on_wasting_clicked(self):
        try:
            if not bool(self.settings.get("wasting_prompt_enabled", False)):
                self._finish("Wasting time")
                return
        except Exception:
            self._finish("Wasting time")
            return
        # Show prompt dialog to capture reflection
        try:
            ask_cons = bool(self.settings.get("wasting_prompt_ask_consequences", True))
        except Exception:
            ask_cons = True
        try:
            ask_what = bool(self.settings.get("wasting_prompt_ask_what", True))
        except Exception:
            ask_what = True
        def _cb(payload):
            try:
                what = (payload or {}).get("what", "").strip()
                cons = (payload or {}).get("consequences", "").strip()
                active = None
                if self.taskdb:
                    try:
                        active = self.taskdb.get_active()
                    except Exception:
                        active = None
                # Persist to DB if available
                try:
                    if self.taskdb:
                        self.taskdb.record_waste_event(what=what, consequences=cons, active_task_id=(active.get("id") if active else None))
                except Exception:
                    log_exception("waste prompt: DB record failed")
                # Also record to CSV for quick export
                try:
                    latency_ms = int((time.monotonic() - self.start_monotonic) * 1000)
                    append_waste_log(slot_start_dt=self.slot_start_dt, latency_ms=latency_ms, what=what, consequences=cons, active_task=active)
                except Exception:
                    log_exception("waste prompt: CSV append failed")
            finally:
                self._finish("Wasting time")
        def _on_cancel():
            # Ensure _finish is called even when dialog is canceled
            self._finish("Wasting time")
        WastePromptDialog(self, ask_what=ask_what, ask_consequences=ask_cons, on_submit=_cb, on_cancel=_on_cancel)

    # Escalation
    def _begin_intensify(self):
        if self._closed: return
        try: self.lift(); self.focus_force()
        except Exception: pass
        # Nudge the taskbar to flash for attention (Windows)
        try: self._flash_taskbar_begin()
        except Exception: pass
        self._step_intensity()

    def _step_intensity(self):
        if self._closed: return
        if self.intensity_level < self.settings["max_intensity_level"]:
            self.intensity_level += 1
        if self.intensity_level >= 1 and self.settings.get("enable_intensity_pulse", True):
            self._pulse_buttons()
        if (self.intensity_level >= 2 and not self._shaking and
            self.settings.get("enable_intensity_shake", True) and not self.settings.get("disable_jiggling", False)):
            self._shaking = True
            self._shake_window(times=12, pixels=10, delay=18)
        if (self.intensity_level >= 3 and not self._arrows_visible and
            self.settings.get("enable_intensity_arrows", True)):
            self._arrows_visible = True
            self._flash_arrows()
        elif self.intensity_level < 3:
            # Reset arrow visibility when intensity drops
            self._arrows_visible = False
        if self.intensity_level < self.settings["max_intensity_level"]:
            self.after(1800, self._step_intensity)

    def _begin_overdrive(self):
        if self._closed: return
        self._overdrive = True
        try: self._flash_taskbar_begin()
        except Exception: pass
        if self.settings.get("enable_overdrive_flash_background", True):
            self._flash_background()
        if self.settings.get("enable_overdrive_shake_loop", True) and not self.settings.get("disable_jiggling", False):
            self._shake_loop(amplitude=18, delay=14)
        if self.settings.get("enable_overdrive_jiggle_buttons", True) and not self.settings.get("disable_jiggling", False):
            self._jiggle_buttons()
        self._info_lbl.config(text="You missed the minute—decide now. (Logged as late once you choose.)")
        # Ensure readable text (avoid mojibake)
        try:
            self._info_lbl.config(text="You missed the minute — decide now. (Will log as late once you choose.)")
        except Exception:
            pass
        # Escalate to stage 4 if enabled
        if self.settings.get("overdrive_stage4_enabled", True):
            delay4 = int(self.settings.get("overdrive_stage4_after_seconds", 12)) * 1000
            self.after(delay4, self._begin_overdrive_stage4)
        # Schedule overdrive Stage 5 (multi-monitor blackout/dim) after Stage 4 + configured delay
        if self.settings.get("overdrive_stage5_enabled", True):
            try:
                s4 = int(self.settings.get("overdrive_stage4_after_seconds", 12)) if self.settings.get("overdrive_stage4_enabled", True) else 0
            except Exception:
                s4 = 0
            try:
                s5 = int(self.settings.get("overdrive_stage5_after_seconds", 60))
            except Exception:
                s5 = 60
            self.after(max(0, (s4 + s5) * 1000), self._begin_overdrive_stage5)

    # Visual helpers
    def _pulse_buttons(self):
        if self._closed: return
        self._pulse_val += self._pulse_dir * 22
        if self._pulse_val > 200: self._pulse_dir = -1
        if self._pulse_val < 30:  self._pulse_dir = 1
        v = self._pulse_val
        g = max(0, min(255, 50 + v))
        col = f"#{255:02x}{g:02x}{g:02x}"
        for b in self._action_buttons:
            try:
                b.configure(highlightthickness=0, bg=col, activebackground=col)
            except Exception:
                pass
        self.after(70, self._pulse_buttons)

    def _shake_window(self, times=10, pixels=10, delay=20):
        if self._closed: return
        try:
            x0, y0 = self.winfo_x(), self.winfo_y()
            w, h = self.winfo_width(), self.winfo_height()
            rect = self._get_own_monitor_workarea()
        except Exception:
            self._shaking = False; return
        def do(n):
            if self._closed: return
            if n <= 0:
                # Reset exactly to original position (also clamped)
                cx, cy = self._clamp_to_rect(x0, y0, w, h, rect)
                self.geometry(f"+{cx}+{cy}")
                self._shaking = False; return
            if self.settings.get("shake_lock_position", True):
                # Do not move the window; simulate time passing only
                self.after(delay, lambda: do(n-1))
                return
            dx = pixels if (n % 2 == 0) else -pixels
            nx, ny = x0 + dx, y0
            nx, ny = self._clamp_to_rect(nx, ny, w, h, rect)
            self.geometry(f"+{nx}+{ny}")
            self.after(delay, lambda: do(n-1))
        do(times)

    def _flash_arrows(self):
        if self._closed: return
        current = self.arrow_left.cget("fg")
        new_fg = "#ff4d4d" if current == "#111" else "#111"
        self.arrow_left.config(fg=new_fg)
        self.arrow_right.config(fg=new_fg)
        DEFAULT_ARROW_FONT_SIZE = 24
        fsize = self.arrow_left.cget("font").split()[-1]
        try: fsize = int(fsize)
        except (ValueError, TypeError): fsize = DEFAULT_ARROW_FONT_SIZE
        fsize = 28 if new_fg == "#ff4d4d" else 22
        self.arrow_left.config(font=("Segoe UI Emoji", fsize))
        self.arrow_right.config(font=("Segoe UI Emoji", fsize))
        self.after(280, self._flash_arrows)

    def _flash_background(self):
        if self._closed or not self._overdrive or self._overdrive_stage4: return
        curr = self.cget("bg")
        nextc = "#300" if curr == "#111" else "#111"
        self.configure(bg=nextc)
        for f in (self.button_row, self.arrow_row):
            f.config(bg=nextc)
        self.after(120, self._flash_background)

    def _begin_overdrive_stage4(self):
        if self._closed or not self._overdrive: return
        self._overdrive_stage4 = True
        # Start ultra-fast red flashing
        self._flash_stage4()

    # ---- Stage 5: overlay blackout/dim across all monitors ----
    def _begin_overdrive_stage5(self):
        if self._closed or not self._overdrive or self._overdrive_stage5:
            return
        self._overdrive_stage5 = True
        try:
            get_logger().info("overdrive stage5: begin")
        except Exception:
            pass
        # If configured max alpha is zero or negative, skip creating overlays entirely
        try:
            _max_a_probe = float(self.settings.get("overdrive_stage5_dim_max_alpha", 0.92))
        except Exception:
            _max_a_probe = 0.92
        if _max_a_probe <= 0.0:
            try:
                get_logger().warning("overdrive stage5: skipped (max alpha <= 0)")
            except Exception:
                pass
            self._overdrive_stage5 = False
            return
        # Decide engine: overlay (default) or gamma/magnifier (Windows only)
        engine = str(self.settings.get("overdrive_stage5_engine", "overlay")).strip().lower()
        if engine not in ("overlay","gamma"):
            engine = "overlay"
        # Prefer magnification (color effect) on Windows for reliable click-through
        try:
            if platform.system().lower() == 'windows' and bool(self.settings.get('overdrive_stage5_click_through', True)):
                engine = 'mag'
        except Exception:
            pass
        self._stage5_engine = engine

        if engine == "mag" and platform.system().lower() == "windows":
            try:
                self._mag_prepare()
            except Exception:
                log_exception("stage5: magnifier prepare failed; falling back to gamma")
                self._stage5_engine = "gamma"
        if self._stage5_engine == "gamma" and platform.system().lower() == "windows":
            # Prepare gamma engine; no overlays created
            try:
                self._gamma_prepare()
            except Exception:
                log_exception("stage5: gamma prepare failed; falling back to overlay")
                self._stage5_engine = "overlay"

        if self._stage5_engine == "overlay":
            try:
                self._create_stage5_overlays()
            except Exception:
                log_exception("stage5 overlay creation failed")
        # Start dimming loop
        self._stage5_dim_alpha = 0.0
        self._stage5_dim_dir = 1
        try:
            self._stage5_start_mono = time.monotonic()
        except Exception:
            self._stage5_start_mono = 0.0
        self._stage5_hold_engaged = False
        self._stage5_dim_tick()

    # ---- Gamma engine (Windows) ----
    def _gamma_prepare(self):
        if platform.system().lower() != 'windows':
            return
        gdi32 = ctypes.windll.gdi32
        user32 = ctypes.windll.user32
        class GAMMARAMP(ctypes.Structure):
            _fields_ = [("Red", ctypes.c_ushort * 256),
                        ("Green", ctypes.c_ushort * 256),
                        ("Blue", ctypes.c_ushort * 256)]
        self._GAMMARAMP = GAMMARAMP
        # Use screen DC (primary). This dims the built-in panel (typical laptop).
        hdc = user32.GetDC(None)
        if not hdc:
            raise RuntimeError("GetDC(None) failed")
        try:
            orig = GAMMARAMP()
            ok = gdi32.GetDeviceGammaRamp(hdc, ctypes.byref(orig))
            if not ok:
                # Some drivers don't support Get; still proceed with a generated linear ramp
                for i in range(256):
                    v = int(min(65535, max(0, i * 257)))
                    orig.Red[i] = v; orig.Green[i] = v; orig.Blue[i] = v
            self._gamma_hdc = hdc
            self._gamma_orig = orig
            self._gamma_active = True
        except Exception:
            # Clean up HDC if anything fails after GetDC
            try:
                user32.ReleaseDC(None, hdc)
            except Exception:
                pass
            raise

    def _gamma_apply_level(self, brightness: float):
        # brightness: 1.0 = normal, 0.0 = black
        if not self._gamma_active or platform.system().lower() != 'windows':
            return
        try:
            b = max(0.0, min(1.0, float(brightness)))
        except Exception:
            b = 1.0
        gdi32 = ctypes.windll.gdi32
        class GAMMARAMP(ctypes.Structure):
            _fields_ = [("Red", ctypes.c_ushort * 256),
                        ("Green", ctypes.c_ushort * 256),
                        ("Blue", ctypes.c_ushort * 256)]
        ramp = GAMMARAMP()
        # Build a simple linear ramp scaled by brightness
        for i in range(256):
            v = int(min(65535, max(0, round(i * 257 * b))))
            ramp.Red[i] = v
            ramp.Green[i] = v
            ramp.Blue[i] = v
        gdi32.SetDeviceGammaRamp(self._gamma_hdc, ctypes.byref(ramp))

    def _gamma_restore(self):
        if not self._gamma_active or platform.system().lower() != 'windows':
            return
        try:
            gdi32 = ctypes.windll.gdi32
            user32 = ctypes.windll.user32
            if self._gamma_hdc and self._gamma_orig:
                gdi32.SetDeviceGammaRamp(self._gamma_hdc, ctypes.byref(self._gamma_orig))
            if self._gamma_hdc:
                user32.ReleaseDC(None, self._gamma_hdc)
        except Exception:
            pass
        finally:
            self._gamma_active = False
            self._gamma_hdc = None
            self._gamma_orig = None

    # ---- Magnification color-effect engine (Windows) ----
    def _mag_prepare(self):
        if platform.system().lower() != 'windows':
            return
        # Load Magnification API
        try:
            self._magnification = ctypes.windll.magnification
        except Exception as e:
            raise RuntimeError("Magnification API not available") from e
        if not self._magnification.MagInitialize():
            raise RuntimeError("MagInitialize failed")
        try:
            # Ensure identity first
            class MAGCOLOREFFECT(ctypes.Structure):
                _fields_ = [("transform", ctypes.c_float * 25)]
            self._MAGCOLOREFFECT = MAGCOLOREFFECT
            ident = MAGCOLOREFFECT()
            mat = ident.transform
            for i in range(25):
                mat[i] = 0.0
            mat[0] = mat[6] = mat[12] = 1.0
            mat[18] = 1.0  # alpha
            mat[24] = 1.0
            # Best effort; ignore failure
            try:
                self._magnification.MagSetFullscreenColorEffect(ctypes.byref(ident))
            except Exception:
                pass
            self._mag_active = True
        except Exception:
            # Clean up if anything fails after MagInitialize
            try:
                self._magnification.MagUninitialize()
            except Exception:
                pass
            raise

    def _mag_apply_level(self, brightness: float):
        if not self._mag_active or platform.system().lower() != 'windows':
            return
        try:
            b = max(0.0, min(1.0, float(brightness)))
        except Exception:
            b = 1.0
        MAGCOLOREFFECT = self._MAGCOLOREFFECT
        eff = MAGCOLOREFFECT()
        mat = eff.transform
        for i in range(25):
            mat[i] = 0.0
        # Scale RGB by b; keep alpha 1
        mat[0] = b
        mat[6] = b
        mat[12] = b
        mat[18] = 1.0
        mat[24] = 1.0
        self._magnification.MagSetFullscreenColorEffect(ctypes.byref(eff))

    def _mag_restore(self):
        if not self._mag_active or platform.system().lower() != 'windows':
            return
        try:
            MAGCOLOREFFECT = self._MAGCOLOREFFECT
            eff = MAGCOLOREFFECT()
            mat = eff.transform
            for i in range(25):
                mat[i] = 0.0
            mat[0] = mat[6] = mat[12] = 1.0
            mat[18] = 1.0
            mat[24] = 1.0
            self._magnification.MagSetFullscreenColorEffect(ctypes.byref(eff))
        except Exception:
            pass
        try:
            self._magnification.MagUninitialize()
        except Exception:
            pass
        self._mag_active = False

    def _get_virtual_screen_rect(self):
        # Return (x, y, w, h) covering all monitors (Windows) or primary screen fallback
        try:
            if platform.system().lower() == "windows":
                user32 = ctypes.windll.user32
                SM_XVIRTUALSCREEN = 76
                SM_YVIRTUALSCREEN = 77
                SM_CXVIRTUALSCREEN = 78
                SM_CYVIRTUALSCREEN = 79
                x = int(user32.GetSystemMetrics(SM_XVIRTUALSCREEN))
                y = int(user32.GetSystemMetrics(SM_YVIRTUALSCREEN))
                w = int(user32.GetSystemMetrics(SM_CXVIRTUALSCREEN))
                h = int(user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))
                if w > 0 and h > 0:
                    return (x, y, w, h)
        except Exception:
            pass
        # Fallback to single screen
        try:
            w = int(self.winfo_screenwidth())
            h = int(self.winfo_screenheight())
            return (0, 0, w, h)
        except Exception:
            return (0, 0, 1920, 1080)

    def _create_stage5_overlays(self):
        # Use a single virtual-screen overlay to cover all monitors
        x, y, w, h = self._get_virtual_screen_rect()
        try:
            get_logger().info("overdrive stage5: overlay rect x=%s y=%s w=%s h=%s", x, y, w, h)
        except Exception:
            pass
        color = str(self.settings.get("overdrive_stage5_dim_color", "#000000") or "#000000")
        click_through = bool(self.settings.get('overdrive_stage5_click_through', True))
        if platform.system().lower() == 'windows' and click_through:
            # Robust native click-through overlay for Windows 10/11
            try:
                ov_native = _WinClickThroughOverlay(x, y, w, h, color_hex=color)
                self._stage5_overlays = [ov_native]
                try:
                    self.lift(); self.focus_force()
                except Exception:
                    pass
                return
            except Exception:
                log_exception("stage5: native overlay failed; falling back to Tk overlay")
        # Fallback: Tk overlay
        ov = tk.Toplevel(self)
        ov.withdraw()
        try: ov.overrideredirect(True)
        except Exception: pass
        try: ov.attributes('-topmost', True)
        except Exception: pass
        try: ov.configure(bg=color)
        except Exception: pass
        try: ov.geometry(f"{w}x{h}+{x}+{y}")
        except Exception: pass
        try: ov.attributes('-alpha', 0.0)
        except Exception: pass
        try: ov.deiconify()
        except Exception: pass
        try:
            if platform.system().lower() == 'windows' and click_through:
                ov.update_idletasks()
                hwnd = wintypes.HWND(ov.winfo_id())
                _enable_click_through_windows(hwnd)
                _install_httransparent_wndproc(hwnd, owner_widget=ov)
        except Exception:
            pass
        self._stage5_overlays = [ov]
        try:
            self.lift(); self.focus_force()
        except Exception:
            pass

    def _stage5_dim_tick(self):
        if self._closed or not self._overdrive_stage5:
            return
        try:
            max_a = float(self.settings.get("overdrive_stage5_dim_max_alpha", 0.92))
        except Exception:
            max_a = 0.92
        slow_enabled = bool(self.settings.get("overdrive_stage5_slow_dim_enabled", False))
        try:
            slow_secs = int(self.settings.get("overdrive_stage5_slow_dim_seconds", 30))
        except Exception:
            slow_secs = 30
        pulse = bool(self.settings.get("overdrive_stage5_dim_pulse", True))
        try:
            hold_after = int(self.settings.get("overdrive_stage5_hold_after_seconds", 0))
        except Exception:
            hold_after = 0

        # Determine target alpha
        a = self._stage5_dim_alpha
        now_mono = time.monotonic()
        if slow_enabled:
            # One-way slow dim to black
            if slow_secs <= 0:
                a = max_a
            else:
                elapsed = max(0.0, now_mono - (self._stage5_start_mono or now_mono))
                # Prevent division by zero
                if slow_secs > 0.001:
                    prog = max(0.0, min(1.0, elapsed / float(slow_secs)))
                else:
                    prog = 1.0
                a = max_a * prog
        else:
            # Pulse fade in/out
            step = 0.05
            a = self._stage5_dim_alpha + (step * self._stage5_dim_dir)
            if a >= max_a:
                a = max_a
                if pulse:
                    self._stage5_dim_dir = -1
            if a <= 0.0:
                a = 0.0
                if pulse:
                    self._stage5_dim_dir = 1

        # Engage final hold if configured
        if (not self._stage5_hold_engaged) and hold_after > 0:
            try:
                if (now_mono - (self._stage5_start_mono or now_mono)) >= hold_after:
                    self._stage5_hold_engaged = True
                    a = max_a
            except Exception:
                pass

        self._stage5_dim_alpha = a

        # Apply engine output
        eng = getattr(self, '_stage5_engine', 'overlay')
        if eng == 'mag' and platform.system().lower() == 'windows':
            # Map overlay alpha to brightness via magnification color matrix
            self._mag_apply_level(1.0 - a)
        elif eng == 'gamma' and platform.system().lower() == 'windows':
            # Map overlay alpha to brightness (1.0 = normal, 0.0 = black)
            self._gamma_apply_level(1.0 - a)
        else:
            click_through = bool(self.settings.get('overdrive_stage5_click_through', True))
            for ov in list(self._stage5_overlays or []):
                try:
                    if hasattr(ov, 'set_alpha') and callable(getattr(ov, 'set_alpha')):
                        ov.set_alpha(a)
                    else:
                        ov.attributes('-alpha', a)
                        # Re-assert click-through on Tk overlay in case Tk reset styles
                        if click_through and platform.system().lower() == 'windows':
                            try: ov.update_idletasks()
                            except Exception: pass
                            hwnd = wintypes.HWND(ov.winfo_id())
                            _enable_click_through_windows(hwnd)
                except Exception:
                    pass
        # Keep prompt above overlays
        if getattr(self, '_stage5_engine', 'overlay') == 'overlay':
            try:
                self.lift()
            except Exception:
                pass
        # Schedule next tick unless we're holding final black
        if self._stage5_hold_engaged and slow_enabled:
            # In slow-dim mode, once held at max we can stop ticking
            self._stage5_dim_timer = None
            return
        if self._stage5_hold_engaged and not slow_enabled and not pulse:
            # If we weren't pulsing anyway, stop
            self._stage5_dim_timer = None
            return
        try:
            # Use 500ms for better performance while maintaining smooth animation
            self._stage5_dim_timer = self.after(500, self._stage5_dim_tick)
        except Exception:
            self._stage5_dim_timer = None

    def _destroy_stage5_overlays(self):
        try:
            if self._stage5_dim_timer is not None:
                try:
                    self.after_cancel(self._stage5_dim_timer)
                    # Only clear timer ID if cancellation succeeded
                    self._stage5_dim_timer = None
                except Exception:
                    # If cancellation failed, log but still clear to prevent double-cancel
                    try:
                        get_logger().warning("Failed to cancel stage5 dim timer")
                    except Exception:
                        pass
                    self._stage5_dim_timer = None
        except Exception:
            pass
        # Restore gamma engine if used
        try:
            if getattr(self, '_stage5_engine', 'overlay') == 'gamma':
                self._gamma_restore()
        except Exception:
            pass
        # Restore magnification engine if used
        try:
            if getattr(self, '_stage5_engine', 'overlay') == 'mag':
                self._mag_restore()
        except Exception:
            pass
        try:
            for ov in list(self._stage5_overlays or []):
                # Restore original wndproc if we subclassed for click-through
                try:
                    old = getattr(ov, "_ct_click_oldproc", None)
                    setter = getattr(ov, "_ct_click_setter", None)
                    if old and setter:
                        try:
                            setter(wintypes.HWND(ov.winfo_id()), GWL_WNDPROC, ctypes.c_void_p(old))
                        except Exception:
                            pass
                except Exception:
                    pass
                try:
                    ov.destroy()
                except Exception:
                    pass
        finally:
            self._stage5_overlays = []
        try:
            get_logger().info("overdrive stage5: destroyed overlays")
        except Exception:
            pass

    def _flash_stage4(self):
        if self._closed or not self._overdrive_stage4: return
        curr = self.cget("bg")
        nextc = "#b00" if curr != "#b00" else "#111"
        self.configure(bg=nextc)
        for f in (self.button_row, self.arrow_row):
            f.config(bg=nextc)
        # Accent buttons as well for consistent alerting
        try:
            for b in self._action_buttons:
                b.configure(bg=("#ff4d4d" if nextc == "#b00" else "#333"), activebackground=("#ff4d4d" if nextc == "#b00" else "#333"))
        except Exception:
            pass
        rate = max(20, int(self.settings.get("overdrive_stage4_flash_ms", 60)))
        self.after(rate, self._flash_stage4)

    def _shake_loop(self, amplitude=16, delay=14):
        if self._closed or not self._overdrive: return
        self._shake_window(times=8, pixels=amplitude, delay=delay)
        self.after(220, lambda: self._shake_loop(amplitude, delay))

    def _jiggle_buttons(self):
        if self._closed or not self._overdrive: return
        style = str(self.settings.get("jiggle_style", "nudge"))
        if style == "off":
            return
        if style == "nudge":
            self._place_buttons_nudge()
        elif style == "pulse":
            fs = random.choice([15,16,17,18])
            try:
                self.btn_study.config(font=("Segoe UI", fs, "bold"))
                if self.btn_waste is not None:
                    self.btn_waste.config(font=("Segoe UI", fs, "bold"))
            except Exception:
                pass
        self.after(1200, self._jiggle_buttons)

    def _place_buttons_nudge(self):
        # Minimal, click-friendly movement
        for w in self.button_row.winfo_children():
            w.grid_forget()
        pad_l = random.randint(0, 2)
        pad_r = random.randint(0, 2)
        pad_y = random.randint(0, 2)
        if self.btn_waste is None:
            pad = max(pad_l, pad_r)
            self.btn_study.grid(row=0, column=0, padx=(pad, pad), pady=pad_y)
        else:
            # Keep order stable to avoid chasing
            self.btn_study.grid(row=0, column=0, padx=(pad_l, 6), pady=pad_y)
            self.btn_waste.grid(row=0, column=1, padx=(6, pad_r), pady=pad_y)

    def _open_settings(self, _evt=None):
        def apply_and_refresh(new_settings):
            self.settings.update(new_settings)
            if self.settings["always_on_top"]:
                self.attributes("-topmost", True)
            else:
                self.attributes("-topmost", False)
            # Apply visibility of 'Wasting time' button immediately
            try:
                want_hide = bool(self.settings.get("hide_wasting_button", False))
                have_btn = (self.btn_waste is not None)
                if want_hide and have_btn:
                    try:
                        self.btn_waste.destroy()
                    except Exception:
                        pass
                    self.btn_waste = None
                    self._action_buttons = [self.btn_study]
                    self._place_buttons_random()
                elif (not want_hide) and (not have_btn):
                    # Create button and place it
                    self.btn_waste = tk.Button(self.button_row, text="Wasting time", font=("Segoe UI", 16, "bold"),
                                               relief="solid", bd=2, width=14, command=self._on_wasting_clicked)
                    self._action_buttons = [self.btn_study, self.btn_waste]
                    self._place_buttons_random()
            except Exception:
                pass
            # Ensure follow-cursor loop is running if enabled
            try:
                if bool(self.settings.get("follow_cursor_monitor", True)):
                    self.after(400, self._follow_cursor_center_loop)
            except Exception:
                pass
        SettingsWindow(self, self.settings, on_save=apply_and_refresh)

    def _ignore_close(self):
        try:
            if bool(self.settings.get("require_active_task", False)) and self.taskdb:
                active = None
                try:
                    active = self.taskdb.get_active()
                except Exception:
                    active = None
                if not active:
                    messagebox.showinfo("Set Task", "You must set a task to continue.")
                    try:
                        self._ensure_task_entry_visible()
                    except Exception:
                        pass
                    return
        except Exception:
            pass
        if self.btn_waste is None:
            messagebox.showinfo("Decide", "Confirm you're Studying (hold if enabled).")
        else:
            messagebox.showinfo("Decide", "Pick one: Studying or Wasting time.")

    def _finish(self, choice):
        if self._closed: return
        # Enforce active task requirement (optional)
        try:
            if bool(self.settings.get("require_active_task", False)) and self.taskdb:
                active = None
                try:
                    active = self.taskdb.get_active()
                except Exception:
                    active = None
                if not active:
                    messagebox.showinfo("Set Task", "You must set a task before continuing.")
                    try:
                        self._ensure_task_entry_visible()
                    except Exception:
                        pass
                    return
        except Exception:
            pass
        # If a task decision is required and user bypasses with Studying/Wasting, count as failure
        try:
            if self._task_decision_required and self.taskdb and self._task_decision_task_id is not None:
                if choice in ("Studying", "Wasting time") and bool(self.settings.get("tasks_study_implies_fail_on_decision", True)):
                    try:
                        self.taskdb.mark_failed(self._task_decision_task_id)
                    except Exception:
                        pass
                    self._task_decision_required = False
                    self._task_decision_task_id = None
                    # Refresh panel/analytics quickly
                    try:
                        self._render_task_panel(); self._refresh_analytics()
                    except Exception:
                        pass
        except Exception:
            pass
        latency_ms = int((time.monotonic() - self.start_monotonic) * 1000)
        try:
            try:
                get_logger().info(
                    "choice=%s latency_ms=%s intensity=%s overdrive=%s",
                    choice, latency_ms, self.intensity_level, self._overdrive
                )
            except Exception:
                pass
            append_log(
                response=choice,
                latency_ms=latency_ms,
                settings=self.settings,
                intensity_level_reached=self.intensity_level + (10 if self._overdrive else 0),
                slot_start_dt=self.slot_start_dt,
                overdrive_deadline_s=int(self.settings["overdrive_after_seconds"])
            )
        except Exception as e:
            try:
                get_logger().error("append_log failed: %s", e)
            except Exception:
                print(f"append_log failed: {e}", file=sys.stderr)
        try:
            self._flash_taskbar_stop()
        except Exception:
            pass
        # Tear down Stage 5 overlays if present
        try:
            self._destroy_stage5_overlays()
        except Exception:
            pass
        # Reset overdrive flags on completion
        self._overdrive_stage4 = False
        self._closed = True
        # Clean up all timers before destroying
        self._cleanup_all_timers()
        self.destroy()

    def _schedule_timer(self, delay_ms, callback):
        """Schedule a timer and track it for cleanup."""
        if self._closed:
            return None
        timer_id = self.after(delay_ms, callback)
        self._active_timers.add(timer_id)
        return timer_id

    def _cancel_timer(self, timer_id):
        """Cancel a specific timer and remove from tracking."""
        if timer_id and timer_id in self._active_timers:
            try:
                self.after_cancel(timer_id)
            except Exception:
                pass
            self._active_timers.discard(timer_id)

    def _cleanup_all_timers(self):
        """Cancel all active timers."""
        for timer_id in list(self._active_timers):
            try:
                self.after_cancel(timer_id)
            except Exception:
                pass
        self._active_timers.clear()

    # ---- Task encouragement UI ----
    def _toggle_task_entry(self, _evt=None):
        if not self.taskdb:
            return
        # Toggle inline task entry frame below panel or time label
        if getattr(self, "_task_entry_frame", None) is not None:
            try:
                self._task_entry_frame.destroy()
            except Exception:
                pass
            self._task_entry_frame = None
            return
        self._task_entry_frame = tk.Frame(self, bg="#111", highlightthickness=1, highlightbackground="#333")
        self._task_entry_frame.pack(padx=14, pady=(6,0), fill="x")
        tk.Label(self._task_entry_frame, text="New Task Title", fg="#ddd", bg="#111").grid(row=0, column=0, sticky="w", padx=8, pady=(6,0))
        title_var = tk.StringVar()
        ttk.Entry(self._task_entry_frame, textvariable=title_var, width=48).grid(row=0, column=1, sticky="we", padx=8, pady=(6,0))
        tk.Label(self._task_entry_frame, text="Why", fg="#bbb", bg="#111").grid(row=1, column=0, sticky="w", padx=8)
        why_var = tk.StringVar(); ttk.Entry(self._task_entry_frame, textvariable=why_var, width=48).grid(row=1, column=1, sticky="we", padx=8)
        tk.Label(self._task_entry_frame, text="Consequences", fg="#bbb", bg="#111").grid(row=2, column=0, sticky="w", padx=8)
        cons_var = tk.StringVar(); ttk.Entry(self._task_entry_frame, textvariable=cons_var, width=48).grid(row=2, column=1, sticky="we", padx=8)
        tk.Label(self._task_entry_frame, text="Expected completion (mins or HH:MM)", fg="#bbb", bg="#111").grid(row=3, column=0, sticky="w", padx=8)
        due_var = tk.StringVar(); ttk.Entry(self._task_entry_frame, textvariable=due_var, width=20).grid(row=3, column=1, sticky="w", padx=8)
        btns = ttk.Frame(self._task_entry_frame); btns.grid(row=4, column=0, columnspan=2, sticky="e", padx=8, pady=(6,8))
        def save_inline():
            data = {
                "title": title_var.get(),
                "why": why_var.get(),
                "consequences": cons_var.get(),
                "due_utc": TaskEntryDialog._parse_due(self=None, txt=due_var.get()) if 'TaskEntryDialog' in globals() else None
            }
            self._on_new_task(data)
            try:
                self._task_entry_frame.destroy()
            except Exception:
                pass
            self._task_entry_frame = None
        def cancel_task_entry():
            try:
                if self._task_entry_frame:
                    self._task_entry_frame.destroy()
            except Exception:
                pass
            finally:
                self._task_entry_frame = None
        ttk.Button(btns, text="Cancel", command=cancel_task_entry).pack(side="right", padx=6)
        ttk.Button(btns, text="Save", command=save_inline).pack(side="right")

    def _ensure_task_entry_visible(self):
        if not self.taskdb:
            return
        try:
            fr = getattr(self, "_task_entry_frame", None)
            exists = bool(fr is not None and int(fr.winfo_exists()) == 1)
        except Exception:
            exists = False
        if not exists:
            try:
                self._toggle_task_entry(None)
            except Exception:
                pass

    def _on_new_task(self, task_data):
        try:
            title = task_data.get("title", "").strip()
            why = task_data.get("why", "").strip()
            cons = task_data.get("consequences", "").strip()
            due_iso = task_data.get("due_utc")
            if not title:
                return
            self.taskdb.start_task(title=title, due_utc=due_iso, why=why, consequences=cons)
            self._render_task_panel()
            self._refresh_analytics()
        except Exception:
            pass

    def _render_task_panel(self):
        if not self._task_panel or not self.taskdb:
            return
        # Preserve open change form while updating the rest
        keep_form = getattr(self, "_task_change_form", None)
        try:
            if keep_form is not None and int(keep_form.winfo_exists()) == 1:
                try:
                    keep_form.pack_forget()
                except Exception:
                    pass
            else:
                keep_form = None
        except Exception:
            keep_form = None
        for w in list(self._task_panel.winfo_children()):
            if keep_form is not None and w == keep_form:
                continue
            try:
                w.destroy()
            except Exception:
                pass
        active = None
        try:
            active = self.taskdb.get_active()
        except Exception:
            active = None
        if not active:
            # Header row with History button even when no active task
            header_row = tk.Frame(self._task_panel, bg="#111")
            header_row.pack(fill="x", padx=8, pady=(6,0))
            hist = tk.Label(header_row, text="History", fg="#7fffb7", bg="#111", cursor="hand2", font=("Segoe UI", 9, "underline"))
            hist.pack(side="right")
            hist.bind("<Button-1>", self._open_task_history)
            # No task message
            lbl = tk.Label(self._task_panel, text="No task set. Click ✎ Task to define one.", fg="#bbb", bg="#111", font=("Segoe UI", 10))
            lbl.pack(anchor="w", padx=8, pady=6)
            return

        # Build active task UI
        title = active.get("title", "")
        why = active.get("why", "")
        cons = active.get("consequences", "")
        due_iso = active.get("due_utc")
        due_txt = "No due time"
        overdue = False
        time_left = ""
        try:
            if due_iso:
                due_dt = datetime.fromisoformat(due_iso)
                local_due = due_dt.astimezone().strftime("%Y-%m-%d %H:%M")
                now = datetime.now(timezone.utc)
                if now > due_dt:
                    overdue = True
                    due_txt = f"Due: {local_due} (LIMIT REACHED)"
                else:
                    rem = due_dt - now
                    mm = int(rem.total_seconds() // 60)
                    ss = int(rem.total_seconds() % 60)
                    due_txt = f"Due: {local_due}"
                    time_left = f"Time left: {mm}m {ss}s"
        except Exception:
            pass

        fg = "#ffb0b0" if overdue else "#cfe9cf"
        # Header row with History button on the right
        header_row = tk.Frame(self._task_panel, bg="#111")
        header_row.pack(fill="x", padx=8, pady=(6,0))
        head = tk.Label(header_row, text=f"Current task: {title}", fg="#eaeaea", bg="#111", font=("Segoe UI", 11, "bold"))
        head.pack(side="left")
        hist = tk.Label(header_row, text="History", fg="#7fffb7", bg="#111", cursor="hand2", font=("Segoe UI", 9, "underline"))
        hist.pack(side="right")
        hist.bind("<Button-1>", self._open_task_history)
        sub = tk.Label(self._task_panel, text=f"Why: {why}", fg="#ddd", bg="#111", font=("Segoe UI", 10))
        sub.pack(anchor="w", padx=8)
        sub2 = tk.Label(self._task_panel, text=f"If not done: {cons}", fg="#ddd", bg="#111", font=("Segoe UI", 10))
        sub2.pack(anchor="w", padx=8)
        due_l = tk.Label(self._task_panel, text=due_txt + (f"  |  {time_left}" if time_left else ""), fg=fg, bg="#111", font=("Segoe UI", 10, "bold" if overdue else ""))
        due_l.pack(anchor="w", padx=8, pady=(0,6))

        # Decision prompt depending on evaluation mode
        self._task_decision_required = False
        self._task_decision_task_id = None
        try:
            window_m = int(self.settings.get("tasks_decision_window_minutes", 10))
        except Exception:
            window_m = 10
        decision_enabled = bool(self.settings.get("tasks_decision_prompt_enabled", True))
        decision_due = False
        eval_mode = str(self.settings.get("tasks_evaluation_mode", "before")).strip().lower()
        try:
            if due_iso:
                due_dt = datetime.fromisoformat(due_iso)
                now = datetime.now(timezone.utc)
                if eval_mode == "before":
                    window_start = due_dt - timedelta(minutes=window_m)
                    if now >= due_dt:
                        # Auto-fail: evaluation window ended at due time
                        try:
                            if active.get("status") == "active":
                                self.taskdb.mark_failed(active.get("id"), timed_out=True)
                                active = self.taskdb.get_active()
                                overdue = True
                        except Exception:
                            pass
                        decision_due = False
                    elif now >= window_start:
                        decision_due = True
                else:  # after
                    window_end = due_dt + timedelta(minutes=window_m)
                    if now < due_dt:
                        decision_due = False
                    elif now >= due_dt and now < window_end:
                        decision_due = True
                    else:
                        # Auto-fail after window end
                        try:
                            if active.get("status") == "active":
                                self.taskdb.mark_failed(active.get("id"), timed_out=True)
                                active = self.taskdb.get_active()
                                overdue = True
                        except Exception:
                            pass
                        decision_due = False
        except Exception:
            decision_due = False

        if decision_enabled and decision_due:
            self._task_decision_required = True
            self._task_decision_task_id = active.get("id")
            if eval_mode == "before":
                msg = "Approaching deadline. Decide: PASSED or FAILED."
            else:
                msg = "Evaluation period started. Mark task as PASSED or FAILED."
            warn = tk.Label(self._task_panel, text=msg, fg="#ff6b6b", bg="#111", font=("Segoe UI", 10, "bold"))
            warn.pack(anchor="w", padx=8, pady=(0,6))
        else:
            # Informational guidance based on mode
            if decision_enabled and due_iso:
                try:
                    due_dt = datetime.fromisoformat(due_iso)
                    now = datetime.now(timezone.utc)
                    if eval_mode == "after":
                        window_end = due_dt + timedelta(minutes=window_m)
                        if now < due_dt:
                            info = tk.Label(self._task_panel, text="Work until the limit; evaluation will be after the deadline.", fg="#aaa", bg="#111", font=("Segoe UI", 9))
                            info.pack(anchor="w", padx=8, pady=(0,6))
                        elif now >= due_dt and now < window_end:
                            remain = window_end - now
                            mm = int(remain.total_seconds() // 60)
                            ss = int(remain.total_seconds() % 60)
                            info = tk.Label(self._task_panel, text=f"Limit reached; evaluation in {mm}m {ss}s.", fg="#ffbd6b", bg="#111", font=("Segoe UI", 9))
                            info.pack(anchor="w", padx=8, pady=(0,6))
                        elif now >= window_end:
                            info = tk.Label(self._task_panel, text="Evaluation window timed out — recorded as FAILED.", fg="#ff6b6b", bg="#111", font=("Segoe UI", 9, "bold"))
                            info.pack(anchor="w", padx=8, pady=(0,6))
                    else:  # before mode
                        window_start = due_dt - timedelta(minutes=window_m)
                        if now < window_start:
                            info = tk.Label(self._task_panel, text=f"Decision window opens {window_m}m before deadline.", fg="#aaa", bg="#111", font=("Segoe UI", 9))
                            info.pack(anchor="w", padx=8, pady=(0,6))
                except Exception:
                    pass

        # Action buttons
        row = tk.Frame(self._task_panel, bg="#111")
        row.pack(anchor="w", padx=6, pady=(0,6))
        done_btn = tk.Button(row, text="✓", fg="#0f0", bg="#222", font=("Segoe UI", 12, "bold"), width=3,
                             command=lambda tid=active["id"], d=due_iso: self._task_mark_done(tid, d))
        change_btn = tk.Button(row, text="✗", fg="#f33", bg="#222", font=("Segoe UI", 12, "bold"), width=3,
                               command=lambda tid=active["id"]: self._show_change_form(tid))
        done_btn.pack(side="left", padx=(2,6))
        change_btn.pack(side="left")

        # Re-attach preserved change form (if any)
        if keep_form is not None:
            try:
                keep_form.pack(fill="x", padx=8, pady=(0,6))
            except Exception:
                pass

        # Live countdown refresh
        if self._task_timer_id:
            try: self.after_cancel(self._task_timer_id)
            except Exception: pass
        self._task_timer_id = self.after(1000, self._render_task_panel)

    def _task_mark_done(self, task_id, due_iso):
        try:
            # If overdue relative to due_iso, mark as failed even if done
            is_overdue = False
            try:
                if due_iso:
                    due_dt = datetime.fromisoformat(due_iso)
                    is_overdue = datetime.now(timezone.utc) > due_dt
            except Exception:
                is_overdue = False
            if is_overdue:
                self.taskdb.mark_failed(task_id)
            else:
                self.taskdb.mark_completed(task_id)
        except Exception:
            pass
        self._task_decision_required = False
        self._task_decision_task_id = None
        self._render_task_panel()
        self._refresh_analytics()

    def _show_change_form(self, task_id):
        # Inline change form under task panel (preserved across refresh)
        try:
            if getattr(self, "_task_change_form", None) is not None and int(self._task_change_form.winfo_exists()) == 1:
                try: self._task_change_form.lift()
                except Exception: pass
                return
        except Exception:
            pass
        form = tk.Frame(self._task_panel, bg="#111")
        form.pack(fill="x", padx=8, pady=(0,6))
        self._task_change_form = form
        tk.Label(form, text="Why change?", fg="#ddd", bg="#111").grid(row=0, column=0, sticky="w")
        reason_var = tk.StringVar()
        ttk.Entry(form, textvariable=reason_var, width=50).grid(row=0, column=1, sticky="we")
        tk.Label(form, text="New task (optional)", fg="#bbb", bg="#111").grid(row=1, column=0, sticky="w", pady=(4,0))
        new_title = tk.StringVar(); ttk.Entry(form, textvariable=new_title, width=40).grid(row=1, column=1, sticky="we", pady=(4,0))
        tk.Label(form, text="Due (mins or HH:MM)", fg="#bbb", bg="#111").grid(row=2, column=0, sticky="w")
        new_due = tk.StringVar(); ttk.Entry(form, textvariable=new_due, width=16).grid(row=2, column=1, sticky="w")
        tk.Label(form, text="Why", fg="#bbb", bg="#111").grid(row=3, column=0, sticky="w")
        new_why = tk.StringVar(); ttk.Entry(form, textvariable=new_why, width=40).grid(row=3, column=1, sticky="we")
        tk.Label(form, text="Consequences", fg="#bbb", bg="#111").grid(row=4, column=0, sticky="w")
        new_cons = tk.StringVar(); ttk.Entry(form, textvariable=new_cons, width=40).grid(row=4, column=1, sticky="we")
        btns = ttk.Frame(form); btns.grid(row=5, column=0, columnspan=2, sticky="e", pady=(6,0))
        def save_change():
            reason = reason_var.get().strip()
            if not reason:
                messagebox.showerror("Required", "Please provide a reason for changing the task.")
                return
            try:
                self.taskdb.mark_changed(task_id, reason)
            except Exception:
                pass
            # Optional new task
            nt = new_title.get().strip()
            if nt:
                due_iso = TaskEntryDialog._parse_due(self=None, txt=new_due.get()) if 'TaskEntryDialog' in globals() else None
                # Fallback quick parse
                if due_iso is None:
                    try:
                        try:
                            mins = int((new_due.get() or '60').strip())
                        except ValueError:
                            mins = 60
                        mins = max(1, mins)
                        due_iso = (datetime.now(timezone.utc) + timedelta(minutes=mins)).isoformat()
                    except Exception:
                        due_iso = None
                try:
                    self.taskdb.start_task(title=nt, due_utc=due_iso, why=new_why.get().strip(), consequences=new_cons.get().strip())
                except Exception:
                    pass
            try:
                form.destroy()
            except Exception:
                pass
            try:
                self._task_change_form = None
            except Exception:
                pass
            self._render_task_panel()
            self._refresh_analytics()
        def cancel_change():
            try: form.destroy()
            finally:
                try: self._task_change_form = None
                except Exception: pass
        ttk.Button(btns, text="Cancel", command=cancel_change).pack(side="right", padx=6)
        ttk.Button(btns, text="Save", command=save_change).pack(side="right")

    def _refresh_analytics(self):
        if not self._analytics_lbl or not self.taskdb:
            return
        try:
            tscale = str(self.settings.get("tasks_analytics_timescale", "lifetime"))
            changed_as_fail = bool(self.settings.get("tasks_change_counts_as_fail", True))
            stats = self.taskdb.analytics_counts(timescale=tscale, treat_changed_as_fail=changed_as_fail)
            self._analytics_lbl.config(text=f"✔ Completed: {stats['completed']}   ✗ Failed: {stats['failed']}   ~ Changed: {stats['changed']}   ⏱ Timed-out: {stats.get('timed_out',0)}")
        except Exception:
            try:
                self._analytics_lbl.config(text="")
            except Exception:
                pass

    def _open_task_history(self, _evt=None):
        if not self.taskdb:
            messagebox.showerror("Unavailable", "Task database not available.")
            return
        try:
            TaskHistoryWindow(self, self.taskdb)
        except Exception:
            log_exception("failed to open TaskHistoryWindow")


    # ---- Windows integrations ----
    def _disable_minimize_button(self):
        if platform.system().lower() != "windows":
            return
        hwnd = self.winfo_id()
        GWL_STYLE = -16
        WS_MINIMIZEBOX = 0x00020000
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
        if style:
            style &= ~WS_MINIMIZEBOX
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style)
            SWP_NOSIZE = 0x0001
            SWP_NOMOVE = 0x0002
            SWP_NOZORDER = 0x0004
            SWP_FRAMECHANGED = 0x0020
            ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                                              SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_FRAMECHANGED)

    def _flash_taskbar_begin(self):
        if platform.system().lower() != "windows":
            return
        hwnd = wintypes.HWND(self.winfo_id())
        class FLASHWINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_uint),
                ("hwnd", wintypes.HWND),
                ("dwFlags", ctypes.c_uint),
                ("uCount", ctypes.c_uint),
                ("dwTimeout", ctypes.c_uint),
            ]
        FLASHW_ALL = 0x0003
        FLASHW_TIMERNOFG = 0x000C
        info = FLASHWINFO(ctypes.sizeof(FLASHWINFO), hwnd, FLASHW_ALL | FLASHW_TIMERNOFG, 0, 0)
        ctypes.windll.user32.FlashWindowEx(ctypes.byref(info))

    def _flash_taskbar_stop(self):
        if platform.system().lower() != "windows":
            return
        hwnd = wintypes.HWND(self.winfo_id())
        class FLASHWINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_uint),
                ("hwnd", wintypes.HWND),
                ("dwFlags", ctypes.c_uint),
                ("uCount", ctypes.c_uint),
                ("dwTimeout", ctypes.c_uint),
            ]
        FLASHW_STOP = 0x0000
        info = FLASHWINFO(ctypes.sizeof(FLASHWINFO), hwnd, FLASHW_STOP, 0, 0)
        ctypes.windll.user32.FlashWindowEx(ctypes.byref(info))

    # ---- Cross-platform guard against minimization ----
    def _prevent_minimize(self, _evt=None):
        if self._closed:
            return
        try:
            if self.state() == 'iconic':
                self.after(0, self.deiconify)
                try: self.lift()
                except Exception: pass
        except Exception:
            pass

# --- Tray icon helpers -------------------------------------------------------
_GDIPLUS_TOKEN = None


class _GdiplusStartupInput(ctypes.Structure):
    _fields_ = [
        ("GdiplusVersion", ctypes.c_uint32),
        ("DebugEventCallback", ctypes.c_void_p),
        ("SuppressBackgroundThread", wintypes.BOOL),
        ("SuppressExternalCodecs", wintypes.BOOL),
    ]


def _ensure_gdiplus_started() -> bool:
    global _GDIPLUS_TOKEN
    if _GDIPLUS_TOKEN is not None:
        return True
    try:
        gdiplus = ctypes.windll.gdiplus
    except Exception:
        return False
    startup_input = _GdiplusStartupInput(1, None, False, False)
    token = ctypes.c_ulonglong()
    status = gdiplus.GdiplusStartup(ctypes.byref(token), ctypes.byref(startup_input), None)
    if status != 0:
        return False
    _GDIPLUS_TOKEN = token
    return True

def _gdiplus_shutdown():
    """Clean up GDI+ resources on application exit."""
    global _GDIPLUS_TOKEN
    if _GDIPLUS_TOKEN is not None:
        try:
            ctypes.windll.gdiplus.GdiplusShutdown(_GDIPLUS_TOKEN)
        except Exception:
            pass
        _GDIPLUS_TOKEN = None


def _create_hicon_from_image(path: str) -> Optional[wintypes.HICON]:
    if not path or not os.path.exists(path):
        return None
    if os.path.splitext(path)[1].lower() == ".ico":
        return None  # handled by LoadImageW
    if not _ensure_gdiplus_started():
        return None
    gdiplus = ctypes.windll.gdiplus
    image = ctypes.c_void_p()
    status = gdiplus.GdipCreateBitmapFromFile(ctypes.c_wchar_p(path), ctypes.byref(image))
    if status != 0 or not image:
        return None
    hicon = wintypes.HICON()
    status = gdiplus.GdipCreateHICONFromBitmap(image, ctypes.byref(hicon))
    gdiplus.GdipDisposeImage(image)
    if status != 0 or not hicon:
        return None
    return hicon
# --- Windows wake/lock watcher: install a custom WNDPROC and listen for unlock/wake ---
class _WindowsWakeWatcher:
    """Hooks the Tk root window proc to receive lock/unlock (WTS), sleep/resume (power),
    display/DPI changes, and tray icon callbacks. Keeps references to callbacks to avoid GC."""
    def __init__(self, root, on_resume_callable, on_pause_callable=None,
                 on_display_change_callable=None, tray_enabled=False,
                 on_tray_click_callable=None, tray_tooltip="Focus Check",
                 tray_icon_path=None):
        self.root = root
        self.on_resume = on_resume_callable
        self.on_pause = on_pause_callable
        self.on_display_change = on_display_change_callable
        self.on_tray_click = on_tray_click_callable
        self.hwnd = root.winfo_id()
        self._tray_enabled = bool(tray_enabled)
        self._tray_added = False
        self._tray_id = 1
        self._hicon = None
        self._tray_icon_path = tray_icon_path

        # API handles
        user32 = ctypes.windll.user32
        self._CallWindowProcW = user32.CallWindowProcW
        # Correct prototypes (avoid 32-bit truncation on 64-bit)
        try:
            self._CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, WPARAM_T, LPARAM_T]
            self._CallWindowProcW.restype = LRESULT
        except Exception:
            pass
        # Use LongPtrW (64-bit safe); fall back if missing
        self._SetWindowLongPtrW = getattr(user32, "SetWindowLongPtrW", None)
        self._GetWindowLongPtrW = getattr(user32, "GetWindowLongPtrW", None)
        if not self._SetWindowLongPtrW:
            self._SetWindowLongPtrW = user32.SetWindowLongW
        if not self._GetWindowLongPtrW:
            self._GetWindowLongPtrW = user32.GetWindowLongW
        # Prototypes for setting/getting window proc pointer
        try:
            self._SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
            self._SetWindowLongPtrW.restype = ctypes.c_void_p
            self._GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
            self._GetWindowLongPtrW.restype = ctypes.c_void_p
        except Exception:
            pass

        # WTS session change notifications live in wtsapi32; if missing, continue without them
        self._WTSRegisterSessionNotification = None
        self._WTSUnRegisterSessionNotification = None
        try:
            wtsapi32 = ctypes.windll.wtsapi32
            try:
                self._WTSRegisterSessionNotification = wtsapi32.WTSRegisterSessionNotification
                self._WTSRegisterSessionNotification.argtypes = [wintypes.HWND, wintypes.DWORD]
                self._WTSRegisterSessionNotification.restype = wintypes.BOOL
            except Exception:
                self._WTSRegisterSessionNotification = None
            # Some environments expose 'WTSUnRegisterSessionNotification' (capital R)
            # while others might expose 'WTSUnregisterSessionNotification'. Try both.
            unreg = getattr(wtsapi32, "WTSUnRegisterSessionNotification", None) or getattr(wtsapi32, "WTSUnregisterSessionNotification", None)
            if unreg:
                self._WTSUnRegisterSessionNotification = unreg
                try:
                    self._WTSUnRegisterSessionNotification.argtypes = [wintypes.HWND]
                    self._WTSUnRegisterSessionNotification.restype = wintypes.BOOL
                except Exception:
                    pass
        except Exception:
            self._WTSRegisterSessionNotification = None
            self._WTSUnRegisterSessionNotification = None

        # Shell_NotifyIcon for tray
        shell32 = ctypes.windll.shell32
        try:
            self._Shell_NotifyIconW = shell32.Shell_NotifyIconW
            self._Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.c_void_p]
            self._Shell_NotifyIconW.restype = wintypes.BOOL
        except Exception:
            self._Shell_NotifyIconW = None

        # Old proc
        self._old_wndproc = self._GetWindowLongPtrW(self.hwnd, GWL_WNDPROC)

        # WNDPROC prototype (pointer-sized return type)
        WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, WPARAM_T, LPARAM_T)

        WM_DISPLAYCHANGE = 0x007E
        WM_DPICHANGED = 0x02E0
        WM_USER = 0x0400
        self._TRAY_MSG = WM_USER + 1
        # Re-add tray icon after Explorer restarts
        try:
            self._TaskbarCreated = user32.RegisterWindowMessageW("TaskbarCreated")
        except Exception:
            self._TaskbarCreated = 0

        @WNDPROC
        def _proc(hwnd, msg, wParam, lParam):
            try:
                if msg == WM_WTSSESSION_CHANGE:
                    if wParam == WTS_SESSION_UNLOCK:
                        # Resume immediately on unlock
                        self.root.after(0, self.on_resume)
                    elif wParam == WTS_SESSION_LOCK:
                        # Pause immediately on lock
                        if self.on_pause:
                            self.root.after(0, lambda: self.on_pause("lock"))
                elif msg == WM_POWERBROADCAST:
                    if wParam in (PBT_APMRESUMEAUTOMATIC, PBT_APMRESUMESUSPEND, PBT_APMRESUMESTANDBY):
                        # Resume immediately on wake
                        self.root.after(0, self.on_resume)
                    elif wParam == PBT_APMSUSPEND:
                        # Pause immediately on suspend
                        if self.on_pause:
                            self.root.after(0, lambda: self.on_pause("sleep"))
                elif msg in (WM_DISPLAYCHANGE, WM_DPICHANGED):
                    if self.on_display_change:
                        self.root.after(50, self.on_display_change)
                elif msg == self._TRAY_MSG:
                    if self.on_tray_click:
                        msg_code = int(lParam)
                        if msg_code in (WM_RBUTTONUP, WM_LBUTTONUP, WM_CONTEXTMENU):
                            self.root.after(0, lambda m=msg_code: self.on_tray_click(m))
                elif self._TaskbarCreated and msg == self._TaskbarCreated:
                    # Explorer restarted; re-add tray icon
                    try:
                        self._tray_added = False
                        if self._tray_enabled:
                            self.root.after(200, lambda: self._tray_add("Focus Check"))
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                if not self._old_wndproc:
                    return ctypes.windll.user32.DefWindowProcW(hwnd, msg, wParam, lParam)
            except Exception:
                pass
            return self._CallWindowProcW(ctypes.c_void_p(self._old_wndproc), hwnd, msg, wParam, lParam)

        # Keep a ref to avoid GC
        self._proc = _proc
        self._SetWindowLongPtrW(self.hwnd, GWL_WNDPROC, self._proc)

        # 0 = NOTIFY_FOR_THIS_SESSION
        try:
            if self._WTSRegisterSessionNotification is not None:
                ok = self._WTSRegisterSessionNotification(self.hwnd, 0)
                if not ok:
                    try:
                        get_logger().warning("WTSRegisterSessionNotification failed; lock/unlock events unavailable")
                    except Exception:
                        pass
        except Exception:
            log_exception("WTSRegisterSessionNotification raised")

        # Setup tray icon if requested
        if self._tray_enabled and self._Shell_NotifyIconW is not None:
            try:
                self._tray_add(tray_tooltip)
            except Exception:
                pass

    def _tray_add(self, tooltip_text):
        if self._Shell_NotifyIconW is None or self._tray_added:
            return
        user32 = ctypes.windll.user32
        # Try loading a custom icon from file first (assets/focus.ico or focus.ico)
        self._hicon = None
        try:
            IMAGE_ICON = 1
            LR_LOADFROMFILE = 0x00000010
            SM_CXSMICON = 49
            SM_CYSMICON = 50
            cx = user32.GetSystemMetrics(SM_CXSMICON)
            cy = user32.GetSystemMetrics(SM_CYSMICON)
            candidates = []
            icon_candidate = getattr(self, "_tray_icon_path", None)
            if icon_candidate and os.path.exists(icon_candidate):
                candidates.append(icon_candidate)
            candidates.extend([
                _resource_path(os.path.join("assets", "focus.ico")),
                _resource_path("focus.ico"),
            ])
            for candidate in candidates:
                if not candidate or not os.path.exists(candidate):
                    continue
                ext = os.path.splitext(candidate)[1].lower()
                h = None
                if ext == ".ico":
                    try:
                        h = user32.LoadImageW(
                            0,
                            ctypes.c_wchar_p(candidate),
                            IMAGE_ICON,
                            cx,
                            cy,
                            LR_LOADFROMFILE,
                        )
                    except Exception:
                        h = None
                if not h:
                    h = _create_hicon_from_image(candidate)
                if h:
                    self._hicon = h
                    break
        except Exception:
            pass
        # Fallback to shared system icon if file load failed
        if not self._hicon:
            try:
                self._hicon = user32.LoadIconW(0, 32512)  # IDI_APPLICATION
                if not self._hicon:
                    self._hicon = user32.LoadIconW(0, 32516)  # IDI_INFORMATION
            except Exception:
                self._hicon = None

        class NOTIFYICONDATA(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_uint),
                ("hWnd", wintypes.HWND),
                ("uID", ctypes.c_uint),
                ("uFlags", ctypes.c_uint),
                ("uCallbackMessage", ctypes.c_uint),
                ("hIcon", wintypes.HICON),
                ("szTip", ctypes.c_wchar * 128),
                ("dwState", ctypes.c_uint),
                ("dwStateMask", ctypes.c_uint),
                ("szInfo", ctypes.c_wchar * 256),
                ("uTimeoutOrVersion", ctypes.c_uint),
                ("szInfoTitle", ctypes.c_wchar * 64),
                ("dwInfoFlags", ctypes.c_uint),
                ("guidItem", ctypes.c_byte * 16),
                ("hBalloonIcon", wintypes.HICON),
            ]
        NIF_MESSAGE = 0x00000001
        NIF_ICON    = 0x00000002
        NIF_TIP     = 0x00000004
        NIF_INFO    = 0x00000010
        NIF_GUID   = 0x00000020
        NIM_ADD     = 0x00000000
        NIM_SETVERSION = 0x00000004

        tip = (tooltip_text or "Focus Check")[:127]
        data = NOTIFYICONDATA()
        data.cbSize = ctypes.sizeof(NOTIFYICONDATA)
        data.hWnd = wintypes.HWND(self.hwnd)
        data.uID = self._tray_id
        flags = NIF_MESSAGE | NIF_TIP
        if self._hicon:
            flags |= NIF_ICON
        # Persistent GUID helps Windows 11 expose the toggle
        try:
            g = uuid.uuid5(uuid.NAMESPACE_DNS, "FocusCheckTrayIcon")
            b = g.bytes_le  # little-endian per WIN32 GUID layout
            for i in range(16):
                data.guidItem[i] = b[i]
            flags |= NIF_GUID
        except Exception:
            pass
        data.uFlags = flags
        data.uCallbackMessage = self._TRAY_MSG
        data.hIcon = self._hicon
        data.szTip = tip
        try:
            try:
                # Explicit marker for tray creation attempt (native)
                get_logger().info("creating icon (native)")
                get_logger().info(
                    "tray(native): NIM_ADD attempting | flags=0x%X hicon=%s tip='%s'",
                    flags, bool(self._hicon), tip
                )
            except Exception:
                pass
        except Exception:
            pass
        ok = self._Shell_NotifyIconW(NIM_ADD, ctypes.byref(data))
        if ok:
            # Set modern behavior (VERSION_4)
            try:
                data.uTimeoutOrVersion = 4
                self._Shell_NotifyIconW(NIM_SETVERSION, ctypes.byref(data))
            except Exception:
                pass
            # One-time info balloon to help user locate the icon
            try:
                info = "Right-click this icon for menu. If hidden, click ^ or enable in Taskbar settings."
                title = "FocusCheck running"
                data.uFlags = flags | NIF_INFO
                data.szInfo = info[:255]
                data.szInfoTitle = title[:63]
                NIIF_INFO = 0x00000001
                data.dwInfoFlags = NIIF_INFO
                self._Shell_NotifyIconW(0x00000001, ctypes.byref(data))  # NIM_MODIFY
            except Exception:
                pass
            self._tray_added = True
            try:
                get_logger().info("tray start succeeded (native)")
                get_logger().info("tray(native): NIM_ADD success; tray icon visible (or in overflow)")
            except Exception:
                pass
        else:
            try:
                get_logger().error("tray start failed (native)")
                get_logger().error("Shell_NotifyIconW(NIM_ADD) failed; tray icon not shown")
            except Exception:
                pass
            # Clean up icon if tray creation failed
            self._destroy_custom_icon()

    def _destroy_custom_icon(self):
        if self._hicon:
            try:
                ctypes.windll.user32.DestroyIcon(self._hicon)
            except Exception:
                pass
            self._hicon = None

    def _tray_remove(self):
        if not self._tray_added or self._Shell_NotifyIconW is None:
            return
        class NOTIFYICONDATA(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_uint),
                ("hWnd", wintypes.HWND),
                ("uID", ctypes.c_uint),
                ("uFlags", ctypes.c_uint),
                ("uCallbackMessage", ctypes.c_uint),
                ("hIcon", wintypes.HICON),
                ("szTip", ctypes.c_wchar * 128),
            ]
        NIM_DELETE = 0x00000002
        data = NOTIFYICONDATA()
        data.cbSize = ctypes.sizeof(NOTIFYICONDATA)
        data.hWnd = wintypes.HWND(self.hwnd)
        data.uID = self._tray_id
        self._Shell_NotifyIconW(NIM_DELETE, ctypes.byref(data))
        self._tray_added = False
        self._destroy_custom_icon()

    def _tray_modify(self, tooltip_text=None, hicon=None):
        # Modify existing tray icon (tooltip and/or icon)
        if not self._tray_added or self._Shell_NotifyIconW is None:
            return
        class NOTIFYICONDATA(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_uint),
                ("hWnd", wintypes.HWND),
                ("uID", ctypes.c_uint),
                ("uFlags", ctypes.c_uint),
                ("uCallbackMessage", ctypes.c_uint),
                ("hIcon", wintypes.HICON),
                ("szTip", ctypes.c_wchar * 128),
                ("dwState", ctypes.c_uint),
                ("dwStateMask", ctypes.c_uint),
                ("szInfo", ctypes.c_wchar * 256),
                ("uTimeoutOrVersion", ctypes.c_uint),
                ("szInfoTitle", ctypes.c_wchar * 64),
                ("dwInfoFlags", ctypes.c_uint),
                ("guidItem", ctypes.c_byte * 16),
                ("hBalloonIcon", wintypes.HICON),
            ]
        NIM_MODIFY = 0x00000001
        NIF_TIP    = 0x00000004
        NIF_ICON   = 0x00000002
        flags = 0
        data = NOTIFYICONDATA()
        data.cbSize = ctypes.sizeof(NOTIFYICONDATA)
        data.hWnd = wintypes.HWND(self.hwnd)
        data.uID = self._tray_id
        # Tooltip
        if tooltip_text is not None:
            tip = (tooltip_text or "Focus Check")[:127]
            data.szTip = tip
            flags |= NIF_TIP
        # Icon
        if hicon:
            data.hIcon = hicon
            flags |= NIF_ICON
        if flags:
            data.uFlags = flags
            self._Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(data))

    def close(self):
        try:
            self._tray_remove()
        except Exception:
            pass
        try:
            self._destroy_custom_icon()
        except Exception:
            pass
        try:
            # Validate that our WNDPROC is still installed before restoring
            current_proc = self._GetWindowLongPtrW(self.hwnd, GWL_WNDPROC)
            if current_proc == ctypes.cast(self._proc, ctypes.c_void_p).value:
                self._SetWindowLongPtrW(self.hwnd, GWL_WNDPROC, self._old_wndproc)
        except Exception:
            pass
        try:
            self._WTSUnRegisterSessionNotification(self.hwnd)
        except Exception:
            pass

# -------------------- App --------------------

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        # Ensure window handle is realized before using it for shell hooks
        try:
            self.root.update_idletasks()
        except Exception:
            pass
        # Emergency quit shortcuts (for dev convenience)
        try:
            self.root.bind_all('<Control-Shift-Escape>', lambda e: self._quit())
            self.root.bind_all('<Alt-q>', lambda e: self._quit())
        except Exception:
            pass
        self.settings = load_settings()
        # App start times for runtime reporting
        self._start_wall = datetime.now()
        self._start_mono = time.monotonic()
        try:
            get_logger().info("App starting v%s | data_dir=%s", APP_VERSION, _get_data_dir())
        except Exception:
            pass
        # Init task DB
        try:
            self.taskdb = TaskDB(TASK_DB_PATH)
        except Exception:
            self.taskdb = None
            log_exception("TaskDB unavailable; continuing without tasks feature")
        ensure_log_header()
        self.guard = PauseGuard(lambda: self.settings)
        self._scheduled = None
        self._current_prompt = None
        self._last_resume_mono = 0.0
        self._next_due_mono = None
        self._next_total_s = None
        self._tray_icon_image = None
        self._tray_icon_path = None
        self._prepare_tray_icon()
        # Heartbeat to catch paused->unpaused edges
        self._start_heartbeat()
        # File heartbeat for watchdogs
        self._start_file_heartbeat()

        # Startup diagnostics (log versions and tray import attempts)
        try:
            self._log_startup_diagnostics()
        except Exception:
            pass

        # Optional cross-platform tray using pystray (preferred when available)
        self._pystray_started = False  # started (requested)
        self._using_pystray = False    # proven alive
        self._tray = None
        try:
            if SystemTray is not None:
                try:
                    get_logger().info("startup: pystray system tray available; attempting start")
                except Exception:
                    pass
                def _get(k, d=None):
                    try:
                        return self.settings.get(k, d)
                    except Exception:
                        return d
                def _set(k, v):
                    try:
                        self.settings[k] = v
                        save_settings(self.settings)
                    except Exception:
                        pass
                # Hooks to track pystray status
                def _on_alive():
                    # Proved alive; mark as using pystray
                    try:
                        get_logger().info("tray post-start check OK (pystray alive)")
                    except Exception:
                        pass
                    self._using_pystray = True
                def _on_failure():
                    # pystray failed - enable native tray if available
                    try:
                        get_logger().error("pystray post-start check failed", exc_info=True)
                    except Exception:
                        pass
                    # If we have a Windows watcher but tray is disabled, enable it
                    if platform.system().lower() == "windows" and getattr(self, "_winwatch", None) is not None:
                        try:
                            # Try to enable the native tray on the existing watcher
                            if hasattr(self._winwatch, '_tray_add'):
                                self._winwatch._tray_add("Focus Check")
                                get_logger().info("fallback: enabled native tray after pystray failure")
                        except Exception:
                            get_logger().exception("failed to enable native tray fallback", exc_info=True)

                self._tray = SystemTray(
                    app=self,
                    name=APP_NAME,
                    tooltip=f"{APP_NAME} running",
                    get_setting=_get,
                    set_setting=_set,
                    open_settings_ui=lambda: self._open_settings_from_tray(),
                    logs_path=APP_LOG_PATH,
                    config_path=SETTINGS_PATH,
                    icon_image=self._tray_icon_image,
                    on_failure=_on_failure,
                    on_alive=_on_alive,
                )
                # Explicit marker for tray creation attempt (pystray)
                try:
                    get_logger().info("creating icon (pystray)")
                except Exception:
                    pass
                started = False
                try:
                    started = bool(self._tray.start())
                except Exception:
                    get_logger().exception("pystray start raised", exc_info=True)
                    started = False
                if started:
                    self._pystray_started = True
                    try:
                        get_logger().info("tray start succeeded (pystray)")
                        get_logger().info("startup: pystray tray started successfully")
                    except Exception:
                        pass
                else:
                    try:
                        get_logger().error("tray start failed (pystray)")
                        get_logger().warning("startup: pystray tray failed to start; falling back (Windows native, if available)")
                    except Exception:
                        pass
        except Exception:
            get_logger().exception("pystray setup failed", exc_info=True)
            self._pystray_started = False
            self._using_pystray = False

        # Windows: listen for power/session/display and enable native tray only if pystray failed.
        self._winwatch = None
        if platform.system().lower() == "windows":
            try:
                # Only enable native tray if pystray didn't start successfully
                enable_native_tray = not self._pystray_started
                self._winwatch = _WindowsWakeWatcher(
                    self.root,
                    on_resume_callable=self._on_resume_event,
                    on_pause_callable=self._on_pause_event,
                    on_display_change_callable=self._on_display_change,
                    tray_enabled=enable_native_tray,
                    on_tray_click_callable=self._on_tray_click,
                    tray_tooltip="Focus Check",
                    tray_icon_path=self._tray_icon_path,
                )
                try:
                    get_logger().info("startup: Windows watcher initialized | native_tray=%s", enable_native_tray)
                except Exception:
                    pass
            except Exception as e:
                print(f"Windows watcher/tray unavailable: {e}", file=sys.stderr)
        # quick first pop to prove it works
        self._schedule_next(2000)

    def _prepare_tray_icon(self):
        candidates: list[str] = []
        try:
            png_path = _resource_path('imageedit_5_9158249849.png')
            if png_path and os.path.exists(png_path):
                candidates.append(png_path)
        except Exception:
            pass
        try:
            base_dirs = []
            try:
                if getattr(sys, "_MEIPASS", None):
                    base_dirs.append(sys._MEIPASS)
            except Exception:
                pass
            base_dirs.append(_get_base_dir())
            for b in base_dirs:
                try:
                    for p in glob.glob(os.path.join(b, "*.png")):
                        if p not in candidates and os.path.exists(p):
                            candidates.append(p)
                    for p in glob.glob(os.path.join(b, "*.ico")):
                        if p not in candidates and os.path.exists(p):
                            candidates.append(p)
                except Exception:
                    pass
        except Exception:
            pass
        if not candidates:
            return
        first = candidates[0]
        self._tray_icon_path = first  # keep whatever we found so native tray can try it
        try:
            from PIL import Image  # type: ignore
        except Exception:
            return
        try:
            with Image.open(first) as img:
                image_rgba = img.convert("RGBA")
                self._tray_icon_image = image_rgba.copy()
                sizes = [16, 20, 24, 32, 48, 64, 128]
                available = [s for s in sizes if s <= min(image_rgba.size)] or [min(image_rgba.size)]
                tmp_path = os.path.join(tempfile.gettempdir(), "focuscheck_tray.ico")
                image_rgba.save(tmp_path, format="ICO", sizes=[(s, s) for s in available])
                self._tray_icon_path = tmp_path
        except Exception:
            self._tray_icon_image = None
            self._tray_icon_path = first
            try:
                get_logger().exception("failed preparing tray icon", exc_info=True)
            except Exception:
                pass

    def _schedule_next(self, delay_ms=None):
        if delay_ms is None:
            delay_ms = int(self.settings["interval_seconds"] * 1000)
        if self._scheduled:
            self.root.after_cancel(self._scheduled)
        try:
            get_logger().debug("scheduling next prompt in %sms", delay_ms)
        except Exception:
            pass
        self._scheduled = self.root.after(delay_ms, self._maybe_show_prompt)
        # Track next due for tray meter
        try:
            self._next_total_s = max(1, int(delay_ms // 1000))
            self._next_due_mono = time.monotonic() + (delay_ms / 1000.0)
        except Exception:
            self._next_total_s = None
            self._next_due_mono = None

    def _format_hms(self, seconds):
        try:
            seconds = int(max(0, seconds))
            m, s = divmod(seconds, 60)
            h, m = divmod(m, 60)
            if h:
                return f"{h}:{m:02d}:{s:02d}"
            else:
                return f"{m}:{s:02d}"
        except Exception:
            return "--"


    def _start_heartbeat(self):
        # Fires a prompt immediately on paused->unpaused transition, as a safety net.
        self._last_paused_state = None
        def tick():
            try:
                paused_now = self.settings.get("pause_when_inactive_or_lid_closed", True) and self.guard.should_pause()
                if self._last_paused_state is True and paused_now is False:
                    # Transition from paused to unpaused: schedule a prompt now
                    self._schedule_next(0)
                self._last_paused_state = paused_now
            except Exception:
                pass
            self.root.after(1000, tick)  # 1 Hz
        tick()

    def _maybe_show_prompt(self):
        self.settings = load_settings()  # refresh
        # Global pause toggle supported by SystemTray (optional)
        try:
            if bool(self.settings.get("paused", False)):
                poll_ms = int(self.settings.get("pause_poll_interval_seconds", 5)) * 1000
                self._schedule_next(poll_ms)
                return
        except Exception:
            pass
        # Prevent duplicate concurrent prompts
        try:
            if self._current_prompt is not None and not getattr(self._current_prompt, "_closed", False):
                # An active prompt is already open; check again shortly
                get_logger().info("prompt already open; deferring new prompt")
                self._schedule_next(1500)
                return
        except Exception:
            pass
        if self.settings.get("pause_when_inactive_or_lid_closed", True) and self.guard.should_pause():
            poll_ms = int(self.settings.get("pause_poll_interval_seconds", 5)) * 1000
            self._schedule_next(poll_ms)
            return

        slot_info = self._slot_start_info()
        try:
            get_logger().info("showing prompt @ %s", slot_info["local_minute"])  # best-effort
        except Exception:
            pass
        dlg = PromptDialog(self.root, self.settings, on_submit=self._on_prompt_done, slot_start_dt=slot_info, taskdb=getattr(self, "taskdb", None), app_ref=self)
        self._current_prompt = dlg
        try:
            dlg.wait_window()
        finally:
            # <-- ALWAYS schedule the next one, even if an exception happens
            self._on_prompt_done()




    def _slot_start_info(self):
        now = datetime.now()
        local_minute = now.strftime("%H:%M")
        return {
            "utc_start": datetime.now(timezone.utc),
            "local_minute": local_minute,
            "mono_start": time.monotonic()
        }

    # --- Windows event hooks ---
    def _on_pause_event(self, reason: str):
        # Set event-driven pause flags based on reason
        try:
            if reason == "lock":
                self.guard.set_locked(True)
            elif reason == "sleep":
                self.guard.set_sleeping(True)
            try:
                get_logger().info("system pause reason=%s", reason)
            except Exception:
                pass
        except Exception:
            pass

    def _on_resume_event(self):
        # Clear pause flags and prompt immediately
        try:
            self.guard.set_locked(False)
            self.guard.set_sleeping(False)
        except Exception:
            pass
        now = time.monotonic()
        if now - self._last_resume_mono > 2.0:  # debounce
            self._schedule_next(0)
        self._last_resume_mono = now
        try:
            get_logger().info("system resume")
        except Exception:
            pass

    def _on_prompt_done(self):
        try:
            self._current_prompt = None
        except Exception:
            pass
        self._schedule_next()

    # Display/DPI change: keep dialogs on-screen
    def _on_display_change(self):
        try:
            if self._current_prompt is not None:
                if self.settings.get("center_on_show", True):
                    self._current_prompt._center_on_active_monitor()
                else:
                    self._current_prompt.ensure_on_screen()
            try:
                get_logger().info("display/DPI change handled")
            except Exception:
                pass
        except Exception:
            pass

    def _call_on_ui_thread(self, callback, *args, **kwargs):
        """Ensure callbacks involving Tk run on the UI thread."""
        root = getattr(self, "root", None)
        if root is None:
            return False
        if threading.current_thread() is threading.main_thread():
            try:
                callback(*args, **kwargs)
                return True
            except Exception:
                try:
                    get_logger().exception("UI dispatch failed", exc_info=True)
                except Exception:
                    pass
                return False
        def _wrapped():
            try:
                callback(*args, **kwargs)
            except Exception:
                try:
                    get_logger().exception("UI dispatch failed", exc_info=True)
                except Exception:
                    pass
        try:
            root.after(0, _wrapped)
            return True
        except Exception:
            try:
                get_logger().exception("Failed scheduling UI callback", exc_info=True)
            except Exception:
                pass
            return False

    # Tray menu
    def _on_tray_click(self, msg=None):
        try:
            try:
                self.settings = load_settings()
            except Exception:
                pass
            if msg == WM_LBUTTONUP:
                if bool(self.settings.get("tray_start_stop_enabled", True)):
                    self._tray_toggle_pause()
                else:
                    self._show_tray_menu()
            else:
                self._show_tray_menu()
        except Exception:
            pass

    def _show_tray_menu(self):
        try:
            try:
                self.settings = load_settings()
            except Exception:
                pass
            paused = bool(self.settings.get("paused", False))
            start_stop_enabled = bool(self.settings.get("tray_start_stop_enabled", True))
            settings_enabled = bool(self.settings.get("tray_settings_button_enabled", True))
            exit_enabled = bool(self.settings.get("tray_exit_button_enabled", True))
            taskdb_available = getattr(self, "taskdb", None) is not None
            startup_enabled = False
            try:
                startup_enabled = self._is_startup_enabled()
            except Exception:
                startup_enabled = False

            native_used = False
            try:
                user32 = ctypes.windll.user32
                TrackPopupMenu = user32.TrackPopupMenu
                try:
                    TrackPopupMenu.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.HWND, ctypes.c_void_p]
                    TrackPopupMenu.restype = ctypes.c_int
                except Exception:
                    pass

                MF_STRING = 0x00000000
                MF_DISABLED = 0x00000002
                MF_GRAYED = 0x00000001
                MF_SEPARATOR = 0x00000800
                TPM_RIGHTBUTTON = 0x0002
                TPM_RETURNCMD = 0x0100
                TPM_NONOTIFY = 0x0080

                CMD_STOP = 1001
                CMD_START = 1002
                CMD_PROMPT = 1003
                CMD_SNOOZE_5 = 1004
                CMD_SNOOZE_15 = 1005
                CMD_SETTINGS = 1006
                CMD_TASK = 1007
                CMD_STARTUP = 1008
                CMD_DATA = 1009
                CMD_LOGS = 1010
                CMD_EXIT = 1011

                actions = {}
                labels = []
                hmenu = user32.CreatePopupMenu()
                if hmenu:
                    try:
                        def _flags(enabled=True):
                            if enabled:
                                return MF_STRING
                            return MF_STRING | MF_DISABLED | MF_GRAYED

                        def _append(cmd_id, text, enabled=True, action=None):
                            label = ctypes.c_wchar_p(text)
                            if not user32.AppendMenuW(hmenu, _flags(enabled), cmd_id, label):
                                raise ctypes.WinError()
                            labels.append(label)
                            if action:
                                actions[cmd_id] = action

                        def _separator():
                            if not user32.AppendMenuW(hmenu, MF_SEPARATOR, 0, None):
                                raise ctypes.WinError()

                        _append(CMD_STOP, "Stop reminders", enabled=start_stop_enabled and not paused, action=self._tray_pause)
                        _append(CMD_START, "Start reminders", enabled=start_stop_enabled and paused, action=self._tray_resume)
                        _separator()
                        _append(CMD_PROMPT, "Prompt now", action=self._tray_prompt_now)
                        _append(CMD_SNOOZE_5, "Snooze 5 minutes", action=lambda: self._tray_snooze(5))
                        _append(CMD_SNOOZE_15, "Snooze 15 minutes", action=lambda: self._tray_snooze(15))
                        _separator()
                        _append(CMD_SETTINGS, "Settings", enabled=settings_enabled, action=self._open_settings_from_tray)
                        _append(CMD_TASK, "Set/Change Task", enabled=taskdb_available, action=self._open_task_dialog_from_tray)
                        _separator()
                        if startup_enabled:
                            _append(CMD_STARTUP, "Disable Run on Startup", action=self._tray_uninstall_startup)
                        else:
                            _append(CMD_STARTUP, "Enable Run on Startup", action=self._tray_install_startup)
                        _append(CMD_DATA, "Open Data Folder", action=self._tray_open_data_folder)
                        _append(CMD_LOGS, "Open Logs Folder", action=self._tray_open_logs_folder)
                        _separator()
                        _append(CMD_EXIT, "Exit", enabled=exit_enabled, action=self._tray_exit)

                        class POINT(ctypes.Structure):
                            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

                        pt = POINT()
                        if not user32.GetCursorPos(ctypes.byref(pt)):
                            pt.x = pt.y = 0
                        try:
                            user32.SetForegroundWindow(self.hwnd)
                        except Exception:
                            pass
                        try:
                            ctypes.set_last_error(0)
                        except AttributeError:
                            try:
                                ctypes.windll.kernel32.SetLastError(0)
                            except Exception:
                                pass
                        cmd = TrackPopupMenu(
                            hmenu,
                            TPM_RIGHTBUTTON | TPM_RETURNCMD | TPM_NONOTIFY,
                            int(pt.x),
                            int(pt.y),
                            0,
                            self.hwnd,
                            None,
                        )
                        if cmd == 0:
                            err = ctypes.get_last_error()
                            if err:
                                raise ctypes.WinError(err)
                    finally:
                        try:
                            user32.DestroyMenu(hmenu)
                        except Exception:
                            pass
                    native_used = True
                    action = actions.get(cmd)
                    if action:
                        action()
            except Exception:
                native_used = False
            if native_used:
                return

            try:
                get_logger().debug("tray menu opened | paused=%s", paused)
            except Exception:
                pass
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(
                label="Stop reminders",
                command=self._tray_pause,
                state=(tk.NORMAL if start_stop_enabled and not paused else tk.DISABLED),
            )
            menu.add_command(
                label="Start reminders",
                command=self._tray_resume,
                state=(tk.NORMAL if start_stop_enabled and paused else tk.DISABLED),
            )
            menu.add_separator()
            menu.add_command(label="Prompt now", command=self._tray_prompt_now)
            menu.add_command(label="Snooze 5 minutes", command=lambda: self._tray_snooze(5))
            menu.add_command(label="Snooze 15 minutes", command=lambda: self._tray_snooze(15))
            menu.add_separator()
            menu.add_command(
                label="Settings",
                command=self._open_settings_from_tray,
                state=(tk.NORMAL if settings_enabled else tk.DISABLED),
            )
            menu.add_command(
                label="Set/Change Task",
                command=self._open_task_dialog_from_tray,
                state=(tk.NORMAL if taskdb_available else tk.DISABLED),
            )
            menu.add_separator()
            if startup_enabled:
                menu.add_command(label="Disable Run on Startup", command=self._tray_uninstall_startup)
            else:
                menu.add_command(label="Enable Run on Startup", command=self._tray_install_startup)
            menu.add_command(label="Open Data Folder", command=self._tray_open_data_folder)
            menu.add_command(label="Open Logs Folder", command=self._tray_open_logs_folder)
            menu.add_separator()
            menu.add_command(
                label="Exit",
                command=self._tray_exit,
                state=(tk.NORMAL if exit_enabled else tk.DISABLED),
            )
            x = y = 0
            try:
                class POINT(ctypes.Structure):
                    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
                pt = POINT()
                ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
                x, y = pt.x, pt.y
            except Exception:
                pass
            try:
                menu.tk_popup(x, y)
            finally:
                try:
                    menu.grab_release()
                except Exception:
                    pass
        except Exception:
            pass


    def _set_paused(self, value: bool, *, source: str = "tray") -> bool:
        value = bool(value)
        current = bool(self.settings.get("paused", False))
        if current == value:
            return False
        self.settings["paused"] = value
        try:
            save_settings(self.settings)
        except Exception:
            pass
        try:
            get_logger().info("paused=%s via %s", value, source)
        except Exception:
            pass
        return True

    def _tray_toggle_pause(self):
        if not bool(self.settings.get("tray_start_stop_enabled", True)):
            return False
        if bool(self.settings.get("paused", False)):
            return self._tray_resume()
        return self._tray_pause()

    def _tray_pause(self):
        def _do_pause():
            changed = self._set_paused(True, source="tray_pause")
            try:
                if changed:
                    get_logger().info("tray: reminders paused")
            except Exception:
                pass
            poll_ms = int(self.settings.get("pause_poll_interval_seconds", 5)) * 1000
            self._schedule_next(poll_ms)
        return self._call_on_ui_thread(_do_pause)

    def _tray_resume(self):
        def _do_resume():
            changed = self._set_paused(False, source="tray_resume")
            try:
                if changed:
                    get_logger().info("tray: reminders resumed")
            except Exception:
                pass
            self._schedule_next()
        return self._call_on_ui_thread(_do_resume)

    def _tray_prompt_now(self):
        self._set_paused(False, source="tray_prompt")
        try:
            get_logger().info("tray: prompt requested immediately")
        except Exception:
            pass
        self._schedule_next(0)

    def _tray_snooze(self, minutes: int):
        try:
            minutes = int(minutes)
        except Exception:
            return
        ms = max(1, minutes) * 60_000
        self._set_paused(False, source=f"snooze_{minutes}m")
        try:
            get_logger().info("tray: snooze for %s minute(s)", minutes)
        except Exception:
            pass
        self._schedule_next(ms)

    def _is_startup_enabled(self) -> bool:
        try:
            return is_startup_installed(APP_NAME)
        except Exception:
            return False

    def _tray_install_startup(self):
        try:
            ok = install_startup(APP_NAME)
            if ok:
                messagebox.showinfo("Startup", "Enabled run on startup.")
        except Exception:
            pass

    def _tray_uninstall_startup(self):
        try:
            ok = uninstall_startup(APP_NAME)
            if ok:
                messagebox.showinfo("Startup", "Disabled run on startup.")
        except Exception:
            pass

    def _tray_open_data_folder(self):
        try:
            path = _get_data_dir()
            if platform.system().lower() == 'windows':
                os.startfile(path)
            else:
                subprocess.Popen(['xdg-open', path])
        except Exception:
            pass

    def _tray_open_logs_folder(self):
        try:
            path = os.path.dirname(APP_LOG_PATH)
            if platform.system().lower() == 'windows':
                os.startfile(path)
            else:
                subprocess.Popen(['xdg-open', path])
        except Exception:
            pass

    def _tray_exit(self):
        def _do_exit():
            try:
                if not bool(self.settings.get("tray_exit_button_enabled", True)):
                    return
            except Exception:
                pass
            self._quit()
        return self._call_on_ui_thread(_do_exit)

    def _open_settings_from_tray(self):
        def _show_settings():
            try:
                self.settings = load_settings()
            except Exception:
                pass
            def apply_and_refresh(new_settings):
                self.settings.update(new_settings)
            SettingsWindow(self.root, self.settings, on_save=apply_and_refresh)
        return self._call_on_ui_thread(_show_settings)

    def _open_task_dialog_from_tray(self):
        if getattr(self, "taskdb", None) is None:
            messagebox.showerror("Unavailable", "Task database not available.")
            return
        TaskEntryDialog(self.root, on_submit=self._on_new_task_from_tray)

    def _on_new_task_from_tray(self, data):
        try:
            title = data.get("title", "").strip()
            why = data.get("why", "").strip()
            cons = data.get("consequences", "").strip()
            due_iso = data.get("due_utc")
            if title:
                self.taskdb.start_task(title=title, due_utc=due_iso, why=why, consequences=cons)
        except Exception:
            pass

    def _quit(self):
        try:
            get_logger().info("quit requested")
        except Exception:
            pass
        try:
            if getattr(self, "_tray", None):
                self._tray.stop()
        except Exception:
            pass
        try:
            if getattr(self, "_winwatch", None):
                self._winwatch.close()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
        sys.exit(0)

    # Heartbeat file for watchdogs
    def _write_heartbeat(self):
        try:
            payload = {
                "utc": datetime.now(timezone.utc).isoformat(),
                "pid": os.getpid(),
                "paused": bool(self.settings.get("pause_when_inactive_or_lid_closed", True) and self.guard.should_pause()),
                "interval_seconds": int(self.settings.get("interval_seconds", 60)),
            }
            with open(HEARTBEAT_PATH, "w", encoding="utf-8") as f:
                json.dump(payload, f)
        except Exception:
            pass

    def _start_file_heartbeat(self):
        def hb():
            try:
                self._write_heartbeat()
            finally:
                self.root.after(60_000, hb)
        hb()

    def _log_startup_diagnostics(self):
        # Centralized diagnostics to help debug tray issues
        try:
            get_logger().info(
                "startup: python=%s | platform=%s | arch_bits=%s | tk=%s",
                sys.version.split()[0], platform.platform(), 8 * ctypes.sizeof(ctypes.c_void_p), getattr(tk, 'TkVersion', '?')
            )
        except Exception:
            pass
        # Environment details
        try:
            import site
            try:
                paths = site.getsitepackages()
            except Exception:
                paths = sys.path
            get_logger().info("startup: sys.executable=%s", sys.executable)
            get_logger().info("startup: site paths=%s", paths)
        except Exception:
            pass
        # Attempt to import pystray/Pillow explicitly for logging
        try:
            get_logger().info("startup: about to import pystray/Pillow")
        except Exception:
            pass
        # pystray
        try:
            import pystray  # type: ignore
            ver = getattr(pystray, '__version__', '?')
            get_logger().info("startup: pystray import OK | version=%s", ver)
        except Exception as e:
            try:
                get_logger().warning("startup: pystray import FAILED: %s", e)
            except Exception:
                pass
        # Pillow
        try:
            import PIL  # type: ignore
            pver = getattr(PIL, '__version__', '?')
            get_logger().info("startup: Pillow import OK | version=%s", pver)
        except Exception as e:
            try:
                get_logger().warning("startup: Pillow import FAILED: %s", e)
            except Exception:
                pass
        # system_tray module presence
        try:
            from importlib import import_module
            mod = None
            try:
                mod = import_module('system_tray')
            except Exception:
                mod = None
            get_logger().info("startup: system_tray module present=%s", bool(mod))
        except Exception:
            pass

    def run(self):
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            try:
                if getattr(self, "_winwatch", None):
                    self._winwatch.close()
            except Exception:
                pass
            # Clean up GDI+ resources
            try:
                _gdiplus_shutdown()
            except Exception:
                pass
            sys.exit(0)

# -------------------- Task Dialogs --------------------

class TaskEntryDialog(tk.Toplevel):
    """Dialog to enter a new current task with due and motivation info."""
    def __init__(self, master, on_submit):
        super().__init__(master)
        self.title("Set Current Task")
        self.configure(bg="#111")
        self.resizable(False, False)
        self.on_submit = on_submit

        pad = {"padx": 8, "pady": 4}
        def row(r, text):
            ttk.Label(self, text=text).grid(row=r, column=0, sticky="w", **pad)

        row(0, "Task title")
        self.title_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.title_var, width=48).grid(row=0, column=1, sticky="we", **pad)

        row(1, "Why are you doing this?")
        self.why_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.why_var, width=48).grid(row=1, column=1, sticky="we", **pad)

        row(2, "Consequences if not done")
        self.cons_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.cons_var, width=48).grid(row=2, column=1, sticky="we", **pad)

        row(3, "Expected completion")
        self.due_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.due_var, width=32).grid(row=3, column=1, sticky="w", **pad)
        ttk.Label(self, text="Enter minutes (e.g., 90) or time HH:MM").grid(row=4, column=1, sticky="w", padx=8)

        btns = ttk.Frame(self)
        btns.grid(row=5, column=0, columnspan=2, sticky="e", padx=8, pady=(8,8))
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right", padx=6)
        ttk.Button(btns, text="Save", command=self._save).pack(side="right")

        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _parse_due(self, txt):
        txt = (txt or "").strip()
        if not txt:
            return None
        # Minutes
        try:
            mins = int(txt)
            mins = max(1, mins)
            return (datetime.now(timezone.utc) + timedelta(minutes=mins)).isoformat()
        except Exception:
            pass
        # HH:MM => today or tomorrow if already passed
        try:
            parts = txt.split(":")
            if len(parts) == 2:
                hh = int(parts[0]); mm = int(parts[1])
                now_local = datetime.now().astimezone()
                due_local = now_local.replace(hour=hh, minute=mm, second=0, microsecond=0)
                if due_local < now_local:
                    due_local = due_local + timedelta(days=1)
                return due_local.astimezone(timezone.utc).isoformat()
        except Exception:
            pass
        return None

    def _save(self):
        title = self.title_var.get().strip()
        if not title:
            messagebox.showerror("Required", "Task title is required.")
            return
        due_iso = self._parse_due(self.due_var.get())
        payload = {
            "title": title,
            "why": self.why_var.get().strip(),
            "consequences": self.cons_var.get().strip(),
            "due_utc": due_iso,
        }
        try:
            self.on_submit(payload)
        except Exception:
            pass
        self.destroy()

class WastePromptDialog(tk.Toplevel):
    """Dialog shown when the user clicks 'Wasting time' if enabled.
    Captures what they're doing and optionally the consequences. Requires
    at least one of the fields to be non-empty.
    """
    def __init__(self, master, ask_what=True, ask_consequences=True, on_submit=None, on_cancel=None):
        super().__init__(master)
        self.title("Before you continue")
        self.configure(bg="#111")
        self.resizable(False, False)
        self.on_submit = on_submit
        self.on_cancel = on_cancel
        self.ask_what = bool(ask_what)
        self.ask_consequences = bool(ask_consequences)

        pad = {"padx": 8, "pady": 4}
        self.what_var = tk.StringVar()
        row = 0
        if self.ask_what:
            ttk.Label(self, text="What are you wasting time on?").grid(row=row, column=0, sticky="w", **pad)
            ttk.Entry(self, textvariable=self.what_var, width=56).grid(row=row, column=1, sticky="we", **pad)
            row += 1

        self.cons_var = tk.StringVar()
        if self.ask_consequences:
            ttk.Label(self, text="What are the consequences of this?").grid(row=row, column=0, sticky="w", **pad)
            ttk.Entry(self, textvariable=self.cons_var, width=56).grid(row=row, column=1, sticky="we", **pad)
            row += 1
        btn_row = row

        btns = ttk.Frame(self)
        btns.grid(row=btn_row, column=0, columnspan=2, sticky="e", padx=8, pady=(8,8))
        ttk.Button(btns, text="Cancel", command=self._cancel).pack(side="right", padx=6)
        ttk.Button(btns, text="Continue", command=self._save).pack(side="right")

        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _cancel(self):
        try:
            if self.on_cancel:
                self.on_cancel()
        except Exception:
            pass
        self.destroy()

    def _save(self):
        what = (self.what_var.get() or "").strip() if self.ask_what else ""
        cons = (self.cons_var.get() or "").strip() if self.ask_consequences else ""
        # Require at least one field if any are shown; otherwise allow empty
        if (self.ask_what or self.ask_consequences) and (not what and not cons):
            messagebox.showerror("Required", "Please fill at least one field or disable both in Settings.")
            return
        payload = {"what": what, "consequences": cons}
        try:
            if self.on_submit:
                self.on_submit(payload)
        except Exception:
            pass
        self.destroy()

class TaskChangeDialog(tk.Toplevel):
    """Dialog to capture reason for changing, and optionally define a new task."""
    def __init__(self, master, on_submit):
        super().__init__(master)
        self.title("Change Current Task")
        self.configure(bg="#111")
        self.resizable(False, False)
        self.on_submit = on_submit

        pad = {"padx": 8, "pady": 4}
        ttk.Label(self, text="Why are you changing this task? (required)").grid(row=0, column=0, columnspan=2, sticky="w", **pad)
        self.reason_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.reason_var, width=56).grid(row=1, column=0, columnspan=2, sticky="we", **pad)

        ttk.Separator(self).grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(6,6))
        ttk.Label(self, text="Optionally define the new task now:").grid(row=3, column=0, columnspan=2, sticky="w", **pad)

        ttk.Label(self, text="Task title").grid(row=4, column=0, sticky="w", **pad)
        self.title_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.title_var, width=48).grid(row=4, column=1, sticky="we", **pad)

        ttk.Label(self, text="Why").grid(row=5, column=0, sticky="w", **pad)
        self.why_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.why_var, width=48).grid(row=5, column=1, sticky="we", **pad)

        ttk.Label(self, text="Consequences").grid(row=6, column=0, sticky="w", **pad)
        self.cons_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.cons_var, width=48).grid(row=6, column=1, sticky="we", **pad)

        ttk.Label(self, text="Expected completion (minutes or HH:MM)").grid(row=7, column=0, sticky="w", **pad)
        self.due_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.due_var, width=32).grid(row=7, column=1, sticky="w", **pad)

        btns = ttk.Frame(self)
        btns.grid(row=8, column=0, columnspan=2, sticky="e", padx=8, pady=(8,8))
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right", padx=6)
        ttk.Button(btns, text="Save", command=self._save).pack(side="right")

        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _parse_due(self, txt):
        txt = (txt or "").strip()
        if not txt:
            return None
        try:
            mins = int(txt)
            mins = max(1, mins)
            return (datetime.now(timezone.utc) + timedelta(minutes=mins)).isoformat()
        except Exception:
            pass
        try:
            parts = txt.split(":")
            if len(parts) == 2:
                hh = int(parts[0]); mm = int(parts[1])
                now_local = datetime.now().astimezone()
                due_local = now_local.replace(hour=hh, minute=mm, second=0, microsecond=0)
                if due_local < now_local:
                    due_local = due_local + timedelta(days=1)
                return due_local.astimezone(timezone.utc).isoformat()
        except Exception:
            pass
        return None

    def _save(self):
        reason = self.reason_var.get().strip()
        if not reason:
            messagebox.showerror("Required", "Please provide a reason for changing the task.")
            return
        due_iso = self._parse_due(self.due_var.get())
        new_task = {
            "title": self.title_var.get().strip(),
            "why": self.why_var.get().strip(),
            "consequences": self.cons_var.get().strip(),
            "due_utc": due_iso,
        }
        try:
            self.on_submit({"reason": reason, "new_task": new_task})
        except Exception:
            pass
        self.destroy()


class TaskHistoryWindow(tk.Toplevel):
    """Popup window showing recent task history in a table."""
    def __init__(self, master, taskdb, limit=200):
        super().__init__(master)
        self.title("Task History")
        self.configure(bg="#111")
        self.resizable(True, True)
        self.taskdb = taskdb
        try:
            self.geometry("820x420")
        except Exception:
            pass

        container = tk.Frame(self, bg="#111")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        cols = ("id","created","title","status","due","completed","timed_out","change_reason")
        tree = ttk.Treeview(container, columns=cols, show="headings", height=16)
        vsb = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        tree.configure(yscroll=vsb.set)

        tree.heading("id", text="ID")
        tree.heading("created", text="Created")
        tree.heading("title", text="Title")
        tree.heading("status", text="Status")
        tree.heading("due", text="Due")
        tree.heading("completed", text="Completed")
        tree.heading("timed_out", text="Timed-out")
        tree.heading("change_reason", text="Change Reason")

        tree.column("id", width=50, anchor="e")
        tree.column("created", width=140, anchor="w")
        tree.column("title", width=220, anchor="w")
        tree.column("status", width=90, anchor="w")
        tree.column("due", width=140, anchor="w")
        tree.column("completed", width=140, anchor="w")
        tree.column("timed_out", width=80, anchor="center")
        tree.column("change_reason", width=200, anchor="w")

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

        # Populate
        data = []
        try:
            data = self.taskdb.list_history(limit=limit, include_active=True)
        except Exception:
            log_exception("TaskHistoryWindow: failed loading history")
        for d in data:
            tree.insert("", "end", values=(
                d.get("id"),
                self._fmt_local(d.get("created_utc")),
                d.get("title", ""),
                d.get("status", ""),
                self._fmt_local(d.get("due_utc")),
                self._fmt_local(d.get("completed_utc")),
                int(d.get("timed_out", 0)),
                d.get("change_reason", "") or "",
            ))

        # Footer
        btns = ttk.Frame(container)
        btns.grid(row=1, column=0, columnspan=2, sticky="e", pady=(8,0))
        ttk.Button(btns, text="Close", command=self.destroy).pack(side="right")

        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _fmt_local(self, iso):
        if not iso:
            return ""
        try:
            dt = datetime.fromisoformat(iso)
            return dt.astimezone().strftime("%Y-%m-%d %H:%M")
        except Exception:
            return str(iso)

if __name__ == "__main__":
    # Optional Windows startup management
    def _compose_startup_command():
        try:
            if getattr(sys, 'frozen', False):
                # Executable built by PyInstaller
                return f'"{sys.executable}"'
            # Fall back to python + script path for dev runs
            return f'"{sys.executable}" "{os.path.abspath(__file__)}"'
        except Exception:
            return os.path.abspath(sys.argv[0] or __file__)

    def install_startup(name: str = APP_NAME):
        if platform.system().lower() != 'windows':
            print("Startup install is supported on Windows only.")
            return False
        try:
            import winreg  # type: ignore
        except Exception:
            print("winreg unavailable; cannot install startup entry.")
            return False
        cmd = _compose_startup_command()
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            except FileNotFoundError:
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, cmd)
            winreg.CloseKey(key)
            try:
                get_logger().info("installed startup: %s -> %s", name, cmd)
            except Exception:
                pass
            print(f"Installed startup entry: {name} -> {cmd}")
            return True
        except Exception as e:
            try:
                get_logger().error("install_startup failed: %s", e)
            except Exception:
                pass
            print(f"Failed to install startup entry: {e}")
            return False

    def uninstall_startup(name: str = APP_NAME):
        if platform.system().lower() != 'windows':
            print("Startup uninstall is supported on Windows only.")
            return False
        try:
            import winreg  # type: ignore
        except Exception:
            print("winreg unavailable; cannot uninstall startup entry.")
            return False
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            try:
                winreg.DeleteValue(key, name)
                print(f"Removed startup entry: {name}")
            except FileNotFoundError:
                print(f"No startup entry named '{name}' found.")
            finally:
                winreg.CloseKey(key)
            try:
                get_logger().info("uninstalled startup: %s", name)
            except Exception:
                pass
            return True
        except Exception as e:
            try:
                get_logger().error("uninstall_startup failed: %s", e)
            except Exception:
                pass
            print(f"Failed to uninstall startup entry: {e}")
            return False

    # Capture uncaught exceptions to the app log
    def _global_excepthook(exc_type, exc, tb):
        try:
            get_logger().exception("UNCAUGHT: %s", exc)
        except Exception:
            pass
        # Also print to stderr for interactive debugging
        try:
            sys.__excepthook__(exc_type, exc, tb)
        except Exception:
            pass
    try:
        sys.excepthook = _global_excepthook
    except Exception:
        pass
    # Lightweight internal diagnostic when requested
    if "--selftest" in sys.argv:
        try:
            print("selftest: python_bits=", 8 * ctypes.sizeof(ctypes.c_void_p))
            if platform.system().lower() == "windows":
                r = tk.Tk(); r.withdraw()
                # Hook watcher
                ev = {"pause": 0, "resume": 0}
                def on_resume(): ev["resume"] += 1
                def on_pause(_): ev["pause"] += 1
                w = _WindowsWakeWatcher(r, on_resume_callable=on_resume, on_pause_callable=on_pause)
                hwnd = r.winfo_id()
                # Stress callback path with typical messages and large params
                try:
                    _ = w._proc(hwnd, WM_WTSSESSION_CHANGE, WPARAM_T(WTS_SESSION_LOCK), LPARAM_T(0))
                    _ = w._proc(hwnd, WM_WTSSESSION_CHANGE, WPARAM_T(WTS_SESSION_UNLOCK), LPARAM_T(0))
                    _ = w._proc(hwnd, WM_POWERBROADCAST, WPARAM_T(PBT_APMSUSPEND), LPARAM_T(0))
                    _ = w._proc(hwnd, WM_POWERBROADCAST, WPARAM_T(PBT_APMRESUMESUSPEND), LPARAM_T(0))
                    # Large values to ensure no overflow on 64-bit
                    _ = w._proc(hwnd, 0xFFFF, WPARAM_T(0xFFFFFFFFFFFFFFFF), LPARAM_T(-1))
                finally:
                    w.close(); r.destroy()
                print("selftest: windows callback path OK, ev=", ev)
            else:
                print("selftest: non-windows platform, skipping winproc test")
        except Exception as e:
            print("selftest: FAILED:", e)
            sys.exit(1)
        sys.exit(0)
    else:
        if "--tray-selftest" in sys.argv:
            # One-shot pystray selftest (~10s)
            try:
                from system_tray_selftest import main as _tray_selftest_main
                _tray_selftest_main()
            except Exception as e:
                try:
                    get_logger().exception("tray-selftest failed", exc_info=True)
                except Exception:
                    print(f"tray-selftest failed: {e}", file=sys.stderr)
                sys.exit(1)
        # Simple CLI for startup management
        if "--install-startup" in sys.argv:
            ok = install_startup()
            sys.exit(0 if ok else 1)
        if "--uninstall-startup" in sys.argv:
            ok = uninstall_startup()
            sys.exit(0 if ok else 1)
        if "--tray-test" in sys.argv:
            # Minimal tray-only test for 20 seconds
            r = tk.Tk(); r.withdraw(); r.update_idletasks()
            try:
                w = _WindowsWakeWatcher(r, on_resume_callable=lambda: None, tray_enabled=True, on_tray_click_callable=lambda _=None: None, tray_tooltip="Focus Check")
                tk.Label(r, text="Tray test running...")
            except Exception as e:
                print(f"Tray test failed: {e}", file=sys.stderr)
                sys.exit(1)
            r.after(20000, lambda: (w.close(), r.destroy()))
            r.mainloop()
            sys.exit(0)
        if not acquire_single_instance():
            print("Another instance is already running. Exiting.", file=sys.stderr)
            sys.exit(0)
        App().run()









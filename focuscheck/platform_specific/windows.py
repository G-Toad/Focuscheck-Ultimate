"""
Windows-specific functionality.

This module contains Windows-specific code extracted from guard.py.
"""

import os
import uuid
import ctypes
from ctypes import wintypes
from typing import Optional
from ..utils.timers import TimerRegistry

# Pointer-sized result type for window procedures on 32/64-bit
LRESULT = getattr(wintypes, 'LRESULT', ctypes.c_ssize_t)
WPARAM_T = getattr(wintypes, 'WPARAM', ctypes.c_size_t)
LPARAM_T = getattr(wintypes, 'LPARAM', ctypes.c_ssize_t)
LONG_PTR = ctypes.c_ssize_t

# Windows constants
GWL_WNDPROC = -4
GWL_EXSTYLE = -20
GWL_STYLE = -16
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
WM_NCHITTEST = 0x0084
HTTRANSPARENT = -1
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205
WM_CONTEXTMENU = 0x007B
WM_DISPLAYCHANGE = 0x007E
WM_QUERYENDSESSION = 0x0011
WM_ENDSESSION = 0x0016
WM_DPICHANGED = 0x02E0

# Windows session / power constants
WM_WTSSESSION_CHANGE = 0x02B1
WTS_SESSION_LOCK = 0x7
WTS_SESSION_UNLOCK = 0x8
WM_POWERBROADCAST = 0x0218
PBT_APMSUSPEND = 0x0004
PBT_APMRESUMESUSPEND = 0x0007
PBT_APMRESUMESTANDBY = 0x0008
PBT_APMRESUMEAUTOMATIC = 0x0012


def classify_watcher_message(msg, wparam, lparam, *, tray_message=0, taskbar_created=0):
    """Translate native watcher messages into platform-independent events."""
    if msg == WM_WTSSESSION_CHANGE:
        if wparam == WTS_SESSION_UNLOCK:
            return ("resume", None)
        if wparam == WTS_SESSION_LOCK:
            return ("pause", "lock")
    elif msg == WM_POWERBROADCAST:
        if wparam in (PBT_APMRESUMEAUTOMATIC, PBT_APMRESUMESUSPEND, PBT_APMRESUMESTANDBY):
            return ("resume", None)
        if wparam == PBT_APMSUSPEND:
            return ("pause", "sleep")
    elif msg in (WM_DISPLAYCHANGE, WM_DPICHANGED):
        return ("display_change", None)
    elif tray_message and msg == tray_message and int(lparam) in (WM_RBUTTONUP, WM_LBUTTONUP, WM_CONTEXTMENU):
        return ("tray_click", int(lparam))
    elif msg == WM_QUERYENDSESSION:
        return ("shutdown", "query_end_session")
    elif msg == WM_ENDSESSION and bool(wparam):
        return ("shutdown", "end_session")
    elif taskbar_created and msg == taskbar_created:
        return ("taskbar_created", None)
    return None

# GDI+ token (global)
_GDIPLUS_TOKEN = None
_win_overlay_class_atom = None
_win_overlay_wndproc = None

if not hasattr(wintypes, "HCURSOR"):
    HCURSOR = wintypes.HANDLE
else:
    HCURSOR = wintypes.HCURSOR


def _user32():
    return ctypes.WinDLL("user32", use_last_error=True)


def _gdi32():
    return ctypes.WinDLL("gdi32", use_last_error=True)


def _kernel32():
    return ctypes.WinDLL("kernel32", use_last_error=True)


def _configure_overlay_api(user32, gdi32, kernel32):
    """Declare the native signatures used by the overlay lifecycle."""
    user32.RegisterClassExW.argtypes = [ctypes.c_void_p]
    user32.RegisterClassExW.restype = wintypes.ATOM
    user32.CreateWindowExW.argtypes = [
        wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, ctypes.c_void_p,
    ]
    user32.CreateWindowExW.restype = wintypes.HWND
    user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM_T, LPARAM_T]
    user32.DefWindowProcW.restype = LRESULT
    user32.BeginPaint.argtypes = [wintypes.HWND, ctypes.c_void_p]
    user32.BeginPaint.restype = wintypes.HDC
    user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetClientRect.restype = wintypes.BOOL
    user32.EndPaint.argtypes = [wintypes.HWND, ctypes.c_void_p]
    user32.EndPaint.restype = wintypes.BOOL
    user32.FillRect.argtypes = [wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.HBRUSH]
    user32.FillRect.restype = ctypes.c_int
    user32.GetClassLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetClassLongPtrW.restype = LONG_PTR
    user32.GetClassLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetClassLongW.restype = ctypes.c_ulong
    user32.SetClassLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, LONG_PTR]
    user32.SetClassLongPtrW.restype = LONG_PTR
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    user32.SetWindowPos.argtypes = [
        wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_int, wintypes.UINT,
    ]
    user32.SetWindowPos.restype = wintypes.BOOL
    user32.RedrawWindow.argtypes = [
        wintypes.HWND, ctypes.POINTER(wintypes.RECT), wintypes.HRGN, wintypes.UINT,
    ]
    user32.RedrawWindow.restype = wintypes.BOOL
    user32.SetLayeredWindowAttributes.argtypes = [
        wintypes.HWND, wintypes.COLORREF, wintypes.BYTE, wintypes.DWORD,
    ]
    user32.SetLayeredWindowAttributes.restype = wintypes.BOOL
    user32.DestroyWindow.argtypes = [wintypes.HWND]
    user32.DestroyWindow.restype = wintypes.BOOL

    gdi32.CreateSolidBrush.argtypes = [wintypes.COLORREF]
    gdi32.CreateSolidBrush.restype = wintypes.HBRUSH
    gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi32.DeleteObject.restype = wintypes.BOOL
    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE


def _configure_window_style_api(user32):
    """Declare signatures shared by click-through and WNDPROC helpers."""
    for name, restype, argtypes in (
        ("GetWindowLongPtrW", LONG_PTR, [wintypes.HWND, ctypes.c_int]),
        ("SetWindowLongPtrW", LONG_PTR, [wintypes.HWND, ctypes.c_int, LONG_PTR]),
        ("GetWindowLongW", ctypes.c_long, [wintypes.HWND, ctypes.c_int]),
        ("SetWindowLongW", ctypes.c_long, [wintypes.HWND, ctypes.c_int, ctypes.c_long]),
    ):
        try:
            function = getattr(user32, name)
            function.argtypes = argtypes
            function.restype = restype
        except AttributeError:
            pass
    user32.SetWindowPos.argtypes = [
        wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_int, wintypes.UINT,
    ]
    user32.SetWindowPos.restype = wintypes.BOOL
    user32.CallWindowProcW.argtypes = [
        ctypes.c_void_p, wintypes.HWND, wintypes.UINT, WPARAM_T, LPARAM_T,
    ]
    user32.CallWindowProcW.restype = LRESULT
    user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM_T, LPARAM_T]
    user32.DefWindowProcW.restype = LRESULT


def _configure_watcher_user32_api(user32):
    """Declare User32 signatures used by the session/tray watcher."""
    user32.RegisterWindowMessageW.argtypes = [wintypes.LPCWSTR]
    user32.RegisterWindowMessageW.restype = wintypes.UINT
    user32.GetSystemMetrics.argtypes = [ctypes.c_int]
    user32.GetSystemMetrics.restype = ctypes.c_int
    user32.LoadImageW.argtypes = [
        wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT,
        ctypes.c_int, ctypes.c_int, wintypes.UINT,
    ]
    user32.LoadImageW.restype = wintypes.HANDLE
    user32.LoadIconW.argtypes = [wintypes.HINSTANCE, ctypes.c_void_p]
    user32.LoadIconW.restype = wintypes.HICON
    user32.DestroyIcon.argtypes = [wintypes.HICON]
    user32.DestroyIcon.restype = wintypes.BOOL
    user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM_T, LPARAM_T]
    user32.DefWindowProcW.restype = LRESULT


def _get_last_error_info():
    try:
        code = ctypes.get_last_error()
        if not code:
            code = _kernel32().GetLastError()
        msg = ""
        try:
            FORMAT_MESSAGE_FROM_SYSTEM = 0x00001000
            FORMAT_MESSAGE_IGNORE_INSERTS = 0x00000200
            buf = ctypes.create_unicode_buffer(1024)
            _kernel32().FormatMessageW(
                FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS,
                None,
                code,
                0,
                buf,
                len(buf),
                None,
            )
            msg = buf.value.strip()
        except Exception:
            msg = ""
        return int(code), msg
    except Exception:
        return None, ""


def _get_window_long_ptr(hwnd, index):
    user32 = _user32()
    try:
        GetWindowLongPtrW = user32.GetWindowLongPtrW
        GetWindowLongPtrW.restype = LONG_PTR
        GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
        return int(GetWindowLongPtrW(hwnd, index))
    except Exception:
        GetWindowLongW = user32.GetWindowLongW
        GetWindowLongW.restype = ctypes.c_long
        GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
        return int(GetWindowLongW(hwnd, index))


def enable_click_through_windows(hwnd):
    """Helper: reliably enable click-through on Windows (64-bit safe)."""
    try:
        user32 = _user32()
        _configure_window_style_api(user32)
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
        SWP_FRAMECHANGED = 0x0020
        return bool(user32.SetWindowPos(
            hwnd, None, 0, 0, 0, 0,
            SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
        ))
    except Exception:
        return False


def install_httransparent_wndproc(hwnd, owner_widget=None):
    """Subclass WNDPROC to make the window return HTTRANSPARENT on WM_NCHITTEST.
    Keeps references on owner_widget to avoid GC and restores on destroy.
    """
    try:
        user32 = _user32()
        _configure_window_style_api(user32)
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
        WNDPROC = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)(
            LRESULT, wintypes.HWND, wintypes.UINT, WPARAM_T, LPARAM_T
        )
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
                return user32.DefWindowProcW(h, msg, wParam, lParam)
        installed = SetWindowLongPtrW(hwnd, GWL_WNDPROC, proc)
        if not installed:
            return False
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


class WinClickThroughOverlay:
    """Native Windows click-through overlay (robust for Windows 10/11)."""
    def __init__(self, x, y, w, h, color_hex="#000000", log_tag=None):
        self._log_tag = log_tag or "overlay"
        self.hwnd = None
        self._brush = None
        self._register_class()
        self._create_window(x, y, w, h, color_hex)

    def _register_class(self):
        global _win_overlay_class_atom, _win_overlay_wndproc
        if _win_overlay_class_atom is not None:
            self._atom = _win_overlay_class_atom
            self._proc = _win_overlay_wndproc
            return
        user32 = _user32()
        gdi32 = _gdi32()
        _configure_overlay_api(user32, gdi32, _kernel32())
        class WNDCLASSEXW(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_uint),
                ("style", ctypes.c_uint),
                ("lpfnWndProc", ctypes.c_void_p),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HINSTANCE),
                ("hIcon", wintypes.HICON),
                ("hCursor", HCURSOR),
                ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR),
                ("hIconSm", wintypes.HICON),
            ]
        WNDPROC = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)(
            LRESULT, wintypes.HWND, wintypes.UINT, WPARAM_T, LPARAM_T
        )
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
                    hbr = user32.GetClassLongPtrW(h, -10)
                except Exception:
                    hbr = user32.GetClassLongW(h, -10)
                user32.FillRect(hdc, ctypes.byref(rect), hbr)
                user32.EndPaint(h, ctypes.byref(ps))
                return 0
            return user32.DefWindowProcW(h, msg, wParam, lParam)

        try:
            user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM_T, LPARAM_T]
            user32.DefWindowProcW.restype = LRESULT
        except Exception:
            pass
        hinst = _kernel32().GetModuleHandleW(None)
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
        try:
            ctypes.set_last_error(0)
        except Exception:
            pass
        atom = user32.RegisterClassExW(ctypes.byref(wc))
        if not atom:
            code, msg = _get_last_error_info()
            try:
                from ..utils import get_logger
                get_logger().error("%s: RegisterClassExW failed | err=%s msg=%s", self._log_tag, code, msg)
            except Exception:
                pass
            # If already registered, proceed
            atom = user32.RegisterClassExW(ctypes.byref(wc))
        _win_overlay_class_atom = atom
        _win_overlay_wndproc = _proc
        self._atom = atom
        self._proc = _proc  # keep ref

    def _create_window(self, x, y, w, h, color_hex):
        user32 = _user32()
        gdi32 = _gdi32()
        _configure_overlay_api(user32, gdi32, _kernel32())
        hinst = _kernel32().GetModuleHandleW(None)
        # Create popup layered transparent, topmost, no-activate toolwindow
        ex = (WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOPMOST | WS_EX_TOOLWINDOW)
        style = WS_POPUP
        try:
            from ..utils import get_logger
            get_logger().info(
                "%s: creating native overlay | rect=%sx%s+%s+%s exstyle=0x%08X style=0x%08X",
                self._log_tag, int(w), int(h), int(x), int(y), ex, style,
            )
        except Exception:
            pass
        try:
            ctypes.set_last_error(0)
        except Exception:
            pass
        self.hwnd = user32.CreateWindowExW(
            ex,
            "FocusCheckOverlayClass",
            None,
            style,
            int(x), int(y), int(w), int(h),
            None, None, hinst, None
        )
        if not self.hwnd:
            code, msg = _get_last_error_info()
            try:
                from ..utils import get_logger
                get_logger().error("%s: CreateWindowExW failed | err=%s msg=%s", self._log_tag, code, msg)
            except Exception:
                pass
            raise RuntimeError(f"CreateWindowExW failed for overlay | err={code} msg={msg}")
        try:
            exstyle_actual = _get_window_long_ptr(self.hwnd, GWL_EXSTYLE)
            style_actual = _get_window_long_ptr(self.hwnd, GWL_STYLE)
            from ..utils import get_logger
            get_logger().info(
                "%s: created hwnd=%s exstyle=0x%08X style=0x%08X",
                self._log_tag, int(self.hwnd), int(exstyle_actual), int(style_actual),
            )
        except Exception:
            pass
        # Set background brush color
        r,g,b = _parse_rgb_hex(color_hex)
        RGB = lambda R,G,B: R | (G << 8) | (B << 16)
        hbrush = gdi32.CreateSolidBrush(RGB(r,g,b))
        self._brush = hbrush
        GCLP_HBRBACKGROUND = -10
        try:
            user32.SetClassLongPtrW(self.hwnd, GCLP_HBRBACKGROUND, hbrush)
        except Exception:
            user32.SetClassLongW(self.hwnd, GCLP_HBRBACKGROUND, hbrush)
        # Show without activation
        try:
            ctypes.set_last_error(0)
            user32.ShowWindow(self.hwnd, SW_SHOWNOACTIVATE)
            from ..utils import get_logger
            get_logger().info("%s: show window", self._log_tag)
        except Exception:
            pass
        try:
            positioned = user32.SetWindowPos(
                self.hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
            )
            if not positioned:
                code, msg = _get_last_error_info()
                from ..utils import get_logger
                get_logger().warning("%s: SetWindowPos failed | err=%s msg=%s", self._log_tag, code, msg)
                self.destroy()
                raise RuntimeError(f"SetWindowPos failed for overlay | err={code} msg={msg}")
        except Exception:
            if self.hwnd:
                self.destroy()
            raise
        # Initial alpha 0
        if not self.set_alpha(0.0):
            self.destroy()
            raise RuntimeError("SetLayeredWindowAttributes failed for overlay")
        try:
            user32.RedrawWindow(self.hwnd, None, None, 0x0001)
        except Exception:
            pass

    def set_alpha(self, a):
        try:
            a = max(0.0, min(1.0, float(a)))
        except Exception:
            a = 0.0
        alpha = int(a * 255) & 0xFF
        try:
            ctypes.set_last_error(0)
        except Exception:
            pass
        ok = _user32().SetLayeredWindowAttributes(self.hwnd, 0, alpha, LWA_ALPHA)
        if not ok:
            code, msg = _get_last_error_info()
            try:
                from ..utils import get_logger
                get_logger().error("%s: SetLayeredWindowAttributes failed | err=%s msg=%s", self._log_tag, code, msg)
            except Exception:
                pass
        else:
            try:
                from ..utils import get_logger
                get_logger().info("%s: set alpha=%s", self._log_tag, alpha)
            except Exception:
                pass
        return bool(ok)

    def destroy(self):
        brush = self._brush
        hwnd = self.hwnd
        if hwnd:
            try:
                result = _user32().DestroyWindow(hwnd)
                # ctypes returns a BOOL; None is retained as compatibility for
                # lightweight test doubles that do not model return values.
                if result is not None and not bool(result):
                    return False
            except Exception:
                return False
        self.hwnd = None
        self._brush = None
        try:
            if brush:
                _gdi32().DeleteObject(brush)
        except Exception:
            pass
        return True


class _GdiplusStartupInput(ctypes.Structure):
    _fields_ = [
        ("GdiplusVersion", ctypes.c_uint32),
        ("DebugEventCallback", ctypes.c_void_p),
        ("SuppressBackgroundThread", wintypes.BOOL),
        ("SuppressExternalCodecs", wintypes.BOOL),
    ]


def _configure_gdiplus_api(gdiplus):
    """Declare signatures for GDI+ startup and icon conversion calls."""
    gdiplus.GdiplusStartup.argtypes = [
        ctypes.POINTER(ctypes.c_ulonglong),
        ctypes.POINTER(_GdiplusStartupInput),
        ctypes.c_void_p,
    ]
    gdiplus.GdiplusStartup.restype = ctypes.c_int
    gdiplus.GdiplusShutdown.argtypes = [ctypes.c_ulonglong]
    gdiplus.GdiplusShutdown.restype = None
    gdiplus.GdipCreateBitmapFromFile.argtypes = [
        ctypes.c_wchar_p,
        ctypes.POINTER(ctypes.c_void_p),
    ]
    gdiplus.GdipCreateBitmapFromFile.restype = ctypes.c_int
    gdiplus.GdipCreateHICONFromBitmap.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(wintypes.HICON),
    ]
    gdiplus.GdipCreateHICONFromBitmap.restype = ctypes.c_int
    gdiplus.GdipDisposeImage.argtypes = [ctypes.c_void_p]
    gdiplus.GdipDisposeImage.restype = ctypes.c_int


def ensure_gdiplus_started() -> bool:
    """Ensure GDI+ is initialized."""
    global _GDIPLUS_TOKEN
    if _GDIPLUS_TOKEN is not None:
        return True
    try:
        gdiplus = ctypes.windll.gdiplus
        _configure_gdiplus_api(gdiplus)
    except Exception:
        return False
    startup_input = _GdiplusStartupInput(1, None, False, False)
    token = ctypes.c_ulonglong()
    status = gdiplus.GdiplusStartup(ctypes.byref(token), ctypes.byref(startup_input), None)
    if status != 0:
        return False
    _GDIPLUS_TOKEN = token
    return True


def gdiplus_shutdown():
    """Clean up GDI+ resources on application exit."""
    global _GDIPLUS_TOKEN
    if _GDIPLUS_TOKEN is not None:
        try:
            gdiplus = ctypes.windll.gdiplus
            _configure_gdiplus_api(gdiplus)
            gdiplus.GdiplusShutdown(_GDIPLUS_TOKEN)
        except Exception:
            pass
        _GDIPLUS_TOKEN = None


def create_hicon_from_image(path: str) -> Optional[wintypes.HICON]:
    """Create HICON from image file using GDI+."""
    if not path or not os.path.exists(path):
        return None
    if os.path.splitext(path)[1].lower() == ".ico":
        return None  # handled by LoadImageW
    if not ensure_gdiplus_started():
        return None
    gdiplus = ctypes.windll.gdiplus
    _configure_gdiplus_api(gdiplus)
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


class WindowsWakeWatcher:
    """Hooks the Tk root window proc to receive lock/unlock (WTS), sleep/resume (power),
    display/DPI changes, and tray icon callbacks. Keeps references to callbacks to avoid GC."""

    def __init__(self, root, on_resume_callable, on_pause_callable=None,
                 on_display_change_callable=None, tray_enabled=False,
                 on_tray_click_callable=None, tray_tooltip="Focus Check",
                 tray_icon_path=None, on_shutdown_callable=None):
        # Import here to avoid circular dependency
        from focuscheck.utils import get_logger, log_exception, resource_path

        self.root = root
        self.on_resume = on_resume_callable
        self.on_pause = on_pause_callable
        self.on_display_change = on_display_change_callable
        self.on_shutdown = on_shutdown_callable
        self.on_tray_click = on_tray_click_callable
        self.hwnd = root.winfo_id()
        self._tray_enabled = bool(tray_enabled)
        self._tray_added = False
        self._tray_id = 1
        self._hicon = None
        self._tray_icon_path = tray_icon_path
        self._closed = False
        self._timers = TimerRegistry(root)

        # API handles
        user32 = ctypes.windll.user32
        _configure_window_style_api(user32)
        _configure_watcher_user32_api(user32)
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
        self._DestroyIcon = user32.DestroyIcon

        # Old proc
        self._old_wndproc = self._GetWindowLongPtrW(self.hwnd, GWL_WNDPROC)

        # WNDPROC prototype (pointer-sized return type)
        WNDPROC = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)(
            LRESULT, wintypes.HWND, wintypes.UINT, WPARAM_T, LPARAM_T
        )

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
                event = classify_watcher_message(
                    msg,
                    wParam,
                    lParam,
                    tray_message=self._TRAY_MSG,
                    taskbar_created=self._TaskbarCreated,
                )
                if event == ("resume", None):
                    self._schedule_ui("session-resume", 0, self.on_resume)
                elif event and event[0] == "pause":
                    if self.on_pause:
                        self._schedule_ui(f"session-{event[1]}", 0, lambda reason=event[1]: self.on_pause(reason))
                elif event == ("display_change", None):
                    if self.on_display_change:
                        self._schedule_ui("display-change", 50, self.on_display_change)
                elif event and event[0] == "tray_click":
                    if self.on_tray_click:
                        self._schedule_ui("tray-click", 0, lambda code=event[1]: self.on_tray_click(code))
                elif event == ("shutdown", "query_end_session"):
                    if self.on_shutdown:
                        self._schedule_ui("query-end-session", 0, lambda: self.on_shutdown("query_end_session"))
                    return LRESULT(1)
                elif event == ("shutdown", "end_session") and self.on_shutdown:
                    self._schedule_ui("end-session", 0, lambda: self.on_shutdown("end_session"))
                elif event == ("taskbar_created", None):
                    # Explorer restarted; re-add tray icon.
                    self._tray_added = False
                    if self._tray_enabled:
                        self._schedule_ui("taskbar-created", 200, lambda: self._tray_add("Focus Check"))
            except Exception:
                pass
            try:
                if not self._old_wndproc:
                    return user32.DefWindowProcW(hwnd, msg, wParam, lParam)
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

    def _schedule_ui(self, name, delay_ms, callback):
        """Post a generation-aware callback while the watcher is live."""
        if self._closed:
            return False
        return self._timers.schedule(name, delay_ms, callback)

    def _tray_add(self, tooltip_text):
        from focuscheck.utils import get_logger, resource_path

        if self._Shell_NotifyIconW is None or self._tray_added:
            return
        user32 = ctypes.windll.user32
        _configure_watcher_user32_api(user32)
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
                resource_path(os.path.join("assets", "focus.ico")),
                resource_path("focus.ico"),
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
                    h = create_hicon_from_image(candidate)
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
                destroy_icon = getattr(self, "_DestroyIcon", None)
                if destroy_icon is None:
                    user32 = ctypes.windll.user32
                    _configure_watcher_user32_api(user32)
                    destroy_icon = user32.DestroyIcon
                destroy_icon(self._hicon)
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
        if self._closed:
            return
        self._closed = True
        try:
            self._timers.close()
        except Exception:
            pass
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


__all__ = [
    'enable_click_through_windows',
    'install_httransparent_wndproc',
    'WindowsWakeWatcher',
    'classify_watcher_message',
    'WinClickThroughOverlay',
    'ensure_gdiplus_started',
    'gdiplus_shutdown',
    'create_hicon_from_image',
    # Constants
    'WM_WTSSESSION_CHANGE',
    'WTS_SESSION_LOCK',
    'WTS_SESSION_UNLOCK',
    'WM_POWERBROADCAST',
    'PBT_APMSUSPEND',
    'PBT_APMRESUMESUSPEND',
    'WPARAM_T',
    'LPARAM_T',
]

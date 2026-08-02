"""
Windows-specific utilities for dialog overlays and click-through functionality.

Contains helper functions and classes for Windows-specific window manipulation,
including click-through overlays and transparent windows.
"""

import ctypes
from ctypes import wintypes

# Windows constants for extended functionality
try:
    GWL_WNDPROC = -4
    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020
    WS_EX_NOACTIVATE = 0x08000000
    LRESULT = getattr(wintypes, 'LRESULT', ctypes.c_ssize_t)
    WPARAM_T = getattr(wintypes, 'WPARAM', ctypes.c_size_t)
    LPARAM_T = getattr(wintypes, 'LPARAM', ctypes.c_ssize_t)
    LONG_PTR = ctypes.c_ssize_t
    WM_NCHITTEST = 0x0084
    HTTRANSPARENT = -1
except Exception:
    pass


def _enable_click_through_windows(hwnd):
    """Enable click-through on a Windows window."""
    try:
        user32 = ctypes.windll.user32
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
            GetWindowLongW = user32.GetWindowLongW
            SetWindowLongW = user32.SetWindowLongW
            GetWindowLongW.restype = ctypes.c_long
            GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
            SetWindowLongW.restype = ctypes.c_long
            SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
            exstyle = int(GetWindowLongW(hwnd, GWL_EXSTYLE))
            exstyle |= (WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE)
            _ = SetWindowLongW(hwnd, GWL_EXSTYLE, ctypes.c_long(exstyle))
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
    """Subclass WNDPROC to make the window return HTTRANSPARENT on WM_NCHITTEST."""
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


# Native Windows click-through overlay class
_win_overlay_class_atom = None


class _WinClickThroughOverlay:
    """Robust native Windows overlay with click-through support."""
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
        def wnd_proc(hwnd, msg, wParam, lParam):
            if msg == WM_NCHITTEST:
                return LRESULT(HTTRANSPARENT)
            return user32.DefWindowProcW(hwnd, msg, wParam, lParam)
        self._wnd_proc = wnd_proc
        hInstance = ctypes.windll.kernel32.GetModuleHandleW(None)
        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.lpfnWndProc = ctypes.cast(wnd_proc, ctypes.c_void_p)
        wc.hInstance = hInstance
        wc.lpszClassName = "FocusCheckOverlayClass"
        atom = user32.RegisterClassExW(ctypes.byref(wc))
        if not atom:
            raise RuntimeError("RegisterClassExW failed")
        _win_overlay_class_atom = atom
        self._atom = atom

    def _create_window(self, x, y, w, h, color_hex):
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        WS_POPUP = 0x80000000
        WS_EX_LAYERED = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020
        WS_EX_NOACTIVATE = 0x08000000
        WS_EX_TOPMOST = 0x00000008
        SW_SHOWNOACTIVATE = 4
        HWND_TOPMOST = -1
        LWA_ALPHA = 0x00000002
        SWP_NOACTIVATE = 0x0010
        SWP_SHOWWINDOW = 0x0040
        r, g, b = self._parse_rgb_hex(color_hex)
        hInstance = ctypes.windll.kernel32.GetModuleHandleW(None)
        self.hwnd = user32.CreateWindowExW(
            WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOPMOST,
            "FocusCheckOverlayClass",
            "FocusCheckOverlay",
            WS_POPUP,
            x, y, w, h,
            None, None, hInstance, None
        )
        if not self.hwnd:
            raise RuntimeError("CreateWindowExW failed")
        self._brush = gdi32.CreateSolidBrush((b << 16) | (g << 8) | r)
        user32.SetLayeredWindowAttributes(self.hwnd, 0, 0, LWA_ALPHA)
        user32.SetWindowPos(self.hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOACTIVATE | SWP_SHOWWINDOW | 0x0001 | 0x0002)
        user32.ShowWindow(self.hwnd, SW_SHOWNOACTIVATE)

    def _parse_rgb_hex(self, s, default=(0,0,0)):
        try:
            t = str(s or "#000000").strip()
            if t.startswith('#') and len(t) == 7:
                hex_part = t[1:]
                if all(c in '0123456789abcdefABCDEF' for c in hex_part):
                    r = int(t[1:3], 16); g = int(t[3:5], 16); b = int(t[5:7], 16)
                    return (r,g,b)
        except (ValueError, TypeError):
            pass
        return default

    def get_hwnd(self):
        """Get the window handle for Z-order positioning."""
        return self.hwnd

    def set_alpha(self, alpha):
        if not self.hwnd:
            return
        try:
            a = int(max(0, min(255, alpha * 255)))
            LWA_ALPHA = 0x00000002
            ctypes.windll.user32.SetLayeredWindowAttributes(self.hwnd, 0, a, LWA_ALPHA)
        except Exception:
            pass

    def destroy(self):
        if self.hwnd:
            try:
                ctypes.windll.user32.DestroyWindow(self.hwnd)
            except Exception:
                pass
            self.hwnd = None
        if self._brush:
            try:
                ctypes.windll.gdi32.DeleteObject(self._brush)
            except Exception:
                pass
            self._brush = None

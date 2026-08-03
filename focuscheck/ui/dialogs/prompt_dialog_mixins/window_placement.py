"""
Window placement mixin for PromptDialog.

Contains methods for positioning the dialog window on screen,
including multi-monitor support and cursor tracking.
"""

import platform
import ctypes
from ctypes import wintypes

LPARAM_T = getattr(wintypes, "LPARAM", ctypes.c_ssize_t)


def _configure_monitor_api(user32):
    """Declare pointer-safe signatures for monitor placement operations."""
    user32.EnumDisplayMonitors.argtypes = [
        wintypes.HDC, ctypes.c_void_p, ctypes.c_void_p, LPARAM_T,
    ]
    user32.EnumDisplayMonitors.restype = wintypes.BOOL
    user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    user32.GetMonitorInfoW.restype = wintypes.BOOL
    user32.GetCursorPos.argtypes = [ctypes.c_void_p]
    user32.GetCursorPos.restype = wintypes.BOOL
    user32.MonitorFromPoint.argtypes = [ctypes.c_void_p, wintypes.DWORD]
    user32.MonitorFromPoint.restype = wintypes.HANDLE
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.c_void_p]
    user32.GetWindowRect.restype = wintypes.BOOL


class WindowPlacementMixin:
    """Mixin for window positioning and placement in PromptDialog."""

    def _get_specific_monitor_workarea(self, monitor_index):
        """
        Return (l, t, r, b) work area for a specific monitor by index.

        Args:
            monitor_index: 0 for primary, 1 for second, etc.

        Returns:
            Tuple of (left, top, right, bottom) coordinates
        """
        try:
            if platform.system().lower() == "windows":
                user32 = ctypes.windll.user32
                _configure_monitor_api(user32)

                # Structures
                class RECT(ctypes.Structure):
                    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
                class MONITORINFO(ctypes.Structure):
                    _fields_ = [("cbSize", ctypes.c_uint), ("rcMonitor", RECT), ("rcWork", RECT), ("dwFlags", ctypes.c_uint)]

                # Enumerate all monitors
                monitors = []
                def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
                    monitors.append(hMonitor)
                    return True

                callback_type = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)
                MONITORENUMPROC = callback_type(
                    ctypes.c_int,
                    wintypes.HANDLE,
                    wintypes.HDC,
                    ctypes.POINTER(RECT),
                    LPARAM_T,
                )
                user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(callback), 0)

                # Get the requested monitor
                if 0 <= monitor_index < len(monitors):
                    hmon = monitors[monitor_index]
                    mi = MONITORINFO()
                    mi.cbSize = ctypes.sizeof(MONITORINFO)
                    if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                        return (mi.rcWork.left, mi.rcWork.top, mi.rcWork.right, mi.rcWork.bottom)
        except Exception:
            pass
        # Fallback: primary screen
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        return (0, 0, int(sw), int(sh))

    def _get_active_monitor_workarea(self):
        """
        Return (l, t, r, b) work area for the monitor currently active.

        On Windows, picks the monitor under the cursor. Falls back to the
        primary screen bounds elsewhere.

        Returns:
            Tuple of (left, top, right, bottom) coordinates
        """
        # Check if specific monitor is set
        if bool(self.settings.get("specific_monitor_only", False)):
            monitor_index = int(self.settings.get("specific_monitor_index", 0))
            return self._get_specific_monitor_workarea(monitor_index)

        try:
            if platform.system().lower() == "windows":
                user32 = ctypes.windll.user32
                _configure_monitor_api(user32)
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
        """
        Return (l, t, r, b) work area for the monitor containing this window.

        On Windows uses the window center to pick a monitor; fall back to
        the primary screen elsewhere.

        Returns:
            Tuple of (left, top, right, bottom) coordinates
        """
        try:
            if platform.system().lower() == "windows":
                user32 = ctypes.windll.user32
                _configure_monitor_api(user32)
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
        """
        Clamp window position to fit within a rectangle.

        Args:
            x: Window X position
            y: Window Y position
            w: Window width
            h: Window height
            rect: Tuple of (left, top, right, bottom) to clamp to

        Returns:
            Tuple of (clamped_x, clamped_y)
        """
        l, t, r, b = rect
        min_x, max_x = l, max(l, r - w)
        min_y, max_y = t, max(t, b - h)
        cx = min(max(int(x), min_x), max_x)
        cy = min(max(int(y), min_y), max_y)
        return cx, cy

    def _center_on_active_monitor(self):
        """
        Center the dialog on the currently active monitor.

        The active monitor is determined by cursor position on Windows,
        or uses the primary screen on other platforms.
        """
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        l, t, r, b = self._get_active_monitor_workarea()
        avail_w, avail_h = (r - l), (b - t)
        x = l + int((avail_w - w) / 2)
        y = t + int((avail_h - h) / 3)
        x, y = self._clamp_to_rect(x, y, w, h, (l, t, r, b))
        self.geometry(self._format_geometry_pos(x, y))

    def _follow_cursor_center_loop(self):
        """
        Periodically check if cursor moved to different monitor and recenter.

        This creates a loop that runs every 400ms to track cursor movement
        across monitors and reposition the dialog accordingly.
        """
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
            # Only reschedule if not closed
            if not self._closed:
                try:
                    self._schedule_timer(400, self._follow_cursor_center_loop)
                except Exception:
                    pass

    def ensure_on_screen(self):
        """
        Ensure the window is fully visible on screen.

        Clamps window position to current monitor's work area if it has
        moved off-screen.
        """
        try:
            self.update_idletasks()
            w, h = self.winfo_width(), self.winfo_height()
            x, y = self.winfo_x(), self.winfo_y()
            rect = self._get_own_monitor_workarea()
            cx, cy = self._clamp_to_rect(x, y, w, h, rect)
            if (cx, cy) != (x, y):
                self.geometry(self._format_geometry_pos(cx, cy))
        except Exception:
            pass

    def _format_geometry_pos(self, x, y):
        """Format geometry position with correct signs for negative coords."""
        try:
            sx = f"{x:+d}" if int(x) < 0 else f"+{int(x)}"
            sy = f"{y:+d}" if int(y) < 0 else f"+{int(y)}"
            return f"{sx}{sy}"
        except Exception:
            return f"+{x}+{y}"

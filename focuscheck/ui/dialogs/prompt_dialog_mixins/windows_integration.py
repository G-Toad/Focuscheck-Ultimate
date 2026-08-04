"""
Windows integration mixin for PromptDialog.

Contains Windows-specific helper methods for minimize button control,
taskbar flashing, and window state management.
"""

import platform
import ctypes
from ctypes import wintypes

try:
    from ....utils import get_logger
except ImportError:
    def get_logger():
        import logging
        return logging.getLogger(__name__)


def _configure_windows_integration_api(user32, kernel32=None):
    """Declare signatures for prompt window style, focus, and flash calls."""
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = ctypes.c_long
    user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
    user32.SetWindowLongW.restype = ctypes.c_long
    user32.SetWindowPos.argtypes = [
        wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_int, wintypes.UINT,
    ]
    user32.SetWindowPos.restype = wintypes.BOOL
    user32.FlashWindowEx.argtypes = [ctypes.c_void_p]
    user32.FlashWindowEx.restype = wintypes.BOOL
    user32.GetForegroundWindow.argtypes = []
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
    user32.AttachThreadInput.restype = wintypes.BOOL
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL
    user32.SetFocus.argtypes = [wintypes.HWND]
    user32.SetFocus.restype = wintypes.HWND
    if kernel32 is not None:
        kernel32.GetCurrentThreadId.argtypes = []
        kernel32.GetCurrentThreadId.restype = wintypes.DWORD


class WindowsIntegrationMixin:
    """Mixin for Windows-specific functionality in PromptDialog."""

    def _disable_minimize_button(self):
        """
        Disable the minimize button on Windows.

        Removes the minimize button from the window's title bar by
        modifying window styles.
        """
        if platform.system().lower() != "windows":
            return
        hwnd = self.winfo_id()
        user32 = ctypes.windll.user32
        _configure_windows_integration_api(user32)
        GWL_STYLE = -16
        WS_MINIMIZEBOX = 0x00020000
        style = user32.GetWindowLongW(hwnd, GWL_STYLE)
        if style:
            style &= ~WS_MINIMIZEBOX
            user32.SetWindowLongW(hwnd, GWL_STYLE, style)
            SWP_NOSIZE = 0x0001
            SWP_NOMOVE = 0x0002
            SWP_NOZORDER = 0x0004
            SWP_FRAMECHANGED = 0x0020
            user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                                SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_FRAMECHANGED)

    def _flash_taskbar_begin(self):
        """
        Start flashing the taskbar icon on Windows.

        Uses FlashWindowEx to attract user attention via taskbar flashing.
        """
        if platform.system().lower() != "windows":
            return
        user32 = ctypes.windll.user32
        _configure_windows_integration_api(user32)
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
        user32.FlashWindowEx(ctypes.byref(info))

    def _flash_taskbar_stop(self):
        """
        Stop flashing the taskbar icon on Windows.

        Stops the taskbar flashing started by _flash_taskbar_begin.
        """
        if platform.system().lower() != "windows":
            return
        user32 = ctypes.windll.user32
        _configure_windows_integration_api(user32)
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
        user32.FlashWindowEx(ctypes.byref(info))

    def _modal_auto_focus_enabled(self):
        """
        Check if modal dialogs should auto-focus.

        Returns:
            True if auto-focus is enabled, False otherwise
        """
        try:
            return bool(self.settings.get("modal_dialog_auto_focus", True))
        except Exception:
            return True

    def _force_window_to_front(self):
        """
        Force window to front and grab focus (OPTIMIZED for performance).

        Uses fast, single-use thread attach before SetForegroundWindow,
        then detaches immediately to prevent CPU overhead on low-end machines.
        """
        if platform.system().lower() != "windows":
            # Non-Windows fallback
            try:
                self.lift()
                self.focus_force()
            except Exception:
                pass
            return

        try:
            hwnd = self.winfo_id()
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            _configure_windows_integration_api(user32, kernel32)

            # Fast, single-use thread attach to allow SetForegroundWindow
            fg_thread = None
            this_thread = None
            attached = False

            try:
                foreground = user32.GetForegroundWindow()
                if foreground != hwnd:
                    fg_thread = user32.GetWindowThreadProcessId(foreground, None)
                    this_thread = kernel32.GetCurrentThreadId()
                    if fg_thread != this_thread:
                        # Attach briefly to allow focus steal
                        attached = user32.AttachThreadInput(fg_thread, this_thread, True)
            except Exception as e:
                # Log but continue
                try:
                    logger = get_logger()
                    logger.debug(f"Thread attach failed: {e}")
                except Exception:
                    pass

            # 1. Show window
            SW_SHOW = 5
            user32.ShowWindow(hwnd, SW_SHOW)

            # 2. Set foreground window (should work now with thread attached)
            result = user32.SetForegroundWindow(hwnd)
            if not result:
                # Log failure for debugging
                try:
                    logger = get_logger()
                    logger.warning("SetForegroundWindow failed - window may not receive focus immediately")
                except Exception:
                    pass

            # 3. Detach thread immediately to prevent CPU overhead
            if attached and fg_thread and this_thread:
                try:
                    user32.AttachThreadInput(fg_thread, this_thread, False)
                except Exception:
                    pass

            # 4. Tkinter-level focus
            self.lift()
            self.focus_force()

        except Exception as e:
            # Log exception and fallback to tkinter methods
            try:
                logger = get_logger()
                logger.error(f"Window focus failed: {e}")
            except Exception:
                pass
            try:
                self.lift()
                self.focus_force()
            except Exception:
                pass

    def _prevent_minimize(self, _evt=None):
        """
        Prevent window minimization by restoring immediately.

        This is a cross-platform guard against minimization attempts.

        Args:
            _evt: Optional event object
        """
        if self._closed:
            return
        try:
            if self.state() == 'iconic':
                schedule = getattr(self, "_schedule_timer", None)
                if callable(schedule):
                    schedule(0, self.deiconify)
                else:
                    # Compatibility for standalone mixin fixtures.
                    self.after(0, self.deiconify)
                try: self.lift()
                except Exception: pass
        except Exception:
            pass

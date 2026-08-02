"""Helpers extracted from IntensificationMixin to reduce file size."""

import platform
import ctypes
from ctypes import wintypes
import tkinter as tk

try:
    from ....utils import get_logger  # type: ignore
except ImportError:
    def get_logger():
        import logging
        return logging.getLogger(__name__)


def lift_all_child_windows(owner):
    """Lift all child Toplevel windows above dim overlays (stage5)."""
    try:
        if not hasattr(owner, '_stage5_topmost_windows'):
            owner._stage5_topmost_windows = []

        overlay_hwnd = getattr(owner, '_stage5_overlay_hwnd', None)
        try:
            insert_after = wintypes.HWND(overlay_hwnd) if overlay_hwnd else wintypes.HWND(-1)
        except Exception:
            insert_after = wintypes.HWND(-1)

        try:
            for window_name in owner.tk.call('wm', 'stackorder', '.'):
                try:
                    widget = owner.nametowidget(window_name)
                    if isinstance(widget, tk.Toplevel) and widget not in (owner._stage5_overlays or []):
                        if widget != owner and not hasattr(widget, '_is_stage5_overlay'):
                            if widget not in owner._stage5_topmost_windows:
                                owner._stage5_topmost_windows.append(widget)

                            widget.lift()
                            widget.attributes('-topmost', True)

                            if platform.system().lower() == 'windows':
                                try:
                                    child_hwnd = wintypes.HWND(widget.winfo_id())
                                    user32 = ctypes.windll.user32
                                    SWP_NOACTIVATE = 0x0010
                                    SWP_NOMOVE = 0x0002
                                    SWP_NOSIZE = 0x0001
                                    user32.SetWindowPos(
                                        child_hwnd,
                                        insert_after,
                                        0, 0, 0, 0,
                                        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
                                    )
                                except Exception:
                                    pass
                except Exception:
                    pass
        except Exception:
            pass
    except Exception:
        pass

    try:
        get_logger().debug("stage5: lifted child windows")
    except Exception:
        pass

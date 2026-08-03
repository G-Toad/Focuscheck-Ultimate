"""
Version 2 sub-popup for flagged websites.
"""

import tkinter as tk
from tkinter import ttk


def _configure_virtual_screen_api(user32):
    """Declare the User32 metrics signature used by the full-screen popup."""
    import ctypes
    user32.GetSystemMetrics.argtypes = [ctypes.c_int]
    user32.GetSystemMetrics.restype = ctypes.c_int


class V2SubPopupDialog(tk.Toplevel):
    """Full-screen warning overlay for flagged websites."""

    def __init__(self, parent, domain, severity=2, on_yes=None, on_no=None):
        super().__init__(parent)
        self._on_yes = on_yes
        self._on_no = on_no
        self._severity = severity

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg="#000000")

        origin_x, origin_y, w, h = _get_virtual_screen_rect()
        self.geometry(_format_geometry(w, h, origin_x, origin_y))

        container = tk.Frame(self, bg="#000000")
        container.place(relx=0.5, rely=0.5, anchor="center")

        title = tk.Label(
            container,
            text="High-risk site detected",
            fg="#ff5555",
            bg="#000000",
            font=("Segoe UI", 22, "bold"),
        )
        title.pack(pady=(0, 12))

        msg = tk.Label(
            container,
            text=f"{domain} is flagged as a distraction site.",
            fg="#ffffff",
            bg="#000000",
            font=("Segoe UI", 14),
        )
        msg.pack(pady=(0, 16))

        if severity >= 2:
            question = tk.Label(
                container,
                text="Do you need an intervention?",
                fg="#ffffff",
                bg="#000000",
                font=("Segoe UI", 14, "bold"),
            )
            question.pack(pady=(0, 12))

            btns = tk.Frame(container, bg="#000000")
            btns.pack()
            yes_btn = ttk.Button(btns, text="Yes", command=self._yes)
            yes_btn.pack(side="left", padx=8)
            ttk.Button(btns, text="No", command=self._no).pack(side="left", padx=8)
        else:
            yes_btn = ttk.Button(container, text="Dismiss", command=self._no)
            yes_btn.pack()

        self.bind("<Escape>", self._on_escape)
        self.bind("<Return>", self._on_return)
        self.bind("<KP_Enter>", self._on_return)
        try:
            yes_btn.focus_set()
        except Exception:
            pass

    def _on_escape(self, _event=None):
        self._no()
        return "break"

    def _on_return(self, _event=None):
        if self._severity >= 2:
            self._yes()
        else:
            self._no()
        return "break"

    def _yes(self):
        try:
            if callable(self._on_yes):
                self._on_yes()
        finally:
            self.destroy()

    def _no(self):
        try:
            if callable(self._on_no):
                self._on_no()
        finally:
            self.destroy()


def _format_geometry(w, h, x, y):
    sx = f"{x:+d}" if x < 0 else f"+{x}"
    sy = f"{y:+d}" if y < 0 else f"+{y}"
    return f"{w}x{h}{sx}{sy}"


def _get_virtual_screen_rect():
    try:
        import platform
        if platform.system().lower() == "windows":
            import ctypes
            user32 = ctypes.windll.user32
            _configure_virtual_screen_api(user32)
            SM_XVIRTUALSCREEN = 76
            SM_YVIRTUALSCREEN = 77
            SM_CXVIRTUALSCREEN = 78
            SM_CYVIRTUALSCREEN = 79
            x = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
            y = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
            w = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
            h = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
            if w > 0 and h > 0:
                return int(x), int(y), int(w), int(h)
    except Exception:
        pass
    root = tk.Tk()
    root.withdraw()
    w = root.winfo_screenwidth()
    h = root.winfo_screenheight()
    root.destroy()
    return 0, 0, int(w), int(h)


__all__ = ["V2SubPopupDialog"]

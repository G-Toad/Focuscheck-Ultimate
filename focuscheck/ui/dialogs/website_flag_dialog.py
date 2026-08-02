"""
Dialog for adding/editing a website flag entry.
"""

import tkinter as tk
from tkinter import ttk, messagebox


class WebsiteFlagDialog(tk.Toplevel):
    """Modal dialog for a single website flag entry."""

    def __init__(self, parent, title="Website Flag", initial=None, on_save=None):
        super().__init__(parent)
        self._on_save = on_save
        self._initial = initial or {}

        self.title(title)
        self.geometry("420x260")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Escape>", lambda _e: self._cancel())
        self.bind("<Return>", lambda _e: self._save())
        self.bind("<KP_Enter>", lambda _e: self._save())

        self._init_vars()
        self._build_ui()
        self._center_on_parent()

    def _init_vars(self):
        init = self._initial
        self.domain_var = tk.StringVar(value=str(init.get("domain", "")))
        self.enabled_var = tk.BooleanVar(value=bool(init.get("enabled", True)))
        self.allow_once_var = tk.BooleanVar(value=bool(init.get("allow_once", False)))
        self.severity_var = tk.StringVar(value=str(init.get("severity", 1)))
        self.cooldown_var = tk.StringVar(value=str(init.get("cooldown_minutes", 5)))

    def _build_ui(self):
        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="Domain (e.g., reddit.com):").pack(anchor="w")
        self.domain_entry = ttk.Entry(container, textvariable=self.domain_var)
        self.domain_entry.pack(fill="x", pady=(0, 8))

        row = ttk.Frame(container)
        row.pack(fill="x", pady=(0, 8))
        ttk.Label(row, text="Severity:").pack(side="left")
        severity = ttk.Combobox(row, textvariable=self.severity_var, values=["1", "2", "3"], width=5, state="readonly")
        severity.pack(side="left", padx=(6, 12))
        ttk.Label(row, text="Cooldown (min):").pack(side="left")
        ttk.Spinbox(row, textvariable=self.cooldown_var, from_=0, to=240, width=6).pack(side="left", padx=(6, 0))

        toggles = ttk.Frame(container)
        toggles.pack(fill="x", pady=(0, 10))
        ttk.Checkbutton(toggles, text="Enabled", variable=self.enabled_var).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(toggles, text="Allow once / snooze", variable=self.allow_once_var).pack(side="left")

        btns = ttk.Frame(container)
        btns.pack(fill="x", pady=(10, 0))
        ttk.Button(btns, text="Cancel", command=self._cancel).pack(side="right")
        ttk.Button(btns, text="Save", command=self._save).pack(side="right", padx=(0, 8))
        try:
            self.domain_entry.focus_set()
        except Exception:
            pass

    def _save(self):
        domain = str(self.domain_var.get() or "").strip().lower()
        if not domain:
            messagebox.showerror("Missing domain", "Please enter a domain (e.g., reddit.com).", parent=self)
            return
        try:
            severity = int(self.severity_var.get())
        except Exception:
            severity = 1
        try:
            cooldown = int(self.cooldown_var.get())
        except Exception:
            cooldown = 5

        payload = {
            "domain": domain,
            "enabled": bool(self.enabled_var.get()),
            "severity": max(1, min(3, severity)),
            "cooldown_minutes": max(0, cooldown),
            "allow_once": bool(self.allow_once_var.get()),
        }
        if callable(self._on_save):
            try:
                self._on_save(payload)
            except Exception:
                pass
        self._close()

    def _cancel(self):
        self._close()

    def _close(self):
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def _center_on_parent(self):
        try:
            parent = self.master
            self.update_idletasks()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            w = self.winfo_width()
            h = self.winfo_height()
            x = px + (pw - w) // 2
            y = py + (ph - h) // 2
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass


__all__ = ["WebsiteFlagDialog"]

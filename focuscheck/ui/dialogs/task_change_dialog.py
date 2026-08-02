"""
Dialog to capture reason for changing task and optionally define new task.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from ...utils.task_payload import build_task_payload


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
        reason_entry = ttk.Entry(self, textvariable=self.reason_var, width=56)
        reason_entry.grid(row=1, column=0, columnspan=2, sticky="we", **pad)

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
        ttk.Button(btns, text="Cancel", command=self._cancel).pack(side="right", padx=6)
        ttk.Button(btns, text="Save", command=self._save).pack(side="right")

        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Return>", self._on_return, add=True)
        self.bind("<KP_Enter>", self._on_return, add=True)
        self.bind("<Escape>", lambda _e: self._cancel(), add=True)
        try:
            reason_entry.focus_set()
        except Exception:
            pass

    def _cancel(self):
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def _on_return(self, _event=None):
        self._save()
        return "break"

    def _save(self):
        reason = self.reason_var.get().strip()
        if not reason:
            messagebox.showerror("Required", "Please provide a reason for changing the task.")
            return
        new_task = build_task_payload(
            self.title_var.get(),
            self.why_var.get(),
            self.cons_var.get(),
            self.due_var.get(),
        )
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()
        try:
            self.on_submit({"reason": reason, "new_task": new_task})
        except Exception:
            pass

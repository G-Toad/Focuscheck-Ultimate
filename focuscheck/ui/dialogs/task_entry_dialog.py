"""
Dialog for entering a new current task with due time and motivation info.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from ...utils.task_payload import build_task_payload


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
        title_entry = ttk.Entry(self, textvariable=self.title_var, width=48)
        title_entry.grid(row=0, column=1, sticky="we", **pad)

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
        ttk.Button(btns, text="Cancel", command=self._cancel).pack(side="right", padx=6)
        ttk.Button(btns, text="Save", command=self._save).pack(side="right")

        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Return>", self._on_return, add=True)
        self.bind("<KP_Enter>", self._on_return, add=True)
        self.bind("<Escape>", lambda _e: self._cancel(), add=True)
        try:
            title_entry.focus_set()
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
        title = self.title_var.get().strip()
        if not title:
            messagebox.showerror("Required", "Task title is required.")
            return
        payload = build_task_payload(title, self.why_var.get(), self.cons_var.get(), self.due_var.get())
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()
        try:
            self.on_submit(payload)
        except Exception:
            pass

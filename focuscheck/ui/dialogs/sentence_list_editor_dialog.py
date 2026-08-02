"""
Generic sentence list editor dialog.

Used to manage lists of exact-typing sentences for confirmations.
Each line is treated as one sentence. Empty lines are ignored.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, font as tkfont


class SentenceListEditorDialog(tk.Toplevel):
    """Simple multi-line editor for sentence lists."""

    def __init__(self, parent, title, sentences, on_save):
        super().__init__(parent)

        self._title = title or "Edit Sentences"
        self._sentences = list(sentences or [])
        self._on_save = on_save

        # Window setup
        self.title(self._title)
        self.configure(bg="#2b2b2b")
        self.geometry("620x480")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Escape>", lambda _e: self._cancel())
        self.bind("<Control-s>", lambda _e: self._save_and_close())

        self._build_ui()
        self._load()
        try:
            self.text.focus_set()
        except Exception:
            pass
        self.update_idletasks()
        self._center_on_parent()

    def _build_ui(self):
        main = tk.Frame(self, bg="#2b2b2b", padx=16, pady=14)
        main.pack(fill=tk.BOTH, expand=True)

        title_lbl = tk.Label(main, text=self._title, bg="#2b2b2b", fg="#ffffff",
                             font=tkfont.Font(family="Segoe UI", size=12, weight="bold"))
        title_lbl.pack(anchor=tk.W, pady=(0, 6))

        info_lbl = tk.Label(
            main,
            text="One sentence per line. These will be picked at random for exact-typing confirmation.",
            bg="#2b2b2b", fg="#aaaaaa"
        )
        info_lbl.pack(anchor=tk.W, pady=(0, 10))

        self.text = scrolledtext.ScrolledText(
            main,
            height=16,
            width=70,
            wrap=tk.WORD,
            bg="#1a1a1a",
            fg="#ffffff",
            insertbackground="#ffffff",
            font=tkfont.Font(family="Consolas", size=10),
            undo=True,
        )
        self.text.pack(fill=tk.BOTH, expand=True)

        btns = tk.Frame(main, bg="#2b2b2b")
        btns.pack(fill=tk.X, pady=(10, 0))

        self.stats = tk.Label(btns, text="0 sentences", bg="#2b2b2b", fg="#888888")
        self.stats.pack(side=tk.LEFT)

        save_btn = tk.Button(btns, text="Save", bg="#00aa00", fg="#ffffff",
                             activebackground="#00cc00", activeforeground="#ffffff",
                             padx=16, pady=6, command=self._save_and_close)
        save_btn.pack(side=tk.RIGHT, padx=(10, 0))

        cancel_btn = tk.Button(btns, text="Cancel", bg="#555555", fg="#ffffff",
                               activebackground="#666666", activeforeground="#ffffff",
                               padx=16, pady=6, command=self._cancel)
        cancel_btn.pack(side=tk.RIGHT)

        # Update stats on change
        self.text.bind('<KeyRelease>', lambda e: self._update_stats())

    def _load(self):
        if self._sentences:
            self.text.insert('1.0', '\n'.join(self._sentences))
        self._update_stats()

    def _update_stats(self):
        lines = [ln.strip() for ln in self.text.get('1.0', tk.END).split('\n') if ln.strip()]
        self.stats.configure(text=f"{len(lines)} sentence{'s' if len(lines) != 1 else ''}")

    def _save_and_close(self):
        lines = [ln.strip() for ln in self.text.get('1.0', tk.END).split('\n') if ln.strip()]
        if callable(self._on_save):
            try:
                self._on_save(lines)
            except Exception:
                pass
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def _cancel(self):
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


__all__ = ["SentenceListEditorDialog"]

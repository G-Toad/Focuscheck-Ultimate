"""
Phrase List Editor Dialog.

Allows editing phrase lists (one phrase per line) with live acronym preview.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, font as tkfont
import re


class PhraseListEditorDialog(tk.Toplevel):
    """Dialog for editing phrase lists with acronym preview."""

    def __init__(self, parent, button_type, phrase_list, on_save):
        """
        Initialize the phrase list editor dialog.

        Args:
            parent: Parent window
            button_type: "study" or "waste" to indicate which button's phrases
            phrase_list: List of current phrases
            on_save: Callback function(new_phrase_list) when saved
        """
        super().__init__(parent)

        self.button_type = button_type
        self.phrase_list = phrase_list if phrase_list else []
        self.on_save_callback = on_save

        # Configure window
        button_name = "Study" if button_type == "study" else "Wasting Time"
        self.title(f"Edit {button_name} Phrases")
        self.configure(bg="#2b2b2b")
        self.geometry("600x500")
        self.resizable(True, True)

        # Make modal
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Escape>", lambda _e: self._cancel())
        self.bind("<Control-s>", lambda _e: self._save_and_close())

        # Build UI
        self._create_ui()

        # Load current phrases
        self._load_phrases()
        try:
            self.text_area.focus_set()
        except Exception:
            pass

        # Center on parent
        self.update_idletasks()
        self._center_on_parent()

    def _create_ui(self):
        """Create the dialog UI."""
        main_frame = tk.Frame(self, bg="#2b2b2b", padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title and instructions
        title_font = tkfont.Font(family="Segoe UI", size=12, weight="bold")
        button_name = "Study" if self.button_type == "study" else "Wasting Time"

        title_lbl = tk.Label(
            main_frame,
            text=f'{button_name} Button Phrases',
            font=title_font,
            bg="#2b2b2b",
            fg="#ffffff"
        )
        title_lbl.pack(anchor=tk.W, pady=(0, 5))

        instructions_lbl = tk.Label(
            main_frame,
            text="Enter one phrase per line. The first letter of each word will be used.",
            bg="#2b2b2b",
            fg="#888888",
            justify=tk.LEFT
        )
        instructions_lbl.pack(anchor=tk.W, pady=(0, 10))

        # Text editor frame
        editor_frame = tk.Frame(main_frame, bg="#2b2b2b")
        editor_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Text area with scrollbar
        text_font = tkfont.Font(family="Consolas", size=10)
        self.text_area = scrolledtext.ScrolledText(
            editor_frame,
            width=60,
            height=15,
            font=text_font,
            bg="#1a1a1a",
            fg="#ffffff",
            insertbackground="#ffffff",
            wrap=tk.WORD,
            undo=True
        )
        self.text_area.pack(fill=tk.BOTH, expand=True)

        # Bind text change to update preview
        self.text_area.bind('<KeyRelease>', self._on_text_change)

        # Preview frame
        preview_frame = tk.Frame(main_frame, bg="#2b2b2b")
        preview_frame.pack(fill=tk.X, pady=(10, 15))

        preview_title_lbl = tk.Label(
            preview_frame,
            text="Acronym Preview:",
            bg="#2b2b2b",
            fg="#888888",
            font=tkfont.Font(size=9)
        )
        preview_title_lbl.pack(anchor=tk.W)

        # Preview text (shows acronyms)
        self.preview_text = tk.Text(
            preview_frame,
            width=60,
            height=6,
            font=tkfont.Font(family="Consolas", size=9),
            bg="#1a1a1a",
            fg="#00aaff",
            state=tk.DISABLED,
            wrap=tk.WORD
        )
        self.preview_text.pack(fill=tk.X, pady=(5, 0))

        # Buttons frame
        btn_frame = tk.Frame(main_frame, bg="#2b2b2b")
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        btn_font = tkfont.Font(family="Segoe UI", size=10, weight="bold")

        # Save button
        save_btn = tk.Button(
            btn_frame,
            text="Save",
            font=btn_font,
            bg="#00aa00",
            fg="#ffffff",
            activebackground="#00cc00",
            activeforeground="#ffffff",
            padx=20,
            pady=8,
            command=self._save_and_close,
            cursor="hand2"
        )
        save_btn.pack(side=tk.RIGHT, padx=(10, 0))

        # Cancel button
        cancel_btn = tk.Button(
            btn_frame,
            text="Cancel",
            font=btn_font,
            bg="#555555",
            fg="#ffffff",
            activebackground="#666666",
            activeforeground="#ffffff",
            padx=20,
            pady=8,
            command=self._cancel,
            cursor="hand2"
        )
        cancel_btn.pack(side=tk.RIGHT)

        # Stats label
        self.stats_lbl = tk.Label(
            btn_frame,
            text="0 phrases",
            bg="#2b2b2b",
            fg="#888888",
            font=tkfont.Font(size=9)
        )
        self.stats_lbl.pack(side=tk.LEFT)

    def _load_phrases(self):
        """Load current phrases into text area."""
        if self.phrase_list:
            text = '\n'.join(self.phrase_list)
            self.text_area.insert('1.0', text)
            self._update_preview()

    def _on_text_change(self, event=None):
        """Handle text change - update preview."""
        self._update_preview()

    def _update_preview(self):
        """Update acronym preview based on current text."""
        # Get all lines
        text = self.text_area.get('1.0', tk.END)
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        # Generate preview
        preview_lines = []
        for line in lines:
            acronym = self._extract_acronym(line)
            if acronym:
                preview_lines.append(f"{acronym} ← {line}")

        # Update preview text
        self.preview_text.configure(state=tk.NORMAL)
        self.preview_text.delete('1.0', tk.END)
        if preview_lines:
            self.preview_text.insert('1.0', '\n'.join(preview_lines))
        else:
            self.preview_text.insert('1.0', '(no phrases yet)')
        self.preview_text.configure(state=tk.DISABLED)

        # Update stats
        self.stats_lbl.configure(text=f"{len(lines)} phrase{'s' if len(lines) != 1 else ''}")

    def _extract_acronym(self, phrase):
        """Extract acronym from phrase (first letter of each word)."""
        words = re.findall(r'\b\w+\b', phrase)
        acronym = ''.join(word[0].upper() for word in words if word)
        return acronym

    def _save_and_close(self):
        """Save phrases and close dialog."""
        # Get all lines
        text = self.text_area.get('1.0', tk.END)
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        # Filter out empty and invalid phrases
        valid_phrases = []
        for line in lines:
            acronym = self._extract_acronym(line)
            if acronym:  # Only include if it produces a valid acronym
                valid_phrases.append(line)

        # Call callback with new list
        if callable(self.on_save_callback):
            self.on_save_callback(valid_phrases)

        # Close dialog
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def _cancel(self):
        """Cancel and close dialog without saving."""
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def _center_on_parent(self):
        """Center dialog on parent window."""
        self.update_idletasks()

        # Get parent position and size
        parent = self.master
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()

        # Get this window size
        width = self.winfo_width()
        height = self.winfo_height()

        # Calculate centered position
        x = parent_x + (parent_w // 2) - (width // 2)
        y = parent_y + (parent_h // 2) - (height // 2)

        # Ensure on screen
        x = max(0, x)
        y = max(0, y)

        self.geometry(f"{width}x{height}+{x}+{y}")

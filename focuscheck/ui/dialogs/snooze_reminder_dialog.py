"""
Snooze Reminder Dialog.

A simple, non-intrusive dialog that reminds the user to re-enable reminders
when they are in snoozed/paused mode. This dialog has no punishment effects
and stays in one place until answered.
"""

import tkinter as tk
from tkinter import ttk

try:
    from ...utils import get_logger
except ImportError:
    def get_logger():
        import logging
        return logging.getLogger(__name__)


class SnoozeReminderDialog(tk.Toplevel):
    """
    Simple reminder dialog when reminders are snoozed.

    Features:
    - No punishment effects (no dimming, no overdrive, no intensification)
    - Stays in one place (doesn't follow cursor across monitors)
    - Just a gentle reminder to re-enable if user forgot
    - Can be dismissed with Yes or No
    """

    def __init__(self, master, settings, on_yes=None, on_no=None):
        """
        Initialize the snooze reminder dialog.

        Args:
            master: Parent tkinter widget
            settings: Settings dictionary
            on_yes: Callback function when user clicks Yes
            on_no: Callback function when user clicks No
        """
        super().__init__(master)
        self.settings = settings
        self.on_yes = on_yes
        self.on_no = on_no
        self._closed = False

        self.title("Reminder")
        self.configure(bg="#222")
        self.resizable(False, False)

        # Simple, non-intrusive styling
        if self.settings.get("always_on_top", True):
            self.attributes("-topmost", True)

        # Don't try to prevent minimize - this is a gentle reminder
        self.protocol("WM_DELETE_WINDOW", self._on_no)

        # Main container
        container = tk.Frame(self, bg="#222", padx=20, pady=20)
        container.pack()

        # Icon/title
        title = tk.Label(
            container,
            text="Reminders are paused",
            fg="#ffcc00",
            bg="#222",
            font=("Segoe UI", 12, "bold")
        )
        title.pack(pady=(0, 10))

        # Question
        question = tk.Label(
            container,
            text="Would you like to turn reminders back on?",
            fg="#ddd",
            bg="#222",
            font=("Segoe UI", 10)
        )
        question.pack(pady=(0, 15))

        # Buttons frame
        buttons = tk.Frame(container, bg="#222")
        buttons.pack()

        # Yes button (re-enable)
        self.btn_yes = tk.Button(
            buttons,
            text="Yes, re-enable",
            font=("Segoe UI", 11),
            bg="#28a745",
            fg="white",
            activebackground="#218838",
            activeforeground="white",
            relief="flat",
            bd=0,
            padx=20,
            pady=8,
            cursor="hand2",
            command=self._on_yes
        )
        self.btn_yes.pack(side="left", padx=(0, 10))

        # No button (keep snoozed)
        self.btn_no = tk.Button(
            buttons,
            text="No, keep paused",
            font=("Segoe UI", 11),
            bg="#444",
            fg="white",
            activebackground="#333",
            activeforeground="white",
            relief="flat",
            bd=0,
            padx=20,
            pady=8,
            cursor="hand2",
            command=self._on_no
        )
        self.btn_no.pack(side="left")

        # Keyboard bindings
        self.bind("<Return>", lambda e: self._on_yes())
        self.bind("<KP_Enter>", lambda e: self._on_yes())
        self.bind("<Escape>", lambda e: self._on_no())

        # Center on screen (but don't follow cursor)
        self.update_idletasks()
        self._center_on_screen()

        # Focus the Yes button by default
        self.after(50, lambda: self.btn_yes.focus_set())

    def _center_on_screen(self):
        """Center the dialog on the primary screen."""
        try:
            # Get window size
            width = self.winfo_width()
            height = self.winfo_height()

            # Get screen size
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()

            # Calculate position
            x = (screen_width - width) // 2
            y = (screen_height - height) // 2

            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def _on_yes(self):
        """Handle Yes button - user wants to re-enable reminders."""
        if self._closed:
            return
        self._closed = True

        try:
            get_logger().info("Snooze reminder: user chose to re-enable reminders")
        except Exception:
            pass

        try:
            if callable(self.on_yes):
                self.on_yes()
        except Exception:
            pass

        try:
            self.destroy()
        except Exception:
            pass

    def _on_no(self):
        """Handle No button - user wants to keep reminders paused."""
        if self._closed:
            return
        self._closed = True

        try:
            get_logger().info("Snooze reminder: user chose to keep reminders paused")
        except Exception:
            pass

        try:
            if callable(self.on_no):
                self.on_no()
        except Exception:
            pass

        try:
            self.destroy()
        except Exception:
            pass


__all__ = ['SnoozeReminderDialog']

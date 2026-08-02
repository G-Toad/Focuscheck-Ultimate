"""
Modern UI widgets for advanced settings interface.

Provides:
- ToggleSwitch: iOS-style on/off toggle
- LabeledSlider: Slider with live value display
- ExpandableCard: Collapsible panel for grouping
- PresetButton: Quick-apply configuration presets
"""

import tkinter as tk
from tkinter import ttk


class ToggleSwitch(tk.Canvas):
    """
    Modern toggle switch widget (iOS-style).

    More intuitive than checkboxes for on/off states.
    """

    def __init__(self, parent, variable, on_color="#4CAF50", off_color="#CCCCCC", **kwargs):
        self.variable = variable
        self.on_color = on_color
        self.off_color = off_color

        super().__init__(parent, width=50, height=24, highlightthickness=0, **kwargs)

        # Draw background
        self.bg = self.create_oval(2, 2, 48, 22, fill=off_color, outline="")
        # Draw knob
        self.knob = self.create_oval(4, 4, 22, 20, fill="white", outline="#999")

        self.bind("<Button-1>", self._toggle)
        self._update_display()

        # Watch variable for external changes
        variable.trace_add("write", lambda *args: self._update_display())

    def _toggle(self, event=None):
        """Toggle the switch state."""
        self.variable.set(not self.variable.get())
        self._update_display()

    def _update_display(self):
        """Update visual appearance based on state."""
        is_on = self.variable.get()

        if is_on:
            # Move knob right, color background
            self.coords(self.knob, 28, 4, 46, 20)
            self.itemconfig(self.bg, fill=self.on_color)
        else:
            # Move knob left, gray background
            self.coords(self.knob, 4, 4, 22, 20)
            self.itemconfig(self.bg, fill=self.off_color)


class LabeledSlider(ttk.Frame):
    """
    Slider with label and live value display.

    Shows percentage for 0.0-1.0 ranges or raw value for others.
    """

    def __init__(self, parent, label, variable, from_=0.0, to=1.0,
                 resolution=0.01, show_percentage=True, suffix="", **kwargs):
        super().__init__(parent, **kwargs)

        self.variable = variable
        self.show_percentage = show_percentage
        self.suffix = suffix

        # Label
        ttk.Label(self, text=label, width=25).pack(side="left", padx=(0, 10))

        # Slider
        self.slider = ttk.Scale(
            self, from_=from_, to=to, orient="horizontal",
            variable=variable, command=self._on_change
        )
        self.slider.pack(side="left", fill="x", expand=True, padx=5)

        # Value display
        self.value_label = ttk.Label(self, text="", width=10, anchor="e")
        self.value_label.pack(side="left", padx=(5, 0))

        self._update_display()

    def _on_change(self, value):
        """Update display when slider moves."""
        self._update_display()

    def _update_display(self):
        """Update the value label."""
        value = self.variable.get()

        if self.show_percentage:
            # Show as percentage
            display = f"{int(value * 100)}%"
        else:
            # Show raw value
            display = f"{value:.2f}"

        if self.suffix:
            display += f" {self.suffix}"

        self.value_label.config(text=display)


class SpinboxWithButtons(ttk.Frame):
    """
    Numeric input with +/- buttons for easier adjustment.
    """

    def __init__(self, parent, label, variable, from_=0, to=100, suffix="", **kwargs):
        super().__init__(parent, **kwargs)

        self.variable = variable

        # Label
        ttk.Label(self, text=label, width=25).pack(side="left", padx=(0, 10))

        # Decrease button
        ttk.Button(self, text="-", width=3, command=self._decrease).pack(side="left")

        # Spinbox
        self.spinbox = ttk.Spinbox(
            self, from_=from_, to=to, textvariable=variable,
            width=10, justify="center"
        )
        self.spinbox.pack(side="left", padx=5)

        # Increase button
        ttk.Button(self, text="+", width=3, command=self._increase).pack(side="left")

        # Suffix
        if suffix:
            ttk.Label(self, text=suffix).pack(side="left", padx=(5, 0))

    def _decrease(self):
        """Decrease value by 1."""
        try:
            current = int(self.variable.get())
            self.variable.set(str(max(0, current - 1)))
        except ValueError:
            pass

    def _increase(self):
        """Increase value by 1."""
        try:
            current = int(self.variable.get())
            self.variable.set(str(current + 1))
        except ValueError:
            pass


class ExpandableCard(ttk.Frame):
    """
    Expandable/collapsible card for grouping related settings.

    Reduces visual clutter by hiding details until needed.
    """

    def __init__(self, parent, title, **kwargs):
        super().__init__(parent, relief="solid", borderwidth=1, **kwargs)

        self.is_expanded = tk.BooleanVar(value=True)

        # Header (clickable)
        self.header = ttk.Frame(self, style="Card.TFrame")
        self.header.pack(fill="x", padx=5, pady=5)
        self.header.bind("<Button-1>", lambda e: self._toggle())

        # Expand/collapse indicator
        self.indicator = ttk.Label(
            self.header, text="▼", font=("Segoe UI", 10),
            cursor="hand2"
        )
        self.indicator.pack(side="left", padx=(0, 5))
        self.indicator.bind("<Button-1>", lambda e: self._toggle())

        # Title
        self.title_label = ttk.Label(
            self.header, text=title, font=("Segoe UI", 10, "bold"),
            cursor="hand2"
        )
        self.title_label.pack(side="left")
        self.title_label.bind("<Button-1>", lambda e: self._toggle())

        # Content frame (expandable)
        self.content = ttk.Frame(self)
        self.content.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _toggle(self):
        """Toggle expanded/collapsed state."""
        self.is_expanded.set(not self.is_expanded.get())

        if self.is_expanded.get():
            self.indicator.config(text="▼")
            self.content.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        else:
            self.indicator.config(text="▶")
            self.content.pack_forget()

    def add_content(self, widget):
        """Add a widget to the card content."""
        widget.pack(in_=self.content, fill="x", pady=3)
        return widget


class ChallengeCard(ttk.Frame):
    """
    Card for individual challenge with toggle, description, and preview.
    """

    def __init__(self, parent, challenge_id, title, description, variable, **kwargs):
        super().__init__(parent, relief="groove", borderwidth=1, **kwargs)

        self.variable = variable

        # Main container
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=10, pady=8)

        # Top row: Toggle + Title
        top_row = ttk.Frame(container)
        top_row.pack(fill="x", pady=(0, 5))

        # Toggle switch
        toggle = ToggleSwitch(top_row, variable)
        toggle.pack(side="left", padx=(0, 10))

        # Title
        ttk.Label(
            top_row, text=title, font=("Segoe UI", 10, "bold")
        ).pack(side="left")

        # Description
        desc_label = ttk.Label(
            container, text=description,
            foreground="gray", font=("Segoe UI", 9),
            wraplength=400
        )
        desc_label.pack(fill="x", pady=(0, 5))

        # Status indicator
        self.status_label = ttk.Label(
            container, text="", font=("Segoe UI", 8, "italic")
        )
        self.status_label.pack(fill="x")

        # Update status when variable changes
        variable.trace_add("write", lambda *args: self._update_status())
        self._update_status()

    def _update_status(self):
        """Update status indicator."""
        if self.variable.get():
            self.status_label.config(
                text="✓ Active - will appear randomly",
                foreground="#2E7D32"
            )
            # Visual feedback via border
            self.config(relief="solid", borderwidth=1)
        else:
            self.status_label.config(
                text="○ Disabled - will never appear",
                foreground="#757575"
            )
            # Lighter border when disabled
            self.config(relief="groove", borderwidth=1)


class PresetButton(ttk.Frame):
    """
    Quick-apply preset configurations.
    """

    def __init__(self, parent, presets, on_apply, **kwargs):
        super().__init__(parent, **kwargs)

        ttk.Label(
            self, text="Quick Presets:", font=("Segoe UI", 10, "bold")
        ).pack(side="left", padx=(0, 10))

        for name, config in presets.items():
            btn = ttk.Button(
                self, text=name,
                command=lambda c=config: on_apply(c),
                width=12
            )
            btn.pack(side="left", padx=5)


class SectionHeader(ttk.Frame):
    """
    Visual section header with optional action buttons.
    """

    def __init__(self, parent, text, actions=None, **kwargs):
        super().__init__(parent, **kwargs)

        # Header label
        label = ttk.Label(
            self, text=text, font=("Segoe UI", 11, "bold"),
            foreground="#1976D2"
        )
        label.pack(side="left", pady=(15, 5))

        # Action buttons (right-aligned)
        if actions:
            for action_text, action_cmd in actions:
                btn = ttk.Button(
                    self, text=action_text, command=action_cmd,
                    width=10
                )
                btn.pack(side="right", padx=5)

        # Separator
        sep = ttk.Separator(self, orient="horizontal")
        sep.pack(fill="x", pady=(5, 10))


class InfoPanel(tk.Frame):
    """
    Informational panel with icon and text.

    Note: Uses tk.Frame instead of ttk.Frame to support background colors.
    """

    def __init__(self, parent, text, panel_type="info", **kwargs):
        super().__init__(parent, relief="solid", borderwidth=1, **kwargs)

        colors = {
            "info": ("#E3F2FD", "#1976D2", "ℹ"),
            "warning": ("#FFF3E0", "#F57C00", "⚠"),
            "success": ("#E8F5E9", "#388E3C", "✓"),
            "tip": ("#F3E5F5", "#7B1FA2", "💡")
        }

        bg_color, fg_color, icon = colors.get(panel_type, colors["info"])

        self.config(background=bg_color)

        container = tk.Frame(self, background=bg_color)
        container.pack(fill="both", expand=True, padx=10, pady=8)

        # Icon
        tk.Label(
            container, text=icon, font=("Segoe UI", 14),
            foreground=fg_color, background=bg_color
        ).pack(side="left", padx=(0, 10))

        # Text
        tk.Label(
            container, text=text, wraplength=500,
            background=bg_color, foreground=fg_color,
            font=("Segoe UI", 9)
        ).pack(side="left", fill="both", expand=True)


__all__ = [
    'ToggleSwitch', 'LabeledSlider', 'SpinboxWithButtons',
    'ExpandableCard', 'ChallengeCard', 'PresetButton',
    'SectionHeader', 'InfoPanel'
]

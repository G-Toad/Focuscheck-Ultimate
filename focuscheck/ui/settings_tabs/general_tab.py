"""General settings tab mixin."""

import tkinter as tk
from tkinter import ttk
from ..modern_widgets import InfoPanel, SectionHeader, SpinboxWithButtons


class GeneralTabMixin:
    """Mixin providing the General tab for settings window."""

    def _create_general_tab(self):
        """Create General tab."""
        tab = self._create_scrollable_tab(self.notebook, "General")

        # Info panel
        InfoPanel(
            tab,
            "Core settings that control FocusCheck's basic behavior and timing",
            panel_type="info"
        ).pack(fill="x", pady=(0, 15))

        # Monitoring Mode
        SectionHeader(tab, "Monitoring Mode").pack(fill="x")
        mode_frame = ttk.Frame(tab)
        mode_frame.pack(fill="x", pady=6)
        ttk.Label(mode_frame, text="Mode:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 10))
        ttk.Radiobutton(
            mode_frame,
            text="Version 1 (classic prompts)",
            variable=self.monitoring_mode_var,
            value="v1",
        ).pack(side="left", padx=(0, 12))
        ttk.Radiobutton(
            mode_frame,
            text="Version 2 (activity-aware)",
            variable=self.monitoring_mode_var,
            value="v2",
        ).pack(side="left")
        InfoPanel(
            tab,
            "Switch between the original prompt system and the new activity-aware pipeline. "
            "All other features (history, tasks, camera, biodata, etc.) stay available in both modes.",
            panel_type="info",
        ).pack(fill="x", pady=(0, 10))

        # Core Timing
        SectionHeader(tab, "Core Timing").pack(fill="x")
        SpinboxWithButtons(tab, "Check interval:", self.interval_var, 10, 600, "seconds").pack(fill="x", pady=3)
        SpinboxWithButtons(tab, "Intensify after:", self.intensify_var, 5, 300, "seconds").pack(fill="x", pady=3)
        SpinboxWithButtons(tab, "Overdrive after:", self.overdrive_var, 20, 600, "seconds").pack(fill="x", pady=3)
        SpinboxWithButtons(tab, "Max intensity level:", self.max_intensity_var, 1, 3, "1-3").pack(fill="x", pady=3)

        # Window Behavior
        SectionHeader(tab, "Window Behavior").pack(fill="x")
        self._add_toggle_row(tab, "Always on top", self.topmost_var,
                            "Keep dialog above all other windows")
        self._add_toggle_row(tab, "Center on show", self.center_var,
                            "Center dialog when it appears")
        self._add_toggle_row(tab, "Follow cursor to monitor", self.follow_cursor_var,
                            "Move dialog to monitor with mouse cursor")

        # Specific monitor selection
        self._add_toggle_row(tab, "Only show on specific monitor", self.specific_monitor_only_var,
                            "Override follow cursor and always use specific monitor")
        SpinboxWithButtons(tab, "Monitor index:", self.specific_monitor_index_var, 0, 10, "0=primary").pack(fill="x", pady=3)
        ttk.Label(tab, text="0 = primary monitor, 1 = second monitor, 2 = third monitor, etc.",
                 foreground="gray", font=("Segoe UI", 8)).pack(fill="x", padx=(30, 0), pady=(0, 5))

        self._add_toggle_row(tab, "Auto-focus follow-ups", self.modal_auto_focus_var,
                            "Automatically focus follow-up dialogs")

        # UI Scaling & Layout
        SectionHeader(tab, "Popup Appearance").pack(fill="x")

        # Layout mode selector
        layout_frame = ttk.Frame(tab)
        layout_frame.pack(fill="x", pady=5)
        ttk.Label(layout_frame, text="Popup layout:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 10))
        layout_combo = ttk.Combobox(layout_frame, textvariable=self.popup_layout_mode_var,
                                    values=["vertical", "horizontal", "compact"], state="readonly", width=15)
        layout_combo.pack(side="left", padx=(0, 10))
        ttk.Label(layout_frame, text="vertical=stacked | horizontal=side-by-side | compact=minimal",
                 foreground="gray", font=("Segoe UI", 8)).pack(side="left")

        InfoPanel(
            tab,
            "🎨 Choose your popup style:\n" +
            "• Vertical: Traditional stacked layout (camera below buttons)\n" +
            "• Horizontal: Side-by-side layout (camera on left, controls on right) - GREAT for widescreen!\n" +
            "• Compact: Minimal centered layout with small camera",
            panel_type="info"
        ).pack(fill="x", pady=(5, 10))

        InfoPanel(
            tab,
            "⚠️ Global UI scaling - shrinks/enlarges entire popup (fonts, buttons, padding). " +
            "Useful if popup doesn't fit on your screen. Changes apply to next popup.",
            panel_type="warning"
        ).pack(fill="x", pady=(0, 10))
        SpinboxWithButtons(tab, "UI Scale:", self.ui_scale_percent_var, 50, 150, "%").pack(fill="x", pady=3)
        ttk.Label(tab, text="50% = half size (very compact), 100% = normal, 150% = 1.5x size (larger)",
                 foreground="gray", font=("Segoe UI", 8)).pack(fill="x", padx=(30, 0), pady=(0, 5))

        # Anti-Habit
        SectionHeader(tab, "Anti-Habit System").pack(fill="x")
        self._add_toggle_row(tab, "Enable anti-habit", self.anti_var,
                            "Prevent autopilot clicking")
        self._add_toggle_row(tab, "Randomize button positions", self.rand_btns_var,
                            "Randomly swap button locations")
        SpinboxWithButtons(tab, "Studying hold time:", self.hold_ms_var, 0, 2000, "ms").pack(fill="x", pady=3)

        # Pause Behavior
        SectionHeader(tab, "Pause Behavior").pack(fill="x")
        self._add_toggle_row(tab, "Never pause (force always-on)", self.force_on_var,
                            "Override all pause conditions")
        self._add_toggle_row(tab, "Pause on idle", self.pause_on_idle_var,
                            "Pause when no keyboard/mouse activity")
        SpinboxWithButtons(tab, "Idle threshold:", self.idle_secs_var, 15, 600, "seconds").pack(fill="x", pady=3)
        self._add_toggle_row(tab, "Pause on Windows lock", self.pause_on_lock_var)
        self._add_toggle_row(tab, "Pause on system sleep", self.pause_on_sleep_var)
        self._add_toggle_row(tab, "Pause on lid closed", self.pause_on_lid_var)

        # System Tray
        SectionHeader(tab, "System Tray").pack(fill="x")
        self._add_toggle_row(tab, "Show Start/Stop button", self.tray_start_stop_enabled_var)
        self._add_toggle_row(tab, "Show Settings button", self.tray_settings_enabled_var)
        self._add_toggle_row(tab, "Show Exit button", self.tray_exit_enabled_var)

        # Snooze Confirmation controls
        SectionHeader(tab, "Snooze Confirmation").pack(fill="x", pady=(12, 0))
        InfoPanel(
            tab,
            "Configure the tray Snooze popup (enable/disable, required questions, sentence list, heuristics).",
            panel_type="info"
        ).pack(fill="x", pady=(0, 8))

        self._add_toggle_row(tab, "Enable snooze confirmation", self.snooze_prompt_enabled_var,
                            "Show the confirmation popup before snoozing from the tray")
        self._add_toggle_row(tab, "Validate reason with heuristics", self.snooze_prompt_validation_var,
                            "Run spam/quality checks on the reason field")

        sub_row = ttk.Frame(tab)
        sub_row.pack(fill="x", pady=(2, 4), padx=(30, 0))
        ttk.Checkbutton(sub_row, text="Prevent paste", variable=self.snooze_prevent_paste_var).pack(side="left")
        ttk.Checkbutton(sub_row, text="Case sensitive match", variable=self.snooze_case_sensitive_var).pack(side="left", padx=(12, 0))

        sent_row = ttk.Frame(tab)
        sent_row.pack(fill="x", pady=(4, 4), padx=(20, 0))
        ttk.Button(sent_row, text="Edit Snooze Confirmation Sentences...",
                   command=self._edit_snooze_sentences).pack(side="left")
        self._snooze_sent_count_lbl = ttk.Label(sent_row, text="", foreground="gray", font=("Segoe UI", 8))
        self._snooze_sent_count_lbl.pack(side="left", padx=(8, 0))
        self._update_snooze_sentence_count_label()

        phrase_row = ttk.Frame(tab)
        phrase_row.pack(fill="x", pady=(2, 2), padx=(20, 0))
        ttk.Checkbutton(phrase_row, text="Require phrase in 'Why are you snoozing?'",
                        variable=self.snooze_require_phrase_var).pack(side="left")
        ttk.Entry(phrase_row, textvariable=self.snooze_required_phrase_var, width=24).pack(side="left", padx=(8, 0))
        ttk.Label(phrase_row, text="(default: 'I am snoozing')", foreground="gray", font=("Segoe UI", 8)).pack(side="left", padx=(6, 0))

        self._add_toggle_row(tab, "Force all heuristics (same as Validation tab)", self.snooze_force_all_heuristics_var,
                            "Override spam settings and enforce every heuristic for snooze confirmation")

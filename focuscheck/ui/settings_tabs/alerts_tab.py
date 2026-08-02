"""Alerts and audio settings tab mixin."""

import tkinter as tk
from tkinter import ttk, messagebox
from ..modern_widgets import (
    InfoPanel, SectionHeader, SpinboxWithButtons, LabeledSlider,
    ExpandableCard
)


class AlertsTabMixin:
    """Mixin providing the Alerts tab for settings window."""

    def _create_alerts_tab(self):
        """Create Alerts tab for Overdrive stages and visual effects."""
        tab = self._create_scrollable_tab(self.notebook, "Alerts")

        # Info panel
        InfoPanel(
            tab,
            "Configure how FocusCheck escalates visual alerts when you ignore prompts. " +
            "Stage 4 adds ultra-fast flashing, Stage 5 dims/blacks out your entire screen.",
            panel_type="info"
        ).pack(fill="x", pady=(0, 15))

        # ===== OVERDRIVE STAGE 4 =====
        stage4_header = SectionHeader(tab, "Overdrive Stage 4 - Ultra-Fast Flashing")
        stage4_header.pack(fill="x", pady=(5, 5))

        self._add_toggle_row(tab, "Enable Stage 4", self.overdrive_stage4_enabled_var,
                            "Trigger ultra-fast red flashing in overdrive mode")

        SpinboxWithButtons(tab, "Trigger after (in overdrive):", self.overdrive_stage4_after_var, 1, 120, "seconds").pack(fill="x", pady=3)
        ttk.Label(tab, text="How many seconds after entering overdrive to activate Stage 4",
                 foreground="gray", font=("Segoe UI", 8)).pack(fill="x", padx=(30, 0), pady=(0, 5))

        SpinboxWithButtons(tab, "Flash interval:", self.overdrive_stage4_flash_var, 20, 500, "milliseconds").pack(fill="x", pady=3)
        ttk.Label(tab, text="How fast the red flashing occurs (lower = faster, more intense)",
                 foreground="gray", font=("Segoe UI", 8)).pack(fill="x", padx=(30, 0), pady=(0, 5))

        # ===== OVERDRIVE STAGE 5 =====
        stage5_header = SectionHeader(tab, "Overdrive Stage 5 - Screen Dimming/Blackout")
        stage5_header.pack(fill="x", pady=(15, 5))

        InfoPanel(
            tab,
            "Stage 5 dims or blacks out all monitors to force you to respond. This is the nuclear option.",
            panel_type="warning"
        ).pack(fill="x", pady=(0, 10))

        self._add_toggle_row(tab, "Enable Stage 5", self.overdrive_stage5_enabled_var,
                            "Enable multi-monitor dimming/blackout")

        SpinboxWithButtons(tab, "Trigger after Stage 4:", self.overdrive_stage5_after_var, 5, 300, "seconds").pack(fill="x", pady=3)
        ttk.Label(tab, text="How many seconds after Stage 4 starts to activate Stage 5 dimming",
                 foreground="gray", font=("Segoe UI", 8)).pack(fill="x", padx=(30, 0), pady=(0, 5))

        # Dimming Engine
        engine_frame = ttk.Frame(tab)
        engine_frame.pack(fill="x", pady=5)
        ttk.Label(engine_frame, text="Dimming engine:", font=("Segoe UI", 9)).pack(side="left", padx=(0, 10))
        engine_combo = ttk.Combobox(engine_frame, textvariable=self.overdrive_stage5_engine_var,
                                    values=["overlay", "gamma"], state="readonly", width=15)
        engine_combo.pack(side="left")
        ttk.Label(engine_frame, text="'overlay' = window overlay, 'gamma' = adjust screen brightness",
                 foreground="gray", font=("Segoe UI", 8)).pack(side="left", padx=(10, 0))

        # Dimming Behavior (Expandable)
        dimming_card = ExpandableCard(tab, "Dimming Behavior & Appearance")
        dimming_card.pack(fill="x", pady=5)

        dimming_card.add_content(self._add_toggle_row(dimming_card.content, "Allow click-through",
                                                      self.overdrive_stage5_click_through_var,
                                                      "Allow clicking through dim overlay to underlying apps"))
        dimming_card.add_content(self._add_toggle_row(dimming_card.content, "Pulsing dim effect",
                                                      self.overdrive_stage5_dim_pulse_var,
                                                      "Pulse the dimming opacity for more urgency"))

        dimming_card.add_content(LabeledSlider(dimming_card.content, "Maximum dim opacity:",
                                              self.overdrive_stage5_dim_max_alpha_var, 0.0, 1.0,
                                              show_percentage=True))

        # Dim color picker
        color_frame = ttk.Frame(dimming_card.content)
        color_frame.pack(fill="x", pady=5)
        ttk.Label(color_frame, text="Dim color (hex):", font=("Segoe UI", 9)).pack(side="left", padx=(0, 10))
        color_entry = ttk.Entry(color_frame, textvariable=self.overdrive_stage5_dim_color_var, width=10)
        color_entry.pack(side="left")
        ttk.Label(color_frame, text="e.g., #000000 = black, #FF0000 = red",
                 foreground="gray", font=("Segoe UI", 8)).pack(side="left", padx=(10, 0))
        dimming_card.add_content(color_frame)

        # Advanced Dimming (Expandable)
        advanced_card = ExpandableCard(tab, "Advanced Dimming Options")
        advanced_card.pack(fill="x", pady=5)

        advanced_card.add_content(SpinboxWithButtons(advanced_card.content, "Hold black screen after:",
                                                     self.overdrive_stage5_hold_after_var, 0, 300, "seconds (0=off)"))
        ttk.Label(advanced_card.content, text="After dimming completes, hold solid black for X seconds (0 to disable)",
                 foreground="gray", font=("Segoe UI", 8)).pack(fill="x", padx=(30, 0), pady=(0, 5))

        advanced_card.add_content(self._add_toggle_row(advanced_card.content, "Enable slow dim to black",
                                                       self.overdrive_stage5_slow_dim_enabled_var,
                                                       "Gradually dim to black over time instead of pulsing"))
        advanced_card.add_content(SpinboxWithButtons(advanced_card.content, "Slow dim duration:",
                                                     self.overdrive_stage5_slow_dim_seconds_var, 1, 120, "seconds"))

        # ===== JIGGLE & ANIMATION EFFECTS =====
        jiggle_header = SectionHeader(tab, "Jiggle & Animation Effects")
        jiggle_header.pack(fill="x", pady=(20, 5))

        InfoPanel(
            tab,
            "Control the visual animations and jiggle effects that grab your attention during prompts.",
            panel_type="info"
        ).pack(fill="x", pady=(0, 10))

        # Jiggle style
        style_frame = ttk.Frame(tab)
        style_frame.pack(fill="x", pady=5)
        ttk.Label(style_frame, text="Jiggle style:", font=("Segoe UI", 9)).pack(side="left", padx=(0, 10))
        style_combo = ttk.Combobox(style_frame, textvariable=self.jiggle_style_var,
                                   values=["off", "nudge", "pulse"], state="readonly", width=15)
        style_combo.pack(side="left")
        ttk.Label(style_frame, text="How buttons and windows shake to get your attention",
                 foreground="gray", font=("Segoe UI", 8)).pack(side="left", padx=(10, 0))

        self._add_toggle_row(tab, "Disable ALL jiggling (override)", self.disable_jiggling_var,
                            "Master switch to disable all jiggle effects regardless of other settings")

        # Intensity Stage Effects (Expandable)
        intensity_card = ExpandableCard(tab, "Intensity Stage Effects (Levels 1-3)")
        intensity_card.pack(fill="x", pady=5)

        intensity_card.add_content(self._add_toggle_row(intensity_card.content, "Enable pulse effect",
                                                        self.enable_intensity_pulse_var,
                                                        "Pulse the dialog window during intensity stages"))
        intensity_card.add_content(self._add_toggle_row(intensity_card.content, "Enable shake effect",
                                                        self.enable_intensity_shake_var,
                                                        "Shake the dialog window during intensity stages"))
        intensity_card.add_content(self._add_toggle_row(intensity_card.content, "Lock position during shake",
                                                        self.shake_lock_position_var,
                                                        "Keep window position locked while shaking (more subtle)"))

        # Overdrive Effects (Expandable)
        overdrive_card = ExpandableCard(tab, "Overdrive Effects (Stage 3+)")
        overdrive_card.pack(fill="x", pady=5)

        overdrive_card.add_content(self._add_toggle_row(overdrive_card.content, "Enable background flash",
                                                        self.enable_overdrive_flash_background_var,
                                                        "Flash the dialog background red in overdrive"))
        overdrive_card.add_content(self._add_toggle_row(overdrive_card.content, "Enable shake loop",
                                                        self.enable_overdrive_shake_loop_var,
                                                        "Continuous shaking during overdrive"))
        overdrive_card.add_content(self._add_toggle_row(overdrive_card.content, "Enable button jiggle",
                                                        self.enable_overdrive_jiggle_buttons_var,
                                                        "Make buttons jiggle individually in overdrive"))

        # ===== AUDIO ALERTS =====
        audio_header = SectionHeader(tab, "Audio Alerts")
        audio_header.pack(fill="x", pady=(20, 5))

        InfoPanel(
            tab,
            "Sophisticated audio alarm system with multiple patterns, safety features, and device switching. "
            "Configure when and how audio alarms play to get your attention.",
            panel_type="info"
        ).pack(fill="x", pady=(0, 10))

        self._add_toggle_row(tab, "Enable audio alerts", self.audio_alerts_enabled_var,
                            "Play sound alarms when prompts are ignored")

        # Trigger point
        trigger_frame = ttk.Frame(tab)
        trigger_frame.pack(fill="x", pady=5)
        ttk.Label(trigger_frame, text="Trigger at:", font=("Segoe UI", 9)).pack(side="left", padx=(0, 10))
        trigger_combo = ttk.Combobox(trigger_frame, textvariable=self.audio_alarm_trigger_var,
                                    values=["intensification", "overdrive", "overdrive_stage4", "overdrive_stage5"],
                                    state="readonly", width=20)
        trigger_combo.pack(side="left")
        ttk.Label(trigger_frame, text="When to start playing audio alerts",
                 foreground="gray", font=("Segoe UI", 8)).pack(side="left", padx=(10, 0))

        # Pattern selection
        pattern_frame = ttk.Frame(tab)
        pattern_frame.pack(fill="x", pady=5)
        ttk.Label(pattern_frame, text="Sound pattern:", font=("Segoe UI", 9)).pack(side="left", padx=(0, 10))
        pattern_combo = ttk.Combobox(pattern_frame, textvariable=self.audio_alarm_pattern_var,
                                     values=["single_beep", "rapid_beeps", "escalating", "pulsing", "siren", "alternating"],
                                     state="readonly", width=20)
        pattern_combo.pack(side="left")
        ttk.Button(pattern_frame, text="Test", command=self._test_audio_pattern, width=8).pack(side="left", padx=(5, 0))
        ttk.Label(pattern_frame, text="Type of sound to play",
                 foreground="gray", font=("Segoe UI", 8)).pack(side="left", padx=(10, 0))

        # Behavior mode
        mode_frame = ttk.Frame(tab)
        mode_frame.pack(fill="x", pady=5)
        ttk.Label(mode_frame, text="Behavior:", font=("Segoe UI", 9)).pack(side="left", padx=(0, 10))
        mode_combo = ttk.Combobox(mode_frame, textvariable=self.audio_alarm_mode_var,
                                   values=["once", "repeating", "escalating_volume", "continuous"],
                                   state="readonly", width=20)
        mode_combo.pack(side="left")
        ttk.Label(mode_frame, text="How to play the pattern",
                 foreground="gray", font=("Segoe UI", 8)).pack(side="left", padx=(10, 0))

        self.audio_duration_widget = SpinboxWithButtons(tab, "Duration:", self.audio_alarm_duration_var, 1, 30, "seconds")
        self.audio_duration_widget.pack(fill="x", pady=3)
        self.audio_duration_label = ttk.Label(tab, text="How long to play (for repeating/escalating modes, ignored for continuous)",
                 foreground="gray", font=("Segoe UI", 8))
        self.audio_duration_label.pack(fill="x", padx=(30, 0), pady=(0, 10))

        # Add callback to grey out duration when continuous mode is selected
        self.audio_alarm_mode_var.trace_add('write', self._on_audio_mode_changed)

        # Safety Settings (Expandable)
        safety_card = ExpandableCard(tab, "Safety & Volume Settings")
        safety_card.pack(fill="x", pady=5)

        safety_card.add_content(self._add_toggle_row(safety_card.content, "Earphone safe mode",
                                                     self.audio_earphone_safe_mode_var,
                                                     "Limit frequencies (800-2000 Hz) and volume for earphone safety"))

        safety_card.add_content(LabeledSlider(safety_card.content, "Maximum volume:",
                                              self.audio_max_volume_var, 0.0, 1.0,
                                              show_percentage=True))
        ttk.Label(safety_card.content, text="Recommended: 0.5-0.7 for earphones, 0.7-1.0 for speakers",
                 foreground="gray", font=("Segoe UI", 8)).pack(fill="x", padx=(30, 0), pady=(0, 5))

        # Device Switching (Expandable)
        device_card = ExpandableCard(tab, "Device Switching (Advanced)")
        device_card.pack(fill="x", pady=5)

        InfoPanel(
            device_card.content,
            "If you're wearing earphones but still not responding, the system can try to switch to laptop speakers. "
            "Requires pycaw library (optional). Install with: pip install pycaw",
            panel_type="warning"
        ).pack(fill="x", pady=(0, 10))

        device_card.add_content(self._add_toggle_row(device_card.content, "Try speaker switch",
                                                     self.audio_try_speaker_switch_var,
                                                     "Attempt to switch from headphones to speakers"))

        device_card.add_content(SpinboxWithButtons(device_card.content, "Switch after:",
                                                   self.audio_speaker_switch_after_var, 10, 120, "seconds"))
        ttk.Label(device_card.content, text="How long to wait before switching to speakers",
                 foreground="gray", font=("Segoe UI", 8)).pack(fill="x", padx=(30, 0), pady=(0, 5))

        # ===== SNOOZE REMINDER =====
        snooze_header = SectionHeader(tab, "Snooze Reminder")
        snooze_header.pack(fill="x", pady=(20, 5))

        InfoPanel(
            tab,
            "Show a gentle reminder when reminders are paused/snoozed, in case you forgot to turn them back on. "
            "This popup has no punishment effects and just asks if you want to re-enable.",
            panel_type="info"
        ).pack(fill="x", pady=(0, 10))

        self._add_toggle_row(tab, "Enable snooze reminders", self.snooze_reminder_enabled_var,
                            "Show periodic reminders to re-enable when snoozed")

        SpinboxWithButtons(tab, "Reminder interval:", self.snooze_reminder_interval_var, 60, 3600, "seconds").pack(fill="x", pady=3)
        ttk.Label(tab, text="How often to show the snooze reminder (300 seconds = 5 minutes)",
                 foreground="gray", font=("Segoe UI", 8)).pack(fill="x", padx=(30, 0), pady=(0, 5))

        # Initialize duration field state based on current mode
        self._on_audio_mode_changed()

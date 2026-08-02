"""
Advanced modern settings window with visual controls.

Features:
- Toggle switches instead of checkboxes
- Sliders with live value display
- Challenge cards with preview
- Preset buttons for quick config
- Expandable sections
- Color-coded feedback
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from .modern_widgets import (
    ToggleSwitch, LabeledSlider, SpinboxWithButtons,
    ExpandableCard, ChallengeCard, PresetButton,
    SectionHeader, InfoPanel
)


class AdvancedSettingsWindow(tk.Toplevel):
    """
    Modern settings window with advanced visual controls.
    """

    # Challenge definitions
    STUDYING_CHALLENGES = [
        ("learning_specificity", "Learning Specificity",
         "Requires naming the exact topic being learned (e.g., 'learning calculus derivatives')"),
        ("goal_connection", "Goal Connection",
         "Forces stating the purpose or goal (e.g., 'to pass Friday's exam')"),
        ("will_commitment", "Will Commitment",
         "Demands a concrete 'I will...' commitment with specific action"),
        ("output_expectation", "Output Expectation",
         "Requires describing the specific deliverable you'll produce"),
    ]

    WASTING_CHALLENGES = [
        ("wasting_acknowledgment", "Wasting Acknowledgment",
         "Forces acknowledging what you're wasting specifically (not just 'time')"),
        ("should_gap", "Should Gap",
         "Demands contrast: what you're doing vs what you should be doing"),
        ("because_reasoning", "Because Reasoning",
         "Requires explaining the real reason for avoiding work"),
        ("hour_projection", "Hour Projection",
         "Forces projecting what will happen in one more hour"),
        ("tomorrow_regret", "Tomorrow Regret",
         "Demands acknowledging what tomorrow-you will regret"),
        ("fear_acknowledgment", "Fear Acknowledgment",
         "Forces naming the underlying fear or anxiety"),
        ("lying_confrontation", "Lying Confrontation",
         "Requires admitting how you're lying to yourself"),
    ]

    # Preset configurations
    CHALLENGE_PRESETS = {
        "Off": {
            "enabled": False,
            "studying_freq": 0.0,
            "wasting_freq": 0.0,
        },
        "Gentle": {
            "enabled": True,
            "studying_freq": 0.1,
            "wasting_freq": 0.2,
            "studying_challenges": ["learning_specificity", "goal_connection"],
            "wasting_challenges": ["should_gap", "tomorrow_regret"],
        },
        "Balanced": {
            "enabled": True,
            "studying_freq": 0.3,
            "wasting_freq": 0.5,
            "studying_challenges": "all",
            "wasting_challenges": ["wasting_acknowledgment", "should_gap",
                                  "because_reasoning", "hour_projection", "tomorrow_regret"],
        },
        "Aggressive": {
            "enabled": True,
            "studying_freq": 0.6,
            "wasting_freq": 0.8,
            "studying_challenges": "all",
            "wasting_challenges": "all",
        },
        "Maximum": {
            "enabled": True,
            "studying_freq": 1.0,
            "wasting_freq": 1.0,
            "studying_challenges": "all",
            "wasting_challenges": "all",
        },
    }

    def __init__(self, master, settings, on_save):
        super().__init__(master)
        self.title("Settings")
        self.geometry("950x750")
        self.minsize(900, 650)
        self.settings = settings.copy()
        self.on_save = on_save

        self._init_vars()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _init_vars(self):
        """Initialize all tkinter variables."""
        s = self.settings

        # Core
        self.interval_var = tk.StringVar(value=str(s.get("interval_seconds", 60)))
        self.intensify_var = tk.StringVar(value=str(s.get("intensify_after_seconds", 15)))
        self.overdrive_var = tk.StringVar(value=str(s.get("overdrive_after_seconds", 60)))
        self.max_intensity_var = tk.StringVar(value=str(s.get("max_intensity_level", 3)))
        self.topmost_var = tk.BooleanVar(value=s.get("always_on_top", True))
        self.center_var = tk.BooleanVar(value=s.get("center_on_show", True))
        self.modal_auto_focus_var = tk.BooleanVar(value=s.get("modal_dialog_auto_focus", True))
        self.follow_cursor_var = tk.BooleanVar(value=s.get("follow_cursor_monitor", True))
        self.webhook_var = tk.StringVar(value=s.get("webhook_url", ""))

        # Anti-habit
        self.anti_var = tk.BooleanVar(value=s.get("anti_habit_enabled", True))
        self.rand_btns_var = tk.BooleanVar(value=s.get("randomize_buttons", True))
        self.hold_ms_var = tk.StringVar(value=str(s.get("studying_hold_ms", 800)))

        # Pause
        self.force_on_var = tk.BooleanVar(value=s.get("force_always_on", True))
        self.pause_var = tk.BooleanVar(value=s.get("pause_when_inactive_or_lid_closed", False))
        self.pause_on_idle_var = tk.BooleanVar(value=s.get("pause_on_idle", False))
        self.pause_on_lid_var = tk.BooleanVar(value=s.get("pause_on_lid_closed", True))
        self.pause_on_lock_var = tk.BooleanVar(value=s.get("pause_on_lock", True))
        self.pause_on_sleep_var = tk.BooleanVar(value=s.get("pause_on_sleep", True))
        self.idle_secs_var = tk.StringVar(value=str(s.get("inactive_as_sleep_seconds", 45)))
        self.pause_poll_var = tk.StringVar(value=str(s.get("pause_poll_interval_seconds", 5)))

        # Challenges - Global
        self.challenge_enabled_var = tk.BooleanVar(value=s.get("challenge_system_enabled", True))
        self.challenge_studying_freq_var = tk.DoubleVar(value=s.get("challenge_studying_frequency", 0.3))
        self.challenge_wasting_freq_var = tk.DoubleVar(value=s.get("challenge_wasting_frequency", 0.5))
        self.challenge_min_words_var = tk.StringVar(value=str(s.get("challenge_min_words", 5)))
        self.challenge_min_length_var = tk.StringVar(value=str(s.get("challenge_min_total_length", 20)))
        self.challenge_allow_skip_var = tk.BooleanVar(value=s.get("challenge_allow_skip", False))
        self.challenge_show_hints_var = tk.BooleanVar(value=s.get("challenge_show_hints", True))

        # Individual challenges
        self.studying_challenge_vars = {}
        for challenge_id, _, _ in self.STUDYING_CHALLENGES:
            self.studying_challenge_vars[challenge_id] = tk.BooleanVar(
                value=s.get(f"challenge_studying_{challenge_id}_enabled", True)
            )

        self.wasting_challenge_vars = {}
        for challenge_id, _, _ in self.WASTING_CHALLENGES:
            self.wasting_challenge_vars[challenge_id] = tk.BooleanVar(
                value=s.get(f"challenge_wasting_{challenge_id}_enabled", True)
            )

        # Spam detection
        self.spam_enabled_var = tk.BooleanVar(value=s.get("spam_detection_enabled", True))
        self.spam_gibberish_var = tk.BooleanVar(value=s.get("spam_gibberish_detection", True))
        self.spam_min_vowel_var = tk.DoubleVar(value=s.get("spam_min_vowel_ratio", 0.2))
        self.spam_max_vowel_var = tk.DoubleVar(value=s.get("spam_max_vowel_ratio", 0.7))
        self.spam_min_unique_var = tk.DoubleVar(value=s.get("spam_min_unique_char_ratio", 0.4))
        self.spam_repetition_var = tk.BooleanVar(value=s.get("spam_repetition_check", True))
        self.spam_max_consecutive_var = tk.StringVar(value=str(s.get("spam_max_consecutive_chars", 2)))
        self.spam_max_pattern_var = tk.StringVar(value=str(s.get("spam_max_pattern_repetition", 3)))
        self.spam_spacing_var = tk.BooleanVar(value=s.get("spam_spacing_check", True))
        self.spam_min_spaces_var = tk.StringVar(value=str(s.get("spam_min_length_require_spaces", 15)))
        self.spam_keyboard_var = tk.BooleanVar(value=s.get("spam_keyboard_pattern_check", True))
        self.spam_min_keyboard_var = tk.StringVar(value=str(s.get("spam_min_keyboard_sequence_length", 4)))
        self.spam_dictionary_var = tk.BooleanVar(value=s.get("spam_dictionary_check", True))
        self.spam_min_word_ratio_var = tk.DoubleVar(value=s.get("spam_min_real_word_ratio", 0.6))
        self.spam_min_word_len_var = tk.StringVar(value=str(s.get("spam_min_word_length", 2)))
        self.spam_timing_var = tk.BooleanVar(value=s.get("spam_timing_check", True))
        self.spam_min_time_var = tk.StringVar(value=str(s.get("spam_min_time_to_submit", 3)))
        self.spam_flag_time_var = tk.StringVar(value=str(s.get("spam_flag_if_under", 2)))

        # UI
        self.waste_prompt_enabled_var = tk.BooleanVar(value=s.get("wasting_prompt_enabled", False))
        self.focus_prompt_enabled_var = tk.BooleanVar(value=s.get("focus_prompt_enabled", False))
        self.require_all_prompt_fields_var = tk.BooleanVar(value=s.get("prompt_require_all_fields", False))
        self.require_task_var = tk.BooleanVar(value=s.get("require_active_task", False))
        self.hide_waste_var = tk.BooleanVar(value=s.get("hide_wasting_button", False))
        self.encourage_var = tk.BooleanVar(value=s.get("encouragement_enabled", True))
        self.show_analytics_var = tk.BooleanVar(value=s.get("show_task_analytics", True))

        # Tray
        self.tray_start_stop_enabled_var = tk.BooleanVar(value=s.get("tray_start_stop_enabled", True))
        self.tray_settings_enabled_var = tk.BooleanVar(value=s.get("tray_settings_button_enabled", True))
        self.tray_exit_enabled_var = tk.BooleanVar(value=s.get("tray_exit_button_enabled", True))

    def _build_ui(self):
        """Build the main UI."""
        main_container = ttk.Frame(self)
        main_container.pack(fill="both", expand=True, padx=15, pady=15)
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_rowconfigure(0, weight=1)

        # Notebook
        self.notebook = ttk.Notebook(main_container)
        self.notebook.grid(row=0, column=0, sticky="nsew", pady=(0, 15))

        # Create tabs
        self._create_general_tab()
        self._create_challenges_tab()
        self._create_spam_tab()
        self._create_behavior_tab()

        # Button bar
        self._create_button_bar(main_container)

    def _create_scrollable_tab(self, parent, tab_name):
        """Create scrollable tab."""
        outer = ttk.Frame(parent)
        parent.add(outer, text=tab_name)

        canvas = tk.Canvas(outer, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        scrollable = ttk.Frame(canvas)

        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        return scrollable

    def _add_toggle_row(self, parent, text, variable, description=None):
        """Add a row with toggle switch."""
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=5)

        toggle = ToggleSwitch(frame, variable)
        toggle.pack(side="left", padx=(0, 15))

        label_frame = ttk.Frame(frame)
        label_frame.pack(side="left", fill="both", expand=True)

        ttk.Label(label_frame, text=text, font=("Segoe UI", 9)).pack(anchor="w")
        if description:
            ttk.Label(
                label_frame, text=description,
                foreground="gray", font=("Segoe UI", 8)
            ).pack(anchor="w", padx=(0, 0))

        return frame

    def _create_general_tab(self):
        """Create General tab."""
        tab = self._create_scrollable_tab(self.notebook, "General")

        # Info panel
        InfoPanel(
            tab,
            "Core settings that control FocusCheck's basic behavior and timing",
            panel_type="info"
        ).pack(fill="x", pady=(0, 15))

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
        self._add_toggle_row(tab, "Auto-focus follow-ups", self.modal_auto_focus_var,
                            "Automatically focus follow-up dialogs")

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

    def _create_challenges_tab(self):
        """Create Challenges tab with modern controls."""
        tab = self._create_scrollable_tab(self.notebook, "Challenges")

        # Info panel
        InfoPanel(
            tab,
            "Challenges force genuine reflection through hard validation constraints. " +
            "Customize which challenges appear and how often.",
            panel_type="tip"
        ).pack(fill="x", pady=(0, 15))

        # Presets
        PresetButton(
            tab, self.CHALLENGE_PRESETS, self._apply_preset
        ).pack(fill="x", pady=(0, 15))

        # Master toggle
        SectionHeader(tab, "Challenge System").pack(fill="x")
        self._add_toggle_row(
            tab, "Enable Challenge System", self.challenge_enabled_var,
            "Master toggle - disabling this turns off all challenges"
        )

        # Global Settings with sliders
        SectionHeader(tab, "Global Settings").pack(fill="x")
        LabeledSlider(
            tab, "Studying frequency:",
            self.challenge_studying_freq_var, 0.0, 1.0, show_percentage=True
        ).pack(fill="x", pady=5)
        LabeledSlider(
            tab, "Wasting frequency:",
            self.challenge_wasting_freq_var, 0.0, 1.0, show_percentage=True
        ).pack(fill="x", pady=5)

        SpinboxWithButtons(tab, "Minimum words:", self.challenge_min_words_var, 1, 20, "words").pack(fill="x", pady=3)
        SpinboxWithButtons(tab, "Minimum length:", self.challenge_min_length_var, 5, 100, "chars").pack(fill="x", pady=3)

        self._add_toggle_row(tab, "Allow skipping", self.challenge_allow_skip_var,
                            "Show cancel button on challenges")
        self._add_toggle_row(tab, "Show hints", self.challenge_show_hints_var,
                            "Display example answers")

        # Studying Challenges
        studying_header = SectionHeader(
            tab, "Studying Challenges",
            actions=[
                ("Enable All", lambda: self._toggle_all_challenges("studying", True)),
                ("Disable All", lambda: self._toggle_all_challenges("studying", False))
            ]
        )
        studying_header.pack(fill="x")

        for challenge_id, name, description in self.STUDYING_CHALLENGES:
            card = ChallengeCard(
                tab, challenge_id, name, description,
                self.studying_challenge_vars[challenge_id]
            )
            card.pack(fill="x", pady=5)

        # Wasting Challenges
        wasting_header = SectionHeader(
            tab, "Wasting Time Challenges",
            actions=[
                ("Enable All", lambda: self._toggle_all_challenges("wasting", True)),
                ("Disable All", lambda: self._toggle_all_challenges("wasting", False))
            ]
        )
        wasting_header.pack(fill="x")

        for challenge_id, name, description in self.WASTING_CHALLENGES:
            card = ChallengeCard(
                tab, challenge_id, name, description,
                self.wasting_challenge_vars[challenge_id]
            )
            card.pack(fill="x", pady=5)

    def _create_spam_tab(self):
        """Create Spam Detection tab."""
        tab = self._create_scrollable_tab(self.notebook, "Spam Detection")

        InfoPanel(
            tab,
            "Spam detection prevents low-effort responses and gaming the system",
            panel_type="warning"
        ).pack(fill="x", pady=(0, 15))

        SectionHeader(tab, "Spam Detection").pack(fill="x")
        self._add_toggle_row(tab, "Enable spam detection", self.spam_enabled_var,
                            "Master toggle for all spam checks")

        # Gibberish
        card = ExpandableCard(tab, "Gibberish Detection")
        card.pack(fill="x", pady=5)
        card.add_content(self._add_toggle_row(card.content, "Enable gibberish check",
                                              self.spam_gibberish_var))
        card.add_content(LabeledSlider(card.content, "Min vowel ratio:",
                                       self.spam_min_vowel_var, 0.0, 1.0, show_percentage=True))
        card.add_content(LabeledSlider(card.content, "Max vowel ratio:",
                                       self.spam_max_vowel_var, 0.0, 1.0, show_percentage=True))
        card.add_content(LabeledSlider(card.content, "Min unique chars:",
                                       self.spam_min_unique_var, 0.0, 1.0, show_percentage=True))

        # Repetition
        card2 = ExpandableCard(tab, "Repetition Detection")
        card2.pack(fill="x", pady=5)
        card2.add_content(self._add_toggle_row(card2.content, "Enable repetition check",
                                               self.spam_repetition_var))
        card2.add_content(SpinboxWithButtons(card2.content, "Max consecutive chars:",
                                             self.spam_max_consecutive_var, 1, 10, "count"))
        card2.add_content(SpinboxWithButtons(card2.content, "Max pattern repetition:",
                                             self.spam_max_pattern_var, 1, 10, "count"))

        # Spacing & Patterns
        card3 = ExpandableCard(tab, "Spacing & Keyboard Patterns")
        card3.pack(fill="x", pady=5)
        card3.add_content(self._add_toggle_row(card3.content, "Enable spacing check",
                                               self.spam_spacing_var))
        card3.add_content(SpinboxWithButtons(card3.content, "Min length for spaces:",
                                             self.spam_min_spaces_var, 5, 50, "chars"))
        card3.add_content(self._add_toggle_row(card3.content, "Enable keyboard patterns",
                                               self.spam_keyboard_var))
        card3.add_content(SpinboxWithButtons(card3.content, "Min keyboard sequence:",
                                             self.spam_min_keyboard_var, 3, 10, "chars"))

        # Dictionary
        card4 = ExpandableCard(tab, "Dictionary Validation")
        card4.pack(fill="x", pady=5)
        card4.add_content(self._add_toggle_row(card4.content, "Enable dictionary check",
                                               self.spam_dictionary_var))
        card4.add_content(LabeledSlider(card4.content, "Min real word ratio:",
                                       self.spam_min_word_ratio_var, 0.0, 1.0, show_percentage=True))
        card4.add_content(SpinboxWithButtons(card4.content, "Min word length:",
                                             self.spam_min_word_len_var, 1, 10, "chars"))

        # Timing
        card5 = ExpandableCard(tab, "Timing Checks")
        card5.pack(fill="x", pady=5)
        card5.add_content(self._add_toggle_row(card5.content, "Enable timing check",
                                               self.spam_timing_var))
        card5.add_content(SpinboxWithButtons(card5.content, "Min time to submit:",
                                             self.spam_min_time_var, 0, 30, "seconds"))
        card5.add_content(SpinboxWithButtons(card5.content, "Flag if under:",
                                             self.spam_flag_time_var, 0, 10, "seconds"))

    def _create_behavior_tab(self):
        """Create Behavior tab."""
        tab = self._create_scrollable_tab(self.notebook, "Behavior")

        SectionHeader(tab, "Prompt Settings").pack(fill="x")
        self._add_toggle_row(tab, "Enable wasting time prompt", self.waste_prompt_enabled_var,
                            "Ask for details when clicking 'Wasting Time'")
        self._add_toggle_row(tab, "Enable studying prompt", self.focus_prompt_enabled_var,
                            "Ask for details when clicking 'Studying'")
        self._add_toggle_row(tab, "Require all fields", self.require_all_prompt_fields_var,
                            "Must answer all follow-up questions")
        self._add_toggle_row(tab, "Require active task", self.require_task_var,
                            "Must have a task to close prompt")

        SectionHeader(tab, "UI Options").pack(fill="x")
        self._add_toggle_row(tab, "Hide wasting button", self.hide_waste_var,
                            "Remove 'Wasting Time' button from main dialog")
        self._add_toggle_row(tab, "Show task encouragement", self.encourage_var)
        self._add_toggle_row(tab, "Show task analytics", self.show_analytics_var)

    def _create_button_bar(self, parent):
        """Create button bar."""
        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=1, column=0, sticky="e")

        ttk.Button(btn_frame, text="Cancel", command=self.destroy, width=12).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Save", command=self._save, width=12).pack(side="right")

    def _toggle_all_challenges(self, challenge_type, enabled):
        """Enable or disable all challenges of a type."""
        if challenge_type == "studying":
            for var in self.studying_challenge_vars.values():
                var.set(enabled)
        else:
            for var in self.wasting_challenge_vars.values():
                var.set(enabled)

    def _apply_preset(self, preset_config):
        """Apply a preset configuration."""
        # Enable/disable system
        self.challenge_enabled_var.set(preset_config.get("enabled", True))

        # Set frequencies
        self.challenge_studying_freq_var.set(preset_config.get("studying_freq", 0.3))
        self.challenge_wasting_freq_var.set(preset_config.get("wasting_freq", 0.5))

        # Set individual challenges
        studying = preset_config.get("studying_challenges", "all")
        if studying == "all":
            for var in self.studying_challenge_vars.values():
                var.set(True)
        else:
            for challenge_id, var in self.studying_challenge_vars.items():
                var.set(challenge_id in studying)

        wasting = preset_config.get("wasting_challenges", "all")
        if wasting == "all":
            for var in self.wasting_challenge_vars.values():
                var.set(True)
        else:
            for challenge_id, var in self.wasting_challenge_vars.items():
                var.set(challenge_id in wasting)

    def _safe_int(self, var, default):
        """Safely convert to int."""
        try:
            return int((var.get() or str(default)).strip())
        except (ValueError, AttributeError):
            return default

    def _safe_float(self, var, default, min_val=None, max_val=None):
        """Safely convert to float with clamping."""
        try:
            val = float(var.get())
            if min_val is not None:
                val = max(min_val, val)
            if max_val is not None:
                val = min(max_val, val)
            return val
        except (ValueError, AttributeError):
            return default

    def _save(self):
        """Save all settings."""
        from focuscheck.settings.manager import save_settings

        try:
            s = {
                # Core
                "interval_seconds": max(10, self._safe_int(self.interval_var, 60)),
                "intensify_after_seconds": max(5, self._safe_int(self.intensify_var, 15)),
                "overdrive_after_seconds": max(20, self._safe_int(self.overdrive_var, 60)),
                "max_intensity_level": min(3, max(1, self._safe_int(self.max_intensity_var, 3))),
                "always_on_top": bool(self.topmost_var.get()),
                "center_on_show": bool(self.center_var.get()),
                "modal_dialog_auto_focus": bool(self.modal_auto_focus_var.get()),
                "follow_cursor_monitor": bool(self.follow_cursor_var.get()),
                "webhook_url": self.webhook_var.get().strip(),

                # Anti-habit
                "anti_habit_enabled": bool(self.anti_var.get()),
                "randomize_buttons": bool(self.rand_btns_var.get()),
                "studying_hold_ms": max(0, self._safe_int(self.hold_ms_var, 800)),

                # Pause
                "force_always_on": bool(self.force_on_var.get()),
                "pause_when_inactive_or_lid_closed": bool(self.pause_var.get()),
                "pause_on_idle": bool(self.pause_on_idle_var.get()),
                "pause_on_lid_closed": bool(self.pause_on_lid_var.get()),
                "pause_on_lock": bool(self.pause_on_lock_var.get()),
                "pause_on_sleep": bool(self.pause_on_sleep_var.get()),
                "inactive_as_sleep_seconds": max(15, self._safe_int(self.idle_secs_var, 45)),
                "pause_poll_interval_seconds": max(2, self._safe_int(self.pause_poll_var, 5)),

                # Challenges
                "challenge_system_enabled": bool(self.challenge_enabled_var.get()),
                "challenge_studying_frequency": self._safe_float(self.challenge_studying_freq_var, 0.3, 0.0, 1.0),
                "challenge_wasting_frequency": self._safe_float(self.challenge_wasting_freq_var, 0.5, 0.0, 1.0),
                "challenge_min_words": max(1, self._safe_int(self.challenge_min_words_var, 5)),
                "challenge_min_total_length": max(1, self._safe_int(self.challenge_min_length_var, 20)),
                "challenge_allow_skip": bool(self.challenge_allow_skip_var.get()),
                "challenge_show_hints": bool(self.challenge_show_hints_var.get()),

                # Spam
                "spam_detection_enabled": bool(self.spam_enabled_var.get()),
                "spam_gibberish_detection": bool(self.spam_gibberish_var.get()),
                "spam_min_vowel_ratio": self._safe_float(self.spam_min_vowel_var, 0.2, 0.0, 1.0),
                "spam_max_vowel_ratio": self._safe_float(self.spam_max_vowel_var, 0.7, 0.0, 1.0),
                "spam_min_unique_char_ratio": self._safe_float(self.spam_min_unique_var, 0.4, 0.0, 1.0),
                "spam_repetition_check": bool(self.spam_repetition_var.get()),
                "spam_max_consecutive_chars": max(1, self._safe_int(self.spam_max_consecutive_var, 2)),
                "spam_max_pattern_repetition": max(1, self._safe_int(self.spam_max_pattern_var, 3)),
                "spam_spacing_check": bool(self.spam_spacing_var.get()),
                "spam_min_length_require_spaces": max(1, self._safe_int(self.spam_min_spaces_var, 15)),
                "spam_keyboard_pattern_check": bool(self.spam_keyboard_var.get()),
                "spam_min_keyboard_sequence_length": max(1, self._safe_int(self.spam_min_keyboard_var, 4)),
                "spam_dictionary_check": bool(self.spam_dictionary_var.get()),
                "spam_min_real_word_ratio": self._safe_float(self.spam_min_word_ratio_var, 0.6, 0.0, 1.0),
                "spam_min_word_length": max(1, self._safe_int(self.spam_min_word_len_var, 2)),
                "spam_timing_check": bool(self.spam_timing_var.get()),
                "spam_min_time_to_submit": max(0, self._safe_int(self.spam_min_time_var, 3)),
                "spam_flag_if_under": max(0, self._safe_int(self.spam_flag_time_var, 2)),

                # UI
                "wasting_prompt_enabled": bool(self.waste_prompt_enabled_var.get()),
                "focus_prompt_enabled": bool(self.focus_prompt_enabled_var.get()),
                "prompt_require_all_fields": bool(self.require_all_prompt_fields_var.get()),
                "require_active_task": bool(self.require_task_var.get()),
                "hide_wasting_button": bool(self.hide_waste_var.get()),
                "encouragement_enabled": bool(self.encourage_var.get()),
                "show_task_analytics": bool(self.show_analytics_var.get()),

                # Tray
                "tray_start_stop_enabled": bool(self.tray_start_stop_enabled_var.get()),
                "tray_settings_button_enabled": bool(self.tray_settings_enabled_var.get()),
                "tray_exit_button_enabled": bool(self.tray_exit_enabled_var.get()),
            }

            # Individual challenges
            for challenge_id, _, _ in self.STUDYING_CHALLENGES:
                s[f"challenge_studying_{challenge_id}_enabled"] = bool(
                    self.studying_challenge_vars[challenge_id].get()
                )

            for challenge_id, _, _ in self.WASTING_CHALLENGES:
                s[f"challenge_wasting_{challenge_id}_enabled"] = bool(
                    self.wasting_challenge_vars[challenge_id].get()
                )

            save_settings(s)
            self.on_save(s)
            self.destroy()

        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save settings: {e}")


# Backwards compatibility - use advanced window as default
SettingsWindow = AdvancedSettingsWindow

# Keep TaskHistoryWindow from the other file
from .windows import TaskHistoryWindow

__all__ = ['SettingsWindow', 'AdvancedSettingsWindow', 'TaskHistoryWindow']

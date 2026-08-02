"""
Modern, scrollable settings window with individual challenge controls.

Follows design principles:
- Resizable window with proper scrolling
- Grouped settings with clear hierarchy
- Breathing room between sections
- Individual control over each feature
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime


class ModernSettingsWindow(tk.Toplevel):
    """
    Modern settings dialog with scrollable tabs and individual challenge controls.

    Design improvements:
    - Fully resizable window
    - Smooth scrolling in all tabs
    - Better visual hierarchy with frames
    - Individual challenge enable/disable
    - Cleaner spacing and organization
    """

    # Challenge IDs for individual control
    STUDYING_CHALLENGES = [
        ("learning_specificity", "Learning Specificity", "Requires naming exact topic being learned"),
        ("goal_connection", "Goal Connection", "Forces stating the goal/purpose"),
        ("will_commitment", "Will Commitment", "Demands concrete 'I will...' statement"),
        ("output_expectation", "Output Expectation", "Requires describing specific deliverable"),
    ]

    WASTING_CHALLENGES = [
        ("wasting_acknowledgment", "Wasting Acknowledgment", "Forces acknowledging specific cost"),
        ("should_gap", "Should Gap", "Demands contrast between doing vs should"),
        ("because_reasoning", "Because Reasoning", "Requires explaining real reason"),
        ("hour_projection", "Hour Projection", "Forces projecting 1-hour consequence"),
        ("tomorrow_regret", "Tomorrow Regret", "Demands acknowledging future regret"),
        ("fear_acknowledgment", "Fear Acknowledgment", "Forces naming the underlying fear"),
        ("lying_confrontation", "Lying Confrontation", "Requires admitting self-deception"),
    ]

    def __init__(self, master, settings, on_save):
        super().__init__(master)
        self.title("Settings")
        self.geometry("900x700")  # Larger default size
        self.minsize(800, 600)  # Minimum size
        self.settings = settings.copy()
        self.on_save = on_save

        # Initialize all settings variables
        self._init_vars()

        # Build the UI
        self._build_ui()

        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _init_vars(self):
        """Initialize all tkinter variables from settings."""
        s = self.settings

        # Core settings
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

        # Pause controls
        self.force_on_var = tk.BooleanVar(value=s.get("force_always_on", True))
        self.pause_var = tk.BooleanVar(value=s.get("pause_when_inactive_or_lid_closed", False))
        self.pause_on_idle_var = tk.BooleanVar(value=s.get("pause_on_idle", False))
        self.pause_on_lid_var = tk.BooleanVar(value=s.get("pause_on_lid_closed", True))
        self.pause_on_lock_var = tk.BooleanVar(value=s.get("pause_on_lock", True))
        self.pause_on_sleep_var = tk.BooleanVar(value=s.get("pause_on_sleep", True))
        self.idle_secs_var = tk.StringVar(value=str(s.get("inactive_as_sleep_seconds", 45)))
        self.pause_poll_var = tk.StringVar(value=str(s.get("pause_poll_interval_seconds", 5)))

        # Challenge system - Global
        self.challenge_enabled_var = tk.BooleanVar(value=s.get("challenge_system_enabled", True))
        self.challenge_studying_freq_var = tk.StringVar(value=str(s.get("challenge_studying_frequency", 0.3)))
        self.challenge_wasting_freq_var = tk.StringVar(value=str(s.get("challenge_wasting_frequency", 0.5)))
        self.challenge_min_words_var = tk.StringVar(value=str(s.get("challenge_min_words", 5)))
        self.challenge_min_length_var = tk.StringVar(value=str(s.get("challenge_min_total_length", 20)))
        self.challenge_allow_skip_var = tk.BooleanVar(value=s.get("challenge_allow_skip", False))
        self.challenge_show_hints_var = tk.BooleanVar(value=s.get("challenge_show_hints", True))

        # Individual studying challenges
        self.studying_challenge_vars = {}
        for challenge_id, _, _ in self.STUDYING_CHALLENGES:
            self.studying_challenge_vars[challenge_id] = tk.BooleanVar(
                value=s.get(f"challenge_studying_{challenge_id}_enabled", True)
            )

        # Individual wasting challenges
        self.wasting_challenge_vars = {}
        for challenge_id, _, _ in self.WASTING_CHALLENGES:
            self.wasting_challenge_vars[challenge_id] = tk.BooleanVar(
                value=s.get(f"challenge_wasting_{challenge_id}_enabled", True)
            )

        # Spam detection
        self.spam_enabled_var = tk.BooleanVar(value=s.get("spam_detection_enabled", True))
        self.spam_gibberish_var = tk.BooleanVar(value=s.get("spam_gibberish_detection", True))
        self.spam_min_vowel_var = tk.StringVar(value=str(s.get("spam_min_vowel_ratio", 0.2)))
        self.spam_max_vowel_var = tk.StringVar(value=str(s.get("spam_max_vowel_ratio", 0.7)))
        self.spam_min_unique_var = tk.StringVar(value=str(s.get("spam_min_unique_char_ratio", 0.4)))
        self.spam_repetition_var = tk.BooleanVar(value=s.get("spam_repetition_check", True))
        self.spam_max_consecutive_var = tk.StringVar(value=str(s.get("spam_max_consecutive_chars", 2)))
        self.spam_max_pattern_var = tk.StringVar(value=str(s.get("spam_max_pattern_repetition", 3)))
        self.spam_spacing_var = tk.BooleanVar(value=s.get("spam_spacing_check", True))
        self.spam_min_spaces_var = tk.StringVar(value=str(s.get("spam_min_length_require_spaces", 15)))
        self.spam_keyboard_var = tk.BooleanVar(value=s.get("spam_keyboard_pattern_check", True))
        self.spam_min_keyboard_var = tk.StringVar(value=str(s.get("spam_min_keyboard_sequence_length", 4)))
        self.spam_dictionary_var = tk.BooleanVar(value=s.get("spam_dictionary_check", True))
        self.spam_min_word_ratio_var = tk.StringVar(value=str(s.get("spam_min_real_word_ratio", 0.6)))
        self.spam_min_word_len_var = tk.StringVar(value=str(s.get("spam_min_word_length", 2)))
        self.spam_timing_var = tk.BooleanVar(value=s.get("spam_timing_check", True))
        self.spam_min_time_var = tk.StringVar(value=str(s.get("spam_min_time_to_submit", 3)))
        self.spam_flag_time_var = tk.StringVar(value=str(s.get("spam_flag_if_under", 2)))

        # Prompts
        self.waste_prompt_enabled_var = tk.BooleanVar(value=s.get("wasting_prompt_enabled", False))
        self.focus_prompt_enabled_var = tk.BooleanVar(value=s.get("focus_prompt_enabled", False))
        self.require_all_prompt_fields_var = tk.BooleanVar(value=s.get("prompt_require_all_fields", False))
        self.require_task_var = tk.BooleanVar(value=s.get("require_active_task", False))

        # Tasks
        self.hide_waste_var = tk.BooleanVar(value=s.get("hide_wasting_button", False))
        self.encourage_var = tk.BooleanVar(value=s.get("encouragement_enabled", True))
        self.show_analytics_var = tk.BooleanVar(value=s.get("show_task_analytics", True))

        # Tray
        self.tray_start_stop_enabled_var = tk.BooleanVar(value=s.get("tray_start_stop_enabled", True))
        self.tray_settings_enabled_var = tk.BooleanVar(value=s.get("tray_settings_button_enabled", True))
        self.tray_exit_enabled_var = tk.BooleanVar(value=s.get("tray_exit_button_enabled", True))

    def _build_ui(self):
        """Build the main UI."""
        # Main container with grid
        main_container = ttk.Frame(self)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_rowconfigure(0, weight=1)

        # Create notebook
        self.notebook = ttk.Notebook(main_container)
        self.notebook.grid(row=0, column=0, sticky="nsew", pady=(0, 10))

        # Create tabs (each will be scrollable)
        self._create_general_tab()
        self._create_challenges_tab()
        self._create_spam_tab()
        self._create_behavior_tab()
        self._create_advanced_tab()

        # Bottom button bar
        self._create_button_bar(main_container)

    def _create_scrollable_tab(self, parent, tab_name):
        """Create a scrollable tab container."""
        # Outer frame
        outer_frame = ttk.Frame(parent)
        parent.add(outer_frame, text=tab_name)

        # Canvas and scrollbar
        canvas = tk.Canvas(outer_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        return scrollable_frame

    def _create_section_header(self, parent, text):
        """Create a section header with consistent styling."""
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=(20, 10))

        ttk.Label(frame, text=text, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        ttk.Separator(frame).pack(fill="x", pady=(5, 0))

        return frame

    def _create_labeled_entry(self, parent, label, variable, suffix="", width=15):
        """Create a labeled entry field."""
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=5)

        ttk.Label(frame, text=label, width=30).pack(side="left")
        ttk.Entry(frame, textvariable=variable, width=width).pack(side="left", padx=5)
        if suffix:
            ttk.Label(frame, text=suffix).pack(side="left")

        return frame

    def _create_checkbox(self, parent, text, variable, description=None):
        """Create a checkbox with optional description."""
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=3)

        ttk.Checkbutton(frame, text=text, variable=variable).pack(anchor="w")
        if description:
            ttk.Label(frame, text=f"  {description}", foreground="gray", font=("Segoe UI", 8)).pack(anchor="w", padx=20)

        return frame

    def _create_general_tab(self):
        """Create General settings tab."""
        tab = self._create_scrollable_tab(self.notebook, "General")

        self._create_section_header(tab, "Core Timing")
        self._create_labeled_entry(tab, "Check interval:", self.interval_var, "seconds")
        self._create_labeled_entry(tab, "Intensify after:", self.intensify_var, "seconds")
        self._create_labeled_entry(tab, "Overdrive after:", self.overdrive_var, "seconds")
        self._create_labeled_entry(tab, "Max intensity level:", self.max_intensity_var, "1-3")

        self._create_section_header(tab, "Window Behavior")
        self._create_checkbox(tab, "Always on top", self.topmost_var)
        self._create_checkbox(tab, "Center on show", self.center_var)
        self._create_checkbox(tab, "Follow cursor to monitor", self.follow_cursor_var,
                             "Recenter dialog on the monitor with mouse cursor")
        self._create_checkbox(tab, "Auto-focus follow-up dialogs", self.modal_auto_focus_var)

        self._create_section_header(tab, "Anti-Habit System")
        self._create_checkbox(tab, "Enable anti-habit", self.anti_var)
        self._create_checkbox(tab, "Randomize button positions", self.rand_btns_var)
        self._create_labeled_entry(tab, "Studying button hold time:", self.hold_ms_var, "ms")

        self._create_section_header(tab, "Pause Behavior")
        self._create_checkbox(tab, "Never pause (force always-on)", self.force_on_var,
                             "Override all pause conditions")
        self._create_checkbox(tab, "Pause on idle", self.pause_on_idle_var)
        self._create_labeled_entry(tab, "Idle threshold:", self.idle_secs_var, "seconds")
        self._create_checkbox(tab, "Pause on Windows lock", self.pause_on_lock_var)
        self._create_checkbox(tab, "Pause on system sleep", self.pause_on_sleep_var)
        self._create_checkbox(tab, "Pause on lid closed", self.pause_on_lid_var)

        self._create_section_header(tab, "System Tray")
        self._create_checkbox(tab, "Show Start/Stop button", self.tray_start_stop_enabled_var)
        self._create_checkbox(tab, "Show Settings button", self.tray_settings_enabled_var)
        self._create_checkbox(tab, "Show Exit button", self.tray_exit_enabled_var)

        self._create_section_header(tab, "Webhook (Optional)")
        frame = ttk.Frame(tab)
        frame.pack(fill="x", pady=5)
        ttk.Label(frame, text="Webhook URL:").pack(anchor="w")
        ttk.Entry(frame, textvariable=self.webhook_var, width=60).pack(fill="x", pady=5)

    def _create_challenges_tab(self):
        """Create Challenges tab with individual controls."""
        tab = self._create_scrollable_tab(self.notebook, "Challenges")

        self._create_section_header(tab, "Challenge System")
        self._create_checkbox(tab, "Enable challenge system", self.challenge_enabled_var,
                             "Master toggle for all challenges")

        self._create_section_header(tab, "Global Settings")
        self._create_labeled_entry(tab, "Studying frequency:", self.challenge_studying_freq_var,
                                  "0.0-1.0 (0.3 = 30%)")
        self._create_labeled_entry(tab, "Wasting frequency:", self.challenge_wasting_freq_var,
                                  "0.0-1.0 (0.5 = 50%)")
        self._create_labeled_entry(tab, "Minimum words:", self.challenge_min_words_var, "words")
        self._create_labeled_entry(tab, "Minimum length:", self.challenge_min_length_var, "characters")
        self._create_checkbox(tab, "Allow skipping", self.challenge_allow_skip_var,
                             "Show cancel button on challenges")
        self._create_checkbox(tab, "Show hints", self.challenge_show_hints_var,
                             "Display example answers")

        self._create_section_header(tab, "Studying Challenges")
        ttk.Label(tab, text="Select which challenges can appear when clicking 'Studying':",
                 foreground="gray", font=("Segoe UI", 9)).pack(anchor="w", pady=(0,10))

        for challenge_id, name, description in self.STUDYING_CHALLENGES:
            self._create_checkbox(tab, name, self.studying_challenge_vars[challenge_id], description)

        self._create_section_header(tab, "Wasting Time Challenges")
        ttk.Label(tab, text="Select which challenges can appear when clicking 'Wasting Time':",
                 foreground="gray", font=("Segoe UI", 9)).pack(anchor="w", pady=(0,10))

        for challenge_id, name, description in self.WASTING_CHALLENGES:
            self._create_checkbox(tab, name, self.wasting_challenge_vars[challenge_id], description)

    def _create_spam_tab(self):
        """Create Spam Detection tab."""
        tab = self._create_scrollable_tab(self.notebook, "Spam Detection")

        self._create_section_header(tab, "Spam Detection")
        self._create_checkbox(tab, "Enable spam detection", self.spam_enabled_var,
                             "Master toggle for all spam checks")

        self._create_section_header(tab, "Gibberish Detection")
        self._create_checkbox(tab, "Enable gibberish check", self.spam_gibberish_var)
        self._create_labeled_entry(tab, "Min vowel ratio:", self.spam_min_vowel_var, "0.0-1.0")
        self._create_labeled_entry(tab, "Max vowel ratio:", self.spam_max_vowel_var, "0.0-1.0")
        self._create_labeled_entry(tab, "Min unique chars:", self.spam_min_unique_var, "0.0-1.0")

        self._create_section_header(tab, "Repetition Detection")
        self._create_checkbox(tab, "Enable repetition check", self.spam_repetition_var)
        self._create_labeled_entry(tab, "Max consecutive chars:", self.spam_max_consecutive_var, "count")
        self._create_labeled_entry(tab, "Max pattern repetition:", self.spam_max_pattern_var, "count")

        self._create_section_header(tab, "Spacing & Patterns")
        self._create_checkbox(tab, "Enable spacing check", self.spam_spacing_var)
        self._create_labeled_entry(tab, "Min length for spaces:", self.spam_min_spaces_var, "chars")
        self._create_checkbox(tab, "Enable keyboard patterns", self.spam_keyboard_var)
        self._create_labeled_entry(tab, "Min keyboard sequence:", self.spam_min_keyboard_var, "chars")

        self._create_section_header(tab, "Dictionary Validation")
        self._create_checkbox(tab, "Enable dictionary check", self.spam_dictionary_var)
        self._create_labeled_entry(tab, "Min real word ratio:", self.spam_min_word_ratio_var, "0.0-1.0")
        self._create_labeled_entry(tab, "Min word length:", self.spam_min_word_len_var, "chars")

        self._create_section_header(tab, "Timing Checks")
        self._create_checkbox(tab, "Enable timing check", self.spam_timing_var)
        self._create_labeled_entry(tab, "Min time to submit:", self.spam_min_time_var, "seconds")
        self._create_labeled_entry(tab, "Flag if under:", self.spam_flag_time_var, "seconds")

    def _create_behavior_tab(self):
        """Create Behavior tab for prompts and UI."""
        tab = self._create_scrollable_tab(self.notebook, "Behavior")

        self._create_section_header(tab, "Prompt Settings")
        self._create_checkbox(tab, "Enable wasting time prompt", self.waste_prompt_enabled_var,
                             "Ask for details when clicking 'Wasting Time'")
        self._create_checkbox(tab, "Enable studying prompt", self.focus_prompt_enabled_var,
                             "Ask for details when clicking 'Studying'")
        self._create_checkbox(tab, "Require all fields", self.require_all_prompt_fields_var,
                             "Must answer all follow-up questions")
        self._create_checkbox(tab, "Require active task", self.require_task_var,
                             "Must have a task to close prompt")

        self._create_section_header(tab, "UI Options")
        self._create_checkbox(tab, "Hide wasting button", self.hide_waste_var,
                             "Remove 'Wasting Time' button from main dialog")
        self._create_checkbox(tab, "Show task encouragement", self.encourage_var)
        self._create_checkbox(tab, "Show task analytics", self.show_analytics_var)

    def _create_advanced_tab(self):
        """Create Advanced tab for power users."""
        tab = self._create_scrollable_tab(self.notebook, "Advanced")

        self._create_section_header(tab, "Advanced Settings")
        ttk.Label(tab, text="Additional settings will be added here.",
                 foreground="gray").pack(anchor="w", pady=10)

    def _create_button_bar(self, parent):
        """Create bottom button bar."""
        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=1, column=0, sticky="e")

        ttk.Button(btn_frame, text="Cancel", command=self.destroy, width=10).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Save", command=self._save, width=10).pack(side="right")

    def _safe_int(self, var, default):
        """Safely convert StringVar to int."""
        try:
            return int((var.get() or str(default)).strip())
        except (ValueError, AttributeError):
            return default

    def _safe_float(self, var, default, min_val=None, max_val=None):
        """Safely convert StringVar to float with clamping."""
        try:
            val = float((var.get() or str(default)).strip())
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

                # Challenge system - Global
                "challenge_system_enabled": bool(self.challenge_enabled_var.get()),
                "challenge_studying_frequency": self._safe_float(self.challenge_studying_freq_var, 0.3, 0.0, 1.0),
                "challenge_wasting_frequency": self._safe_float(self.challenge_wasting_freq_var, 0.5, 0.0, 1.0),
                "challenge_min_words": max(1, self._safe_int(self.challenge_min_words_var, 5)),
                "challenge_min_total_length": max(1, self._safe_int(self.challenge_min_length_var, 20)),
                "challenge_allow_skip": bool(self.challenge_allow_skip_var.get()),
                "challenge_show_hints": bool(self.challenge_show_hints_var.get()),

                # Spam detection
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

                # Prompts
                "wasting_prompt_enabled": bool(self.waste_prompt_enabled_var.get()),
                "focus_prompt_enabled": bool(self.focus_prompt_enabled_var.get()),
                "prompt_require_all_fields": bool(self.require_all_prompt_fields_var.get()),
                "require_active_task": bool(self.require_task_var.get()),

                # UI
                "hide_wasting_button": bool(self.hide_waste_var.get()),
                "encouragement_enabled": bool(self.encourage_var.get()),
                "show_task_analytics": bool(self.show_analytics_var.get()),

                # Tray
                "tray_start_stop_enabled": bool(self.tray_start_stop_enabled_var.get()),
                "tray_settings_button_enabled": bool(self.tray_settings_enabled_var.get()),
                "tray_exit_button_enabled": bool(self.tray_exit_enabled_var.get()),
            }

            # Individual studying challenges
            for challenge_id, _, _ in self.STUDYING_CHALLENGES:
                s[f"challenge_studying_{challenge_id}_enabled"] = bool(
                    self.studying_challenge_vars[challenge_id].get()
                )

            # Individual wasting challenges
            for challenge_id, _, _ in self.WASTING_CHALLENGES:
                s[f"challenge_wasting_{challenge_id}_enabled"] = bool(
                    self.wasting_challenge_vars[challenge_id].get()
                )

            save_settings(s)
            self.on_save(s)
            self.destroy()

        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save settings: {e}")


class TaskHistoryWindow(tk.Toplevel):
    """Task history window (unchanged from original)."""

    def __init__(self, master, taskdb, limit=200):
        super().__init__(master)
        self.title("Task History")
        self.configure(bg="#111")
        self.resizable(True, True)
        self.taskdb = taskdb
        self.geometry("820x420")

        try:
            from focuscheck.utils.logging_utils import log_exception
        except ImportError:
            def log_exception(msg):
                pass

        container = tk.Frame(self, bg="#111")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        cols = ("id","created","title","status","due","completed","timed_out","change_reason")
        tree = ttk.Treeview(container, columns=cols, show="headings", height=16)
        vsb = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        tree.configure(yscroll=vsb.set)

        tree.heading("id", text="ID")
        tree.heading("created", text="Created")
        tree.heading("title", text="Title")
        tree.heading("status", text="Status")
        tree.heading("due", text="Due")
        tree.heading("completed", text="Completed")
        tree.heading("timed_out", text="Timed-out")
        tree.heading("change_reason", text="Change Reason")

        tree.column("id", width=50, anchor="e")
        tree.column("created", width=140, anchor="w")
        tree.column("title", width=220, anchor="w")
        tree.column("status", width=90, anchor="w")
        tree.column("due", width=140, anchor="w")
        tree.column("completed", width=140, anchor="w")
        tree.column("timed_out", width=80, anchor="center")
        tree.column("change_reason", width=200, anchor="w")

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

        data = []
        try:
            data = self.taskdb.list_history(limit=limit, include_active=True)
        except Exception:
            log_exception("TaskHistoryWindow: failed loading history")

        for d in data:
            tree.insert("", "end", values=(
                d.get("id"),
                self._fmt_local(d.get("created_utc")),
                d.get("title", ""),
                d.get("status", ""),
                self._fmt_local(d.get("due_utc")),
                self._fmt_local(d.get("completed_utc")),
                int(d.get("timed_out", 0)),
                d.get("change_reason", "") or "",
            ))

        btns = ttk.Frame(container)
        btns.grid(row=1, column=0, columnspan=2, sticky="e", pady=(8,0))
        ttk.Button(btns, text="Close", command=self.destroy).pack(side="right")

        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _fmt_local(self, iso):
        if not iso:
            return ""
        try:
            dt = datetime.fromisoformat(iso)
            return dt.astimezone().strftime("%Y-%m-%d %H:%M")
        except Exception:
            return ""


# Maintain backwards compatibility
SettingsWindow = ModernSettingsWindow

__all__ = ['SettingsWindow', 'ModernSettingsWindow', 'TaskHistoryWindow']

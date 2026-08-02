"""
Main application windows.

Contains SettingsWindow and TaskHistoryWindow classes.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime


class SettingsWindow(tk.Toplevel):
    """Settings dialog window with tabbed interface for all configuration options."""

    def __init__(self, master, settings, on_save):
        super().__init__(master)
        self.title("Settings")
        self.resizable(False, False)
        self.settings = settings.copy()
        self.on_save = on_save
        pad = {"padx": 8, "pady": 6}

        def add_row(r, label, var, suffix=""):
            ttk.Label(self, text=label).grid(row=r, column=0, sticky="w", **pad)
            e = ttk.Entry(self, textvariable=var, width=12)
            e.grid(row=r, column=1, sticky="w", **pad)
            ttk.Label(self, text=suffix).grid(row=r, column=2, sticky="w")

        # Core timings
        self.interval_var = tk.StringVar(value=str(self.settings["interval_seconds"]))
        self.intensify_var = tk.StringVar(value=str(self.settings["intensify_after_seconds"]))
        self.overdrive_var = tk.StringVar(value=str(self.settings["overdrive_after_seconds"]))
        self.max_intensity_var = tk.StringVar(value=str(self.settings["max_intensity_level"]))

        self.topmost_var = tk.BooleanVar(value=bool(self.settings["always_on_top"]))
        self.center_var = tk.BooleanVar(value=bool(self.settings["center_on_show"]))
        self.modal_auto_focus_var = tk.BooleanVar(value=bool(self.settings.get("modal_dialog_auto_focus", True)))

        # Anti-habit
        self.anti_var = tk.BooleanVar(value=bool(self.settings["anti_habit_enabled"]))
        self.rand_btns_var = tk.BooleanVar(value=bool(self.settings["randomize_buttons"]))
        self.hold_ms_var = tk.StringVar(value=str(self.settings["studying_hold_ms"]))

        # Pause guard
        self.force_on_var = tk.BooleanVar(value=bool(self.settings.get("force_always_on", False)))
        self.pause_var = tk.BooleanVar(value=bool(self.settings["pause_when_inactive_or_lid_closed"]))
        self.pause_on_idle_var = tk.BooleanVar(value=bool(self.settings.get("pause_on_idle", False)))
        self.pause_on_lid_var = tk.BooleanVar(value=bool(self.settings.get("pause_on_lid_closed", True)))
        self.pause_on_lock_var = tk.BooleanVar(value=bool(self.settings.get("pause_on_lock", True)))
        self.pause_on_sleep_var = tk.BooleanVar(value=bool(self.settings.get("pause_on_sleep", True)))
        self.idle_secs_var = tk.StringVar(value=str(self.settings["inactive_as_sleep_seconds"]))
        self.pause_poll_var = tk.StringVar(value=str(self.settings["pause_poll_interval_seconds"]))

        self.webhook_var = tk.StringVar(value=str(self.settings.get("webhook_url", "")))
        # Stage 4 overdrive
        self.stage4_enabled_var = tk.BooleanVar(value=bool(self.settings.get("overdrive_stage4_enabled", True)))
        self.stage4_after_var = tk.StringVar(value=str(self.settings.get("overdrive_stage4_after_seconds", 12)))
        self.stage4_rate_var = tk.StringVar(value=str(self.settings.get("overdrive_stage4_flash_ms", 60)))

        # Stage 5 overdrive (screen blackout/dimming)
        self.stage5_enabled_var = tk.BooleanVar(value=bool(self.settings.get("overdrive_stage5_enabled", True)))
        self.stage5_after_var = tk.StringVar(value=str(self.settings.get("overdrive_stage5_after_seconds", 60)))
        self.stage5_pulse_var = tk.BooleanVar(value=bool(self.settings.get("overdrive_stage5_dim_pulse", True)))
        self.stage5_alpha_var = tk.StringVar(value=str(self.settings.get("overdrive_stage5_dim_max_alpha", 0.92)))
        self.stage5_color_var = tk.StringVar(value=str(self.settings.get("overdrive_stage5_dim_color", "#000000")))
        self.stage5_clickthrough_var = tk.BooleanVar(value=bool(self.settings.get("overdrive_stage5_click_through", True)))
        self.stage5_engine_var = tk.StringVar(value=str(self.settings.get("overdrive_stage5_engine", "overlay")))
        # New stage 5 features
        self.stage5_hold_after_var = tk.StringVar(value=str(self.settings.get("overdrive_stage5_hold_after_seconds", 0)))
        self.stage5_slow_dim_enabled_var = tk.BooleanVar(value=bool(self.settings.get("overdrive_stage5_slow_dim_enabled", False)))
        self.stage5_slow_dim_secs_var = tk.StringVar(value=str(self.settings.get("overdrive_stage5_slow_dim_seconds", 30)))

        # Time info settings
        self.show_time_info_var = tk.BooleanVar(value=bool(self.settings.get("show_time_info", False)))
        self.time_mode_var = tk.StringVar(value=str(self.settings.get("time_info_mode", "hour")))
        self.time_anchor_var = tk.StringVar(value=str(self.settings.get("time_info_anchor_hhmm", "09:00")))
        self.time_12h_var = tk.BooleanVar(value=bool(self.settings.get("time_info_12h", False)))
        self.time_secs_var = tk.BooleanVar(value=bool(self.settings.get("time_info_show_seconds", False)))
        self.time_refresh_var = tk.StringVar(value=str(self.settings.get("time_info_refresh_ms", 1000)))

        # Alert / jiggle behavior
        self.disable_jiggle_var = tk.BooleanVar(value=bool(self.settings.get("disable_jiggling", False)))
        self.intensity_pulse_var = tk.BooleanVar(value=bool(self.settings.get("enable_intensity_pulse", True)))
        self.intensity_shake_var = tk.BooleanVar(value=bool(self.settings.get("enable_intensity_shake", True)))
        self.intensity_arrows_var = tk.BooleanVar(value=bool(self.settings.get("enable_intensity_arrows", True)))

        # Challenge system
        self.challenge_enabled_var = tk.BooleanVar(value=bool(self.settings.get("challenge_system_enabled", True)))
        self.challenge_studying_freq_var = tk.StringVar(value=str(self.settings.get("challenge_studying_frequency", 0.3)))
        self.challenge_wasting_freq_var = tk.StringVar(value=str(self.settings.get("challenge_wasting_frequency", 0.5)))
        self.challenge_min_words_var = tk.StringVar(value=str(self.settings.get("challenge_min_words", 5)))
        self.challenge_min_length_var = tk.StringVar(value=str(self.settings.get("challenge_min_total_length", 20)))
        self.challenge_allow_skip_var = tk.BooleanVar(value=bool(self.settings.get("challenge_allow_skip", False)))
        self.challenge_show_hints_var = tk.BooleanVar(value=bool(self.settings.get("challenge_show_hints", True)))

        # Spam detection
        self.spam_enabled_var = tk.BooleanVar(value=bool(self.settings.get("spam_detection_enabled", True)))
        self.spam_gibberish_var = tk.BooleanVar(value=bool(self.settings.get("spam_gibberish_detection", True)))
        self.spam_min_vowel_var = tk.StringVar(value=str(self.settings.get("spam_min_vowel_ratio", 0.2)))
        self.spam_max_vowel_var = tk.StringVar(value=str(self.settings.get("spam_max_vowel_ratio", 0.7)))
        self.spam_min_unique_var = tk.StringVar(value=str(self.settings.get("spam_min_unique_char_ratio", 0.4)))
        self.spam_repetition_var = tk.BooleanVar(value=bool(self.settings.get("spam_repetition_check", True)))
        self.spam_max_consecutive_var = tk.StringVar(value=str(self.settings.get("spam_max_consecutive_chars", 2)))
        self.spam_max_pattern_var = tk.StringVar(value=str(self.settings.get("spam_max_pattern_repetition", 3)))
        self.spam_spacing_var = tk.BooleanVar(value=bool(self.settings.get("spam_spacing_check", True)))
        self.spam_min_spaces_var = tk.StringVar(value=str(self.settings.get("spam_min_length_require_spaces", 15)))
        self.spam_keyboard_var = tk.BooleanVar(value=bool(self.settings.get("spam_keyboard_pattern_check", True)))
        self.spam_min_keyboard_var = tk.StringVar(value=str(self.settings.get("spam_min_keyboard_sequence_length", 4)))
        self.spam_dictionary_var = tk.BooleanVar(value=bool(self.settings.get("spam_dictionary_check", True)))
        self.spam_min_word_ratio_var = tk.StringVar(value=str(self.settings.get("spam_min_real_word_ratio", 0.6)))
        self.spam_min_word_len_var = tk.StringVar(value=str(self.settings.get("spam_min_word_length", 2)))
        self.spam_timing_var = tk.BooleanVar(value=bool(self.settings.get("spam_timing_check", True)))
        self.spam_min_time_var = tk.StringVar(value=str(self.settings.get("spam_min_time_to_submit", 3)))
        self.spam_flag_time_var = tk.StringVar(value=str(self.settings.get("spam_flag_if_under", 2)))

        # Task / wasting-time prompt toggles
        self.waste_prompt_enabled_var = tk.BooleanVar(value=bool(self.settings.get("wasting_prompt_enabled", False)))
        self.waste_prompt_what_var = tk.BooleanVar(value=bool(self.settings.get("wasting_prompt_ask_what", True)))
        self.waste_prompt_cons_var = tk.BooleanVar(value=bool(self.settings.get("wasting_prompt_ask_consequences", True)))
        self.focus_prompt_enabled_var = tk.BooleanVar(value=bool(self.settings.get("focus_prompt_enabled", False)))
        self.focus_prompt_doing_var = tk.BooleanVar(value=bool(self.settings.get("focus_prompt_ask_doing", True)))
        self.focus_prompt_benefits_var = tk.BooleanVar(value=bool(self.settings.get("focus_prompt_ask_benefits", True)))
        self.require_all_prompt_fields_var = tk.BooleanVar(value=bool(self.settings.get("prompt_require_all_fields", False)))
        self.shake_lock_var = tk.BooleanVar(value=bool(self.settings.get("shake_lock_position", True)))
        self.od_flash_bg_var = tk.BooleanVar(value=bool(self.settings.get("enable_overdrive_flash_background", True)))
        self.od_shake_loop_var = tk.BooleanVar(value=bool(self.settings.get("enable_overdrive_shake_loop", True)))
        self.od_jiggle_btns_var = tk.BooleanVar(value=bool(self.settings.get("enable_overdrive_jiggle_buttons", True)))
        self.jiggle_style_var = tk.StringVar(value=str(self.settings.get("jiggle_style", "nudge")))

        # Task / UI settings
        self.hide_waste_var = tk.BooleanVar(value=bool(self.settings.get("hide_wasting_button", False)))
        self.encourage_var = tk.BooleanVar(value=bool(self.settings.get("encouragement_enabled", True)))
        self.show_analytics_var = tk.BooleanVar(value=bool(self.settings.get("show_task_analytics", True)))
        self.change_as_fail_var = tk.BooleanVar(value=bool(self.settings.get("tasks_change_counts_as_fail", True)))
        self.require_task_var = tk.BooleanVar(value=bool(self.settings.get("require_active_task", False)))
        self.tasks_timescale_var = tk.StringVar(value=str(self.settings.get("tasks_analytics_timescale", "lifetime")))
        self.tasks_decision_enabled_var = tk.BooleanVar(value=bool(self.settings.get("tasks_decision_prompt_enabled", True)))
        # Unified window
        self.tasks_decision_window_var = tk.StringVar(value=str(self.settings.get("tasks_decision_window_minutes", 10)))
        self.tasks_study_implies_fail_var = tk.BooleanVar(value=bool(self.settings.get("tasks_study_implies_fail_on_decision", True)))
        self.tasks_eval_mode_var = tk.StringVar(value=str(self.settings.get("tasks_evaluation_mode", "before")))

        # New general/tray settings
        self.follow_cursor_var = tk.BooleanVar(value=bool(self.settings.get("follow_cursor_monitor", True)))
        self.tray_start_stop_enabled_var = tk.BooleanVar(value=bool(self.settings.get("tray_start_stop_enabled", True)))
        self.tray_settings_enabled_var = tk.BooleanVar(value=bool(self.settings.get("tray_settings_button_enabled", True)))
        self.tray_exit_enabled_var = tk.BooleanVar(value=bool(self.settings.get("tray_exit_button_enabled", True)))
        # New time info toggle for task remaining
        self.time_show_task_left_var = tk.BooleanVar(value=bool(self.settings.get("time_info_show_task_remaining", False)))

        # Tabbed notebook
        # Make main content scrollable (Notebook inside a Canvas)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        scroll_container = ttk.Frame(self)
        scroll_container.grid(row=0, column=0, sticky="nsew")
        scroll_container.grid_columnconfigure(0, weight=1)
        scroll_container.grid_rowconfigure(0, weight=1)
        cv = tk.Canvas(scroll_container, highlightthickness=0)
        vsb = ttk.Scrollbar(scroll_container, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=vsb.set)
        cv.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        nb = ttk.Notebook(cv)
        _nbw = cv.create_window((0, 0), window=nb, anchor="nw")
        def _sync_scroll(_evt=None):
            try:
                cv.configure(scrollregion=cv.bbox("all"))
                cv.itemconfigure(_nbw, width=cv.winfo_width())
            except Exception:
                pass
        nb.bind("<Configure>", _sync_scroll)
        cv.bind("<Configure>", _sync_scroll)

        tab_general = ttk.Frame(nb)
        tab_tray = ttk.Frame(nb)
        tab_antihabit = ttk.Frame(nb)
        tab_pause = ttk.Frame(nb)
        tab_overdrive = ttk.Frame(nb)
        tab_time = ttk.Frame(nb)
        tab_tasks = ttk.Frame(nb)
        tab_challenges = ttk.Frame(nb)
        tab_spam = ttk.Frame(nb)

        nb.add(tab_general, text="General")
        nb.add(tab_tray, text="Tray")
        nb.add(tab_antihabit, text="Anti-Habit")
        nb.add(tab_pause, text="Pause")
        nb.add(tab_overdrive, text="Overdrive")
        nb.add(tab_time, text="Time Info")
        nb.add(tab_tasks, text="Tasks")
        nb.add(tab_challenges, text="Challenges")
        nb.add(tab_spam, text="Spam Detection")

        # General
        def add_row_to(parent, r, label, var, suffix=""):
            ttk.Label(parent, text=label).grid(row=r, column=0, sticky="w", **pad)
            e = ttk.Entry(parent, textvariable=var, width=12)
            e.grid(row=r, column=1, sticky="w", **pad)
            ttk.Label(parent, text=suffix).grid(row=r, column=2, sticky="w")
        add_row_to(tab_general, 0, "Interval:", self.interval_var, "seconds")
        add_row_to(tab_general, 1, "Intensify after:", self.intensify_var, "seconds")
        add_row_to(tab_general, 2, "Overdrive after:", self.overdrive_var, "seconds")
        add_row_to(tab_general, 3, "Max intensity level:", self.max_intensity_var, "1–3")
        ttk.Checkbutton(tab_general, text="Always on top", variable=self.topmost_var).grid(row=4, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_general, text="Center on show", variable=self.center_var).grid(row=5, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_general, text="Recenter to cursor's monitor while open", variable=self.follow_cursor_var).grid(row=6, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_general, text="Auto-focus follow-up dialogs", variable=self.modal_auto_focus_var).grid(row=7, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(tab_general, text="Webhook URL (optional)").grid(row=8, column=0, columnspan=3, sticky="w", **pad)
        ttk.Entry(tab_general, textvariable=self.webhook_var, width=48).grid(row=9, column=0, columnspan=3, sticky="we", padx=8, pady=(0,8))

        # Tray
        ttk.Label(tab_tray, text="Tray Menu Buttons", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_tray, text="Show start/stop button", variable=self.tray_start_stop_enabled_var).grid(row=1, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_tray, text="Show settings button", variable=self.tray_settings_enabled_var).grid(row=2, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_tray, text="Show exit button", variable=self.tray_exit_enabled_var).grid(row=3, column=0, columnspan=3, sticky="w", **pad)

        # Anti-Habit
        ttk.Checkbutton(tab_antihabit, text="Anti-habit enabled", variable=self.anti_var).grid(row=0, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_antihabit, text="Randomize button positions", variable=self.rand_btns_var).grid(row=1, column=0, columnspan=3, sticky="w", **pad)
        add_row_to(tab_antihabit, 2, "Studying hold:", self.hold_ms_var, "ms")

        # Pause
        ttk.Checkbutton(tab_pause, text="Never pause (force always-on)", variable=self.force_on_var).grid(row=0, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_pause, text="Enable pausing when away/asleep", variable=self.pause_var).grid(row=1, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_pause, text="Pause on idle (no keyboard/mouse)", variable=self.pause_on_idle_var).grid(row=2, column=0, columnspan=3, sticky="w", **pad)
        add_row_to(tab_pause, 3, "Idle threshold:", self.idle_secs_var, "seconds")
        ttk.Checkbutton(tab_pause, text="Pause on Windows lock", variable=self.pause_on_lock_var).grid(row=4, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_pause, text="Pause on system sleep", variable=self.pause_on_sleep_var).grid(row=5, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_pause, text="Pause on lid closed (Linux/macOS)", variable=self.pause_on_lid_var).grid(row=6, column=0, columnspan=3, sticky="w", **pad)
        add_row_to(tab_pause, 7, "Pause poll interval:", self.pause_poll_var, "seconds")

        # Overdrive
        ttk.Checkbutton(tab_overdrive, text="Enable Stage 4 overdrive (ultra-fast red flash)", variable=self.stage4_enabled_var).grid(row=0, column=0, columnspan=3, sticky="w", **pad)
        add_row_to(tab_overdrive, 1, "Stage 4 after:", self.stage4_after_var, "seconds")
        add_row_to(tab_overdrive, 2, "Stage 4 flash rate:", self.stage4_rate_var, "ms")
        ttk.Separator(tab_overdrive).grid(row=3, column=0, columnspan=3, sticky="ew", padx=8, pady=(4,6))
        ttk.Checkbutton(tab_overdrive, text="Disable all jiggling/movement", variable=self.disable_jiggle_var).grid(row=4, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_overdrive, text="Intensity: pulse buttons", variable=self.intensity_pulse_var).grid(row=5, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_overdrive, text="Intensity: shake window", variable=self.intensity_shake_var).grid(row=6, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_overdrive, text="Keep window fixed (no movement)", variable=self.shake_lock_var).grid(row=7, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_overdrive, text="Intensity: flashing arrows", variable=self.intensity_arrows_var).grid(row=8, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_overdrive, text="Overdrive: flash background", variable=self.od_flash_bg_var).grid(row=9, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_overdrive, text="Overdrive: shake window loop", variable=self.od_shake_loop_var).grid(row=10, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_overdrive, text="Overdrive: jiggle buttons", variable=self.od_jiggle_btns_var).grid(row=11, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(tab_overdrive, text="Jiggle style").grid(row=12, column=0, sticky="w", **pad)
        ttk.Combobox(tab_overdrive, textvariable=self.jiggle_style_var, values=("off","nudge","pulse"), state="readonly", width=12).grid(row=12, column=1, sticky="w", **pad)

        # Stage 5 (multi-monitor dim/blackout)
        ttk.Separator(tab_overdrive).grid(row=19, column=0, columnspan=3, sticky="ew", padx=8, pady=(8,6))
        ttk.Checkbutton(tab_overdrive, text="Enable Stage 5 overdrive (dim/blackout)", variable=self.stage5_enabled_var).grid(row=20, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(tab_overdrive, text="Stage 5 after (sec after Stage 4)").grid(row=21, column=0, sticky="w", **pad)
        ttk.Entry(tab_overdrive, textvariable=self.stage5_after_var, width=12).grid(row=21, column=1, sticky="w", **pad)
        ttk.Checkbutton(tab_overdrive, text="Allow clicks through dimmer (no input blocking)", variable=self.stage5_clickthrough_var).grid(row=22, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_overdrive, text="Pulse dimming (fade in/out)", variable=self.stage5_pulse_var).grid(row=23, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(tab_overdrive, text="Max dim alpha (0-1)").grid(row=24, column=0, sticky="w", **pad)
        ttk.Entry(tab_overdrive, textvariable=self.stage5_alpha_var, width=12).grid(row=24, column=1, sticky="w", **pad)
        ttk.Label(tab_overdrive, text="Overlay color (#RRGGBB)").grid(row=25, column=0, sticky="w", **pad)
        ttk.Entry(tab_overdrive, textvariable=self.stage5_color_var, width=12).grid(row=25, column=1, sticky="w", **pad)
        ttk.Label(tab_overdrive, text="Dim engine").grid(row=26, column=0, sticky="w", **pad)
        ttk.Combobox(tab_overdrive, textvariable=self.stage5_engine_var, values=("overlay","gamma"), state="readonly", width=12).grid(row=26, column=1, sticky="w", **pad)
        ttk.Checkbutton(tab_overdrive, text="Slow-dim to black (one-way)", variable=self.stage5_slow_dim_enabled_var).grid(row=27, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(tab_overdrive, text="Slow-dim duration").grid(row=28, column=0, sticky="w", **pad)
        ttk.Entry(tab_overdrive, textvariable=self.stage5_slow_dim_secs_var, width=12).grid(row=28, column=1, sticky="w", **pad)
        ttk.Label(tab_overdrive, text="Hold black after").grid(row=29, column=0, sticky="w", **pad)
        ttk.Entry(tab_overdrive, textvariable=self.stage5_hold_after_var, width=12).grid(row=29, column=1, sticky="w", **pad)

        # Time Info
        ttk.Checkbutton(tab_time, text="Show time info under buttons", variable=self.show_time_info_var).grid(row=0, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(tab_time, text="Time info mode").grid(row=1, column=0, sticky="w", **pad)
        ttk.Combobox(tab_time, textvariable=self.time_mode_var, values=("hour","day","anchor","launch"), state="readonly", width=12).grid(row=1, column=1, sticky="w", **pad)
        add_row_to(tab_time, 2, "Anchor (HH:MM):", self.time_anchor_var)
        ttk.Checkbutton(tab_time, text="12-hour time (AM/PM)", variable=self.time_12h_var).grid(row=3, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_time, text="Show seconds", variable=self.time_secs_var).grid(row=4, column=0, columnspan=3, sticky="w", **pad)
        add_row_to(tab_time, 5, "Refresh interval:", self.time_refresh_var, "ms")
        ttk.Checkbutton(tab_time, text="Show time until current task due", variable=self.time_show_task_left_var).grid(row=6, column=0, columnspan=3, sticky="w", **pad)

        # Tasks
        ttk.Checkbutton(tab_tasks, text="Enable task encouragement panel", variable=self.encourage_var).grid(row=0, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_tasks, text="Hide 'Wasting time' button", variable=self.hide_waste_var).grid(row=1, column=0, columnspan=3, sticky="w", **pad)
        ttk.Separator(tab_tasks).grid(row=2, column=0, columnspan=3, sticky="ew", padx=8, pady=(4,6))
        ttk.Checkbutton(tab_tasks, text="Require pass/fail decision", variable=self.tasks_decision_enabled_var).grid(row=3, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(tab_tasks, text="Evaluation timing").grid(row=4, column=0, sticky="w", **pad)
        ttk.Combobox(tab_tasks, textvariable=self.tasks_eval_mode_var, values=("before","after"), state="readonly", width=12).grid(row=4, column=1, sticky="w", **pad)
        add_row_to(tab_tasks, 5, "Decision window:", self.tasks_decision_window_var, "minutes")
        ttk.Checkbutton(tab_tasks, text="Pressing 'Studying' counts as fail when decision required", variable=self.tasks_study_implies_fail_var).grid(row=6, column=0, columnspan=3, sticky="w", **pad)
        ttk.Separator(tab_tasks).grid(row=7, column=0, columnspan=3, sticky="ew", padx=8, pady=(4,6))
        ttk.Checkbutton(tab_tasks, text="Show task analytics in prompt", variable=self.show_analytics_var).grid(row=8, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_tasks, text="Treat changed tasks as failures", variable=self.change_as_fail_var).grid(row=9, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(tab_tasks, text="Analytics timescale").grid(row=10, column=0, sticky="w", **pad)
        ttk.Combobox(tab_tasks, textvariable=self.tasks_timescale_var, values=("lifetime","today","7d","30d"), state="readonly", width=12).grid(row=10, column=1, sticky="w", **pad)
        ttk.Separator(tab_tasks).grid(row=11, column=0, columnspan=3, sticky="ew", padx=8, pady=(4,6))
        ttk.Checkbutton(tab_tasks, text="Prompt for details on 'Wasting time'", variable=self.waste_prompt_enabled_var).grid(row=12, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_tasks, text="Ask what you're wasting time on", variable=self.waste_prompt_what_var).grid(row=13, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_tasks, text="Ask for consequences too", variable=self.waste_prompt_cons_var).grid(row=14, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_tasks, text="Prompt for details on 'Studying'", variable=self.focus_prompt_enabled_var).grid(row=15, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_tasks, text="Ask what you're doing", variable=self.focus_prompt_doing_var).grid(row=16, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_tasks, text="Ask what the benefits are", variable=self.focus_prompt_benefits_var).grid(row=17, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_tasks, text="Require answers for every enabled follow-up question", variable=self.require_all_prompt_fields_var).grid(row=18, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_tasks, text="Require an active task to close prompt", variable=self.require_task_var).grid(row=19, column=0, columnspan=3, sticky="w", **pad)

        # Challenges tab
        ttk.Label(tab_challenges, text="Challenge-Based Reflection System", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(tab_challenges, text="Forces genuine reflection through hard validation constraints.", font=("Segoe UI", 8)).grid(row=1, column=0, columnspan=3, sticky="w", **pad)
        ttk.Separator(tab_challenges).grid(row=2, column=0, columnspan=3, sticky="ew", padx=8, pady=(4,6))
        ttk.Checkbutton(tab_challenges, text="Enable challenge system", variable=self.challenge_enabled_var).grid(row=3, column=0, columnspan=3, sticky="w", **pad)
        add_row_to(tab_challenges, 4, "Studying challenge frequency:", self.challenge_studying_freq_var, "0.0-1.0 (0.3 = 30%)")
        add_row_to(tab_challenges, 5, "Wasting challenge frequency:", self.challenge_wasting_freq_var, "0.0-1.0 (0.5 = 50%)")
        add_row_to(tab_challenges, 6, "Minimum words required:", self.challenge_min_words_var, "words")
        add_row_to(tab_challenges, 7, "Minimum response length:", self.challenge_min_length_var, "characters")
        ttk.Checkbutton(tab_challenges, text="Allow skipping challenges (cancel button)", variable=self.challenge_allow_skip_var).grid(row=8, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_challenges, text="Show example hints for challenges", variable=self.challenge_show_hints_var).grid(row=9, column=0, columnspan=3, sticky="w", **pad)
        ttk.Separator(tab_challenges).grid(row=10, column=0, columnspan=3, sticky="ew", padx=8, pady=(8,6))
        ttk.Label(tab_challenges, text="Challenge Types:", font=("Segoe UI", 9, "bold")).grid(row=11, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(tab_challenges, text="Studying: Learning Specificity, Goal Connection, Will Commitment, Output Expectation", font=("Segoe UI", 8)).grid(row=12, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(tab_challenges, text="Wasting: Acknowledgment, Should Gap, Reasoning, Hour Projection, Tomorrow Regret, Fear, Lying", font=("Segoe UI", 8)).grid(row=13, column=0, columnspan=3, sticky="w", **pad)

        # Spam Detection tab
        ttk.Label(tab_spam, text="Spam Detection System", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(tab_spam, text="Validates responses to prevent low-effort spam and gaming.", font=("Segoe UI", 8)).grid(row=1, column=0, columnspan=3, sticky="w", **pad)
        ttk.Separator(tab_spam).grid(row=2, column=0, columnspan=3, sticky="ew", padx=8, pady=(4,6))
        ttk.Checkbutton(tab_spam, text="Enable spam detection", variable=self.spam_enabled_var).grid(row=3, column=0, columnspan=3, sticky="w", **pad)

        ttk.Label(tab_spam, text="Gibberish Detection", font=("Segoe UI", 9, "bold")).grid(row=4, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_spam, text="Enable gibberish detection", variable=self.spam_gibberish_var).grid(row=5, column=0, columnspan=3, sticky="w", **pad)
        add_row_to(tab_spam, 6, "Min vowel ratio:", self.spam_min_vowel_var, "0.0-1.0")
        add_row_to(tab_spam, 7, "Max vowel ratio:", self.spam_max_vowel_var, "0.0-1.0")
        add_row_to(tab_spam, 8, "Min unique char ratio:", self.spam_min_unique_var, "0.0-1.0")

        ttk.Separator(tab_spam).grid(row=9, column=0, columnspan=3, sticky="ew", padx=8, pady=(8,6))
        ttk.Label(tab_spam, text="Repetition Detection", font=("Segoe UI", 9, "bold")).grid(row=10, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_spam, text="Enable repetition check", variable=self.spam_repetition_var).grid(row=11, column=0, columnspan=3, sticky="w", **pad)
        add_row_to(tab_spam, 12, "Max consecutive chars:", self.spam_max_consecutive_var, "count")
        add_row_to(tab_spam, 13, "Max pattern repetition:", self.spam_max_pattern_var, "count")

        ttk.Separator(tab_spam).grid(row=14, column=0, columnspan=3, sticky="ew", padx=8, pady=(8,6))
        ttk.Label(tab_spam, text="Spacing & Keyboard Patterns", font=("Segoe UI", 9, "bold")).grid(row=15, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_spam, text="Enable spacing check", variable=self.spam_spacing_var).grid(row=16, column=0, columnspan=3, sticky="w", **pad)
        add_row_to(tab_spam, 17, "Min length for spaces:", self.spam_min_spaces_var, "characters")
        ttk.Checkbutton(tab_spam, text="Enable keyboard pattern check", variable=self.spam_keyboard_var).grid(row=18, column=0, columnspan=3, sticky="w", **pad)
        add_row_to(tab_spam, 19, "Min keyboard sequence:", self.spam_min_keyboard_var, "characters")

        ttk.Separator(tab_spam).grid(row=20, column=0, columnspan=3, sticky="ew", padx=8, pady=(8,6))
        ttk.Label(tab_spam, text="Dictionary Validation", font=("Segoe UI", 9, "bold")).grid(row=21, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_spam, text="Enable dictionary check", variable=self.spam_dictionary_var).grid(row=22, column=0, columnspan=3, sticky="w", **pad)
        add_row_to(tab_spam, 23, "Min real word ratio:", self.spam_min_word_ratio_var, "0.0-1.0")
        add_row_to(tab_spam, 24, "Min word length:", self.spam_min_word_len_var, "characters")

        ttk.Separator(tab_spam).grid(row=25, column=0, columnspan=3, sticky="ew", padx=8, pady=(8,6))
        ttk.Label(tab_spam, text="Timing Validation", font=("Segoe UI", 9, "bold")).grid(row=26, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(tab_spam, text="Enable timing check", variable=self.spam_timing_var).grid(row=27, column=0, columnspan=3, sticky="w", **pad)
        add_row_to(tab_spam, 28, "Min time to submit:", self.spam_min_time_var, "seconds")
        add_row_to(tab_spam, 29, "Flag if submitted under:", self.spam_flag_time_var, "seconds")

        # Footer buttons
        btns = ttk.Frame(self)
        btns.grid(row=1, column=0, sticky="e", padx=8, pady=(0,8))
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right", padx=6)
        ttk.Button(btns, text="Save", command=self._save).pack(side="right")

        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _safe_int(self, var, default):
        """Safely convert StringVar to int with fallback."""
        try:
            return int((var.get() or str(default)).strip())
        except (ValueError, AttributeError):
            return default

    def _safe_float(self, var, default, min_val=None, max_val=None):
        """Safely convert StringVar to float with fallback and optional clamping."""
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
        # Import save_settings dynamically to avoid circular dependency
        from focuscheck.settings.manager import save_settings

        try:
            s = {
                "interval_seconds": max(10, self._safe_int(self.interval_var, 30)),
                "intensify_after_seconds": max(5, self._safe_int(self.intensify_var, 120)),
                "overdrive_after_seconds": max(20, self._safe_int(self.overdrive_var, 300)),
                "max_intensity_level": min(3, max(1, self._safe_int(self.max_intensity_var, 3))),
                "always_on_top": bool(self.topmost_var.get()),
                "center_on_show": bool(self.center_var.get()),
                "modal_dialog_auto_focus": bool(self.modal_auto_focus_var.get()),

                "anti_habit_enabled": bool(self.anti_var.get()),
                "randomize_buttons": bool(self.rand_btns_var.get()),
                "studying_hold_ms": max(0, self._safe_int(self.hold_ms_var, 600)),

                "force_always_on": bool(self.force_on_var.get()),
                "pause_when_inactive_or_lid_closed": bool(self.pause_var.get()),
                "pause_on_idle": bool(self.pause_on_idle_var.get()),
                "pause_on_lid_closed": bool(self.pause_on_lid_var.get()),
                "pause_on_lock": bool(self.pause_on_lock_var.get()),
                "pause_on_sleep": bool(self.pause_on_sleep_var.get()),
                "inactive_as_sleep_seconds": max(15, self._safe_int(self.idle_secs_var, 300)),
                "pause_poll_interval_seconds": max(2, self._safe_int(self.pause_poll_var, 5)),

                "webhook_url": self.webhook_var.get().strip()
            }
            # Stage 4
            s.update({
                "overdrive_stage4_enabled": bool(self.stage4_enabled_var.get()),
                "overdrive_stage4_after_seconds": max(1, self._safe_int(self.stage4_after_var, 30)),
                "overdrive_stage4_flash_ms": max(20, self._safe_int(self.stage4_rate_var, 100)),
            })
            # Stage 5
            try:
                s5_alpha = float(self.stage5_alpha_var.get())
            except Exception:
                s5_alpha = 0.92
            s5_alpha = max(0.0, min(1.0, s5_alpha))
            s.update({
                "overdrive_stage5_enabled": bool(self.stage5_enabled_var.get()),
                "overdrive_stage5_after_seconds": max(5, self._safe_int(self.stage5_after_var, 60)),
                "overdrive_stage5_dim_pulse": bool(self.stage5_pulse_var.get()),
                "overdrive_stage5_dim_max_alpha": s5_alpha,
                "overdrive_stage5_dim_color": (self.stage5_color_var.get() or "#000000").strip(),
                "overdrive_stage5_click_through": bool(self.stage5_clickthrough_var.get()),
                "overdrive_stage5_hold_after_seconds": max(0, self._safe_int(self.stage5_hold_after_var, 0)),
                "overdrive_stage5_slow_dim_enabled": bool(self.stage5_slow_dim_enabled_var.get()),
                "overdrive_stage5_slow_dim_seconds": max(1, self._safe_int(self.stage5_slow_dim_secs_var, 30)),
                "overdrive_stage5_engine": (self.stage5_engine_var.get() or "overlay").strip().lower() if (self.stage5_engine_var.get() or "overlay").strip().lower() in ("overlay","gamma") else "overlay",
            })
            # Time info
            mode = self.time_mode_var.get().strip().lower()
            if mode not in ("hour","day","anchor","launch"):
                mode = "hour"
            # Sanitize HH:MM
            anc = self.time_anchor_var.get().strip()
            try:
                hh, mm = anc.split(":"); hh = int(hh); mm = int(mm)
                if not (0 <= hh <= 23 and 0 <= mm <= 59):
                    anc = "09:00"
                else:
                    anc = f"{hh:02d}:{mm:02d}"
            except Exception:
                anc = "09:00"
            s.update({
                "show_time_info": bool(self.show_time_info_var.get()),
                "time_info_mode": mode,
                "time_info_anchor_hhmm": anc,
                "time_info_12h": bool(self.time_12h_var.get()),
                "time_info_show_seconds": bool(self.time_secs_var.get()),
                "time_info_refresh_ms": max(250, self._safe_int(self.time_refresh_var, 1000)),
                "time_info_show_task_remaining": bool(self.time_show_task_left_var.get()),
                # New UI / Task settings
                "hide_wasting_button": bool(self.hide_waste_var.get()),
                "wasting_prompt_enabled": bool(self.waste_prompt_enabled_var.get()),
                "wasting_prompt_ask_what": bool(self.waste_prompt_what_var.get()),
                "wasting_prompt_ask_consequences": bool(self.waste_prompt_cons_var.get()),
                "focus_prompt_enabled": bool(self.focus_prompt_enabled_var.get()),
                "focus_prompt_ask_doing": bool(self.focus_prompt_doing_var.get()),
                "focus_prompt_ask_benefits": bool(self.focus_prompt_benefits_var.get()),
                "prompt_require_all_fields": bool(self.require_all_prompt_fields_var.get()),
                "require_active_task": bool(self.require_task_var.get()),
                "encouragement_enabled": bool(self.encourage_var.get()),
                "show_task_analytics": bool(self.show_analytics_var.get()),
                "tasks_change_counts_as_fail": bool(self.change_as_fail_var.get()),
                "tasks_analytics_timescale": str(self.tasks_timescale_var.get()).strip().lower(),
                "tasks_decision_prompt_enabled": bool(self.tasks_decision_enabled_var.get()),
                "tasks_study_implies_fail_on_decision": bool(self.tasks_study_implies_fail_var.get()),
                "tasks_evaluation_mode": str(self.tasks_eval_mode_var.get()).strip().lower(),
                "tasks_decision_window_minutes": max(0, self._safe_int(self.tasks_decision_window_var, 10)),
                # Alert / jiggle
                "disable_jiggling": bool(self.disable_jiggle_var.get()),
                "enable_intensity_pulse": bool(self.intensity_pulse_var.get()),
                "enable_intensity_shake": bool(self.intensity_shake_var.get()),
                "enable_intensity_arrows": bool(self.intensity_arrows_var.get()),
                "shake_lock_position": bool(self.shake_lock_var.get()),
                "enable_overdrive_flash_background": bool(self.od_flash_bg_var.get()),
                "enable_overdrive_shake_loop": bool(self.od_shake_loop_var.get()),
                "enable_overdrive_jiggle_buttons": bool(self.od_jiggle_btns_var.get()),
                "jiggle_style": str(self.jiggle_style_var.get()).strip().lower(),
                # Tray/general
                "follow_cursor_monitor": bool(self.follow_cursor_var.get()),
                "tray_start_stop_enabled": bool(self.tray_start_stop_enabled_var.get()),
                "tray_settings_button_enabled": bool(self.tray_settings_enabled_var.get()),
                "tray_exit_button_enabled": bool(self.tray_exit_enabled_var.get()),
                # Challenge system
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
            })
        except ValueError:
            messagebox.showerror("Invalid values", "Please enter whole numbers only.")
            return
        save_settings(s)
        self.on_save(s)
        self.destroy()


class TaskHistoryWindow(tk.Toplevel):
    """Popup window showing recent task history in a table."""

    def __init__(self, master, taskdb, limit=200):
        super().__init__(master)
        self.title("Task History")
        self.configure(bg="#111")
        self.resizable(True, True)
        self.taskdb = taskdb
        try:
            self.geometry("820x420")
        except Exception:
            pass

        # Import log_exception dynamically
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

        # Populate
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

        # Footer
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


__all__ = ['SettingsWindow', 'TaskHistoryWindow']

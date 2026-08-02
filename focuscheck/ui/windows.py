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
from .camera_test_window import CameraTestWindow
from .schema_controls import SchemaSettingsBinding
from .settings_tabs import (
    GeneralTabMixin,
    ValidationTabMixin,
    WebsiteFlagsTabMixin,
    ChallengesTabMixin,
    SpamTabMixin,
    AlertsTabMixin,
    BehaviorTabMixin
)


class AdvancedSettingsWindow(
    GeneralTabMixin,
    ValidationTabMixin,
    WebsiteFlagsTabMixin,
    ChallengesTabMixin,
    SpamTabMixin,
    AlertsTabMixin,
    BehaviorTabMixin,
    tk.Toplevel
):
    """
    Modern settings window with advanced visual controls.

    Inherits tab creation methods from multiple mixins:
    - GeneralTabMixin: Core settings, timing, window behavior
    - ValidationTabMixin: Challenge system and spam detection
    - ChallengesTabMixin: Individual challenge configuration
    - SpamTabMixin: Spam detection settings
    - AlertsTabMixin: Overdrive stages, audio alerts, visual effects
    - BehaviorTabMixin: Prompts, time info, tasks, camera settings
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
        self.resizable(True, True)  # Explicitly enable resizing
        self.settings = settings.copy()
        self.on_save = on_save

        self._init_vars()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Escape>", lambda _e: self._cancel())

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
        self.specific_monitor_only_var = tk.BooleanVar(value=s.get("specific_monitor_only", False))
        self.specific_monitor_index_var = tk.StringVar(value=str(s.get("specific_monitor_index", 0)))
        self.webhook_var = tk.StringVar(value=s.get("webhook_url", ""))
        self.monitoring_mode_var = tk.StringVar(value=s.get("monitoring_mode", "v1"))

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
        self.challenge_min_words_var = tk.StringVar(value=str(s.get("challenge_min_words", 3)))
        self.challenge_min_length_var = tk.StringVar(value=str(s.get("challenge_min_total_length", 10)))
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
        self.spam_min_vowel_var = tk.DoubleVar(value=s.get("spam_min_vowel_ratio", 0.15))
        self.spam_max_vowel_var = tk.DoubleVar(value=s.get("spam_max_vowel_ratio", 0.75))
        self.spam_min_unique_var = tk.DoubleVar(value=s.get("spam_min_unique_char_ratio", 0.3))
        self.spam_repetition_var = tk.BooleanVar(value=s.get("spam_repetition_check", True))
        self.spam_max_consecutive_var = tk.StringVar(value=str(s.get("spam_max_consecutive_chars", 3)))
        self.spam_max_pattern_var = tk.StringVar(value=str(s.get("spam_max_pattern_repetition", 4)))
        self.spam_spacing_var = tk.BooleanVar(value=s.get("spam_spacing_check", True))
        self.spam_min_spaces_var = tk.StringVar(value=str(s.get("spam_min_length_require_spaces", 20)))
        self.spam_keyboard_var = tk.BooleanVar(value=s.get("spam_keyboard_pattern_check", True))
        self.spam_min_keyboard_var = tk.StringVar(value=str(s.get("spam_min_keyboard_sequence_length", 5)))
        self.spam_dictionary_var = tk.BooleanVar(value=s.get("spam_dictionary_check", True))
        self.spam_min_word_ratio_var = tk.DoubleVar(value=s.get("spam_min_real_word_ratio", 0.5))
        self.spam_min_word_len_var = tk.StringVar(value=str(s.get("spam_min_word_length", 2)))
        self.spam_timing_var = tk.BooleanVar(value=s.get("spam_timing_check", True))
        self.spam_min_time_var = tk.StringVar(value=str(s.get("spam_min_time_to_submit", 2)))
        self.spam_flag_time_var = tk.StringVar(value=str(s.get("spam_flag_if_under", 1)))
        self.v2_force_all_validations_var = tk.BooleanVar(value=s.get("v2_force_all_validations", True))
        self.v2_question_use_window_title_var = tk.BooleanVar(value=s.get("v2_question_use_window_title", True))
        self.v2_focus_requires_enter_var = tk.BooleanVar(value=s.get("v2_focus_requires_enter", False))
        self.v2_hide_prompt_during_intervention_var = tk.BooleanVar(value=s.get("v2_hide_prompt_during_intervention", True))

        # UI
        self.ui_scale_percent_var = tk.StringVar(value=str(s.get("ui_scale_percent", 100)))
        self.popup_layout_mode_var = tk.StringVar(value=s.get("popup_layout_mode", "vertical"))
        self.waste_ask_what_var = tk.BooleanVar(value=s.get("wasting_prompt_ask_what", True))
        self.waste_ask_cons_var = tk.BooleanVar(value=s.get("wasting_prompt_ask_consequences", True))
        self.waste_validation_var = tk.BooleanVar(value=s.get("wasting_prompt_validation_enabled", True))
        self.focus_ask_doing_var = tk.BooleanVar(value=s.get("focus_prompt_ask_doing", True))
        self.focus_ask_benefits_var = tk.BooleanVar(value=s.get("focus_prompt_ask_benefits", True))
        self.require_all_prompt_fields_var = tk.BooleanVar(value=s.get("prompt_require_all_fields", False))
        self.require_task_var = tk.BooleanVar(value=s.get("require_active_task", False))
        self.hide_waste_var = tk.BooleanVar(value=s.get("hide_wasting_button", False))

        # Phrase Acronym Challenge / button labels
        self.phrase_acronym_enabled_var = tk.BooleanVar(value=s.get("phrase_acronym_enabled", False))
        self.custom_button_phrases_var = tk.BooleanVar(value=s.get("custom_button_phrases_enabled", False))
        self.study_phrase_mode_var = tk.StringVar(value=s.get("study_phrase_mode", "random"))
        self.waste_phrase_mode_var = tk.StringVar(value=s.get("waste_phrase_mode", "random"))
        self.study_phrase_override_var = tk.StringVar(value=s.get("study_phrase_override", ""))
        self.waste_phrase_override_var = tk.StringVar(value=s.get("waste_phrase_override", ""))
        # Store phrase lists (will be updated via editor dialog)
        self.study_phrase_list = list(s.get("study_phrase_list", []))
        self.waste_phrase_list = list(s.get("waste_phrase_list", []))
        self.encourage_var = tk.BooleanVar(value=s.get("encouragement_enabled", True))
        self.show_analytics_var = tk.BooleanVar(value=s.get("show_task_analytics", True))

        # Tray
        self.tray_start_stop_enabled_var = tk.BooleanVar(value=s.get("tray_start_stop_enabled", True))
        self.tray_settings_enabled_var = tk.BooleanVar(value=s.get("tray_settings_button_enabled", True))
        self.tray_exit_enabled_var = tk.BooleanVar(value=s.get("tray_exit_button_enabled", True))

        # Website flags
        self.website_flags_list = list(s.get("website_flags", []))

        # Overdrive Stage 4
        self.overdrive_stage4_enabled_var = tk.BooleanVar(value=s.get("overdrive_stage4_enabled", True))
        self.overdrive_stage4_after_var = tk.StringVar(value=str(s.get("overdrive_stage4_after_seconds", 12)))
        self.overdrive_stage4_flash_var = tk.StringVar(value=str(s.get("overdrive_stage4_flash_ms", 60)))

        # Overdrive Stage 5 (Dimming)
        self.overdrive_stage5_enabled_var = tk.BooleanVar(value=s.get("overdrive_stage5_enabled", True))
        self.overdrive_stage5_after_var = tk.StringVar(value=str(s.get("overdrive_stage5_after_seconds", 60)))
        self.overdrive_stage5_click_through_var = tk.BooleanVar(value=s.get("overdrive_stage5_click_through", True))
        self.overdrive_stage5_dim_pulse_var = tk.BooleanVar(value=s.get("overdrive_stage5_dim_pulse", True))
        self.overdrive_stage5_dim_max_alpha_var = tk.DoubleVar(value=s.get("overdrive_stage5_dim_max_alpha", 0.92))
        self.overdrive_stage5_dim_color_var = tk.StringVar(value=s.get("overdrive_stage5_dim_color", "#000000"))
        self.overdrive_stage5_engine_var = tk.StringVar(value=s.get("overdrive_stage5_engine", "overlay"))
        self.overdrive_stage5_hold_after_var = tk.StringVar(value=str(s.get("overdrive_stage5_hold_after_seconds", 0)))
        self.overdrive_stage5_slow_dim_enabled_var = tk.BooleanVar(value=s.get("overdrive_stage5_slow_dim_enabled", False))
        self.overdrive_stage5_slow_dim_seconds_var = tk.StringVar(value=str(s.get("overdrive_stage5_slow_dim_seconds", 30)))

        # Time Info Display
        self.show_time_info_var = tk.BooleanVar(value=s.get("show_time_info", False))
        self.time_info_mode_var = tk.StringVar(value=s.get("time_info_mode", "hour"))
        self.time_info_anchor_var = tk.StringVar(value=s.get("time_info_anchor_hhmm", "09:00"))
        self.time_info_12h_var = tk.BooleanVar(value=s.get("time_info_12h", False))
        self.time_info_show_seconds_var = tk.BooleanVar(value=s.get("time_info_show_seconds", False))
        self.time_info_refresh_var = tk.StringVar(value=str(s.get("time_info_refresh_ms", 1000)))
        self.time_info_show_task_remaining_var = tk.BooleanVar(value=s.get("time_info_show_task_remaining", False))

        # Task Analytics & Decisions
        self.tasks_analytics_timescale_var = tk.StringVar(value=s.get("tasks_analytics_timescale", "lifetime"))
        self.tasks_change_counts_as_fail_var = tk.BooleanVar(value=s.get("tasks_change_counts_as_fail", True))
        self.tasks_decision_prompt_enabled_var = tk.BooleanVar(value=s.get("tasks_decision_prompt_enabled", True))
        self.tasks_study_implies_fail_var = tk.BooleanVar(value=s.get("tasks_study_implies_fail_on_decision", True))
        self.tasks_evaluation_mode_var = tk.StringVar(value=s.get("tasks_evaluation_mode", "before"))
        self.tasks_decision_window_var = tk.StringVar(value=str(s.get("tasks_decision_window_minutes", 10)))

        # Jiggle & Animation Effects
        self.jiggle_style_var = tk.StringVar(value=s.get("jiggle_style", "nudge"))
        self.disable_jiggling_var = tk.BooleanVar(value=s.get("disable_jiggling", False))
        self.enable_intensity_pulse_var = tk.BooleanVar(value=s.get("enable_intensity_pulse", True))
        self.enable_intensity_shake_var = tk.BooleanVar(value=s.get("enable_intensity_shake", True))
        self.shake_lock_position_var = tk.BooleanVar(value=s.get("shake_lock_position", True))
        self.enable_overdrive_flash_background_var = tk.BooleanVar(value=s.get("enable_overdrive_flash_background", True))
        self.enable_overdrive_shake_loop_var = tk.BooleanVar(value=s.get("enable_overdrive_shake_loop", True))
        self.enable_overdrive_jiggle_buttons_var = tk.BooleanVar(value=s.get("enable_overdrive_jiggle_buttons", True))

        # Audio Alerts
        self.audio_alerts_enabled_var = tk.BooleanVar(value=s.get("audio_alerts_enabled", False))
        self.audio_alarm_duration_var = tk.StringVar(value=str(s.get("audio_alarm_duration_seconds", 5)))
        self.audio_alarm_pattern_var = tk.StringVar(value=s.get("audio_alarm_pattern", "rapid_beeps"))
        self.audio_alarm_mode_var = tk.StringVar(value=s.get("audio_alarm_mode", "once"))
        self.audio_alarm_trigger_var = tk.StringVar(value=s.get("audio_alarm_trigger", "overdrive"))
        self.audio_earphone_safe_mode_var = tk.BooleanVar(value=s.get("audio_earphone_safe_mode", True))
        self.audio_max_volume_var = tk.DoubleVar(value=s.get("audio_max_volume", 0.7))
        self.audio_try_speaker_switch_var = tk.BooleanVar(value=s.get("audio_try_speaker_switch", False))
        self.audio_speaker_switch_after_var = tk.StringVar(value=str(s.get("audio_speaker_switch_after_seconds", 30)))

        # Snooze Reminder
        self.snooze_reminder_enabled_var = tk.BooleanVar(value=s.get("snooze_reminder_enabled", True))
        self.snooze_reminder_interval_var = tk.StringVar(value=str(s.get("snooze_reminder_interval_seconds", 300)))

        # Snooze confirmation prompt
        self.snooze_prompt_enabled_var = tk.BooleanVar(value=s.get("snooze_prompt_enabled", True))
        self.snooze_prompt_validation_var = tk.BooleanVar(value=s.get("snooze_prompt_validation_enabled", True))
        self.snooze_prevent_paste_var = tk.BooleanVar(value=s.get("snooze_exact_prevent_paste", True))
        self.snooze_case_sensitive_var = tk.BooleanVar(value=s.get("snooze_sentence_case_sensitive", True))
        self.snooze_sentence_list = list(s.get("snooze_prompt_sentences", []))
        self.snooze_require_phrase_var = tk.BooleanVar(value=s.get("snooze_exact_require_phrase", False))
        self.snooze_required_phrase_var = tk.StringVar(value=s.get("snooze_exact_required_phrase", "I am snoozing"))

        # Validation alignment (Validation tab)
        self.snooze_force_all_heuristics_var = tk.BooleanVar(value=s.get("snooze_exact_force_all_heuristics", False))

        # Camera Feed
        self.camera_feed_enabled_var = tk.BooleanVar(value=s.get("camera_feed_enabled", False))
        self.camera_feed_mode_var = tk.StringVar(value=s.get("camera_feed_mode", "live"))
        self.camera_capture_on_click_var = tk.BooleanVar(value=s.get("camera_capture_on_click", False))
        self.camera_device_index_var = tk.StringVar(value=str(s.get("camera_device_index", 0)))
        self.camera_fps_var = tk.StringVar(value=str(s.get("camera_fps", 30)))

        # Camera sizing mode
        self.camera_sizing_mode_var = tk.StringVar(value=s.get("camera_sizing_mode", "aspect_ratio"))

        # Fixed size settings
        self.camera_feed_width_var = tk.StringVar(value=str(s.get("camera_feed_width", 320)))
        self.camera_feed_height_var = tk.StringVar(value=str(s.get("camera_feed_height", 240)))

        # Face tracking settings
        self.camera_face_max_width_var = tk.StringVar(value=str(s.get("camera_face_max_width", 400)))
        self.camera_face_max_height_var = tk.StringVar(value=str(s.get("camera_face_max_height", 300)))
        self.camera_face_zoom_factor_var = tk.DoubleVar(value=s.get("camera_face_zoom_factor", 1.5))
        self.camera_face_maximize_in_display_var = tk.BooleanVar(value=s.get("camera_face_maximize_in_display", True))
        self.camera_face_fallback_mode_var = tk.StringVar(value=s.get("camera_face_fallback_mode", "aspect_ratio"))

        # Face centering fine-tuning
        self.camera_face_center_vertical_bias_var = tk.DoubleVar(value=s.get("camera_face_center_vertical_bias", 0.65))
        self.camera_face_crop_width_multiplier_var = tk.DoubleVar(value=s.get("camera_face_crop_width_multiplier", 1.4))
        self.camera_face_crop_height_multiplier_var = tk.DoubleVar(value=s.get("camera_face_crop_height_multiplier", 1.6))

        # Edge-aware zoom
        self.camera_face_edge_aware_zoom_var = tk.BooleanVar(value=s.get("camera_face_edge_aware_zoom", True))
        self.camera_face_edge_threshold_var = tk.DoubleVar(value=s.get("camera_face_edge_threshold", 0.15))
        self.camera_face_edge_zoom_multiplier_var = tk.DoubleVar(value=s.get("camera_face_edge_zoom_multiplier", 1.3))

        # Face detection method
        self.camera_face_detection_method_var = tk.StringVar(value=s.get("camera_face_detection_method", "haar"))
        self.camera_face_detection_interval_var = tk.StringVar(value=str(s.get("camera_face_detection_interval", 10)))

        # Camera flip
        self.camera_flip_horizontal_var = tk.BooleanVar(value=s.get("camera_flip_horizontal", True))

        # Camera visual effects
        self.camera_show_face_detection_var = tk.BooleanVar(value=s.get("camera_show_face_detection", False))
        self.camera_invert_colors_var = tk.BooleanVar(value=s.get("camera_invert_colors", False))

        # Adaptive brightness
        self.camera_adaptive_brightness_enabled_var = tk.BooleanVar(value=s.get("camera_adaptive_brightness_enabled", False))
        self.camera_adaptive_brightness_overexposed_var = tk.BooleanVar(value=s.get("camera_adaptive_brightness_overexposed", False))
        self.camera_adaptive_brightness_dim_var = tk.BooleanVar(value=s.get("camera_adaptive_brightness_dim", False))
        self.camera_adaptive_brightness_intensity_var = tk.DoubleVar(value=s.get("camera_adaptive_brightness_intensity", 0.5))

        # Biodata Display
        self.biodata_enabled_var = tk.BooleanVar(value=s.get("biodata_enabled", False))
        self.biodata_title_var = tk.StringVar(value=s.get("biodata_title", "Mr"))
        self.biodata_first_name_var = tk.StringVar(value=s.get("biodata_first_name", ""))
        self.biodata_last_name_var = tk.StringVar(value=s.get("biodata_last_name", ""))
        self.biodata_show_full_name_var = tk.BooleanVar(value=s.get("biodata_show_full_name", True))
        self.biodata_birthdate_var = tk.StringVar(value=s.get("biodata_birthdate", "2005-01-01"))
        self.biodata_age_format_var = tk.StringVar(value=s.get("biodata_age_format", "simple"))
        self.biodata_show_days_lived_var = tk.BooleanVar(value=s.get("biodata_show_days_lived", False))
        self.biodata_show_lineage_var = tk.BooleanVar(value=s.get("biodata_show_lineage", False))
        self.biodata_lineage_text_var = tk.StringVar(value=s.get("biodata_lineage_text", "Heir of the Singh family"))
        self.biodata_show_role_var = tk.BooleanVar(value=s.get("biodata_show_role", False))
        self.biodata_role_text_var = tk.StringVar(value=s.get("biodata_role_text", "Student"))
        self.biodata_custom_text_var = tk.StringVar(value=s.get("biodata_custom_text", ""))

        # Biodata visual style
        self.biodata_style_var = tk.StringVar(value=s.get("biodata_style", "dramatic"))
        self.biodata_pulse_animation_var = tk.BooleanVar(value=s.get("biodata_pulse_animation", True))
        self.biodata_font_size_var = tk.IntVar(value=s.get("biodata_font_size", 14))

        # The remaining editable schema keys are rendered by the generated
        # Advanced tab rather than silently disappearing from the UI.
        self._schema_settings = SchemaSettingsBinding(self.settings)
        self.webhook_var = self._schema_settings.variables["webhook_url"]

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
        self._create_validation_tab()
        self._create_website_flags_tab()
        self._create_challenges_tab()
        self._create_spam_tab()
        self._create_alerts_tab()
        self._create_behavior_tab()
        self._create_schema_settings_tab()

        # Button bar
        self._create_button_bar(main_container)

    def _create_schema_settings_tab(self):
        """Create controls generated from the canonical settings schema."""
        tab = self._create_scrollable_tab(self.notebook, "Advanced")
        self._schema_settings.build(tab)

    def _create_scrollable_tab(self, parent, tab_name):
        """Create scrollable tab."""
        outer = ttk.Frame(parent)
        parent.add(outer, text=tab_name)

        # Configure outer frame to expand properly
        outer.grid_rowconfigure(0, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        # Canvas for scrolling
        canvas = tk.Canvas(outer, highlightthickness=0, bg='white')
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        scrollable = ttk.Frame(canvas)

        # Update scroll region when content changes
        def _configure_scroll_region(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        scrollable.bind("<Configure>", _configure_scroll_region)

        # Create window in canvas and store reference
        window_id = canvas.create_window((0, 0), window=scrollable, anchor="nw")

        # Update canvas window width when canvas size changes
        def _configure_canvas_width(event):
            canvas.itemconfig(window_id, width=event.width)

        canvas.bind("<Configure>", _configure_canvas_width)
        canvas.configure(yscrollcommand=scrollbar.set)

        # Mousewheel scrolling - bind to canvas and its children
        def _on_mousewheel(event):
            # Prevent scrolling beyond bounds
            scroll_amount = int(-1*(event.delta/120))
            # Get current scroll position
            current_pos = canvas.yview()

            # Only scroll if not at the bounds
            if scroll_amount < 0 and current_pos[0] <= 0:
                # At top, trying to scroll up - don't allow
                return "break"
            elif scroll_amount > 0 and current_pos[1] >= 1.0:
                # At bottom, trying to scroll down - don't allow
                return "break"

            canvas.yview_scroll(scroll_amount, "units")
            return "break"

        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")

        # Only bind mousewheel when mouse is over this tab
        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)

        # Grid layout for proper resizing
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

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

    def _create_button_bar(self, parent):
        """Create button bar."""
        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=1, column=0, sticky="e")

        ttk.Button(btn_frame, text="Cancel", command=self._cancel, width=12).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Save", command=self._save, width=12).pack(side="right")

    def _cancel(self):
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

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

    def _test_audio_pattern(self):
        """Test the currently selected audio pattern."""
        try:
            from focuscheck.utils.audio import get_audio_alarm

            # Get current settings
            pattern = self.audio_alarm_pattern_var.get()
            mode = self.audio_alarm_mode_var.get()
            safe_mode = self.audio_earphone_safe_mode_var.get()
            max_volume = self.audio_max_volume_var.get()
            duration = self._safe_int(self.audio_alarm_duration_var, 5)

            # Get audio alarm instance
            alarm = get_audio_alarm()

            # Stop any currently playing audio
            alarm.stop()

            # For testing, use "once" mode if continuous is selected
            # Otherwise use the selected mode
            test_mode = "once" if mode == "continuous" else mode

            # Play the pattern
            alarm.play_pattern(
                pattern=pattern,
                duration_seconds=duration,
                mode=test_mode,
                safe_mode=safe_mode,
                max_volume=max_volume
            )

        except Exception as e:
            messagebox.showwarning("Audio Test", f"Audio test failed: {e}\n\nMake sure audio is available on your system.")

    def _on_audio_mode_changed(self, *args):
        """Handle audio mode changes to grey out duration when continuous is selected."""
        try:
            mode = self.audio_alarm_mode_var.get()
            is_continuous = (mode == "continuous")

            # Disable/enable the duration widget based on mode
            if hasattr(self, 'audio_duration_widget'):
                # The SpinboxWithButtons widget contains child widgets
                # We need to disable the spinbox and buttons
                state = 'disabled' if is_continuous else 'normal'

                def disable_recursive(widget):
                    """Recursively disable all interactive widgets."""
                    try:
                        # Try to configure state for this widget
                        if hasattr(widget, 'configure'):
                            widget.configure(state=state)
                    except tk.TclError:
                        pass  # Some widgets don't support state

                    # Recurse into children
                    for child in widget.winfo_children():
                        disable_recursive(child)

                disable_recursive(self.audio_duration_widget)

                # Update label color to show it's disabled
                if hasattr(self, 'audio_duration_label'):
                    if is_continuous:
                        self.audio_duration_label.configure(foreground="darkgray")
                    else:
                        self.audio_duration_label.configure(foreground="gray")
        except Exception:
            pass  # Ignore errors during UI updates

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
            # Patch the loaded revision draft instead of rebuilding a partial
            # document. This preserves state-only, plugin, and future keys.
            s = dict(self.settings)
            s.update({
                "settings_revision": int(self.settings.get("settings_revision", 0)),
                # Core
                "interval_seconds": max(10, self._safe_int(self.interval_var, 60)),
                "intensify_after_seconds": max(5, self._safe_int(self.intensify_var, 15)),
                "overdrive_after_seconds": max(20, self._safe_int(self.overdrive_var, 60)),
                "max_intensity_level": min(3, max(1, self._safe_int(self.max_intensity_var, 3))),
                "always_on_top": bool(self.topmost_var.get()),
                "center_on_show": bool(self.center_var.get()),
                "modal_dialog_auto_focus": bool(self.modal_auto_focus_var.get()),
                "follow_cursor_monitor": bool(self.follow_cursor_var.get()),
                "specific_monitor_only": bool(self.specific_monitor_only_var.get()),
                "specific_monitor_index": max(0, min(10, self._safe_int(self.specific_monitor_index_var, 0))),
                "monitoring_mode": str(self.monitoring_mode_var.get()).strip().lower(),

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
                "v2_force_all_validations": bool(self.v2_force_all_validations_var.get()),
                "v2_question_use_window_title": bool(self.v2_question_use_window_title_var.get()),
                "v2_focus_requires_enter": bool(self.v2_focus_requires_enter_var.get()),
                "v2_hide_prompt_during_intervention": bool(self.v2_hide_prompt_during_intervention_var.get()),

                # UI
                "ui_scale_percent": max(50, min(150, self._safe_int(self.ui_scale_percent_var, 100))),
                "popup_layout_mode": str(self.popup_layout_mode_var.get()).strip().lower(),
                "wasting_prompt_ask_what": bool(self.waste_ask_what_var.get()),
                "wasting_prompt_ask_consequences": bool(self.waste_ask_cons_var.get()),
                "wasting_prompt_validation_enabled": bool(self.waste_validation_var.get()),
                "focus_prompt_ask_doing": bool(self.focus_ask_doing_var.get()),
                "focus_prompt_ask_benefits": bool(self.focus_ask_benefits_var.get()),
                "prompt_require_all_fields": bool(self.require_all_prompt_fields_var.get()),
                "require_active_task": bool(self.require_task_var.get()),
                "hide_wasting_button": bool(self.hide_waste_var.get()),
                "encouragement_enabled": bool(self.encourage_var.get()),
                "show_task_analytics": bool(self.show_analytics_var.get()),

                # Phrase Acronym Challenge
                "phrase_acronym_enabled": bool(self.phrase_acronym_enabled_var.get()),
                "custom_button_phrases_enabled": bool(self.custom_button_phrases_var.get()),
                "study_phrase_list": list(self.study_phrase_list),
                "study_phrase_mode": str(self.study_phrase_mode_var.get()),
                "study_phrase_override": str(self.study_phrase_override_var.get()),
                "waste_phrase_list": list(self.waste_phrase_list),
                "waste_phrase_mode": str(self.waste_phrase_mode_var.get()),
                "waste_phrase_override": str(self.waste_phrase_override_var.get()),

                # Tray
                "tray_start_stop_enabled": bool(self.tray_start_stop_enabled_var.get()),
                "tray_settings_button_enabled": bool(self.tray_settings_enabled_var.get()),
                "tray_exit_button_enabled": bool(self.tray_exit_enabled_var.get()),

                # Website flags
                "website_flags": list(self.website_flags_list),

                # Overdrive Stage 4
                "overdrive_stage4_enabled": bool(self.overdrive_stage4_enabled_var.get()),
                "overdrive_stage4_after_seconds": max(1, self._safe_int(self.overdrive_stage4_after_var, 12)),
                "overdrive_stage4_flash_ms": max(20, self._safe_int(self.overdrive_stage4_flash_var, 60)),

                # Overdrive Stage 5 (Dimming)
                "overdrive_stage5_enabled": bool(self.overdrive_stage5_enabled_var.get()),
                "overdrive_stage5_after_seconds": max(5, self._safe_int(self.overdrive_stage5_after_var, 60)),
                "overdrive_stage5_click_through": bool(self.overdrive_stage5_click_through_var.get()),
                "overdrive_stage5_dim_pulse": bool(self.overdrive_stage5_dim_pulse_var.get()),
                "overdrive_stage5_dim_max_alpha": self._safe_float(self.overdrive_stage5_dim_max_alpha_var, 0.92, 0.0, 1.0),
                "overdrive_stage5_dim_color": self.overdrive_stage5_dim_color_var.get().strip(),
                "overdrive_stage5_engine": str(self.overdrive_stage5_engine_var.get()).strip().lower(),
                "overdrive_stage5_hold_after_seconds": max(0, self._safe_int(self.overdrive_stage5_hold_after_var, 0)),
                "overdrive_stage5_slow_dim_enabled": bool(self.overdrive_stage5_slow_dim_enabled_var.get()),
                "overdrive_stage5_slow_dim_seconds": max(1, self._safe_int(self.overdrive_stage5_slow_dim_seconds_var, 30)),

                # Time Info Display
                "show_time_info": bool(self.show_time_info_var.get()),
                "time_info_mode": str(self.time_info_mode_var.get()).strip().lower(),
                "time_info_anchor_hhmm": str(self.time_info_anchor_var.get()).strip(),
                "time_info_12h": bool(self.time_info_12h_var.get()),
                "time_info_show_seconds": bool(self.time_info_show_seconds_var.get()),
                "time_info_refresh_ms": max(250, self._safe_int(self.time_info_refresh_var, 1000)),
                "time_info_show_task_remaining": bool(self.time_info_show_task_remaining_var.get()),

                # Task Analytics & Decisions
                "tasks_analytics_timescale": str(self.tasks_analytics_timescale_var.get()).strip().lower(),
                "tasks_change_counts_as_fail": bool(self.tasks_change_counts_as_fail_var.get()),
                "tasks_decision_prompt_enabled": bool(self.tasks_decision_prompt_enabled_var.get()),
                "tasks_study_implies_fail_on_decision": bool(self.tasks_study_implies_fail_var.get()),
                "tasks_evaluation_mode": str(self.tasks_evaluation_mode_var.get()).strip().lower(),
                "tasks_decision_window_minutes": max(0, self._safe_int(self.tasks_decision_window_var, 10)),

                # Jiggle & Animation Effects
                "jiggle_style": str(self.jiggle_style_var.get()).strip().lower(),
                "disable_jiggling": bool(self.disable_jiggling_var.get()),
                "enable_intensity_pulse": bool(self.enable_intensity_pulse_var.get()),
                "enable_intensity_shake": bool(self.enable_intensity_shake_var.get()),
                "shake_lock_position": bool(self.shake_lock_position_var.get()),
                "enable_overdrive_flash_background": bool(self.enable_overdrive_flash_background_var.get()),
                "enable_overdrive_shake_loop": bool(self.enable_overdrive_shake_loop_var.get()),
                "enable_overdrive_jiggle_buttons": bool(self.enable_overdrive_jiggle_buttons_var.get()),

                # Audio Alerts
                "audio_alerts_enabled": bool(self.audio_alerts_enabled_var.get()),
                "audio_alarm_duration_seconds": max(1, self._safe_int(self.audio_alarm_duration_var, 5)),
                "audio_alarm_pattern": str(self.audio_alarm_pattern_var.get()).strip().lower(),
                "audio_alarm_mode": str(self.audio_alarm_mode_var.get()).strip().lower(),
                "audio_alarm_trigger": str(self.audio_alarm_trigger_var.get()).strip().lower(),
                "audio_earphone_safe_mode": bool(self.audio_earphone_safe_mode_var.get()),
                "audio_max_volume": self._safe_float(self.audio_max_volume_var, 0.7, 0.0, 1.0),
                "audio_try_speaker_switch": bool(self.audio_try_speaker_switch_var.get()),
                "audio_speaker_switch_after_seconds": max(10, self._safe_int(self.audio_speaker_switch_after_var, 30)),

                # Snooze Reminder
                "snooze_reminder_enabled": bool(self.snooze_reminder_enabled_var.get()),
                "snooze_reminder_interval_seconds": max(60, self._safe_int(self.snooze_reminder_interval_var, 300)),

                # Snooze Confirmation
                "snooze_prompt_enabled": bool(self.snooze_prompt_enabled_var.get()),
                "snooze_prompt_ask_reason": bool(self.settings.get("snooze_prompt_ask_reason", True)),
                "snooze_prompt_validation_enabled": bool(self.snooze_prompt_validation_var.get()),
                "snooze_prompt_exact_enabled": bool(self.settings.get("snooze_prompt_exact_enabled", True)),
                "snooze_exact_prevent_paste": bool(self.snooze_prevent_paste_var.get()),
                "snooze_sentence_case_sensitive": bool(self.snooze_case_sensitive_var.get()),
                "snooze_prompt_sentences": list(self.snooze_sentence_list),
                "snooze_exact_require_phrase": bool(self.snooze_require_phrase_var.get()),
                "snooze_exact_required_phrase": str(self.snooze_required_phrase_var.get()).strip(),
                # Validation alignment
                "snooze_exact_force_all_heuristics": bool(self.snooze_force_all_heuristics_var.get()),

                # Camera Feed
                "camera_feed_enabled": bool(self.camera_feed_enabled_var.get()),
                "camera_feed_mode": str(self.camera_feed_mode_var.get()).strip().lower(),
                "camera_capture_on_click": bool(self.camera_capture_on_click_var.get()),
                "camera_flip_horizontal": bool(self.camera_flip_horizontal_var.get()),
                "camera_device_index": max(0, self._safe_int(self.camera_device_index_var, 0)),
                "camera_fps": min(60, max(1, self._safe_int(self.camera_fps_var, 30))),

                # Camera sizing mode
                "camera_sizing_mode": str(self.camera_sizing_mode_var.get()).strip().lower(),

                # Fixed size settings (also used as max dimensions in aspect_ratio mode)
                "camera_feed_width": min(1920, max(160, self._safe_int(self.camera_feed_width_var, 320))),
                "camera_feed_height": min(1080, max(120, self._safe_int(self.camera_feed_height_var, 240))),

                # Face tracking settings
                "camera_face_max_width": min(1920, max(160, self._safe_int(self.camera_face_max_width_var, 400))),
                "camera_face_max_height": min(1080, max(120, self._safe_int(self.camera_face_max_height_var, 300))),
                "camera_face_zoom_factor": self._safe_float(self.camera_face_zoom_factor_var, 1.5, 1.0, 3.0),
                "camera_face_maximize_in_display": bool(self.camera_face_maximize_in_display_var.get()),
                "camera_face_fallback_mode": str(self.camera_face_fallback_mode_var.get()).strip().lower(),

                # Face centering fine-tuning
                "camera_face_center_vertical_bias": self._safe_float(self.camera_face_center_vertical_bias_var, 0.65, 0.5, 1.0),
                "camera_face_crop_width_multiplier": self._safe_float(self.camera_face_crop_width_multiplier_var, 1.4, 1.0, 2.5),
                "camera_face_crop_height_multiplier": self._safe_float(self.camera_face_crop_height_multiplier_var, 1.6, 1.0, 2.5),

                # Edge-aware zoom
                "camera_face_edge_aware_zoom": bool(self.camera_face_edge_aware_zoom_var.get()),
                "camera_face_edge_threshold": self._safe_float(self.camera_face_edge_threshold_var, 0.15, 0.05, 0.3),
                "camera_face_edge_zoom_multiplier": self._safe_float(self.camera_face_edge_zoom_multiplier_var, 1.3, 1.1, 2.0),

                # Face detection method
                "camera_face_detection_method": str(self.camera_face_detection_method_var.get()).strip().lower(),
                "camera_face_detection_interval": min(60, max(1, self._safe_int(self.camera_face_detection_interval_var, 10))),

                # Camera visual effects
                "camera_show_face_detection": bool(self.camera_show_face_detection_var.get()),
                "camera_invert_colors": bool(self.camera_invert_colors_var.get()),

                # Biodata Display
                "biodata_enabled": bool(self.biodata_enabled_var.get()),
                "biodata_title": str(self.biodata_title_var.get()).strip(),
                "biodata_first_name": str(self.biodata_first_name_var.get()).strip(),
                "biodata_last_name": str(self.biodata_last_name_var.get()).strip(),
                "biodata_show_full_name": bool(self.biodata_show_full_name_var.get()),
                "biodata_birthdate": str(self.biodata_birthdate_var.get()).strip(),
                "biodata_age_format": str(self.biodata_age_format_var.get()).strip().lower(),
                "biodata_show_days_lived": bool(self.biodata_show_days_lived_var.get()),
                "biodata_show_lineage": bool(self.biodata_show_lineage_var.get()),
                "biodata_lineage_text": str(self.biodata_lineage_text_var.get()).strip(),
                "biodata_show_role": bool(self.biodata_show_role_var.get()),
                "biodata_role_text": str(self.biodata_role_text_var.get()).strip(),
                "biodata_custom_text": str(self.biodata_custom_text_var.get()).strip(),

                # Biodata visual style
                "biodata_style": str(self.biodata_style_var.get()).strip(),
                "biodata_pulse_animation": bool(self.biodata_pulse_animation_var.get()),
                "biodata_font_size": int(self.biodata_font_size_var.get()),
            })

            # Individual challenges
            for challenge_id, _, _ in self.STUDYING_CHALLENGES:
                s[f"challenge_studying_{challenge_id}_enabled"] = bool(
                    self.studying_challenge_vars[challenge_id].get()
                )

            for challenge_id, _, _ in self.WASTING_CHALLENGES:
                s[f"challenge_wasting_{challenge_id}_enabled"] = bool(
                    self.wasting_challenge_vars[challenge_id].get()
                )

            # Merge schema-generated controls last so every generated field is
            # included in the same revision-aware save transaction.
            s.update(self._schema_settings.values())

            result = save_settings(s)
            if not result:
                message = "Settings changed elsewhere; reload before saving." if getattr(result, "conflict", False) else (
                    getattr(result, "error", None) or "Settings could not be written durably."
                )
                messagebox.showerror("Save Error", message)
                return
            self.on_save(s)
            self.destroy()

        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save settings: {e}")


# Task History Window (kept from original)
class TaskHistoryWindow(tk.Toplevel):
    """Task history window."""

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
            # Fallback if logging not available
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


# Backwards compatibility
SettingsWindow = AdvancedSettingsWindow

__all__ = ['SettingsWindow', 'AdvancedSettingsWindow', 'TaskHistoryWindow']

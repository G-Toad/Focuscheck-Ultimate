"""
Canonical registry of all settings keys.
"""

SETTINGS_REGISTRY = {
    # General
    "settings_schema_version": {"type": int, "default": 1, "description": "Schema version for settings file."},
    "interval_seconds": {"type": int, "default": 60, "description": "Interval between prompts in seconds."},
    "intensify_after_seconds": {"type": int, "default": 15, "description": "Time before prompt intensifies."},
    "overdrive_after_seconds": {"type": int, "default": 60, "description": "Time before prompt goes into overdrive."},
    "max_intensity_level": {"type": int, "default": 3, "description": "Maximum intensity level for prompts."},
    "always_on_top": {"type": bool, "default": True, "description": "Keep prompt window on top of other windows."},
    "center_on_show": {"type": bool, "default": True, "description": "Center prompt window on screen."},
    "follow_cursor_monitor": {"type": bool, "default": True, "description": "Center prompt on monitor with cursor."},
    "specific_monitor_only": {"type": bool, "default": False, "description": "Only show prompt on a specific monitor."},
    "specific_monitor_index": {"type": int, "default": 0, "description": "Index of the monitor to show the prompt on."},

    # Monitoring
    "monitoring_mode": {"type": str, "default": "v1", "description": "Monitoring engine version (v1 or v2)."},

    # Anti-habit
    "anti_habit_enabled": {"type": bool, "default": True, "description": "Enable anti-habit features."},
    "randomize_buttons": {"type": bool, "default": True, "description": "Randomize button order."},
    "studying_hold_ms": {"type": int, "default": 800, "description": "Hold time for studying button."},

    # Pause/disable controls
    "force_always_on": {"type": bool, "default": True, "description": "Never pause for any reason when True."},
    "pause_when_inactive_or_lid_closed": {"type": bool, "default": False, "description": "Master toggle for pausing logic."},
    "pause_on_idle": {"type": bool, "default": False, "description": "Pause when user is idle."},
    "pause_on_lid_closed": {"type": bool, "default": True, "description": "Pause when laptop lid is closed."},
    "pause_on_lock": {"type": bool, "default": True, "description": "Pause when session is locked."},
    "pause_on_sleep": {"type": bool, "default": True, "description": "Pause during system sleep."},
    "inactive_as_sleep_seconds": {"type": int, "default": 45, "description": "Idle time before pausing."},
    "pause_poll_interval_seconds": {"type": int, "default": 5, "description": "Polling interval when paused."},
    "paused": {"type": bool, "default": False, "description": "Current pause state."},

    # Spam Detection
    "spam_detection_enabled": {"type": bool, "default": True, "description": "Master switch for spam detection."},
    "spam_gibberish_detection": {"type": bool, "default": True, "description": "Enable gibberish detection."},
    "spam_min_vowel_ratio": {"type": float, "default": 0.15, "description": "Minimum vowel ratio for gibberish detection."},
    "spam_max_vowel_ratio": {"type": float, "default": 0.75, "description": "Maximum vowel ratio for gibberish detection."},
    "spam_min_unique_char_ratio": {"type": float, "default": 0.3, "description": "Minimum unique character ratio for gibberish detection."},
    "spam_repetition_check": {"type": bool, "default": True, "description": "Enable repetition check."},
    "spam_max_consecutive_chars": {"type": int, "default": 3, "description": "Maximum consecutive characters."},
    "spam_max_pattern_repetition": {"type": int, "default": 4, "description": "Maximum pattern repetition."},
    "spam_spacing_check": {"type": bool, "default": True, "description": "Enable spacing check."},
    "spam_min_length_require_spaces": {"type": int, "default": 20, "description": "Minimum length to require spaces."},
    "spam_keyboard_pattern_check": {"type": bool, "default": True, "description": "Enable keyboard pattern check."},
    "spam_min_keyboard_sequence_length": {"type": int, "default": 5, "description": "Minimum keyboard sequence length."},
    "spam_dictionary_check": {"type": bool, "default": True, "description": "Enable dictionary check."},
    "spam_min_real_word_ratio": {"type": float, "default": 0.5, "description": "Minimum real word ratio."},
    "spam_min_word_length": {"type": int, "default": 2, "description": "Minimum word length for dictionary check."},
    "spam_timing_check": {"type": bool, "default": True, "description": "Enable timing check."},
    "spam_min_time_to_submit": {"type": int, "default": 2, "description": "Minimum time to submit."},
    "spam_flag_if_under": {"type": int, "default": 1, "description": "Flag if submitted under this time."},
    "spam_banned_words": {"type": list, "default": ["idk", "dunno", "meh", "whatever"], "description": "Banned words."},
    "spam_vague_words": {"type": list, "default": ["stuff", "things", "something", "nothing"], "description": "Vague words."},

    # V2 Prompt
    "v2_force_all_validations": {"type": bool, "default": True, "description": "Force all validations in V2 prompt."},
}


try:
    from .defaults import DEFAULT_SETTINGS

    for key, default in DEFAULT_SETTINGS.items():
        SETTINGS_REGISTRY.setdefault(
            key,
            {
                "type": type(default),
                "default": default,
                "description": "Auto-registered default setting.",
            },
        )
except Exception:
    pass

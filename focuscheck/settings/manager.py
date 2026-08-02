"""Settings management - loading, saving, and validation."""

import json
import os
import platform
import threading
from .defaults import DEFAULT_SETTINGS
from ..utils.paths import choose_path
from ..utils.logging_utils import log_exception, get_logger, log_doctor_mode
from .registry import SETTINGS_REGISTRY


_settings_lock = threading.Lock()


def validate_settings(data):
    """Coerce and clamp settings to safe ranges; fill defaults; preserve unknown keys."""
    s = DEFAULT_SETTINGS.copy()

    # FIRST: Merge ALL keys from data (including unknown ones from plugins/future versions)
    for k, v in data.items():
        if k not in SETTINGS_REGISTRY:
            log_doctor_mode("UnknownSetting", f"Unknown setting key '{k}' found.", {"key": k, "value": v})
        s[k] = v

    # SECOND: Apply defaults for any missing keys
    for k, v in DEFAULT_SETTINGS.items():
        if k not in s:
            s[k] = v

    # THIRD: Coercions and clamps for known settings
    def _int(v, d):
        try:
            result = int(v)
            # Prevent extremely large values that could cause issues
            if abs(result) > 2**31 - 1:
                return d
            return result
        except (ValueError, TypeError, OverflowError):
            return d
    def _bool(v, d=False):
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return bool(v)
        if isinstance(v, str):
            normalized = v.strip().lower()
            if normalized in ("1", "true", "yes", "y", "on"):
                return True
            if normalized in ("0", "false", "no", "n", "off", ""):
                return False
        return bool(d)
    s["settings_schema_version"] = 1
    s["interval_seconds"] = max(10, _int(s.get("interval_seconds"), DEFAULT_SETTINGS["interval_seconds"]))
    s["intensify_after_seconds"] = max(5, _int(s.get("intensify_after_seconds"), DEFAULT_SETTINGS["intensify_after_seconds"]))
    s["overdrive_after_seconds"] = max(20, _int(s.get("overdrive_after_seconds"), DEFAULT_SETTINGS["overdrive_after_seconds"]))
    s["max_intensity_level"] = min(3, max(1, _int(s.get("max_intensity_level"), DEFAULT_SETTINGS["max_intensity_level"])))
    s["studying_hold_ms"] = max(200, _int(s.get("studying_hold_ms"), DEFAULT_SETTINGS["studying_hold_ms"]))
    s["inactive_as_sleep_seconds"] = max(15, _int(s.get("inactive_as_sleep_seconds"), DEFAULT_SETTINGS["inactive_as_sleep_seconds"]))
    s["specific_monitor_index"] = max(0, min(10, _int(s.get("specific_monitor_index"), DEFAULT_SETTINGS["specific_monitor_index"])))
    s["pause_poll_interval_seconds"] = max(2, _int(s.get("pause_poll_interval_seconds"), DEFAULT_SETTINGS["pause_poll_interval_seconds"]))
    s["overdrive_stage4_after_seconds"] = max(1, _int(s.get("overdrive_stage4_after_seconds"), DEFAULT_SETTINGS["overdrive_stage4_after_seconds"]))
    s["overdrive_stage4_flash_ms"] = max(20, _int(s.get("overdrive_stage4_flash_ms"), DEFAULT_SETTINGS["overdrive_stage4_flash_ms"]))
    # Stage 5 clamps
    s["overdrive_stage5_after_seconds"] = max(5, _int(s.get("overdrive_stage5_after_seconds"), DEFAULT_SETTINGS["overdrive_stage5_after_seconds"]))
    s["overdrive_stage5_hold_after_seconds"] = max(0, _int(s.get("overdrive_stage5_hold_after_seconds"), DEFAULT_SETTINGS["overdrive_stage5_hold_after_seconds"]))
    s["overdrive_stage5_slow_dim_seconds"] = max(1, _int(s.get("overdrive_stage5_slow_dim_seconds"), DEFAULT_SETTINGS["overdrive_stage5_slow_dim_seconds"]))
    try:
        a = float(s.get("overdrive_stage5_dim_max_alpha", DEFAULT_SETTINGS["overdrive_stage5_dim_max_alpha"]))
        if not (0.0 <= a <= 1.0):
            a = DEFAULT_SETTINGS["overdrive_stage5_dim_max_alpha"]
        s["overdrive_stage5_dim_max_alpha"] = a
    except Exception:
        s["overdrive_stage5_dim_max_alpha"] = DEFAULT_SETTINGS["overdrive_stage5_dim_max_alpha"]
    # Booleans
    for b in [
        "always_on_top", "center_on_show", "follow_cursor_monitor", "specific_monitor_only",
        "anti_habit_enabled", "randomize_buttons", "overlays_enabled",
        "force_always_on", "paused", "pause_when_inactive_or_lid_closed", "pause_on_idle",
        "pause_on_lid_closed", "pause_on_lock", "pause_on_sleep",
        "overdrive_stage4_enabled",
        "overdrive_stage5_enabled",
        "show_time_info", "time_info_12h", "time_info_show_seconds",
        "time_info_show_task_remaining",
        "hide_wasting_button",
        "modal_dialog_auto_focus",
        "wasting_prompt_ask_what", "wasting_prompt_ask_consequences",
        "wasting_prompt_validation_enabled",
        "v2_force_all_validations",
        "v2_question_use_window_title",
        "v2_focus_requires_enter",
        "v2_hide_prompt_during_intervention",
        "focus_prompt_ask_doing", "focus_prompt_ask_benefits",
        "prompt_require_all_fields",
        "require_active_task",
        "encouragement_enabled", "show_task_analytics", "tasks_change_counts_as_fail",
        "tasks_decision_prompt_enabled", "tasks_study_implies_fail_on_decision",
        "disable_jiggling", "enable_intensity_pulse", "enable_intensity_shake",
        "shake_lock_position",
        "enable_overdrive_flash_background", "enable_overdrive_shake_loop",
        "enable_overdrive_jiggle_buttons",
        "overdrive_stage5_dim_pulse",
        "tray_start_stop_enabled",
        "tray_settings_button_enabled",
        "tray_exit_button_enabled",
        "overdrive_stage5_click_through",
        "overdrive_stage5_slow_dim_enabled",
        # Snooze confirmation
        "snooze_prompt_enabled",
        "snooze_prompt_ask_reason",
        "snooze_prompt_validation_enabled",
        "snooze_prompt_exact_enabled",
        "snooze_exact_prevent_paste",
        "snooze_sentence_case_sensitive",
        "snooze_exact_require_focus_during_typing",
        "snooze_exact_force_all_heuristics",
        "snooze_exact_require_phrase",
        # Challenge system
        "challenge_system_enabled", "challenge_allow_skip", "challenge_show_hints",
        # Individual studying challenges
        "challenge_studying_learning_specificity_enabled",
        "challenge_studying_goal_connection_enabled",
        "challenge_studying_will_commitment_enabled",
        "challenge_studying_output_expectation_enabled",
        # Individual wasting challenges
        "challenge_wasting_wasting_acknowledgment_enabled",
        "challenge_wasting_should_gap_enabled",
        "challenge_wasting_because_reasoning_enabled",
        "challenge_wasting_hour_projection_enabled",
        "challenge_wasting_tomorrow_regret_enabled",
        "challenge_wasting_fear_acknowledgment_enabled",
        "challenge_wasting_lying_confrontation_enabled",
        # Spam detection
        "spam_detection_enabled", "spam_gibberish_detection", "spam_repetition_check",
        "spam_spacing_check", "spam_keyboard_pattern_check", "spam_dictionary_check",
        "spam_timing_check",
        # Camera feed
        "camera_feed_enabled", "camera_capture_on_click", "camera_face_maximize_in_display",
        "camera_flip_horizontal", "camera_face_edge_aware_zoom",
        # Biodata display
        "biodata_enabled", "biodata_show_full_name", "biodata_show_days_lived",
        "biodata_show_lineage", "biodata_show_role",
        # Audio alerts
        "audio_alerts_enabled", "audio_earphone_safe_mode", "audio_try_speaker_switch",
        # Snooze reminder
        "snooze_reminder_enabled",
    ]:
        s[b] = _bool(s.get(b, DEFAULT_SETTINGS[b]), DEFAULT_SETTINGS[b])
    # Strings
    s["webhook_url"] = str(s.get("webhook_url", "")).strip()
    s["snooze_until_utc"] = str(s.get("snooze_until_utc", DEFAULT_SETTINGS.get("snooze_until_utc", "")) or "").strip()
    s["overdrive_stage5_dim_color"] = str(s.get("overdrive_stage5_dim_color", DEFAULT_SETTINGS["overdrive_stage5_dim_color"]) or "#000000").strip()
    eng = str(data.get("overdrive_stage5_engine", DEFAULT_SETTINGS["overdrive_stage5_engine"])).strip().lower()
    if eng not in ("overlay", "gamma"):
        eng = "overlay"
    s["overdrive_stage5_engine"] = eng
    # Time info mode clamp
    mode = str(s.get("time_info_mode", "hour")).lower().strip()
    if mode not in ("hour", "day", "anchor", "launch"):
        mode = "hour"
    s["time_info_mode"] = mode
    # Analytics timescale clamp
    tscale = str(s.get("tasks_analytics_timescale", "lifetime")).lower().strip()
    if tscale not in ("lifetime", "today", "7d", "30d"):
        tscale = "lifetime"
    s["tasks_analytics_timescale"] = tscale
    # Unified decision window minutes (with legacy fallback)
    try:
        winm = s.get("tasks_decision_window_minutes", None)
        if winm is None:
            # Back-compat: derive from legacy per-mode settings
            emode_probe = str(s.get("tasks_evaluation_mode", "before")).strip().lower()
            if emode_probe == "before":
                winm = s.get("tasks_decision_threshold_minutes", 10)
            else:
                winm = s.get("tasks_post_eval_minutes", 10)
        s["tasks_decision_window_minutes"] = max(0, int(winm))
    except Exception:
        s["tasks_decision_window_minutes"] = 10
    # Evaluation timing clamp
    emode = str(s.get("tasks_evaluation_mode", "before")).strip().lower()
    if emode not in ("before", "after"):
        emode = "before"
    s["tasks_evaluation_mode"] = emode
    # Keep legacy keys sanitized but unused in UI
    try:
        s["tasks_decision_threshold_minutes"] = max(0, int(s.get("tasks_decision_threshold_minutes", 5)))
    except Exception:
        s["tasks_decision_threshold_minutes"] = 5
    try:
        s["tasks_post_eval_minutes"] = max(0, int(s.get("tasks_post_eval_minutes", 10)))
    except Exception:
        s["tasks_post_eval_minutes"] = 10
    # Jiggle style
    js = str(s.get("jiggle_style", "nudge")).strip().lower()
    if js not in ("off", "nudge", "pulse"):
        js = "nudge"
    s["jiggle_style"] = js
    # Anchor HH:MM sanitize
    def _sanitize_hhmm(val, default="09:00"):
        try:
            txt = str(val).strip()
            parts = txt.split(":")
            if len(parts) != 2: return default
            hh = int(parts[0]); mm = int(parts[1])
            if 0 <= hh <= 23 and 0 <= mm <= 59:
                return f"{hh:02d}:{mm:02d}"
            return default
        except Exception:
            return default
    s["time_info_anchor_hhmm"] = _sanitize_hhmm(s.get("time_info_anchor_hhmm", "09:00"), "09:00")
    # Refresh rate clamp
    s["time_info_refresh_ms"] = max(250, _int(s.get("time_info_refresh_ms"), DEFAULT_SETTINGS["time_info_refresh_ms"]))

    # UI scaling validation (50-150%)
    s["ui_scale_percent"] = max(50, min(150, _int(s.get("ui_scale_percent"), DEFAULT_SETTINGS["ui_scale_percent"])))

    # Popup layout mode validation
    layout_mode = str(s.get("popup_layout_mode", "vertical")).strip().lower()
    if layout_mode not in ("vertical", "horizontal", "compact"):
        layout_mode = "vertical"
    s["popup_layout_mode"] = layout_mode

    # Monitoring mode clamp
    mon_mode = str(s.get("monitoring_mode", "v1")).strip().lower()
    if mon_mode not in ("v1", "v2"):
        mon_mode = "v1"
    s["monitoring_mode"] = mon_mode

    # Button label behavior validation
    s["custom_button_phrases_enabled"] = bool(s.get("custom_button_phrases_enabled", False))
    for prefix in ("study", "waste"):
        mode = str(s.get(f"{prefix}_phrase_mode", "random")).strip().lower()
        if mode not in ("random", "sequential", "override"):
            mode = "random"
        s[f"{prefix}_phrase_mode"] = mode

        phrases = s.get(f"{prefix}_phrase_list", [])
        if not isinstance(phrases, list):
            phrases = []
        # Strip and drop empties
        s[f"{prefix}_phrase_list"] = [str(p).strip() for p in phrases if str(p).strip()]
        s[f"{prefix}_phrase_override"] = str(s.get(f"{prefix}_phrase_override", "")).strip()

    # Challenge system validation
    try:
        s["challenge_studying_frequency"] = max(0.0, min(1.0, float(s.get("challenge_studying_frequency", DEFAULT_SETTINGS["challenge_studying_frequency"]))))
    except Exception:
        s["challenge_studying_frequency"] = DEFAULT_SETTINGS["challenge_studying_frequency"]
    try:
        s["challenge_wasting_frequency"] = max(0.0, min(1.0, float(s.get("challenge_wasting_frequency", DEFAULT_SETTINGS["challenge_wasting_frequency"]))))
    except Exception:
        s["challenge_wasting_frequency"] = DEFAULT_SETTINGS["challenge_wasting_frequency"]
    s["challenge_min_words"] = max(1, _int(s.get("challenge_min_words"), DEFAULT_SETTINGS["challenge_min_words"]))
    s["challenge_min_total_length"] = max(1, _int(s.get("challenge_min_total_length"), DEFAULT_SETTINGS["challenge_min_total_length"]))

    # Spam detection validation
    try:
        s["spam_min_vowel_ratio"] = max(0.0, min(1.0, float(s.get("spam_min_vowel_ratio", DEFAULT_SETTINGS["spam_min_vowel_ratio"]))))
    except Exception:
        s["spam_min_vowel_ratio"] = DEFAULT_SETTINGS["spam_min_vowel_ratio"]
    try:
        s["spam_max_vowel_ratio"] = max(0.0, min(1.0, float(s.get("spam_max_vowel_ratio", DEFAULT_SETTINGS["spam_max_vowel_ratio"]))))
    except Exception:
        s["spam_max_vowel_ratio"] = DEFAULT_SETTINGS["spam_max_vowel_ratio"]
    try:
        s["spam_min_unique_char_ratio"] = max(0.0, min(1.0, float(s.get("spam_min_unique_char_ratio", DEFAULT_SETTINGS["spam_min_unique_char_ratio"]))))
    except Exception:
        s["spam_min_unique_char_ratio"] = DEFAULT_SETTINGS["spam_min_unique_char_ratio"]
    s["spam_max_consecutive_chars"] = max(1, _int(s.get("spam_max_consecutive_chars"), DEFAULT_SETTINGS["spam_max_consecutive_chars"]))
    s["spam_max_pattern_repetition"] = max(1, _int(s.get("spam_max_pattern_repetition"), DEFAULT_SETTINGS["spam_max_pattern_repetition"]))
    s["spam_min_length_require_spaces"] = max(1, _int(s.get("spam_min_length_require_spaces"), DEFAULT_SETTINGS["spam_min_length_require_spaces"]))
    s["spam_min_keyboard_sequence_length"] = max(1, _int(s.get("spam_min_keyboard_sequence_length"), DEFAULT_SETTINGS["spam_min_keyboard_sequence_length"]))
    try:
        s["spam_min_real_word_ratio"] = max(0.0, min(1.0, float(s.get("spam_min_real_word_ratio", DEFAULT_SETTINGS["spam_min_real_word_ratio"]))))
    except Exception:
        s["spam_min_real_word_ratio"] = DEFAULT_SETTINGS["spam_min_real_word_ratio"]
    s["spam_min_word_length"] = max(1, _int(s.get("spam_min_word_length"), DEFAULT_SETTINGS["spam_min_word_length"]))
    s["spam_min_time_to_submit"] = max(0, _int(s.get("spam_min_time_to_submit"), DEFAULT_SETTINGS["spam_min_time_to_submit"]))
    s["spam_flag_if_under"] = max(0, _int(s.get("spam_flag_if_under"), DEFAULT_SETTINGS["spam_flag_if_under"]))

    # Spam banned/vague words (preserve as lists)
    if "spam_banned_words" in s and isinstance(s["spam_banned_words"], list):
        s["spam_banned_words"] = s["spam_banned_words"]
    else:
        s["spam_banned_words"] = DEFAULT_SETTINGS["spam_banned_words"]
    if "spam_vague_words" in s and isinstance(s["spam_vague_words"], list):
        s["spam_vague_words"] = s["spam_vague_words"]
    else:
        s["spam_vague_words"] = DEFAULT_SETTINGS["spam_vague_words"]

    # Snooze prompt sentence list normalization
    sentences = s.get("snooze_prompt_sentences", DEFAULT_SETTINGS["snooze_prompt_sentences"])
    if not isinstance(sentences, list):
        sentences = []
    s["snooze_prompt_sentences"] = [str(x).strip() for x in sentences if str(x).strip()]

    # Snooze exact-typing heuristics clamps
    def _float(v, d):
        try:
            return float(v)
        except (ValueError, TypeError):
            return d
    s["snooze_exact_min_time_seconds"] = max(0.0, _float(s.get("snooze_exact_min_time_seconds"), DEFAULT_SETTINGS["snooze_exact_min_time_seconds"]))
    s["snooze_exact_time_per_char"] = max(0.0, _float(s.get("snooze_exact_time_per_char"), DEFAULT_SETTINGS["snooze_exact_time_per_char"]))
    try:
        s["snooze_exact_min_keypress_ratio"] = max(0.0, min(1.0, float(s.get("snooze_exact_min_keypress_ratio", DEFAULT_SETTINGS["snooze_exact_min_keypress_ratio"])) ))
    except Exception:
        s["snooze_exact_min_keypress_ratio"] = DEFAULT_SETTINGS["snooze_exact_min_keypress_ratio"]
    s["snooze_exact_max_jump_chars"] = max(1, _int(s.get("snooze_exact_max_jump_chars"), DEFAULT_SETTINGS["snooze_exact_max_jump_chars"]))
    # Snooze required phrase sanitization
    try:
        phrase = str(s.get("snooze_exact_required_phrase", DEFAULT_SETTINGS["snooze_exact_required_phrase"]))
    except Exception:
        phrase = DEFAULT_SETTINGS["snooze_exact_required_phrase"]
    s["snooze_exact_required_phrase"] = phrase.strip()

    # Camera feed settings
    s["camera_feed_enabled"] = bool(s.get("camera_feed_enabled", DEFAULT_SETTINGS["camera_feed_enabled"]))
    s["camera_capture_on_click"] = bool(s.get("camera_capture_on_click", DEFAULT_SETTINGS["camera_capture_on_click"]))
    # Camera mode validation
    camera_mode = s.get("camera_feed_mode", DEFAULT_SETTINGS["camera_feed_mode"])
    if camera_mode not in ("live", "static"):
        camera_mode = DEFAULT_SETTINGS["camera_feed_mode"]
    s["camera_feed_mode"] = camera_mode
    # Camera device and FPS
    s["camera_device_index"] = max(0, _int(s.get("camera_device_index"), DEFAULT_SETTINGS["camera_device_index"]))
    s["camera_fps"] = max(1, min(60, _int(s.get("camera_fps"), DEFAULT_SETTINGS["camera_fps"])))

    # Camera sizing mode validation
    sizing_mode = s.get("camera_sizing_mode", DEFAULT_SETTINGS["camera_sizing_mode"])
    if sizing_mode not in ("aspect_ratio", "fixed_size", "face_tracking", "manual_crop"):
        sizing_mode = DEFAULT_SETTINGS["camera_sizing_mode"]
    s["camera_sizing_mode"] = sizing_mode

    # Fixed size mode dimensions (also used as max dimensions in aspect_ratio mode)
    s["camera_feed_width"] = max(160, min(1920, _int(s.get("camera_feed_width"), DEFAULT_SETTINGS["camera_feed_width"])))
    s["camera_feed_height"] = max(120, min(1080, _int(s.get("camera_feed_height"), DEFAULT_SETTINGS["camera_feed_height"])))

    # Face tracking settings
    s["camera_face_max_width"] = max(160, min(1920, _int(s.get("camera_face_max_width"), DEFAULT_SETTINGS["camera_face_max_width"])))
    s["camera_face_max_height"] = max(120, min(1080, _int(s.get("camera_face_max_height"), DEFAULT_SETTINGS["camera_face_max_height"])))
    try:
        s["camera_face_zoom_factor"] = max(1.0, min(3.0, float(s.get("camera_face_zoom_factor", DEFAULT_SETTINGS["camera_face_zoom_factor"]))))
    except Exception:
        s["camera_face_zoom_factor"] = DEFAULT_SETTINGS["camera_face_zoom_factor"]
    # Face tracking fallback mode
    fallback_mode = s.get("camera_face_fallback_mode", DEFAULT_SETTINGS["camera_face_fallback_mode"])
    if fallback_mode not in ("aspect_ratio", "fixed_size"):
        fallback_mode = DEFAULT_SETTINGS["camera_face_fallback_mode"]
    s["camera_face_fallback_mode"] = fallback_mode

    # Face centering fine-tuning
    try:
        s["camera_face_center_vertical_bias"] = max(0.5, min(1.0, float(s.get("camera_face_center_vertical_bias", DEFAULT_SETTINGS["camera_face_center_vertical_bias"]))))
    except Exception:
        s["camera_face_center_vertical_bias"] = DEFAULT_SETTINGS["camera_face_center_vertical_bias"]
    try:
        s["camera_face_crop_width_multiplier"] = max(1.0, min(2.5, float(s.get("camera_face_crop_width_multiplier", DEFAULT_SETTINGS["camera_face_crop_width_multiplier"]))))
    except Exception:
        s["camera_face_crop_width_multiplier"] = DEFAULT_SETTINGS["camera_face_crop_width_multiplier"]
    try:
        s["camera_face_crop_height_multiplier"] = max(1.0, min(2.5, float(s.get("camera_face_crop_height_multiplier", DEFAULT_SETTINGS["camera_face_crop_height_multiplier"]))))
    except Exception:
        s["camera_face_crop_height_multiplier"] = DEFAULT_SETTINGS["camera_face_crop_height_multiplier"]

    # Edge-aware zoom
    s["camera_face_edge_aware_zoom"] = bool(s.get("camera_face_edge_aware_zoom", DEFAULT_SETTINGS["camera_face_edge_aware_zoom"]))
    try:
        s["camera_face_edge_threshold"] = max(0.05, min(0.3, float(s.get("camera_face_edge_threshold", DEFAULT_SETTINGS["camera_face_edge_threshold"]))))
    except Exception:
        s["camera_face_edge_threshold"] = DEFAULT_SETTINGS["camera_face_edge_threshold"]
    try:
        s["camera_face_edge_zoom_multiplier"] = max(1.1, min(2.0, float(s.get("camera_face_edge_zoom_multiplier", DEFAULT_SETTINGS["camera_face_edge_zoom_multiplier"]))))
    except Exception:
        s["camera_face_edge_zoom_multiplier"] = DEFAULT_SETTINGS["camera_face_edge_zoom_multiplier"]

    # Face detection method
    detection_method = str(s.get("camera_face_detection_method", "haar")).strip().lower()
    if detection_method not in ("haar", "dnn"):
        detection_method = "haar"
    s["camera_face_detection_method"] = detection_method

    # Face detection interval and max misses
    s["camera_face_detection_interval"] = max(1, min(30, _int(s.get("camera_face_detection_interval"), DEFAULT_SETTINGS.get("camera_face_detection_interval", 10))))
    s["camera_face_max_misses"] = max(1, min(50, _int(s.get("camera_face_max_misses"), DEFAULT_SETTINGS.get("camera_face_max_misses", 5))))

    # Manual crop mode settings validation
    s["manual_crop_box_width"] = max(160, min(1920, _int(s.get("manual_crop_box_width"), DEFAULT_SETTINGS["manual_crop_box_width"])))
    s["manual_crop_box_height"] = max(120, min(1080, _int(s.get("manual_crop_box_height"), DEFAULT_SETTINGS["manual_crop_box_height"])))

    # Anchor mode validation
    anchor_mode = str(s.get("manual_crop_anchor_mode", "center")).strip().lower()
    if anchor_mode not in ("edge", "corner", "center"):
        anchor_mode = DEFAULT_SETTINGS["manual_crop_anchor_mode"]
    s["manual_crop_anchor_mode"] = anchor_mode

    # Zoom validation
    try:
        s["manual_crop_zoom"] = max(0.5, min(5.0, float(s.get("manual_crop_zoom", DEFAULT_SETTINGS["manual_crop_zoom"]))))
    except Exception:
        s["manual_crop_zoom"] = DEFAULT_SETTINGS["manual_crop_zoom"]

    # Center mode settings
    try:
        s["manual_crop_center_offset_x"] = max(-0.5, min(0.5, float(s.get("manual_crop_center_offset_x", DEFAULT_SETTINGS["manual_crop_center_offset_x"]))))
    except Exception:
        s["manual_crop_center_offset_x"] = DEFAULT_SETTINGS["manual_crop_center_offset_x"]
    try:
        s["manual_crop_center_offset_y"] = max(-0.5, min(0.5, float(s.get("manual_crop_center_offset_y", DEFAULT_SETTINGS["manual_crop_center_offset_y"]))))
    except Exception:
        s["manual_crop_center_offset_y"] = DEFAULT_SETTINGS["manual_crop_center_offset_y"]

    # Edge mode settings
    edge = str(s.get("manual_crop_edge", "top")).strip().lower()
    if edge not in ("top", "bottom", "left", "right"):
        edge = DEFAULT_SETTINGS["manual_crop_edge"]
    s["manual_crop_edge"] = edge
    try:
        s["manual_crop_edge_offset"] = max(-1.0, min(1.0, float(s.get("manual_crop_edge_offset", DEFAULT_SETTINGS["manual_crop_edge_offset"]))))
    except Exception:
        s["manual_crop_edge_offset"] = DEFAULT_SETTINGS["manual_crop_edge_offset"]

    # Corner mode settings
    corner = str(s.get("manual_crop_corner", "top_left")).strip().lower()
    if corner not in ("top_left", "top_right", "bottom_left", "bottom_right"):
        corner = DEFAULT_SETTINGS["manual_crop_corner"]
    s["manual_crop_corner"] = corner
    try:
        s["manual_crop_corner_expand_x"] = max(0.0, min(5.0, float(s.get("manual_crop_corner_expand_x", DEFAULT_SETTINGS["manual_crop_corner_expand_x"]))))
    except Exception:
        s["manual_crop_corner_expand_x"] = DEFAULT_SETTINGS["manual_crop_corner_expand_x"]
    try:
        s["manual_crop_corner_expand_y"] = max(0.0, min(5.0, float(s.get("manual_crop_corner_expand_y", DEFAULT_SETTINGS["manual_crop_corner_expand_y"]))))
    except Exception:
        s["manual_crop_corner_expand_y"] = DEFAULT_SETTINGS["manual_crop_corner_expand_y"]

    # Display options
    grid_overlay = str(s.get("manual_crop_grid_overlay", "off")).strip().lower()
    if grid_overlay not in ("off", "rule_of_thirds", "4x4", "custom"):
        grid_overlay = DEFAULT_SETTINGS["manual_crop_grid_overlay"]
    s["manual_crop_grid_overlay"] = grid_overlay
    s["manual_crop_show_safe_zones"] = bool(s.get("manual_crop_show_safe_zones", DEFAULT_SETTINGS["manual_crop_show_safe_zones"]))
    s["manual_crop_lock_aspect"] = bool(s.get("manual_crop_lock_aspect", DEFAULT_SETTINGS["manual_crop_lock_aspect"]))
    try:
        s["manual_crop_preview_opacity"] = max(0.0, min(1.0, float(s.get("manual_crop_preview_opacity", DEFAULT_SETTINGS["manual_crop_preview_opacity"]))))
    except Exception:
        s["manual_crop_preview_opacity"] = DEFAULT_SETTINGS["manual_crop_preview_opacity"]

    # Crop presets validation
    presets = s.get("manual_crop_presets", None)
    if not isinstance(presets, dict):
        s["manual_crop_presets"] = DEFAULT_SETTINGS["manual_crop_presets"].copy()
    else:
        # Keep user presets but ensure defaults exist
        for name, config in DEFAULT_SETTINGS["manual_crop_presets"].items():
            if name not in presets:
                presets[name] = config
        s["manual_crop_presets"] = presets

    # Biodata display validation
    # Sanitize text fields (limit length and strip whitespace)
    def _sanitize_text(val, default, max_len=100):
        try:
            txt = str(val).strip()
            if len(txt) > max_len:
                txt = txt[:max_len]
            return txt
        except Exception:
            return default

    s["biodata_title"] = _sanitize_text(s.get("biodata_title", DEFAULT_SETTINGS["biodata_title"]), DEFAULT_SETTINGS["biodata_title"], 20)
    s["biodata_first_name"] = _sanitize_text(s.get("biodata_first_name", DEFAULT_SETTINGS["biodata_first_name"]), DEFAULT_SETTINGS["biodata_first_name"], 50)
    s["biodata_last_name"] = _sanitize_text(s.get("biodata_last_name", DEFAULT_SETTINGS["biodata_last_name"]), DEFAULT_SETTINGS["biodata_last_name"], 50)
    s["biodata_lineage_text"] = _sanitize_text(s.get("biodata_lineage_text", DEFAULT_SETTINGS["biodata_lineage_text"]), DEFAULT_SETTINGS["biodata_lineage_text"], 150)
    s["biodata_role_text"] = _sanitize_text(s.get("biodata_role_text", DEFAULT_SETTINGS["biodata_role_text"]), DEFAULT_SETTINGS["biodata_role_text"], 100)
    s["biodata_custom_text"] = _sanitize_text(s.get("biodata_custom_text", DEFAULT_SETTINGS["biodata_custom_text"]), DEFAULT_SETTINGS["biodata_custom_text"], 200)

    # Validate birthdate format (YYYY-MM-DD)
    def _validate_date(val, default="2005-01-01"):
        try:
            txt = str(val).strip()
            # Basic format check: YYYY-MM-DD
            if len(txt) == 10 and txt[4] == '-' and txt[7] == '-':
                parts = txt.split('-')
                year = int(parts[0])
                month = int(parts[1])
                day = int(parts[2])
                # Validate ranges
                if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                    return txt
            return default
        except Exception:
            return default

    s["biodata_birthdate"] = _validate_date(s.get("biodata_birthdate", DEFAULT_SETTINGS["biodata_birthdate"]), DEFAULT_SETTINGS["biodata_birthdate"])

    # Validate age format
    age_format = s.get("biodata_age_format", DEFAULT_SETTINGS["biodata_age_format"])
    if age_format not in ("simple", "precise", "decimal"):
        age_format = DEFAULT_SETTINGS["biodata_age_format"]
    s["biodata_age_format"] = age_format

    # Website flags normalization
    flags = s.get("website_flags", [])
    normalized = []
    if isinstance(flags, list):
        for entry in flags:
            if not isinstance(entry, dict):
                continue
            domain = str(entry.get("domain", "")).strip().lower()
            if not domain:
                continue
            severity = entry.get("severity", 1)
            cooldown = entry.get("cooldown_minutes", 5)
            normalized.append({
                "domain": domain,
                "enabled": bool(entry.get("enabled", True)),
                "severity": max(1, min(3, _int(severity, 1))),
                "cooldown_minutes": max(0, _int(cooldown, 5)),
                "allow_once": bool(entry.get("allow_once", False)),
                "last_dismissed": float(entry.get("last_dismissed", 0.0)) if isinstance(entry.get("last_dismissed"), (int, float)) else None,
            })
    s["website_flags"] = normalized

    return s


def load_settings():
    """Load settings from JSON file."""
    logger = get_logger()
    SETTINGS_PATH = choose_path("focus_settings.json")

    logger.info("=" * 80)
    logger.info("load_settings() CALLED - Loading settings from disk")
    logger.info("  SETTINGS_PATH: %s", SETTINGS_PATH)
    logger.info("  Acquiring settings lock...")

    with _settings_lock:
        logger.info("  Lock acquired")
        logger.info("  Checking if settings file exists...")
        exists = os.path.exists(SETTINGS_PATH)
        logger.info("    File exists: %s", exists)

        if exists:
            logger.info("  Settings file exists, attempting to load...")
            try:
                logger.info("    Opening file for reading...")
                with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                    logger.info("    File opened successfully")
                    logger.info("    Parsing JSON...")
                    data = json.load(f)
                    logger.info("    JSON parsed successfully")
                    logger.info("      Raw data type: %s", type(data))
                    logger.info("      Number of keys: %s", len(data) if isinstance(data, dict) else "N/A")

                logger.info("    Validating settings...")
                validated = validate_settings(data)
                logger.info("    Settings validated successfully")
                logger.info("      Validated keys: %s", len(validated))
                logger.info("load_settings() COMPLETED - Settings loaded from file")
                logger.info("=" * 80)
                return validated
            except Exception as e:
                logger.error("  ERROR loading settings file: %s", e)
                logger.exception("  Full exception:")
                log_exception("load_settings: failed to parse settings; using defaults")
                logger.info("  Falling through to default settings...")
        else:
            logger.info("  Settings file does not exist, will use defaults")

        # Create data dir if needed
        logger.info("  Creating data directory if needed...")
        try:
            dir_path = os.path.dirname(SETTINGS_PATH)
            logger.info("    Directory path: %s", dir_path)
            os.makedirs(dir_path, exist_ok=True)
            logger.info("    Directory created/verified")
        except Exception as e:
            logger.error("    ERROR creating directory: %s", e)

        logger.info("  Returning default settings copy...")
        defaults = DEFAULT_SETTINGS.copy()
        logger.info("    Default settings keys: %s", len(defaults))
        logger.info("load_settings() COMPLETED - Using defaults")
        logger.info("=" * 80)
        return defaults


def save_settings(s):
    """Save settings to JSON file atomically."""
    logger = get_logger()
    SETTINGS_PATH = choose_path("focus_settings.json")

    logger.info("=" * 80)
    logger.info("save_settings() CALLED - Saving settings to disk")
    logger.info("  SETTINGS_PATH: %s", SETTINGS_PATH)
    logger.info("  Input settings type: %s", type(s))
    logger.info("  Input settings keys: %s", len(s) if isinstance(s, dict) else "N/A")
    logger.info("  Acquiring settings lock...")

    with _settings_lock:
        logger.info("  Lock acquired")
        logger.info("  Creating data directory if needed...")

        try:
            dir_path = os.path.dirname(SETTINGS_PATH)
            logger.info("    Directory path: %s", dir_path)
            os.makedirs(dir_path, exist_ok=True)
            logger.info("    Directory created/verified")
        except Exception as e:
            logger.error("    ERROR creating directory: %s", e)

        temp_path = SETTINGS_PATH + ".tmp"
        logger.info("  Temporary file path: %s", temp_path)

        try:
            logger.info("  Starting atomic write...")
            logger.info("    Validating settings before save...")
            validated = validate_settings(s)
            logger.info("    Settings validated")
            logger.info("      Validated keys: %s", len(validated))

            logger.info("    Opening temporary file for writing...")
            with open(temp_path, "w", encoding="utf-8") as f:
                logger.info("    Temporary file opened")
                logger.info("    Dumping JSON to file...")
                json.dump(validated, f, indent=2)
                logger.info("    JSON dumped successfully")

                logger.info("    Flushing write buffer...")
                f.flush()
                logger.info("    Buffer flushed")

                logger.info("    Forcing write to disk (fsync)...")
                os.fsync(f.fileno())
                logger.info("    fsync completed")

            logger.info("  Temporary file written successfully")
            logger.info("    File size: %s bytes", os.path.getsize(temp_path))

            logger.info("  Replacing settings file atomically...")
            os.replace(temp_path, SETTINGS_PATH)
            logger.info("    Replace completed successfully")

            logger.info("  Atomic write completed successfully")
            logger.info("  Final file size: %s bytes", os.path.getsize(SETTINGS_PATH))
            get_logger().info("settings saved")
            logger.info("save_settings() COMPLETED - SUCCESS")
            logger.info("=" * 80)

        except Exception as e:
            logger.error("  ERROR during save operation: %s", e)
            logger.exception("  Full exception:")

            # Clean up temp file on failure
            logger.info("  Attempting cleanup of temporary file...")
            try:
                if os.path.exists(temp_path):
                    logger.info("    Temporary file exists, removing...")
                    os.remove(temp_path)
                    logger.info("    Temporary file removed")
                else:
                    logger.info("    Temporary file doesn't exist, nothing to clean")
            except Exception as cleanup_e:
                logger.error("    ERROR during cleanup: %s", cleanup_e)

            log_exception("save_settings: failed to write file")
            logger.info("save_settings() COMPLETED - FAILED")
            logger.info("=" * 80)

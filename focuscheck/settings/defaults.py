"""
Default settings for FocusCheck application.

This module contains all default configuration values.
"""

DEFAULT_SETTINGS = {
    "settings_schema_version": 2,
    "settings_revision": 0,
    "interval_seconds": 60,
    "intensify_after_seconds": 15,
    "overdrive_after_seconds": 60,
    "max_intensity_level": 3,
    "always_on_top": True,
    "center_on_show": True,
    # Recenter dialog to the monitor under the mouse cursor while open
    "follow_cursor_monitor": True,
    # Only show popup on specific monitor (overrides follow_cursor_monitor)
    "specific_monitor_only": False,
    "specific_monitor_index": 0,  # 0=primary, 1=second monitor, 2=third, etc

    "monitoring_mode": "v1",  # v1 | v2

    # Anti-habit
    "anti_habit_enabled": True,
    "randomize_buttons": True,
    "studying_hold_ms": 800,

    # Pause/disable controls
    # Hard override: never pause for any reason when True
    "force_always_on": True,
    # Master toggle for pausing logic (kept for backward compatibility)
    "pause_when_inactive_or_lid_closed": False,
    # Granular toggles
    "pause_on_idle": False,               # default OFF per request
    "pause_on_lid_closed": True,
    "pause_on_lock": True,               # Windows: pause while session locked
    "pause_on_sleep": True,              # Pause during system sleep
    # Idle threshold & poll cadence
    "inactive_as_sleep_seconds": 45,     # used only if pause_on_idle=True
    "pause_poll_interval_seconds": 5,    # how often to re-check while paused
    "paused": False,
    "snooze_until_utc": "",

    # Optional webhook
    "webhook_url": "",

    # Master switch for overlay-style visual interventions.
    "overlays_enabled": True,

    # Overdrive stage 4 (ultra-fast red flashing)
    "overdrive_stage4_enabled": True,
    "overdrive_stage4_after_seconds": 12,
    "overdrive_stage4_flash_ms": 60,
    # Overdrive stage 5 (multi-monitor dim/blackout)
    "overdrive_stage5_enabled": True,
    # Trigger stage 5 this many seconds after stage 4 begins
    "overdrive_stage5_after_seconds": 60,
    # Dimming behavior
    # Allow underlying apps to remain clickable while dimmed
    "overdrive_stage5_click_through": True,
    "overdrive_stage5_dim_pulse": True,
    "overdrive_stage5_dim_max_alpha": 0.92,
    "overdrive_stage5_dim_color": "#000000",
    # Stage 5 engine: overlay | gamma
    "overdrive_stage5_engine": "overlay",
    # Stage 5 optional: hold final black after N seconds (0 = off)
    "overdrive_stage5_hold_after_seconds": 0,
    # Stage 5 optional: one-way slow-dim to black over N seconds
    "overdrive_stage5_slow_dim_enabled": False,
    "overdrive_stage5_slow_dim_seconds": 30,

    # Time info label under buttons
    "show_time_info": False,
    "time_info_mode": "hour",          # hour | day | anchor | launch
    "time_info_anchor_hhmm": "09:00",
    "time_info_12h": False,
    "time_info_show_seconds": False,
    "time_info_refresh_ms": 1000,
    # Also show remaining time until current task due (if any)
    "time_info_show_task_remaining": False,

    # UI tweaks
    "hide_wasting_button": False,
    "modal_dialog_auto_focus": True,
    "ui_scale_percent": 100,  # Global UI scaling (50-150%) - shrinks entire popup proportionally
    "popup_layout_mode": "vertical",  # Layout style: vertical | horizontal | compact

    # Wasting-time prompt (optional)
    # When enabled, clicking 'Wasting time' asks for details to drive reflection
    "wasting_prompt_ask_what": True,
    # Also ask for consequences
    "wasting_prompt_ask_consequences": True,
    # Allow disabling validation entirely for the wasting prompt
    "wasting_prompt_validation_enabled": True,

    "v2_force_all_validations": True,
    "v2_question_use_window_title": True,
    "v2_focus_requires_enter": False,
    "v2_hide_prompt_during_intervention": True,

    # Studying confirmation prompt (optional)
    "focus_prompt_ask_doing": True,
    "focus_prompt_ask_benefits": True,

    # Require answers for every enabled follow-up question before closing dialogs
    "prompt_require_all_fields": False,

    # Require an active task before closing the prompt (optional)
    "require_active_task": False,

    # Spam detection for prompt responses
    "spam_detection_enabled": True,
    # Gibberish detection
    "spam_gibberish_detection": True,
    "spam_min_vowel_ratio": 0.15,  # Lowered from 0.2 to be less strict
    "spam_max_vowel_ratio": 0.75,  # Raised from 0.7 to be less strict
    "spam_min_unique_char_ratio": 0.3,  # Lowered from 0.4 to allow more repetition in short responses
    # Character repetition
    "spam_repetition_check": True,
    "spam_max_consecutive_chars": 3,  # Raised from 2: now "aaa" ok, "aaaa" flagged
    "spam_max_pattern_repetition": 4,  # Raised from 3: "asdf" repeated 4x ok, 5x flagged
    # Spacing
    "spam_spacing_check": True,
    "spam_min_length_require_spaces": 20,  # Raised from 15 to allow short phrases without spaces
    # Keyboard patterns (qwerty, asdf, etc.)
    "spam_keyboard_pattern_check": True,
    "spam_min_keyboard_sequence_length": 5,  # Raised from 4 to reduce false positives
    # Dictionary validation
    "spam_dictionary_check": True,
    "spam_min_real_word_ratio": 0.5,  # Lowered from 0.6 (60%) to 50% to be more lenient
    "spam_min_word_length": 2,
    # Timing validation
    "spam_timing_check": True,
    "spam_min_time_to_submit": 2,  # Lowered from 3 to 2 seconds
    "spam_flag_if_under": 1,  # Lowered from 2 to 1 second - only flag extremely fast responses
    # Word quality
    "spam_banned_words": ["idk", "dunno", "meh", "whatever"],
    "spam_vague_words": ["stuff", "things", "something", "nothing"],

    # Challenge-based reflection barriers
    "challenge_system_enabled": True,
    "challenge_studying_frequency": 0.3,   # 30% of studying prompts get a challenge
    "challenge_wasting_frequency": 0.5,    # 50% of wasting prompts get a challenge
    "challenge_min_words": 3,              # Minimum word count for challenge responses (lowered from 5)
    "challenge_min_total_length": 10,      # Minimum character count (lowered from 20 to allow short but valid responses)
    "challenge_allow_skip": False,         # If True, user can cancel challenge dialog
    "challenge_show_hints": True,          # Show example answers for challenges

    # Individual studying challenges (all enabled by default)
    "challenge_studying_learning_specificity_enabled": True,
    "challenge_studying_goal_connection_enabled": True,
    "challenge_studying_will_commitment_enabled": True,
    "challenge_studying_output_expectation_enabled": True,

    # Individual wasting challenges (all enabled by default)
    "challenge_wasting_wasting_acknowledgment_enabled": True,
    "challenge_wasting_should_gap_enabled": True,
    "challenge_wasting_because_reasoning_enabled": True,
    "challenge_wasting_hour_projection_enabled": True,
    "challenge_wasting_tomorrow_regret_enabled": True,
    "challenge_wasting_fear_acknowledgment_enabled": True,
    "challenge_wasting_lying_confrontation_enabled": True,

    # Phrase Acronym Challenge Feature (mutually exclusive with reflection questions)
    "phrase_acronym_enabled": False,  # Enable the acronym challenge instead of reflection questions

    # Button label behavior
    "custom_button_phrases_enabled": False,  # Use custom/random phrases instead of classic labels

    # Study Button Phrases
    "study_phrase_list": [
        "By any means necessary",
        "Focus on the goal",
        "Excellence demands sacrifice",
        "Win this moment",
    ],
    "study_phrase_mode": "random",  # random | sequential | override
    "study_phrase_override": "",  # Single phrase when mode="override"
    "study_phrase_index": 0,  # Track position for sequential mode

    # Wasting Time Button Phrases
    "waste_phrase_list": [
        "Stop wasting precious time",
        "Get back to work now",
        "Discipline equals freedom",
        "Future you is watching",
    ],
    "waste_phrase_mode": "random",  # random | sequential | override
    "waste_phrase_override": "",  # Single phrase when mode="override"
    "waste_phrase_index": 0,  # Track position for sequential mode

    # Acronym Dialog Display Options
    "phrase_acronym_box_size": 60,  # Size of each letter box (pixels)
    "phrase_acronym_letter_size": 45,  # Size of draggable letter buttons (pixels)
    "phrase_acronym_font_size": 16,  # Font size for phrase text below boxes

    # Tray action controls
    "tray_start_stop_enabled": True,
    "tray_settings_button_enabled": True,
    "tray_exit_button_enabled": True,

    "website_flags": [],

    # Task encouragement feature (optional)
    "encouragement_enabled": True,
    "show_task_analytics": True,
    # lifetime | today | 7d | 30d
    "tasks_analytics_timescale": "lifetime",
    # Whether changing tasks should count as a failure for analytics
    "tasks_change_counts_as_fail": True,
    # Task deadline decision prompt
    "tasks_decision_prompt_enabled": True,
    "tasks_decision_threshold_minutes": 5,  # legacy (deprecated)
    "tasks_study_implies_fail_on_decision": True,
    # Evaluation timing: before = ask within threshold before due; after = ask after due + offset
    "tasks_evaluation_mode": "before",  # before | after
    "tasks_post_eval_minutes": 10,  # legacy (deprecated)
    # Unified decision window (minutes) applied depending on evaluation mode
    "tasks_decision_window_minutes": 10,

    # Alert/jiggle behavior controls
    "disable_jiggling": False,
    "enable_intensity_pulse": True,
    "enable_intensity_shake": True,
    "shake_lock_position": True,
    "enable_overdrive_flash_background": True,
    "enable_overdrive_shake_loop": True,
    "enable_overdrive_jiggle_buttons": True,
    # off | nudge | pulse
    "jiggle_style": "nudge",

    # Audio alerts
    "audio_alerts_enabled": False,  # Play audio alarms when prompts are ignored
    "audio_alarm_duration_seconds": 5,  # Duration of alarm playback (for repeating/escalating modes)
    # Audio pattern: single_beep, rapid_beeps, escalating, pulsing, siren, alternating
    "audio_alarm_pattern": "rapid_beeps",
    # Audio behavior: once, repeating, escalating_volume, continuous
    "audio_alarm_mode": "once",
    # Trigger point: intensification, overdrive, overdrive_stage4, overdrive_stage5
    "audio_alarm_trigger": "overdrive",
    # Safety and volume
    "audio_earphone_safe_mode": True,  # Limit frequencies and volume for earphone safety
    "audio_max_volume": 0.7,  # Maximum volume scale (0.0-1.0)
    # Device switching
    "audio_try_speaker_switch": False,  # Try to switch from headphones to speakers if unresponsive
    "audio_speaker_switch_after_seconds": 30,  # After this many seconds, try switching to speakers

    # Snooze reminder
    "snooze_reminder_enabled": True,  # Show gentle reminder to re-enable when snoozed
    "snooze_reminder_interval_seconds": 300,  # How often to show reminder (default: 5 minutes)

    # Camera feed reflection feature
    "camera_feed_enabled": False,  # Enable camera feed in popup window
    "camera_feed_mode": "live",  # live | static - live feed vs snapshot when popup appears
    "camera_capture_on_click": False,  # Capture photo when buttons are clicked (for accountability logs)
    "camera_device_index": 0,  # Camera device index (0 = default camera)
    "camera_fps": 20,  # Frame rate for live feed (20=balanced, 30=smooth but CPU intensive, 15=low-end CPUs)
    "camera_flip_horizontal": True,  # Flip camera horizontally (mirror effect)

    # Camera sizing mode: aspect_ratio | fixed_size | face_tracking | manual_crop
    "camera_sizing_mode": "aspect_ratio",  # aspect_ratio = maintain natural ratio, fixed_size = fill specified dimensions (may distort), face_tracking = zoom to face, manual_crop = custom crop with live preview

    # Fixed size mode settings (used when camera_sizing_mode = "fixed_size")
    "camera_feed_width": 320,  # Width of camera display in pixels
    "camera_feed_height": 240,  # Height of camera display in pixels

    # Face tracking mode settings (used when camera_sizing_mode = "face_tracking")
    "camera_face_max_width": 400,  # Maximum width when face tracking (recommended: 400 for good presence without overwhelming)
    "camera_face_max_height": 300,  # Maximum height when face tracking (recommended: 300)
    "camera_face_zoom_factor": 1.5,  # How much to zoom into detected face (1.0 = just face, 1.5 = face + some context)
    "camera_face_maximize_in_display": True,  # Scale face-tracked output to fill display box (maintains aspect ratio)
    "camera_face_fallback_mode": "aspect_ratio",  # What to do when no face detected: aspect_ratio | fixed_size

    # Face centering fine-tuning (advanced settings for proper chin/face framing)
    "camera_face_center_vertical_bias": 0.65,  # Vertical center point (0.5=middle, 0.65=lower - includes chin, 1.0=bottom)
    "camera_face_crop_width_multiplier": 1.4,  # How much wider than detected face (1.0=exact, 1.4=40% wider)
    "camera_face_crop_height_multiplier": 1.6,  # How much taller than detected face (1.0=exact, 1.6=60% taller for chin)

    # Edge-aware zoom (prevents face cutoff when near frame edges)
    "camera_face_edge_aware_zoom": True,  # Automatically zoom out when face is near edges
    "camera_face_edge_threshold": 0.15,  # How close to edge triggers zoom-out (0.1=10% from edge, 0.2=20%)
    "camera_face_edge_zoom_multiplier": 1.3,  # How much to zoom out at edges (1.3=30% more visible area)

    # Face detection algorithm
    "camera_face_detection_method": "haar",  # haar (fast, CPU-friendly) | dnn (accurate, more CPU)
    "camera_face_detection_interval": 10,  # Run face detection every N frames (higher = better performance, lower = smoother tracking)
    "camera_face_max_misses": 5,  # Expire cached face after N consecutive failed detections

    # Manual crop mode settings (used when camera_sizing_mode = "manual_crop")
    "manual_crop_box_width": 400,  # Output box width in pixels
    "manual_crop_box_height": 300,  # Output box height in pixels
    "manual_crop_anchor_mode": "center",  # Anchor mode: edge | corner | center
    "manual_crop_zoom": 1.0,  # Zoom level (0.5-5.0, where 1.0 = no zoom, 2.0 = 2x zoom)

    # Center-based anchor mode settings
    "manual_crop_center_offset_x": 0.0,  # X offset from center (-0.5 to 0.5, percentage of frame width)
    "manual_crop_center_offset_y": 0.0,  # Y offset from center (-0.5 to 0.5, percentage of frame height)

    # Edge-based anchor mode settings
    "manual_crop_edge": "top",  # Which edge to anchor to: top | bottom | left | right
    "manual_crop_edge_offset": 0.0,  # Offset perpendicular to edge (-1.0 to 1.0)

    # Corner-based anchor mode settings
    "manual_crop_corner": "top_left",  # Which corner: top_left | top_right | bottom_left | bottom_right
    "manual_crop_corner_expand_x": 1.0,  # Horizontal expansion from corner (0.0-5.0)
    "manual_crop_corner_expand_y": 1.0,  # Vertical expansion from corner (0.0-5.0)

    # Display and preview options
    "manual_crop_grid_overlay": "off",  # Grid overlay: off | rule_of_thirds | 4x4 | custom
    "manual_crop_show_safe_zones": False,  # Show areas that might be cut off
    "manual_crop_lock_aspect": True,  # Lock aspect ratio when adjusting dimensions
    "manual_crop_preview_opacity": 0.7,  # Opacity of crop overlay in preview (0.0-1.0)

    # Crop presets (stored as JSON dict: name -> settings)
    "manual_crop_presets": {
        "Face Close-up": {"anchor_mode": "center", "zoom": 2.0, "center_offset_x": 0.0, "center_offset_y": -0.1, "box_width": 320, "box_height": 240},
        "Upper Body": {"anchor_mode": "center", "zoom": 1.3, "center_offset_x": 0.0, "center_offset_y": 0.0, "box_width": 400, "box_height": 300},
        "Full Frame": {"anchor_mode": "center", "zoom": 1.0, "center_offset_x": 0.0, "center_offset_y": 0.0, "box_width": 640, "box_height": 480},
        "Desk View": {"anchor_mode": "edge", "zoom": 1.2, "edge": "top", "edge_offset": 0.0, "box_width": 640, "box_height": 360},
    },

    # Camera visual effects & enhancements
    "camera_show_face_detection": False,  # Show face detection markers (rectangles, center points, crop regions)
    "camera_invert_colors": False,  # Invert all colors (B&W negative effect)

    # Manual camera adjustments with auto-adapt
    "camera_manual_adjustments_enabled": False,  # Enable manual color/brightness adjustments
    "camera_manual_brightness": 0.5,  # 0.0=darkest, 0.5=neutral, 1.0=brightest
    "camera_manual_contrast": 0.5,  # 0.0=flat, 0.5=neutral, 1.0=punchy
    "camera_manual_saturation": 0.5,  # 0.0=grayscale, 0.5=neutral, 1.0=vibrant
    "camera_manual_sharpness": 0.5,  # 0.0=soft/blurry, 0.5=neutral, 1.0=sharp
    "camera_manual_gamma": 0.5,  # 0.0=lift shadows, 0.5=neutral, 1.0=crush blacks
    "camera_manual_tint": 0.5,  # 0.0=cool/blue, 0.5=neutral, 1.0=warm/orange
    "camera_auto_adapt": False,  # Intelligently scale manual settings based on lighting conditions

    # Biodata identity display (shown below camera feed for self-awareness and accountability)
    "biodata_enabled": False,  # Master toggle for biodata display
    "biodata_title": "Mr",  # Title prefix (Mr, Ms, Dr, etc.)
    "biodata_first_name": "",  # First name
    "biodata_last_name": "",  # Last name
    "biodata_show_full_name": True,  # Display full name in popup
    "biodata_birthdate": "2005-01-01",  # Birth date in YYYY-MM-DD format for age calculation
    "biodata_age_format": "simple",  # Age display format: simple | precise | decimal
    "biodata_show_days_lived": False,  # Show total days lived
    "biodata_show_lineage": False,  # Show family lineage/heritage information
    "biodata_lineage_text": "Heir of the Singh family",  # Custom lineage text
    "biodata_show_role": False,  # Show current role/phase
    "biodata_role_text": "Student",  # Custom role text
    "biodata_custom_text": "",  # Additional custom statement for personal purpose/legacy

    # Biodata visual style (for maximum impact and visibility)
    "biodata_style": "dramatic",  # Visual style: simple | dramatic | minimal
    "biodata_pulse_animation": True,  # Enable pulsing animation on warning icons
    "biodata_font_size": 14,  # Font size for biodata text (8-24)

    # Gentle reminder system (non-intrusive, draggable reminder with drift-back)
    "gentle_reminder_enabled": False,  # Enable gentle reminder mode (no punishment, just nudges)
    "gentle_reminder_interval": 15,  # How often to show reminder (minutes)
    "gentle_reminder_drift_enabled": True,  # Enable gradual drift back to center
    "gentle_reminder_drift_delay": 5,  # Minutes before starting to drift back to center
    "gentle_reminder_drift_speed": 1.0,  # Drift speed in pixels per frame (0.5=slow, 2.0=fast)

    # Snooze confirmation prompt (before applying a snooze from tray/menu)
    # Master toggle (controls whether the dialog appears)
    "snooze_prompt_enabled": True,
    # Ask for reason first
    "snooze_prompt_ask_reason": True,
    # Enforce validation heuristics on the reason field
    "snooze_prompt_validation_enabled": True,
    # Require exact-typing confirmation after reason
    "snooze_prompt_exact_enabled": True,
    # Disallow paste in the exact-typing field
    "snooze_exact_prevent_paste": True,
    # Require exact case match when validating typed sentence
    "snooze_sentence_case_sensitive": True,
    # Sentences used for exact typing (picked randomly)
    "snooze_prompt_sentences": [
        "I am choosing to cause disorder.",
        "I am disrupting my focus and accepting the consequences.",
        "I am letting impulsiveness overwrite my goals.",
        "I am abandoning discipline and embracing chaos.",
    ],

    # Snooze exact-typing heuristics (hidden settings)
    "snooze_exact_min_time_seconds": 2,      # Minimum time before allowing submit
    "snooze_exact_time_per_char": 0.03,      # Additional time per character in target sentence
    "snooze_exact_min_keypress_ratio": 0.8,  # Required keypresses >= ratio * sentence length
    "snooze_exact_max_jump_chars": 3,        # Disallow inserts with >N chars in one change
    "snooze_exact_require_focus_during_typing": True,

    # Snooze validation alignment options
    # Force all spam/validation heuristics ON for snooze reason/exact entry regardless of global toggles
    "snooze_exact_force_all_heuristics": False,
    # Require a specific phrase to appear in the exact-typing sentence
    "snooze_exact_require_phrase": False,
    "snooze_exact_required_phrase": "I am snoozing",
}

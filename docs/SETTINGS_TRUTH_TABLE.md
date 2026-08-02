# Settings Truth Table

This document is the Phase 1/4 contract for FocusCheck settings. It classifies every setting family and calls out keys that are intentionally hidden, legacy-only, or not user-facing until implemented.

For exact per-key reference counts, run:

```powershell
py -3 tools\settings_inventory.py
```

Current default key count: `231`.

## Active User-Facing Families

- Core schedule/window: `interval_seconds`, `intensify_after_seconds`, `overdrive_after_seconds`, `max_intensity_level`, `always_on_top`, `center_on_show`, `modal_dialog_auto_focus`, `follow_cursor_monitor`, `specific_monitor_only`, `specific_monitor_index`, `monitoring_mode`, `ui_scale_percent`, `popup_layout_mode`.
- Prompt behavior: `anti_habit_enabled`, `randomize_buttons`, `studying_hold_ms`, `hide_wasting_button`, `encouragement_enabled`, `prompt_require_all_fields`, `require_active_task`.
- Pause/tray: `force_always_on`, `pause_when_inactive_or_lid_closed`, `pause_on_idle`, `pause_on_lid_closed`, `pause_on_lock`, `pause_on_sleep`, `inactive_as_sleep_seconds`, `pause_poll_interval_seconds`, `tray_start_stop_enabled`, `tray_settings_button_enabled`, `tray_exit_button_enabled`.
- V1 detail prompts: `wasting_prompt_ask_what`, `wasting_prompt_ask_consequences`, `wasting_prompt_validation_enabled`, `focus_prompt_ask_doing`, `focus_prompt_ask_benefits`.
- V2 prompt: `v2_force_all_validations`, `v2_question_use_window_title`, `v2_focus_requires_enter`, `v2_hide_prompt_during_intervention`.
- Spam/challenge validation: all `spam_*` keys, all active `challenge_*` frequency/minimum/master keys, and individual `challenge_studying_*_enabled` / `challenge_wasting_*_enabled` keys.
- Tasks/time: `tasks_analytics_timescale`, `tasks_change_counts_as_fail`, `tasks_decision_prompt_enabled`, `tasks_study_implies_fail_on_decision`, `tasks_evaluation_mode`, `tasks_decision_window_minutes`, `show_task_analytics`, all `time_info_*` keys.
- Button phrases/acronym: `custom_button_phrases_enabled`, `study_phrase_*`, `waste_phrase_*`, `phrase_acronym_*`.
- Alerts/overdrive/audio: all `overdrive_stage4_*`, `overdrive_stage5_*`, `jiggle_style`, `disable_jiggling`, `enable_intensity_*`, `enable_overdrive_*`, `audio_*`.
- Snooze: `snooze_prompt_enabled`, `snooze_prompt_ask_reason`, `snooze_prompt_validation_enabled`, `snooze_prompt_exact_enabled`, `snooze_exact_*`, `snooze_sentence_case_sensitive`, `snooze_prompt_sentences`, `snooze_reminder_*`.
- Camera/biodata: `camera_feed_*`, `camera_capture_on_click`, `camera_flip_horizontal`, `camera_device_index`, `camera_fps`, `camera_sizing_mode`, face tracking keys, manual crop keys, manual camera adjustment keys, `camera_auto_adapt`, `camera_show_face_detection`, `camera_invert_colors`, all `biodata_*`.
- Website flags: `website_flags`.

## State-Only Or Internal

- `settings_schema_version`: migration/validation state.
- `paused`: durable manual pause state.
- `snooze_until_utc`: durable snooze expiry state.
- `study_phrase_index`, `waste_phrase_index`: runtime sequential phrase state.
- `overlays_enabled`: internal intervention overlay gate. It is active but not exposed in normal settings; expose later only if users need a clear "disable intervention overlays" switch.

## Legacy/Migration-Only

- `tasks_decision_threshold_minutes`: legacy fallback for `tasks_decision_window_minutes`.
- `tasks_post_eval_minutes`: legacy fallback for `tasks_decision_window_minutes`.

These should stay hidden from UI and eventually be removed after a migration window.

## Hidden Runtime Knobs

These defaults are consumed but intentionally not normal user controls yet:

- `camera_face_max_misses`
- `camera_manual_adjustments_enabled`
- `camera_manual_brightness`
- `camera_manual_contrast`
- `camera_manual_saturation`
- `camera_manual_sharpness`
- `camera_manual_gamma`
- `camera_manual_tint`
- `camera_auto_adapt`
- `snooze_exact_min_time_seconds`
- `snooze_exact_time_per_char`
- `snooze_exact_min_keypress_ratio`
- `snooze_exact_max_jump_chars`
- `snooze_exact_require_focus_during_typing`

## Dormant Or Product Decision Required

- `webhook_url`: legacy/default key with no dispatch implementation. The Settings UI does not save edits to it; keep hidden unless webhook delivery is implemented.
- `gentle_reminder_enabled`, `gentle_reminder_interval`: no active app launcher. Hide/remove or wire `GentleReminderDialog`.
- `gentle_reminder_drift_enabled`, `gentle_reminder_drift_delay`, `gentle_reminder_drift_speed`: only read by unlaunched gentle reminder UI. Keep hidden until gentle reminders are active.

## Decisions Made In This Pass

- Pause guard behavior now relies on `PauseGuard.should_pause()` directly, so visible granular pause toggles work without being silently blocked by a hidden master switch.
- `snooze_prompt_ask_reason` and `snooze_prompt_exact_enabled` are now respected by the snooze dialog and preserved by settings save.
- `camera_face_fallback_mode` is now consumed by the camera runtime.
- The settings window no longer writes non-default `camera_adaptive_brightness_*` keys; the active runtime key is `camera_auto_adapt` from the live adjustment flow.
- The settings window no longer saves `webhook_url`; it remains a hidden legacy/default key until delivery exists.
- Supervisor startup is now the canonical startup path; tray/main startup registration writes a Run key that launches `focuscheck_supervisor.py --run`.

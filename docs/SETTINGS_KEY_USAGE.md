# Settings Key Usage

This document lists all the settings keys found in the codebase and where they are used.

## Spam Detection

- `spam_detection_enabled`: Master switch for spam detection.
  - Used in: `focuscheck/settings/gates.py`, `focuscheck/ui/dialogs/v2_prompt_dialog.py`, `focuscheck/ui/dialogs/waste_prompt_dialog.py`, `focuscheck/ui/dialogs/focus_prompt_dialog.py`, `focuscheck/ui/dialogs/snooze_prompt_dialog.py`
- `spam_gibberish_detection`: Enable gibberish detection.
  - Used in: `focuscheck/ui/dialogs/v2_prompt_dialog.py`, `focuscheck/ui/dialogs/waste_prompt_dialog.py`, `focuscheck/ui/dialogs/focus_prompt_dialog.py`, `focuscheck/ui/dialogs/snooze_prompt_dialog.py`
- `spam_min_vowel_ratio`: Minimum vowel ratio for gibberish detection.
  - Used in: `focuscheck/ui/dialogs/v2_prompt_dialog.py`, `focuscheck/ui/dialogs/waste_prompt_dialog.py`, `focuscheck/ui/dialogs/focus_prompt_dialog.py`, `focuscheck/ui/dialogs/snooze_prompt_dialog.py`
- `spam_max_vowel_ratio`: Maximum vowel ratio for gibberish detection.
  - Used in: `focuscheck/ui/dialogs/v2_prompt_dialog.py`, `focuscheck/ui/dialogs/waste_prompt_dialog.py`, `focuscheck/ui/dialogs/focus_prompt_dialog.py`, `focuscheck/ui/dialogs/snooze_prompt_dialog.py`
- `spam_min_unique_char_ratio`: Minimum unique character ratio for gibberish detection.
  - Used in: `focuscheck/ui/dialogs/v2_prompt_dialog.py`, `focuscheck/ui/dialogs/waste_prompt_dialog.py`, `focuscheck/ui/dialogs/focus_prompt_dialog.py`, `focuscheck/ui/dialogs/snooze_prompt_dialog.py`
- ... (and so on for all spam detection settings)

## Pause/Disable Controls

- `force_always_on`: Never pause for any reason when True.
  - Used in: `focuscheck/settings/gates.py`, `focuscheck/ui/guards.py`
- `pause_when_inactive_or_lid_closed`: Master toggle for pausing logic.
  - Used in: `focuscheck/settings/gates.py`, `focuscheck/ui/guards.py`, `focuscheck/app.py`
- `pause_on_idle`: Pause when user is idle.
  - Used in: `focuscheck/ui/guards.py`
- `pause_on_lid_closed`: Pause when laptop lid is closed.
  - Used in: `focuscheck/ui/guards.py`
- `pause_on_lock`: Pause when session is locked.
  - Used in: `focuscheck/ui/guards.py`
- `pause_on_sleep`: Pause during system sleep.
  - Used in: `focuscheck/ui/guards.py`

## Tray Button Visibility

- `tray_start_stop_enabled`: Enable/disable the start/stop button in the tray menu.
  - Used in: `focuscheck/settings/gates.py`, `focuscheck/system_tray.py`
- `tray_settings_button_enabled`: Enable/disable the settings button in the tray menu.
  - Used in: `focuscheck/settings/gates.py`, `focuscheck/system_tray.py`
- `tray_exit_button_enabled`: Enable/disable the exit button in the tray menu.
  - Used in: `focuscheck/settings/gates.py`, `focuscheck/system_tray.py`

## Audit Notes

The current authoritative settings classification is in `docs/SETTINGS_TRUTH_TABLE.md`.

- State-only defaults without a normal settings UI control: `paused`, `snooze_until_utc`.
- Internal/default-only keys without a settings UI control: `settings_schema_version`, `study_phrase_index`, `waste_phrase_index`.
- Legacy normalized keys without active runtime behavior: `tasks_decision_threshold_minutes`, `tasks_post_eval_minutes`.
- Defaults with no product feature consumer: `webhook_url` (preserved and validated, but hidden until delivery exists).

The authoritative regression entry point for settings semantics is:

```powershell
py -3 tools\qa_scenario_runner.py --reset
```

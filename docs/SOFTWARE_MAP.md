# FocusCheck Software Map

This document maps the extracted project by runtime phase, functional area, and important UI/backend state.

## Phase 1: Launch

- `main.py` is the primary Python entry point.
- `start_focuscheck.bat` launches `focuscheck_supervisor.py`, which then starts `main.py`.
- `Start FocusCheck.cmd` directly launches `main.py` with `pythonw`.
- `main.py --selftest` validates Windows wake/session callback wiring.
- `main.py --tray-selftest` validates optional tray imports through `tools/system_tray_selftest.py`.
- `main.py --install-startup` and `main.py --uninstall-startup` delegate Windows startup registration to `focuscheck.platform_specific`; the Run key targets `focuscheck_supervisor.py --run`.

## Phase 2: Single Instance And Supervision

- `focuscheck.utils.file_ops.acquire_single_instance()` prevents duplicate app instances on Windows using a mutex.
- `focuscheck_supervisor.py` restarts the app if it exits unexpectedly.
- `focuscheck_supervisor.py` uses a supervisor lock file to avoid duplicate watchdog loops.
- Tray/app quit writes an intentional stop file when supervised so the watchdog does not relaunch the app after a user-requested exit.
- The app writes heartbeat data so the supervisor can tell whether the UI process is alive.
- Startup commands are composed by the platform layer and use the supervisor as the canonical release path.

## Phase 3: Settings And Gates

- `focuscheck.settings.defaults.DEFAULT_SETTINGS` defines baseline behavior.
- `focuscheck.settings.manager` loads, saves, and normalizes user settings.
- `focuscheck.settings.registry` documents setting keys, types, defaults, and descriptions.
- `focuscheck.settings.gates` centralizes feature switches for spam detection, tray controls, settings visibility, pause detection, and overlays.
- Important state keys include `paused`, `force_always_on`, `pause_when_inactive_or_lid_closed`, monitoring mode, reminder interval, prompt settings, spam settings, challenge settings, camera settings, and overdrive settings.

## Phase 4: App Coordination

- `focuscheck.app.App` owns the Tk root, settings, task DB, monitoring engine, tray, prompt scheduling, pause guard, and shutdown path.
- Initial monitoring state is derived from persisted settings and environment overrides.
- The app schedules reminder checks with Tk timers.
- The app suppresses prompts while manually paused, snoozed, idle-paused, locked, sleeping, or lid-closed depending on settings.
- The app writes file heartbeats and startup diagnostics.

## Phase 5: Monitoring

- `focuscheck.monitoring.EngineV1` handles basic reminder timing and app state checks.
- `focuscheck.monitoring.EngineV2` adds richer activity/browser classification and waste detection paths.
- `focuscheck.platform_specific.activity_probe`, `window_enumeration`, `browser_info`, `browser_tabs`, and `cdp_browser` provide Windows/browser context when available.
- Engine output can trigger normal check-ins, waste prompts, website flagging, or intervention flows.

## Phase 6: Tray And User Control

- `focuscheck.system_tray.SystemTray` provides optional pystray integration.
- Tray state supports start reminders, stop reminders, toggle pause, open settings, open logs, open data folder, prompt now, snooze, and exit.
- If pystray or Pillow are missing, tray setup is expected to fail gracefully without stopping the core app.
- Manual pause is persisted via the `paused` setting.
- Snooze pauses reminders temporarily and schedules automatic unpause.

## Phase 7: Prompt UI States

- `focuscheck.ui.dialogs.PromptDialog` is the main check-in prompt.
- `V2PromptDialog` is the richer second-generation prompt path.
- Studying/focus state can open `FocusPromptDialog`.
- Waste/distraction state can open `WastePromptDialog`.
- Snooze confirmation can open `SnoozePromptDialog`.
- Snooze reminder popups use `SnoozeReminderDialog`.
- `GentleReminderDialog` exists in code but has no active launcher path; it is dormant until deliberately wired or archived.
- Prompt behavior can escalate through challenge validation, spam detection, intervention wizard, audio alarm, overlays, dimming, click-through overlays, camera feed, and task-management panels.

## Phase 8: Validation And Anti-Spam

- `focuscheck.ui.dialogs.spam_detection.SpamDetector` implements local response-quality checks.
- `focuscheck.settings.gates.is_spam_detection_enabled()` controls whether spam detection runs.
- Dialog validation can reject empty, vague, repetitive, gibberish, too-fast, banned-word, or challenge-failing responses depending on settings.
- `tests/test_validation.py` currently tests the canonical spam gate.

## Phase 9: Tasks And Persistence

- `focuscheck.database.TaskDB` stores task state in SQLite.
- CSV/JSONL-style logs track focus prompts, waste logs, doctor/anomaly information, and app events.
- Task UI includes task entry, task change, task history, inline task panels, due dates, completion, and analytics refresh.
- Path helpers route user data to `%APPDATA%/FocusCheck` on Windows unless `FOCUS_DATA_DIR` overrides it.

## Phase 10: Settings UI

- `focuscheck.ui.windows.SettingsWindow` is the active settings window.
- Settings tabs live under `focuscheck.ui.settings_tabs`.
- Major tab areas include general behavior, validation, spam detection, challenges, website flags, alerts, pause controls, camera controls, overdrive controls, and tray controls.
- `CameraTestWindow`, `CameraAdjustmentWindow`, and `CropAdjustmentWindow` support camera preview/crop calibration.

## Phase 11: Platform Integration

- `focuscheck.platform_specific.startup` installs/removes Windows startup integration.
- `focuscheck.platform_specific.windows` handles Windows wake/session events, click-through overlays, icon/resource helpers, and window behavior.
- Browser/window helpers collect active app/window/tab context when supported.
- Non-Windows paths generally degrade by disabling Windows-only behavior.

## Phase 12: Reference Ports

- `ports/csharp-wpf/` is an experimental C# WPF port, not the active runtime.
- `ports/ios/` is an iOS/reference implementation with Swift app, widget, notifications, activity monitoring placeholders, spam/challenge utilities, and psychology/setup docs.
- Ports should not be treated as canonical behavior unless a feature is explicitly being ported.

## Phase 13: Archive And Non-Runtime Material

- `_archive/legacy/` contains old code, backup UI files, exploratory implementations, and pre-cleanup archive folders.
- `_archive/analysis/` contains generated analysis outputs.
- `_archive/reference/` contains reference dumps.
- `_archive/packages/` stores copied zip packages.
- `_archive/scratch/` stores generated logs and temporary outputs.
- `_archive/generated/` stores generated files that are useful to keep but should not live in active runtime folders.

## Current Validation Commands

- `py -3 -m compileall main.py focuscheck focuscheck_supervisor.py tests tools`
- `py -3 tests\test_validation.py`
- `py -3 main.py --selftest`
- `py -3 main.py --tray-selftest`
- `run_test.bat` launches `tools\manual_snooze_dialog.py`, an interactive/manual Tk snooze dialog smoke test, and writes output to `_archive\scratch\test_output.log`.

## Architecture Notes

- The Python Tk app is the product source of truth.
- `focuscheck/app.py` is large and coordinates too many responsibilities; future polishing should split scheduler, tray actions, prompt orchestration, and lifecycle/heartbeat handling.
- `focuscheck/ui/dialogs/prompt_dialog.py` and its mixins are the densest UI area; future polishing should focus there after stabilizing tests.
- Settings are reasonably centralized, but all feature decisions should continue moving into `focuscheck.settings.gates`.
- Active root should stay small: launchers, entry points, package dirs, tests, tools, docs, ports, archive, dependency files.

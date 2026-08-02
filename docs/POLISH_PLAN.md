# FocusCheck Polish Plan

This plan is the working checklist for systematically hardening and completing FocusCheck. It combines local validation, Codex subagent audits, and the attempted Gemini audit. Gemini CLI was unavailable because `gemini --yolo` failed with an `IneligibleTierError`; the failure logs are preserved under `_archive/analysis/gemini/`.

## Phase 0: Baseline And Quality Gate

- Status: in progress.
- Baseline commit: `4f400d9` (`Baseline organized FocusCheck extraction`).
- Required command gate:
  - `py -3 -m compileall main.py focuscheck focuscheck_supervisor.py tests tools`
  - `py -3 -m unittest discover -s tests -p "test*.py"`
  - `py -3 main.py --selftest`
  - `py -3 main.py --tray-selftest`
- Keep manual GUI smoke tests in `tools/`, not `tests/`.

## Phase 1: Runtime Safety

- Fix settings save atomicity on Windows.
- Stop normal lock/sleep events from terminating the app.
- Normalize task due datetimes so naïve stored values do not silently bypass timeout handling.
- Keep optional dependencies optional at import time, especially OpenCV/camera paths.
- Add regression tests for each runtime safety fix.

## Phase 2: Settings And State Semantics

- Status: completed for the current hardening pass.
- Complete or auto-fill `SETTINGS_REGISTRY` from `DEFAULT_SETTINGS` so diagnostics identify real unknown keys.
- Add missing defaults for feature gates such as `overlays_enabled`.
- Separate durable manual pause/stopped state from transient startup/supervisor force-start behavior.
- Add tests for `validate_settings`, feature gates, startup state resolution, and pause/snooze persistence.

## Phase 3: App Lifecycle And Scheduling

- Status: completed for the current hardening pass.
- Make prompt completion idempotent so multiple callbacks cannot schedule duplicate next prompts.
- Add a common prompt lifecycle interface for cleanup before regeneration, settings changes, or snooze.
- Ensure V1 and V2 prompts both expose compatible timer/overlay cleanup behavior.
- Add tests around prompt active/stale/closed transitions with fake prompt objects.

## Phase 4: UI/Dialog Polish

- Status: completed for the current hardening pass.
- Reduce eager imports from `focuscheck.ui` and `focuscheck.ui.dialogs` to narrow blast radius.
- Fix V2 intervention cancellation so failed/cancelled intervention does not restore and immediately close contradictory UI.
- Move task due parsing to a shared pure helper instead of calling `TaskEntryDialog._parse_due(self=None, ...)`.
- Respect `always_on_top` consistently in `SnoozePromptDialog`.
- Decide whether `V2SubPopupDialog` and `GentleReminderDialog` are active features or archive candidates.

## Phase 5: Persistence And Data Integrity

- Status: completed for the current hardening pass.
- Add `TaskDB` tests for schema creation, active task lifecycle, status transitions, history, analytics, waste/focus event recording, and overdue handling.
- Make CSV/JSONL write failures observable to callers or explicitly documented as best-effort.
- Add temp-directory based tests for path helpers and persistence modules.

## Phase 6: Monitoring And Platform Integration

- Status: completed for the current hardening pass.
- Add tests for `EngineV2` URL/domain matching, website flag cooldowns, severity metadata, and disabled flags.
- Add tests for startup command composition and call signatures from CLI and tray.
- Keep Windows-only behavior guarded and non-Windows-safe.

## Phase 7: Product Completion Pass

- Status: completed for the current hardening pass.
- Walk every user operation: launch, tray, settings, pause, snooze, prompt now, prompt answers, waste/focus paths, task operations, intervention, camera, overlays, browser flags, startup install/uninstall, shutdown.
- For each operation, document expected states, add a smoke/manual repro if GUI-bound, and automate pure logic where possible.
- Only after state coverage is stable, do visual/UI polish.
- Operation/state coverage lives in `docs/OPERATIONS_MATRIX.md`.

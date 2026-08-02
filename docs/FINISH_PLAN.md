# FocusCheck Finish Plan

This is the practical plan to finish the current program without wandering into endless cleanup. The goal is a stable, usable Windows app with documented behavior, automated regression coverage for core logic, and manual verification for UI/OS behavior that cannot be trusted from unit tests alone.

## Current Position

- The repo is organized and committed.
- Core tests pass.
- An isolated QA harness exists: `tools/qa_scenario_runner.py`.
- Phase 1-4 hardening now has concrete docs/tests: `docs/OPERATIONS_MATRIX.md`, `docs/SETTINGS_TRUTH_TABLE.md`, and the QA harness.
- The app has known complex surfaces: Tk prompts, tray, Windows startup, pause/snooze, V1/V2 prompt logic, settings, task DB, CSV logs, camera, overlays, and browser flag monitoring.
- Antigravity CLI is installed and usable through `agy`; use it for extra audit passes, not as the source of truth.

## Rule For Finishing

Do not start a full rewrite yet. Finish by stabilizing the existing product until the behavior is explicit and testable. If a module is too messy to safely patch, replace that module behind the same interface.

## Phase 1: Lock The Product Contract

Objective: define what the app is supposed to do before changing more behavior.

Tasks:

- Expand `docs/OPERATIONS_MATRIX.md` until every user operation has expected states and failure states.
- Finish `docs/SETTINGS_KEY_USAGE.md` so every setting is classified as active, state-only, legacy, dead, or needs decision.
- Add an explicit list of unsupported/dead features to remove or hide from UI.
- Use `agy --mode plan --print` for a second-opinion audit of the operation matrix and settings map.

Acceptance:

- Every UI button/menu/action is listed.
- Every setting key has a status.
- Dead settings/features are not silently presented as working features.

## Phase 2: Complete The QA Harness

Objective: make non-disruptive testing the default way to validate the app.

Tasks:

- Add QA scenarios for prompt scheduling, pause/resume/snooze, prompt-now, startup state, and settings save/reload.
- Add withdrawn Tk smoke tests for each small dialog.
- Add pure tests for settings tabs where possible: create tab, change variables, save payload.
- Add a QA report section for manual-only checks with pass/fail notes.
- Keep `_qa_runtime/` ignored.

Acceptance:

- `py -3 tools\qa_scenario_runner.py --reset` returns `qa_failures=0`.
- The generated report clearly shows covered and uncovered areas.
- Any uncovered area is documented as manual-only or future work.

## Phase 3: Fix High-Risk User Flows

Objective: remove the bugs that make the app feel broken or hostile.

Tasks:

- Run through task entry/change/complete/fail flows.
- Run V1 prompt states: studying, wasting, required task, focus detail, waste detail, challenge, spam rejection.
- Run V2 prompt states: answer/no, answer/yes intervention, failed intervention, Escape/close prevention.
- Run tray states: pause, resume, snooze, duplicate snooze, prompt-now, settings, exit disabled.
- Fix every case where Enter does nothing, close bypasses validation, state is contradictory, or logs are silently wrong.

Acceptance:

- No prompt can disappear without a valid state transition.
- No tray action leaves the app in a contradictory state.
- No task operation creates hidden duplicate active tasks.
- All fixed flows have either an automated test or a manual checklist entry.

## Phase 4: Settings Truth Pass

Objective: make settings trustworthy.

Tasks:

- For each settings tab, verify every control saves the intended key.
- For each saved key, verify the runtime actually consumes it.
- Hide or label dead settings: `webhook_url`, `gentle_reminder_*`, and other no-consumer keys unless implemented.
- Decide whether legacy task decision keys stay as migration-only or are removed from visible UI.
- Add settings round-trip tests for high-risk booleans and numeric clamps.

Acceptance:

- Every visible setting does something real.
- Every state-only setting is not exposed as normal user config.
- Invalid settings files recover safely.

## Phase 5: UI Polish And Consolidation

Objective: make the active UI coherent after behavior is stable.

Status: completed for the release-candidate pass. Remaining duplicated task-entry UI is documented as future consolidation, not a blocker.

Tasks:

- Standardize Enter/Escape behavior across all dialogs.
- Standardize topmost/focus behavior so the app interrupts only when intended.
- Consolidate duplicated dialog code where safe.
- Remove or archive unused dialogs only after confirming no runtime path uses them.
- Improve copy and error messages for required fields, validation failures, and snooze/intervention failures.

Acceptance:

- Dialog behavior is predictable.
- UI text explains what happened and what to do next.
- Unused UI code is either removed or explicitly documented.

## Phase 6: Windows Integration Pass

Objective: prove the app behaves on the real target OS.

Status: completed for code-level lifecycle hardening. Manual Windows shell checks remain in `docs/RELEASE_CHECKLIST.md`.

Tasks:

- Verify startup install/uninstall.
- Verify direct launch and supervisor launch.
- Verify single-instance behavior.
- Verify lock/sleep/idle pause behavior.
- Verify tray icon/menu under normal Windows shell.
- Verify app shutdown cleans tray, timers, prompts, and heartbeat.

Acceptance:

- Windows lifecycle behavior is documented with exact commands.
- Startup does not point to a test runner or temporary path.
- Shutdown leaves no zombie app process.

## Phase 7: Optional Feature Decisions

Objective: stop pretending unfinished features are complete.

Status: completed for release-candidate scope. Dormant webhook and gentle-reminder paths are hidden/documented rather than presented as finished features.

Tasks:

- Camera feed: either validate dependency-missing fallback and core behavior, or disable in UI by default.
- Overlays/stage5: verify manually on Windows or gate behind an explicit experimental label.
- Website flags: verify real browser/window detection, not just pure URL matching.
- Gentle reminder: implement it or remove/hide the settings.
- Webhook: implement it or remove/hide the setting.

Acceptance:

- Experimental features are labeled.
- Dead features are gone from the user-facing UI.
- Optional dependencies fail gracefully.

## Phase 8: Release Candidate

Objective: produce a clean checkpoint that can be run confidently.

Status: completed for this release-candidate checkpoint. Manual Windows shell checks remain required before external distribution.

Tasks:

- Run full validation:

```powershell
py -3 -m compileall main.py focuscheck focuscheck_supervisor.py tests tools
py -3 -m unittest discover -s tests -p "test*.py"
py -3 tools\qa_scenario_runner.py --reset
py -3 main.py --selftest
py -3 main.py --tray-selftest
```

- Run the manual checklist from `docs/OPERATIONS_MATRIX.md`.
- Update README with final run/test instructions.
- Commit the release candidate.

Acceptance:

- Git working tree is clean.
- Automated validation passes.
- Manual-only scenarios are either passed or listed as known limitations.

## Rewrite Decision

Only start a v3 rewrite after Phase 1 through Phase 4 are complete. If rewriting, use a strangler approach:

- Keep existing settings/data compatibility.
- Rewrite pure core first: settings, scheduler, pause/snooze, task lifecycle, logging.
- Replace UI adapters one by one.
- Keep the old app runnable until the new path passes the same operation matrix.

## Immediate Next Work

1. Continue expanding QA harness coverage for tray/menu gates, settings apply/reload, and V1 prompt keyboard paths.
2. Run a real manual UI pass and fix every discovered broken state.
3. Verify Windows startup/tray/lock/sleep behavior manually from `docs/RELEASE_CHECKLIST.md`.
4. Only then decide whether to rewrite larger modules.

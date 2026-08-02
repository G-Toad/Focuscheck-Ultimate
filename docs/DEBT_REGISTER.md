# Debt Register

This register separates known defects, design debt, dormant features, and uncertain behaviour. Do not use it as permission for broad cleanup.

## Confirmed Defects

- None currently open from the latest automated validation pass.

## High-Risk Behaviour Needing More Harness Coverage

- Supervisor unexpected child crash/restart has fake-process harness coverage; live child kill/restart remains a manual Windows gate.
- Real tray menu shell behaviour still needs manual Windows QA; fake command-handler coverage exists.
- Sleep/resume and workstation lock/unlock native notifications still need manual Windows QA or a future injectable event source.
- Website flags still need a manual browser matrix; fake active-window provider flow and sequence tests exist.
- Intervention overlay behaviour needs monitor-safe manual testing.

## Design Debt

- `focuscheck.app.App` coordinates too many responsibilities: scheduling, tray, settings application, prompt lifecycle, task DB, heartbeat, and platform watchers.
- V1/V2 prompt flows share concepts but have divergent implementation details.
- Inline task-entry/task-change panels now share payload construction with standalone dialogs; visual layout duplication remains.
- Settings UI saves a very large payload and mixes active controls, legacy settings, and hidden runtime state.
- Platform-specific Windows behaviours are partially abstracted but still leak into UI/application coordination.

## Dormant Or Product-Decision Features

- `GentleReminderDialog` is intentionally deferred and has no active launcher path.
- `webhook_url` is intentionally deferred legacy/default state with no dispatch implementation and is not saved from Settings.
- Gentle-reminder settings remain deferred legacy/default keys and are not saved from Settings.
- Some legacy task threshold keys exist for migration compatibility.

## Uncertain Behaviour To Characterize Before Refactor

- Stage 5 settings are validation-covered, but the complete user-facing product contract still needs manual confirmation.
- Direct `Start FocusCheck.cmd` is now characterized as a direct child launch, but whether it should remain supported long term is still a product decision.
- Whether camera preview should be allowed to remain open while Settings closes.
- Whether V2 should become the default monitoring mode after manual QA.
- How aggressive website-flag interventions should be for severity 1 and 2.

## Refactor Order

1. Continue desktop-safe QA harness coverage for remaining prompt/settings flows.
2. Supervisor abnormal-process recovery and live Windows startup/tray verification.
3. Native lock, sleep, resume, and workstation notification verification.
4. V1/V2 interventions, snooze, and settings-state transitions.
5. Website-flag behaviour.
6. Task-entry/task-change UI consolidation.
7. Gentle reminder product decision.
8. Webhook product decision.
9. General UI copy/layout cleanup.

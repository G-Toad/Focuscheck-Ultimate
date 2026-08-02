# Slice Completion Status

This document closes the nine repo-defined finish slices into one of three states:
automated, deferred by explicit product decision, or manual Windows gated.

## Completed With Automated Evidence

1. Desktop-safe QA harness coverage for prompt/settings flows.
   Evidence: `tools/qa_scenario_runner.py`, `tests/test_settings_window.py`, `tests/test_dialog_keyboard.py`.

2. V1/V2 intervention, snooze, and settings-state transitions.
   Evidence: `tests/test_v2_flows.py`, `tests/test_settings_state.py`, `tests/test_dialog_keyboard.py`, QA runner prompt scenarios.

3. Website-flag behaviour in deterministic harness.
   Evidence: exact/subdomain/cooldown/suffix tests plus fake active-window provider tests.

4. Task-entry/task-change payload consolidation.
   Evidence: `focuscheck.utils.task_payload.build_task_payload` is shared by standalone dialogs and inline prompt forms.

5. General UI/runtime polish that can be checked safely.
   Evidence: explicit keyboard handlers for V2 sub-popup, launch-script contracts, settings save payload tests, compile and selftests.

## Completed As Deferred Product Decisions

6. Gentle reminder.
   Decision: keep gentle-reminder settings optional and expose them through schema-generated controls; launch and shutdown behavior is covered by App lifecycle tests.
   Evidence: `gentle_reminder_*` is persisted by the generated settings binding and the scheduler lifecycle regression covers the dialog path.

7. Webhook.
   Decision: keep `webhook_url` as hidden legacy/default state until a real dispatch implementation exists.
   Evidence: settings save payload excludes `webhook_url`; release docs identify it as deferred.

## Manual Windows Gates

8. Supervisor/startup/tray/native session behaviour.
   Automated evidence exists for locks, command composition, fake tray callbacks, intentional exit, and crash restart.
   Manual evidence still required: live tray shell, Run key inspection, duplicate supervisor launch, child kill/restart, tray exit without restart.

9. Native lock/sleep/resume/browser/overlay behaviour.
   Automated evidence exists for fake guard events, fake activity provider, and intervention state transitions.
   Manual evidence still required: real workstation lock/unlock, sleep/resume, supported-browser active tab matrix, and multi-monitor overlays.

## Verification Command

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify.ps1
```

The verifier proves the automated portion of these slices. The manual gates above remain physical Windows checks and cannot be proven by simulation alone.

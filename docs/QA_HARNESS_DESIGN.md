# Desktop-Safe QA Harness Design

The goal is to test Windows-heavy behaviour without disrupting the real desktop or mutating the live profile.

## Principles

- Use fake adapters for OS, tray, timers, dialogs, process control, browser probes, and settings storage.
- Keep live UI launches out of automated verification.
- Feed synthetic event sequences into app/supervisor logic.
- Write scenario evidence to `_qa_runtime`.
- Treat manual Windows checks as a separate release gate.

## Boundaries To Introduce

- `StartupAdapter`: install, uninstall, query startup entries.
- `ProcessAdapter`: launch child, poll exit, terminate, kill tree.
- `SupervisorLockStore`: acquire, reject duplicate, recover stale lock.
- `Clock`: wall time, monotonic time, sleep/wait.
- `TrayAdapter`: menu command dispatch without pystray/native shell.
- `DialogPresenter`: prompt, messagebox, intervention selection, subpopup.
- `ActivityProvider`: active window, browser URL/title, process metadata.
- `GuardEventSource`: lock, unlock, sleep, resume, idle, lid-closed.
- `SettingsStore`: load/save/normalize against temp data.
- `NotificationAdapter`: audio, visual, toast, overlay side effects.

## Scenario Examples

```text
Start supervisor
Start child
Simulate child crash
Confirm restart occurs
Simulate intentional tray exit
Confirm restart does not occur
Start again
Simulate workstation lock
Simulate resume
Confirm intervention state remains coherent
```

```text
Load settings with V2 mode and website flag
Fake active browser URL reddit.com
Run subpopup tick
Confirm severity 3 starts intervention
Confirm cooldown saved once
Confirm app intervention state resets
```

```text
Open Settings through fake tray
Change pause and snooze controls
Save settings
Reload settings
Confirm only active UI keys changed
```

## Implementation Shape

1. Define narrow protocols or small classes for the boundaries above.
2. Keep production adapters thin wrappers around current modules.
3. Add fake adapters under `tests/fakes/` or `tools/qa_fakes/`.
4. Extend `tools/qa_scenario_runner.py` to run named scenario sequences.
5. Add a machine-readable report with pass/fail, logs, and final state snapshots.

## Non-Goals

- Do not replace manual Windows QA.
- Do not automate real Run-key writes in normal test runs.
- Do not show real Tk prompts during default verification.
- Do not introduce a large framework until small adapters prove useful.


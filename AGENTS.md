# FocusCheck Agent Instructions

These instructions are persistent rules for AI agents working in this repository.

## Product Summary

FocusCheck is a Windows-focused Tkinter desktop app that periodically checks whether the user is focused. It includes tray controls, reminders, snooze, task tracking, V1/V2 prompt flows, intervention overlays, website flags, camera-related optional flows, and a supervisor process.

## Active Runtime Entry Points

- `main.py`: application CLI and Tk app entry point.
- `focuscheck_supervisor.py`: watchdog launcher and canonical startup target.
- `start_focuscheck.bat`: preferred manual Windows launch path through the supervisor.
- `Start FocusCheck.cmd`: direct lightweight launch path, not the release startup path.

## Repository Layout

- `focuscheck/`: active Python package.
- `focuscheck/app.py`: Tk root, scheduler, tray coordination, prompt lifecycle, pause/snooze state.
- `focuscheck/monitoring/`: V1/V2 monitoring engines.
- `focuscheck/platform_specific/`: Windows startup, activity, tray, and platform probes.
- `focuscheck/ui/`: Settings windows, dialogs, camera UI, prompt UI.
- `focuscheck/database/`: Task and logging persistence.
- `focuscheck/settings/`: defaults, normalization, gates, registry.
- `tests/`: automated tests.
- `tools/`: verification and QA utilities.
- `docs/`: architecture, behaviour, release, QA, and debt documentation.
- `_archive/`, `ports/`: non-primary material. Do not modify unless explicitly requested.

## Windows And Tkinter Constraints

- Treat supervisor, tray, startup, lock/sleep/resume, and intervention paths as high risk.
- Tk widgets and message boxes must run on the Tk/UI thread. Tray callbacks should dispatch into the Tk loop before touching Tk objects.
- Avoid launching the production UI during automated validation. Use `tools/qa_scenario_runner.py` and tests first.
- Only run the real app when the user explicitly asks for a manual launch or smoke test.
- Startup registration must launch `focuscheck_supervisor.py --run --base-dir ...`, not direct `main.py`.
- User-requested tray/app exit while supervised must not be treated as a crash. It must not cause supervisor restart.
- Duplicate supervisor attempts must not create multiple restart loops.
- Never alter live `%APPDATA%\FocusCheck` data in automated tests unless the user explicitly asks for live manual testing.

## Persistent State

- Normal runtime data is under `%APPDATA%\FocusCheck` or `%LOCALAPPDATA%\FocusCheck`.
- Tests and harnesses should use `FOCUS_DATA_DIR` or `_qa_runtime` where possible.
- Settings are normalized through `focuscheck.settings.manager`.
- Unknown settings should not be casually deleted; classify or migrate them deliberately.

## Required Verification

Use the single deterministic entry point where possible:

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify.ps1
```

Equivalent manual stages:

```powershell
py -3 -m compileall main.py focuscheck focuscheck_supervisor.py tests tools
py -3 -m unittest discover -s tests -p "test*.py"
py -3 tools\qa_scenario_runner.py --reset
py -3 main.py --selftest
py -3 main.py --tray-selftest
py -3 tools\settings_inventory.py
```

Manual Windows QA remains required for startup registry, tray shell behaviour, process termination, workstation lock/unlock, sleep/resume, and real browser website flags.

## Completion Criteria

A task is complete only when:

- The observable behaviour requested by the issue is implemented.
- Existing documented behaviours in `docs/BEHAVIOUR_SPEC.md` are preserved.
- Tests or QA scenarios were added or strengthened when feasible.
- `tools\verify.ps1` passes, or any skipped/failing stage is explicitly justified.
- The diff has been reviewed for unrelated cleanup, process lifecycle races, UI-thread violations, and swallowed errors.
- Remaining manual Windows checks are listed when they cannot be automated.

## Forbidden Without Explicit User Approval

- Wholesale rewrite.
- Broad cleanup mixed into a bug fix.
- New runtime dependencies without a concrete benefit and fallback plan.
- Changing startup, supervisor, tray, sleep/resume, or intervention semantics without updating `docs/BEHAVIOUR_SPEC.md` and tests.
- Running destructive Git commands such as reset/checkout of user work.
- Running unattended production app launches as part of automated verification.
- Reformatting large files unrelated to the assigned task.

## Agent Workflow

- Start complex tasks with a read-only plan.
- Prefer small bounded issues with one observable outcome.
- Add characterization tests before refactoring high-risk behaviour.
- Use subagents only for independent bounded audits, test/log analysis, or isolated implementation scopes.
- Do not allow multiple agents to edit the same high-risk module concurrently.
- Use an independent review pass for substantial diffs.
- Flag unknown behaviour instead of inventing intended behaviour.


# FocusCheck

FocusCheck is a Windows-focused desktop app that periodically checks whether the user is focused, prompts for reflection, tracks tasks/history, and can escalate prompts with validation, challenges, camera-based flows, website flags, and anti-habit UI behavior.

## Active Layout

- `main.py` - primary app entry point and CLI/selftest handling.
- `focuscheck/` - active Python package.
- `focuscheck_supervisor.py` - watchdog process that keeps FocusCheck alive and is the canonical startup target.
- `start_focuscheck.bat` - preferred Windows launcher through the supervisor.
- `Start FocusCheck.cmd` - direct lightweight launcher.
- `tests/` - root-level test scripts.
- `tools/` - manual/selftest tools.
- `docs/` - product notes, version 2 plans, settings notes, and repro checklists.
- `ports/` - non-primary ports/prototypes, currently C# WPF and iOS.
- `_archive/` - preserved scratch, legacy, generated, analysis, reference, and packaged artifacts.

## Current Product State

- Version 1 monitoring remains available through `EngineV1`.
- Version 2 monitoring scaffolding exists through `EngineV2`.
- Settings include monitoring mode, validation controls, website flags, spam detection, challenges, camera feed behavior, pause behavior, and multi-stage overdrive behavior.
- Browser/window metadata support is Windows-oriented and best-effort.
- Runtime state is stored under `%APPDATA%`/`%LOCALAPPDATA%` FocusCheck paths.

## Common Commands

```bat
start_focuscheck.bat
```

```powershell
py -3 main.py --selftest
py -3 tests\test_validation.py
py -3 -m unittest discover -s tests -p "test*.py"
run_test.bat
```

Supervisor:

```powershell
py -3 focuscheck_supervisor.py --run
py -3 focuscheck_supervisor.py --install-startup
py -3 focuscheck_supervisor.py --uninstall-startup
py -3 main.py --install-startup
py -3 main.py --uninstall-startup
```

`main.py --install-startup` and the tray startup menu write a Current User Run key that launches `focuscheck_supervisor.py --run --base-dir ...`, not a direct unsupervised `main.py` process.

## Dependencies

Core UI uses the Python standard library `tkinter`. Optional/full-feature paths use packages listed in `requirements.txt`, especially tray icon and camera/image support.

## Notes

- Keep active code in `focuscheck/`, `main.py`, and `focuscheck_supervisor.py`.
- Keep root free of generated logs, scratch files, copied zips, and one-off analysis output.
- Use `docs/specs/version2-original-spec.txt` for the preserved original v2 spec.
- Use `docs/REPOSITORY_LAYOUT.md` and `docs/SOFTWARE_MAP.md` for the current repo structure and runtime map.
- Use `AGENTS.md` for persistent agent instructions and `PLANS.md` for high-risk execution plans.
- Use `docs/ARCHITECTURE_CURRENT.md`, `docs/BEHAVIOUR_SPEC.md`, `docs/TEST_MATRIX.md`, and `docs/DEBT_REGISTER.md` before significant refurbishment work.
- Use `docs/OPERATIONS_MATRIX.md` for the user-operation/state verification checklist.
- Use `docs/QA_HARNESS.md` and `tools/qa_scenario_runner.py` for isolated, non-live-profile QA runs.
- Use `docs/FINISH_PLAN.md` and `docs/SETTINGS_TRUTH_TABLE.md` for the product completion contract.
- Use `docs/RELEASE_CHECKLIST.md` before treating a checkpoint as release-ready.
- Use `tools/verify.ps1` as the deterministic verification entry point.
- `run_test.bat` launches the manual snooze dialog smoke test; automated tests live under `tests/`.

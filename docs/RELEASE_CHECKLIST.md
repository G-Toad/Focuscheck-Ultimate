# Release Checklist

Use this as the Phase 8 release-candidate gate.

## Automated Checks

Run from the repo root:

```powershell
py -3 -m compileall main.py focuscheck focuscheck_supervisor.py tests tools
py -3 -m unittest discover -s tests -p "test*.py"
py -3 tools\qa_scenario_runner.py --reset
py -3 main.py --selftest
py -3 main.py --tray-selftest
```

If `pytest` is not installed, use `unittest`; this repo does not require pytest for the current test suite.

## Windows Manual Checks

- Use `docs/SLICE_COMPLETION_STATUS.md` as the slice-level closeout map.
- Launch with `start_focuscheck.bat`; confirm the supervisor starts `main.py` and writes `focuscheck_supervisor.log`.
- With a persisted manual pause, confirm normal launch preserves it; separately run `--force-start` and confirm the explicit override is limited to that invocation.
- Use tray Exit while supervised; confirm the app exits and the supervisor does not restart it.
- Start a second supervisor; confirm it exits with a "Supervisor already running" message instead of launching a restart loop.
- Use tray "Enable supervised run on startup"; confirm the Current User Run key points to `focuscheck_supervisor.py --run --base-dir`.
- Disable startup from the tray; confirm the Run key is removed.
- Lock, unlock, sleep, and resume Windows; confirm pause/resume behavior follows the Settings toggles.
- Trigger Prompt Now, Snooze, Settings, Logs, Data Folder, and Exit from the tray.
- In V2 mode, add a website flag such as `reddit.com`, visit the site in a supported browser, and confirm the warning/intervention path.
- Run `docs/MANUAL_REPRO_CHECKLIST.md` for intervention cancel/verify paths.

## Release Blockers

- Any crash on launch, Settings save, Prompt Now, Snooze, tray Exit, or startup install/uninstall.
- Supervisor relaunches the app after a user-requested tray Exit.
- Startup command points at `main.py`, a test runner, a temporary path, or a stale extracted folder.
- Website flags or intervention overlays claim to be enabled but cannot be verified manually.

## Known Deferred Work

- `webhook_url` is intentionally deferred hidden legacy/default state; there is no webhook dispatch implementation.
- Inline and standalone task forms now share payload construction; visual/layout duplication remains a lower-risk UI refactor.

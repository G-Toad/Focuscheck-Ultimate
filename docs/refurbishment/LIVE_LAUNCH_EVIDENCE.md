# Live Launch Evidence

This is direct Windows-process evidence, separate from the bounded unit/self-test runner and the manual UI matrix.

## Run

Command:

```powershell
$env:FOCUS_DATA_DIR = "$env:TEMP\FocusCheck_live_app_<unique>"
$env:FOCUSCHECK_START_STOP_MODE = "paused"
$env:FOCUSCHECK_FORCE_STARTED = ""
python main.py --run-seconds=3
```

Observed on 2026-08-03 (historical run):

- Process exit code: `0`.
- Data root was a unique `%TEMP%` directory, not `%APPDATA%` and not the repository.
- The run created `focus_app.log`, `focus_log.csv`, `focus_settings.json`, `focus_tasks.sqlite3`, `hb.txt`, `runtime_state.jsonl`, and `structured_events.jsonl`.
- No interactive tray, prompt, browser, lock/sleep/resume, startup-registry, or packaged-installer behavior was claimed by this run.

This evidence supports direct launch, isolated path selection, basic persistence initialization, heartbeat publication, and clean timed shutdown only.

Latest isolated rerun on 2026-08-03:

```powershell
$env:FOCUS_DATA_DIR = "$env:TEMP\FocusCheckDirectLaunch_<unique>"
py -3 -c "from focuscheck.settings import save_settings; save_settings({'paused': True, 'snooze_until_utc': ''})"
$env:FOCUSCHECK_FORCE_STARTED = "1" # legacy variable; must be ignored
py -3 main.py --run-seconds=3
py -3 -c "from focuscheck.settings import load_settings; print(load_settings().get('paused'))"
```

- Process exit code: `0`; elapsed time was approximately `4.1` seconds.
- The unique temporary root contained `focus_app.log`, `focus_log.csv`, `focus_settings.json.lock`, `focus_tasks.sqlite3`, `hb.txt`, `runtime_state.jsonl`, and `structured_events.jsonl`.
- With a persisted pause, the process exited `0` and the post-run settings read `paused=True`; the legacy force-start environment variable did not bypass the explicit-start contract. The command targeted only the unique temporary root; startup/profile mutation was not independently inspected by this rerun.
- This remains direct-process evidence only, not manual UI, supervisor-restart, browser, overlay, lock/sleep/resume, or installer evidence.

Latest isolated source-supervisor rerun on 2026-08-03:

- Started `focuscheck_supervisor.py --run --base-dir <repo>` with `FOCUS_DATA_DIR` and supervisor marker paths under a unique temporary root.
- The source child published a protocol-version `1` `ready` heartbeat with child PID `12404`.
- A generation-bound `source_live_selftest` stop request was atomically written; the supervisor exited, published `status=acknowledged`, and reported `termination=graceful`.
- This proves one bounded source supervisor/child handshake and intentional stop. It does not prove sleep/resume, registry startup, interactive UI, or production-duration supervision.

The repeatable automated source-process scenario is `tools/source_supervisor_selftest.py`. It launches disposable children and verifies failure/restart into a second generation, a generation/PID-bound stop with durable graceful acknowledgement, heartbeat hang recovery with old-child reaping, and circuit-breaker entry after repeated crashes. These are bounded source-process scenarios, not production-duration, sleep/resume, or target-machine evidence.

## Native tray smoke

Command:

```powershell
$env:FOCUS_DATA_DIR = "$env:TEMP\FocusCheck_live_tray_<unique>"
python main.py --tray-test
```

Observed on 2026-08-03:

- The native Windows tray/session watcher test ran for its bounded 20-second window and exited with code `0`.
- This confirms the isolated callback construction and teardown path used by `--tray-test`.
- It does not prove interactive menu commands, pystray fallback selection, Explorer restart, or the full manual tray/Tk matrix.

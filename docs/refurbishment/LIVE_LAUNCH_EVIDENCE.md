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

Latest isolated real supervisor probe on 2026-08-03:

- A real `focuscheck_supervisor.py --run --base-dir <repo>` launched the actual `main.py` child under a unique `%TEMP%` data root and published heartbeat child PID `27844`.
- A second supervisor using the same isolated marker paths exited without launching a duplicate and logged the existing-lock rejection.
- A generation-bound `real-supervisor-probe` stop request produced `status=acknowledged` and `termination=graceful`; both supervisor processes exited with code `0` and no cleanup process remained.

This is direct source-supervisor/duplicate-launch evidence. It does not prove
Run-key startup, lock/sleep/resume, interactive tray behavior, browser activity,
or production-duration supervision.

Latest isolated live child-crash/restart probe on 2026-08-03:

- A real `focuscheck_supervisor.py --run` launched `main.py` under a unique
  disposable data root and published child PID `19832`.
- Only that heartbeat-reported child was terminated. The same real supervisor
  then launched replacement child PID `26880`; the PID changed and the log
  contained both the child-exit and second-start records.
- The isolated supervisor tree, marker files, and disposable data root were
  removed after the probe.

This is direct live source-supervisor crash/restart evidence. It does not prove
intentional tray-exit acknowledgement, lock/sleep/resume, production-duration
supervision, or target-machine behavior.

Latest isolated startup-folder launcher probe on 2026-08-03:

- With `APPDATA` redirected to a unique disposable directory, `--install-startup` generated `RunFocusCheckSupervisor.cmd` under the expected Startup-folder path.
- The generated launcher contained the supervisor script, `--run`, the exact repository `--base-dir`, and the requested check/resume/restart timing arguments.
- `--uninstall-startup` removed the launcher, and the path was absent afterward.

This proves the source launcher generation/removal contract in an isolated
Windows profile. It does not prove real Explorer/Run-key shell execution or
interactive startup behavior.

Latest isolated canonical Run-key probe on 2026-08-03:

- A uniquely named disposable value was written to the current user's
  `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` key through
  `startup.install_startup()`.
- The value was stored as `REG_SZ` and contained the source-mode Python
  command targeting `focuscheck_supervisor.py --run --base-dir` with the exact
  repository root.
- `inspect_startup()` classified the installed value as `valid`, and
  `is_startup_installed()` returned true.
- `startup.uninstall_startup()` removed the value; a final inspection returned
  `absent`. Cleanup also ran in `finally`, and the real `FocusCheck` value was
  not touched.

This is direct per-user registry install/inspection/removal evidence. It does
not prove that Explorer launches the value at sign-in, nor lock/sleep/resume,
interactive tray behavior, or target-machine startup behavior.

Latest bounded live browser-provider probe on 2026-08-03:

- The native window enumerator found two visible supported-browser windows on
  this Windows session, one Chrome and one Firefox.
- Activity/window and tab-provider calls completed within the bounded probe;
  UI Automation/CDP returned no tab titles on this host, and no browser
  profile or tab state was modified.

This demonstrates graceful no-data behavior for unavailable browser metadata.
It does not prove URL extraction, exact/subdomain matching, cooldown/severity
behavior, or the supported-browser intervention matrix.

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

## Automated Tk QA rerun

Command:

```powershell
python tools/qa_scenario_runner.py --reset
```

Observed on 2026-08-03 at code commit `68dd06b`:

- Exit code: `0`.
- `qa_failures=0` with withdrawn-root Tk scenarios enabled.
- Reports were written under the disposable `_qa_runtime` root.

This is automated Tk/resource evidence only. It does not replace the manual
Windows matrix for interactive tray commands, focus/DPI behavior, browser
providers, lock/sleep/resume, or native overlay observation.

## Current runtime probes

On 2026-08-03, an isolated `python main.py --run-seconds=20` process exited
with code `0`, created the canonical runtime artifacts, and produced no
`Traceback`, `ERROR`, or exception records in `focus_app.log`. The real
`python main.py --tray-test` Windows watcher entrypoint also ran its bounded
20-second window and exited with code `0`.

A composed isolated prompt probe then disabled optional V1 follow-up fields,
waited for the real prompt scheduler to create a V1 prompt, invoked a valid
studying response, and exited cleanly. The log recorded
`choice=Studying`; no `append_log` failure, traceback, or exception was
observed. This proves a direct automated runtime response path, not manual
keyboard/mouse focus, tray-menu, browser, lock/sleep/resume, hardware, or
release evidence.

An isolated composed Settings probe opened one real `AdvancedSettingsWindow`
through `App._open_settings_from_tray`, changed `interval_seconds` to `42`,
and invoked the window save path on the Tk owner thread. The process exited
with code `0`; the canonical `focus_settings.json` read back
`interval_seconds=42`, with no save error, traceback, or exception observed.
This proves one durable Settings path, not full visual control-by-control or
target-user migration evidence.

Latest isolated 60-second direct launch on 2026-08-03:

- Command: `FOCUS_DATA_DIR=<unique %TEMP% root>; FOCUSCHECK_START_STOP_MODE=paused; py -3 main.py --run-seconds=60`.
- Application exit code: `0`; elapsed time: approximately `61.1` seconds.
- The disposable root contained `focus_app.log`, `focus_log.csv`, `focus_settings.json`, `focus_settings.json.lock`, `focus_tasks.sqlite3`, `hb.txt`, `runtime_state.jsonl`, and `structured_events.jsonl`.
- `focus_app.log` contained zero `Traceback`, `ERROR`, or `Exception` matches.

This strengthens direct timed-launch and persistence-initialization evidence only;
it does not prove interactive tray behavior, supervisor restart, browser
providers, lock/sleep/resume, overlays, hardware, startup registry, or release
installer behavior.

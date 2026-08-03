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

Latest extended supervised-duration probe on 2026-08-03:

- The actual supervisor launched the actual `main.py` child in a unique
  disposable data root and observed a ready heartbeat sequence advancing from
  `2` to `4` over approximately `213` seconds with one stable child PID.
- A generation/PID/process-start-bound stop request was accepted after the
  probe preserved the heartbeat's raw ISO `process_start_utc` value.
- The supervisor wrote a durable acknowledgement with
  `status=acknowledged`, `termination=graceful`, and exited; the child also
  exited and the disposable root was removed.
- An earlier probe attempt using a locale-converted process-start timestamp was
  rejected as expected; no forced termination was used.

This strengthens supervised-duration and stop-protocol evidence. It does not
prove production-duration supervision, sleep/resume, Explorer sign-in, or
target-machine lifecycle behavior.

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

Latest isolated real package-lifecycle startup probe on 2026-08-03:

- Using the current frozen package and disposable install/data roots, real
  `package_lifecycle.ps1` `Install` and `Upgrade` operations registered a
  unique HKCU Run value targeting the installed
  `FocusCheckSupervisor.exe --run --base-dir` command.
- Real `Uninstall` removed that value and archived the package; the temporary
  transaction root was removed and the production `FocusCheck` value was not
  touched.

This proves package-script registration/removal and target-path composition. It
does not prove Explorer sign-in execution, signing, or target-machine install
behavior.

Latest bounded live browser-provider probe on 2026-08-03:

- The native window enumerator found two visible supported-browser windows on
  this Windows session, one Chrome and one Firefox.
- Activity/window and tab-provider calls completed within the bounded probe;
  UI Automation/CDP returned no tab titles on this host, and no browser
  profile or tab state was modified.

This demonstrates graceful no-data behavior for unavailable browser metadata.
It does not prove URL extraction, exact/subdomain matching, cooldown/severity
behavior, or the supported-browser intervention matrix.

Latest disposable live CDP success probe on 2026-08-03:

- A headless Chrome instance with a unique temporary profile exposed CDP only
  on late candidate port `9229`.
- The real provider discovered the page target, returned the bounded title
  `FocusCheck CDP Probe`, returned its data URL, and listed the tab title.
- The Chrome process tree and temporary profile were removed after the probe;
  no user browser profile was used.

This proves bounded CDP discovery and title/URL extraction for a disposable
Chromium target. It does not prove real user-browser coverage, Firefox/UIA
extraction, or the website-flag intervention matrix.

Latest disposable live Edge CDP probe on 2026-08-03:

- A headless Microsoft Edge instance with a unique temporary profile exposed
  CDP on port `9229`.
- The real provider discovered `Edg/151.0.4129.59`, returned the bounded
  `about:blank` target and tab title, and exited without changing a user
  profile.
- The Edge process and temporary profile were removed after the probe.

This adds a real supported Chromium-family provider result. It does not prove
Firefox UI Automation extraction, real user-browser behavior, or website-flag
intervention semantics.

Firefox capability probe on 2026-08-03:

- The repository provider recognized the live Firefox process as supported but
  returned bounded no-data (`tabs=[]`, `url=None`) for its visible window.
- UI Automation client creation failed on this host with COM
  `Invalid class string`.
- A disposable Firefox `--remote-debugging-port` probe returned HTTP `404` for
  both `/json/version` and `/json/list`; it did not expose a Chromium CDP
  target protocol.
- The disposable Firefox process/profile were removed after the probe.

This is explicit host-capability evidence, not Firefox extraction evidence;
Firefox UIA extraction remains a target-machine/manual gate.

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

## Extended native overlay stress

Command:

```powershell
$env:FOCUSCHECK_NATIVE_OVERLAY_CYCLES='100'
$env:FOCUSCHECK_NATIVE_OVERLAY_SECONDS='0.10'
python tools/spotlight_overlay_selftest.py
```

Observed on 2026-08-03:

- Exit code: `0` on the real Windows host.
- Virtual screen: `x=-1920`, `y=0`, `w=3840`, `h=1080`.
- `100/100` overlay create/update/destroy lifecycle cycles passed.
- `199/199` `SetWindowRgn` updates passed with no reported native failure.

This strengthens automated native resource evidence. It does not prove live
multi-monitor DPI transitions, user-visible intervention restoration, or
hardware-specific overlay behavior.

## Extended direct runtime probe

Command:

```powershell
$env:FOCUS_DATA_DIR = "$env:TEMP\\FocusCheckDurationProbe_<unique>"
python main.py --run-seconds=180
```

Observed on 2026-08-03:

- Exit code: `0` after approximately `181.8` seconds.
- The isolated log contained zero matches for `Traceback`, `ERROR`, or
  `Exception`.
- The application process exited and the disposable data root was removed.
- Expected caveats were recorded: three `SetForegroundWindow failed` warnings
  in the non-interactive desktop session and one direct-launch warning that a
  supervisor stop request was not confirmed.

This is extended direct-entrypoint duration evidence, not production-duration
supervisor or interactive Windows acceptance evidence.

Post-fix direct shutdown probe on 2026-08-03:

- A disposable `python main.py --run-seconds=20` session exited with code `0`.
- The isolated log contained zero `Traceback`, `ERROR`, or `Exception` matches
  and zero `supervisor stop request durability is not confirmed` warnings.
- The disposable data root was removed after inspection.

This confirms direct shutdown no longer reports a missing-supervisor false
positive; supervised shutdown still uses the explicit stop-request protocol.

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

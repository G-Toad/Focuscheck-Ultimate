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

Observed on 2026-08-03:

- Process exit code: `0`.
- Data root was a unique `%TEMP%` directory, not `%APPDATA%` and not the repository.
- The run created `focus_app.log`, `focus_log.csv`, `focus_settings.json`, `focus_tasks.sqlite3`, `hb.txt`, `runtime_state.jsonl`, and `structured_events.jsonl`.
- No interactive tray, prompt, browser, lock/sleep/resume, startup-registry, or packaged-installer behavior was claimed by this run.

This evidence supports direct launch, isolated path selection, basic persistence initialization, heartbeat publication, and clean timed shutdown only.

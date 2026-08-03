# FocusCheck QA Harness

Use `tools/qa_scenario_runner.py` when validating FocusCheck without touching the live user profile.

## What It Does

- Sets `FOCUS_DATA_DIR` to `_qa_runtime/data` before importing app modules.
- Writes structured events to `_qa_runtime/events.jsonl`.
- Generates a local visual report at `_qa_runtime/report.html`.
- Exercises settings validation, feature gates, durable settings save/reload, startup state resolution, expired scheduler timers, pause/snooze/prompt eligibility, tray prompt-now and snooze delegation, V2 intervention state/logging, TaskDB, CSV logging, website flag matching, and withdrawn Tk dialog keyboard flows.
- The generated HTML report includes a Manual Windows Gates section for checks that automation cannot prove safely.

## Run

```powershell
py -3 tools\qa_scenario_runner.py --reset
```

If GUI popups must be avoided entirely:

```powershell
py -3 tools\qa_scenario_runner.py --reset --skip-gui
```

## Rule

Do not use the normal app launch for systematic QA unless a manual smoke step explicitly requires it. Run automated and semi-automated scenarios inside `_qa_runtime` first, then document any real GUI/manual checks in `docs/OPERATIONS_MATRIX.md`.

## Current Scenario Groups

- `settings.*`
- `startup.*`
- `app.schedule_next.*`
- `v2.*`
- `taskdb.*`
- `csv_logger.*`
- `monitoring.*`
- `gui.*`

Latest full harness run on 2026-08-03 completed with `qa_failures=0`, including
the withdrawn-root Tk dialog scenarios. This is automated GUI evidence only and
does not populate the manual Windows evidence matrix.

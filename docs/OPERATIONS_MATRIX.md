# FocusCheck Operations Matrix

This matrix is the Phase 7 completion checklist. Each operation should have an expected state, automated coverage where possible, and a manual repro when UI-bound.

## Launch And Process

- Launch via `start_focuscheck.bat`: supervisor starts `main.py`, heartbeat file updates, no duplicate app process.
- Launch via `Start FocusCheck.cmd`: direct `main.py` start, no supervisor restart.
- CLI selftest: `py -3 main.py --selftest` validates Windows callback path.
- Tray selftest: `py -3 main.py --tray-selftest` validates tray module/gates.
- Duplicate launch: single-instance mutex exits the second process.
- Exit: tray exit or quit tears down timers, tray, watcher, current prompt, and Tk root.

## Startup Management

- Install startup: `main.py --install-startup` writes a stable command pointing at `focuscheck_supervisor.py --run --base-dir ...`.
- Uninstall startup: `main.py --uninstall-startup` removes the same app name.
- Tray startup toggle: uses the same startup API and app name.
- Non-Windows startup operations: return false without crashing.

## Settings

- Load missing settings: defaults are filled.
- Load malformed settings: app falls back safely.
- Save settings: writes temp file, fsyncs, then atomically replaces target.
- Unknown settings: preserved but logged as unknown.
- Boolean strings: `"false"`/`"no"` become false, not true.
- Registry: every default key is registered or auto-registered.
- Truth table: `docs/SETTINGS_TRUTH_TABLE.md` classifies active, state-only, internal, legacy, hidden, and dead/decision settings.
- Isolated QA: `py -3 tools\qa_scenario_runner.py --reset` must produce `qa_failures=0` and `_qa_runtime/report.html`.
- Known state-only keys: `paused`, `snooze_until_utc`.
- Known legacy/dead keys to resolve in a later product decision: `webhook_url`, `tasks_decision_threshold_minutes`, `tasks_post_eval_minutes`. Gentle reminder settings are active and scheduled by App.

## Pause, Resume, And Snooze

- Manual stop: sets `paused=True`, persists it, suppresses prompts.
- Manual stop with prompt open: closes the active prompt before scheduling paused polling.
- Manual resume: clears `paused`, cancels active snooze timer/state, schedules next prompt.
- Prompt now: clears pause/snooze state and schedules immediate prompt.
- Snooze: sets `paused=True`, persists `snooze_until_utc`, closes active prompt, schedules unpause.
- Snooze confirmation: reuses the existing confirmation dialog instead of opening duplicates.
- Snooze expiry: clears pause/snooze state and schedules immediate prompt.
- Restart during active snooze: preserves paused state and schedules remaining expiry.
- Restart after expired snooze: clears stale snooze state.
- Lock/sleep: sets guard pause flags without exiting the app.
- Resume/unlock: clears guard flags and schedules prompt with debounce.
- Heartbeat: reports `paused`, `manual_paused`, `guard_paused`, and `pause_reason`.
- Guard scheduling: visible granular pause toggles are evaluated through `PauseGuard.should_pause()` and are not silently blocked by hidden app-level master checks.

## Prompt Scheduling

- Normal prompt: engine creates one prompt and tracks it as current.
- Existing prompt: suppresses duplicate prompt creation and retries later.
- Expired scheduled timer ID: cancellation failure is ignored and a fresh timer is still scheduled.
- Hidden prompt: attempts recovery before destroying stale prompt.
- Closed prompt: `_on_prompt_done()` is idempotent and schedules exactly one next prompt.
- Settings changed with prompt open: prompt cleanup runs before regeneration.
- Snooze with prompt open: prompt cleanup runs before pausing.

## V1 Prompt States

- Initial prompt visible.
- Studying response.
- Wasting-time response.
- Task required/not required.
- Focus detail prompt enabled/disabled.
- Waste detail prompt enabled/disabled.
- Challenge validation enabled/disabled.
- Spam validation enabled/disabled.
- Intensification stages.
- Overdrive flash/shake/stage5 overlay.
- Camera feed enabled/disabled and dependency-missing fallback.
- Task panel create/change/complete/fail.

## V2 Prompt And Interventions

- Activity-aware prompt renders app/window/url context.
- Escape/window close cannot dismiss the prompt without a valid answer.
- `yes` intervention path only logs/closes after intervention completion.
- Cancelled/failed intervention restores prompt without duplicating successful completion state.
- Intervention exception resets app intervention state so future prompts are not permanently suppressed.
- `no` intervention path logs and closes prompt.
- V2 cleanup exposes app-compatible timer/overlay cleanup hooks.
- V2 subpopup respects disabled flags, cooldowns, exact domains, and subdomains without suffix attacks.

## Tray

- Pause/resume menu states reflect `paused`.
- Start/stop menu honors `tray_start_stop_enabled`.
- Settings menu honors `tray_settings_button_enabled`.
- Exit menu honors `tray_exit_button_enabled`.
- Open logs/data folder handles missing platform support without crashing.
- Missing pystray/Pillow disables tray gracefully.

## Tasks And Persistence

- Start task creates active task.
- Starting a new task replaces any previous active task by marking it changed.
- Complete task clears active task and records history.
- Change task marks current task changed and can create a replacement.
- Fail/timed-out task records failed state.
- Overdue active tasks fail with aware or naive UTC due times.
- Analytics counts completed, failed, changed, and timed-out tasks.
- Waste/focus events record normalized strings and active task IDs.
- CSV append creates headers and data rows.
- CSV/JSONL write failure returns false without crashing runtime.

## Monitoring

- Engine V1 creates classic prompt.
- Engine V2 creates activity-aware prompt.
- Engine V2 website flags match exact host/subdomain.
- Engine V2 rejects suffix attacks such as `badreddit.com` for `reddit.com`.
- Engine V2 respects disabled flags and cooldowns.
- Browser/window probes fail softly when platform support is missing.

## Camera And Overlays

- Camera modules import when OpenCV is missing.
- Camera windows show a user-visible error when OpenCV is missing.
- Face tracking fallback honors `camera_face_fallback_mode`.
- Manual crop math is pure and testable.
- Overlay feature gate can disable overlay-style interventions.
- Windows click-through overlay helpers fail softly on unsupported systems.

## Required Validation Commands

- `py -3 -m compileall main.py focuscheck focuscheck_supervisor.py tests tools`
- `py -3 -m unittest discover -s tests -p "test*.py"`
- `py -3 main.py --selftest`
- `py -3 main.py --tray-selftest`
- `py -3 tools\settings_inventory.py`
- Manual UI smoke: `run_test.bat`

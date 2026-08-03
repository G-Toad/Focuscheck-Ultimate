# Behaviour Specification

This file defines externally observable behaviour that agents must preserve unless a task explicitly changes it.

## Supervisor Lifecycle

### Normal Supervised Launch

1. The supervisor starts from `focuscheck_supervisor.py --run`.
2. The supervisor acquires its lock file.
3. The supervisor launches `main.py` as the child app.
4. The child app writes heartbeat data.
5. The supervisor logs child start and monitors child liveness.

### Duplicate Supervisor Attempt

1. A second supervisor attempts to start.
2. The second supervisor detects the lock.
3. The second supervisor exits without launching another child app.
4. Existing supervisor and child app continue running.

### Unexpected Child Exit

1. The child app exits without an intentional stop marker.
2. The supervisor treats this as unexpected.
3. The supervisor waits using restart backoff.
4. The supervisor launches a fresh child app.

### Intentional Tray/App Exit

1. The user chooses Exit or app quit.
2. The child app writes the supervisor stop marker if supervised.
3. The child app stops tray integration and platform watchers.
4. The child app destroys the Tk root and exits.
5. The supervisor sees the intentional stop marker.
6. The supervisor clears the marker and exits without restarting the child.
7. Startup registration is not modified.

## Startup Registration

1. `main.py --install-startup` and tray startup enablement use the same platform startup API.
2. The startup command points at `focuscheck_supervisor.py --run --base-dir ...`.
3. Startup registration and manual launchers must not point at `main.py`, a test runner, a temporary extraction path, or a stale folder; all supported launchers use the supervisor.
4. Uninstall removes the same app name used during install.
5. Non-Windows startup operations return false or no-op safely without crashing.

## Pause, Resume, And Snooze

### Manual Stop

1. Manual stop sets `paused=True`.
2. Open prompts are closed or suppressed according to app logic.
3. Future scheduled prompts are suppressed while manually paused.

### Manual Resume

1. Manual resume clears manual pause.
2. Active snooze state is cancelled.
3. The next prompt is scheduled normally.

### Snooze

1. Snooze records `snooze_until_utc`.
2. Snooze sets paused state while active.
3. Snooze closes the active prompt if needed.
4. Snooze expiry clears pause/snooze state.
5. Restart during active snooze preserves the remaining snooze.
6. Restart after expired snooze clears stale snooze state.

## Windows Guard Events

1. Lock, idle, lid-closed, sleep, and resume are treated as guard pause events, not app exit events.
2. Guard pause must not overwrite manual pause intent.
3. Unlock/resume clears only the relevant guard flags.
4. Prompt scheduling after unlock/resume must debounce and avoid duplicate prompts.

## Prompt Lifecycle

1. Normal scheduling creates at most one active prompt.
2. Existing active prompts suppress duplicate prompt creation.
3. Prompt completion is idempotent.
4. Closing or cancelling unsupported prompt states must not produce a successful focus/waste log.
5. Settings changes with a prompt open must clean up the current prompt before regeneration.

## V2 Intervention Behaviour

### User Accepts Intervention

1. V2 prompt records intervention-active state.
2. Intervention wizard receives the active settings source.
3. Optional overlay creation respects `overlays_enabled`.
4. Completion logs success and closes the prompt only after the intervention completes.
5. App intervention state resets after completion.

### User Cancels Or Intervention Fails

1. Failed or cancelled intervention does not log successful prompt completion.
2. The prompt is restored if it was hidden.
3. App intervention state resets.
4. Future prompts are not permanently suppressed.

## Website Flags

1. Disabled flags do not trigger.
2. Cooldown suppresses recently dismissed flags.
3. Exact host and subdomain matches trigger.
4. Suffix attacks such as `badreddit.com` for `reddit.com` do not trigger when host parsing succeeds.
5. Severity 3 directly starts the intervention path.
6. Lower severities show the subpopup path.

## Settings

1. Missing settings load defaults.
2. Malformed settings fall back safely.
3. Boolean strings such as `"false"` and `"no"` normalize to false.
4. Unknown keys are classified before removal.
5. `webhook_url` remains a hidden compatibility key until webhook delivery is implemented; gentle-reminder settings are user-facing optional configuration and schedule a non-blocking reminder when enabled.

## Dialog Controls

1. Modal dialogs must release grabs on explicit cancel and window close.
2. Escape should cancel or choose the safer negative action where applicable.
3. Enter should submit only where the dialog is not a multiline editor.
4. Multiline editors use Ctrl+S for save and Escape for cancel.
5. Dialogs should set an initial focus target.

## Manual Windows Verification Required

The following cannot be considered fully proven by current automated tests:

- Real tray icon/menu shell behaviour.
- Current User Run key creation/removal on a real profile.
- Sleep/resume and workstation lock/unlock notifications.
- Real browser active-window URL detection.
- Overlay behaviour across physical monitors.

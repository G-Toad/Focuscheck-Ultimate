# Current Architecture

This document describes the architecture as it exists now. It is descriptive, not aspirational.

## Process Model

- `focuscheck_supervisor.py` is the release startup process. It launches `main.py`, monitors child liveness, watches heartbeat freshness, and restarts unexpected exits.
- `main.py` creates the Tk app and writes heartbeat files for the supervisor.
- The supervisor creates a lock file to avoid duplicate watchdog loops.
- The app writes an intentional stop file before user-requested supervised exit so the supervisor does not relaunch it.
- The app itself still uses a Windows mutex through `focuscheck.utils.file_ops.acquire_single_instance()` to avoid duplicate child app instances.

## Launch And Startup Paths

- Preferred manual launch: `start_focuscheck.bat`.
- Canonical startup registration: Current User Run key pointing at `focuscheck_supervisor.py --run --base-dir ...`.
- `Start FocusCheck.cmd` is a compatibility alias that delegates to `start_focuscheck.bat`; it does not bypass supervision.
- Direct `main.py` launch remains available for selftests and lightweight manual troubleshooting, but it is not the release startup target.

## Main Application Coordination

- `focuscheck.app.App` owns the Tk root, settings, task database, monitoring engine, pause guard, tray integration, prompt scheduling, and shutdown.
- Scheduling uses Tk `after()` timers.
- Prompt creation is delegated to the active monitoring engine.
- Settings changes can regenerate active prompts.
- Snooze and manual pause are persisted in settings.

## Monitoring Engines

- `EngineV1` is the classic periodic prompt path.
- `EngineV2` adds active window/browser context, richer prompts, website flags, and intervention paths.
- Browser/window probing is best-effort and Windows-oriented.
- Website flag matching must distinguish exact host/subdomain matches from suffix attacks.

## UI Model

- The UI uses Tkinter dialogs and windows.
- Tk widgets must be manipulated on the Tk thread.
- Tray callbacks may come from pystray/native callback threads and must dispatch to the Tk loop before showing message boxes or creating dialogs.
- Modal dialogs should have predictable Escape, Enter, window-close, grab-release, and focus behaviour.

## Persistence

- Runtime settings are loaded and normalized by `focuscheck.settings.manager`.
- Default settings live in `focuscheck.settings.defaults`.
- Feature gates live in `focuscheck.settings.gates`.
- Task state lives in SQLite through `focuscheck.database.TaskDB`.
- Logs and heartbeat files are written under FocusCheck app data directories unless `FOCUS_DATA_DIR` redirects test/runtime data.

## High-Risk Boundaries

- Supervisor restart loop versus intentional user exit.
- Startup install/uninstall consistency.
- Tray callback threading.
- Sleep/resume, lock/unlock, and idle pause.
- V1/V2 prompt completion and intervention cancellation.
- Website flag subpopup and intervention transitions.
- Settings normalization of legacy, hidden, and dormant keys.

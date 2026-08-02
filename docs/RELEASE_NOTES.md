# FocusCheck Ultimate Refurbishment Checkpoint

## Current checkpoint

- Branch: `main`
- Automated test baseline: 210 unittest cases.
- Verification runner: compile, tests, QA, application self-test, tray self-test, settings inventory, and diagnostic bundle stages pass.
- Core-service performance soak budgets pass; native/UI long-duration measurements remain pending.
- Isolated native overlay region-update self-test passes; the broader native/UI matrix remains pending.
- Release status: `NOT_READY`.

## Known limitations

- Native Windows, browser, overlay, lock/sleep/resume, startup registry, real installer shell, and signing evidence remain pending; scripted package and disposable install lifecycle contracts are covered by automated tests.
- The full runtime state and timer architecture is being migrated incrementally; legacy App callbacks still exist.
- Code signing is not configured.
- A disposable PyInstaller build, packaged self-test, and disposable install/upgrade/uninstall lifecycle have passed; real installer shell and signing remain pending.
- Supervisor restart waits are cancellation-aware, and accepted generation-bound stop requests receive an atomic durable acknowledgement.
- Native pause-guard API failures now expose bounded health metadata in diagnostics and heartbeats while retaining safe fail-open behavior.
- Startup inspection now detects legacy Startup-folder launchers and duplicate registry/folder startup, with an explicit canonical-route repair operation.
- Single-instance mutex API signatures are explicit and the owned Windows handle is released through the main lifecycle finally block.
- App lifecycle phases are now explicit and published in the heartbeat: `starting`, `ready`, `stopping`, `stopped`, and `failed`.
- Lifecycle and runtime transitions now append privacy-safe bounded metadata to `structured_events.jsonl`; diagnostic bundles include it without user content.
- Retention now rejects symlink candidates, accepts an injected clock for deterministic planning, and writes metadata-only deletion audit records.
- A static settings contract now verifies every `_save()` key against the canonical schema and prevents runtime state keys from entering ordinary UI saves.
- Windows session shutdown now separates `query_end_session` preparation from committed `end_session` cleanup and avoids process-level forced exit.
- Guard sampling is centralized through the runtime coordinator, so prompt, scheduler, and heartbeat paths share one effective-pause source of truth.
- The activity process-path probe now declares its Win32 handle, buffer, and pointer signatures before crossing the ctypes boundary.
- Foreground and top-level window enumeration now declare user32, process, and PSAPI signatures before crossing the ctypes boundary.
- Task analytics now store UTC while accepting an explicit timezone and injected clock for local-day/DST boundaries; existing callers retain an explicit UTC default.
- TaskDB schema migration version 3 normalizes recoverable legacy timestamps and clears invalid legacy due dates with an auditable repair reason; a checked-in legacy SQL fixture covers the path.
- Settings inventory now distinguishes editor references from runtime consumers and proves all 170 visible save keys have a non-editor consumer.
- TaskDB now verifies SQLite integrity and creates a numbered pre-migration backup before mutating an older database; corrupt files are rejected without replacement.
- `tools/export_data.py` now provides an atomic, allowlisted ZIP export with explicit sensitive-category opt-in, symlink rejection, and a SHA-256 manifest; the bounded runner exercises it in a disposable root.
- Tray/App data controls now provide metadata-only inventory, confirmed clear-log/personal-data actions, and explicit-age log retention through packaged services with metadata-only audit records.
- Data inventory and allowlisted export now cover application/supervisor logs plus settings recovery, audit, heartbeat, and diagnostic artifacts without including file contents in metadata previews.
- Tray fallback now stops the pystray adapter on the Tk owner thread before enabling the native adapter, preventing overlapping tray backends.
- Prompt scheduling now uses the validated in-memory settings snapshot instead of reparsing settings on every tick.
- Heartbeat publication now follows the App-owned frozen data-root snapshot instead of an import-time path constant.
- Application logging now binds to the App-owned log path before the first logger handler is created.
- The diagnostic bundle service now supports a live-data preview and sanitized operational bundle from the tray, excluding settings, tasks, camera files, and exports.
- Shutdown now explicitly cleans the active prompt and shuts down the monitoring engine exactly once before destroying Tk.
- Fixed guard-state refresh recursion so lock/idle/sleep pause state reaches the runtime coordinator.

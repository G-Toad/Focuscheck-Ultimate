# FocusCheck Ultimate Refurbishment Checkpoint

## Current checkpoint

- Branch: `main`
- Automated test baseline: 174 unittest cases.
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

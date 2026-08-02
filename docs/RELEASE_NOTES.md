# FocusCheck Ultimate Refurbishment Checkpoint

## Current checkpoint

- Branch: `main`
- Automated test baseline: 118 unittest cases.
- Verification runner: compile, tests, QA, application self-test, tray self-test, settings inventory, and diagnostic bundle stages pass.
- Core-service performance soak budgets pass; native/UI long-duration measurements remain pending.
- Release status: `NOT_READY`.

## Known limitations

- Native Windows, browser, overlay, lock/sleep/resume, startup registry, packaging, upgrade, and rollback evidence remain pending.
- The full runtime state and timer architecture is being migrated incrementally; legacy App callbacks still exist.
- Code signing is not configured.
- A disposable PyInstaller build and packaged self-test have passed; installer lifecycle and rollback execution remain pending.

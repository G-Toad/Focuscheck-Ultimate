# FocusCheck Ultimate Refurbishment Checkpoint

## Current checkpoint

- Branch: `main`
- Automated test baseline: 122 unittest cases.
- Verification runner: compile, tests, QA, application self-test, tray self-test, settings inventory, and diagnostic bundle stages pass.
- Core-service performance soak budgets pass; native/UI long-duration measurements remain pending.
- Release status: `NOT_READY`.

## Known limitations

- Native Windows, browser, overlay, lock/sleep/resume, startup registry, installer shell, and signing evidence remain pending; scripted package promotion/rollback is covered by automated tests.
- The full runtime state and timer architecture is being migrated incrementally; legacy App callbacks still exist.
- Code signing is not configured.
- A disposable PyInstaller build and packaged self-test have passed; installer lifecycle and rollback execution remain pending.

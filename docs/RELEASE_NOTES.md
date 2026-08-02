# FocusCheck Ultimate Refurbishment Checkpoint

## Current checkpoint

- Branch: `main`
- Automated test baseline: 149 unittest cases.
- Verification runner: compile, tests, QA, application self-test, tray self-test, settings inventory, and diagnostic bundle stages pass.
- Core-service performance soak budgets pass; native/UI long-duration measurements remain pending.
- Isolated native overlay region-update self-test passes; the broader native/UI matrix remains pending.
- Release status: `NOT_READY`.

## Known limitations

- Native Windows, browser, overlay, lock/sleep/resume, startup registry, real installer shell, and signing evidence remain pending; scripted package and disposable install lifecycle contracts are covered by automated tests.
- The full runtime state and timer architecture is being migrated incrementally; legacy App callbacks still exist.
- Code signing is not configured.
- A disposable PyInstaller build, packaged self-test, and disposable install/upgrade/uninstall lifecycle have passed; real installer shell and signing remain pending.

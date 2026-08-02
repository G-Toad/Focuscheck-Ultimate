# Release Evidence

- Automated: `123` unittest cases pass in the isolated verification runner, including live-profile isolation assertion.
- Compileall, application self-test, tray self-test, QA scenario runner, and settings inventory pass.
- Core-service performance soak passes its timer, state, SQLite growth, memory, and elapsed-time budgets.
- Release decision: `NOT_READY`.
- Pinned PyInstaller packaging, packaged self-test, and scripted package promotion/rollback evidence are present; installer shell lifecycle and signing remain unverified.
- Native Windows and UI evidence is pending and must be attached before release claims.

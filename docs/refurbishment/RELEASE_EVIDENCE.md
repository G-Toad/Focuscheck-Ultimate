# Release Evidence

- Automated: `114` unittest cases pass in the isolated verification runner, including live-profile isolation assertion.
- Compileall, application self-test, tray self-test, QA scenario runner, and settings inventory pass.
- Core-service performance soak passes its timer, state, SQLite growth, memory, and elapsed-time budgets.
- Release decision: `NOT_READY`.
- Pinned PyInstaller packaging and packaged self-test evidence are present; installer lifecycle, upgrade/rollback execution, and signing remain unverified.
- Native Windows and UI evidence is pending and must be attached before release claims.

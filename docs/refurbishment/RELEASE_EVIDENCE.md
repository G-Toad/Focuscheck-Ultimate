# Release Evidence

- Automated: `139` unittest cases pass in the isolated verification runner, including live-profile isolation assertion, repository-write and process-leak guards, diagnostic response redaction, coordinator-owned website pause suppression, durable `allow_once` consumption, activity-confidence policy, the full-schema boolean coercion matrix, and canonical website-domain matching.
- Settings input budgets reject oversized collections/strings before normalization or persistence.
- Task timestamps are normalized to UTC at the persistence boundary, with malformed inputs rejected by regression tests.
- Settings load/save is covered by an OS-level sidecar lock regression test.
- Runtime transition journal is App-wired and covered by metadata-only transition tests.
- Prompt acquisition is coordinator-denied during effective pause/snooze, with regression coverage.
- Compileall, application self-test, tray self-test, QA scenario runner, and settings inventory pass.
- Core-service performance soak passes its timer, state, SQLite growth, memory, and elapsed-time budgets.
- Release decision: `NOT_READY`.
- Pinned PyInstaller packaging, packaged self-test, and scripted package promotion/rollback evidence are present; installer shell lifecycle and signing remain unverified.
- Native Windows and UI evidence is pending and must be attached before release claims.

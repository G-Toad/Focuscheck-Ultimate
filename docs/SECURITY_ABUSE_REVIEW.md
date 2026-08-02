# Security and Abuse Review

## Scope

This review covers local data handling, startup persistence, supervisor control files, diagnostic exports, and the intervention controls. It is a source-level review; it is not a penetration test or a claim of Windows release certification.

## Controls

- Settings and task data stay under the canonical per-user data root; diagnostic generation excludes raw settings and SQLite data.
- Diagnostic text redacts known Windows user paths and common password/token/API-key patterns. Sharing remains a user decision because generic secret detection is not complete.
- CSV exports neutralize formula-leading cell values. JSON and SQLite retain source values and are not spreadsheet formats.
- Retention is dry-run by default and only operates on known application log files when `--apply` is supplied.
- Startup entries are written under the current user's Run key and now have a non-mutating valid/stale/malformed inspection path.
- Supervisor stop requests are JSON, PID-bound, and generation-aware; a child cannot be stopped solely because an unrelated process has the same executable name.
- The compatibility WerFault hook is intentionally a no-op and does not terminate unrelated system processes.
- Lock and runtime files are scoped to the canonical data root and disposable verification overrides are supported.

## Residual risks

- A local user or administrator can read or modify another local user's files and registry state.
- The current diagnostic redaction is pattern-based and must be reviewed before sharing.
- Native Windows APIs, installer permissions, code signing, and upgrade/rollback behavior still require target-machine evidence.
- This review does not establish protection against malware running with the user's privileges.

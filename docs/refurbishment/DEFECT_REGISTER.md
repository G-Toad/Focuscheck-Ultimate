# Defect Register

| ID | Severity | Classification | Evidence | Fix | Tests | Manual verification | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CFG-001 | 1 | confirmed defect | Malformed settings silently fell back and destroyed recovery context. | Quarantine corrupt file and recover `.bak`. | `SettingsSaveTests`. | Not run. | fixed |
| CFG-002 | 1 | confirmed defect | Save had no structured observable durability result. | `SettingsSaveResult` exposes path, revision, durable-write, backup, validation, conflict, and error fields while remaining bool-compatible. | settings result and write-failure regressions. | Not run. | fixed |
| CFG-003 | 2 | confirmed defect | Date validation accepted impossible calendar dates. | `datetime.date` validation. | settings validation regression. | Not run. | fixed |
| SUP-003 | 1 | confirmed defect | Supervisor killed every `WerFault.exe` process system-wide. | Compatibility hook is a no-op; no call sites remain. | source review and compile. | Target Windows crash test required. | fixed |
| SUP-001 | 1 | confirmed defect | Normal launcher forced start over durable pause. | Removed force-start from normal launcher. | launch script regression. | Live supervised pause test required. | fixed |
| SUP-007 | 1 | confirmed defect | Two heartbeat writers/files existed. | Single App-owned JSON heartbeat. | self-tests and verification runner. | Live hang/restart test required. | fixed |
| SUP-004 | 1 | confirmed defect | Intentional-stop marker was existence/PID-only and could be stale or foreign. | Atomic structured request bound to supervisor, generation, PID, process-start time, nonce, and freshness window. | `SupervisorEntrypointTests`, lifecycle tests. | Live user-exit race required. | fixed |
| SUP-005 | 2 | confirmed defect | PID-only supervisor lock could be ambiguous under PID reuse. | Structured owner record with process-start token and instance nonce; ownership-checked release. | `test_stale_supervisor_lock_recovers_after_pid_reuse`, lock lifecycle tests. | Live duplicate-supervisor test required. | fixed |
| SUP-006 | 2 | confirmed defect | Wall-clock heartbeat age could misclassify clock changes and was shorter than the file heartbeat cadence. | Sequence receipt-time freshness with explicit heartbeat interval and legacy wall-clock fallback. | `test_supervisor_uses_sequence_receipt_time_not_wall_clock_age`, heartbeat protocol tests. | Live sleep/resume and hang test required. | fixed |
| SUP-002 | 1 | confirmed defect | Restart delay reset was not explicitly tied to a stable ready child. | Reset exponential backoff only after a current-generation ready heartbeat remains healthy for `STABLE_RUNTIME_SECONDS`. | `test_restart_backoff_resets_only_after_stable_ready_window`. | Live crash-loop and recovery test required. | fixed |
| DB-003 | 2 | confirmed defect | No database invariant prevented duplicate active tasks. | Unique partial index and legacy reconciliation. | TaskDB lifecycle tests. | Concurrent live UI test required. | fixed |
| LOGDATA-001 | 2 | confirmed defect | CSV rotation happened outside the per-file lock. | Rotation now occurs inside the lock. | CSV tests. | Not run. | fixed |

# Release Evidence

The current automated baseline is `259` tests; the detailed older bullets are retained as historical baseline context.

- Automated: `164` unittest cases pass in the isolated verification runner, including live-profile isolation assertion, repository-write and process-leak guards, canonical path/legacy settings conflict handling, busy-file-safe logging, frozen source/frozen entrypoint and startup command resolution, disposable install/upgrade/uninstall and package promotion/rollback, structured settings-save durability results, atomic heartbeat publication and throttled write-failure diagnostics, mainloop exception preservation through cleanup, manual-pause-preserving snooze transitions, tray task-dialog owner-thread dispatch, tray exit lifecycle without tray-thread process exit, explicit Windows idle API signatures and wrap-safe tick arithmetic, atomic legacy task/log migration with hash conflict preservation, diagnostic response redaction, coordinator-owned website pause suppression, durable `allow_once` consumption, injected cooldown-clock boundaries, activity-confidence policy, PID-reuse-resistant supervisor lock ownership, sequence receipt-time heartbeat freshness, stable-ready restart backoff reset, the full-schema boolean coercion matrix, canonical website-domain matching, generation-bound stale/foreign stop-request rejection, atomic stop-request writes, and the bounded packaged supervisor readiness/reaping harness contract.
- Settings input budgets reject oversized collections/strings before normalization or persistence.
- Latest verification checkpoint: `259` unittest cases pass; it additionally covers clock-aware expired-snooze persistence, coordinator-owned snooze expiry/manual-pause preservation, injected-clock snooze reconciliation, startup snooze timer ownership, intervention selection/spotlight timer ownership, V1 PromptDialog owner notification after a studying choice, the existing prompt/camera timer cleanup regressions, deterministic settings/domain/runtime invariant tests, the checked-in settings migration fixture matrix, three selected mutants killed in the bounded mutation-smoke stage, and all 14 bounded verification stages.
- Task timestamps are normalized to UTC at the persistence boundary, with malformed inputs rejected by regression tests.
- Settings load/save is covered by an OS-level sidecar lock regression test.
- Runtime transition journal is App-wired and covered by metadata-only transition tests.
- Prompt acquisition is coordinator-denied during effective pause/snooze, with regression coverage.
- Compileall, application self-test, tray self-test, QA scenario runner, and settings inventory pass.
- Isolated native overlay self-test passes virtual-screen region updates without live-profile logging contention.
- Core-service performance soak passes its timer, state, SQLite growth, memory, and elapsed-time budgets.
- Release decision: `NOT_READY`.
- Pinned PyInstaller packaging, packaged self-test, scripted package promotion/rollback, and disposable install/upgrade/uninstall evidence are present; real installer shell lifecycle and signing remain unverified.
- Native Windows and UI evidence is pending and must be attached before release claims.

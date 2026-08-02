# Current Operation Matrix

This is the current repository-grounded operation matrix. `automated` means the bounded runner or unit tests exercise the behavior. `manual_pending` means the implementation exists or is documented but target Windows evidence is still required.

| Area | Operation/state | Current contract | Evidence |
| --- | --- | --- | --- |
| Launch | Direct child start | `main.py` performs single-instance enforcement before App composition. | `automated` |
| Launch | Supervised start | `focuscheck_supervisor.py` owns heartbeat, generation, nonce-bound stop requests, process-start-token lock ownership, stale detection, and bounded restart behavior. | `automated`; live restart `manual_pending` |
| Startup | Run-key registration | Per-user registry startup is canonical; inspection distinguishes absent, valid, stale, malformed, legacy, duplicate, and error states, with explicit repair. | `automated`; registry/moved-install `manual_pending` |
| Runtime | Manual pause | Durable settings mutation is transactional and cross-process serialized. | `automated` |
| Runtime | Snooze | Durable UTC expiry is stored and effective pause is clock-testable. | `automated`; tray/Tk `manual_pending` |
| Runtime | Guard pause | Guard reasons are tracked separately from manual intent. | `automated`/source; lock/sleep `manual_pending` |
| Runtime | Prompt eligibility | Coordinator denies prompt acquisition during effective pause, active intervention, active prompt, or shutdown. | `automated` |
| Prompt | V1/V2 dialog ownership | One active prompt generation is tracked; duplicate completion is idempotent. | `automated`; visible UI cleanup `manual_pending` |
| Intervention | Start/cancel/complete | App owns an intervention lease; cancellation does not consume website cooldown. | `automated`; overlay restoration `manual_pending` |
| Activity | CDP discovery | Page targets only, URL query/fragment removed, bounded request/discovery timeout. | `automated`; live browsers `manual_pending` |
| Data | Settings | Migration, quarantine, rotating backups, readback validation, revision conflicts, and OS-level sidecar lock. | `automated` |
| Data | Tasks | SQLite schema journal, one active task, UTC timestamp boundary, integrity-checked pre-migration backup, and backup/restore. | `automated`; full UI flow `manual_pending` |
| Data | Export | Allowlisted ZIP export defaults to logs/metadata; settings, tasks, and camera data require explicit category selection and are recorded in a SHA-256 manifest. | `automated`; user-facing control `manual_pending` |
| Privacy | Camera | Disabled by default, optional dependencies degrade, capture is opt-in, photos stay in app data or controlled temp recovery. | `automated`/source; camera hardware `manual_pending` |
| Privacy | Diagnostics | Bundle excludes raw settings/tasks and applies pattern-based path/secret redaction. | `automated`; sharing review required |
| Packaging | Build | Pinned PyInstaller build and packaged self-test. | `automated` |
| Packaging | Promotion/rollback | Non-destructive staged promotion and retained-backup rollback with SHA-256 manifest. | `automated`; installer/signing `manual_pending` |
| Native | Overlay/tray/session hooks | Pointer-sized declarations, idempotent overlay resource release, and isolated virtual-screen region-update self-test. | automated smoke; broader live Windows `manual_pending` |

Release status remains `NOT_READY` until all `manual_pending` rows have target-machine evidence and the final acceptance gates are rerun.

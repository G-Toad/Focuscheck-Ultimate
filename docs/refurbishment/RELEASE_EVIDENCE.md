# Release Evidence

The current automated baseline is `506` tests across 19 bounded stages; the detailed older bullets are retained as historical baseline context.

The latest filesystem-composition checkpoint adds an injectable canonical data-root directory-creation boundary and regression coverage. Manual Windows, browser, power/session, installer/signing, target-user migration, and production-release evidence remain pending.

The latest lifecycle checkpoint adds injectable startup and shutdown stage hooks plus a real constructor failure matrix covering all 13 startup checkpoints; manual and release gates remain pending.

The latest prompt checkpoint adds typed prompt outcomes and App source-to-outcome mapping for completion, cancellation, pause, settings, and shutdown interruption; the complete interactive close matrix remains pending.

The latest website-flag checkpoint adds coordinator and standalone suppression matrices for pause, snooze, guard, shutdown, prompt, and intervention states; live browser/overlay evidence remains pending.

The latest intervention checkpoint closes spotlight overlays and restores hidden prompts when action-dialog construction fails; deterministic intervention cleanup coverage passes, while live overlay evidence remains pending.

The latest tray checkpoint adds explicit tray lifecycle states and tested idempotent/failure transitions; native tray and Explorer-restart evidence remain pending.

The latest composition checkpoint adds an injectable Tk root factory used by the startup failure matrix while retaining `tk.Tk` as the production default; interactive Windows evidence remains pending.

The latest prompt checkpoint adds typed outcome state to V1/V2 prompt instances and preserves first interruption outcomes through teardown; the complete interactive close matrix remains pending.

The latest camera checkpoint releases allocated capture handles on closed-device and initialization-exception paths across prompt and preview windows, with deterministic cleanup/failure coverage; live camera hardware and frame-lifetime evidence remain pending.

The latest native-wrapper checkpoint makes top-level window callbacks platform-safe and reports actual `PostMessageW` close results; focused provider/native tests pass, while live window-control evidence remains pending.

The latest click-through checkpoint reports `SetWindowPos` failure instead of claiming input-style setup succeeded, with focused native-style coverage; live overlay/input evidence remains pending.

The latest WNDPROC checkpoint reports callback-installation failure from `SetWindowLongPtrW` instead of claiming success; focused setter-result coverage passes, while live overlay/input evidence remains pending.

The latest packaging checkpoint rejects unsafe source packages before moving the current installation, including forbidden source/debug/runtime-data files and reparse points; focused lifecycle coverage passes, while signed installer and target-machine evidence remain pending.

The latest signing checkpoint validates source executable signatures before promotion and reports unavailable signature tooling explicitly; focused coverage preserves the existing install on rejection, while real certificate and target-machine evidence remain pending.

- The current verifier has `19` passing bounded stages. The test-category inventory explicitly separates automated categories from live/manual/opt-in categories. `state_restart_selftest` runs the real entrypoint three times in an isolated data root and verifies persisted manual pause, active snooze restoration, expired-snooze reconciliation, heartbeat pause truth, and clean shutdown.
- Settings UI regression coverage verifies the composed Advanced Settings window uses the App persistence callback, not the UI module's repository import, and applies the normalized committed revision state.
- Child settings regression coverage verifies camera and crop saves use the injected App callback and apply normalized committed values only after durable success.
- Prompt regression coverage verifies V1 sequential phrase-index advancement uses the App callback and leaves shared state unchanged after a failed durable write.
- V2 website-flag regression coverage verifies `allow_once` persistence uses the App callback and applies committed state without invoking the module repository.
- Runtime-state regression coverage verifies the App persistence boundary applies committed settings back to the coordinator during durable pause/snooze state changes.
- Runtime-state view coverage verifies immutable revision/effective-reason snapshots and revision rollback after failed persistence.
- Status/heartbeat regression coverage verifies scalar-safe runtime revision and pause-reason publication from the immutable view.
- Tray regression coverage verifies the post-start health timer is cancelled and cleared during tray stop.
- Mutation-smoke coverage kills five selected mutants, including TaskDB active-to-completed and supervisor stable-ready backoff contracts.
- Prompt UI regression coverage verifies both V1 and V2 Settings entry points pass the App persistence callback.
- Verification-runner regression coverage verifies timed-out stages are terminated by PID tree and the report records commit, environment, test summary, manual requirements, process leaks, and `partial` status.

- The current verifier has `16` passing bounded stages, including `source_supervisor_selftest`, which launches disposable real children and verifies failure/restart, generation/PID-bound stop acknowledgement, heartbeat hang recovery, circuit-breaker entry, and child reaping. This does not replace manual target-machine, sleep/resume, or production-duration supervision evidence.
- Fatal-mainloop cleanup is covered by a failure-injection matrix across runtime state, prompt, reminder, engine, timer, tray, watcher, and Tk-root stages; the regression also verifies no intentional supervisor-stop request is emitted after a crash.
- Partial-construction failure injection verifies acquired runtime resources are released and the original startup exception is re-raised without an intentional supervisor-stop request.
- Tray command regression coverage verifies fallback setting writes call an App-owned command and do not invoke module-level persistence.
- Intervention regressions verify App-owned runs generate and pass one identity through the wizard, preserve prompt context, and clear the identity/lease on failure.

- Automated: `164` unittest cases pass in the isolated verification runner, including live-profile isolation assertion, repository-write and process-leak guards, canonical path/legacy settings conflict handling, busy-file-safe logging, frozen source/frozen entrypoint and startup command resolution, disposable install/upgrade/uninstall and package promotion/rollback, structured settings-save durability results, atomic heartbeat publication and throttled write-failure diagnostics, mainloop exception preservation through cleanup, manual-pause-preserving snooze transitions, tray task-dialog owner-thread dispatch, tray exit lifecycle without tray-thread process exit, explicit Windows idle API signatures and wrap-safe tick arithmetic, atomic legacy task/log migration with hash conflict preservation, diagnostic response redaction, coordinator-owned website pause suppression, durable `allow_once` consumption, injected cooldown-clock boundaries, activity-confidence policy, PID-reuse-resistant supervisor lock ownership, sequence receipt-time heartbeat freshness, stable-ready restart backoff reset, the full-schema boolean coercion matrix, canonical website-domain matching, generation-bound stale/foreign stop-request rejection, atomic stop-request writes, and the bounded packaged supervisor readiness/reaping harness contract.
- Settings input budgets reject oversized collections/strings before normalization or persistence.
- Browser provider inputs are bounded to 256 targets and 2048-character titles/4096-character URLs before tab matching.
- Latest verification checkpoint: `283` unittest cases pass; it additionally covers Tk/non-daemon-thread resource cleanup, clock-aware expired-snooze persistence, coordinator-owned snooze expiry/manual-pause preservation, injected-clock snooze reconciliation, deterministic TaskDB transition/overdue timestamps, bounded/clocked activity provider success/error/timeout cases, icon extraction, spotlight region, intervention positioning, core overlay lifecycle, dialog-owned overlay Win32 signature declarations, bounded intervention-reflection JSONL records, bounded rotation, corruption-tolerant reads, process-global overlay WNDPROC retention, repeated native overlay lifecycle cycles, spotlight region handle ownership on success/failure paths, core/dialog click-through and WNDPROC fallback signatures, native tray/session watcher User32 signatures, prompt Windows integration style/focus/taskbar signatures, V2 subpopup metrics and phrase-acronym focus signatures, pointer-safe prompt monitor placement signatures and callback width, intensification gamma and Magnification API signatures, startup snooze timer ownership, intervention selection/spotlight timer ownership, V1/V2 prompt timer registry invalidation, prompt-hosted biodata pulse ownership, exhaustive schema-generated settings-control round trips, V1 PromptDialog owner notification after a studying choice, snooze-prompt, Gentle Reminder, and Snooze Reminder registry invalidation on close, the existing prompt/camera timer cleanup regressions, deterministic settings/domain/runtime invariant tests, the checked-in settings migration fixture matrix, three selected mutants killed in the bounded mutation-smoke stage, and all 15 bounded verification stages.
- Task timestamps are normalized to UTC at the persistence boundary, with malformed inputs rejected by regression tests.
- Settings load/save is covered by an OS-level sidecar lock regression test.
- Runtime transition journal is App-wired and covered by metadata-only transition tests.
- Prompt acquisition is coordinator-denied during effective pause/snooze, with regression coverage.
- Compileall, application self-test, tray self-test, QA scenario runner, and settings inventory pass.
- The full QA harness, including withdrawn-root Tk scenarios, most recently passed with `qa_failures=0`; this remains automated evidence and does not satisfy the manual Windows matrix.
- Isolated native overlay self-test passes explicit region signatures and repeated bounded `3/3` create/update/destroy cycles without live-profile logging contention.
- Core-service performance soak passes its timer, state, SQLite growth, memory, and elapsed-time budgets.
- Release decision: `NOT_READY`.
- Pinned PyInstaller packaging, direct frozen-child self-test, packaged supervisor READY/stop-acknowledgement, manifest validation, and current disposable install/upgrade/rollback/uninstall evidence are present; real installer shell lifecycle, signing, production-duration supervision, and target-machine evidence remain unverified.
- Native Windows and broader UI evidence is pending and must be attached before release claims; the automated resource-leak stage now exercises representative V1/V2 prompt cleanup on a withdrawn Tk root.
- Current commit `c8c8f2d` was rebuilt with PyInstaller `6.16.0`; both frozen executables passed promotion, manifest validation, child self-test, and packaged supervisor READY/stop-acknowledgement/reaping self-test. This remains unsigned disposable-package evidence, not installer, signing, production-duration, or target-machine evidence.
- The same current package passed a fresh disposable `Install` -> `Upgrade` -> reversible `Uninstall` transaction with backup retention and data-root deletion safeguards; the existing unrelated startup entry was not removed.

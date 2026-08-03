# Release Evidence

Latest native-tray correction: source checkpoint `08e45f7` declares the `kernel32.SetLastError` contract used while opening the native tray menu and removes the raw untyped fallback call. The full verifier passed all 20 stages with 570 tests and zero process leaks; live Windows/UIA/browser behavior and packaging remain manual gates.

Latest native-error correction: source checkpoint `b0d4114` centralizes pointer-safe `GetLastError` and `FormatMessageW` declarations and reuses the contract from intervention diagnostics. The full verifier passed all 20 stages with 569 tests and zero process leaks; live Windows/UIA/browser behavior and packaging remain manual gates.

Latest native-overlay correction: source checkpoints `d605f65` and `8814d0f` declare the intensification stage-5 `SetWindowPos` contract and keep configured User32/GDI handles for later overlay alpha/destruction calls, with compatibility-safe partial-fixture fallbacks. The full verifier passed all 20 stages with 568 tests and zero process leaks; live Windows/UIA/browser behavior and packaging remain manual gates.

Latest native-boundary correction: source checkpoint `cd42777` declares the `SetWindowPos` ctypes signature before intensification child-window updates and adds regression coverage. The full verifier passed all 20 stages with 567 tests and zero process leaks; live Windows/UIA/browser behavior and packaging remain manual gates.

Latest browser-boundary correction: source checkpoint `4dd8484` normalizes case-insensitive Windows executable paths to browser basenames across URL detection and session recovery. Focused browser tests and the full verifier passed with 566 tests across all 20 stages and zero process leaks; real browser/UIA behavior remains manual.

Latest browser-matrix correction: source checkpoint `117b6d9` covers the read-only session fallback for Chrome, Edge, Brave, Opera, Opera GX, and Firefox, including titleless URL recovery. The full verifier passed all 20 stages with 564 tests and zero process leaks; live browser/UIA extraction and website-flag intervention remain manual gates.

Latest plan-traceability correction: source checkpoint `8055695` adds explicit accepted alias rows for every one of the 84 defect identifiers named by the controlling V1 plan, plus a dedicated `plan_register_coverage` verifier stage. The full verifier passed all 20 stages with 562 tests and zero process leaks; the register contains 148 defect rows and 6 contradiction rows with no untriaged severity-0/1 entries. Manual/release gates remain pending.

Latest resource-soak correction: source checkpoint `2b46a2c` extends the bounded performance stage with 500 activity-provider calls and a non-daemon-thread leak postcondition. The stage passed in 5.023 seconds with zero timer callbacks and zero non-daemon thread leaks; the full verifier passed all 19 stages with 561 tests and zero process leaks. Manual long-duration UI/native/browser and release gates remain pending.

Latest status-window composition correction: source checkpoint `fa8c96c` routes the App-owned diagnostic status `Toplevel` through an injectable factory. The verifier report completed with all 19 stages passed, 561 tests, and zero process leaks; the outer command wrapper timed out after report generation, so the report is the authoritative result. Release status remains partial because manual Windows and packaging gates are not run.

Latest composition-root UI correction: source checkpoint `5035440` routes App-owned intervention, Settings, task, snooze, and reminder dialog construction through injectable `AppDependencies` factories while preserving production defaults and standalone fixture compatibility. Focused lifecycle regressions and the full verifier passed with 561 tests across all 19 stages and zero process leaks; release status remains partial because manual Windows and packaging gates are not run.

Latest V2 polling evidence: source checkpoint `711de87` prevents website polling from restarting after a lease ends while another prompt, intervention, pause, shutdown, or guard condition remains active. The full verifier passed all 19 stages with 558 tests and zero process leaks; release status remains partial because manual Windows and packaging gates are not run.

Latest composed prompt-Settings evidence: source checkpoint `a3cff73` proves V1/V2 prompt Settings links use the App-owned close boundary when available and preserve standalone compatibility. The verifier report records all 19 stages passed, 557 tests, and zero process leaks; the outer wrapper timed out after report generation and is recorded as such. Release status remains partial because manual Windows and packaging gates are not run.

Latest Settings/prompt evidence: source checkpoint `1f8500e` proves tray Settings refresh releases the active prompt lease through the shared close path before scheduling regeneration. The full verifier passed all 19 stages with 556 tests; release status remains partial because manual Windows and packaging gates are not run.

Latest prompt-lifecycle evidence: source checkpoint `fe63f77` proves V2 website polling is suspended for prompt ownership and resumes after completion, interruption, rejection, or creation failure. The full verifier passed all 19 stages with 555 tests; release status remains partial because manual Windows and packaging gates are not run.

Latest intervention-lifecycle evidence: source checkpoint `a948f12` proves V2 website polling is suspended for the entire App-owned intervention lease and resumes after lease cleanup, including failure-isolated finalization. The full verifier passed all 19 stages with 554 tests; release status remains partial because manual Windows and packaging gates are not run.

Latest tray-snooze evidence: source checkpoint `f5b25ed` proves the fallback tray's direct snooze-setting path notifies the monitoring engine after a durable transition. The full verifier passed all 19 stages with 553 tests; release status remains partial because manual Windows and packaging gates are not run.

Latest snooze-lifecycle evidence: source checkpoint `6b62ff6` proves cancelling a snooze notifies the monitoring engine when manual pause is already clear, restoring V2 website polling eligibility. The full verifier passed all 19 stages with 552 tests; release status remains partial because manual Windows and packaging gates are not run.

Latest guard-lifecycle evidence: source checkpoint `0f12197` forwards effective guard activation and clearing to the monitoring engine, with regression coverage for both transitions. The full verifier passed all 19 stages with 551 tests; release status remains partial because manual Windows and packaging gates are not run.

Latest engine-state evidence: source checkpoint `0648136` adds the pause-transition hook to the monitoring interface and proves V2 website polling is cancelled while effectively paused and resumed after eligibility returns. The full verifier passed all 19 stages with 550 tests; release status remains partial because manual Windows and packaging gates are not run.

Latest timer-registry evidence: source checkpoint `c4b73a3` removes phantom timer ownership after one-shot or recurring Tk scheduler failure. The full verifier passed all 19 stages with 548 tests; release status remains partial because manual Windows and packaging gates are not run.

Latest engine-switch evidence: source checkpoint `7013367` constructs the replacement monitoring engine before tearing down the existing engine, and regression coverage proves factory failure preserves the active engine and prompt. The full verifier passed all 19 stages with 546 tests; release status remains partial because manual Windows and packaging gates are not run.

The current automated baseline is `544` tests across 19 bounded stages at source checkpoint `809696e`; the detailed older bullets are retained as historical baseline context.

The latest register checkpoint adds automated validation for 98 unique defect rows and 6 contradiction rows, including traceability fields and untriaged severity-0/1 detection. It corrected a duplicate `DB-011` identifier; this does not convert manual target-machine requirements into automated passes.

The latest release-evidence checkpoint adds a non-destructive manual checklist CLI. It refuses to record pass/fail without explicit human confirmation, validates the five-case schema, and atomically writes only an explicitly requested case; the committed manual evidence remains `not_run`.

The latest browser profile-boundary checkpoint rejects symlinked profile components before recovery reads. The full verifier passed; the symlink-specific test is skipped when the host cannot create directory symlinks, and live browser evidence remains pending.

The latest browser-session safety checkpoint bounds reads even when a session file changes after its initial stat, with an oversized-file regression. Focused browser tests and the full verifier passed; live browser evidence remains pending.

The latest heartbeat metadata checkpoint makes lifecycle snapshot serialization capability-safe for injected adapters and adds regression coverage for mapping, missing, and failing snapshot shapes. Focused lifecycle tests and the full verifier passed; manual Windows and release evidence remains pending.

The latest composition checkpoint adds an injectable activity-provider factory for V2 engine construction while preserving direct-provider and production defaults. Focused lifecycle tests and the full verifier passed; live browser and Windows evidence remains pending.

The latest lifecycle observability checkpoint makes heartbeat readiness capability-safe for injected lifecycle adapters and adds regression coverage for enum, string, and missing phase values. Focused lifecycle tests and the full verifier passed; manual Windows and release evidence remains pending.

The latest browser-session checkpoint adds bounded read-only Firefox recovery parsing and conservative Chromium session URL extraction as a final tab-listing fallback after UI Automation and CDP, with query/fragment redaction. Focused browser tests and the full verifier passed; recovered session data is not treated as foreground identity and live browser evidence remains pending.

The latest lifecycle correction removes the duplicate lifecycle completion transition from `App.run()` so `_cleanup_runtime` is the single cleanup owner. Focused lifecycle regressions and the full verifier passed; manual Windows, hardware, packaging, and release evidence remain pending.

The latest health-snapshot checkpoint adds bounded supervisor, heartbeat, watcher, TaskDB, and activity-provider health metadata to the status surface without exposing runtime paths or user content; interactive status-window evidence remains pending.

The latest composition-root checkpoint adds injectable factories for the core clock, event ledger, lifecycle, timer, runtime journal, and runtime-state services, with constructor failure-injection coverage across all startup checkpoints. Manual Windows and release evidence remains pending.

The latest composition-root extension adds injectable PauseGuard and PromptCoordinator factories, including coordinator recovery-path coverage, while preserving standalone fixture defaults. Full composition extraction and manual Windows/release evidence remain pending.

The latest composition-root engine correction routes V1/V2 engine selection through an injectable factory receiving the selected engine class and App context, while preserving default production construction and V2 clock/provider wiring. Manual Windows and release evidence remains pending.

The latest startup composition correction routes legacy migration through an injectable App dependency and removes global migration patching from the constructor failure matrix. Production defaults remain unchanged; existing-user migration and manual release evidence remain pending.

The latest startup composition extension routes log-header creation through an injectable dependency and removes global log-header patching from the constructor failure matrix. Production defaults remain unchanged; existing-user and manual release evidence remain pending.

The latest path-composition extension routes canonical `AppPaths` selection through an injectable factory before later startup side effects, with a regression covering the frozen path boundary. Production defaults remain unchanged; target-user migration and manual release evidence remain pending.

The latest path-binding extension routes CSV and application-log path configuration through injectable App dependencies receiving the frozen `AppPaths` snapshot. Production defaults remain unchanged; target-user and manual release evidence remain pending.

The latest tray-composition correction honors an injected tray adapter even when the optional tray import is unavailable, preserving headless composition and production fallback behavior. Native tray evidence remains pending.

The latest watcher-composition correction honors an explicitly injected watcher adapter on non-Windows hosts while retaining the Windows-only default. Live session/power/display watcher evidence remains pending.

The latest fault-injection correction makes the real 13-checkpoint constructor failure matrix use the injected App-owned timer factory rather than patching the timer module global. The automated baseline is unchanged; manual/release evidence remains pending.

The latest fault-injection extension also injects tray and watcher adapters in that matrix, removing global optional-backend and platform patches while exercising composed startup through watcher initialization. Manual/release evidence remains pending.

The latest lifecycle cleanup correction makes partial-construction shutdown capability-safe for minimal injected lifecycle adapters, preserving the original startup error and continuing cleanup. Manual/release evidence remains pending.

The latest TaskDB concurrency correction atomically reserves pre-migration backup names and uses unique temporary paths, eliminating concurrent Windows first-open collisions. The focused concurrency regression passed 20 consecutive runs; manual/release evidence remains pending.

The latest native self-test checkpoint routes the standalone `--tray-test` timeout through a named timer registry and cleans up the registry/root when watcher construction fails; broader native/manual evidence remains pending.

The latest timer-ownership checkpoint routes CLI run-limit and tray-simulation scheduling through the App-owned named registry and removes direct entrypoint `root.after()` calls; interactive/manual Windows evidence remains pending.

The latest startup-security checkpoint hardens both generated Startup-folder batch launchers and registry startup commands against path metacharacter, percent-expansion, delayed-expansion, and line-break injection, with focused hostile-path coverage. Real startup-shell and target-machine evidence remain pending.

The latest application-log checkpoint redacts unstructured tray diagnostic labels and adds regression coverage for returned values and settings values.

The latest tray-log privacy checkpoint also redacts `RETURNING (via ...)` and `Found in config file:` fallback values; the complete target-user privacy evidence remains pending.

The latest ledger privacy checkpoint bounds free-form `reason` and `target` fields to structural metadata, with regression coverage for private text and path leakage.

The latest observability checkpoint prevents the status window from rendering the absolute data-root path and adds regression coverage; live status interaction remains pending.

The latest browser-provider checkpoint bounds UI Automation COM tab enumeration with a single-flight worker and CDP fallback; focused timeout coverage passes, while live browser/provider evidence remains pending.

The latest native-boundary checkpoint normalizes supervisor console-control and prompt monitor-enumeration callback factories, with source-level coverage across all active callback wrappers; live native evidence remains pending.

The latest callback-portability checkpoint normalizes the remaining primary tray-watcher and dialog-overlay WNDPROC factories to the platform-safe callback fallback, with source-level regression coverage; live native behavior remains pending.

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

The latest settings checkpoint routes tray reloads through the App composition boundary and refreshes coordinator-owned runtime truth, preserving the prior snapshot on load failure; focused lifecycle coverage passes, while interactive tray/settings evidence remains pending.

The latest prompt-regeneration checkpoint rejects scheduling after the composed timer registry closes, preventing raw Tk callbacks during shutdown; focused lifecycle coverage passes, while interactive settings/shutdown evidence remains pending.

The latest overlay checkpoint retains native handles after a failed `DestroyWindow` for retry and releases the brush once destruction succeeds; focused cleanup coverage passes, while live overlay evidence remains pending.

The latest activity-provider checkpoint restricts CDP/UIA URL enrichment to supported browsers, preventing cross-process title collisions; focused coverage passes, while live browser/provider evidence remains pending.

The latest dialog-native checkpoint aligns the parallel `windows_utils` wrapper with primary native failure/retry semantics for click-through, WNDPROC, and overlay destruction; focused coverage passes, while live dialog-overlay evidence remains pending.

The latest overlay-creation checkpoint fails closed on layered-attribute or Z-order setup failure and exposes `set_alpha()` outcomes across both wrappers; focused coverage passes, while live dialog-overlay evidence remains pending.

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

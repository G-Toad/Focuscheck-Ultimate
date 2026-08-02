# Refurbishment Plan Audit

Audit basis: `focuscheck_ultimate_repo_grounded_refurbishment_plan_v1.md`, inspected against repository state at the current refurbishment checkpoint.

Status meanings:

- **Implemented**: the plan requirement has a direct implementation and matching evidence.
- **Partial**: some requested work exists, but one or more explicit requirements are missing.
- **Missing**: no credible implementation or evidence was found.
- **Unverified**: implementation may exist, but the plan requires runtime/manual evidence that is absent.

## Phase Audit

| Plan phase | Status | Evidence and gap |
| --- | --- | --- |
| 0 Repository truth and baseline | Partial | Baseline tests, compile, self-tests, and inventory were captured. Behavior snapshots, profile/registry non-mutation proof, and manual release baseline are absent. |
| 1 Safety and test isolation | Partial | WerFault broad kill was removed, verification uses a disposable data root, hashes the live profile before/after stages, and now guards the repository against unexpected writes plus surviving FocusCheck-owned processes. Settings writes now use an OS-level sidecar lock. Direct `unittest -s tests` still produced live-profile logger contention, and no general filesystem sandbox exists outside the bounded runner. |
| 2 Product contract and contradictions | Partial | Registers and several regression tests exist. The full contradiction/contract closure and complete transition truth tables do not. |
| 3 Verification refurbishment | Partial | Bounded stages, JSON reporting, timeouts, live-profile isolation assertion, repository/process guards, and an injectable service clock exist. Comprehensive fault-injection harnesses, thread/window leak checks, and all required test categories do not. |
| 4 Unified paths and data location | Partial | Frozen `AppPaths` covers canonical data/runtime paths, `FOCUS_DATA_DIR` precedence is fixed, and failed AppData resolution now uses controlled temp recovery rather than the source directory. Legacy hash/revision conflict resolution and complete atomic migration workflow remain absent. |
| 5 Settings repository and schema | Partial | V1/V2 migration, quarantine, rotating `.bak/.bak.1/.bak.2` recovery, migration journal, atomic readback-validated save, OS-level cross-process locking, recursive/file-size input budgets, typed schema descriptors, revision/conflict handling, and fixture classes now exist. Complete UI schema generation and broader migration fixtures remain incomplete. |
| 6 Runtime state coordinator | Partial | `RuntimeStateCoordinator` owns transactional pause/snooze mutation, expiry-aware state, refreshed settings adoption, exclusive prompt/intervention/shutdown leases, clock-injected prompt eligibility, prompt denial during effective pause, website-check suppression through the coordinator, and an App-wired metadata-only transition journal. Full guard synchronization and crash/restart recovery evidence remain absent. |
| 7 Scheduler and timer ownership | Partial | Generation-aware `TimerRegistry` now owns App prompt, heartbeat, snooze, and EngineV2 timers, with 1,000-cycle stress coverage. Runtime-state decisions use an injected clock, while Tk timer scheduling remains UI-controlled, dialog/remaining callback timers remain distributed, and the broader stress matrix is absent. |
| 8 Supervisor and heartbeat | Partial | Versioned generation/readiness/sequence heartbeat validation, PID-bound JSON stop requests, stale checks, force-start correction, circuit breaker, and lifecycle tests now exist. Acknowledgement timeout, sleep-gap handling, and the complete failure matrix are not proven. |
| 9 Startup and single-instance | Partial | Launcher and startup tests now include non-mutating registry inspection for valid and stale/moved-install commands. Duplicate-state correctness, repair execution, and manual registry evidence remain absent. |
| 10 Application lifecycle/composition | Partial | Quit/lifecycle regression tests exist. No composition-root refactor or failure-injection coverage at every startup/shutdown stage was found. |
| 11 Tray adapters | Partial | Command tests and self-test exist; Tk dispatch now targets the recorded owner thread and direct JSON persistence fallback was removed. Complete backend state machine and required native manual matrix are not proven. |
| 12 Windows native wrappers | Partial | Native wrappers retain pointer-sized declarations for key window procedures, and overlay destruction now releases brush/window handles exactly once under a fake-DLL regression test. Complete Win32 signature audit, native stress harness, and live evidence remain absent. |
| 13 Prompt coordinator | Partial | `PromptCoordinator` now owns one active prompt generation and makes polling, tray close, and destruction completion idempotent. Dialog-specific timer/grab cleanup and the complete close-path matrix remain unverified. |
| 14 V1 prompt flow | Unverified | Existing source and tests cover selected flows; the plan's full visible UI, interruption, persistence, cleanup, and manual evidence matrix was not executed. |
| 15 V2 prompt/activity model | Partial | V2 intervention outcome behavior has regression coverage. Full typed activity snapshots, provider isolation, stale/error behavior, and every intervention outcome are not proven. |
| 16 Website flags | Partial | Canonical hostname normalization now rejects ambiguous URL/port/wildcard input, preserves IDN/IP matching, prevents title fallback from overriding an authoritative non-matching host, defines durable `allow_once` dismissal consumption before cooldown, and blocks severity-3 intervention from medium/low-confidence title-only activity; matching/cooldown tests exist. All paused/locked suppression states, provider matrix, and live browser coverage are absent. |
| 17 Intervention coordinator/overlays | Partial | Cancellation no longer consumes cooldown and App now owns an intervention lease/coordinator entry point. Generation cancellation proof, full cleanup matrix, and overlay manual matrix remain absent. |
| 18 Settings UI | Partial | Existing UI tests, revision conflict result handling, and owner-thread/tray contract tests exist. Schema-generated controls, complete visible-control round trips, runtime-consumer proof, and manual UI evidence are absent. |
| 19 Task database | Partial | Stronger SQLite setup, active-task index, transition returns, versioned migration journal, checkpointed backup/restore, concurrent-writer tests, and a UTC normalization/rejection boundary now exist. UI flow tests, legacy-row normalization, and full timezone matrix remain incomplete. |
| 20 Logs/export/privacy/retention | Partial | CSV locking, JSONL rotation, spreadsheet-formula neutralization, diagnostic redaction of user responses, data inventory, and a dry-run-by-default retention tool now exist. Export privacy evidence and complete data-inventory controls remain incomplete. |
| 21 Camera/optional dependencies | Partial | Missing OpenCV/Pillow paths degrade without crashing, capture is opt-in, camera photos use canonical app data or controlled temp recovery rather than the working directory, and failed encodes are reported. Live camera validation and full frame-lifetime evidence remain absent. |
| 22 Browser/activity providers | Partial | Typed activity snapshots normalize provider errors, freshness/confidence, and strip URL query/fragment data; title-only activity is medium confidence and cannot trigger severity-3 intervention; CDP discovery now has a bounded overall deadline and per-request cap with fake-provider tests. Broader provider matrices and live supported-browser evidence remain incomplete. |
| 23 Observability/supportability | Partial | A sanitized bundle generator and bounded Doctor anomaly storage now exist. Structured event schema, throttling, user-facing diagnostics, and verified bundle contents across real failures are incomplete. |
| 24 Security/abuse review | Partial | A dedicated source-level security/abuse review now records data, export, startup, supervisor, and residual-risk controls; penetration testing and target-machine evidence remain absent. |
| 25 Dependencies/packaging | Partial | Runtime requirements are pinned, PyInstaller build/self-test evidence exists, and scripted non-destructive package promotion/rollback now executes in disposable tests. Installer shell integration, signing, and target-machine lifecycle evidence remain open. |
| 26 Performance/resource stability | Partial | Explicit core-service budgets and a disposable timer/state/SQLite soak gate now pass. Long-duration UI/native/camera/browser measurements and production-session budgets remain open. |
| 27 Automated test expansion | Partial | 139 unittest cases, self-tests, a bounded performance soak, repository/process guards, package lifecycle tests, privacy, settings, runtime-state, activity-confidence, and website-domain coercion matrices, and a native cleanup regression exist. Property tests, broader integration breadth, withdrawn-root Tk tests, native live tests, and mutation testing are absent. |
| 28 Manual Windows matrix | Unverified | `docs/refurbishment/manual-evidence.json` explicitly records all five groups as `not_run`. |
| 29 Cleanup after correctness | Missing | The plan's final cleanup/reverification gate cannot be satisfied while release and manual gates remain open. |

## Mandatory Artifacts

All named documentation/report files exist, and migration fixtures plus a diagnostic bundle generator exist. File presence is not completion evidence: `manual-evidence.json` is explicitly `not_run`, and the defect register covers only a subset of the plan's defect register with incomplete required fields such as reproduction, commit/PR, and per-defect manual verification.

The plan's final-release deliverables were also checked individually:

| Required deliverable | Status |
| --- | --- |
| Updated architecture and behaviour specs | Partial; refurbishment maps exist, but the required coordinator architecture is not implemented. |
| Current operation matrix | Present in `docs/refurbishment/CURRENT_OPERATION_MATRIX.md`; manual rows remain explicitly pending. |
| Settings schema/truth table generated or verified | Partial; typed schema descriptors and revision tests exist, but the UI is not generated from the schema and the full truth table is incomplete. |
| Lifecycle/state-machine documentation | Present; implementation and full evidence remain partial. |
| Defect/contradiction registers with no untriaged severity 0/1 | Not met; the defect register is incomplete and several severity-1 items remain unverified. |
| Deterministic verification report | Partial; report is machine-readable and includes a bounded resource-stability gate, but deterministic clock and process/thread/window leak assertions are absent. |
| Manual evidence bundle | Present only as a not-run template. |
| Migration fixtures | Partial; one legacy fixture exists, not the full required fixture set. |
| Release notes | Present in `docs/RELEASE_NOTES.md`; release status remains `NOT_READY`. |
| Rollback instructions | Present in `docs/ROLLBACK.md` and exercised by the disposable package transaction test; target-machine evidence remains open. |
| Packaging/install instructions | Present with scripted promotion/rollback and PyInstaller build contract; installer shell integration and target-machine evidence remain open. |
| Privacy/data-retention documentation | Partial; privacy notes exist, but retention/data inventory controls are incomplete. |
| Support diagnostic instructions | Present in `docs/SUPPORT_DIAGNOSTICS.md`; redaction is pattern-based and target-machine support evidence remains open. |

## Automated Evidence

The bounded runner at `tools/verification_runner.py` currently reports passing stages for compileall, 139 unittest cases, QA scenario, app self-test, tray self-test, settings inventory, diagnostic bundle generation, performance soak, profile isolation, repository-write guarding, and FocusCheck process-leak guarding. The unittest stage also exercises package promotion/rollback, native overlay handle cleanup, runtime transition metadata, cross-process settings locking, UTC task timestamp normalization, settings input budgets, diagnostic response redaction, boolean coercion for every boolean default in the schema, coordinator-owned website pause suppression, canonical website-domain matching, durable `allow_once` consumption, and activity-confidence policy. These stages do not prove the plan's native Windows, installer shell, signing, browser, overlay, sleep/resume, registry, or manual UI requirements.

## Final Acceptance Gates

| Gate | Status | Reason |
| --- | --- | --- |
| A Repository/build | Partial | The source tree and pinned dependency contract are verified, and a disposable PyInstaller build/self-test is evidenced; installer, signing, and deployment verification remain open. |
| B Automated verification | Partial | All eleven bounded stages pass; integration breadth, thread/window leak checks, and full test-category coverage are absent. |
| C Settings/data | Partial | Migration, recovery, backup, atomic save, and revision conflict are tested; complete one-root architecture, migration journal, and all bounded-input fixtures are absent. |
| D Runtime state | Unverified | No complete truth-table/manual evidence proves pause, snooze, guards, effective pause, and duplicate-prompt invariants. |
| E Supervisor/startup | Partial | Several supervisor regressions pass; circuit breaker, generation-bound stop protocol, and native startup evidence are absent. |
| F Tk/tray/UI | Unverified | Source tests and self-tests exist, but owner-thread, tray uniqueness, deterministic dialog cleanup, and persistence-error UI evidence are incomplete. |
| G Prompts/interventions | Partial | Selected cancellation/cooldown behavior is tested; full V1/V2 matrices and orphan-overlay evidence are absent. |
| H Windows native | Unverified | No complete ctypes/resource audit or live lock/sleep/resume/multi-monitor/DPI evidence. |
| I Tasks/logs/privacy | Partial | Some DB and log hardening passes; retention, safe exports, complete privacy controls, and versioned recovery are incomplete. |
| J Release evidence | Not met | Manual checklist is `not_run`; upgrade/rollback and release notes/package consistency are not tested. |

## Explicit Scope Boundary

The plan itself says that static inspection must not be treated as proof of application launch, startup registry behavior, lock/sleep/resume, real browser detection, overlays, packaging, or user-data migration. Those items were checked for evidence and remain unverified or missing; they are not silently inferred from source presence or green automated tests.

## Verdict

The repository is an automated hardening checkpoint, not completion of the V1 refurbishment plan. Release status remains `NOT_READY`. The minimum evidence needed to change that verdict is the missing implementation work above plus completed manual Windows evidence and a reproducible packaging/rollback path.

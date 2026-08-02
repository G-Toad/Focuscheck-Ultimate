# Refurbishment Plan Audit

Audit basis: `focuscheck_ultimate_repo_grounded_refurbishment_plan_v1.md`, inspected against repository state at commit `1b49756`.

Status meanings:

- **Implemented**: the plan requirement has a direct implementation and matching evidence.
- **Partial**: some requested work exists, but one or more explicit requirements are missing.
- **Missing**: no credible implementation or evidence was found.
- **Unverified**: implementation may exist, but the plan requires runtime/manual evidence that is absent.

## Phase Audit

| Plan phase | Status | Evidence and gap |
| --- | --- | --- |
| 0 Repository truth and baseline | Partial | Baseline tests, compile, self-tests, and inventory were captured. Behavior snapshots, profile/registry non-mutation proof, and manual release baseline are absent. |
| 1 Safety and test isolation | Partial | WerFault broad kill was removed and verification uses a disposable data root. No filesystem write guard or process-leak guard was found; direct `unittest -s tests` still produced live-profile logger contention. |
| 2 Product contract and contradictions | Partial | Registers and several regression tests exist. The full contradiction/contract closure and complete transition truth tables do not. |
| 3 Verification refurbishment | Partial | Bounded stages and JSON reporting exist. Deterministic clock, comprehensive fault-injection harnesses, isolation assertions, and all required test categories do not. |
| 4 Unified paths and data location | Partial | Frozen `AppPaths` now covers the canonical data/runtime paths and `FOCUS_DATA_DIR` precedence was fixed. Legacy hash/revision conflict resolution, migration journal, and complete atomic migration workflow remain absent. |
| 5 Settings repository and schema | Partial | V1/V2 migration, quarantine, backup recovery, atomic save, typed schema descriptors, revision/conflict handling, and fixture classes now exist. `.bak.1/.bak.2`, migration journal, complete UI schema generation, and bounded-input coverage remain incomplete. |
| 6 Runtime state coordinator | Partial | `RuntimeStateCoordinator` owns transactional pause/snooze mutation, expiry-aware state, refreshed settings adoption, and exclusive prompt/intervention/shutdown leases. Full App integration, guard synchronization, and transition journal remain absent. |
| 7 Scheduler and timer ownership | Partial | Generation-aware `TimerRegistry` now owns App prompt, heartbeat, snooze, and EngineV2 timers. Dialog/remaining callback timers remain distributed, there is no injected clock, and the required stress matrix is absent. |
| 8 Supervisor and heartbeat | Partial | Versioned generation/readiness/sequence heartbeat validation, PID-bound JSON stop requests, stale checks, force-start correction, circuit breaker, and lifecycle tests now exist. Acknowledgement timeout, sleep-gap handling, and the complete failure matrix are not proven. |
| 9 Startup and single-instance | Partial | Launcher and startup tests exist. Correctness inspection across absent/stale/legacy/duplicate/repairable states, moved-install tests, and manual registry evidence are absent. |
| 10 Application lifecycle/composition | Partial | Quit/lifecycle regression tests exist. No composition-root refactor or failure-injection coverage at every startup/shutdown stage was found. |
| 11 Tray adapters | Partial | Command tests and self-test exist; Tk dispatch now targets the recorded owner thread and direct JSON persistence fallback was removed. Complete backend state machine and required native manual matrix are not proven. |
| 12 Windows native wrappers | Unverified | Existing native modules and documentation exist, but the complete Win32 signature audit, resource ledger validation, native stress harness, and live evidence are absent. |
| 13 Prompt coordinator | Partial | Prompt lifecycle tests/docs exist. There is no single common dialog coordinator proving one outcome, timer ownership, grab cleanup, and duplicate-completion handling for every close path. |
| 14 V1 prompt flow | Unverified | Existing source and tests cover selected flows; the plan's full visible UI, interruption, persistence, cleanup, and manual evidence matrix was not executed. |
| 15 V2 prompt/activity model | Partial | V2 intervention outcome behavior has regression coverage. Full typed activity snapshots, provider isolation, stale/error behavior, and every intervention outcome are not proven. |
| 16 Website flags | Partial | Matching/cooldown tests exist. Confidence model, all paused/locked suppression states, provider matrix, and live browser coverage are absent. |
| 17 Intervention coordinator/overlays | Partial | Cancellation no longer consumes cooldown and App now owns an intervention lease/coordinator entry point. Generation cancellation proof, full cleanup matrix, and overlay manual matrix remain absent. |
| 18 Settings UI | Partial | Existing UI tests, revision conflict result handling, and owner-thread/tray contract tests exist. Schema-generated controls, complete visible-control round trips, runtime-consumer proof, and manual UI evidence are absent. |
| 19 Task database | Partial | Stronger SQLite setup, active-task index, transition returns, versioned migration journal, checkpointed backup/restore, and tests now exist. Concurrent writers, timezone contract, and UI flow tests remain incomplete. |
| 20 Logs/export/privacy/retention | Partial | CSV locking, JSONL rotation, and spreadsheet-formula neutralization now exist. Data inventory, retention policy, export privacy evidence, and bounded doctor anomalies remain incomplete. |
| 21 Camera/optional dependencies | Unverified | Existing camera code is present, but dependency isolation, no-frame-persistence proof, missing-dependency behavior, and live validation are absent. |
| 22 Browser/activity providers | Partial | Typed activity snapshots now normalize provider errors, freshness/confidence, and strip URL query/fragment data. Provider timeouts, fake-provider matrix breadth, and live supported-browser evidence remain incomplete. |
| 23 Observability/supportability | Partial | A sanitized bundle generator exists. Structured event schema, throttling, user-facing diagnostics, and verified bundle contents across real failures are incomplete. |
| 24 Security/abuse review | Missing | No dedicated security/abuse-resistance review artifact or evidence was found. |
| 25 Dependencies/packaging | Partial | Runtime requirements are pinned and PyInstaller spec/build/install/rollback contracts now exist. PyInstaller build, installer lifecycle, signing, and rollback remain unverified. |
| 26 Performance/resource stability | Missing | No explicit resource budgets, soak tests, or performance gates were found. |
| 27 Automated test expansion | Partial | 104 unittest cases and self-tests exist. Property tests, integration breadth, withdrawn-root Tk tests, native tests, and mutation testing are absent. |
| 28 Manual Windows matrix | Unverified | `docs/refurbishment/manual-evidence.json` explicitly records all five groups as `not_run`. |
| 29 Cleanup after correctness | Missing | The plan's final cleanup/reverification gate cannot be satisfied while release and manual gates remain open. |

## Mandatory Artifacts

All 15 named documentation/report files exist, and migration fixtures plus a diagnostic bundle generator exist. File presence is not completion evidence: `manual-evidence.json` is explicitly `not_run`, and the defect register covers only a subset of the plan's defect register with incomplete required fields such as reproduction, commit/PR, and per-defect manual verification.

The plan's final-release deliverables were also checked individually:

| Required deliverable | Status |
| --- | --- |
| Updated architecture and behaviour specs | Partial; refurbishment maps exist, but the required coordinator architecture is not implemented. |
| Current operation matrix | Missing as a clearly identified current matrix. |
| Settings schema/truth table generated or verified | Partial; typed schema descriptors and revision tests exist, but the UI is not generated from the schema and the full truth table is incomplete. |
| Lifecycle/state-machine documentation | Present; implementation and full evidence remain partial. |
| Defect/contradiction registers with no untriaged severity 0/1 | Not met; the defect register is incomplete and several severity-1 items remain unverified. |
| Deterministic verification report | Partial; report is machine-readable, but deterministic clock and leak assertions are absent. |
| Manual evidence bundle | Present only as a not-run template. |
| Migration fixtures | Partial; one legacy fixture exists, not the full required fixture set. |
| Release notes | Missing as a release artifact. |
| Rollback instructions | Present in `docs/ROLLBACK.md`, but untested. |
| Packaging/install instructions | Present as a PyInstaller contract, but unverified on Windows. |
| Privacy/data-retention documentation | Partial; privacy notes exist, but retention/data inventory controls are incomplete. |
| Support diagnostic instructions | Partial; generator exists, but user-facing support instructions are absent. |

## Automated Evidence

The bounded runner at `tools/verification_runner.py` currently reports passing stages for compileall, 104 unittest cases, QA scenario, app self-test, tray self-test, settings inventory, and diagnostic bundle generation. These stages do not prove the plan's native Windows, packaging, browser, overlay, sleep/resume, registry, or manual UI requirements.

## Final Acceptance Gates

| Gate | Status | Reason |
| --- | --- | --- |
| A Repository/build | Partial | The tree is clean and source checks pass, but dependencies are unpinned and no reproducible packaged build exists. |
| B Automated verification | Partial | The seven bounded stages pass; integration breadth, leak checks, and full test-category coverage are absent. |
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

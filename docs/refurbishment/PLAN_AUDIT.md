# Refurbishment Plan Audit

Audit basis: `focuscheck_ultimate_repo_grounded_refurbishment_plan_v1.md`, inspected against repository state at commit `59f665e`.

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
| 4 Unified paths and data location | Partial | `FOCUS_DATA_DIR` precedence was fixed. No frozen `AppPaths`, legacy hash/revision conflict resolution, migration journal, or complete atomic migration workflow exists. |
| 5 Settings repository and schema | Partial | V1/V2 migration, quarantine, backup recovery, atomic save, and several regressions exist. Typed schema descriptors, revision/conflict handling, `.bak.1/.bak.2`, migration journal, and all listed fixtures are missing. |
| 6 Runtime state coordinator | Missing | No dedicated state coordinator or transition journal was found; pause, snooze, guard, prompt, and shutdown state remain distributed. |
| 7 Scheduler and timer ownership | Missing | No `TimerRegistry` or injected clock was found. Timers remain owned by individual components; the required stress matrix is absent. |
| 8 Supervisor and heartbeat | Partial | JSON heartbeat, stale checks, force-start correction, and some lifecycle tests exist. Generation/readiness protocol, circuit breaker, stop handshake, sleep-gap handling, and the complete failure matrix are not proven. |
| 9 Startup and single-instance | Partial | Launcher and startup tests exist. Correctness inspection across absent/stale/legacy/duplicate/repairable states, moved-install tests, and manual registry evidence are absent. |
| 10 Application lifecycle/composition | Partial | Quit/lifecycle regression tests exist. No composition-root refactor or failure-injection coverage at every startup/shutdown stage was found. |
| 11 Tray adapters | Partial | Command tests and self-test exist. Tk dispatch ownership, complete backend state machine, fallback semantics, and required native manual matrix are not proven. |
| 12 Windows native wrappers | Unverified | Existing native modules and documentation exist, but the complete Win32 signature audit, resource ledger validation, native stress harness, and live evidence are absent. |
| 13 Prompt coordinator | Partial | Prompt lifecycle tests/docs exist. There is no single common dialog coordinator proving one outcome, timer ownership, grab cleanup, and duplicate-completion handling for every close path. |
| 14 V1 prompt flow | Unverified | Existing source and tests cover selected flows; the plan's full visible UI, interruption, persistence, cleanup, and manual evidence matrix was not executed. |
| 15 V2 prompt/activity model | Partial | V2 intervention outcome behavior has regression coverage. Full typed activity snapshots, provider isolation, stale/error behavior, and every intervention outcome are not proven. |
| 16 Website flags | Partial | Matching/cooldown tests exist. Confidence model, all paused/locked suppression states, provider matrix, and live browser coverage are absent. |
| 17 Intervention coordinator/overlays | Partial | Cancellation no longer consumes cooldown and state docs exist. No single intervention lease/coordinator, generation cancellation proof, full cleanup matrix, or overlay manual matrix exists. |
| 18 Settings UI | Partial | Existing UI tests and save-result handling exist. Schema-generated controls, complete visible-control round trips, runtime-consumer proof, and manual UI evidence are absent. |
| 19 Task database | Partial | Stronger SQLite setup, active-task index, transition returns, and tests exist. Versioned migration fixtures, concurrent writers, backup/recovery, timezone contract, and UI flow tests are incomplete. |
| 20 Logs/export/privacy/retention | Partial | CSV locking and JSONL rotation were improved. Formula injection, data inventory, retention policy, export privacy, and bounded doctor anomalies are not fully implemented or evidenced. |
| 21 Camera/optional dependencies | Unverified | Existing camera code is present, but dependency isolation, no-frame-persistence proof, missing-dependency behavior, and live validation are absent. |
| 22 Browser/activity providers | Unverified | Providers exist, but timeout, stale/confidence, URL privacy, fake-provider matrix, and live supported-browser evidence are not complete. |
| 23 Observability/supportability | Partial | A sanitized bundle generator exists. Structured event schema, throttling, user-facing diagnostics, and verified bundle contents across real failures are incomplete. |
| 24 Security/abuse review | Missing | No dedicated security/abuse-resistance review artifact or evidence was found. |
| 25 Dependencies/packaging | Missing | `requirements.txt` remains unpinned. No reproducible installer, upgrade/uninstall/rollback process, or signing policy is present. |
| 26 Performance/resource stability | Missing | No explicit resource budgets, soak tests, or performance gates were found. |
| 27 Automated test expansion | Partial | 79 unittest cases and self-tests exist. Property tests, integration breadth, withdrawn-root Tk tests, native tests, and mutation testing are absent. |
| 28 Manual Windows matrix | Unverified | `docs/refurbishment/manual-evidence.json` explicitly records all five groups as `not_run`. |
| 29 Cleanup after correctness | Missing | The plan's final cleanup/reverification gate cannot be satisfied while release and manual gates remain open. |

## Mandatory Artifacts

All 15 named documentation/report files exist, and migration fixtures plus a diagnostic bundle generator exist. File presence is not completion evidence: `manual-evidence.json` is explicitly `not_run`, and the defect register covers only a subset of the plan's defect register with incomplete required fields such as reproduction, commit/PR, and per-defect manual verification.

## Automated Evidence

The bounded runner at `tools/verification_runner.py` currently reports passing stages for compileall, unittest, QA scenario, app self-test, tray self-test, settings inventory, and diagnostic bundle generation. These stages do not prove the plan's native Windows, packaging, browser, overlay, sleep/resume, registry, or manual UI requirements.

## Verdict

The repository is an automated hardening checkpoint, not completion of the V1 refurbishment plan. Release status remains `NOT_READY`. The minimum evidence needed to change that verdict is the missing implementation work above plus completed manual Windows evidence and a reproducible packaging/rollback path.

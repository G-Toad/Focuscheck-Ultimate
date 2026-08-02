# Focus Refurbishment Skill

Use this skill for controlled refurbishment work in the FocusCheck repository.

## Purpose

Make FocusCheck more reliable without broad rewrites or behaviour drift.

## Procedure

1. Read `AGENTS.md`.
2. Read the relevant sections of `docs/BEHAVIOUR_SPEC.md`, `docs/TEST_MATRIX.md`, and `docs/DEBT_REGISTER.md`.
3. Start with a read-only plan for non-trivial tasks.
4. Identify the observable behaviour that must remain unchanged.
5. Add or strengthen characterization tests before changing risky code.
6. Work only on the assigned issue or bounded outcome.
7. Avoid unrelated cleanup and formatting churn.
8. Run:

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify.ps1
```

9. Inspect the complete diff.
10. Request independent review before merge for supervisor, startup, tray, settings, sleep/resume, website flags, or intervention changes.

## Required Review Focus

- Behaviour changes not required by the issue.
- UI thread violations.
- Process lifecycle races.
- State not reset during disarm, exit, lock, resume, or cancellation.
- Error paths missing cleanup.
- Tests that only mirror implementation details.
- Dormant code accidentally reactivated.
- Logs or exceptions being swallowed.

## Output Shape

When finishing a task, report:

- Behaviour changed.
- Tests added or updated.
- Verification command and result.
- Manual Windows checks still required.
- Any remaining uncertainty.

## Constraints

- Do not propose or perform a wholesale rewrite.
- Do not introduce dependencies without concrete benefit and fallback.
- Do not combine unrelated cleanup.
- Do not mutate live user data during automated tests.
- Do not run production UI unless explicitly requested.


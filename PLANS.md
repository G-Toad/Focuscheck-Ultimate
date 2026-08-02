# FocusCheck Execution Plan Template

Use this template for multi-step or high-risk work.

## Objective

State the observable behaviour or defect being addressed.

## Scope

- In scope:
- Out of scope:

## Relevant Behaviour

Reference exact sections in:

- `docs/BEHAVIOUR_SPEC.md`
- `docs/TEST_MATRIX.md`
- `docs/DEBT_REGISTER.md`

## Risk Areas

- Supervisor/startup/tray lifecycle:
- Tk/UI thread behaviour:
- Persistent settings/data:
- V1/V2 prompt or intervention state:
- Windows manual QA required:

## Proposed Change

Describe the smallest coherent change. Do not include unrelated cleanup.

## Characterization Tests

List tests or harness scenarios to add or strengthen before refactoring.

## Verification

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify.ps1
```

List any extra targeted manual commands.

## Rollback Plan

State which commit or files can be reverted if the change fails manual Windows QA.

## Review Checklist

- Behaviour requested by the issue changed.
- Unrelated behaviour did not change.
- UI work stays on the Tk thread.
- Supervisor intentional exit and crash paths remain distinct.
- Startup command still targets the supervisor.
- Settings migrations preserve unknown or legacy data deliberately.
- Logs contain enough evidence for failures.


"""Check that every defect ID in the controlling V1 plan has a register row."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFECT_REGISTER = ROOT / "docs" / "refurbishment" / "DEFECT_REGISTER.md"

# Snapshot of the plan's named defect identifiers. The external controlling
# plan is not required at verification time; this keeps the repository's
# traceability contract reproducible in a clean checkout.
EXPECTED_PLAN_DEFECT_IDS = frozenset({
    'PATH-001', 'PATH-002', 'PATH-003', 'CFG-001', 'CFG-002', 'CFG-003',
    'CFG-004', 'CFG-005', 'CFG-006', 'CFG-007', 'CFG-008', 'CFG-009', 'CFG-010',
    'SUP-001', 'SUP-002', 'SUP-003', 'SUP-004', 'SUP-005', 'SUP-006', 'SUP-007',
    'SUP-008', 'SUP-009', 'SUP-010', 'START-001', 'START-002', 'START-003',
    'START-004', 'START-005', 'PAUSE-001', 'SNOOZE-001', 'SNOOZE-002',
    'SNOOZE-003', 'GUARD-001', 'GUARD-002', 'SCHED-001', 'TRAY-001', 'TRAY-002',
    'TRAY-003', 'TRAY-004', 'TRAY-005', 'UI-001', 'UI-002', 'UI-003', 'UI-004',
    'UI-005', 'PROMPT-001', 'PROMPT-002', 'PROMPT-003', 'ENGINE-001',
    'ENGINE-002', 'ENGINE-003', 'FLAG-001', 'FLAG-002', 'FLAG-003', 'FLAG-004',
    'FLAG-005', 'FLAG-006', 'INT-001', 'INT-002', 'INT-003', 'WIN-001', 'WIN-002',
    'WIN-003', 'WIN-004', 'WIN-005', 'DB-001', 'DB-002', 'DB-003', 'DB-004',
    'DB-005', 'DB-006', 'DB-007', 'DB-008', 'LOGDATA-001', 'LOGDATA-002',
    'LOGDATA-003', 'PRIV-001', 'OBS-001', 'OBS-002', 'DEP-001', 'VERIFY-001',
    'VERIFY-002', 'VERIFY-003', 'PKG-001',
})


def register_ids(path: Path = DEFECT_REGISTER) -> set[str]:
    """Return all data-row IDs from the eight-column defect table."""
    ids: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\|\s*([A-Z][A-Z0-9-]*-\d+)\s*\|", line)
        if match:
            ids.add(match.group(1))
    return ids


def coverage(path: Path = DEFECT_REGISTER) -> dict[str, object]:
    ids = register_ids(path)
    return {
        "expected_plan_ids": len(EXPECTED_PLAN_DEFECT_IDS),
        "registered_ids": len(ids),
        "missing": sorted(EXPECTED_PLAN_DEFECT_IDS - ids),
        "extra": sorted(ids - EXPECTED_PLAN_DEFECT_IDS),
        "complete": EXPECTED_PLAN_DEFECT_IDS <= ids,
    }


def main() -> int:
    result = coverage()
    print(
        f"plan defect coverage: expected={result['expected_plan_ids']} "
        f"registered={result['registered_ids']} complete={result['complete']}"
    )
    if result["missing"]:
        print("missing=" + ",".join(result["missing"]))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

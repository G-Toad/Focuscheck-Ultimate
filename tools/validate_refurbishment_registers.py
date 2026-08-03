"""Validate the markdown defect and contradiction register contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFECT_REGISTER = ROOT / "docs" / "refurbishment" / "DEFECT_REGISTER.md"
CONTRADICTION_REGISTER = ROOT / "docs" / "refurbishment" / "CONTRADICTION_REGISTER.md"
_ALLOWED_DEFECT_STATUSES = {"fixed", "open", "triaged", "deferred", "accepted"}
_ALLOWED_CONTRADICTION_STATUSES = {"fixed", "documented", "open", "deferred"}


def _table_rows(path: Path, prefix: str, expected_columns: int) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith(f"| {prefix}"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != expected_columns or any(not cell for cell in cells):
            raise ValueError(f"malformed register row in {path.name}: {line}")
        rows.append(cells)
    if not rows:
        raise ValueError(f"register has no rows: {path}")
    return rows


def validate_registers(
    defect_path: Path = DEFECT_REGISTER,
    contradiction_path: Path = CONTRADICTION_REGISTER,
) -> dict[str, Any]:
    defects = _table_rows(defect_path, "CFG-", 8)
    # Defect IDs use multiple prefixes; the first parse above establishes the
    # expected table shape, then inspect all data rows from the same file.
    all_defect_rows = []
    for line in defect_path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| ") or line.startswith("| ---") or line.startswith("| ID "):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 8 and cells[0] not in {"ID", "---"}:
            all_defect_rows.append(cells)
    if len(all_defect_rows) < len(defects):
        raise ValueError("defect register contains rows with inconsistent ID prefixes")
    ids: set[str] = set()
    for row in all_defect_rows:
        defect_id, severity, _classification, evidence, fix, tests, manual, status = row
        if defect_id in ids:
            raise ValueError(f"duplicate defect id: {defect_id}")
        ids.add(defect_id)
        try:
            severity_number = int(severity)
        except ValueError as exc:
            raise ValueError(f"invalid severity for {defect_id}: {severity}") from exc
        if severity_number < 0 or severity_number > 3:
            raise ValueError(f"severity outside 0-3 for {defect_id}: {severity}")
        if status not in _ALLOWED_DEFECT_STATUSES:
            raise ValueError(f"invalid defect status for {defect_id}: {status}")
        if severity_number <= 1 and status in {"open", "untriaged"}:
            raise ValueError(f"untriaged severity-{severity_number} defect: {defect_id}")
        if not any(value.strip() for value in (evidence, fix, tests, manual)):
            raise ValueError(f"defect lacks traceability fields: {defect_id}")

    contradictions = _table_rows(contradiction_path, "CONTR-", 5)
    contradiction_ids: set[str] = set()
    for row in contradictions:
        contradiction_id, contradiction, decision, evidence, status = row
        if contradiction_id in contradiction_ids:
            raise ValueError(f"duplicate contradiction id: {contradiction_id}")
        contradiction_ids.add(contradiction_id)
        if status not in _ALLOWED_CONTRADICTION_STATUSES:
            raise ValueError(f"invalid contradiction status for {contradiction_id}: {status}")
        if not all(value.strip() for value in (contradiction, decision, evidence)):
            raise ValueError(f"contradiction lacks traceability fields: {contradiction_id}")

    return {
        "defects": len(all_defect_rows),
        "contradictions": len(contradictions),
        "untriaged_high_severity": 0,
    }


def main() -> int:
    summary = validate_registers()
    print(
        f"valid refurbishment registers: {summary['defects']} defects, "
        f"{summary['contradictions']} contradictions, "
        f"untriaged severity-0/1={summary['untriaged_high_severity']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Safely inspect and record target-machine manual evidence.

This tool deliberately does not infer manual results from automated tests.
Passing or failing a case requires an explicit human confirmation flag.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = ROOT / "docs" / "refurbishment" / "manual-evidence.json"
_CASE_STATUSES = {"not_run", "manual_pass", "manual_fail"}
_OUTCOMES = {"not_run", "pass", "fail"}
_REQUIRED_CASE_FIELDS = {
    "id", "name", "status", "date_utc", "commit", "machine", "exact_steps",
    "expected", "observed", "screenshot_log_references", "pass_fail", "tester",
}


def _read(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_payload(payload)
    return payload


def validate_payload(payload: Any) -> None:
    """Validate the evidence contract without changing it."""
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("manual evidence must be a schema version 1 object")
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("manual evidence must contain cases")
    ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict) or not _REQUIRED_CASE_FIELDS <= set(case):
            raise ValueError("manual evidence case is missing required fields")
        case_id = str(case["id"])
        if not case_id or case_id in ids:
            raise ValueError(f"duplicate or empty manual evidence id: {case_id!r}")
        ids.add(case_id)
        if case.get("status") not in _CASE_STATUSES:
            raise ValueError(f"invalid case status: {case.get('status')!r}")
        expected_status = {
            "not_run": "not_run",
            "manual_pass": "pass",
            "manual_fail": "fail",
        }[case["status"]]
        if case.get("pass_fail") != expected_status:
            raise ValueError(f"case {case_id} has inconsistent status/pass_fail")
    status = payload.get("status")
    if status not in {"not_run", "manual_pass", "manual_fail"}:
        raise ValueError(f"invalid overall manual evidence status: {status!r}")


def _overall_status(cases: list[dict[str, Any]]) -> str:
    statuses = {case["status"] for case in cases}
    if "manual_fail" in statuses:
        return "manual_fail"
    if statuses == {"manual_pass"}:
        return "manual_pass"
    return "not_run"


def _current_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        try:
            Path(temporary).unlink()
        except OSError:
            pass


def record_case(
    path: Path,
    case_id: str,
    outcome: str,
    *,
    observed: str = "",
    tester: str = "",
    machine: str = "",
    screenshots: list[str] | None = None,
    commit: str | None = None,
    date_utc: str | None = None,
    human_confirmed: bool = False,
) -> dict[str, Any]:
    """Record one explicitly observed case and atomically update the file."""
    if outcome not in _OUTCOMES:
        raise ValueError(f"outcome must be one of {sorted(_OUTCOMES)}")
    if outcome in {"pass", "fail"} and not human_confirmed:
        raise ValueError("pass/fail requires --human-confirmed after target-machine execution")
    if outcome in {"pass", "fail"} and not observed.strip():
        raise ValueError("pass/fail requires an observed-result note")
    if not tester.strip() and outcome != "not_run":
        raise ValueError("pass/fail requires a tester name")
    payload = _read(path)
    case = next((candidate for candidate in payload["cases"] if candidate["id"] == case_id), None)
    if case is None:
        raise ValueError(f"unknown manual evidence case: {case_id}")
    case_status = {"not_run": "not_run", "pass": "manual_pass", "fail": "manual_fail"}[outcome]
    case.update({
        "status": case_status,
        "date_utc": date_utc or datetime.now(timezone.utc).isoformat(),
        "commit": commit or _current_commit(),
        "machine": machine or platform.node() or "unknown",
        "observed": observed,
        "screenshot_log_references": list(screenshots or []),
        "pass_fail": outcome,
        "tester": tester,
    })
    payload["status"] = _overall_status(payload["cases"])
    validate_payload(payload)
    _atomic_write(path, payload)
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("list", "validate", "record"))
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--case", dest="case_id")
    parser.add_argument("--outcome", choices=sorted(_OUTCOMES))
    parser.add_argument("--observed", default="")
    parser.add_argument("--tester", default="")
    parser.add_argument("--machine", default="")
    parser.add_argument("--screenshot", action="append", dest="screenshots", default=[])
    parser.add_argument("--commit")
    parser.add_argument("--human-confirmed", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    payload = _read(args.evidence)
    if args.command == "validate":
        print(f"valid manual evidence: {len(payload['cases'])} cases; status={payload['status']}")
        return 0
    if args.command == "list":
        for case in payload["cases"]:
            print(f"{case['id']}\t{case['status']}\t{case['name']}")
        return 0
    if not args.case_id or args.outcome is None:
        raise SystemExit("record requires --case and --outcome")
    record_case(
        args.evidence,
        args.case_id,
        args.outcome,
        observed=args.observed,
        tester=args.tester,
        machine=args.machine,
        screenshots=args.screenshots,
        commit=args.commit,
        human_confirmed=args.human_confirmed,
    )
    print(f"recorded {args.case_id} as {args.outcome}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

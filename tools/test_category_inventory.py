"""Validate the explicit automated/manual test-category contract."""

from __future__ import annotations

import argparse
import fnmatch
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "refurbishment" / "test-category-manifest.json"
OUTPUT = ROOT / "_verify_runtime" / "test-category-inventory.json"


def build_inventory() -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    categories = manifest.get("categories")
    if not isinstance(categories, dict) or not categories:
        raise ValueError("test category manifest has no categories")

    inventory = {}
    for name, definition in categories.items():
        status = definition.get("status")
        patterns = definition.get("patterns", [])
        if status not in {"automated", "manual_required", "opt_in_required"}:
            raise ValueError(f"invalid status for {name}: {status}")
        matches = sorted(
            str(path.relative_to(ROOT)).replace("\\", "/")
            for path in ROOT.glob("tests/*.py")
            if any(fnmatch.fnmatch(str(path.relative_to(ROOT)).replace("\\", "/"), pattern) for pattern in patterns)
        )
        if status == "automated" and not matches:
            raise ValueError(f"automated category has no test files: {name}")
        inventory[name] = {
            "status": status,
            "patterns": patterns,
            "matched_files": matches,
            "evidence_file": definition.get("evidence_file"),
        }

    return {
        "schema_version": manifest.get("schema_version"),
        "categories": inventory,
        "automated_categories": sorted(name for name, item in inventory.items() if item["status"] == "automated"),
        "manual_categories": sorted(name for name, item in inventory.items() if item["status"] != "automated"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    payload = build_inventory()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

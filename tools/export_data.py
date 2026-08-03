"""Command-line wrapper for the packaged FocusCheck data export service."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Direct script execution starts with ``tools`` on sys.path, not the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from focuscheck.utils.data_export import CATEGORIES, export_data, validate_export


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--include", nargs="+", choices=CATEGORIES, default=("logs", "metadata"))
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--verify", action="store_true", help="validate an existing export archive")
    args = parser.parse_args()
    if args.verify:
        print(json.dumps(validate_export(args.output), indent=2, sort_keys=True))
        return 0
    if args.source is None:
        parser.error("--source is required unless --verify is used")
    manifest = export_data(args.source, args.output, categories=args.include, overwrite=args.overwrite)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

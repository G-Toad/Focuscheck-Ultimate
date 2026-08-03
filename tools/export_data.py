"""Command-line wrapper for the packaged FocusCheck data export service."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Direct script execution starts with ``tools`` on sys.path, not the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from focuscheck.utils.data_export import CATEGORIES, export_data, import_data, validate_export


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--include", nargs="+", choices=CATEGORIES)
    parser.add_argument("--overwrite", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--verify", action="store_true", help="validate an existing export archive")
    mode.add_argument("--import-archive", type=Path, help="restore selected user data from an export archive")
    parser.add_argument("--destination", type=Path, help="data root for --import-archive")
    parser.add_argument("--confirm-sensitive", action="store_true", help="confirm settings/tasks/camera restore")
    args = parser.parse_args()
    if args.verify:
        if args.output is None:
            parser.error("--output is required with --verify")
        print(json.dumps(validate_export(args.output), indent=2, sort_keys=True))
        return 0
    if args.import_archive is not None:
        if args.destination is None:
            parser.error("--destination is required with --import-archive")
        include = args.include or ("settings", "tasks")
        manifest = import_data(
            args.import_archive,
            args.destination,
            categories=include,
            overwrite=args.overwrite,
            confirmed=args.confirm_sensitive,
        )
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return 0
    if args.source is None:
        parser.error("--source is required unless --verify is used")
    if args.output is None:
        parser.error("--output is required for export")
    manifest = export_data(args.source, args.output, categories=args.include or ("logs", "metadata"), overwrite=args.overwrite)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

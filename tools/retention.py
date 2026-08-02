"""Command-line wrapper for the packaged retention service."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from focuscheck.utils.data_retention import apply_retention, retention_plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--max-age-days", type=int, default=90)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(apply_retention(args.root, max_age_days=args.max_age_days, apply=args.apply), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

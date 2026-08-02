"""Command-line wrapper for the packaged diagnostic bundle service."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

DEFAULT_RUNTIME = Path(__file__).resolve().parents[1] / "_verify_runtime"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from focuscheck.utils.diagnostics import create_bundle, preview_bundle, sanitize


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    output = args.output or args.runtime / "diagnostic_bundle.zip"
    print(create_bundle(args.runtime, output, overwrite=args.overwrite or output.exists()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

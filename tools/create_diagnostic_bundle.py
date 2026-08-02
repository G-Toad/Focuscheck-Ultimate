"""Create a sanitized diagnostic bundle from disposable verification output."""

from __future__ import annotations

import argparse
import os
import re
import zipfile
from pathlib import Path


DEFAULT_RUNTIME = Path(__file__).resolve().parents[1] / "_verify_runtime"
_SECRET_PATTERNS = (
    re.compile(r"(?i)(password|token|secret|api[_ -]?key)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]+"),
)


def sanitize(text: str, *, root: Path) -> str:
    """Redact usernames, local roots, and common credential-shaped values."""
    result = text.replace(str(root), "<verification-root>")
    result = result.replace(str(Path.home()), "<user-home>")
    result = re.sub(r"(?i)C:\\Users\\[^\\\r\n]+", "<windows-user-path>", result)
    for pattern in _SECRET_PATTERNS:
        result = pattern.sub(lambda match: match.group(1) + "=<redacted>" if "=" in match.group(0) or ":" in match.group(0) else "Bearer <redacted>", result)
    return result


def create_bundle(runtime: Path, output: Path) -> Path:
    runtime = runtime.resolve()
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    candidates = sorted(runtime.glob("*.log")) + [
        runtime / "verification.json",
        runtime / "structured_events.jsonl",
    ]
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source in candidates:
            if source.is_file():
                archive.writestr(source.name, sanitize(source.read_text(encoding="utf-8", errors="replace"), root=runtime))
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or args.runtime / "diagnostic_bundle.zip"
    print(create_bundle(args.runtime, output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

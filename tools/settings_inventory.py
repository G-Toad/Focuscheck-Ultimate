"""Print a reference inventory for every FocusCheck default setting."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {"_archive", "_qa_runtime", "ports", "__pycache__"}
SKIP_FILES = {
    "focuscheck/settings/defaults.py",
    "focuscheck/settings/registry.py",
}


def _load_defaults():
    module = ast.parse((ROOT / "focuscheck/settings/defaults.py").read_text(encoding="utf-8"))
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "DEFAULT_SETTINGS":
                return ast.literal_eval(node.value)
    raise RuntimeError("DEFAULT_SETTINGS assignment not found")


def _source_files():
    for base in ("focuscheck", "tests", "tools"):
        for path in (ROOT / base).rglob("*.py"):
            rel = path.relative_to(ROOT).as_posix()
            if any(part in SKIP_PARTS for part in path.parts):
                continue
            if rel in SKIP_FILES:
                continue
            yield path


def main() -> int:
    defaults = _load_defaults()
    files = list(_source_files())
    try:
        print(f"settings={len(defaults)}")
        print("key\treferences\tfiles")
        for key in sorted(defaults):
            refs = []
            for path in files:
                text = path.read_text(encoding="utf-8", errors="ignore")
                if key in text:
                    refs.append(path.relative_to(ROOT).as_posix())
            print(f"{key}\t{len(refs)}\t{', '.join(refs)}")
    except OSError:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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


def _ui_save_keys():
    """Extract literal keys persisted by the hand-built settings window."""
    path = ROOT / "focuscheck" / "ui" / "windows.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    keys = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != "_save":
            continue
        for child in ast.walk(node):
            if not isinstance(child, ast.Dict):
                continue
            for key in child.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    keys.add(key.value)
    return keys


def _runtime_source_files():
    """Return application files outside the settings editor and test/tool trees."""
    files = []
    for path in (ROOT / "focuscheck").rglob("*.py"):
        rel = path.relative_to(ROOT).as_posix()
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if rel == "focuscheck/ui/windows.py" or rel.startswith("focuscheck/ui/settings_tabs/") or rel in SKIP_FILES:
            continue
        files.append(path)
    return files


def main() -> int:
    defaults = _load_defaults()
    files = list(_source_files())
    runtime_files = _runtime_source_files()
    try:
        print(f"settings={len(defaults)}")
        visible_keys = sorted(_ui_save_keys() - {"settings_revision"})
        runtime_only_refs = {
            key: [path.relative_to(ROOT).as_posix() for path in runtime_files if key in path.read_text(encoding="utf-8", errors="ignore")]
            for key in visible_keys
        }
        missing_runtime = [key for key, refs in runtime_only_refs.items() if not refs]
        print(f"visible_save_keys={len(visible_keys)}")
        print(f"visible_without_runtime_consumer={len(missing_runtime)}")
        if missing_runtime:
            print("missing_runtime_keys=" + ",".join(missing_runtime))
        print("key\treferences\tfiles")
        for key in sorted(defaults):
            refs = []
            for path in files:
                text = path.read_text(encoding="utf-8", errors="ignore")
                if key in text:
                    refs.append(path.relative_to(ROOT).as_posix())
            print(f"{key}\t{len(refs)}\t{', '.join(refs)}")
    except (OSError, SyntaxError, ValueError):
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

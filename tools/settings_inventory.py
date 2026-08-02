"""Print a reference inventory for every FocusCheck default setting."""

from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
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
    """Return keys persisted by both hand-built and generated UI controls."""
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
    # The advanced tab is generated from the canonical schema and therefore
    # cannot be discovered by walking literal dictionaries in ``_save``.
    from focuscheck.ui.schema_controls import EXISTING_DYNAMIC_KEYS, SCHEMA_CONTROL_KEYS

    return keys | set(EXISTING_DYNAMIC_KEYS) | set(SCHEMA_CONTROL_KEYS)


def _non_visible_classifications():
    from focuscheck.ui.schema_controls import NON_VISIBLE_SETTING_CLASSIFICATIONS

    return dict(NON_VISIBLE_SETTING_CLASSIFICATIONS)


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
        excluded = _non_visible_classifications()
        unclassified = sorted((set(defaults) - set(visible_keys)) - set(excluded))
        unexpected_classifications = sorted(set(excluded) - set(defaults) - {"settings_revision"})
        runtime_only_refs = {
            key: [path.relative_to(ROOT).as_posix() for path in runtime_files if key in path.read_text(encoding="utf-8", errors="ignore")]
            for key in visible_keys
        }
        missing_runtime = [key for key, refs in runtime_only_refs.items() if not refs]
        print(f"visible_save_keys={len(visible_keys)}")
        print(f"visible_without_runtime_consumer={len(missing_runtime)}")
        print(f"classified_non_visible={len(set(defaults) & set(excluded))}")
        print(f"unclassified_non_visible={len(unclassified)}")
        if unexpected_classifications:
            print("unexpected_classifications=" + ",".join(unexpected_classifications))
        if unclassified:
            print("unclassified_keys=" + ",".join(unclassified))
        if unclassified or unexpected_classifications:
            return 1
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

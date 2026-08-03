"""Print a reference inventory for every FocusCheck default setting."""

from __future__ import annotations

import ast
import argparse
import json
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


def build_inventory() -> dict:
    """Build a deterministic, per-key settings truth inventory."""
    defaults = _load_defaults()
    files = list(_source_files())
    runtime_files = _runtime_source_files()
    visible_keys = _ui_save_keys() - {"settings_revision"}
    classifications = _non_visible_classifications()
    from focuscheck.settings.schema import get_settings_schema
    from focuscheck.ui.schema_controls import SCHEMA_CONTROL_KEYS

    schema = get_settings_schema()
    keys = []
    for key in sorted(defaults):
        descriptor = schema[key]
        references = [
            path.relative_to(ROOT).as_posix()
            for path in files
            if key in path.read_text(encoding="utf-8", errors="ignore")
        ]
        runtime_references = [
            path.relative_to(ROOT).as_posix()
            for path in runtime_files
            if key in path.read_text(encoding="utf-8", errors="ignore")
        ]
        if key in visible_keys:
            classification = "active_user_facing"
            ui_owner = "schema_generated" if key in SCHEMA_CONTROL_KEYS else "hand_built_or_specialized"
        else:
            classification = classifications.get(key, "unclassified")
            ui_owner = "none"
        keys.append({
            "key": key,
            "classification": classification,
            "ui_owner": ui_owner,
            "canonical_type": descriptor.canonical_type,
            "default": descriptor.default,
            "ui_section": descriptor.ui_section,
            "sensitivity": descriptor.sensitivity,
            "persistence_class": descriptor.persistence_class,
            "deprecated": descriptor.deprecated,
            "runtime_consumer": descriptor.runtime_consumer,
            "runtime_references": runtime_references,
            "references": references,
        })
    return {
        "schema_version": 1,
        "default_key_count": len(defaults),
        "visible_key_count": len(visible_keys),
        "non_visible_key_count": len(defaults) - len(visible_keys),
        "keys": keys,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    inventory = build_inventory()
    defaults = {item["key"] for item in inventory["keys"]}
    visible_keys = {item["key"] for item in inventory["keys"] if item["classification"] == "active_user_facing"}
    classifications = _non_visible_classifications()
    unclassified = sorted(item["key"] for item in inventory["keys"] if item["classification"] == "unclassified")
    unexpected_classifications = sorted(set(classifications) - defaults - {"settings_revision"})
    try:
        print(f"settings={inventory['default_key_count']}")
        missing_runtime = sorted(item["key"] for item in inventory["keys"] if item["classification"] == "active_user_facing" and not item["runtime_references"])
        print(f"visible_save_keys={len(visible_keys)}")
        print(f"visible_without_runtime_consumer={len(missing_runtime)}")
        print(f"classified_non_visible={inventory['non_visible_key_count'] - len(unclassified)}")
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
        for item in inventory["keys"]:
            print(f"{item['key']}\t{len(item['references'])}\t{', '.join(item['references'])}")
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(inventory, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
            print(f"inventory_json={args.output}")
    except (OSError, SyntaxError, ValueError):
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

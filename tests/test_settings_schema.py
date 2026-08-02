"""Static contracts between the hand-built settings UI and canonical schema."""

from __future__ import annotations

import ast
from pathlib import Path
import unittest

from focuscheck.settings.schema import get_settings_schema, schema_manifest


class SettingsSchemaContractTests(unittest.TestCase):
    def test_visible_save_keys_are_registered_and_state_only_keys_are_excluded(self):
        source_path = Path(__file__).resolve().parents[1] / "focuscheck" / "ui" / "windows.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        save_keys: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_save":
                for child in ast.walk(node):
                    if isinstance(child, ast.Dict):
                        for key in child.keys:
                            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                                save_keys.add(key.value)

        schema = get_settings_schema()
        self.assertTrue(save_keys)
        self.assertEqual(set(), save_keys - set(schema) - {"settings_revision"})
        self.assertNotIn("paused", save_keys)
        self.assertNotIn("snooze_until_utc", save_keys)
        self.assertTrue(all(schema[key].ui_section for key in save_keys if key in schema))

    def test_schema_manifest_is_sorted_and_json_ready(self):
        manifest = schema_manifest()
        self.assertEqual(sorted(item["key"] for item in manifest), [item["key"] for item in manifest])
        self.assertTrue(all({"key", "canonical_type", "default", "ui_section"}.issubset(item) for item in manifest))

    def test_visible_settings_have_runtime_consumers_outside_editor(self):
        from tools import settings_inventory

        runtime_files = settings_inventory._runtime_source_files()
        missing = [
            key for key in settings_inventory._ui_save_keys()
            if key != "settings_revision"
            and not any(key in path.read_text(encoding="utf-8", errors="ignore") for path in runtime_files)
        ]
        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()

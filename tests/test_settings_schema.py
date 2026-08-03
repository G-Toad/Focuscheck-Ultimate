"""Static contracts between the hand-built settings UI and canonical schema."""

from __future__ import annotations

import ast
from pathlib import Path
import unittest

from focuscheck.settings.schema import SENSITIVE_SETTING_KEYS, get_settings_schema, schema_manifest
from focuscheck.ui.schema_controls import (
    EXISTING_DYNAMIC_KEYS,
    NON_VISIBLE_SETTING_CLASSIFICATIONS,
    SCHEMA_CONTROL_KEYS,
)


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

    def test_sensitive_setting_registry_is_explicit_and_schema_backed(self):
        schema = get_settings_schema()
        self.assertTrue(SENSITIVE_SETTING_KEYS)
        self.assertTrue(SENSITIVE_SETTING_KEYS <= set(schema))
        self.assertTrue(all(schema[key].sensitivity == "sensitive" for key in SENSITIVE_SETTING_KEYS))
        self.assertEqual("sensitive", schema["webhook_url"].sensitivity)
        self.assertEqual("sensitive", schema["website_flags"].sensitivity)

    def test_generated_controls_are_schema_keys_and_exclude_runtime_state(self):
        schema = get_settings_schema()
        self.assertTrue(set(SCHEMA_CONTROL_KEYS) <= set(schema))
        self.assertTrue(set(EXISTING_DYNAMIC_KEYS) <= set(schema))
        self.assertNotIn("paused", SCHEMA_CONTROL_KEYS)
        self.assertNotIn("snooze_until_utc", SCHEMA_CONTROL_KEYS)
        self.assertNotIn("settings_revision", SCHEMA_CONTROL_KEYS)
        self.assertNotIn("webhook_url", SCHEMA_CONTROL_KEYS)
        self.assertIn("gentle_reminder_interval", SCHEMA_CONTROL_KEYS)

        from tools import settings_inventory

        self.assertTrue(set(SCHEMA_CONTROL_KEYS) <= settings_inventory._ui_save_keys())
        self.assertTrue(set(EXISTING_DYNAMIC_KEYS) <= settings_inventory._ui_save_keys())

    def test_visible_settings_have_runtime_consumers_outside_editor(self):
        from tools import settings_inventory

        runtime_files = settings_inventory._runtime_source_files()
        missing = [
            key for key in settings_inventory._ui_save_keys()
            if key != "settings_revision"
            and not any(key in path.read_text(encoding="utf-8", errors="ignore") for path in runtime_files)
        ]
        self.assertEqual([], missing)

    def test_every_non_visible_default_has_an_explicit_classification(self):
        from tools import settings_inventory

        defaults = set(settings_inventory._load_defaults())
        visible = settings_inventory._ui_save_keys() - {"settings_revision"}
        excluded = set(NON_VISIBLE_SETTING_CLASSIFICATIONS)
        self.assertEqual(set(), (defaults - visible) - excluded)
        self.assertEqual(set(), excluded - defaults - {"settings_revision"})


if __name__ == "__main__":
    unittest.main()

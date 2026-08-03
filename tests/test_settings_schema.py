"""Static contracts between the hand-built settings UI and canonical schema."""

from __future__ import annotations

import ast
from pathlib import Path
import unittest
from unittest import mock

from focuscheck.settings.defaults import DEFAULT_SETTINGS
from focuscheck.settings.schema import SENSITIVE_SETTING_KEYS, get_settings_schema, schema_manifest
from focuscheck.ui.schema_controls import (
    EXISTING_DYNAMIC_KEYS,
    NON_VISIBLE_SETTING_CLASSIFICATIONS,
    SCHEMA_CONTROL_KEYS,
)


class SettingsSchemaContractTests(unittest.TestCase):
    def test_hand_built_controls_round_trip_through_save_payload(self):
        """Exercise the real hand-built _save mapping without requiring Tk."""
        from focuscheck.ui.windows import AdvancedSettingsWindow

        source_path = Path(__file__).resolve().parents[1] / "focuscheck" / "ui" / "windows.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        bindings: dict[str, str] = {}
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or node.name != "_save":
                continue
            for child in ast.walk(node):
                if not isinstance(child, ast.Dict):
                    continue
                for key, value in zip(child.keys, child.values):
                    if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                        continue
                    for ref in ast.walk(value):
                        if isinstance(ref, ast.Attribute) and ref.attr.endswith("_var"):
                            bindings[ref.attr] = key.value

        class FakeVariable:
            def __init__(self, value):
                self.value = value

            def get(self):
                return self.value

        window = AdvancedSettingsWindow.__new__(AdvancedSettingsWindow)
        window.settings = dict(DEFAULT_SETTINGS)
        window.on_save = mock.Mock()
        window.persist_settings = mock.Mock(return_value=True)
        window.destroy = mock.Mock()
        window._schema_settings = mock.Mock()
        window._schema_settings.values.return_value = {}

        for attr, key in bindings.items():
            self.assertIn(key, DEFAULT_SETTINGS, key)
            value = DEFAULT_SETTINGS[key]
            # Tk StringVar/DoubleVar values arrive as text; BooleanVar keeps
            # a bool. Model that boundary so fallback parsing is exercised.
            window.__dict__[attr] = FakeVariable(value if isinstance(value, bool) else str(value))
        window.study_phrase_list = list(DEFAULT_SETTINGS["study_phrase_list"])
        window.waste_phrase_list = list(DEFAULT_SETTINGS["waste_phrase_list"])
        window.snooze_sentence_list = list(DEFAULT_SETTINGS["snooze_prompt_sentences"])
        window.website_flags_list = list(DEFAULT_SETTINGS["website_flags"])
        window.studying_challenge_vars = {
            challenge_id: FakeVariable(DEFAULT_SETTINGS[f"challenge_studying_{challenge_id}_enabled"])
            for challenge_id, _, _ in window.STUDYING_CHALLENGES
        }
        window.wasting_challenge_vars = {
            challenge_id: FakeVariable(DEFAULT_SETTINGS[f"challenge_wasting_{challenge_id}_enabled"])
            for challenge_id, _, _ in window.WASTING_CHALLENGES
        }

        window._save()

        window.persist_settings.assert_called_once()
        payload = window.persist_settings.call_args.args[0]
        for key in bindings.values():
            self.assertIn(key, payload, key)
            self.assertEqual(DEFAULT_SETTINGS[key], payload[key], key)
        for challenge_id in window.studying_challenge_vars:
            key = f"challenge_studying_{challenge_id}_enabled"
            self.assertEqual(DEFAULT_SETTINGS[key], payload[key], key)
        for challenge_id in window.wasting_challenge_vars:
            key = f"challenge_wasting_{challenge_id}_enabled"
            self.assertEqual(DEFAULT_SETTINGS[key], payload[key], key)

    def test_hand_built_controls_have_save_payload_bindings(self):
        source_path = Path(__file__).resolve().parents[1] / "focuscheck" / "ui" / "windows.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        init_vars: set[str] = set()
        save_bindings: dict[str, set[str]] = {}

        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name == "_init_vars":
                for child in ast.walk(node):
                    if not isinstance(child, ast.Assign):
                        continue
                    for target in child.targets:
                        if isinstance(target, ast.Attribute) and target.attr.endswith("_var"):
                            init_vars.add(target.attr)
            elif node.name == "_save":
                for child in ast.walk(node):
                    if not isinstance(child, ast.Dict):
                        continue
                    for key, value in zip(child.keys, child.values):
                        if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                            continue
                        for ref in ast.walk(value):
                            if isinstance(ref, ast.Attribute) and ref.attr.endswith("_var"):
                                save_bindings.setdefault(ref.attr, set()).add(key.value)

        # webhook_var is intentionally retained only for legacy compatibility
        # and is hidden from the active settings UI/save payload.
        self.assertNotIn("webhook_var", save_bindings)
        missing = sorted(init_vars - {"webhook_var"} - set(save_bindings))
        self.assertEqual([], missing)

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

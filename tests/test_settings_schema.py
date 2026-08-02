from __future__ import annotations

import json
import unittest


class SettingsSchemaTests(unittest.TestCase):
    def test_schema_covers_defaults_and_is_json_ready(self):
        from focuscheck.settings.defaults import DEFAULT_SETTINGS
        from focuscheck.settings.schema import schema_manifest

        manifest = schema_manifest()
        self.assertEqual(set(DEFAULT_SETTINGS), {item["key"] for item in manifest})
        json.dumps(manifest)
        for item in manifest:
            self.assertTrue(item["canonical_type"])
            self.assertIn(item["sensitivity"], {"normal", "sensitive"})
            self.assertTrue(item["ui_section"])

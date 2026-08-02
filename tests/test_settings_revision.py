from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class SettingsRevisionTests(unittest.TestCase):
    def test_stale_revision_is_rejected_and_current_file_is_preserved(self):
        from focuscheck.settings import manager

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "focus_settings.json"
            path.write_text(json.dumps({"settings_revision": 4, "interval_seconds": 60}), encoding="utf-8")
            with mock.patch.object(manager, "choose_path", return_value=str(path)):
                self.assertFalse(manager.save_settings({"settings_revision": 3, "interval_seconds": 30}))
            current = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(4, current["settings_revision"])
            self.assertEqual(60, current["interval_seconds"])

    def test_save_increments_revision(self):
        from focuscheck.settings import manager

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "focus_settings.json"
            with mock.patch.object(manager, "choose_path", return_value=str(path)):
                self.assertTrue(manager.save_settings({"settings_revision": 0, "interval_seconds": 30}))
                first = json.loads(path.read_text(encoding="utf-8"))
                self.assertTrue(manager.save_settings({"settings_revision": first["settings_revision"], "interval_seconds": 40}))
            second = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(2, second["settings_revision"])
            self.assertEqual(40, second["interval_seconds"])

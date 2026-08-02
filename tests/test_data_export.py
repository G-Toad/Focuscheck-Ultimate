from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path


class DataExportTests(unittest.TestCase):
    def test_default_export_excludes_sensitive_categories_and_writes_manifest(self):
        from tools.export_data import export_data

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            root = Path(temp_dir) / "data"
            output = Path(temp_dir) / "exports" / "focus.zip"
            root.mkdir()
            (root / "focus_log.csv").write_text("header\n", encoding="utf-8")
            (root / "structured_events.jsonl").write_text('{"category":"runtime"}\n', encoding="utf-8")
            (root / "focus_settings.json").write_text('{"private":"value"}', encoding="utf-8")
            (root / "focus_tasks.sqlite3").write_bytes(b"private tasks")

            manifest = export_data(root, output)

            self.assertEqual(["logs", "metadata"], manifest["categories"])
            self.assertEqual({"focus_log.csv", "structured_events.jsonl", "EXPORT_MANIFEST.json"},
                             set(zipfile.ZipFile(output).namelist()))
            self.assertTrue(all(not item["sensitive"] for item in manifest["files"]))

    def test_sensitive_categories_require_explicit_selection_and_manifest_hashes_files(self):
        from tools.export_data import export_data

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            root = Path(temp_dir) / "data"
            output = Path(temp_dir) / "export.zip"
            root.mkdir()
            (root / "focus_settings.json").write_text('{"private":"value"}', encoding="utf-8")

            manifest = export_data(root, output, categories=("settings",))
            self.assertEqual(["settings"], manifest["categories"])
            self.assertTrue(manifest["files"][0]["sensitive"])
            with zipfile.ZipFile(output) as archive:
                embedded = json.loads(archive.read("EXPORT_MANIFEST.json"))
            self.assertEqual(manifest, embedded)

    def test_export_rejects_symlink_sources_and_existing_destination(self):
        from tools.export_data import export_data

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            root = Path(temp_dir) / "data"
            root.mkdir()
            source = root / "focus_log.csv"
            source.write_text("safe", encoding="utf-8")
            output = Path(temp_dir) / "export.zip"
            export_data(root, output)
            with self.assertRaises(FileExistsError):
                export_data(root, output)

            link = root / "focus_waste_log.csv"
            try:
                link.symlink_to(source)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            with self.assertRaises(ValueError):
                export_data(root, Path(temp_dir) / "symlink.zip")

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


class DataExportTests(unittest.TestCase):
    def test_inventory_is_metadata_only_and_clear_requires_confirmation(self):
        from focuscheck.utils.data_export import clear_data, inventory_data

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            root = Path(temp_dir) / "data"
            root.mkdir()
            (root / "focus_log.csv").write_text("private response", encoding="utf-8")
            (root / "focus_settings.json").write_text('{"private":"value"}', encoding="utf-8")
            (root / "focus_tasks.sqlite3").write_bytes(b"private tasks")

            inventory = inventory_data(root)
            self.assertEqual({"focus_log.csv", "focus_settings.json", "focus_tasks.sqlite3"},
                             {item["path"] for item in inventory["files"]})
            self.assertNotIn("private response", json.dumps(inventory))
            with self.assertRaises(PermissionError):
                clear_data(root, categories=("logs",), confirmed=False)

            report = clear_data(root, categories=("logs",), confirmed=True)
            self.assertEqual(["logs"], report["categories"])
            self.assertFalse((root / "focus_log.csv").exists())
            self.assertTrue((root / "focus_settings.json").exists())
            self.assertTrue((root / "focus_tasks.sqlite3").exists())
            self.assertIn('"operation":"clear_data"', (root / "data_clear_audit.jsonl").read_text(encoding="utf-8"))
            self.assertIn('"format_version":1', (root / "data_clear_audit.jsonl").read_text(encoding="utf-8"))

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

    def test_validate_export_checks_manifest_and_member_hashes(self):
        from focuscheck.utils.data_export import export_data, validate_export

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "data"
            output = Path(temp_dir) / "export.zip"
            root.mkdir()
            (root / "focus_log.csv").write_text("safe", encoding="utf-8")
            export_data(root, output)

            manifest = validate_export(output)
            self.assertEqual(1, manifest["format_version"])

            tampered = Path(temp_dir) / "tampered.zip"
            with zipfile.ZipFile(output) as source, zipfile.ZipFile(tampered, "w") as target:
                for info in source.infolist():
                    target.writestr(info, b"tampered" if info.filename == "focus_log.csv" else source.read(info))
            with self.assertRaises(ValueError):
                validate_export(tampered)

    def test_validate_export_rejects_traversal_and_future_versions(self):
        from focuscheck.utils.data_export import validate_export

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            traversal = root / "traversal.zip"
            with zipfile.ZipFile(traversal, "w") as archive:
                archive.writestr("../escape.txt", "bad")
                archive.writestr("EXPORT_MANIFEST.json", json.dumps({
                    "format_version": 1,
                    "categories": ["logs"],
                    "files": [{"path": "../escape.txt", "category": "logs", "size": 3,
                               "sha256": "x", "sensitive": False}],
                }))
            with self.assertRaises(ValueError):
                validate_export(traversal)

            future = root / "future.zip"
            with zipfile.ZipFile(future, "w") as archive:
                archive.writestr("EXPORT_MANIFEST.json", json.dumps({
                    "format_version": 99, "categories": [], "files": [],
                }))
            with self.assertRaises(ValueError):
                validate_export(future)

    def test_inventory_covers_known_operational_and_recovery_artifacts_without_contents(self):
        from focuscheck.utils.data_export import inventory_data

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifacts = {
                "focus_app.log": "private app detail",
                "focuscheck_supervisor.log": "private supervisor detail",
                "focus_settings.json.corrupt-2026": "private settings",
                "focus_settings.json.migration.jsonl": "private migration detail",
                "retention_audit.jsonl": "private retention detail",
                "hb.txt": "private heartbeat detail",
                "diagnostic_bundle.zip": "private bundle bytes",
                "camera_1.png": "private camera bytes",
            }
            for name, value in artifacts.items():
                (root / name).write_text(value, encoding="utf-8")

            report = inventory_data(root)
            indexed = {item["path"]: item for item in report["files"]}

            self.assertEqual(set(artifacts), set(indexed))
            self.assertTrue(all("size" in item and "sensitive" in item for item in indexed.values()))
            self.assertNotIn("private app detail", json.dumps(report))
            self.assertNotIn("private settings", json.dumps(report))
            self.assertTrue(indexed["focus_settings.json.corrupt-2026"]["sensitive"])
            self.assertFalse(indexed["hb.txt"]["sensitive"])

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

    def test_export_rejects_destination_that_is_an_input_file(self):
        from focuscheck.utils.data_export import export_data

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "data"
            root.mkdir()
            source = root / "focus_log.csv"
            source.write_text("safe", encoding="utf-8")
            with self.assertRaises(ValueError):
                export_data(root, source, overwrite=True)
            self.assertEqual("safe", source.read_text(encoding="utf-8"))

    def test_export_rejects_source_mutation_before_promoting_archive(self):
        from focuscheck.utils.data_export import export_data

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            root = Path(temp_dir) / "data"
            root.mkdir()
            source = root / "focus_log.csv"
            source.write_text("before", encoding="utf-8")
            output = Path(temp_dir) / "export.zip"
            original_write = zipfile.ZipFile.write

            def mutate_before_write(archive, filename, arcname=None, compress_type=None):
                Path(filename).write_text("after", encoding="utf-8")
                return original_write(archive, filename, arcname=arcname, compress_type=compress_type)

            with mock.patch.object(zipfile.ZipFile, "write", autospec=True, side_effect=mutate_before_write):
                with self.assertRaises(ValueError):
                    export_data(root, output)
            self.assertFalse(output.exists())

    def test_data_operations_reject_symlinked_root(self):
        from focuscheck.utils.data_export import clear_data, export_data, inventory_data
        from focuscheck.utils.data_retention import apply_retention, retention_plan

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            base = Path(temp_dir)
            real_root = base / "real"
            real_root.mkdir()
            (real_root / "focus_log.csv").write_text("safe", encoding="utf-8")
            linked_root = base / "linked"
            try:
                linked_root.symlink_to(real_root, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")

            with self.assertRaises(ValueError):
                export_data(linked_root, base / "export.zip")
            with self.assertRaises(ValueError):
                inventory_data(linked_root)
            with self.assertRaises(ValueError):
                clear_data(linked_root, categories=("logs",), confirmed=True)
            with self.assertRaises(ValueError):
                retention_plan(linked_root, max_age_days=1)
            with self.assertRaises(ValueError):
                apply_retention(linked_root, max_age_days=1, apply=True)

from __future__ import annotations

import tempfile
import unittest
import zipfile
import json
from pathlib import Path

from tools.create_diagnostic_bundle import create_bundle, sanitize


class DiagnosticBundleTests(unittest.TestCase):
    def test_status_formatter_uses_only_whitelisted_health_fields(self):
        from focuscheck.utils.diagnostics import format_status_snapshot

        rendered = format_status_snapshot({
            "version": "1.2.3",
            "lifecycle": "ready",
            "data_root": "C:/FocusCheck",
            "transition_sink_failures": 2,
            "private_response": "should not appear",
            "url": "https://private.example/path",
        })

        self.assertIn("Version: 1.2.3", rendered)
        self.assertIn("Lifecycle: ready", rendered)
        self.assertIn("Transition journal failures: 2", rendered)
        self.assertNotIn("should not appear", rendered)
        self.assertNotIn("private.example", rendered)

    def test_sanitize_redacts_paths_and_credentials(self):
        root = Path("C:/verification")
        value = f"{root}{Path('/log')} password=secret Bearer abc123"
        result = sanitize(value, root=root)
        self.assertNotIn("secret", result)
        self.assertNotIn("abc123", result)
        self.assertIn("<verification-root>", result)

    def test_bundle_contains_only_sanitized_runtime_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime = Path(temp_dir)
            (runtime / "stage.log").write_text("password=secret", encoding="utf-8")
            (runtime / "verification.json").write_text("{}", encoding="utf-8")
            output = create_bundle(runtime, runtime / "bundle.zip")
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(
                    {"stage.log", "verification.json", "DIAGNOSTIC_MANIFEST.json"},
                    set(archive.namelist()),
                )
                self.assertNotIn("secret", archive.read("stage.log").decode())
                manifest = json.loads(archive.read("DIAGNOSTIC_MANIFEST.json"))
                self.assertEqual(1, manifest["format_version"])
                self.assertEqual("<runtime-root>", manifest["root"])
                self.assertNotIn(str(runtime), archive.read("DIAGNOSTIC_MANIFEST.json").decode())

    def test_preview_excludes_sensitive_categories_and_bundle_redacts_private_fields(self):
        from focuscheck.utils.diagnostics import create_bundle, preview_bundle

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "focus_app.log").write_text(
                "title=Private title url=https://example.test/path?q=secret password=hunter2",
                encoding="utf-8",
            )
            (root / "focus_settings.json").write_text('{"private":"value"}', encoding="utf-8")
            (root / "focus_tasks.sqlite3").write_bytes(b"task")

            preview = preview_bundle(root)
            self.assertEqual(["focus_app.log"], [item["path"] for item in preview["files"]])
            self.assertEqual({"settings", "tasks", "camera", "exports"}, set(preview["excluded"]))
            output = root / "bundle.zip"
            create_bundle(root, output)
            with zipfile.ZipFile(output) as archive:
                content = archive.read("focus_app.log").decode()
            self.assertNotIn("Private title", content)
            self.assertNotIn("secret", content)
            self.assertNotIn("hunter2", content)

    def test_diagnostic_operations_reject_symlinked_root(self):
        from focuscheck.utils.diagnostics import create_bundle, preview_bundle

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            base = Path(temp_dir)
            real_root = base / "real"
            real_root.mkdir()
            (real_root / "stage.log").write_text("safe", encoding="utf-8")
            linked_root = base / "linked"
            try:
                linked_root.symlink_to(real_root, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("directory symlinks unavailable")

            with self.assertRaises(ValueError):
                preview_bundle(linked_root)
            with self.assertRaises(ValueError):
                create_bundle(linked_root, base / "diagnostic.zip")

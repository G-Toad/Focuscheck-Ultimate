from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.create_diagnostic_bundle import create_bundle, sanitize


class DiagnosticBundleTests(unittest.TestCase):
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
                self.assertEqual({"stage.log", "verification.json"}, set(archive.namelist()))
                self.assertNotIn("secret", archive.read("stage.log").decode())

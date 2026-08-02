from __future__ import annotations

import unittest
import shutil
import subprocess
import tempfile
from pathlib import Path


class PackagingContractTests(unittest.TestCase):
    def test_runtime_dependencies_are_pinned(self):
        root = Path(__file__).resolve().parents[1]
        lines = [line.strip() for line in (root / "requirements.txt").read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertTrue(lines)
        self.assertTrue(all("==" in line for line in lines))

    def test_package_and_rollback_contracts_exist(self):
        root = Path(__file__).resolve().parents[1]
        for relative in (
            "packaging/focuscheck.spec",
            "tools/build_package.ps1",
            "tools/promote_package.ps1",
            "tools/rollback_package.ps1",
            "docs/INSTALL.md",
            "docs/ROLLBACK.md",
            "docs/RELEASE_NOTES.md",
        ):
            self.assertTrue((root / relative).is_file(), relative)

    def test_package_lifecycle_scripts_are_non_destructive_and_hash_artifacts(self):
        root = Path(__file__).resolve().parents[1]
        promote = (root / "tools/promote_package.ps1").read_text(encoding="utf-8")
        rollback = (root / "tools/rollback_package.ps1").read_text(encoding="utf-8")
        self.assertIn("package-manifest.json", promote)
        self.assertIn("SHA256", promote)
        self.assertIn("Previous package retained", promote)
        self.assertIn("Failed package retained", rollback)
        self.assertNotIn("focus_settings.json", promote)
        self.assertNotIn("focus_tasks.sqlite3", promote)

    def test_package_promotion_and_rollback_transaction(self):
        powershell = shutil.which("powershell") or shutil.which("pwsh")
        if not powershell:
            self.skipTest("PowerShell is required for package lifecycle verification")
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            package = temp / "package"
            install = temp / "install"
            package.mkdir()
            install.mkdir()
            (package / "FocusCheck.exe").write_text("new", encoding="ascii")
            (install / "FocusCheck.exe").write_text("old", encoding="ascii")

            promoted = subprocess.run(
                [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(root / "tools/promote_package.ps1"), "-PackageDir", str(package), "-InstallDir", str(install), "-Version", "test"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(0, promoted.returncode, promoted.stdout + promoted.stderr)
            backups = list(temp.glob(".FocusCheck.backup.*"))
            self.assertEqual(1, len(backups))
            self.assertTrue((install / "package-manifest.json").exists())

            rolled_back = subprocess.run(
                [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(root / "tools/rollback_package.ps1"), "-InstallDir", str(install), "-BackupDir", str(backups[0])],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(0, rolled_back.returncode, rolled_back.stdout + rolled_back.stderr)
            self.assertEqual("old", (install / "FocusCheck.exe").read_text(encoding="ascii"))
            self.assertEqual(1, len(list(temp.glob(".FocusCheck.failed.*"))))

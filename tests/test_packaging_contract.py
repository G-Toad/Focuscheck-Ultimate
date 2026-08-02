from __future__ import annotations

import unittest
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
            "docs/INSTALL.md",
            "docs/ROLLBACK.md",
            "docs/RELEASE_NOTES.md",
        ):
            self.assertTrue((root / relative).is_file(), relative)

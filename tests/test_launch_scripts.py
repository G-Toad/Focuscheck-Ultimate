"""Launch script contract tests."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LaunchScriptContractTests(unittest.TestCase):
    def test_startup_batch_launches_supervisor_started(self):
        script = (ROOT / "start_focuscheck.bat").read_text(encoding="utf-8").lower()

        self.assertNotIn("focuscheck_force_started", script)
        self.assertIn("focuscheck_supervisor.py", script)
        self.assertIn("--run", script)
        self.assertIn("--base-dir", script)

    def test_legacy_command_delegates_to_canonical_supervisor_launcher(self):
        script = (ROOT / "Start FocusCheck.cmd").read_text(encoding="utf-8").lower()

        self.assertIn("start_focuscheck.bat", script)
        self.assertNotIn("pythonw main.py", script)
        self.assertNotIn("focuscheck_force_started", script)


if __name__ == "__main__":
    unittest.main()

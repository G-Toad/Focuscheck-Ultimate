"""Launch script contract tests."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LaunchScriptContractTests(unittest.TestCase):
    def test_startup_batch_launches_supervisor_started(self):
        script = (ROOT / "start_focuscheck.bat").read_text(encoding="utf-8").lower()

        self.assertIn("focuscheck_force_started=1", script)
        self.assertIn("focuscheck_supervisor.py", script)
        self.assertIn("--run", script)
        self.assertIn("--base-dir", script)

    def test_legacy_command_remains_direct_child_launch(self):
        script = (ROOT / "Start FocusCheck.cmd").read_text(encoding="utf-8").lower()

        self.assertIn("pythonw main.py", script)
        self.assertNotIn("focuscheck_supervisor.py", script)
        self.assertNotIn("focuscheck_force_started", script)


if __name__ == "__main__":
    unittest.main()

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

    def test_force_start_is_an_explicit_supervisor_argument(self):
        import inspect
        import focuscheck_supervisor

        parser_source = inspect.getsource(focuscheck_supervisor.parse_args)
        self.assertIn('"--force-start"', parser_source)

    def test_tray_test_timeout_uses_named_timer_registry(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")

        self.assertIn("from focuscheck.utils.timers import TimerRegistry", source)
        self.assertIn('timers.schedule("tray-test-timeout"', source)
        self.assertNotIn("r.after(20000", source)


if __name__ == "__main__":
    unittest.main()

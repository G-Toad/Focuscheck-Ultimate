"""Desktop-safe supervisor lifecycle harness tests."""

from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path


class MemoryLogger:
    def __init__(self):
        self.lines: list[str] = []

    def log(self, message: str) -> None:
        self.lines.append(message)


class FakeEvent:
    def __init__(self):
        self._set = False
        self.waits: list[float] = []

    def set(self) -> None:
        self._set = True

    def is_set(self) -> bool:
        return self._set

    def wait(self, timeout=None) -> bool:
        self.waits.append(timeout)
        return self._set


class FakeProcess:
    def __init__(self, pid: int, exit_code=None):
        self.pid = pid
        self.exit_code = exit_code
        self.terminated = False
        self.killed = False

    def poll(self):
        return self.exit_code

    def terminate(self):
        self.terminated = True
        self.exit_code = 0

    def kill(self):
        self.killed = True
        self.exit_code = -9

    def wait(self, timeout=None):
        return self.exit_code


class HarnessSupervisor:
    def __init__(self, temp_dir: str, launch_plan):
        from focuscheck_supervisor import FocusCheckSupervisor

        class TestSupervisor(FocusCheckSupervisor):
            def _setup_signal_handlers(self):
                return None

            def _launch_focuscheck(inner_self):
                if not launch_plan:
                    inner_self.stop_event.set()
                    return
                item = launch_plan.pop(0)
                if item == "intentional-exit":
                    proc = FakeProcess(200 + len(inner_self.launches), exit_code=0)
                    Path(temp_dir, "supervisor.stop").write_text(json.dumps({
                        "protocol_version": 1, "pid": proc.pid, "reason": "user_exit",
                    }), encoding="ascii")
                elif item == "crash":
                    proc = FakeProcess(200 + len(inner_self.launches), exit_code=7)
                else:
                    proc = FakeProcess(200 + len(inner_self.launches), exit_code=None)
                inner_self.child = proc
                inner_self.launches.append(proc)
                inner_self.logger.log(f"fake launch pid={proc.pid} state={item}")
                if not launch_plan and item != "intentional-exit":
                    inner_self.stop_after_last_launch = True

            def _terminate_child(inner_self):
                inner_self.terminations += 1
                super()._terminate_child()

        self.logger = MemoryLogger()
        self.supervisor = TestSupervisor(
            target_script=Path(temp_dir) / "main.py",
            python_executable="python",
            logger=self.logger,
            check_interval=1,
            resume_gap=10,
            restart_delay=1,
            stop_file=Path(temp_dir) / "supervisor.stop",
        )
        self.supervisor.stop_event = FakeEvent()
        self.supervisor.launches = []
        self.supervisor.terminations = 0
        self.supervisor.stop_after_last_launch = False

        original_launch = self.supervisor._launch_focuscheck

        def launch_and_maybe_stop():
            original_launch()
            if self.supervisor.stop_after_last_launch:
                self.supervisor.stop_event.set()

        self.supervisor._launch_focuscheck = launch_and_maybe_stop


class SupervisorHarnessTests(unittest.TestCase):
    def test_duplicate_supervisor_lock_rejected_without_live_processes(self):
        from focuscheck_supervisor import SupervisorLock

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            lock_path = Path(temp_dir) / "supervisor.lock"
            first = SupervisorLock(lock_path)
            second = SupervisorLock(lock_path)

            self.assertTrue(first.acquire())
            try:
                self.assertFalse(second.acquire())
            finally:
                first.release()

            self.assertFalse(lock_path.exists())

    def test_stale_supervisor_lock_recovers_without_live_processes(self):
        from focuscheck_supervisor import SupervisorLock

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            lock_path = Path(temp_dir) / "supervisor.lock"
            lock_path.write_text("0", encoding="ascii")

            lock = SupervisorLock(lock_path)
            self.assertTrue(lock.acquire())
            lock.release()

            self.assertFalse(lock_path.exists())

    def test_child_crash_restarts_without_real_processes(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            harness = HarnessSupervisor(temp_dir, ["crash", "running"])

            harness.supervisor.run()

            self.assertEqual(2, len(harness.supervisor.launches))
            self.assertTrue(any("FocusCheck exited with 7" in line for line in harness.logger.lines))
            self.assertTrue(any("Restarting in" in line for line in harness.logger.lines))

    def test_intentional_stop_does_not_restart(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            harness = HarnessSupervisor(temp_dir, ["intentional-exit"])

            harness.supervisor.run()

            self.assertEqual(1, len(harness.supervisor.launches))
            self.assertTrue(any("Intentional FocusCheck stop requested" in line for line in harness.logger.lines))
            self.assertFalse((Path(temp_dir) / "supervisor.stop").exists())

    def test_running_child_is_terminated_when_supervisor_stops(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            harness = HarnessSupervisor(temp_dir, ["running"])

            harness.supervisor.run()

            self.assertEqual(1, harness.supervisor.terminations)
            self.assertTrue(harness.supervisor.launches[0].terminated)


if __name__ == "__main__":
    unittest.main()

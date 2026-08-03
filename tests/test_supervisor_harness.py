"""Desktop-safe supervisor lifecycle harness tests."""

from __future__ import annotations

import tempfile
import unittest
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock


class MemoryLogger:
    def __init__(self):
        self.lines: list[str] = []

    def log(self, message: str) -> None:
        self.lines.append(message)


class SupervisorEntrypointTests(unittest.TestCase):
    def test_source_and_frozen_entrypoint_resolution(self):
        import focuscheck_supervisor as supervisor

        base = Path("C:/FocusCheck/app")
        with mock.patch.object(supervisor.sys, "frozen", False, create=True):
            self.assertEqual(base / "main.py", supervisor.resolve_supervised_target(base))
            self.assertEqual(Path(supervisor.__file__).resolve(), supervisor.resolve_supervisor_entrypoint())

        with mock.patch.object(supervisor.sys, "frozen", True, create=True), \
                mock.patch.object(supervisor.sys, "executable", "C:/FocusCheck/app/FocusCheckSupervisor.exe"):
            self.assertEqual(base / "FocusCheck.exe", supervisor.resolve_supervised_target(base))
            self.assertEqual(Path("C:/FocusCheck/app/FocusCheckSupervisor.exe"), supervisor.resolve_supervisor_entrypoint())

    def test_frozen_startup_launcher_points_at_supervisor_executable(self):
        import focuscheck_supervisor as supervisor

        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.object(supervisor.sys, "frozen", True, create=True), \
                mock.patch.object(supervisor.sys, "executable", str(Path(temp_dir) / "FocusCheckSupervisor.exe")), \
                mock.patch.object(supervisor, "get_startup_dir", return_value=Path(temp_dir)):
            launcher = supervisor.install_startup_launcher(Path(temp_dir), "ignored-python.exe", 10, 90, 5)
            content = launcher.read_text(encoding="ascii")
            self.assertIn("FocusCheckSupervisor.exe", content)
            self.assertNotIn("focuscheck_supervisor.py", content)

    def test_frozen_inner_heartbeat_pid_is_accepted_for_stop_handshake(self):
        from focuscheck_supervisor import FocusCheckSupervisor

        with tempfile.TemporaryDirectory() as temp_dir:
            stop_file = Path(temp_dir) / "supervisor.stop"
            stop_file.write_text(json.dumps({
                "protocol_version": 1,
                "request_id": "frozen-inner",
                "supervisor_id": "supervisor",
                "generation": "generation",
                "pid": 222,
                "process_start_utc": "2030-01-01T00:00:00+00:00",
                "utc": datetime.now(timezone.utc).isoformat(),
                "reason": "user_exit",
            }), encoding="ascii")
            supervisor = FocusCheckSupervisor.__new__(FocusCheckSupervisor)
            supervisor.stop_file = stop_file
            supervisor.child = type("Child", (), {"pid": 111})()
            supervisor._last_heartbeat_pid = 222
            supervisor._last_heartbeat_process_start_utc = "2030-01-01T00:00:00+00:00"
            supervisor.supervisor_id = "supervisor"
            supervisor.child_generation = "generation"
            self.assertTrue(supervisor._intentional_stop_requested())

    def test_stop_handshake_rejects_foreign_generation_and_stale_request(self):
        from focuscheck_supervisor import FocusCheckSupervisor

        with tempfile.TemporaryDirectory() as temp_dir:
            stop_file = Path(temp_dir) / "supervisor.stop"
            supervisor = FocusCheckSupervisor.__new__(FocusCheckSupervisor)
            supervisor.stop_file = stop_file
            supervisor.child = type("Child", (), {"pid": 111})()
            supervisor._last_heartbeat_pid = 111
            supervisor._last_heartbeat_process_start_utc = "2030-01-01T00:00:00+00:00"
            supervisor.supervisor_id = "current"
            supervisor.child_generation = "generation-current"
            request = {
                "protocol_version": 1,
                "request_id": "nonce",
                "supervisor_id": "foreign",
                "generation": "generation-current",
                "pid": 111,
                "process_start_utc": supervisor._last_heartbeat_process_start_utc,
                "utc": datetime.now(timezone.utc).isoformat(),
            }
            stop_file.write_text(json.dumps(request), encoding="ascii")
            self.assertFalse(supervisor._intentional_stop_requested())
            request["supervisor_id"] = "current"
            request["utc"] = "2000-01-01T00:00:00+00:00"
            stop_file.write_text(json.dumps(request), encoding="ascii")
            self.assertFalse(supervisor._intentional_stop_requested())


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
                        "protocol_version": 1, "request_id": "fake-nonce",
                        "supervisor_id": inner_self.supervisor_id,
                        "generation": inner_self.child_generation,
                        "pid": proc.pid,
                        "process_start_utc": "",
                        "utc": datetime.now(timezone.utc).isoformat(),
                        "reason": "user_exit",
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
                return super()._terminate_child()

        self.logger = MemoryLogger()
        self.supervisor = TestSupervisor(
            target_script=Path(temp_dir) / "main.py",
            python_executable="python",
            logger=self.logger,
            check_interval=1,
            resume_gap=10,
            restart_delay=1,
            stop_file=Path(temp_dir) / "supervisor.stop",
            stop_ack_file=Path(temp_dir) / "supervisor.stop.ack",
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
    def test_launch_failure_wait_is_cancellation_aware(self):
        import focuscheck_supervisor as supervisor_module
        from focuscheck_supervisor import FocusCheckSupervisor

        supervisor = FocusCheckSupervisor.__new__(FocusCheckSupervisor)
        supervisor.target_script = Path("C:/FocusCheck/main.py")
        supervisor.python_executable = "python"
        supervisor.logger = MemoryLogger()
        supervisor.stop_event = FakeEvent()
        supervisor.current_delay = 3.0
        supervisor.child = None
        supervisor.supervisor_id = "supervisor"
        supervisor.child_generation = None
        supervisor.stop_file = Path("C:/FocusCheck/supervisor.stop")
        supervisor.stop_ack_file = Path("C:/FocusCheck/supervisor.stop.ack")
        supervisor.heartbeat_path = Path("C:/FocusCheck/hb.txt")
        with mock.patch.object(supervisor_module.subprocess, "Popen", side_effect=OSError("launcher unavailable")):
            supervisor._launch_focuscheck()

        self.assertEqual([3.0], supervisor.stop_event.waits)
        self.assertIsNone(supervisor.child)
        self.assertTrue(any("Failed to start FocusCheck" in line for line in supervisor.logger.lines))

    def test_force_start_is_forwarded_only_when_explicitly_configured(self):
        import focuscheck_supervisor as supervisor_module
        from focuscheck_supervisor import FocusCheckSupervisor

        supervisor = FocusCheckSupervisor.__new__(FocusCheckSupervisor)
        supervisor.target_script = Path("C:/FocusCheck/main.py")
        supervisor.python_executable = "python"
        supervisor.logger = MemoryLogger()
        supervisor.stop_event = FakeEvent()
        supervisor.current_delay = 3.0
        supervisor.force_start = True
        supervisor.child = None
        supervisor.supervisor_id = "supervisor"
        supervisor.child_generation = None
        supervisor.stop_file = Path("C:/FocusCheck/supervisor.stop")
        supervisor.stop_ack_file = Path("C:/FocusCheck/supervisor.stop.ack")
        supervisor.heartbeat_path = Path("C:/FocusCheck/hb.txt")
        process = mock.Mock(pid=1234)
        with mock.patch.object(supervisor_module.subprocess, "Popen", return_value=process) as popen:
            supervisor._launch_focuscheck()

        command = popen.call_args.args[0]
        self.assertEqual(["python", str(Path("C:/FocusCheck/main.py")), "--force-start"], command)

    def test_resume_gap_uses_process_scoped_restart(self):
        import focuscheck_supervisor as supervisor_module
        from focuscheck_supervisor import FocusCheckSupervisor

        supervisor = FocusCheckSupervisor.__new__(FocusCheckSupervisor)
        supervisor.logger = MemoryLogger()
        supervisor.stop_event = FakeEvent()
        supervisor.child = FakeProcess(321)
        supervisor.current_delay = 4.0
        supervisor.restart_delay = 4.0
        supervisor._restart_history = []
        supervisor._degraded_until = 0.0
        supervisor.last_tick = 10.0
        with mock.patch.object(supervisor_module, "kill_process_tree") as kill_tree, \
                mock.patch.object(supervisor_module.time, "monotonic", return_value=100.0):
            supervisor._force_restart("Detected 90.0s watchdog gap (likely resume/unlock)")

        kill_tree.assert_called_once_with(321)
        self.assertTrue(any("forcing restart" in line for line in supervisor.logger.lines))

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

    def test_stale_supervisor_lock_recovers_after_pid_reuse(self):
        import focuscheck_supervisor as supervisor_module
        from focuscheck_supervisor import SupervisorLock

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            lock_path = Path(temp_dir) / "supervisor.lock"
            lock_path.write_text(json.dumps({
                "protocol_version": 1,
                "pid": 321,
                "process_start_token": "old-process",
                "instance_nonce": "old-instance",
            }), encoding="ascii")
            with mock.patch.object(supervisor_module, "_process_start_token", return_value="new-process"), \
                    mock.patch.object(supervisor_module, "_pid_is_alive", return_value=True):
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

    def test_frozen_child_cleanup_terminates_validated_inner_pid(self):
        import focuscheck_supervisor as supervisor_module
        from focuscheck_supervisor import FocusCheckSupervisor

        supervisor = FocusCheckSupervisor.__new__(FocusCheckSupervisor)
        supervisor.target_script = Path("C:/FocusCheck/FocusCheck.exe")
        supervisor.child = FakeProcess(111)
        supervisor._last_heartbeat_pid = 222
        supervisor.logger = MemoryLogger()
        with mock.patch.object(supervisor_module, "_pid_is_alive", return_value=True), \
                mock.patch.object(supervisor_module, "kill_process_tree") as kill_tree:
            supervisor._terminate_child()

        kill_tree.assert_called_once_with(222)
        self.assertTrue(supervisor.child is None)

    def test_restart_backoff_resets_only_after_stable_ready_window(self):
        import focuscheck_supervisor as supervisor_module
        from focuscheck_supervisor import FocusCheckSupervisor

        supervisor = FocusCheckSupervisor.__new__(FocusCheckSupervisor)
        supervisor.restart_delay = 1.0
        supervisor.current_delay = 8.0
        supervisor._restart_history = [1.0]
        supervisor._degraded_until = 99.0
        supervisor._ready_since_mono = 10.0
        supervisor.logger = MemoryLogger()
        with mock.patch.object(supervisor_module.time, "monotonic", return_value=39.9):
            supervisor._maybe_reset_after_stable()
        self.assertEqual(8.0, supervisor.current_delay)
        with mock.patch.object(supervisor_module.time, "monotonic", return_value=40.0):
            supervisor._maybe_reset_after_stable()
        self.assertEqual(1.0, supervisor.current_delay)
        self.assertEqual([], supervisor._restart_history)
        self.assertEqual(0.0, supervisor._degraded_until)

    def test_intentional_stop_is_acknowledged_for_current_generation(self):
        from focuscheck_supervisor import FocusCheckSupervisor, FileLogger

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            root = Path(temp_dir)
            stop_file = root / "supervisor.stop"
            ack_file = root / "supervisor.stop.ack"
            supervisor = FocusCheckSupervisor(
                target_script=root / "main.py",
                python_executable="python",
                logger=FileLogger(root / "supervisor.log"),
                stop_file=stop_file,
                stop_ack_file=ack_file,
                heartbeat_path=root / "hb.txt",
            )
            supervisor.child_generation = "generation-1"
            request = {
                "protocol_version": 1,
                "request_id": "request-1",
                "supervisor_id": supervisor.supervisor_id,
                "generation": "generation-1",
                "pid": 1234,
                "process_start_utc": "2026-08-03T00:00:00+00:00",
                "utc": datetime.now(timezone.utc).isoformat(),
                "reason": "user_exit",
            }
            stop_file.write_text(json.dumps(request), encoding="utf-8")

            self.assertTrue(supervisor._intentional_stop_requested(expected_pid=1234))
            self.assertTrue(supervisor._acknowledge_stop_request())
            ack = json.loads(ack_file.read_text(encoding="utf-8"))
            self.assertEqual("request-1", ack["request_id"])
            self.assertEqual("generation-1", ack["generation"])
            self.assertEqual("acknowledged", ack["status"])
            self.assertEqual("unknown", ack["termination"])

    def test_child_termination_timeout_is_reported_and_forced(self):
        from focuscheck_supervisor import FocusCheckSupervisor

        class HangingProcess:
            pid = 1234

            def __init__(self):
                self.killed = False
                self.wait_calls = []

            def poll(self):
                return None

            def terminate(self):
                return None

            def kill(self):
                self.killed = True

            def wait(self, timeout=None):
                self.wait_calls.append(timeout)
                if len(self.wait_calls) == 1:
                    raise __import__("subprocess").TimeoutExpired(["FocusCheck"], timeout)
                return -9

        process = HangingProcess()
        supervisor = FocusCheckSupervisor.__new__(FocusCheckSupervisor)
        supervisor.child = process
        supervisor.target_script = Path("main.py")
        supervisor.logger = MemoryLogger()

        termination = supervisor._terminate_child()

        self.assertEqual("forced_after_timeout", termination)
        self.assertTrue(process.killed)
        self.assertEqual([10.0, 5.0], process.wait_calls)
        self.assertTrue(any("forcing termination" in line for line in supervisor.logger.lines))

    def test_intentional_stop_acknowledgement_ignores_foreign_generation(self):
        from focuscheck_supervisor import FocusCheckSupervisor, FileLogger

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            root = Path(temp_dir)
            stop_file = root / "supervisor.stop"
            ack_file = root / "supervisor.stop.ack"
            supervisor = FocusCheckSupervisor(
                target_script=root / "main.py",
                python_executable="python",
                logger=FileLogger(root / "supervisor.log"),
                stop_file=stop_file,
                stop_ack_file=ack_file,
                heartbeat_path=root / "hb.txt",
            )
            supervisor.child_generation = "generation-current"
            stop_file.write_text(json.dumps({
                "protocol_version": 1,
                "request_id": "request-foreign",
                "supervisor_id": supervisor.supervisor_id,
                "generation": "generation-old",
                "pid": 1234,
                "utc": datetime.now(timezone.utc).isoformat(),
            }), encoding="utf-8")

            self.assertFalse(supervisor._intentional_stop_requested(expected_pid=1234))
            self.assertFalse(ack_file.exists())

    def test_stop_acknowledgement_write_failure_is_explicit(self):
        from focuscheck_supervisor import FocusCheckSupervisor, FileLogger

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            supervisor = FocusCheckSupervisor(
                target_script=root / "main.py",
                python_executable="python",
                logger=FileLogger(root / "supervisor.log"),
                stop_file=root / "supervisor.stop",
                stop_ack_file=root / "missing" / "supervisor.stop.ack",
                heartbeat_path=root / "hb.txt",
            )
            supervisor.child_generation = "generation-1"
            (root / "supervisor.stop").write_text("{not-json", encoding="ascii")

            with mock.patch.object(supervisor.logger, "log") as log:
                self.assertFalse(supervisor._acknowledge_stop_request())

            log.assert_called_once()
            self.assertIn("Could not acknowledge intentional stop", log.call_args.args[0])


if __name__ == "__main__":
    unittest.main()

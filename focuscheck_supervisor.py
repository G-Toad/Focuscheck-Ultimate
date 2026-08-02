#!/usr/bin/env python3
"""FocusCheck Supervisor

Keeps main.py alive and adds helper commands to wire it into Windows startup.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

DEFAULT_CHECK_INTERVAL = 10.0
DEFAULT_RESUME_GAP = 90.0
DEFAULT_RESTART_DELAY = 5.0
MAX_RESTART_DELAY = 120.0
STARTUP_SCRIPT_NAME = "RunFocusCheckSupervisor.cmd"
LOG_DIR_NAME = "FocusCheck"
LOG_FILE_NAME = "focuscheck_supervisor.log"

SEM_FAILCRITICALERRORS = 0x0001
SEM_NOGPFAULTERRORBOX = 0x0002
SEM_NOOPENFILEERRORBOX = 0x8000
WER_FAULT_REPORTING_NO_UI = 0x20
STILL_ACTIVE = 259
HEARTBEAT_FILENAME = "hb.txt"
SUPERVISOR_LOCK_FILENAME = "supervisor.lock"
SUPERVISOR_STOP_FILENAME = "supervisor.stop"
HEARTBEAT_MAX_AGE = 12.0
HEARTBEAT_GRACE_PERIOD = 15.0
FORCED_RESTART_PAUSE = 0.2
RESTART_WINDOW_SECONDS = 300.0
MAX_RESTARTS_IN_WINDOW = 5
DEGRADED_COOLDOWN_SECONDS = 300.0


def _resolve_focuscheck_dir() -> Path:
    override = os.environ.get("FOCUS_DATA_DIR")
    if override:
        return Path(override)
    base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / LOG_DIR_NAME
    return Path.home() / LOG_DIR_NAME


def default_heartbeat_path() -> Path:
    return _resolve_focuscheck_dir() / HEARTBEAT_FILENAME


def default_supervisor_lock_path() -> Path:
    override = os.environ.get("FOCUSCHECK_SUPERVISOR_LOCK_FILE")
    if override:
        return Path(override)
    return _resolve_focuscheck_dir() / SUPERVISOR_LOCK_FILENAME


def default_supervisor_stop_path() -> Path:
    override = os.environ.get("FOCUSCHECK_SUPERVISOR_STOP_FILE")
    if override:
        return Path(override)
    return _resolve_focuscheck_dir() / SUPERVISOR_STOP_FILENAME


def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        return _windows_pid_is_alive(pid)
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except OSError:
        return False


def _windows_pid_is_alive(pid: int) -> bool:
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = (ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong)
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.GetExitCodeProcess.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong))
        kernel32.GetExitCodeProcess.restype = ctypes.c_int
        kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
        kernel32.CloseHandle.restype = ctypes.c_int

        process_query_limited_information = 0x1000
        handle = kernel32.OpenProcess(process_query_limited_information, 0, pid)
        if not handle:
            return False
        try:
            exit_code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return False
            return exit_code.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        return False


class SupervisorLock:
    """Atomic file lock to prevent multiple supervisor loops."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_supervisor_lock_path()
        self._fd: int | None = None

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(2):
            try:
                self._fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(self._fd, str(os.getpid()).encode("ascii", errors="ignore"))
                return True
            except FileExistsError:
                if attempt or not self._remove_stale_lock():
                    return False
        return False

    def _remove_stale_lock(self) -> bool:
        try:
            raw = self.path.read_text(encoding="ascii").strip()
            pid = int(raw) if raw else 0
        except Exception:
            pid = 0
        if _pid_is_alive(pid):
            return False
        try:
            self.path.unlink()
            return True
        except OSError:
            return False

    def release(self) -> None:
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass

    def __enter__(self) -> "SupervisorLock":
        if not self.acquire():
            raise RuntimeError(f"FocusCheck supervisor already running ({self.path})")
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        self.release()


def suppress_windows_error_dialogs() -> None:
    if os.name != "nt":
        return
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    except Exception:
        return
    try:
        kernel32.SetErrorMode(
            SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX | SEM_NOOPENFILEERRORBOX
        )
    except Exception:
        pass
    try:
        wer_set_flags = getattr(kernel32, "WerSetFlags", None)
        if wer_set_flags:
            wer_set_flags(WER_FAULT_REPORTING_NO_UI)
    except Exception:
        pass


def kill_process_tree(pid: int) -> None:
    if pid <= 0:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass
        return
    try:
        os.killpg(pid, signal.SIGKILL)
    except Exception:
        try:
            os.kill(pid, getattr(signal, "SIGKILL", signal.SIGTERM))
        except Exception:
            pass


def kill_werfault_dialogs() -> None:
    """Retained compatibility hook; never terminate unrelated system processes."""
    return

class FileLogger:
    """Very small file based logger with cheap rotation."""

    def __init__(self, path: Path, max_bytes: int = 512 * 1024) -> None:
        self.path = path
        self.max_bytes = max_bytes
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, message: str) -> None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"{timestamp} | {message}\n"
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line)
        try:
            if self.path.stat().st_size > self.max_bytes:
                backup = self.path.with_suffix(".log.bak")
                if backup.exists():
                    backup.unlink()
                self.path.rename(backup)
        except OSError:
            pass


class FocusCheckSupervisor:
    """Watchdog that keeps FocusCheck alive."""

    def __init__(
        self,
        target_script: Path,
        python_executable: str,
        logger: FileLogger,
        check_interval: float = DEFAULT_CHECK_INTERVAL,
        resume_gap: float = DEFAULT_RESUME_GAP,
        restart_delay: float = DEFAULT_RESTART_DELAY,
        stop_file: Path | None = None,
        heartbeat_path: Path | None = None,
    ) -> None:
        self.target_script = target_script
        self.python_executable = python_executable
        self.logger = logger
        self.check_interval = max(1.0, check_interval)
        self.resume_gap = max(self.check_interval * 2.0, resume_gap)
        self.restart_delay = max(1.0, restart_delay)
        self.stop_event = threading.Event()
        self.child: subprocess.Popen[str] | None = None
        self.last_tick = time.monotonic()
        self.current_delay = self.restart_delay
        self._ctrl_handler = None
        self._setup_signal_handlers()
        self.heartbeat_path = heartbeat_path or default_heartbeat_path()
        self.stop_file = stop_file or default_supervisor_stop_path()
        self._heartbeat_grace_deadline = 0.0
        self.supervisor_id = uuid.uuid4().hex
        self.child_generation: str | None = None
        self._restart_history: list[float] = []
        self._degraded_until = 0.0
        suppress_windows_error_dialogs()
        self._clear_stop_request()

    def _setup_signal_handlers(self) -> None:
        def _signal_handler(signum, _frame):
            self.logger.log(f"Received signal {signum}, shutting down supervisor")
            self.stop_event.set()

        for sig_name in ("SIGTERM", "SIGINT"):
            sig = getattr(signal, sig_name, None)
            if sig is not None:
                try:
                    signal.signal(sig, _signal_handler)
                except (OSError, ValueError):
                    pass

        if os.name == "nt":
            try:
                import ctypes
                from ctypes import wintypes

                kernel32 = ctypes.windll.kernel32

                @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)
                def handler(ctrl_type):  # type: ignore[misc]
                    self.logger.log(f"Windows control event {ctrl_type}, stopping")
                    self.stop_event.set()
                    return True

                if not kernel32.SetConsoleCtrlHandler(handler, True):
                    self.logger.log("Could not register console handler")
                else:
                    self._ctrl_handler = handler
            except Exception as exc:  # pragma: no cover - best effort only
                self.logger.log(f"Failed to hook console handler: {exc}")

    def _launch_focuscheck(self) -> None:
        cmd = [self.python_executable, str(self.target_script)]
        env = os.environ.copy()
        env.setdefault("FOCUSCHECK_SUPERVISED", "1")
        self.child_generation = uuid.uuid4().hex
        env["FOCUSCHECK_SUPERVISOR_ID"] = self.supervisor_id
        env["FOCUSCHECK_CHILD_GENERATION"] = self.child_generation
        # A normal supervised launch must preserve a durable manual pause. An
        # explicit force-start command may set this environment variable.
        env["FOCUSCHECK_SUPERVISOR_STOP_FILE"] = str(self.stop_file)
        creationflags = 0
        startupinfo = None
        if os.name == "nt":
            creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            creationflags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            self.child = subprocess.Popen(
                cmd,
                cwd=str(self.target_script.parent),
                env=env,
                creationflags=creationflags,
                startupinfo=startupinfo,
            )
            self.logger.log(f"FocusCheck started (pid={self.child.pid})")
            self.last_tick = time.monotonic()
            self._heartbeat_grace_deadline = time.monotonic() + HEARTBEAT_GRACE_PERIOD
        except Exception as exc:
            self.logger.log(f"Failed to start FocusCheck: {exc}")
            time.sleep(min(self.current_delay, MAX_RESTART_DELAY))
    def _kill_child_tree(self) -> None:
        if not self.child:
            return
        proc = self.child
        self.child = None
        if proc.poll() is not None:
            return
        self.logger.log("Force killing FocusCheck process tree")
        kill_process_tree(proc.pid)
        try:
            proc.wait(timeout=2)
        except Exception:
            pass

    def _force_restart(self, reason: str) -> None:
        self.logger.log(f"{reason}; forcing restart")
        self._record_restart_failure(reason)
        self._kill_child_tree()
        self.current_delay = self.restart_delay
        self.last_tick = time.monotonic()
        time.sleep(FORCED_RESTART_PAUSE)

    def _record_restart_failure(self, reason: str) -> None:
        now = time.monotonic()
        self._restart_history = [stamp for stamp in self._restart_history if now - stamp <= RESTART_WINDOW_SECONDS]
        self._restart_history.append(now)
        if len(self._restart_history) >= MAX_RESTARTS_IN_WINDOW:
            self._degraded_until = now + DEGRADED_COOLDOWN_SECONDS
            self.logger.log(
                f"Circuit breaker open after {len(self._restart_history)} restart failures; "
                f"degraded cooldown={DEGRADED_COOLDOWN_SECONDS:.0f}s reason={reason}"
            )

    def _circuit_breaker_open(self) -> bool:
        if self._degraded_until <= 0:
            return False
        if time.monotonic() >= self._degraded_until:
            self._degraded_until = 0.0
            self._restart_history.clear()
            self.logger.log("Circuit breaker cooldown elapsed; resuming supervised launch")
            return False
        return True


    def _terminate_child(self) -> None:
        if not self.child:
            return
        proc = self.child
        self.child = None
        if proc.poll() is not None:
            return
        self.logger.log("Stopping FocusCheck")
        try:
            proc.terminate()
        except Exception:
            try:
                proc.kill()
            except Exception:
                return
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
                proc.wait(timeout=5)
            except Exception:
                pass
    def _heartbeat_stale(self) -> bool:
        if self.child is None or self.child.poll() is not None:
            return False
        if time.monotonic() < self._heartbeat_grace_deadline:
            return False
        try:
            raw = self.heartbeat_path.read_text(encoding="utf-8").strip()
            payload = json.loads(raw)
            if int(payload.get("protocol_version", 0)) != 1:
                return True
            if payload.get("readiness") != "ready":
                return True
            if self.child_generation and payload.get("generation") != self.child_generation:
                return True
            heartbeat_utc = payload.get("utc")
            heartbeat_pid = int(payload.get("pid", 0))
            if heartbeat_pid and self.child is not None and heartbeat_pid != self.child.pid:
                return True
            from datetime import datetime, timezone
            timestamp = datetime.fromisoformat(str(heartbeat_utc).replace("Z", "+00:00"))
            age = time.time() - timestamp.astimezone(timezone.utc).timestamp()
            return age > HEARTBEAT_MAX_AGE or age < -HEARTBEAT_MAX_AGE
        except FileNotFoundError:
            return True
        except (ValueError, TypeError, OSError, json.JSONDecodeError):
            return True

    def stop(self) -> None:
        self.stop_event.set()

    def _clear_stop_request(self) -> None:
        try:
            self.stop_file.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass

    def _intentional_stop_requested(self, expected_pid: int | None = None) -> bool:
        try:
            payload = json.loads(self.stop_file.read_text(encoding="utf-8"))
            if int(payload.get("protocol_version", 0)) != 1:
                return False
            requested_pid = int(payload.get("pid", 0))
            if expected_pid is None and self.child is not None:
                expected_pid = self.child.pid
            return requested_pid > 0 and (expected_pid is None or requested_pid == expected_pid)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return False

    def run(self) -> None:
        self.logger.log("Supervisor loop starting")
        while not self.stop_event.is_set():
            if self.child is None or self.child.poll() is not None:
                if self.child is not None:
                    exited_pid = self.child.pid
                    exit_code = self.child.poll()
                    self.logger.log(f"FocusCheck exited with {exit_code}")
                    self.child = None
                    if self._intentional_stop_requested(exited_pid):
                        self.logger.log("Intentional FocusCheck stop requested; supervisor exiting")
                        self._clear_stop_request()
                        self.stop_event.set()
                        break
                    self._record_restart_failure(f"child exit {exit_code}")
                    if self._circuit_breaker_open():
                        self.logger.log("Circuit breaker holding automatic restart")
                        self.stop_event.wait(min(self.check_interval, max(0.1, self._degraded_until - time.monotonic())))
                        continue
                    sleep_for = min(self.current_delay, MAX_RESTART_DELAY)
                    self.logger.log(f"Restarting in {sleep_for:.1f}s")
                    self.stop_event.wait(sleep_for)
                    self.current_delay = min(self.current_delay * 2.0, MAX_RESTART_DELAY)
                    if self.stop_event.is_set():
                        break
                self._launch_focuscheck()
                continue
            now = time.monotonic()
            gap = now - self.last_tick
            if gap >= self.resume_gap:
                self._force_restart(
                    f"Detected {gap:.1f}s watchdog gap (likely resume/unlock)"
                )
                continue
            if self._heartbeat_stale():
                self._force_restart("Heartbeat stale; FocusCheck unresponsive")
                continue
            self.last_tick = now
            if now - self._heartbeat_grace_deadline > 300:
                self.current_delay = self.restart_delay
                self._restart_history.clear()
            self.stop_event.wait(self.check_interval)
        self.logger.log("Supervisor loop stopping")
        self._terminate_child()


def resolve_pythonw(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    exe = Path(sys.executable)
    name = exe.name.lower()
    if name.startswith("python"):
        pythonw = exe.with_name("pythonw.exe")
        if pythonw.exists():
            return str(pythonw)
    found = shutil.which("pythonw.exe")
    if found:
        return found
    return sys.executable


def default_log_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    log_dir = base / LOG_DIR_NAME
    return log_dir / LOG_FILE_NAME


def get_startup_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA is not available; cannot resolve Startup folder")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def install_startup_launcher(
    base_dir: Path,
    python_executable: str,
    check_interval: float,
    resume_gap: float,
    restart_delay: float,
) -> Path:
    startup_dir = get_startup_dir()
    startup_dir.mkdir(parents=True, exist_ok=True)
    supervisor_script = Path(__file__).resolve()
    launcher_path = startup_dir / STARTUP_SCRIPT_NAME
    cmd = (
        f"\"{python_executable}\" \"{supervisor_script}\" --run "
        f"--base-dir \"{base_dir}\" --check-interval {check_interval} "
        f"--resume-gap {resume_gap} --restart-delay {restart_delay}"
    )
    content = (
        "@echo off\r\n"
        "setlocal\r\n"
        f"cd /d \"{base_dir}\"\r\n"
        f"start \"FocusCheck Supervisor\" {cmd}\r\n"
        "endlocal\r\n"
    )
    launcher_path.write_text(content, encoding="ascii")
    return launcher_path


def uninstall_startup_launcher() -> bool:
    launcher_path = get_startup_dir() / STARTUP_SCRIPT_NAME
    if launcher_path.exists():
        launcher_path.unlink()
        return True
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FocusCheck watchdog helper")
    parser.add_argument("--run", action="store_true", help="Run the supervisor loop")
    parser.add_argument(
        "--install-startup",
        action="store_true",
        help="Drop a launcher into the Windows Startup folder",
    )
    parser.add_argument(
        "--uninstall-startup",
        action="store_true",
        help="Remove the Startup launcher",
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Directory containing main.py",
    )
    parser.add_argument(
        "--python",
        dest="python_executable",
        default=None,
        help="Python interpreter to use for launching FocusCheck",
    )
    parser.add_argument("--check-interval", type=float, default=DEFAULT_CHECK_INTERVAL)
    parser.add_argument("--resume-gap", type=float, default=DEFAULT_RESUME_GAP)
    parser.add_argument("--restart-delay", type=float, default=DEFAULT_RESTART_DELAY)
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Custom log file location",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    did_anything = False
    python_executable = resolve_pythonw(args.python_executable)
    base_dir = args.base_dir.resolve()
    target_script = base_dir / "main.py"
    if not target_script.exists():
        raise FileNotFoundError(f"Could not find main.py at {target_script}")

    if args.install_startup:
        path = install_startup_launcher(
            base_dir=base_dir,
            python_executable=python_executable,
            check_interval=args.check_interval,
            resume_gap=args.resume_gap,
            restart_delay=args.restart_delay,
        )
        print(f"Startup launcher created at: {path}")
        did_anything = True

    if args.uninstall_startup:
        removed = uninstall_startup_launcher()
        print("Startup launcher removed" if removed else "Startup launcher not present")
        did_anything = True

    if args.run:
        did_anything = True
        log_path = args.log_file or default_log_path()
        logger = FileLogger(log_path)
        lock = SupervisorLock()
        if not lock.acquire():
            logger.log(f"Supervisor already running; lock present at {lock.path}")
            print(f"Supervisor already running; lock present at {lock.path}")
        else:
            try:
                supervisor = FocusCheckSupervisor(
                    target_script=target_script,
                    python_executable=python_executable,
                    logger=logger,
                    check_interval=args.check_interval,
                    resume_gap=args.resume_gap,
                    restart_delay=args.restart_delay,
                )
                supervisor.run()
            finally:
                lock.release()

    if not did_anything:
        print("Nothing to do. Pass --run, --install-startup, or --uninstall-startup.")


if __name__ == "__main__":
    main()


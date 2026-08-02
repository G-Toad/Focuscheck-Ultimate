"""
FocusCheck - Main entry point.

Handles command-line arguments and application startup.
"""

import sys
import os
import ctypes
import time

# Ensure the package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SEM_FAILCRITICALERRORS = 0x0001
SEM_NOGPFAULTERRORBOX  = 0x0002
SEM_NOOPENFILEERRORBOX = 0x8000

if os.name == "nt":
    try:
        ctypes.windll.kernel32.SetErrorMode(
            SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX | SEM_NOOPENFILEERRORBOX
        )
    except Exception:
        pass

HEARTBEAT_FILENAME = "hb.txt"
HEARTBEAT_INTERVAL_MS = 1500


def _focuscheck_data_dir() -> str:
    base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
    if base:
        return os.path.join(base, "FocusCheck")
    return os.path.join(os.path.expanduser("~"), "FocusCheck")


HEARTBEAT_PATH = os.path.join(_focuscheck_data_dir(), HEARTBEAT_FILENAME)


def start_heartbeat_writer(app, interval_ms: int = HEARTBEAT_INTERVAL_MS) -> None:
    """Write a heartbeat file periodically so the supervisor can detect hangs."""
    directory = os.path.dirname(HEARTBEAT_PATH)

    def _beat() -> None:
        try:
            os.makedirs(directory, exist_ok=True)
            with open(HEARTBEAT_PATH, "w", encoding="ascii") as handle:
                handle.write(str(time.time()))
        except Exception:
            pass
        try:
            app.root.after(interval_ms, _beat)
        except Exception:
            pass

    try:
        _beat()
    except Exception:
        pass


from focuscheck import App
from focuscheck.platform_specific import install_startup, uninstall_startup
from focuscheck.utils import acquire_single_instance, get_logger

def setup_exception_handler():
    """Set up global exception handler."""
    def _global_excepthook(exc_type, exc, tb):
        try:
            get_logger().exception("UNCAUGHT: %s", exc)
        except Exception:
            pass
        try:
            sys.__excepthook__(exc_type, exc, tb)
        except Exception:
            pass
    
    try:
        sys.excepthook = _global_excepthook
    except Exception:
        pass


def main():
    """Main entry point."""
    setup_exception_handler()
    
    # Handle CLI arguments
    if "--selftest" in sys.argv:
        # Import and run selftest from refactored modules
        from focuscheck.platform_specific.windows import WindowsWakeWatcher
        from focuscheck.config import (
            WM_WTSSESSION_CHANGE, WTS_SESSION_LOCK, WTS_SESSION_UNLOCK,
            WM_POWERBROADCAST, PBT_APMSUSPEND, PBT_APMRESUMESUSPEND
        )
        from focuscheck.platform_specific.windows import WPARAM_T, LPARAM_T
        import tkinter as tk
        import platform
        import ctypes
        
        try:
            print("selftest: python_bits=", 8 * ctypes.sizeof(ctypes.c_void_p))
            if platform.system().lower() == "windows":
                r = tk.Tk()
                r.withdraw()
                ev = {"pause": 0, "resume": 0}
                
                def on_resume():
                    ev["resume"] += 1
                
                def on_pause(_):
                    ev["pause"] += 1
                
                w = WindowsWakeWatcher(r, on_resume_callable=on_resume, on_pause_callable=on_pause)
                hwnd = r.winfo_id()
                
                try:
                    _ = w._proc(hwnd, WM_WTSSESSION_CHANGE, WPARAM_T(WTS_SESSION_LOCK), LPARAM_T(0))
                    _ = w._proc(hwnd, WM_WTSSESSION_CHANGE, WPARAM_T(WTS_SESSION_UNLOCK), LPARAM_T(0))
                    _ = w._proc(hwnd, WM_POWERBROADCAST, WPARAM_T(PBT_APMSUSPEND), LPARAM_T(0))
                    _ = w._proc(hwnd, WM_POWERBROADCAST, WPARAM_T(PBT_APMRESUMESUSPEND), LPARAM_T(0))
                    _ = w._proc(hwnd, 0xFFFF, WPARAM_T(0xFFFFFFFFFFFFFFFF), LPARAM_T(-1))
                finally:
                    w.close()
                    r.destroy()
                print("selftest: windows callback path OK, ev=", ev)
            else:
                print("selftest: non-windows platform, skipping winproc test")
        except Exception as e:
            print("selftest: FAILED:", e)
            sys.exit(1)
        sys.exit(0)
    
    # Tray selftest
    if "--tray-selftest" in sys.argv:
        try:
            from tools.system_tray_selftest import main as _tray_selftest_main
            _tray_selftest_main()
        except Exception as e:
            try:
                get_logger().exception("tray-selftest failed", exc_info=True)
            except Exception:
                print(f"tray-selftest failed: {e}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)
    
    # Startup management
    if "--install-startup" in sys.argv:
        ok = install_startup()
        sys.exit(0 if ok else 1)
    
    if "--uninstall-startup" in sys.argv:
        ok = uninstall_startup()
        sys.exit(0 if ok else 1)
    
    # Tray test
    if "--tray-test" in sys.argv:
        import tkinter as tk
        from focuscheck.platform_specific.windows import WindowsWakeWatcher

        r = tk.Tk()
        r.withdraw()
        r.update_idletasks()
        try:
            w = WindowsWakeWatcher(
                r,
                on_resume_callable=lambda: None,
                tray_enabled=True,
                on_tray_click_callable=lambda _=None: None,
                tray_tooltip="Focus Check"
            )
            tk.Label(r, text="Tray test running...")
        except Exception as e:
            print(f"Tray test failed: {e}", file=sys.stderr)
            sys.exit(1)
        r.after(20000, lambda: (w.close(), r.destroy()))
        r.mainloop()
        sys.exit(0)
    
    # Single instance check
    if not acquire_single_instance():
        try:
            get_logger().warning("single-instance: exiting before UI start")
        except Exception:
            pass
        print("Another instance is already running. Exiting.", file=sys.stderr)
        sys.exit(0)
    
    # Start the application (with optional timeout/simulation)
    try:
        # Instantiate app first so we can schedule actions on its Tk loop
        app = App()
        start_heartbeat_writer(app)

        # Optional: run for N seconds then quit (prevents running forever during tests)
        run_secs = None
        for arg in sys.argv:
            if arg.startswith("--run-seconds="):
                try:
                    run_secs = int(arg.split("=", 1)[1])
                except Exception:
                    run_secs = None
                break
        if run_secs is not None and run_secs > 0:
            try:
                app.root.after(run_secs * 1000, app._quit)
            except Exception:
                pass

        # Optional: simulate a tray snooze click after a short delay
        simulate_snooze_mins = None
        for arg in sys.argv:
            if arg.startswith("--simulate-tray-snooze="):
                try:
                    simulate_snooze_mins = int(arg.split("=", 1)[1])
                except Exception:
                    simulate_snooze_mins = 5
                break
        # Optional: force-enable snooze confirmation for simulation
        if simulate_snooze_mins is not None:
            try:
                # Defer a bit to allow the app loop to settle
                app.root.after(1500, lambda: app._tray_snooze(simulate_snooze_mins))
            except Exception:
                pass

        app.run()
    except Exception as e:
        get_logger().exception("Application crashed: %s", e)
        print(f"Application error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

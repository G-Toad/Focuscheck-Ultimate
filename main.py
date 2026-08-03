"""
FocusCheck - Main entry point.

Handles command-line arguments and application startup.
"""

import sys
import os
import ctypes
import time
from ctypes import wintypes

# Ensure the package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SEM_FAILCRITICALERRORS = 0x0001
SEM_NOGPFAULTERRORBOX  = 0x0002
SEM_NOOPENFILEERRORBOX = 0x8000


def _configure_windows_error_api(kernel32):
    """Declare the process-wide Windows error-mode API before calling it."""
    kernel32.SetErrorMode.argtypes = [wintypes.UINT]
    kernel32.SetErrorMode.restype = wintypes.UINT

if os.name == "nt":
    try:
        kernel32 = ctypes.windll.kernel32
        _configure_windows_error_api(kernel32)
        kernel32.SetErrorMode(
            SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX | SEM_NOOPENFILEERRORBOX
        )
    except Exception:
        pass

from focuscheck import App
from focuscheck.platform_specific import install_startup, uninstall_startup
from focuscheck.utils import acquire_single_instance, get_logger, release_single_instance

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
        from focuscheck.utils.timers import TimerRegistry

        r = tk.Tk()
        r.withdraw()
        r.update_idletasks()
        timers = TimerRegistry(r)
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
            timers.close()
            r.destroy()
            print(f"Tray test failed: {e}", file=sys.stderr)
            sys.exit(1)

        def _finish_tray_test():
            timers.close()
            w.close()
            r.destroy()

        timers.schedule("tray-test-timeout", 20000, _finish_tray_test)
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
        app = App(force_start="--force-start" in sys.argv)
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
            app.schedule_once("cli-run-limit", run_secs * 1000, app._quit)

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
            # Defer a bit to allow the app loop to settle.
            app.schedule_once(
                "cli-simulate-tray-snooze",
                1500,
                lambda: app._tray_snooze(simulate_snooze_mins),
            )

        app.run()
    except Exception as e:
        get_logger().exception("Application crashed: %s", e)
        print(f"Application error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        release_single_instance()


if __name__ == "__main__":
    main()

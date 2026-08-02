"""Pause state management based on system conditions."""

import platform
import ctypes
import glob
import subprocess


from ..settings.gates import is_pause_enabled


class PauseGuard:
    """
    Manages automatic pausing based on idle time, lock, and sleep.
    
    Checks various conditions and determines if reminders should be paused.
    """
    
    def __init__(self, settings_getter):
        self._get_settings = settings_getter
        self._os = platform.system().lower()
        # Event-driven pause flags (Windows lock/sleep)
        self._locked = False
        self._sleeping = False

    # Event hooks (called by platform watchers)
    def set_locked(self, is_locked: bool):
        self._locked = bool(is_locked)

    def set_sleeping(self, is_sleeping: bool):
        self._sleeping = bool(is_sleeping)

    def should_pause(self):
        s = self._get_settings()
        if not is_pause_enabled(s):
            return False

        # If any enabled mechanism says "away", pause.
        if s.get("pause_on_idle", False) and self._looks_inactive_by_idle():
            return True
        if s.get("pause_on_lid_closed", True) and (self._looks_lid_closed_linux() or self._looks_lid_closed_macos()):
            return True
        if self._os == "windows":
            if s.get("pause_on_lock", True) and self._locked:
                return True
            if s.get("pause_on_sleep", True) and self._sleeping:
                return True
        return False

    # ---- Windows / general idle detection ----
    def _looks_inactive_by_idle(self):
        s = self._get_settings()
        thresh_ms = int(s.get("inactive_as_sleep_seconds", 45)) * 1000

        try:
            if platform.system().lower() == "windows":
                class LASTINPUTINFO(ctypes.Structure):
                    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
                plii = LASTINPUTINFO()
                plii.cbSize = ctypes.sizeof(LASTINPUTINFO)
                if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(plii)):
                    k32 = ctypes.windll.kernel32
                    # Prefer 64-bit tick count to avoid 49.7-day wrap
                    get64 = getattr(k32, 'GetTickCount64', None)
                    if get64:
                        tick_now = get64()
                        idle_ms = int(tick_now - plii.dwTime)
                    else:
                        tick_now = k32.GetTickCount()
                        # Handle wrap-around for 32-bit tick count (proper signed arithmetic)
                        diff = (int(tick_now) - int(plii.dwTime)) & 0xFFFFFFFF
                        if diff > 0x7FFFFFFF:
                            diff -= 0x100000000
                        idle_ms = abs(diff)
                    return idle_ms >= thresh_ms
                # If API fails, fall back to no-pause
                return False
            else:
                # On non-Windows, we don't have a clean idle API without deps.
                # Treat as not-inactive here; lid checks may still pause.
                return False
        except Exception:
            return False

    # ---- Linux laptop lid via ACPI ----
    def _looks_lid_closed_linux(self):
        if self._os != "linux":
            return False
        try:
            paths = glob.glob("/proc/acpi/button/lid/*/state")
            for p in paths:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    txt = f.read().lower()
                    if "closed" in txt:
                        return True
        except Exception:
            pass
        return False

    # ---- macOS clamshell ----
    def _looks_lid_closed_macos(self):
        if self._os != "darwin":
            return False
        try:
            # ioreg returns AppleClamshellState = Yes when lid is closed
            out = subprocess.check_output(
                ["ioreg", "-r", "-k", "AppleClamshellState", "-d", "1"],
                stderr=subprocess.DEVNULL, timeout=1.0
            ).decode("utf-8", "ignore").lower()
            if "appleclamshellstate" in out and ("= yes" in out or "yes" in out):
                return True
        except Exception:
            pass
        return False


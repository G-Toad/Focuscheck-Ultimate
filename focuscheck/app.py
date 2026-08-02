"""
Main application class for FocusCheck.

Handles the main event loop, scheduling of prompts, system tray integration,
and coordination of all application components.
"""

import json
import os
import sys
import time
import glob
import subprocess
import tempfile
import threading
import platform
import ctypes
import uuid
from pathlib import Path
from ctypes import wintypes
from datetime import datetime, timedelta, timezone
import tkinter as tk
from tkinter import messagebox

# Application config and constants
from .config import (
    APP_NAME,
    APP_VERSION,
    WM_LBUTTONUP,
)

# Settings management
from .settings import load_settings, save_settings, DEFAULT_SETTINGS

# Database
from .database import TaskDB, ensure_log_header

# UI components
from .ui.dialogs.task_entry_dialog import TaskEntryDialog
from .ui.dialogs.snooze_reminder_dialog import SnoozeReminderDialog
from .ui.guards import PauseGuard
from .runtime.state import RuntimeStateCoordinator
from .runtime.journal import RuntimeTransitionJournal
from .runtime.lifecycle import LifecycleCoordinator, LifecyclePhase
from .ui.prompt_coordinator import PromptCoordinator
from .utils.timers import TimerRegistry
from .ui.windows import SettingsWindow

# Monitoring engines
from .monitoring import EngineV1, EngineV2

# Lazy-imported in snooze flow to avoid circulars
try:
    from .ui.dialogs.snooze_prompt_dialog import SnoozePromptDialog
except Exception:
    SnoozePromptDialog = None  # type: ignore

# Platform-specific components
from .platform_specific import (
    install_startup,
    uninstall_startup,
    is_startup_installed,
)

# Utilities
from .utils import (
    get_logger,
    log_exception,
    get_data_dir,
    get_base_dir,
    migrate_legacy_data,
    resource_path,
)

# Path constants
from .utils.paths import (
    SETTINGS_PATH,
    HEARTBEAT_PATH,
    TASK_DB_PATH,
    APP_LOG_PATH,
    get_app_paths,
)

FILE_HEARTBEAT_INTERVAL_SECONDS = 60_000


def resolve_initial_monitoring_state(settings):
    """Return (started_bool, reason) for initial monitoring state."""
    try:
        force = str(os.environ.get("FOCUSCHECK_FORCE_STARTED", "")).strip().lower()
    except Exception:
        force = ""
    if force in ("1", "true", "yes", "on"):
        return True, "env_force_started"

    try:
        mode = str(os.environ.get("FOCUSCHECK_START_STOP_MODE", "")).strip().lower()
    except Exception:
        mode = ""
    if mode in ("stopped", "stop", "paused", "pause"):
        return False, "env_mode_stopped"

    if bool(settings.get("paused", False)):
        return False, "persisted_paused"

    return True, "default_force_started"


def _snapshot_window(root, window):
    snap = {
        "exists": None,
        "viewable": None,
        "ismapped": None,
        "state": None,
        "topmost": None,
        "geometry": None,
        "x": None,
        "y": None,
        "rootx": None,
        "rooty": None,
        "w": None,
        "h": None,
        "grab": None,
        "focus": None,
        "class": None,
        "name": None,
    }
    try:
        snap["exists"] = bool(window.winfo_exists())
    except Exception:
        pass
    try:
        snap["viewable"] = bool(window.winfo_viewable())
    except Exception:
        pass
    try:
        snap["ismapped"] = bool(window.winfo_ismapped())
    except Exception:
        pass
    try:
        snap["state"] = window.state()
    except Exception:
        pass
    try:
        snap["topmost"] = bool(window.attributes("-topmost"))
    except Exception:
        pass
    try:
        snap["geometry"] = window.winfo_geometry()
    except Exception:
        pass
    try:
        snap["x"] = int(window.winfo_x())
        snap["y"] = int(window.winfo_y())
        snap["rootx"] = int(window.winfo_rootx())
        snap["rooty"] = int(window.winfo_rooty())
        snap["w"] = int(window.winfo_width())
        snap["h"] = int(window.winfo_height())
    except Exception:
        pass
    try:
        snap["class"] = window.winfo_class()
    except Exception:
        pass
    try:
        snap["name"] = window.winfo_name()
    except Exception:
        pass
    try:
        grab = root.grab_current()
        snap["grab"] = getattr(grab, "winfo_name", lambda: str(grab))() if grab is not None else None
    except Exception:
        pass
    try:
        focus = root.focus_get()
        snap["focus"] = getattr(focus, "winfo_name", lambda: str(focus))() if focus is not None else None
    except Exception:
        pass
    return snap


def _window_visible(window):
    try:
        return bool(window.winfo_exists()) and bool(window.winfo_viewable())
    except Exception:
        return False

# Optional system tray (gracefully degrades if not available)
try:
    from .system_tray import SystemTray
except ImportError:
    SystemTray = None  # type: ignore

# Platform-specific imports
if platform.system().lower() == "windows":
    from .platform_specific import WindowsWakeWatcher


class App:
    def __init__(self):
        self.lifecycle = LifecycleCoordinator()
        self.lifecycle.transition(LifecyclePhase.STARTING, reason="app_construct")
        self.root = tk.Tk()
        self._tk_thread_id = threading.get_ident()
        try:
            self.root._focuscheck_tk_thread_id = self._tk_thread_id
        except Exception:
            pass
        try:
            def _tk_callback_exception(exc, val, tb):
                try:
                    get_logger().exception("tk callback exception", exc_info=(exc, val, tb))
                except Exception:
                    pass
            self.root.report_callback_exception = _tk_callback_exception
        except Exception:
            pass
        self.root.withdraw()
        self._timers = TimerRegistry(self.root)
        # Ensure window handle is realized before using it for shell hooks
        try:
            self.root.update_idletasks()
        except Exception:
            pass
        # Emergency quit shortcuts (for dev convenience)
        try:
            self.root.bind_all('<Control-Shift-Escape>', lambda e: self._quit())
            self.root.bind_all('<Alt-q>', lambda e: self._quit())
        except Exception:
            pass
        self.settings = load_settings()
        try:
            migration_events = migrate_legacy_data(get_app_paths())
            if migration_events:
                get_logger().info("legacy data migration completed | events=%d", len(migration_events))
        except Exception:
            get_logger().exception("legacy data migration failed", exc_info=True)
        self._runtime_journal = RuntimeTransitionJournal(get_app_paths().runtime_state)
        self._runtime_state = RuntimeStateCoordinator(
            self.settings,
            persist=save_settings,
            transition_sink=self._runtime_journal.append,
        )
        self._snooze_unpause_timer_id = None
        self._snooze_confirm_dialog = None
        try:
            self._apply_initial_monitoring_state()
        except Exception:
            try:
                get_logger().exception("startup: failed applying initial monitoring state", exc_info=True)
            except Exception:
                pass
        self._engine = None
        # App start times for runtime reporting
        self._start_wall = datetime.now()
        self._start_mono = time.monotonic()
        try:
            get_logger().info("App starting v%s | data_dir=%s", APP_VERSION, get_data_dir())
        except Exception:
            pass
        # Init task DB
        try:
            self.taskdb = TaskDB(TASK_DB_PATH)
        except Exception:
            self.taskdb = None
            log_exception("TaskDB unavailable; continuing without tasks feature")
        ensure_log_header()
        self.guard = PauseGuard(lambda: self.settings)
        self._ensure_engine()
        self._scheduled = None
        self._current_prompt = None
        self._prompt_coordinator = PromptCoordinator()
        self._intervention_active = False
        self._last_resume_mono = 0.0
        self._next_due_mono = None
        self._next_total_s = None
        self._shutdown_requested = False
        self._heartbeat_sequence = 0
        self._process_start_utc = datetime.now(timezone.utc).isoformat()
        # Snooze reminder tracking
        self._snooze_reminder_next_mono = 0.0
        self._snooze_reminder_dialog = None
        self._tray_icon_image = None
        self._tray_icon_path = None
        self._prepare_tray_icon()
        # Heartbeat to catch paused->unpaused edges
        self._start_heartbeat()
        # File heartbeat for watchdogs
        self._start_file_heartbeat()
        # Snooze reminder check loop
        self._start_snooze_reminder_check()

        # Startup diagnostics (log versions and tray import attempts)
        try:
            self._log_startup_diagnostics()
        except Exception:
            pass

        # Optional cross-platform tray using pystray (preferred when available)
        self._pystray_started = False  # started (requested)
        self._using_pystray = False    # proven alive
        self._tray = None
        try:
            if SystemTray is not None:
                try:
                    get_logger().info("startup: pystray system tray available; attempting start")
                except Exception:
                    pass
                def _get(k, d=None):
                    try:
                        return self.settings.get(k, d)
                    except Exception:
                        return d
                def _set(k, v):
                    try:
                        self.settings[k] = v
                        save_settings(self.settings)
                    except Exception:
                        pass
                # Hooks to track pystray status
                def _on_alive():
                    # Proved alive; mark as using pystray
                    try:
                        get_logger().info("tray post-start check OK (pystray alive)")
                    except Exception:
                        pass
                    self._using_pystray = True
                def _on_failure():
                    # pystray failed - enable native tray if available
                    try:
                        get_logger().error("pystray post-start check failed", exc_info=True)
                    except Exception:
                        pass
                    # If we have a Windows watcher but tray is disabled, enable it
                    if platform.system().lower() == "windows" and getattr(self, "_winwatch", None) is not None:
                        try:
                            # Try to enable the native tray on the existing watcher
                            if hasattr(self._winwatch, '_tray_add'):
                                self._winwatch._tray_add("Focus Check")
                                get_logger().info("fallback: enabled native tray after pystray failure")
                        except Exception:
                            get_logger().exception("failed to enable native tray fallback", exc_info=True)

                self._tray = SystemTray(
                    app=self,
                    name=APP_NAME,
                    tooltip=f"{APP_NAME} running",
                    get_setting=_get,
                    set_setting=_set,
                    open_settings_ui=lambda: self._open_settings_from_tray(),
                    logs_path=APP_LOG_PATH,
                    config_path=SETTINGS_PATH,
                    icon_image=self._tray_icon_image,
                    on_failure=_on_failure,
                    on_alive=_on_alive,
                )
                # Explicit marker for tray creation attempt (pystray)
                try:
                    get_logger().info("creating icon (pystray)")
                except Exception:
                    pass
                started = False
                try:
                    started = bool(self._tray.start())
                except Exception:
                    get_logger().exception("pystray start raised", exc_info=True)
                    started = False
                if started:
                    self._pystray_started = True
                    try:
                        get_logger().info("tray start succeeded (pystray)")
                        get_logger().info("startup: pystray tray started successfully")
                    except Exception:
                        pass
                else:
                    try:
                        get_logger().error("tray start failed (pystray)")
                        get_logger().warning("startup: pystray tray failed to start; falling back (Windows native, if available)")
                    except Exception:
                        pass
        except Exception:
            get_logger().exception("pystray setup failed", exc_info=True)
            self._pystray_started = False
            self._using_pystray = False

        # Windows: listen for power/session/display and enable native tray only if pystray failed.
        self._winwatch = None
        if platform.system().lower() == "windows":
            try:
                # Only enable native tray if pystray didn't start successfully
                enable_native_tray = not self._pystray_started
                self._winwatch = WindowsWakeWatcher(
                    self.root,
                    on_resume_callable=self._on_resume_event,
                    on_pause_callable=self._on_pause_event,
                    on_display_change_callable=self._on_display_change,
                    tray_enabled=enable_native_tray,
                    on_tray_click_callable=self._on_tray_click,
                    tray_tooltip="Focus Check",
                    tray_icon_path=self._tray_icon_path,
                    on_shutdown_callable=self._handle_system_shutdown,
                )
                try:
                    get_logger().info("startup: Windows watcher initialized | native_tray=%s", enable_native_tray)
                except Exception:
                    pass
            except Exception as e:
                print(f"Windows watcher/tray unavailable: {e}", file=sys.stderr)
        # quick first pop to prove it works
        self._schedule_next(2000)
        self.lifecycle.transition(LifecyclePhase.READY, reason="app_ready")

    def _apply_initial_monitoring_state(self):
        desired, reason = resolve_initial_monitoring_state(self.settings)
        self._reconcile_snooze_state_on_startup()
        persisted_paused = bool(self.settings.get("paused", False))
        logger = get_logger()
        if desired:
            if bool(self.settings.get("paused", False)) and str(self.settings.get("snooze_until_utc", "")).strip():
                try:
                    logger.info("startup: preserving active snooze until %s", self.settings.get("snooze_until_utc"))
                except Exception:
                    pass
                return
            if persisted_paused:
                try:
                    logger.info("startup: overriding persisted paused=True -> False")
                except Exception:
                    pass
            changed = self._set_paused(False, source=f"startup_{reason}")
            try:
                if changed:
                    logger.info("startup: initial monitoring state=STARTED (forced) reason=%s", reason)
                else:
                    logger.info("startup: initial monitoring state=STARTED (already running) reason=%s", reason)
            except Exception:
                pass
        else:
            if not persisted_paused:
                try:
                    logger.info("startup: overriding persisted paused=False -> True")
                except Exception:
                    pass
            changed = self._set_paused(True, source=f"startup_{reason}")
            try:
                if changed:
                    logger.info("startup: initial monitoring state=STOPPED (env override) reason=%s", reason)
                else:
                    logger.info("startup: initial monitoring state=STOPPED (already stopped) reason=%s", reason)
            except Exception:
                pass

    def _prepare_tray_icon(self):
        candidates: list[str] = []

        # Priority 1: Check assets directory for custom tray_icon.png
        try:
            assets_dir = os.path.join(get_base_dir(), 'focuscheck', 'assets')
            custom_icon = os.path.join(assets_dir, 'tray_icon.png')
            if os.path.exists(custom_icon):
                candidates.append(custom_icon)
                get_logger().info(f"Using custom tray icon: {custom_icon}")
        except Exception as e:
            get_logger().debug(f"No custom tray icon found: {e}")

        # Priority 2: Original default icon
        try:
            png_path = resource_path('imageedit_5_9158249849.png')
            if png_path and os.path.exists(png_path):
                candidates.append(png_path)
        except Exception:
            pass

        # Priority 3: Search for any PNG/ICO in base directories
        try:
            base_dirs = []
            try:
                if getattr(sys, "_MEIPASS", None):
                    base_dirs.append(sys._MEIPASS)
            except Exception:
                pass
            base_dirs.append(get_base_dir())
            for b in base_dirs:
                try:
                    for p in glob.glob(os.path.join(b, "*.png")):
                        if p not in candidates and os.path.exists(p):
                            candidates.append(p)
                    for p in glob.glob(os.path.join(b, "*.ico")):
                        if p not in candidates and os.path.exists(p):
                            candidates.append(p)
                except Exception:
                    pass
        except Exception:
            pass
        if not candidates:
            return
        first = candidates[0]
        self._tray_icon_path = first  # keep whatever we found so native tray can try it
        try:
            from PIL import Image  # type: ignore
        except Exception:
            return
        try:
            with Image.open(first) as img:
                image_rgba = img.convert("RGBA")
                self._tray_icon_image = image_rgba.copy()
                sizes = [16, 20, 24, 32, 48, 64, 128]
                available = [s for s in sizes if s <= min(image_rgba.size)] or [min(image_rgba.size)]
                tmp_path = os.path.join(tempfile.gettempdir(), "focuscheck_tray.ico")
                image_rgba.save(tmp_path, format="ICO", sizes=[(s, s) for s in available])
                self._tray_icon_path = tmp_path
        except Exception:
            self._tray_icon_image = None
            self._tray_icon_path = first
            try:
                get_logger().exception("failed preparing tray icon", exc_info=True)
            except Exception:
                pass

    def _reconcile_snooze_state_on_startup(self):
        snooze_until = str(self.settings.get("snooze_until_utc", "") or "").strip()
        if not snooze_until:
            return
        try:
            until = datetime.fromisoformat(snooze_until)
            if until.tzinfo is None:
                until = until.replace(tzinfo=timezone.utc)
            else:
                until = until.astimezone(timezone.utc)
            now = datetime.now(timezone.utc)
            if until <= now:
                self.settings["snooze_until_utc"] = ""
                self.settings["paused"] = False
                save_settings(self.settings)
                return
            self.settings["paused"] = True
            save_settings(self.settings)
            remaining_ms = max(1, int((until - now).total_seconds() * 1000))

            def _expire_snooze():
                self._snooze_unpause_timer_id = None
                self.settings["snooze_until_utc"] = ""
                self._set_paused(False, source="snooze_expired_startup")
                self._schedule_next(0)

            self._snooze_unpause_timer_id = self.root.after(remaining_ms, _expire_snooze)
        except Exception:
            self.settings["snooze_until_utc"] = ""
            save_settings(self.settings)

    def _get_engine_class(self, settings):
        try:
            mode = str(settings.get("monitoring_mode", "v1")).strip().lower()
        except Exception:
            mode = "v1"
        return EngineV2 if mode == "v2" else EngineV1

    def _ensure_engine(self):
        cls = self._get_engine_class(self.settings)
        if self._engine is None or not isinstance(self._engine, cls):
            old_engine = self._engine
            self._engine = cls(self)
            try:
                if old_engine is not None:
                    old_engine.shutdown()
            except Exception:
                pass
            try:
                get_logger().info("monitoring engine set to %s", getattr(self._engine, "name", cls.__name__))
            except Exception:
                pass
        try:
            self._engine.on_settings_updated(self.settings)
        except Exception:
            pass

    def _schedule_next(self, delay_ms=None):
        if delay_ms is None:
            delay_ms = int(self.settings["interval_seconds"] * 1000)
        if self._scheduled and not hasattr(self, "_timers"):
            try:
                self.root.after_cancel(self._scheduled)
            except Exception:
                pass
            self._scheduled = None
        try:
            get_logger().debug("scheduling next prompt in %sms", delay_ms)
        except Exception:
            pass
        if hasattr(self, "_timers"):
            self._timers.schedule("prompt", delay_ms, self._maybe_show_prompt)
            self._scheduled = self._timers.callback_id("prompt")
        else:
            self._scheduled = self.root.after(delay_ms, self._maybe_show_prompt)
        # Track next due for tray meter
        try:
            self._next_total_s = max(1, int(delay_ms // 1000))
            self._next_due_mono = time.monotonic() + (delay_ms / 1000.0)
        except Exception:
            self._next_total_s = None
            self._next_due_mono = None

    def _format_hms(self, seconds):
        try:
            seconds = int(max(0, seconds))
            m, s = divmod(seconds, 60)
            h, m = divmod(m, 60)
            if h:
                return f"{h}:{m:02d}:{s:02d}"
            else:
                return f"{m}:{s:02d}"
        except Exception:
            return "--"


    def _start_heartbeat(self):
        # Fires a prompt immediately on paused->unpaused transition, as a safety net.
        self._last_paused_state = None
        def tick():
            try:
                paused_now = self.guard.should_pause()
                if self._last_paused_state is True and paused_now is False:
                    # Transition from paused to unpaused: schedule a prompt now
                    self._schedule_next(0)
                self._last_paused_state = paused_now
            except Exception:
                pass
            if hasattr(self, "_timers"):
                return
            self.root.after(1000, tick)  # 1 Hz
        tick()
        if hasattr(self, "_timers"):
            self._timers.schedule("pause-edge", 1000, tick, interval_ms=1000)

    def _maybe_show_prompt(self):
        self.settings = load_settings()  # refresh
        if getattr(self, "_runtime_state", None) is not None:
            self._runtime_state.refresh_from_settings(self.settings)
            guard_paused = bool(self.guard.should_pause())
            self._runtime_state.set_guard_reason("system_guard", guard_paused)
            if self._runtime_state.snapshot.effectively_paused:
                poll_ms = int(self.settings.get("pause_poll_interval_seconds", 5)) * 1000
                self._schedule_next(poll_ms)
                return
        try:
            get_logger().info(
                "prompt: maybe_show | thread=%s tk_thread=%s",
                threading.get_ident(),
                getattr(self, "_tk_thread_id", None),
            )
        except Exception:
            pass
        # Global pause toggle supported by SystemTray (optional)
        try:
            if bool(self.settings.get("paused", False)):
                poll_ms = int(self.settings.get("pause_poll_interval_seconds", 5)) * 1000
                self._schedule_next(poll_ms)
                return
        except Exception:
            pass
        # Clear stale grabs that block new dialogs
        try:
            grab = self.root.grab_current()
            if grab is not None and not _window_visible(grab):
                try:
                    get_logger().warning("prompt: releasing stale grab | owner=%s", getattr(grab, "winfo_name", lambda: str(grab))())
                except Exception:
                    pass
                try:
                    grab.grab_release()
                except Exception:
                    pass
        except Exception:
            pass
        # Prevent duplicate concurrent prompts
        try:
            if self._current_prompt is not None and not getattr(self._current_prompt, "_closed", False):
                try:
                    snap = _snapshot_window(self.root, self._current_prompt)
                    get_logger().info("prompt: existing prompt snapshot | %s", snap)
                except Exception:
                    pass
                try:
                    if not self._current_prompt.winfo_exists():
                        get_logger().warning("prompt: stale prompt handle; clearing")
                        self._current_prompt = None
                    elif not _window_visible(self._current_prompt):
                        # Attempt recovery of hidden prompt
                        try:
                            self._current_prompt.update_idletasks()
                            self._current_prompt.deiconify()
                            self._current_prompt.lift()
                            self._current_prompt.focus_force()
                            if hasattr(self._current_prompt, "_center_on_active_monitor"):
                                self._current_prompt._center_on_active_monitor()
                            elif hasattr(self._current_prompt, "ensure_on_screen"):
                                self._current_prompt.ensure_on_screen()
                        except Exception:
                            pass
                        try:
                            snap2 = _snapshot_window(self.root, self._current_prompt)
                            get_logger().info("prompt: recovery snapshot | %s", snap2)
                        except Exception:
                            pass
                        if not _window_visible(self._current_prompt):
                            get_logger().warning("prompt: hidden prompt still not visible; destroying and clearing")
                            try:
                                self._current_prompt.destroy()
                            except Exception:
                                pass
                            self._current_prompt = None
                    if self._current_prompt is not None:
                        # An active prompt is already open; check again shortly
                        get_logger().info("prompt already open; deferring new prompt")
                        self._schedule_next(1500)
                        return
                except Exception:
                    # If any prompt state check fails, fall back to deferring
                    try:
                        get_logger().exception("prompt: failed checking existing prompt", exc_info=True)
                    except Exception:
                        pass
                    self._schedule_next(1500)
                    return
        except Exception:
            pass
        # Prevent prompts while intervention workflow is active
        try:
            if bool(getattr(self, "_intervention_active", False)):
                self._schedule_next(1500)
                return
        except Exception:
            pass
        if self.guard.should_pause():
            poll_ms = int(self.settings.get("pause_poll_interval_seconds", 5)) * 1000
            try:
                get_logger().info("prompt: suppressed due to guard pause; poll_ms=%s", poll_ms)
            except Exception:
                pass
            self._schedule_next(poll_ms)
            return

        self._ensure_engine()

        runtime_state = getattr(self, "_runtime_state", None)
        if runtime_state is not None and not runtime_state.begin_prompt():
            self._schedule_next(1500)
            return

        slot_info = self._slot_start_info()
        try:
            get_logger().info("showing prompt @ %s", slot_info["local_minute"])  # best-effort
        except Exception:
            pass
        try:
            try:
                get_logger().info("prompt: about to create dialog")
            except Exception:
                pass
            dlg = self._engine.create_prompt(self.settings, slot_info)
        except Exception:
            log_exception("monitoring engine failed to create prompt")
            if runtime_state is not None:
                runtime_state.end_prompt()
            self._schedule_next()
            return
        if dlg is None:
            if runtime_state is not None:
                runtime_state.end_prompt()
            self._schedule_next()
            return
        self._current_prompt = dlg
        prompt_generation = self._prompt_coordinator.open(dlg)
        if prompt_generation is None:
            self._current_prompt = None
            if runtime_state is not None:
                runtime_state.end_prompt()
            self._schedule_next(1500)
            return
        try:
            dlg.update_idletasks()
            dlg.deiconify()
            dlg.lift()
            dlg.focus_force()
        except Exception:
            pass
        try:
            snap = _snapshot_window(self.root, dlg)
            get_logger().info("prompt: created dialog | %s", snap)
        except Exception:
            pass

        def _check_prompt_visible():
            try:
                if not _window_visible(dlg):
                    try:
                        get_logger().warning("prompt: dialog not visible after delay; attempting recovery")
                    except Exception:
                        pass
                    try:
                        dlg.update_idletasks()
                        dlg.deiconify()
                        dlg.lift()
                        dlg.focus_force()
                        if hasattr(dlg, "_center_on_active_monitor"):
                            dlg._center_on_active_monitor()
                        elif hasattr(dlg, "ensure_on_screen"):
                            dlg.ensure_on_screen()
                    except Exception:
                        pass
                    try:
                        snap2 = _snapshot_window(self.root, dlg)
                        get_logger().info("prompt: post-recovery snapshot | %s", snap2)
                    except Exception:
                        pass
            except Exception:
                try:
                    get_logger().exception("prompt: visibility check failed", exc_info=True)
                except Exception:
                    pass

        try:
            self.root.after(300, _check_prompt_visible)
        except Exception:
            pass

        # Use non-blocking approach instead of wait_window() to avoid GIL issues with pystray
        def _check_dialog_closed():
            try:
                if not self._prompt_coordinator.is_current(dlg, prompt_generation):
                    return
                # Check if dialog window still exists
                if dlg.winfo_exists():
                    # Dialog still open, check again in 100ms
                    self.root.after(100, _check_dialog_closed)
                else:
                    # Dialog closed, schedule next prompt
                    self._on_prompt_done()
            except Exception:
                # Dialog destroyed or error, schedule next prompt
                self._on_prompt_done()

        # Start checking if dialog is closed
        self.root.after(100, _check_dialog_closed)




    def _slot_start_info(self):
        now = datetime.now()
        local_minute = now.strftime("%H:%M")
        return {
            "utc_start": datetime.now(timezone.utc),
            "local_minute": local_minute,
            "mono_start": time.monotonic()
        }

    # --- Windows event hooks ---
    def _on_pause_event(self, reason: str):
        # Set event-driven pause flags based on reason
        try:
            if reason == "lock":
                self.guard.set_locked(True)
            elif reason == "sleep":
                self.guard.set_sleeping(True)
            try:
                get_logger().info("system pause reason=%s", reason)
            except Exception:
                pass
        except Exception:
            pass

        if reason in {"lock", "sleep"}:
            try:
                self._schedule_next(int(self.settings.get("pause_poll_interval_seconds", 5)) * 1000)
            except Exception:
                pass

    def _on_resume_event(self):
        # Clear pause flags and prompt immediately
        try:
            self.guard.set_locked(False)
            self.guard.set_sleeping(False)
        except Exception:
            pass
        now = time.monotonic()
        if now - self._last_resume_mono > 2.0:  # debounce
            self._schedule_next(0)
        self._last_resume_mono = now
        try:
            get_logger().info("system resume")
        except Exception:
            pass

    def _handle_system_shutdown(self, stage: str):
        if self._shutdown_requested:
            try:
                get_logger().info("system shutdown already in progress (stage=%s)", stage)
            except Exception:
                pass
            return
        self._shutdown_requested = True
        lifecycle = getattr(self, "lifecycle", None)
        if lifecycle is not None:
            lifecycle.begin_shutdown(reason=f"windows_{stage}")
        try:
            get_logger().info("system shutdown requested | stage=%s", stage)
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
        time.sleep(0.1)
        os._exit(0)

    def _on_prompt_done(self):
        prompt = self._current_prompt
        if prompt is None:
            return
        coordinator = getattr(self, "_prompt_coordinator", None)
        if coordinator is None:
            coordinator = PromptCoordinator()
            self._prompt_coordinator = coordinator
        coordinator.complete(prompt)
        self._current_prompt = None
        state = getattr(self, "_runtime_state", None)
        if state is not None:
            state.end_prompt()
        self._schedule_next()

    def run_intervention(self, settings, *, preselect_hwnd=None, preselect_title=None) -> bool:
        """Run one intervention under the application-owned lease."""
        state = getattr(self, "_runtime_state", None)
        if state is not None and not state.begin_intervention():
            return False
        self._intervention_active = True
        try:
            from .ui.dialogs.intervention_wizard import InterventionWizard
            wizard = InterventionWizard(self.root, settings)
            return bool(wizard.run(preselect_hwnd=preselect_hwnd, preselect_title=preselect_title))
        except Exception:
            try:
                get_logger().exception("intervention coordinator failed", exc_info=True)
            except Exception:
                pass
            return False
        finally:
            self._intervention_active = False
            if state is not None:
                state.end_intervention()

    # Display/DPI change: keep dialogs on-screen
    def _on_display_change(self):
        try:
            if self._current_prompt is not None:
                if self.settings.get("center_on_show", True):
                    self._current_prompt._center_on_active_monitor()
                else:
                    self._current_prompt.ensure_on_screen()
            try:
                get_logger().info("display/DPI change handled")
            except Exception:
                pass
        except Exception:
            pass

    def _call_on_ui_thread(self, callback, *args, **kwargs):
        """Ensure callbacks involving Tk run on the UI thread."""
        root = getattr(self, "root", None)
        if root is None:
            return False
        owner_thread_id = getattr(self, "_tk_thread_id", None)
        if owner_thread_id is None:
            owner_thread_id = getattr(root, "_focuscheck_tk_thread_id", None)
        if owner_thread_id is None:
            owner_thread_id = threading.main_thread().ident
        if threading.get_ident() == owner_thread_id:
            try:
                callback(*args, **kwargs)
                return True
            except Exception:
                try:
                    get_logger().exception("UI dispatch failed", exc_info=True)
                except Exception:
                    pass
                return False
        def _wrapped():
            try:
                callback(*args, **kwargs)
            except Exception:
                try:
                    get_logger().exception("UI dispatch failed", exc_info=True)
                except Exception:
                    pass
        try:
            root.after(0, _wrapped)
            return True
        except Exception:
            try:
                get_logger().exception("Failed scheduling UI callback", exc_info=True)
            except Exception:
                pass
            return False

    # Tray menu
    def _on_tray_click(self, msg=None):
        try:
            try:
                self.settings = load_settings()
            except Exception:
                pass
            if msg == WM_LBUTTONUP:
                if bool(self.settings.get("tray_start_stop_enabled", True)):
                    self._tray_toggle_pause()
                else:
                    self._show_tray_menu()
            else:
                self._show_tray_menu()
        except Exception:
            pass

    def _show_tray_menu(self):
        try:
            try:
                self.settings = load_settings()
            except Exception:
                pass
            paused = bool(self.settings.get("paused", False))
            start_stop_enabled = bool(self.settings.get("tray_start_stop_enabled", True))
            settings_enabled = bool(self.settings.get("tray_settings_button_enabled", True))
            exit_enabled = bool(self.settings.get("tray_exit_button_enabled", True))
            taskdb_available = getattr(self, "taskdb", None) is not None
            startup_enabled = False
            try:
                startup_enabled = self._is_startup_enabled()
            except Exception:
                startup_enabled = False

            native_used = False
            try:
                user32 = ctypes.windll.user32
                TrackPopupMenu = user32.TrackPopupMenu
                try:
                    TrackPopupMenu.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.HWND, ctypes.c_void_p]
                    TrackPopupMenu.restype = ctypes.c_int
                except Exception:
                    pass

                MF_STRING = 0x00000000
                MF_DISABLED = 0x00000002
                MF_GRAYED = 0x00000001
                MF_SEPARATOR = 0x00000800
                TPM_RIGHTBUTTON = 0x0002
                TPM_RETURNCMD = 0x0100
                TPM_NONOTIFY = 0x0080

                CMD_STOP = 1001
                CMD_START = 1002
                CMD_PROMPT = 1003
                CMD_SNOOZE_5 = 1004
                CMD_SNOOZE_15 = 1005
                CMD_SETTINGS = 1006
                CMD_TASK = 1007
                CMD_STARTUP = 1008
                CMD_DATA = 1009
                CMD_LOGS = 1010
                CMD_EXIT = 1011

                actions = {}
                labels = []
                hmenu = user32.CreatePopupMenu()
                if hmenu:
                    try:
                        def _flags(enabled=True):
                            if enabled:
                                return MF_STRING
                            return MF_STRING | MF_DISABLED | MF_GRAYED

                        def _append(cmd_id, text, enabled=True, action=None):
                            label = ctypes.c_wchar_p(text)
                            if not user32.AppendMenuW(hmenu, _flags(enabled), cmd_id, label):
                                raise ctypes.WinError()
                            labels.append(label)
                            if action:
                                actions[cmd_id] = action

                        def _separator():
                            if not user32.AppendMenuW(hmenu, MF_SEPARATOR, 0, None):
                                raise ctypes.WinError()

                        _append(CMD_STOP, "Stop reminders", enabled=start_stop_enabled and not paused, action=self._tray_pause)
                        _append(CMD_START, "Start reminders", enabled=start_stop_enabled and paused, action=self._tray_resume)
                        _separator()
                        _append(CMD_PROMPT, "Prompt now", action=self._tray_prompt_now)
                        _append(CMD_SNOOZE_5, "Snooze 5 minutes", action=lambda: self._tray_snooze(5))
                        _append(CMD_SNOOZE_15, "Snooze 15 minutes", action=lambda: self._tray_snooze(15))
                        _separator()
                        _append(CMD_SETTINGS, "Settings", enabled=settings_enabled, action=self._open_settings_from_tray)
                        _append(CMD_TASK, "Set/Change Task", enabled=taskdb_available, action=self._open_task_dialog_from_tray)
                        _separator()
                        if startup_enabled:
                            _append(CMD_STARTUP, "Disable Run on Startup", action=self._tray_uninstall_startup)
                        else:
                            _append(CMD_STARTUP, "Enable Run on Startup", action=self._tray_install_startup)
                        _append(CMD_DATA, "Open Data Folder", action=self._tray_open_data_folder)
                        _append(CMD_LOGS, "Open Logs Folder", action=self._tray_open_logs_folder)
                        _separator()
                        _append(CMD_EXIT, "Exit", enabled=exit_enabled, action=self._tray_exit)

                        class POINT(ctypes.Structure):
                            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

                        pt = POINT()
                        if not user32.GetCursorPos(ctypes.byref(pt)):
                            pt.x = pt.y = 0
                        try:
                            # Get hwnd from WindowsWakeWatcher if available
                            hwnd = self._winwatch.hwnd if self._winwatch else self.root.winfo_id()
                            user32.SetForegroundWindow(hwnd)
                        except Exception:
                            pass
                        try:
                            ctypes.set_last_error(0)
                        except AttributeError:
                            try:
                                ctypes.windll.kernel32.SetLastError(0)
                            except Exception:
                                pass
                        hwnd = self._winwatch.hwnd if self._winwatch else self.root.winfo_id()
                        cmd = TrackPopupMenu(
                            hmenu,
                            TPM_RIGHTBUTTON | TPM_RETURNCMD | TPM_NONOTIFY,
                            int(pt.x),
                            int(pt.y),
                            0,
                            hwnd,
                            None,
                        )
                        if cmd == 0:
                            err = ctypes.get_last_error()
                            if err:
                                raise ctypes.WinError(err)
                    finally:
                        try:
                            user32.DestroyMenu(hmenu)
                        except Exception:
                            pass
                    native_used = True
                    action = actions.get(cmd)
                    if action:
                        action()
            except Exception:
                native_used = False
            if native_used:
                return

            try:
                get_logger().debug("tray menu opened | paused=%s", paused)
            except Exception:
                pass
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(
                label="Stop reminders",
                command=self._tray_pause,
                state=(tk.NORMAL if start_stop_enabled and not paused else tk.DISABLED),
            )
            menu.add_command(
                label="Start reminders",
                command=self._tray_resume,
                state=(tk.NORMAL if start_stop_enabled and paused else tk.DISABLED),
            )
            menu.add_separator()
            menu.add_command(label="Prompt now", command=self._tray_prompt_now)
            menu.add_command(label="Snooze 5 minutes", command=lambda: self._tray_snooze(5))
            menu.add_command(label="Snooze 15 minutes", command=lambda: self._tray_snooze(15))
            menu.add_separator()
            menu.add_command(
                label="Settings",
                command=self._open_settings_from_tray,
                state=(tk.NORMAL if settings_enabled else tk.DISABLED),
            )
            menu.add_command(
                label="Set/Change Task",
                command=self._open_task_dialog_from_tray,
                state=(tk.NORMAL if taskdb_available else tk.DISABLED),
            )
            menu.add_separator()
            if startup_enabled:
                menu.add_command(label="Disable Run on Startup", command=self._tray_uninstall_startup)
            else:
                menu.add_command(label="Enable Run on Startup", command=self._tray_install_startup)
            menu.add_command(label="Open Data Folder", command=self._tray_open_data_folder)
            menu.add_command(label="Open Logs Folder", command=self._tray_open_logs_folder)
            menu.add_separator()
            menu.add_command(
                label="Exit",
                command=self._tray_exit,
                state=(tk.NORMAL if exit_enabled else tk.DISABLED),
            )
            x = y = 0
            try:
                class POINT(ctypes.Structure):
                    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
                pt = POINT()
                ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
                x, y = pt.x, pt.y
            except Exception:
                pass
            try:
                menu.tk_popup(x, y)
            finally:
                try:
                    menu.grab_release()
                except Exception:
                    pass
        except Exception:
            pass


    def _set_paused(self, value: bool, *, source: str = "tray") -> bool:
        value = bool(value)
        changed = self._runtime_state.set_manual_paused(value)
        if not changed:
            return False
        try:
            get_logger().info("paused=%s via %s", value, source)
            if value:
                get_logger().info("monitoring: stopped by %s", source)
            else:
                get_logger().info("monitoring: started by %s", source)
        except Exception:
            pass
        return True

    def _cancel_snooze(self):
        if hasattr(self, "_timers"):
            self._timers.cancel("snooze-expiry")
        if self._snooze_unpause_timer_id is not None:
            try:
                self.root.after_cancel(self._snooze_unpause_timer_id)
            except Exception:
                pass
            self._snooze_unpause_timer_id = None
        if str(self.settings.get("snooze_until_utc", "") or "").strip():
            state = getattr(self, "_runtime_state", None)
            if state is not None:
                state.clear_snooze()
            else:
                self.settings["snooze_until_utc"] = ""
                try:
                    save_settings(self.settings)
                except Exception:
                    pass

    def _close_current_prompt(self, source="unknown"):
        prompt = getattr(self, "_current_prompt", None)
        if prompt is None:
            return False
        try:
            if getattr(prompt, "_closed", False):
                self._current_prompt = None
                return False
        except Exception:
            pass
        try:
            if not prompt.winfo_exists():
                self._current_prompt = None
                return False
        except Exception:
            self._current_prompt = None
            return False
        try:
            prompt._closed = True
        except Exception:
            pass
        for cleanup_name in ("_cleanup_camera_feed", "_cleanup_all_timers", "_cleanup_timers", "_destroy_stage5_overlays"):
            try:
                cleanup = getattr(prompt, cleanup_name, None)
                if callable(cleanup):
                    cleanup()
            except Exception:
                pass
        try:
            prompt.destroy()
        except Exception:
            pass
        coordinator = getattr(self, "_prompt_coordinator", None)
        if coordinator is None:
            coordinator = PromptCoordinator()
            self._prompt_coordinator = coordinator
        coordinator.close(prompt)
        self._current_prompt = None
        state = getattr(self, "_runtime_state", None)
        if state is not None:
            state.end_prompt()
        try:
            get_logger().info("current prompt closed via %s", source)
        except Exception:
            pass
        return True

    def _tray_toggle_pause(self):
        if not bool(self.settings.get("tray_start_stop_enabled", True)):
            return False
        if bool(self.settings.get("paused", False)):
            return self._tray_resume()
        return self._tray_pause()

    def _tray_pause(self):
        def _do_pause():
            changed = self._set_paused(True, source="tray_pause")
            self._close_current_prompt(source="tray_pause")
            try:
                if changed:
                    get_logger().info("tray: reminders paused")
            except Exception:
                pass
            poll_ms = int(self.settings.get("pause_poll_interval_seconds", 5)) * 1000
            self._schedule_next(poll_ms)
        return self._call_on_ui_thread(_do_pause)

    def _tray_resume(self):
        def _do_resume():
            self._cancel_snooze()
            changed = self._set_paused(False, source="tray_resume")
            try:
                if changed:
                    get_logger().info("tray: reminders resumed")
            except Exception:
                pass
            self._schedule_next()
        return self._call_on_ui_thread(_do_resume)

    def _tray_prompt_now(self):
        def _do_prompt_now():
            try:
                get_logger().info(
                    "promptnow: clicked | thread=%s tk_thread=%s",
                    threading.get_ident(),
                    getattr(self, "_tk_thread_id", None),
                )
            except Exception:
                pass
            self._cancel_snooze()
            self._set_paused(False, source="tray_prompt")
            try:
                get_logger().info("tray: prompt requested immediately")
            except Exception:
                pass
            self._schedule_next(0)
        return self._call_on_ui_thread(_do_prompt_now)

    def _tray_snooze(self, minutes: int):
        def _perform_snooze(mins: int):
            """Actually apply snooze (pause + schedule unpause)."""
            try:
                mins = int(mins)
            except Exception:
                mins = 5
            ms = max(1, mins) * 60_000
            try:
                get_logger().info("tray: performing snooze mins=%s ms=%s", mins, ms)
            except Exception:
                pass

            # Set paused to True for snooze duration
            until = datetime.now(timezone.utc) + timedelta(milliseconds=ms)
            state = getattr(self, "_runtime_state", None)
            if state is not None:
                if not state.set_snooze_until(until):
                    get_logger().warning("tray: snooze state was not persisted")
                    return
            else:
                self.settings["snooze_until_utc"] = until.isoformat()
                save_settings(self.settings)
            try:
                get_logger().info("tray: snooze for %s minute(s) - paused=True", mins)
            except Exception:
                pass

            self._close_current_prompt(source=f"snooze_{mins}m")

            # Cancel any existing snooze unpause timer
            if self._snooze_unpause_timer_id is not None:
                try:
                    self.root.after_cancel(self._snooze_unpause_timer_id)
                except Exception:
                    pass
                self._snooze_unpause_timer_id = None
                try:
                    get_logger().info("tray: cancelled prior snooze-unpause timer")
                except Exception:
                    pass

            # Schedule timer to un-pause after snooze duration expires
            def _unpause_after_snooze():
                self._snooze_unpause_timer_id = None
                state = getattr(self, "_runtime_state", None)
                if state is not None:
                    state.clear_snooze()
                else:
                    self.settings["snooze_until_utc"] = ""
                    save_settings(self.settings)
                try:
                    get_logger().info("tray: snooze expired, resuming reminders")
                except Exception:
                    pass
                # Resume normal reminder schedule
                self._schedule_next(0)

            if hasattr(self, "_timers"):
                self._timers.schedule("snooze-expiry", ms, _unpause_after_snooze)
                self._snooze_unpause_timer_id = self._timers.callback_id("snooze-expiry")
            else:
                self._snooze_unpause_timer_id = self.root.after(ms, _unpause_after_snooze)
            try:
                get_logger().info("tray: scheduled unpause timer ms=%s", ms)
            except Exception:
                pass

            # Don't schedule next reminder now - it will happen when unpause timer fires

        def _do_snooze():
            try:
                mins = int(minutes)
            except Exception:
                mins = 5
            # If snooze confirmation prompt enabled, show it first
            if bool(self.settings.get("snooze_prompt_enabled", True)) and SnoozePromptDialog is not None:
                try:
                    existing = getattr(self, "_snooze_confirm_dialog", None)
                    if existing is not None and existing.winfo_exists():
                        existing.lift()
                        return True
                except Exception:
                    self._snooze_confirm_dialog = None

                def _on_submit(_payload=None):
                    # Proceed with actual snooze
                    try:
                        if hasattr(self, "_snooze_confirm_dialog") and self._snooze_confirm_dialog is not None:
                            self._snooze_confirm_dialog = None
                    except Exception:
                        pass
                    try:
                        get_logger().info("snooze prompt: user confirmed; applying snooze")
                    except Exception:
                        pass
                    try:
                        get_logger().info("snooze prompt: user confirmed; applying snooze")
                    except Exception:
                        pass
                    _perform_snooze(mins)

                def _on_cancel():
                    try:
                        if hasattr(self, "_snooze_confirm_dialog") and self._snooze_confirm_dialog is not None:
                            self._snooze_confirm_dialog = None
                    except Exception:
                        pass
                    try:
                        get_logger().info("snooze prompt: user cancelled; leaving reminders paused=%s",
                                         bool(self.settings.get("paused", False)))
                    except Exception:
                        pass
                    # Do nothing (user aborted snooze)
                    return

                try:
                    try:
                        get_logger().info("snooze prompt: showing confirmation dialog before snoozing %s min", mins)
                    except Exception:
                        pass
                    dlg = SnoozePromptDialog(
                        self.root,
                        settings=self.settings,
                        on_submit=_on_submit,
                        on_cancel=_on_cancel,
                    )
                    self._snooze_confirm_dialog = dlg
                except Exception:
                    try:
                        get_logger().exception("snooze prompt: dialog creation failed; falling back to direct snooze")
                    except Exception:
                        pass
                    # If dialog creation fails for any reason, fall back to performing snooze directly
                    _perform_snooze(mins)
                return

            else:
                try:
                    get_logger().info("snooze prompt: disabled or missing; snoozing immediately")
                except Exception:
                    pass
            _perform_snooze(mins)
        return self._call_on_ui_thread(_do_snooze)

    def _is_startup_enabled(self) -> bool:
        try:
            return is_startup_installed(APP_NAME)
        except Exception:
            return False

    def _tray_install_startup(self):
        def _do_install():
            try:
                ok = install_startup(APP_NAME)
                if ok:
                    messagebox.showinfo("Startup", "Enabled supervised run on startup.")
                return bool(ok)
            except Exception:
                return False
        return self._call_on_ui_thread(_do_install)

    def _tray_uninstall_startup(self):
        def _do_uninstall():
            try:
                ok = uninstall_startup(APP_NAME)
                if ok:
                    messagebox.showinfo("Startup", "Disabled run on startup.")
                return bool(ok)
            except Exception:
                return False
        return self._call_on_ui_thread(_do_uninstall)

    def _tray_open_data_folder(self):
        try:
            path = get_data_dir()
            if platform.system().lower() == 'windows':
                os.startfile(path)
            else:
                subprocess.Popen(['xdg-open', path])
            return True  # Successfully opened folder
        except Exception:
            return False  # Failed to open folder

    def _tray_open_logs_folder(self):
        try:
            path = os.path.dirname(APP_LOG_PATH)
            if platform.system().lower() == 'windows':
                os.startfile(path)
            else:
                subprocess.Popen(['xdg-open', path])
            return True  # Successfully opened folder
        except Exception:
            return False  # Failed to open folder

    def _tray_exit(self):
        def _do_exit():
            try:
                if not bool(self.settings.get("tray_exit_button_enabled", True)):
                    return
            except Exception:
                pass
            self._quit()
        return self._call_on_ui_thread(_do_exit)

    def _open_settings_from_tray(self):
        def _show_settings():
            try:
                self.settings = load_settings()
            except Exception:
                pass

            def apply_and_refresh(new_settings):
                """
                Apply new settings and regenerate any open prompt.
                """
                self.settings.update(new_settings)
                self._ensure_engine()

                # If there's an open prompt, close it and reopen with new settings
                if self._current_prompt is not None:
                    try:
                        # Check if prompt still exists and is not closed
                        if not getattr(self._current_prompt, "_closed", False) and self._current_prompt.winfo_exists():
                            try:
                                get_logger().info("Settings changed - closing current prompt to regenerate with new settings")
                            except Exception:
                                pass

                            # Mark as closed
                            try:
                                self._current_prompt._closed = True
                            except Exception:
                                pass

                            # Clean up and destroy
                            try:
                                self._current_prompt._cleanup_camera_feed()
                            except Exception:
                                pass

                            try:
                                self._current_prompt._cleanup_all_timers()
                            except Exception:
                                pass

                            try:
                                self._current_prompt._destroy_stage5_overlays()
                            except Exception:
                                pass

                            try:
                                self._current_prompt.destroy()
                            except Exception:
                                pass

                            # Clear reference
                            self._current_prompt = None

                            # Schedule immediate new prompt with updated settings
                            self.root.after(100, lambda: self._schedule_next(0))

                    except Exception as e:
                        try:
                            get_logger().error(f"Failed to regenerate prompt after settings change: {e}")
                        except Exception:
                            pass

            SettingsWindow(self.root, self.settings, on_save=apply_and_refresh)
        return self._call_on_ui_thread(_show_settings)

    def _open_task_dialog_from_tray(self):
        def _show_task_dialog():
            if getattr(self, "taskdb", None) is None:
                messagebox.showerror("Unavailable", "Task database not available.")
                return False
            try:
                TaskEntryDialog(self.root, on_submit=self._on_new_task_from_tray)
                return True
            except Exception:
                return False

        return self._call_on_ui_thread(_show_task_dialog)

    def _on_new_task_from_tray(self, data):
        try:
            title = data.get("title", "").strip()
            why = data.get("why", "").strip()
            cons = data.get("consequences", "").strip()
            due_iso = data.get("due_utc")
            if title:
                self.taskdb.start_task(title=title, due_utc=due_iso, why=why, consequences=cons)
        except Exception:
            pass

    def _quit(self):
        try:
            get_logger().info("quit requested")
        except Exception:
            pass
        lifecycle = getattr(self, "lifecycle", None)
        if lifecycle is not None:
            lifecycle.begin_shutdown(reason="user_exit")
        self._request_supervisor_stop()
        try:
            if getattr(self, "_runtime_state", None) is not None:
                self._runtime_state.request_shutdown()
            if getattr(self, "_timers", None) is not None:
                self._timers.close()
        except Exception:
            get_logger().exception("shutdown coordinator cleanup failed", exc_info=True)
        try:
            if getattr(self, "_tray", None):
                self._tray.stop()
        except Exception:
            pass
        try:
            if getattr(self, "_winwatch", None):
                self._winwatch.close()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
        if lifecycle is not None:
            lifecycle.mark_stopped(reason="user_exit_complete")
        sys.exit(0)

    def _request_supervisor_stop(self):
        stop_file = os.environ.get("FOCUSCHECK_SUPERVISOR_STOP_FILE")
        if not stop_file:
            return
        temp_path = None
        try:
            stop_path = Path(stop_file)
            stop_path.parent.mkdir(parents=True, exist_ok=True)
            request = {
                "protocol_version": 1,
                "request_id": uuid.uuid4().hex,
                "supervisor_id": os.environ.get("FOCUSCHECK_SUPERVISOR_ID", ""),
                "generation": os.environ.get("FOCUSCHECK_CHILD_GENERATION", ""),
                "pid": os.getpid(),
                "process_start_utc": getattr(self, "_process_start_utc", ""),
                "utc": datetime.now(timezone.utc).isoformat(),
                "reason": "user_exit",
            }
            temp_path = stop_path.with_name(f"{stop_path.name}.{os.getpid()}.{request['request_id']}.tmp")
            with temp_path.open("w", encoding="ascii") as handle:
                json.dump(request, handle, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, stop_path)
        except Exception:
            try:
                get_logger().warning("failed writing supervisor stop request", exc_info=True)
            except Exception:
                pass
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink()
                except OSError:
                    pass

    # Heartbeat file for watchdogs
    def _write_heartbeat(self):
        temp_path = None
        try:
            self._heartbeat_sequence = getattr(self, "_heartbeat_sequence", 0) + 1
            process_start_utc = getattr(self, "_process_start_utc", datetime.now(timezone.utc).isoformat())
            manual_paused = bool(self.settings.get("paused", False))
            guard_paused = bool(self.guard.should_pause())
            if manual_paused:
                pause_reason = "manual"
            elif guard_paused:
                pause_reason = "guard"
            else:
                pause_reason = ""
            guard_health = {}
            guard_diagnostics = getattr(self.guard, "diagnostics", None)
            if callable(guard_diagnostics):
                candidate_health = guard_diagnostics()
                if isinstance(candidate_health, dict):
                    guard_health = candidate_health
            payload = {
                "protocol_version": 1,
                "supervisor_id": os.environ.get("FOCUSCHECK_SUPERVISOR_ID", ""),
                "generation": os.environ.get("FOCUSCHECK_CHILD_GENERATION", ""),
                "utc": datetime.now(timezone.utc).isoformat(),
                "pid": os.getpid(),
                "process_start_utc": process_start_utc,
                "sequence": self._heartbeat_sequence,
                "heartbeat_interval_seconds": FILE_HEARTBEAT_INTERVAL_SECONDS / 1000,
                "readiness": getattr(getattr(self, "lifecycle", None), "phase", LifecyclePhase.READY).value,
                "lifecycle": getattr(getattr(self, "lifecycle", None), "snapshot", lambda: {})(),
                "tk_pulse": True,
                "paused": bool(manual_paused or guard_paused),
                "manual_paused": manual_paused,
                "guard_paused": guard_paused,
                "guard_health": guard_health,
                "pause_reason": pause_reason,
                "interval_seconds": int(self.settings.get("interval_seconds", 60)),
            }
            heartbeat_path = Path(HEARTBEAT_PATH)
            heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = heartbeat_path.with_name(
                f"{heartbeat_path.name}.{os.getpid()}.{self._heartbeat_sequence}.tmp"
            )
            with temp_path.open("w", encoding="utf-8") as f:
                json.dump(payload, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, heartbeat_path)
            self._heartbeat_write_failures = 0
        except Exception as exc:
            self._heartbeat_write_failures = getattr(self, "_heartbeat_write_failures", 0) + 1
            now = time.monotonic()
            last_log = getattr(self, "_last_heartbeat_failure_log_mono", 0.0)
            count = self._heartbeat_write_failures
            if count <= 3 or count % 10 == 0 or now - last_log >= 60.0:
                try:
                    get_logger().warning(
                        "heartbeat write failed | consecutive=%d | error_type=%s",
                        count,
                        type(exc).__name__,
                    )
                except Exception:
                    pass
                self._last_heartbeat_failure_log_mono = now
        finally:
            if temp_path is not None:
                try:
                    Path(temp_path).unlink()
                except OSError:
                    pass

    def _start_file_heartbeat(self):
        def hb():
            try:
                self._write_heartbeat()
            finally:
                if not hasattr(self, "_timers"):
                    self.root.after(FILE_HEARTBEAT_INTERVAL_SECONDS, hb)
        hb()
        if hasattr(self, "_timers"):
            self._timers.schedule(
                "file-heartbeat",
                FILE_HEARTBEAT_INTERVAL_SECONDS,
                hb,
                interval_ms=FILE_HEARTBEAT_INTERVAL_SECONDS,
            )

    def _start_snooze_reminder_check(self):
        """Start periodic check for showing snooze reminder."""
        def check():
            try:
                self._maybe_show_snooze_reminder()
            finally:
                # Check every 10 seconds
                if not hasattr(self, "_timers"):
                    self.root.after(10_000, check)
        check()
        if hasattr(self, "_timers"):
            self._timers.schedule("snooze-reminder", 10_000, check, interval_ms=10_000)

    def _maybe_show_snooze_reminder(self):
        """Show snooze reminder dialog if conditions are met."""
        try:
            # Check if snooze reminder is enabled
            if not self.settings.get("snooze_reminder_enabled", True):
                return

            # Check if reminders are currently paused/snoozed
            if not self.settings.get("paused", False):
                # Not snoozed, reset timer for next time
                self._snooze_reminder_next_mono = 0.0
                return

            # Check if a snooze reminder dialog is already open
            if self._snooze_reminder_dialog is not None:
                try:
                    if self._snooze_reminder_dialog.winfo_exists():
                        return  # Already showing
                except Exception:
                    pass
                self._snooze_reminder_dialog = None

            # Check if it's time to show the reminder
            now_mono = time.monotonic()
            if self._snooze_reminder_next_mono == 0.0:
                # First time snoozed, set initial timer
                interval = int(self.settings.get("snooze_reminder_interval_seconds", 300))
                self._snooze_reminder_next_mono = now_mono + interval
                return

            if now_mono < self._snooze_reminder_next_mono:
                return  # Not time yet

            # Show the snooze reminder dialog
            def on_yes():
                """User wants to re-enable reminders."""
                self._snooze_reminder_dialog = None
                self._tray_resume()  # Use existing resume method

            def on_no():
                """User wants to keep reminders paused."""
                self._snooze_reminder_dialog = None
                # Reset timer for next reminder
                interval = int(self.settings.get("snooze_reminder_interval_seconds", 300))
                self._snooze_reminder_next_mono = time.monotonic() + interval

            try:
                self._snooze_reminder_dialog = SnoozeReminderDialog(
                    self.root,
                    self.settings,
                    on_yes=on_yes,
                    on_no=on_no
                )
            except Exception:
                log_exception("Failed to show snooze reminder")
                self._snooze_reminder_dialog = None

        except Exception:
            pass

    def _log_startup_diagnostics(self):
        # Centralized diagnostics to help debug tray issues
        try:
            get_logger().info(
                "startup: python=%s | platform=%s | arch_bits=%s | tk=%s",
                sys.version.split()[0], platform.platform(), 8 * ctypes.sizeof(ctypes.c_void_p), getattr(tk, 'TkVersion', '?')
            )
        except Exception:
            pass
        # Environment details
        try:
            import site
            try:
                paths = site.getsitepackages()
            except Exception:
                paths = sys.path
            get_logger().info("startup: sys.executable=%s", sys.executable)
            get_logger().info("startup: site paths=%s", paths)
        except Exception:
            pass
        # Attempt to import pystray/Pillow explicitly for logging
        try:
            get_logger().info("startup: about to import pystray/Pillow")
        except Exception:
            pass
        # pystray
        try:
            import pystray  # type: ignore
            ver = getattr(pystray, '__version__', '?')
            get_logger().info("startup: pystray import OK | version=%s", ver)
        except Exception as e:
            try:
                get_logger().warning("startup: pystray import FAILED: %s", e)
            except Exception:
                pass
        # Pillow
        try:
            import PIL  # type: ignore
            pver = getattr(PIL, '__version__', '?')
            get_logger().info("startup: Pillow import OK | version=%s", pver)
        except Exception as e:
            try:
                get_logger().warning("startup: Pillow import FAILED: %s", e)
            except Exception:
                pass
        # system_tray module presence
        try:
            from importlib import import_module
            mod = None
            try:
                mod = import_module('focuscheck.system_tray')
            except Exception:
                mod = None
            get_logger().info("startup: system_tray module present=%s", bool(mod))
        except Exception:
            pass

    def run(self):
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            return
        except Exception as exc:
            lifecycle = getattr(self, "lifecycle", None)
            if lifecycle is not None:
                lifecycle.fail(exc, reason="mainloop_exception")
            raise
        finally:
            try:
                if getattr(self, "_winwatch", None):
                    self._winwatch.close()
            except Exception:
                pass
            # Clean up GDI+ resources if on Windows
            if platform.system().lower() == "windows":
                try:
                    from .platform_specific.windows import gdiplus_shutdown
                    gdiplus_shutdown()
                except Exception:
                    pass
            lifecycle = getattr(self, "lifecycle", None)
            if lifecycle is not None and lifecycle.phase == LifecyclePhase.STOPPING:
                lifecycle.mark_stopped(reason="run_cleanup")

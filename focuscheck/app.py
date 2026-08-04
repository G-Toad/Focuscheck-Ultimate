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
from .database import TaskDB, configure_paths as configure_csv_paths, ensure_log_header

# UI components
from .ui.dialogs.task_entry_dialog import TaskEntryDialog
from .ui.dialogs.snooze_reminder_dialog import SnoozeReminderDialog
from .ui.dialogs.gentle_reminder_dialog import GentleReminderDialog
from .ui.guards import PauseGuard
from .runtime.state import RuntimeStateCoordinator
from .runtime.journal import RuntimeTransitionJournal
from .runtime.lifecycle import LifecycleCoordinator, LifecyclePhase
from .runtime.events import StructuredEventLedger
from .runtime.dependencies import AppDependencies
from .utils.clock import SystemClock
from .ui.prompt_coordinator import PromptCoordinator, PromptOutcome
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
    configure_log_path,
    get_logger,
    log_exception,
    get_data_dir,
    get_base_dir,
    migrate_legacy_data,
    migration_has_fatal_failure,
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


def _configure_native_tray_api(user32, kernel32=None):
    """Declare pointer-safe signatures for the native tray menu calls."""
    user32.CreatePopupMenu.argtypes = []
    user32.CreatePopupMenu.restype = wintypes.HMENU
    user32.AppendMenuW.argtypes = [
        wintypes.HMENU,
        wintypes.UINT,
        ctypes.c_size_t,
        wintypes.LPCWSTR,
    ]
    user32.AppendMenuW.restype = wintypes.BOOL
    user32.DestroyMenu.argtypes = [wintypes.HMENU]
    user32.DestroyMenu.restype = wintypes.BOOL
    user32.GetCursorPos.argtypes = [ctypes.c_void_p]
    user32.GetCursorPos.restype = wintypes.BOOL
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL
    user32.TrackPopupMenu.argtypes = [
        wintypes.HMENU,
        wintypes.UINT,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.HWND,
        ctypes.c_void_p,
    ]
    user32.TrackPopupMenu.restype = ctypes.c_int
    if kernel32 is not None:
        kernel32.SetLastError.argtypes = [wintypes.DWORD]
        kernel32.SetLastError.restype = None
        kernel32.GetLastError.argtypes = []
        kernel32.GetLastError.restype = wintypes.DWORD


def resolve_initial_monitoring_state(settings, *, force_start=False):
    """Return (started_bool, reason) for initial monitoring state."""
    if bool(force_start):
        return True, "explicit_force_start"

    try:
        mode = str(os.environ.get("FOCUSCHECK_START_STOP_MODE", "")).strip().lower()
    except Exception:
        mode = ""
    if mode in ("stopped", "stop", "paused", "pause"):
        return False, "env_mode_stopped"

    # Once migrated, durable manual intent is authoritative. The legacy
    # compatibility field remains the fallback for pre-migration callers.
    persisted_paused = bool(
        settings.get("manual_paused", settings.get("paused", False))
    )
    if persisted_paused:
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
    def __init__(self, *, force_start=False, clock=None, activity_provider=None, dependencies=None):
        # Keep construction failures inside the same lifecycle contract as
        # mainloop failures. The initializer may have acquired partial
        # resources before a critical dependency or repository raises.
        self._shutdown_requested = False
        self._clock_override = clock
        self._activity_provider = activity_provider
        self._dependencies = dependencies or AppDependencies()
        self._shutdown_cleanup_complete = False
        try:
            self._initialize(force_start=force_start)
        except BaseException as exc:
            lifecycle = getattr(self, "lifecycle", None)
            if lifecycle is not None:
                lifecycle.fail(exc, reason="startup_exception")
            self._cleanup_runtime(reason="startup_failure", request_supervisor=False)
            raise

    def _initialize(self, *, force_start=False):
        self._force_start = bool(force_start)
        # Freeze one path snapshot for every component composed by this App.
        paths_factory = self._dependencies.app_paths_factory or get_app_paths
        self.paths = paths_factory(filesystem=getattr(self._dependencies, "filesystem", None))
        self._startup_stage("paths_composed")
        clock_factory = self._dependencies.clock_factory or SystemClock
        self._runtime_clock = self._clock_override or clock_factory()
        self._startup_stage("clock_composed")
        csv_paths_configurator = self._dependencies.csv_paths_configurator or configure_csv_paths
        csv_paths_configurator(self.paths)
        log_path_configurator = self._dependencies.log_path_configurator or configure_log_path
        log_path_configurator(self.paths.app_log)
        event_ledger_factory = self._dependencies.event_ledger_factory or StructuredEventLedger
        self._event_ledger = event_ledger_factory(
            self.paths.structured_events,
            clock=self._runtime_clock,
            monotonic_clock=self._runtime_clock.monotonic,
        )
        lifecycle_factory = self._dependencies.lifecycle_factory or LifecycleCoordinator
        self.lifecycle = lifecycle_factory(
            _sink=lambda event: self._event_ledger.append("lifecycle", event)
        )
        self.lifecycle.transition(LifecyclePhase.STARTING, reason="app_construct")
        self._startup_stage("lifecycle_starting")
        root_factory = getattr(self._dependencies, "tk_root_factory", None) or tk.Tk
        self.root = root_factory()
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
        timer_registry_factory = self._dependencies.timer_registry_factory or TimerRegistry
        self._timers = timer_registry_factory(
            self.root,
            event_sink=lambda event: self._event_ledger.append("timer", event),
        )
        self._startup_stage("tk_and_timers_created")
        self._ui_dispatch_sequence = 0
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
        settings_loader = self._dependencies.settings_loader or load_settings
        self.settings = settings_loader()
        self._startup_stage("settings_loaded")
        try:
            migration_factory = self._dependencies.legacy_migration_factory or migrate_legacy_data
            migration_events = migration_factory(self.paths)
            if migration_events:
                if migration_has_fatal_failure(migration_events):
                    raise RuntimeError("legacy data migration did not complete safely")
                get_logger().info("legacy data migration completed | events=%d", len(migration_events))
        except Exception:
            get_logger().exception("legacy data migration failed", exc_info=True)
            raise
        self._startup_stage("migration_completed")
        journal_factory = self._dependencies.runtime_journal_factory or RuntimeTransitionJournal
        self._runtime_journal = journal_factory(
            self.paths.runtime_state,
            clock=self._runtime_clock,
        )

        def record_runtime_event(event):
            journal_ok = self._runtime_journal.append(event)
            self._event_ledger.append("runtime", event)
            return journal_ok

        state_factory = self._dependencies.runtime_state_factory or RuntimeStateCoordinator
        self._runtime_state = state_factory(
            self.settings,
            persist=self._persist_settings_draft,
            clock=self._runtime_clock,
            transition_sink=record_runtime_event,
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
            # Do not enter READY with an unknown durable pause state. The
            # constructor-level lifecycle handler owns partial cleanup.
            raise
        self._startup_stage("initial_monitoring_state_applied")
        self._engine = None
        self._engine_shutdown = False
        # App start times for runtime reporting
        self._start_wall = self._runtime_clock.now_utc()
        self._start_mono = self._runtime_clock.monotonic()
        try:
            get_logger().info("App starting v%s | data_dir=%s", APP_VERSION, get_data_dir())
        except Exception:
            pass
        # Init task DB
        try:
                task_db_factory = self._dependencies.task_db_factory or TaskDB
                task_db_kwargs = {
                    "clock": self._runtime_clock,
                    "event_sink": lambda event: self._event_ledger.append("task", event),
                }
                if callable(self._dependencies.sqlite_connection_factory):
                    task_db_kwargs["connection_factory"] = self._dependencies.sqlite_connection_factory
                self.taskdb = task_db_factory(self.paths.task_db, **task_db_kwargs)
        except Exception:
            self.taskdb = None
            log_exception("TaskDB unavailable; continuing without tasks feature")
        self._startup_stage("repositories_initialized")
        log_header_factory = self._dependencies.log_header_factory or ensure_log_header
        log_header_factory(self.paths.focus_log)
        guard_factory = self._dependencies.guard_factory or PauseGuard
        self.guard = guard_factory(lambda: self.settings)
        self._ensure_engine()
        self._startup_stage("engine_initialized")
        self._scheduled = None
        self._current_prompt = None
        self._prompt_coordinator = self._new_prompt_coordinator()
        self._intervention_active = False
        self._active_intervention_id = None
        self._last_resume_mono = 0.0
        self._next_due_mono = None
        self._next_total_s = None
        self._shutdown_requested = False
        self._shutdown_cleanup_complete = False
        self._heartbeat_sequence = 0
        self._process_start_utc = self._now_utc().isoformat()
        # Snooze reminder tracking
        self._snooze_reminder_next_mono = 0.0
        self._snooze_reminder_dialog = None
        self._gentle_reminder_next_mono = 0.0
        self._gentle_reminder_dialog = None
        self._tray_icon_image = None
        self._tray_icon_path = None
        self._prepare_tray_icon()
        # Heartbeat to catch paused->unpaused edges
        self._start_heartbeat()
        # File heartbeat for watchdogs
        self._start_file_heartbeat()
        # Snooze reminder check loop
        self._start_snooze_reminder_check()
        # Optional non-blocking gentle reminder loop
        self._start_gentle_reminder_check()
        self._startup_stage("services_started")

        # Startup diagnostics (log versions and tray import attempts)
        try:
            self._log_startup_diagnostics()
        except Exception:
            pass

        # Optional cross-platform tray using pystray (preferred when available)
        self._pystray_started = False  # started (requested)
        self._using_pystray = False    # proven alive
        self._native_tray_fallback_active = False
        self._tray = None
        try:
            tray_factory = self._tray_factory()
            if tray_factory is not None:
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
                        self._set_tray_setting(k, v)
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
                    # Fallback must run on the Tk owner thread and stop
                    # pystray before enabling a second tray backend.
                    try:
                        get_logger().error("pystray post-start check failed", exc_info=True)
                    except Exception:
                        pass
                    self._call_on_ui_thread(self._activate_native_tray_fallback)

                self._tray = tray_factory(
                    app=self,
                    name=APP_NAME,
                    tooltip=f"{APP_NAME} running",
                    get_setting=_get,
                    set_setting=_set,
                    open_settings_ui=lambda: self._open_settings_from_tray(),
                    logs_path=str(self.paths.app_log),
                    config_path=str(self.paths.settings),
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
        self._startup_stage("tray_initialized")

        # Windows: listen for power/session/display and enable native tray only if pystray failed.
        self._winwatch = None
        watcher_factory = self._watcher_factory()
        if watcher_factory is not None:
            try:
                # Only enable native tray if pystray didn't start successfully
                enable_native_tray = not self._pystray_started
                self._winwatch = watcher_factory(
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
        self._startup_stage("watcher_initialized")
        # quick first pop to prove it works
        self._schedule_next(2000)
        self.lifecycle.transition(LifecyclePhase.READY, reason="app_ready")
        self._startup_stage("ready")
        # The initial heartbeat is emitted during construction while the
        # lifecycle is still STARTING. Publish READY immediately so a
        # supervisor does not mistake the normal file-heartbeat cadence for a
        # hung startup.
        self._write_heartbeat()

    def _tray_factory(self):
        """Prefer an injected adapter even when optional tray imports are absent."""
        return getattr(getattr(self, "_dependencies", None), "tray_factory", None) or SystemTray

    def _watcher_factory(self):
        """Use explicit watcher injection on any host; default only on Windows."""
        injected = getattr(getattr(self, "_dependencies", None), "watcher_factory", None)
        if injected is not None:
            return injected
        if platform.system().lower() == "windows":
            return WindowsWakeWatcher
        return None

    def _startup_stage(self, name):
        """Expose deterministic startup checkpoints without changing defaults."""
        hook = getattr(getattr(self, "_dependencies", None), "startup_stage_hook", None)
        if callable(hook):
            hook(name)

    def _new_prompt_coordinator(self):
        """Compose a prompt coordinator without bypassing App dependencies."""
        factory = getattr(getattr(self, "_dependencies", None), "prompt_coordinator_factory", None)
        return (factory or PromptCoordinator)()

    def _apply_initial_monitoring_state(self):
        # Reconcile snooze first so an expired effective pause cannot be
        # mistaken for durable manual intent by the startup decision.
        self._reconcile_snooze_state_on_startup()
        desired, reason = resolve_initial_monitoring_state(
            self.settings,
            force_start=self._force_start,
        )
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
            now = self._now_utc()
            if until <= now:
                state = getattr(self, "_runtime_state", None)
                if state is not None:
                    state.clear_snooze()
                else:
                    self.settings["snooze_until_utc"] = ""
                    save_settings(self.settings)
                return
            self.settings["paused"] = True
            save_settings(self.settings)

            remaining_ms = max(1, int((until - now).total_seconds() * 1000))

            if hasattr(self, "_timers"):
                self._timers.schedule("snooze-expiry", remaining_ms, self._expire_snooze)
                self._snooze_unpause_timer_id = self._timers.callback_id("snooze-expiry")
            else:
                self._snooze_unpause_timer_id = self.root.after(remaining_ms, self._expire_snooze)
        except Exception:
            self.settings["snooze_until_utc"] = ""
            save_settings(self.settings)

    def _now_utc(self):
        """Return the coordinator clock value, with a standalone fallback."""
        runtime_clock = getattr(self, "_runtime_clock", None)
        now_utc = getattr(runtime_clock, "now_utc", None)
        if callable(now_utc):
            try:
                return now_utc().astimezone(timezone.utc)
            except (AttributeError, TypeError, ValueError, OverflowError):
                pass
        state = getattr(self, "_runtime_state", None)
        clock = getattr(state, "clock", None)
        now_utc = getattr(clock, "now_utc", None)
        if callable(now_utc):
            try:
                return now_utc().astimezone(timezone.utc)
            except (AttributeError, TypeError, ValueError, OverflowError):
                pass
        return datetime.now(timezone.utc)

    def _record_operational_event(self, category: str, **fields) -> None:
        """Persist bounded lifecycle metadata without affecting application flow."""
        ledger = getattr(self, "_event_ledger", None)
        append = getattr(ledger, "append", None)
        if not callable(append):
            return
        try:
            append(category, fields)
        except Exception:
            # Diagnostics must never turn a lifecycle operation into a failure.
            pass

    def _monotonic(self):
        """Return the App-owned monotonic clock with legacy fallback."""
        runtime_clock = getattr(self, "_runtime_clock", None)
        monotonic = getattr(runtime_clock, "monotonic", None)
        if callable(monotonic):
            try:
                return float(monotonic())
            except (TypeError, ValueError, OverflowError):
                pass
        return time.monotonic()

    def _get_engine_class(self, settings):
        try:
            mode = str(settings.get("monitoring_mode", "v1")).strip().lower()
        except Exception:
            mode = "v1"
        return EngineV2 if mode == "v2" else EngineV1

    def _new_engine(self, cls):
        """Compose the selected monitoring engine through the App boundary."""
        factory = getattr(getattr(self, "_dependencies", None), "engine_factory", None)
        if callable(factory):
            return factory(cls, self)
        if cls is EngineV2:
            activity_provider = getattr(self, "_activity_provider", None)
            if activity_provider is None:
                provider_factory = getattr(getattr(self, "_dependencies", None), "activity_provider_factory", None)
                if callable(provider_factory):
                    activity_provider = provider_factory()
                    self._activity_provider = activity_provider
            return cls(
                self,
                activity_provider=activity_provider,
                clock=getattr(self, "_runtime_clock", None),
            )
        return cls(self)

    def _ensure_engine(self):
        cls = self._get_engine_class(self.settings)
        if self._engine is None or not isinstance(self._engine, cls):
            old_engine = self._engine
            # Construct the replacement before tearing down the current
            # engine. A factory failure must leave the running engine intact.
            replacement = self._new_engine(cls)
            if old_engine is not None:
                # A prompt owns resources that are independent of the
                # monitoring engine. Close it before replacing the engine so
                # a mode switch cannot strand camera, timer, or overlay state.
                if getattr(self, "_current_prompt", None) is not None:
                    self._close_current_prompt(source="engine_switch")
                try:
                    old_engine.shutdown()
                except Exception:
                    pass
            self._engine = replacement
            try:
                get_logger().info("monitoring engine set to %s", getattr(self._engine, "name", cls.__name__))
            except Exception:
                pass
        try:
            self._engine.on_settings_updated(self.settings)
        except Exception:
            pass

    def _shutdown_engine(self):
        """Stop the active monitoring engine exactly once during teardown."""
        if getattr(self, "_engine_shutdown", False):
            return
        self._engine_shutdown = True
        engine = getattr(self, "_engine", None)
        self._engine = None
        if engine is not None:
            try:
                engine.shutdown()
            except Exception:
                get_logger().exception("monitoring engine shutdown failed", exc_info=True)

    def _close_current_prompt_for_shutdown(self):
        """Run prompt-owned cleanup before the Tk root is destroyed."""
        prompt = getattr(self, "_current_prompt", None)
        self._current_prompt = None
        if prompt is None:
            return
        self._mark_prompt_interruption(prompt, PromptOutcome.INTERRUPTED_BY_SHUTDOWN)
        try:
            prompt._closed = True
        except Exception:
            pass
        for method_name in ("_cleanup_camera_feed", "_cleanup_all_timers", "_destroy_stage5_overlays"):
            method = getattr(prompt, method_name, None)
            if callable(method):
                try:
                    method()
                except Exception:
                    get_logger().exception("prompt shutdown cleanup failed: %s", method_name, exc_info=True)
        try:
            prompt.destroy()
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
            self._next_due_mono = self._monotonic() + (delay_ms / 1000.0)
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
                paused_now = self._refresh_guard_state()
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

    def _refresh_guard_state(self) -> bool:
        """Sample guard state once and publish it to the runtime coordinator."""
        try:
            guard = getattr(self, "guard", None)
            guard_paused = bool(guard.should_pause()) if guard is not None else False
        except Exception:
            guard_paused = False
        runtime_state = getattr(self, "_runtime_state", None)
        if runtime_state is not None:
            previous_effective = None
            try:
                previous_effective = bool(runtime_state.is_effectively_paused())
            except Exception:
                pass
            runtime_state.set_guard_reason("system_guard", guard_paused)
            if previous_effective is not None:
                try:
                    current_effective = bool(runtime_state.is_effectively_paused())
                    if current_effective != previous_effective:
                        self._notify_engine_pause_state(source="system_guard")
                except Exception:
                    pass
        return guard_paused

    def _maybe_show_prompt(self):
        # Prompt eligibility uses the validated snapshot owned by App. Settings
        # reloads happen at startup and explicit settings/tray entry points,
        # not on every scheduler tick.
        if getattr(self, "_runtime_state", None) is not None:
            self._runtime_state.refresh_from_settings(self.settings)
            self._refresh_guard_state()
            # Route eligibility through the coordinator so injected clocks and
            # all pause sources remain authoritative at the scheduler boundary.
            if self._runtime_state.is_effectively_paused():
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
                            self._close_current_prompt(source="visibility_recovery")
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
        if self._refresh_guard_state():
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
        self._notify_engine_prompt_state(active=True, source="prompt_started")

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
            self._notify_engine_prompt_state(active=False, source="prompt_failed")
            self._schedule_next()
            return
        if dlg is None:
            if runtime_state is not None:
                runtime_state.end_prompt()
            self._notify_engine_prompt_state(active=False, source="prompt_failed")
            self._schedule_next()
            return
        self._current_prompt = dlg
        prompt_generation = self._prompt_coordinator.open(dlg)
        if prompt_generation is None:
            self._current_prompt = None
            if runtime_state is not None:
                runtime_state.end_prompt()
            self._notify_engine_prompt_state(active=False, source="prompt_rejected")
            self._schedule_next(1500)
            return
        self._record_operational_event("prompt", event="opened", outcome="started")
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

        # Use non-blocking approach instead of wait_window() to avoid GIL issues with pystray
        def _check_dialog_closed():
            try:
                if not self._prompt_coordinator.is_current(dlg, prompt_generation):
                    self._cancel_prompt_observers()
                    return
                # Check if dialog window still exists
                if dlg.winfo_exists():
                    # Dialog still open, check again in 100ms
                    if not hasattr(self, "_timers"):
                        self._prompt_closed_timer_id = self.root.after(100, _check_dialog_closed)
                else:
                    # Dialog closed, schedule next prompt
                    self._on_prompt_done()
            except Exception:
                # Dialog destroyed or error, schedule next prompt
                self._on_prompt_done()

        if hasattr(self, "_timers"):
            self._timers.schedule("prompt-visible", 300, _check_prompt_visible)
            self._timers.schedule("prompt-closed", 100, _check_dialog_closed, interval_ms=100)
        else:
            self._prompt_visibility_timer_id = self.root.after(300, _check_prompt_visible)
            self._prompt_closed_timer_id = self.root.after(100, _check_dialog_closed)




    def _slot_start_info(self):
        now = self._now_utc().astimezone()
        local_minute = now.strftime("%H:%M")
        return {
            "utc_start": now.astimezone(timezone.utc),
            "local_minute": local_minute,
            "mono_start": self._monotonic()
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
            # Do not leave a prompt or camera capture alive while the session
            # is locked or the workstation is entering sleep.
            try:
                self._close_current_prompt(source=f"system_{reason}")
            except Exception:
                try:
                    get_logger().exception("failed to close prompt for system pause", exc_info=True)
                except Exception:
                    pass
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
        now = self._monotonic()
        if now - self._last_resume_mono > 2.0:  # debounce
            self._schedule_next(0)
        self._last_resume_mono = now
        try:
            get_logger().info("system resume")
        except Exception:
            pass

    def _handle_system_shutdown(self, stage: str):
        if stage == "query_end_session":
            try:
                get_logger().info("system shutdown query received; preparing without committing exit")
            except Exception:
                pass
            self._windows_shutdown_query = True
            return
        self._quit(reason=f"windows_{stage}")

    def _on_prompt_done(self):
        self._cancel_prompt_observers()
        prompt = self._current_prompt
        if prompt is None:
            return
        coordinator = getattr(self, "_prompt_coordinator", None)
        if coordinator is None:
            coordinator = self._new_prompt_coordinator()
            self._prompt_coordinator = coordinator
        coordinator.complete(prompt)
        self._record_operational_event("prompt", event="completed", outcome="completed")
        self._current_prompt = None
        state = getattr(self, "_runtime_state", None)
        if state is not None:
            state.end_prompt()
        self._notify_engine_prompt_state(active=False, source="prompt_completed")
        self._schedule_next()

    def _cancel_prompt_observers(self):
        """Cancel visibility/closed polling owned by the current prompt."""
        timers = getattr(self, "_timers", None)
        if timers is not None:
            timers.cancel("prompt-visible")
            timers.cancel("prompt-closed")
        root = getattr(self, "root", None)
        for attribute in ("_prompt_visibility_timer_id", "_prompt_closed_timer_id"):
            timer_id = getattr(self, attribute, None)
            if timer_id is None or root is None:
                continue
            try:
                root.after_cancel(timer_id)
            except Exception:
                pass
            setattr(self, attribute, None)

    def run_intervention(
        self,
        settings,
        *,
        preselect_hwnd=None,
        preselect_title=None,
        prompt_ref=None,
        hide_prompt=False,
    ) -> bool:
        """Run one intervention under the application-owned lease."""
        state = getattr(self, "_runtime_state", None)
        if state is not None and not state.begin_intervention():
            self._record_operational_event("intervention", event="rejected", outcome="lease_unavailable")
            return False
        self._intervention_active = True
        intervention_id = uuid.uuid4().hex
        self._active_intervention_id = intervention_id
        self._notify_engine_intervention_state(active=True, source="intervention_started")
        hidden = False
        outcome = "failed"
        self._record_operational_event("intervention", event="started", outcome="started")
        try:
            from .ui.dialogs.intervention_wizard import InterventionWizard
            if hide_prompt and prompt_ref is not None:
                try:
                    prompt_ref.withdraw()
                    hidden = True
                except Exception:
                    get_logger().exception("intervention prompt hide failed", exc_info=True)
            wizard_factory = getattr(
                getattr(self, "_dependencies", None),
                "intervention_wizard_factory",
                None,
            )
            wizard = (wizard_factory or InterventionWizard)(self.root, settings)
            completed = bool(wizard.run(
                preselect_hwnd=preselect_hwnd,
                preselect_title=preselect_title,
                prompt_ref=prompt_ref,
                hide_prompt=hide_prompt,
                intervention_id=intervention_id,
            ))
            outcome = "completed" if completed else "cancelled"
            return completed
        except Exception:
            try:
                get_logger().exception("intervention coordinator failed", exc_info=True)
            except Exception:
                pass
            return False
        finally:
            if hidden:
                try:
                    prompt_ref.deiconify()
                    prompt_ref.lift()
                    prompt_ref.focus_force()
                except Exception:
                    get_logger().exception("intervention prompt restore failed", exc_info=True)
            self._intervention_active = False
            self._active_intervention_id = None
            try:
                if state is not None:
                    state.end_intervention()
            finally:
                self._notify_engine_intervention_state(active=False, source="intervention_ended")
                self._record_operational_event("intervention", event="ended", outcome=outcome)

    def _notify_engine_intervention_state(self, *, active: bool, source: str) -> None:
        """Forward intervention lease changes without coupling App to an engine type."""
        engine = getattr(self, "_engine", None)
        handler = getattr(type(engine), "on_intervention_changed", None) if engine is not None else None
        if not callable(handler):
            return
        try:
            handler(engine, bool(active), source=source)
        except Exception:
            try:
                get_logger().exception("monitoring engine intervention notification failed", exc_info=True)
            except Exception:
                pass

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
            timers = getattr(self, "_timers", None)
            if timers is not None:
                if timers.closed:
                    return False
                self._ui_dispatch_sequence = getattr(self, "_ui_dispatch_sequence", 0) + 1
                return bool(timers.schedule(
                    f"ui-dispatch-{self._ui_dispatch_sequence}",
                    0,
                    _wrapped,
                ))
            else:
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
            self._reload_settings_snapshot()
            if msg == WM_LBUTTONUP:
                if bool(self.settings.get("tray_start_stop_enabled", True)):
                    self._tray_toggle_pause()
                else:
                    self._show_tray_menu()
            else:
                self._show_tray_menu()
        except Exception:
            pass

    def _activate_native_tray_fallback(self):
        """Switch tray backends only after the preferred adapter has stopped."""
        if getattr(self, "_native_tray_fallback_active", False):
            return False
        tray = getattr(self, "_tray", None)
        if tray is not None and getattr(self, "_pystray_started", False):
            try:
                tray.stop()
            except Exception:
                get_logger().exception("fallback: failed stopping pystray; native tray not enabled", exc_info=True)
                return False
        self._pystray_started = False
        self._using_pystray = False
        watcher = getattr(self, "_winwatch", None)
        if platform.system().lower() != "windows" or watcher is None or not hasattr(watcher, "_tray_add"):
            return False
        try:
            watcher._tray_add("Focus Check")
            self._native_tray_fallback_active = True
            self._record_operational_event("tray", event="backend", outcome="native_fallback")
            get_logger().info("fallback: enabled native tray after pystray failure")
            return True
        except Exception:
            get_logger().exception("failed to enable native tray fallback", exc_info=True)
            return False

    def _show_tray_menu(self):
        try:
            self._reload_settings_snapshot()
            paused = self._manual_pause_intent()
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
                kernel32 = ctypes.windll.kernel32
                _configure_native_tray_api(user32, kernel32)
                TrackPopupMenu = user32.TrackPopupMenu

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
                CMD_EXPORT = 1011
                CMD_INVENTORY = 1012
                CMD_CLEAR_LOGS = 1013
                CMD_CLEAR_DATA = 1014
                CMD_RETAIN_LOGS = 1015
                CMD_DIAGNOSTIC = 1016
                CMD_EXIT = 1017
                CMD_STATUS = 1018

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
                        _append(CMD_EXPORT, "Export Data", action=self._tray_export_data)
                        _append(CMD_INVENTORY, "Data Inventory", action=self._tray_show_data_inventory)
                        _append(CMD_CLEAR_LOGS, "Clear Logs", action=self._tray_clear_logs)
                        _append(CMD_CLEAR_DATA, "Clear Personal Data", action=self._tray_clear_data)
                        _append(CMD_RETAIN_LOGS, "Clean Old Logs", action=self._tray_retain_logs)
                        _append(CMD_DIAGNOSTIC, "Create Diagnostic Bundle", action=self._tray_diagnostic_bundle)
                        _append(CMD_STATUS, "FocusCheck Status", action=self._tray_show_status)
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
                                kernel32.SetLastError(0)
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
                            try:
                                err = int(kernel32.GetLastError())
                            except Exception:
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
            menu.add_command(label="Export Data", command=self._tray_export_data)
            menu.add_command(label="Data Inventory", command=self._tray_show_data_inventory)
            menu.add_command(label="Clear Logs", command=self._tray_clear_logs)
            menu.add_command(label="Clear Personal Data", command=self._tray_clear_data)
            menu.add_command(label="Clean Old Logs", command=self._tray_retain_logs)
            menu.add_command(label="Create Diagnostic Bundle", command=self._tray_diagnostic_bundle)
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
                fallback_user32 = ctypes.windll.user32
                _configure_native_tray_api(fallback_user32)
                fallback_user32.GetCursorPos(ctypes.byref(pt))
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
        self._notify_engine_pause_state(source=source)
        try:
            get_logger().info("paused=%s via %s", value, source)
            if value:
                get_logger().info("monitoring: stopped by %s", source)
            else:
                get_logger().info("monitoring: started by %s", source)
        except Exception:
            pass
        return True

    def _notify_engine_pause_state(self, *, source: str) -> None:
        """Forward effective-pause changes without coupling App to an engine type."""
        engine = getattr(self, "_engine", None)
        handler = getattr(type(engine), "on_pause_changed", None) if engine is not None else None
        if not callable(handler):
            return
        runtime_state = getattr(self, "_runtime_state", None)
        try:
            paused = bool(runtime_state.is_effectively_paused()) if runtime_state is not None else bool(
                getattr(self, "settings", {}).get("paused", False)
            )
            handler(engine, paused, source=source)
        except Exception:
            try:
                get_logger().exception("monitoring engine pause notification failed", exc_info=True)
            except Exception:
                pass

    def _expire_snooze(self):
        """Clear snooze through the coordinator without changing manual pause."""
        self._snooze_unpause_timer_id = None
        state = getattr(self, "_runtime_state", None)
        if state is not None:
            state.clear_snooze()
        else:
            self.settings["snooze_until_utc"] = ""
            save_settings(self.settings)
        self._notify_engine_pause_state(source="snooze_expired")
        try:
            get_logger().info("snooze expired, resuming eligible reminders")
        except Exception:
            pass
        self._schedule_next(0)

    def _cancel_snooze_timer(self):
        """Cancel the named snooze timer through its owning registry."""
        timers = getattr(self, "_timers", None)
        if timers is not None:
            timers.cancel("snooze-expiry")
        elif self._snooze_unpause_timer_id is not None:
            try:
                self.root.after_cancel(self._snooze_unpause_timer_id)
            except Exception:
                pass
        self._snooze_unpause_timer_id = None

    def _cancel_snooze(self):
        self._cancel_snooze_timer()
        if str(self.settings.get("snooze_until_utc", "") or "").strip():
            state = getattr(self, "_runtime_state", None)
            if state is not None:
                changed = state.clear_snooze()
                if changed:
                    self._notify_engine_pause_state(source="snooze_cancelled")
            else:
                self.settings["snooze_until_utc"] = ""
                try:
                    save_settings(self.settings)
                    self._notify_engine_pause_state(source="snooze_cancelled")
                except Exception:
                    pass

    def _close_current_prompt(self, source="unknown"):
        self._cancel_prompt_observers()
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
            self._mark_prompt_interruption(prompt, self._prompt_interruption_outcome(source))
        except Exception:
            pass
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
            coordinator = self._new_prompt_coordinator()
            self._prompt_coordinator = coordinator
        coordinator.close(prompt, outcome=self._prompt_interruption_outcome(source))
        self._record_operational_event("prompt", event="closed", outcome=f"interrupted_{source}")
        self._current_prompt = None
        state = getattr(self, "_runtime_state", None)
        if state is not None:
            state.end_prompt()
        self._notify_engine_prompt_state(active=False, source=f"prompt_interrupted_{source}")
        try:
            get_logger().info("current prompt closed via %s", source)
        except Exception:
            pass
        return True

    def _notify_engine_prompt_state(self, *, active: bool, source: str) -> None:
        """Forward prompt ownership without coupling App to an engine type."""
        engine = getattr(self, "_engine", None)
        handler = getattr(type(engine), "on_prompt_changed", None) if engine is not None else None
        if not callable(handler):
            return
        try:
            handler(engine, bool(active), source=source)
        except Exception:
            try:
                get_logger().exception("monitoring engine prompt notification failed", exc_info=True)
            except Exception:
                pass

    @staticmethod
    def _mark_prompt_interruption(prompt, outcome):
        setter = getattr(prompt, "set_interruption_outcome", None)
        if callable(setter):
            setter(outcome)

    @staticmethod
    def _prompt_interruption_outcome(source):
        """Normalize lifecycle sources into the shared prompt outcome contract."""
        source = str(source or "").lower()
        if "shutdown" in source or source.startswith("windows_"):
            return PromptOutcome.INTERRUPTED_BY_SHUTDOWN
        if "setting" in source:
            return PromptOutcome.INTERRUPTED_BY_SETTINGS
        if "pause" in source or "snooze" in source:
            return PromptOutcome.INTERRUPTED_BY_PAUSE
        return PromptOutcome.CANCELLED

    def _tray_toggle_pause(self):
        if not bool(self.settings.get("tray_start_stop_enabled", True)):
            return False
        if self._manual_pause_intent():
            return self._tray_resume()
        return self._tray_pause()

    def _manual_pause_intent(self) -> bool:
        """Return durable user pause intent, not snooze or guard pause state."""
        runtime_state = getattr(self, "_runtime_state", None)
        if runtime_state is not None:
            try:
                return bool(runtime_state.snapshot.manual_paused)
            except Exception:
                pass
        settings = getattr(self, "settings", {}) or {}
        return bool(settings.get("manual_paused", settings.get("paused", False)))

    def _set_tray_setting(self, key: str, value) -> bool:
        """Persist tray fallback writes through App-owned state/repository APIs."""
        key = str(key)

        def _apply():
            if key == "paused":
                return self._set_paused(bool(value), source="tray_fallback")
            if key == "snooze_until_utc":
                state = getattr(self, "_runtime_state", None)
                if state is not None:
                    changed = state.set_snooze_until(value)
                    if changed:
                        self._notify_engine_pause_state(source="tray_snooze_setting")
                    return changed
            self.settings[key] = value
            result = self._persist_settings_draft(self.settings)
            durable = getattr(result, "durable_write", result)
            if durable:
                committed = getattr(result, "committed_settings", None)
                if isinstance(committed, dict):
                    self.settings.update(committed)
            return bool(durable)

        return bool(self._call_on_ui_thread(_apply))

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
            until = self._now_utc() + timedelta(milliseconds=ms)
            state = getattr(self, "_runtime_state", None)
            if state is not None:
                if not state.set_snooze_until(until):
                    get_logger().warning("tray: snooze state was not persisted")
                    return
            else:
                self.settings["snooze_until_utc"] = until.isoformat()
                save_settings(self.settings)
            self._notify_engine_pause_state(source=f"snooze_{mins}m")
            try:
                get_logger().info("tray: snooze for %s minute(s) - paused=True", mins)
            except Exception:
                pass

            self._close_current_prompt(source=f"snooze_{mins}m")

            # Cancel any existing snooze timer, including a registry-owned timer
            # whose legacy callback ID is not exposed by the caller.
            had_timer = self._snooze_unpause_timer_id is not None
            self._cancel_snooze_timer()
            if had_timer:
                try:
                    get_logger().info("tray: cancelled prior snooze-unpause timer")
                except Exception:
                    pass

            # Schedule timer to un-pause after snooze duration expires
            if hasattr(self, "_timers"):
                self._timers.schedule("snooze-expiry", ms, self._expire_snooze)
                self._snooze_unpause_timer_id = self._timers.callback_id("snooze-expiry")
            else:
                self._snooze_unpause_timer_id = self.root.after(ms, self._expire_snooze)
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
                    prompt_factory = getattr(
                        getattr(self, "_dependencies", None),
                        "snooze_prompt_factory",
                        None,
                    )
                    dlg = (prompt_factory or SnoozePromptDialog)(
                        self.root,
                        settings=self.settings,
                        on_submit=_on_submit,
                        on_cancel=_on_cancel,
                        monotonic_clock=self._monotonic,
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

    def _data_root(self) -> Path:
        """Return the App composition root, with a lifecycle-test fallback."""
        paths = getattr(self, "paths", None)
        if paths is not None:
            return Path(paths.root)
        return Path(get_data_dir())

    def _diagnostic_status_snapshot(self) -> dict:
        """Return only health metadata suitable for display to the user."""
        guard_status = "unknown"
        try:
            health = self.guard.diagnostics()
            if isinstance(health, dict):
                guard_status = "healthy" if bool(health.get("healthy", True)) else "degraded"
        except Exception:
            guard_status = "unavailable"
        try:
            lifecycle = getattr(getattr(self, "lifecycle", None), "phase", None)
            lifecycle = getattr(lifecycle, "value", lifecycle) or "unknown"
        except Exception:
            lifecycle = "unknown"
        try:
            from .doctor import get_anomalies
            anomaly_count = len(get_anomalies())
        except Exception:
            anomaly_count = 0
        try:
            from .settings.schema import get_settings_schema
            schema_key_count = len(get_settings_schema())
        except Exception:
            schema_key_count = "unknown"
        if bool(getattr(self, "_using_pystray", False)):
            tray_backend = "pystray"
        elif bool(getattr(self, "_native_tray_fallback_active", False)):
            tray_backend = "native fallback"
        else:
            tray_backend = "unavailable"
        prompt = getattr(self, "_current_prompt", None)
        camera = getattr(prompt, "_camera_capability", None)
        if not isinstance(camera, dict):
            camera = {"state": "inactive"}
        else:
            camera = {"state": str(camera.get("state", "unknown"))}
        runtime_state = getattr(self, "_runtime_state", None)
        effective_paused = bool(getattr(self, "settings", {}).get("paused", False))
        snooze_active = False
        guard_reasons = []
        runtime_revision = None
        pause_reason = None
        transition_sink_failures = 0
        if runtime_state is not None:
            try:
                view_factory = getattr(type(runtime_state), "snapshot_view", None)
                view = runtime_state.snapshot_view() if callable(view_factory) else None
                if view is not None:
                    effective_paused = bool(view.effective_pause)
                    snooze_active = bool(view.snooze_active)
                    guard_reasons = sorted(view.guard_reasons)
                    runtime_revision = view.revision
                    pause_reason = view.effective_pause_reason
                    transition_sink_failures = int(getattr(view, "transition_sink_failures", 0) or 0)
                else:
                    effective_paused = bool(runtime_state.is_effectively_paused())
                    snapshot = runtime_state.snapshot
                    snooze_active = bool(snapshot.snooze_active(runtime_state.clock.now_utc()))
                    guard_reasons = sorted(str(reason) for reason in snapshot.guard_reasons)
            except Exception:
                pass
        supervisor_id = str(os.environ.get("FOCUSCHECK_SUPERVISOR_ID", "") or "").strip()
        supervisor_generation = str(os.environ.get("FOCUSCHECK_CHILD_GENERATION", "") or "").strip()
        heartbeat_age_seconds = None
        heartbeat_path = getattr(getattr(self, "paths", None), "heartbeat", None)
        if heartbeat_path:
            try:
                heartbeat_age_seconds = round(max(0.0, time.time() - Path(heartbeat_path).stat().st_mtime), 1)
            except (OSError, ValueError, TypeError):
                heartbeat_age_seconds = None
        watcher = getattr(self, "_winwatch", None)
        watcher_state = "registered" if watcher is not None else "unavailable"
        if bool(getattr(watcher, "closed", False)):
            watcher_state = "closed"
        return {
            "application": APP_NAME,
            "version": APP_VERSION,
            "lifecycle": lifecycle,
            "monitoring": "running" if getattr(self, "_engine", None) is not None and not getattr(self, "_engine_shutdown", False) else "stopped",
            "paused": effective_paused,
            "effective_paused": effective_paused,
            "snooze_active": snooze_active,
            "pause_reason": pause_reason,
            "runtime_revision": runtime_revision,
            "transition_sink_failures": transition_sink_failures,
            "guard_reasons": guard_reasons,
            "prompt_active": getattr(self, "_current_prompt", None) is not None,
            "intervention_active": bool(getattr(self, "_intervention_active", False)),
            "intervention_id": getattr(self, "_active_intervention_id", None),
            "camera": camera,
            "guard_status": guard_status,
            "tray_backend": tray_backend,
            "settings_schema_keys": schema_key_count,
            "doctor_anomalies": anomaly_count,
            "pid": os.getpid(),
            "supervisor": "supervised" if supervisor_id else "direct",
            "supervisor_generation": supervisor_generation[:96] or "none",
            "heartbeat_age_seconds": heartbeat_age_seconds,
            "windows_watcher": watcher_state,
            "task_db": "available" if getattr(self, "taskdb", None) is not None else "unavailable",
            "activity_provider": "configured" if getattr(self, "_activity_provider", None) is not None else "unavailable",
            "data_root": str(self._data_root()),
        }

    def _lifecycle_readiness(self) -> str:
        """Return heartbeat-safe lifecycle text for injected adapters."""
        lifecycle = getattr(self, "lifecycle", None)
        phase = getattr(lifecycle, "phase", None)
        value = getattr(phase, "value", phase)
        return str(value or LifecyclePhase.READY.value)

    def _lifecycle_snapshot(self) -> dict:
        """Return optional lifecycle metadata without trusting adapter shape."""
        snapshot = getattr(getattr(self, "lifecycle", None), "snapshot", None)
        try:
            value = snapshot() if callable(snapshot) else snapshot
        except Exception:
            return {}
        return dict(value) if isinstance(value, dict) else {}

    def _tray_show_status(self):
        """Show a small privacy-safe health window on the Tk owner thread."""
        def _show():
            existing = getattr(self, "_diagnostic_status_window", None)
            try:
                if existing is not None and existing.winfo_exists():
                    existing.lift()
                    existing.focus_force()
                    existing._refresh()
                    return True
            except Exception:
                pass
            from .utils.diagnostics import format_status_snapshot
            window_factory = getattr(
                getattr(self, "_dependencies", None),
                "status_window_factory",
                None,
            )
            window = (window_factory or tk.Toplevel)(self.root)
            window.title("FocusCheck Status")
            window.geometry("560x430")
            window.minsize(480, 320)
            window.transient(self.root)
            ttk_label = tk.Label(
                window,
                text="Operational health only. User responses, task text, URLs, and camera data are not shown.",
                anchor="w",
                justify="left",
                wraplength=520,
            )
            ttk_label.pack(fill="x", padx=12, pady=(12, 6))
            text = tk.Text(window, height=16, width=70, state="disabled", wrap="word")
            text.pack(fill="both", expand=True, padx=12, pady=6)
            buttons = tk.Frame(window)
            buttons.pack(fill="x", padx=12, pady=(0, 12))

            def refresh():
                rendered = format_status_snapshot(self._diagnostic_status_snapshot())
                text.configure(state="normal")
                text.delete("1.0", tk.END)
                text.insert("1.0", rendered)
                text.configure(state="disabled")

            def close():
                self._diagnostic_status_window = None
                window.destroy()

            tk.Button(buttons, text="Refresh", command=refresh).pack(side="left")
            tk.Button(buttons, text="Close", command=close).pack(side="right")
            window.protocol("WM_DELETE_WINDOW", close)
            window._refresh = refresh
            self._diagnostic_status_window = window
            refresh()
            window.focus_force()
            return True

        return self._call_on_ui_thread(_show)

    def _close_diagnostic_status_window(self):
        """Close the optional status window during application shutdown."""
        window = getattr(self, "_diagnostic_status_window", None)
        self._diagnostic_status_window = None
        if window is None:
            return
        try:
            window.destroy()
        except Exception:
            pass

    def _tray_open_data_folder(self):
        try:
            path = str(self._data_root())
            if platform.system().lower() == 'windows':
                os.startfile(path)
            else:
                subprocess.Popen(['xdg-open', path])
            return True  # Successfully opened folder
        except Exception:
            return False  # Failed to open folder

    def _tray_open_logs_folder(self):
        try:
            paths = getattr(self, "paths", None)
            log_path = Path(paths.app_log) if paths is not None else Path(APP_LOG_PATH)
            path = str(log_path.parent)
            if platform.system().lower() == 'windows':
                os.startfile(path)
            else:
                subprocess.Popen(['xdg-open', path])
            return True  # Successfully opened folder
        except Exception:
            return False  # Failed to open folder

    def _tray_export_data(self):
        """Export privacy-safe data from a tray callback on the Tk thread."""
        def _do_export():
            from tkinter import filedialog
            from .utils.data_export import export_data

            try:
                data_dir = self._data_root()
                export_dir = data_dir / "exports"
                export_dir.mkdir(parents=True, exist_ok=True)
                output = filedialog.asksaveasfilename(
                    title="Export FocusCheck data",
                    initialdir=str(export_dir),
                    initialfile="focuscheck-export.zip",
                    defaultextension=".zip",
                    filetypes=[("FocusCheck export", "*.zip"), ("All files", "*.*")],
                )
                if not output:
                    return False

                categories = ("logs", "metadata")
                include_sensitive = messagebox.askyesno(
                    "Sensitive data",
                    "Include settings and task data in this export?\n\n"
                    "These files may contain personal productivity information.",
                )
                if include_sensitive:
                    categories += ("settings", "tasks")

                manifest = export_data(data_dir, output, categories=categories)
                messagebox.showinfo(
                    "Export complete",
                    f"Exported {len(manifest['files'])} files to:\n{output}",
                )
                return True
            except Exception as exc:
                try:
                    get_logger().exception("Data export failed", exc_info=True)
                except Exception:
                    pass
                messagebox.showerror("Export failed", str(exc))
                return False

        return self._call_on_ui_thread(_do_export)

    def _tray_show_data_inventory(self):
        """Show a metadata-only inventory without exposing file contents."""
        def _show_inventory():
            from .utils.data_export import inventory_data

            try:
                report = inventory_data(self._data_root())
                totals = {}
                for item in report["files"]:
                    category = item["category"]
                    totals[category] = totals.get(category, 0) + 1
                lines = [f"Data root: {report['root']}", ""]
                if not totals:
                    lines.append("No known FocusCheck data files were found.")
                else:
                    lines.append("Known files by category:")
                    lines.extend(f"- {category}: {count}" for category, count in sorted(totals.items()))
                messagebox.showinfo("FocusCheck data inventory", "\n".join(lines))
                return True
            except Exception as exc:
                messagebox.showerror("Data inventory failed", str(exc))
                return False

        return self._call_on_ui_thread(_show_inventory)

    def _tray_clear_logs(self):
        """Clear only known log files after an explicit user confirmation."""
        def _clear_logs():
            from .utils.data_export import clear_data

            if not messagebox.askyesno(
                "Clear logs",
                "Delete FocusCheck log and response files, including rotated copies?",
            ):
                return False
            try:
                report = clear_data(self._data_root(), categories=("logs",), confirmed=True)
                deleted = sum(1 for item in report["files"] if item.get("deleted"))
                if report.get("audit_written") is False:
                    messagebox.showwarning(
                        "Logs cleared with warning",
                        f"Deleted {deleted} log files, but the audit record was not durable.",
                    )
                else:
                    messagebox.showinfo("Logs cleared", f"Deleted {deleted} log files.")
                return True
            except Exception as exc:
                messagebox.showerror("Clear logs failed", str(exc))
                return False

        return self._call_on_ui_thread(_clear_logs)

    def _tray_clear_data(self):
        """Clear settings, tasks, and camera files, leaving operational logs intact."""
        def _clear_personal_data():
            from .utils.data_export import clear_data

            if not messagebox.askyesno(
                "Clear personal data",
                "Delete settings, task history, and captured camera files?\n\n"
                "This cannot be undone and the app should be restarted afterward.",
            ):
                return False
            try:
                report = clear_data(
                    self._data_root(),
                    categories=("settings", "tasks", "camera"),
                    confirmed=True,
                )
                deleted = sum(1 for item in report["files"] if item.get("deleted"))
                if report.get("audit_written") is False:
                    messagebox.showwarning(
                        "Personal data cleared with warning",
                        f"Deleted {deleted} personal data files, but the audit record was not durable. "
                        "Restart FocusCheck to reload defaults.",
                    )
                else:
                    messagebox.showinfo(
                        "Personal data cleared",
                        f"Deleted {deleted} personal data files. Restart FocusCheck to reload defaults.",
                    )
                return True
            except Exception as exc:
                messagebox.showerror("Clear personal data failed", str(exc))
                return False

        return self._call_on_ui_thread(_clear_personal_data)

    def _tray_retain_logs(self):
        """Apply an explicitly selected retention period to old log files."""
        def _retain_logs():
            from tkinter import simpledialog
            from .utils.data_retention import apply_retention

            days = simpledialog.askinteger(
                "Clean old logs",
                "Delete log files older than how many days?",
                initialvalue=90,
                minvalue=1,
                maxvalue=3650,
            )
            if days is None:
                return False
            try:
                result = apply_retention(self._data_root(), max_age_days=days, apply=True)
                deleted = sum(1 for item in result if item.get("deleted"))
                audit_failures = sum(1 for item in result if item.get("audit_written") is False)
                if audit_failures:
                    messagebox.showwarning(
                        "Log cleanup completed with warning",
                        f"Deleted {deleted} old log files, but {audit_failures} audit record(s) were not durable.",
                    )
                else:
                    messagebox.showinfo("Log cleanup complete", f"Deleted {deleted} old log files.")
                return True
            except Exception as exc:
                messagebox.showerror("Log cleanup failed", str(exc))
                return False

        return self._call_on_ui_thread(_retain_logs)

    def _tray_diagnostic_bundle(self):
        """Preview and create a sanitized bundle from operational data only."""
        def _create_bundle():
            from tkinter import filedialog
            from .utils.diagnostics import create_bundle, preview_bundle

            try:
                data_dir = self._data_root()
                preview = preview_bundle(data_dir)
                files = preview["files"]
                summary = "\n".join(
                    f"- {item['path']} ({item['size']} bytes)" for item in files
                ) or "- No operational files found"
                if not messagebox.askyesno(
                    "Diagnostic bundle preview",
                    "Only operational logs and metadata will be included.\n"
                    "Settings, tasks, camera files, and exports are excluded.\n\n"
                    f"Files:\n{summary}\n\nCreate the bundle?",
                ):
                    return False
                export_dir = data_dir / "exports"
                export_dir.mkdir(parents=True, exist_ok=True)
                output = filedialog.asksaveasfilename(
                    title="Save diagnostic bundle",
                    initialdir=str(export_dir),
                    initialfile="focuscheck-diagnostic.zip",
                    defaultextension=".zip",
                    filetypes=[("Diagnostic bundle", "*.zip"), ("All files", "*.*")],
                )
                if not output:
                    return False
                create_bundle(data_dir, output)
                messagebox.showinfo("Diagnostic bundle", f"Created sanitized bundle:\n{output}")
                return True
            except Exception as exc:
                messagebox.showerror("Diagnostic bundle failed", str(exc))
                return False

        return self._call_on_ui_thread(_create_bundle)

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
            self._reload_settings_snapshot()

            def apply_and_refresh(new_settings):
                """
                Apply new settings and regenerate any open prompt.
                """
                self.settings.update(new_settings)
                self._ensure_engine()

                # Reuse the coordinator-owned close path so prompt leases,
                # timers, and engine polling are released consistently.
                if self._current_prompt is not None:
                    try:
                        self._close_current_prompt(source="settings")
                        if self._current_prompt is None:
                            self._schedule_prompt_regeneration()
                    except Exception as e:
                        try:
                            get_logger().error(f"Failed to regenerate prompt after settings change: {e}")
                        except Exception:
                            pass

            settings_factory = getattr(
                getattr(self, "_dependencies", None),
                "settings_window_factory",
                None,
            )
            (settings_factory or SettingsWindow)(
                self.root,
                self.settings,
                on_save=apply_and_refresh,
                persist_settings=self._persist_settings_draft,
            )
        return self._call_on_ui_thread(_show_settings)

    def _reload_settings_snapshot(self) -> bool:
        """Reload settings through the composition root and update runtime truth."""
        try:
            loader = getattr(getattr(self, "_dependencies", None), "settings_loader", None)
            loaded = (loader or load_settings)()
            if not isinstance(loaded, dict):
                return False
            self.settings = loaded
            state = getattr(self, "_runtime_state", None)
            if state is not None:
                state.refresh_from_settings(loaded)
            # Tray reloads can change the monitoring mode or V2 website flags.
            # Reconfigure an already-running engine without creating one during
            # startup-only reads.
            if getattr(self, "_engine", None) is not None:
                self._ensure_engine()
            return True
        except Exception:
            try:
                get_logger().exception("failed to reload settings snapshot", exc_info=True)
            except Exception:
                pass
            return False

    def _schedule_prompt_regeneration(self):
        """Schedule post-settings prompt regeneration through the App timer owner."""
        callback = lambda: self._schedule_next(0)
        timers = getattr(self, "_timers", None)
        if timers is not None:
            if timers.closed:
                return False
            timers.schedule("settings-prompt-regenerate", 100, callback)
            return True
        try:
            self.root.after(100, callback)
            return True
        except Exception:
            return False

    def schedule_once(self, name: str, delay_ms: int, callback) -> bool:
        """Schedule an App-owned one-shot callback through the named registry."""
        timers = getattr(self, "_timers", None)
        if timers is None or timers.closed:
            return False
        try:
            return bool(timers.schedule(str(name), int(delay_ms), callback))
        except Exception:
            return False

    def _persist_settings_draft(self, draft):
        """Persist a settings-window draft through the App composition root."""
        settings_saver = getattr(getattr(self, "_dependencies", None), "settings_saver", None)
        result = (settings_saver or save_settings)(draft)
        committed = getattr(result, "committed_settings", None)
        if getattr(result, "durable_write", bool(result)) and isinstance(committed, dict):
            self.settings.update(committed)
            state = getattr(self, "_runtime_state", None)
            if state is not None:
                state.refresh_from_settings(committed)
        return result

    def _open_task_dialog_from_tray(self):
        def _show_task_dialog():
            if getattr(self, "taskdb", None) is None:
                messagebox.showerror("Unavailable", "Task database not available.")
                return False
            try:
                dialog_factory = getattr(
                    getattr(self, "_dependencies", None),
                    "task_entry_dialog_factory",
                    None,
                )
                (dialog_factory or TaskEntryDialog)(self.root, on_submit=self._on_new_task_from_tray)
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

    def _quit(self, *, reason: str = "user_exit"):
        if getattr(self, "_shutdown_requested", False):
            return
        self._shutdown_requested = True
        try:
            get_logger().info("quit requested | reason=%s", reason)
        except Exception:
            pass
        self._cleanup_runtime(reason=reason, request_supervisor=True)
        sys.exit(0)

    def _cleanup_runtime(self, *, reason: str, request_supervisor: bool) -> None:
        """Run the reverse-order runtime cleanup contract exactly once."""
        if getattr(self, "_shutdown_cleanup_complete", False):
            return
        self._shutdown_cleanup_complete = True
        self._record_operational_event("shutdown", event="started", outcome=reason)
        lifecycle = getattr(self, "lifecycle", None)
        if lifecycle is not None:
            try:
                phase = getattr(lifecycle, "phase", None)
                begin_shutdown = getattr(lifecycle, "begin_shutdown", None)
                if phase not in (LifecyclePhase.STOPPING, LifecyclePhase.STOPPED) and callable(begin_shutdown):
                    begin_shutdown(reason=reason)
            except Exception:
                get_logger().exception("shutdown lifecycle transition failed", exc_info=True)
        # Direct launches do not have a supervisor to notify. Only enter the
        # stop-request path when the supervised composition injected its marker
        # file; otherwise a normal direct exit must not emit a false warning.
        if request_supervisor and os.environ.get("FOCUSCHECK_SUPERVISOR_STOP_FILE"):
            try:
                if self._request_supervisor_stop(reason=reason) is False:
                    get_logger().warning("supervisor stop request durability is not confirmed")
            except Exception:
                try:
                    get_logger().exception("failed requesting supervisor stop", exc_info=True)
                except Exception:
                    pass
        try:
            if getattr(self, "_runtime_state", None) is not None:
                self._runtime_state.request_shutdown()
            self._shutdown_stage("runtime_rejected")
        except Exception:
            get_logger().exception("runtime state shutdown failed", exc_info=True)
        for name, callback in (
            ("prompt", self._close_current_prompt_for_shutdown),
            ("snooze_confirmation", self._close_snooze_confirmation),
            ("snooze_reminder", self._close_snooze_reminder),
            ("gentle_reminder", self._close_gentle_reminder),
            ("diagnostic_status", self._close_diagnostic_status_window),
            ("engine", self._shutdown_engine),
        ):
            try:
                callback()
                self._shutdown_stage(f"{name}_closed")
            except Exception:
                get_logger().exception("shutdown cleanup failed: %s", name, exc_info=True)
        timers = getattr(self, "_timers", None)
        if timers is not None:
            try:
                timers.close()
                self._shutdown_stage("timers_closed")
            except Exception:
                get_logger().exception("shutdown cleanup failed: timers", exc_info=True)
        try:
            if getattr(self, "_tray", None):
                self._tray.stop()
            self._shutdown_stage("tray_stopped")
        except Exception:
            get_logger().exception("shutdown cleanup failed: tray", exc_info=True)
        try:
            if getattr(self, "_winwatch", None):
                self._winwatch.close()
            self._shutdown_stage("watcher_closed")
        except Exception:
            get_logger().exception("shutdown cleanup failed: watcher", exc_info=True)
        try:
            self.root.destroy()
            self._shutdown_stage("tk_destroyed")
        except Exception:
            get_logger().exception("shutdown cleanup failed: root", exc_info=True)
        if lifecycle is not None:
            try:
                if getattr(lifecycle, "phase", None) == LifecyclePhase.STOPPING:
                    mark_stopped = getattr(lifecycle, "mark_stopped", None)
                    if callable(mark_stopped):
                        mark_stopped(reason=f"{reason}_complete")
            except Exception:
                get_logger().exception("shutdown lifecycle completion failed", exc_info=True)

    def _shutdown_stage(self, name):
        """Expose deterministic shutdown checkpoints without changing defaults."""
        hook = getattr(getattr(self, "_dependencies", None), "shutdown_stage_hook", None)
        if callable(hook):
            hook(name)

    def _request_supervisor_stop(self, *, reason: str = "user_exit") -> bool:
        stop_file = os.environ.get("FOCUSCHECK_SUPERVISOR_STOP_FILE")
        if not stop_file:
            return False
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
                "utc": self._now_utc().isoformat(),
                "reason": str(reason)[:80],
            }
            temp_path = stop_path.with_name(f"{stop_path.name}.{os.getpid()}.{request['request_id']}.tmp")
            with temp_path.open("w", encoding="ascii") as handle:
                json.dump(request, handle, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, stop_path)
            return True
        except Exception:
            try:
                get_logger().warning("failed writing supervisor stop request", exc_info=True)
            except Exception:
                pass
            return False
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
            process_start_utc = getattr(self, "_process_start_utc", None) or self._now_utc().isoformat()
            runtime_state = getattr(self, "_runtime_state", None)
            transition_sink_failures = 0
            if runtime_state is not None:
                view_factory = getattr(type(runtime_state), "snapshot_view", None)
                view = runtime_state.snapshot_view() if callable(view_factory) else None
                if view is not None:
                    manual_paused = bool(view.manual_paused)
                    snooze_active = bool(view.snooze_active)
                    guard_reasons = set(view.guard_reasons)
                    guard_paused = bool(guard_reasons)
                    effective_paused = bool(view.effective_pause)
                    runtime_revision = view.revision
                    pause_reason = view.effective_pause_reason
                    transition_sink_failures = int(getattr(view, "transition_sink_failures", 0) or 0)
                else:
                    snapshot = runtime_state.snapshot
                    manual_paused = bool(snapshot.manual_paused)
                    snooze_active = bool(snapshot.snooze_active(runtime_state.clock.now_utc()))
                    guard_reasons = set(snapshot.guard_reasons)
                    guard_paused = bool(guard_reasons)
                    effective_paused = bool(runtime_state.is_effectively_paused())
                    revision = getattr(snapshot, "revision", None)
                    runtime_revision = revision if isinstance(revision, (int, float, str)) else None
                    pause_reason = None
            else:
                manual_paused = bool(self.settings.get("paused", False))
                snooze_active = False
                guard_paused = bool(self.guard.should_pause())
                guard_reasons = {"system_guard"} if guard_paused else set()
                effective_paused = bool(manual_paused or guard_paused)
                runtime_revision = None
                pause_reason = None
                transition_sink_failures = 0
            if manual_paused:
                pause_reason = "manual"
            elif snooze_active:
                pause_reason = "snooze"
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
                "utc": self._now_utc().isoformat(),
                "pid": os.getpid(),
                "process_start_utc": process_start_utc,
                "sequence": self._heartbeat_sequence,
                "heartbeat_interval_seconds": FILE_HEARTBEAT_INTERVAL_SECONDS / 1000,
                "readiness": self._lifecycle_readiness(),
                "lifecycle": self._lifecycle_snapshot(),
                "tk_pulse": True,
                "paused": effective_paused,
                "effective_paused": effective_paused,
                "manual_paused": manual_paused,
                "snooze_active": snooze_active,
                "guard_paused": guard_paused,
                "guard_reasons": sorted(guard_reasons),
                "guard_health": guard_health,
                "pause_reason": pause_reason,
                "runtime_revision": runtime_revision,
                "transition_sink_failures": transition_sink_failures,
                "interval_seconds": int(self.settings.get("interval_seconds", 60)),
            }
            paths = getattr(self, "paths", None)
            heartbeat_path = Path(getattr(paths, "heartbeat", HEARTBEAT_PATH))
            heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
            heartbeat_writer = getattr(getattr(self, "_dependencies", None), "heartbeat_writer", None)
            if callable(heartbeat_writer):
                heartbeat_writer(heartbeat_path, payload)
            else:
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
            now = self._monotonic()
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

    def _close_snooze_confirmation(self):
        """Close an open tray snooze confirmation without applying snooze."""
        dialog = getattr(self, "_snooze_confirm_dialog", None)
        self._snooze_confirm_dialog = None
        if dialog is None:
            return
        try:
            close = getattr(dialog, "close", None)
            if callable(close):
                close()
            else:
                dialog.destroy()
        except Exception:
            try:
                dialog.destroy()
            except Exception:
                pass

    def _close_snooze_reminder(self):
        """Close the reminder without treating shutdown as a user choice."""
        dialog = getattr(self, "_snooze_reminder_dialog", None)
        self._snooze_reminder_dialog = None
        if dialog is None:
            return
        try:
            close = getattr(dialog, "close", None)
            if callable(close):
                close()
            else:
                dialog.destroy()
        except Exception:
            try:
                dialog.destroy()
            except Exception:
                pass

    def _maybe_show_snooze_reminder(self):
        """Show snooze reminder dialog if conditions are met."""
        try:
            # Check if snooze reminder is enabled
            if not self.settings.get("snooze_reminder_enabled", True):
                return

            # A manual pause is distinct from a snooze. Only an active,
            # persisted snooze may trigger a re-enable reminder.
            snooze_until_raw = str(self.settings.get("snooze_until_utc", "") or "").strip()
            if not snooze_until_raw:
                self._snooze_reminder_next_mono = 0.0
                return
            try:
                snooze_until = datetime.fromisoformat(snooze_until_raw)
                if snooze_until.tzinfo is None:
                    snooze_until = snooze_until.replace(tzinfo=timezone.utc)
                else:
                    snooze_until = snooze_until.astimezone(timezone.utc)
                if snooze_until <= self._now_utc():
                    self._snooze_reminder_next_mono = 0.0
                    return
            except (TypeError, ValueError, OverflowError):
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
            now_mono = self._monotonic()
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
                self._snooze_reminder_next_mono = self._monotonic() + interval

            try:
                reminder_factory = getattr(
                    getattr(self, "_dependencies", None),
                    "snooze_reminder_dialog_factory",
                    None,
                )
                self._snooze_reminder_dialog = (reminder_factory or SnoozeReminderDialog)(
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

    def _start_gentle_reminder_check(self):
        """Start the optional non-blocking gentle reminder scheduler."""
        def check():
            try:
                self._maybe_show_gentle_reminder()
            finally:
                if not hasattr(self, "_timers"):
                    self.root.after(10_000, check)

        check()
        if hasattr(self, "_timers"):
            self._timers.schedule("gentle-reminder", 10_000, check, interval_ms=10_000)

    def _close_gentle_reminder(self):
        dialog = getattr(self, "_gentle_reminder_dialog", None)
        self._gentle_reminder_dialog = None
        if dialog is None:
            return
        try:
            dialog._on_dismiss()
        except Exception:
            try:
                dialog.destroy()
            except Exception:
                pass

    def _maybe_show_gentle_reminder(self):
        """Show a draggable reminder at the configured interval when enabled."""
        try:
            if not self.settings.get("gentle_reminder_enabled", False):
                self._gentle_reminder_next_mono = 0.0
                self._close_gentle_reminder()
                return
            runtime_state = getattr(self, "_runtime_state", None)
            if runtime_state is not None:
                try:
                    effectively_paused = bool(runtime_state.is_effectively_paused())
                except Exception:
                    effectively_paused = bool(self.settings.get("paused", False))
            else:
                # Standalone fixtures and legacy consumers may not compose the
                # runtime coordinator; retain their compatibility behavior.
                effectively_paused = bool(self.settings.get("paused", False))
            if effectively_paused or self._current_prompt is not None:
                return
            dialog = self._gentle_reminder_dialog
            if dialog is not None:
                try:
                    if dialog.winfo_exists():
                        return
                except Exception:
                    self._gentle_reminder_dialog = None

            now_mono = self._monotonic()
            if self._gentle_reminder_next_mono == 0.0:
                interval_minutes = max(1, int(self.settings.get("gentle_reminder_interval", 15)))
                self._gentle_reminder_next_mono = now_mono + interval_minutes * 60
                return
            if now_mono < self._gentle_reminder_next_mono:
                return

            def on_dismiss():
                self._gentle_reminder_dialog = None
                interval_minutes = max(1, int(self.settings.get("gentle_reminder_interval", 15)))
                self._gentle_reminder_next_mono = self._monotonic() + interval_minutes * 60

            reminder_factory = getattr(
                getattr(self, "_dependencies", None),
                "gentle_reminder_dialog_factory",
                None,
            )
            self._gentle_reminder_dialog = (reminder_factory or GentleReminderDialog)(
                self.root, self.settings, on_dismiss=on_dismiss
            )
        except Exception:
            log_exception("Failed to show gentle reminder")
            self._gentle_reminder_dialog = None

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
            # A fatal mainloop exception must still release every owned
            # resource, but must not be reported as an intentional user exit.
            self._cleanup_runtime(reason="run_cleanup", request_supervisor=False)
            # Clean up GDI+ resources if on Windows
            if platform.system().lower() == "windows":
                try:
                    from .platform_specific.windows import gdiplus_shutdown
                    gdiplus_shutdown()
                except Exception:
                    pass

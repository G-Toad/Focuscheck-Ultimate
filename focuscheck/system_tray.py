"""
SystemTray: optional, non-breaking system tray integration using pystray.

Drop-in usage (minimal):

    from system_tray import SystemTray

    app = ...  # your app object (optional)
    tray = SystemTray(app=app, name="YourApp", tooltip="YourApp running")
    tray.start()

Pass custom accessors to wire into your existing settings/UI:

    tray = SystemTray(
        app=app,
        get_setting=lambda k, d=None: settings.get(k, d),
        set_setting=lambda k, v: (settings.__setitem__(k, v), save_settings(settings)),
        open_settings_ui=lambda: show_settings(),
        logs_path=APP_LOG_PATH,  # optional
        config_path=SETTINGS_PATH # optional
    )
    tray.start()

If pystray/Pillow are not installed, the module logs a warning and continues
without a tray. No hard dependency is introduced.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import platform
import subprocess
import sys
import threading
from enum import Enum
from typing import Any, Callable, Optional

# Route to the app's logger if available so messages land in the app log file
logger = logging.getLogger("focuscheck")

try:  # Optional dependency
    import pystray  # type: ignore
except Exception:  # pragma: no cover - optional
    pystray = None  # type: ignore

try:  # Optional dependency
    from PIL import Image, ImageDraw, ImageFont  # type: ignore
except Exception:  # pragma: no cover - optional
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore
    ImageFont = None  # type: ignore


from .settings import gates


class TrayState(str, Enum):
    """Explicit lifecycle state for the optional tray backend."""

    STOPPED = "stopped"
    STARTING = "starting"
    READY = "ready"
    FAILED = "failed"
    STOPPING = "stopping"


class SystemTray:
    """Optional, non-blocking system tray icon with a small menu.

    - Prefers provided accessors; otherwise makes a best-effort to detect
      settings/config/logs from the `app` object or common globals.
    - If pystray/Pillow are not available, skips tray gracefully.
    - Runs detached so it won't block app loops.
    """

    def __init__(
        self,
        *,
        app: Any = None,
        name: str = "App",
        tooltip: Optional[str] = None,
        get_setting: Optional[Callable[[str, Any], Any]] = None,
        set_setting: Optional[Callable[[str, Any], None]] = None,
        open_settings_ui: Optional[Callable[[], None]] = None,
        logs_path: Optional[str] = None,
        config_path: Optional[str] = None,
        icon_image: Optional[Any] = None,
        on_failure: Optional[Callable[[], None]] = None,
        on_alive: Optional[Callable[[], None]] = None,
    ) -> None:
        logger.info("=" * 80)
        logger.info("SystemTray.__init__() STARTING - Initializing system tray")
        logger.info("  Parameters:")
        logger.info("    - app: %s", app)
        logger.info("    - name: %s", name)
        logger.info("    - tooltip: %s", tooltip)
        logger.info("    - get_setting: %s", "provided" if get_setting else "None")
        logger.info("    - set_setting: %s", "provided" if set_setting else "None")
        logger.info("    - open_settings_ui: %s", "provided" if open_settings_ui else "None")
        logger.info("    - logs_path: %s", logs_path)
        logger.info("    - config_path: %s", config_path)
        logger.info("    - icon_image: %s", "provided" if icon_image else "None")
        logger.info("    - on_failure: %s", "provided" if on_failure else "None")
        logger.info("    - on_alive: %s", "provided" if on_alive else "None")

        logger.info("  Setting instance variables...")
        self.app = app
        self.name = name
        self.tooltip = tooltip or name
        logger.info("    - self.tooltip set to: %s", self.tooltip)

        self._external_get = get_setting
        self._external_set = set_setting
        self._external_open_settings = open_settings_ui
        self._logs_path = logs_path
        self._config_path = config_path
        self._icon_image = icon_image

        logger.info("  Initializing internal state variables...")
        self._icon: Optional["pystray.Icon"] = None
        self._thread: Optional[threading.Thread] = None
        self._post_start_timer: Optional[threading.Timer] = None
        self._running = False
        self._state = TrayState.STOPPED
        self._on_failure = on_failure
        self._on_alive = on_alive
        logger.info("    - _running: False")
        logger.info("    - _icon: None")
        logger.info("    - _thread: None")

        # Best-effort defaults (no hard dependency on app internals)
        logger.info("  Calling _detect_defaults()...")
        self._detect_defaults()
        logger.info("SystemTray.__init__() COMPLETED")
        logger.info("=" * 80)

    # ------------- Public API -------------
    @property
    def state(self) -> TrayState:
        return self._state

    def start(self) -> bool:
        """Start the tray icon in a detached way. Returns True if started."""
        logger.info("=" * 80)
        logger.info("SystemTray.start() CALLED - Starting system tray icon")
        logger.info("  Current state:")
        logger.info("    - self._running: %s", self._running)
        logger.info("    - self.name: %s", self.name)
        logger.info("    - self.tooltip: %s", self.tooltip)

        if self._state is TrayState.READY or self._running:
            logger.info("  Tray is already running, returning True")
            logger.info("SystemTray.start() COMPLETED - Already running")
            logger.info("=" * 80)
            return True
        if self._state is TrayState.STARTING:
            return False
        self._state = TrayState.STARTING

        logger.info("  Checking dependencies...")
        logger.info("    - pystray available: %s", pystray is not None)
        logger.info("    - Image (PIL) available: %s", Image is not None)

        if pystray is None or Image is None:
            logger.warning("SystemTray: pystray/Pillow not available; skipping tray")
            logger.warning("    - pystray: %s", pystray)
            logger.warning("    - Image: %s", Image)
            logger.info("SystemTray.start() FAILED - Missing dependencies")
            self._state = TrayState.FAILED
            logger.info("=" * 80)
            return False

        logger.info("  Creating icon image...")
        try:
            logger.info("    - Attempting to create icon image...")
            image = self._icon_image or self._make_icon_image()
            logger.info("    - Icon image created successfully: %s", image)
        except Exception as e:
            logger.exception("    - ERROR creating icon image: %s", e)
            image = None

        if image is None:
            logger.warning("SystemTray: no icon image available; skipping tray")
            logger.info("SystemTray.start() FAILED - No icon image")
            self._state = TrayState.FAILED
            logger.info("=" * 80)
            return False

        logger.info("  Building menu...")
        try:
            menu = self._build_menu()
            logger.info("    - Menu built successfully: %s", menu)
            logger.info("  Creating pystray.Icon object...")
            self._icon = pystray.Icon(self.name, image, self.tooltip, menu)
        except Exception:
            logger.exception("SystemTray: icon construction failed")
            self._icon = None
            self._state = TrayState.FAILED
            return False
        logger.info("    - Icon object created: %s", self._icon)

        # Prefer run_detached when available; otherwise a daemon thread
        logger.info("  Checking for run_detached method...")
        logger.info("    - hasattr(self._icon, 'run_detached'): %s", hasattr(self._icon, "run_detached"))

        try:
            if hasattr(self._icon, "run_detached"):
                logger.info("  Using run_detached() method...")
                try:
                    logger.info("    - Calling icon.run_detached()...")
                    logger.info("icon.run_detached() called")
                except Exception as e:
                    logger.exception("    - Error logging run_detached call: %s", e)

                self._icon.run_detached()
                logger.info("    - run_detached() completed")
                self._running = True
                self._state = TrayState.READY
                logger.info("    - _running set to True")

                # schedule post-start check
                logger.info("    - Scheduling post-start check...")
                self._schedule_post_start_check()
                logger.info("SystemTray.start() COMPLETED - Using run_detached()")
                logger.info("=" * 80)
                return True
        except Exception as e:
            logger.exception("SystemTray: run_detached failed: %s", e)
            logger.info("  Falling through to background thread method...")

        logger.info("  Creating background thread for tray icon...")

        def _run():
            logger.info("    - Background thread _run() started")
            logger.info("      Thread name: %s", threading.current_thread().name)
            logger.info("      Thread ID: %s", threading.current_thread().ident)
            try:
                logger.info("      Calling self._icon.run()...")
                self._icon.run()
                logger.info("      self._icon.run() completed")
            except Exception as e:
                logger.exception("      SystemTray: icon loop crashed: %s", e)
                logger.info("      Exception type: %s", type(e))
                logger.info("      Exception args: %s", e.args)
                if self._running:
                    self._running = False
                    self._state = TrayState.FAILED
                    if callable(self._on_failure):
                        with contextlib.suppress(Exception):
                            self._on_failure()

        try:
            logger.info("SystemTray: running pystray icon on background thread")
        except Exception:
            pass

        logger.info("    - Creating Thread object...")
        self._thread = threading.Thread(target=_run, name=f"{self.name}-tray", daemon=True)
        logger.info("      Thread created: %s", self._thread)
        logger.info("      Thread name: %s", self._thread.name)
        logger.info("      Thread daemon: %s", self._thread.daemon)

        logger.info("    - Starting thread...")
        try:
            self._thread.start()
        except Exception:
            logger.exception("SystemTray: tray thread failed to start")
            self._thread = None
            self._icon = None
            self._state = TrayState.FAILED
            return False
        logger.info("      Thread started successfully")
        logger.info("      Thread is_alive: %s", self._thread.is_alive())

        self._running = True
        self._state = TrayState.READY
        logger.info("    - _running set to True")

        logger.info("    - Scheduling post-start check...")
        self._schedule_post_start_check()

        logger.info("SystemTray.start() COMPLETED - Using background thread")
        logger.info("=" * 80)
        return True

    def _schedule_post_start_check(self) -> None:
        # Non-blocking post-start smoke test: update tooltip once. If it fails, log and trigger fallback.
        previous = self._post_start_timer
        if previous is not None:
            with contextlib.suppress(Exception):
                previous.cancel()

        timer_holder = {}

        def _check():
            try:
                if not self._running:
                    return
                if self._icon is None:
                    raise RuntimeError("icon object missing in post-start check")
                # Force a small title change to trigger an update
                old = getattr(self._icon, "title", self.tooltip)
                new = (old or self.tooltip or self.name) + " "
                try:
                    self._icon.title = new
                    self._icon.title = old
                except Exception:
                    # Some backends may not expose title; a no-op is fine
                    pass
                try:
                    logger.info("SystemTray: post-start check OK")
                except Exception:
                    pass
                # Notify alive
                if callable(self._on_alive):
                    try:
                        self._on_alive()
                    except Exception:
                        logger.exception("SystemTray: on_alive callback failed")
            except Exception:
                logger.exception("SystemTray: post-start check failed")
                if self._running:
                    self._state = TrayState.FAILED
                if callable(self._on_failure):
                    try:
                        self._on_failure()
                    except Exception:
                        logger.exception("SystemTray: on_failure callback failed")
            finally:
                if self._post_start_timer is timer_holder.get("timer"):
                    self._post_start_timer = None

        t = threading.Timer(0.6, _check)
        t.daemon = True
        timer_holder["timer"] = t
        self._post_start_timer = t
        t.start()

    def stop(self) -> None:
        if (
            self._state is TrayState.STOPPED
            and not self._running
            and self._icon is None
            and self._post_start_timer is None
        ):
            return
        self._state = TrayState.STOPPING
        self._running = False
        timer = self._post_start_timer
        self._post_start_timer = None
        if timer is not None:
            with contextlib.suppress(Exception):
                timer.cancel()
        with contextlib.suppress(Exception):
            if self._icon is not None:
                self._icon.visible = False
                self._icon.stop()
        # Join background thread if present
        th = self._thread
        self._thread = None
        if th is not None and th.is_alive():
            with contextlib.suppress(Exception):
                th.join(timeout=2.0)
        self._icon = None
        self._state = TrayState.STOPPED

    # ------------- Internal helpers -------------
    def _detect_defaults(self) -> None:
        # Detect logs/config paths from common names if not provided
        if self._logs_path is None:
            for attr in ("APP_LOG_PATH", "LOG_PATH", "log_path", "logs_path"):
                self._logs_path = getattr(self.app, attr, None) if self.app is not None else None
                if self._logs_path:
                    break
        if self._config_path is None:
            for attr in ("SETTINGS_PATH", "CONFIG_PATH", "settings_path", "config_path"):
                self._config_path = getattr(self.app, attr, None) if self.app is not None else None
                if self._config_path:
                    break

    def _call_app(self, name: str, *args: Any, **kwargs: Any) -> Any:
        if self.app is None:
            return False
        fn = getattr(self.app, name, None)
        if not callable(fn):
            return False
        try:
            return fn(*args, **kwargs)
        except Exception:
            logger.exception("SystemTray: app.%s failed", name)
            return False

    # Settings accessors (defensive)
    def _get_setting(self, key: str, default: Any = None) -> Any:
        logger.info(">>> _get_setting() CALLED")
        logger.info("    - key: '%s'", key)
        logger.info("    - default: %s", default)
        logger.info("    - Checking external getter...")

        if callable(self._external_get):
            logger.info("      External getter is callable, attempting to use it...")
            try:
                result = self._external_get(key, default)
                logger.info("      External getter SUCCESS - returned: %s", result)
                logger.info("<<< _get_setting() RETURNING (via external): %s", result)
                return result
            except Exception as e:
                logger.exception("      SystemTray: external get_setting failed: %s", e)
                logger.info("      Falling through to other methods...")
        else:
            logger.info("      External getter not available")

        # Try app.settings dict
        logger.info("    - Trying app.settings dict...")
        with contextlib.suppress(Exception):
            s = getattr(self.app, "settings", None)
            logger.info("      app.settings: %s", type(s))
            if isinstance(s, dict):
                logger.info("      app.settings is a dict, checking for key '%s'...", key)
                if key in s:
                    result = s.get(key, default)
                    logger.info("      Found in app.settings: %s", result)
                    logger.info("<<< _get_setting() RETURNING (via app.settings): %s", result)
                    return result
                else:
                    logger.info("      Key '%s' not found in app.settings", key)

        # Try JSON config
        logger.info("    - Trying JSON config file...")
        logger.info("      _config_path: %s", self._config_path)
        logger.info("      File exists: %s", os.path.exists(self._config_path) if self._config_path else False)

        if self._config_path and os.path.exists(self._config_path):
            logger.info("      Attempting to read config file: %s", self._config_path)
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.info("      Config file loaded successfully")
                logger.info("      Config data type: %s", type(data))
                if isinstance(data, dict):
                    logger.info("      Config is a dict, checking for key '%s'...", key)
                    if key in data:
                        result = data.get(key, default)
                        logger.info("      Found in config file: %s", result)
                        logger.info("<<< _get_setting() RETURNING (via config): %s", result)
                        return result
                    else:
                        logger.info("      Key '%s' not found in config", key)
            except Exception as e:
                logger.exception("      Error reading config file: %s", e)

        logger.info("    - No setting found, returning default: %s", default)
        logger.info("<<< _get_setting() RETURNING (default): %s", default)
        return default

    def _set_setting(self, key: str, value: Any) -> None:
        logger.info(">>> _set_setting() CALLED")
        logger.info("    - key: '%s'", key)
        logger.info("    - value: %s (type: %s)", value, type(value))
        logger.info("    - Checking external setter...")

        if callable(self._external_set):
            logger.info("      External setter is callable, attempting to use it...")
            try:
                self._external_set(key, value)
                logger.info("      External setter SUCCESS")
                logger.info("<<< _set_setting() COMPLETED (via external)")
                return
            except Exception as e:
                logger.exception("      SystemTray: external set_setting failed: %s", e)
                logger.info("      Falling through to other methods...")
        else:
            logger.info("      External setter not available")

        # Persistence belongs to the App composition root. The adapter may
        # request a fallback write, but never mutates settings or imports the
        # settings repository itself.
        saved = bool(self._call_app("_set_tray_setting", key, value))
        logger.info("    - App-owned fallback result: %s", saved)
        if not saved:
            logger.error("SystemTray: setting '%s' was not persisted; App command unavailable or failed", key)
            logger.info("<<< _set_setting() FAILED")
            return
        logger.info("<<< _set_setting() COMPLETED")

    # UI hooks
    def _open_settings(self) -> None:
        logger.info("=" * 80)
        logger.info("MENU ACTION: _open_settings() CALLED")
        logger.info("  User clicked 'Settings' in tray menu")

        # Prefer explicit hook
        logger.info("  Checking for external open_settings callback...")
        logger.info("    _external_open_settings: %s", self._external_open_settings)

        if callable(self._external_open_settings):
            logger.info("    External callback is callable, attempting to use it...")
            try:
                logger.info("    Calling external open_settings_ui()...")
                self._external_open_settings()
                logger.info("    External open_settings_ui() SUCCESS")
                logger.info("MENU ACTION: _open_settings() COMPLETED (via external)")
                logger.info("=" * 80)
                return
            except Exception as e:
                logger.exception("    SystemTray: open_settings_ui failed: %s", e)
                logger.info("    Falling through to other methods...")
        else:
            logger.info("    External callback not available")

        # Try common app methods
        logger.info("  Trying common app methods...")
        for name in ("open_settings", "show_settings", "_open_settings_from_tray"):
            logger.info("    Checking method: %s", name)
            fn = getattr(self.app, name, None)
            logger.info("      Found: %s", fn)
            if callable(fn):
                logger.info("      Method is callable, attempting to call it...")
                try:
                    fn()
                    logger.info("      Method %s() SUCCESS", name)
                    logger.info("MENU ACTION: _open_settings() COMPLETED (via %s)", name)
                    logger.info("=" * 80)
                    return
                except Exception as e:
                    logger.exception("      SystemTray: %s() failed: %s", name, e)
                    logger.info("      Continuing to next method...")

        # Open config file if known
        logger.info("  Trying to open config file directly...")
        logger.info("    _config_path: %s", self._config_path)
        logger.info("    File exists: %s", os.path.exists(self._config_path) if self._config_path else False)

        if self._config_path and os.path.exists(self._config_path):
            logger.info("    Opening config file in OS default editor...")
            self._open_path_in_os(self._config_path)
            logger.info("MENU ACTION: _open_settings() COMPLETED (via config file)")
            logger.info("=" * 80)
            return

        # Last resort: small info dialog if a Tk root exists; otherwise no-op
        logger.info("  Last resort: showing info dialog...")
        with contextlib.suppress(Exception):
            import tkinter as tk  # lazy import
            logger.info("    Searching for Tk root...")
            root = getattr(self.app, "root", None) or getattr(tk, "_default_root", None)
            logger.info("      Found root: %s", root)
            if root and callable(getattr(root, "after", None)):
                logger.info("      Scheduling message dialog...")
                def _msg():
                    logger.info("        Showing 'No settings UI available' dialog")
                    try:
                        from tkinter import messagebox
                        messagebox.showinfo(self.name, "No settings UI available.")
                        logger.info("        Dialog shown")
                    except Exception as e:
                        logger.exception("        Dialog failed: %s", e)
                dispatch = getattr(self.app, "_call_on_ui_thread", None)
                if callable(dispatch):
                    dispatch(_msg)
                else:
                    root.after(0, _msg)
                logger.info("MENU ACTION: _open_settings() COMPLETED (via dialog)")
                logger.info("=" * 80)
                return

        logger.info("  No method succeeded")
        logger.info("MENU ACTION: _open_settings() COMPLETED (no action)")
        logger.info("=" * 80)

    # OS helpers
    def _open_path_in_os(self, path: str) -> None:
        try:
            if platform.system().lower() == "windows":
                os.startfile(path)  # type: ignore[attr-defined]
            elif platform.system().lower() == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception:
            logger.exception("SystemTray: failed opening path: %s", path)

    # Menu and actions
    def _is_paused(self) -> bool:
        runtime_state = getattr(self.app, "_runtime_state", None)
        if runtime_state is not None:
            try:
                return bool(runtime_state.snapshot.manual_paused)
            except Exception:
                pass
        # Standalone adapters may not have the coordinator, but migrated
        # settings still carry durable manual intent separately.
        return bool(self._get_setting("manual_paused", self._get_setting("paused", False)))

    def _pause_checked(self, _: Any = None) -> bool:
        return self._is_paused()

    def _start_stop_setting_enabled(self) -> bool:
        return gates.is_start_stop_enabled(self.app.settings)

    def _stop_enabled(self, _: Any = None) -> bool:
        return self._start_stop_setting_enabled() and not self._is_paused()

    def _start_enabled(self, _: Any = None) -> bool:
        return self._start_stop_setting_enabled() and self._is_paused()

    def _settings_enabled(self, _: Any = None) -> bool:
        return gates.is_settings_enabled(self.app.settings)

    def _exit_enabled(self, _: Any = None) -> bool:
        return gates.is_exit_enabled(self.app.settings)

    def _stop_reminders(self, icon: Any, item: Any) -> None:
        logger.info("=" * 80)
        logger.info("MENU ACTION: _stop_reminders() CALLED")
        logger.info("  User clicked 'Stop reminders' in tray menu")
        logger.info("  Parameters:")
        logger.info("    - icon: %s", icon)
        logger.info("    - item: %s", item)

        logger.info("  Checking if start/stop is enabled...")
        enabled = self._start_stop_setting_enabled()
        logger.info("    Start/stop enabled: %s", enabled)

        if not enabled:
            logger.info("  Start/stop is disabled, returning without action")
            logger.info("MENU ACTION: _stop_reminders() ABORTED (disabled)")
            logger.info("=" * 80)
            return

        logger.info("  Attempting to call app._tray_pause()...")
        result = self._call_app('_tray_pause')
        logger.info("    app._tray_pause() returned: %s", result)

        if not result:
            logger.info("    App method not available or failed, handling manually...")
            logger.info("    Checking current pause state...")
            paused = self._is_paused()
            logger.info("      Currently paused: %s", paused)

            if not paused:
                logger.info("      Not paused, setting 'paused' to True...")
                self._set_setting("paused", True)
                logger.info("      Reminders stopped (paused=True)")
            else:
                logger.info("      Already paused, no action needed")
        else:
            logger.info("    App handled pause via _tray_pause()")

        logger.info("MENU ACTION: _stop_reminders() COMPLETED")
        logger.info("=" * 80)

    def _start_reminders(self, icon: Any, item: Any) -> None:
        logger.info("=" * 80)
        logger.info("MENU ACTION: _start_reminders() CALLED")
        logger.info("  User clicked 'Start reminders' in tray menu")
        logger.info("  Parameters:")
        logger.info("    - icon: %s", icon)
        logger.info("    - item: %s", item)

        logger.info("  Checking if start/stop is enabled...")
        enabled = self._start_stop_setting_enabled()
        logger.info("    Start/stop enabled: %s", enabled)

        if not enabled:
            logger.info("  Start/stop is disabled, returning without action")
            logger.info("MENU ACTION: _start_reminders() ABORTED (disabled)")
            logger.info("=" * 80)
            return

        logger.info("  Attempting to call app._tray_resume()...")
        result = self._call_app('_tray_resume')
        logger.info("    app._tray_resume() returned: %s", result)

        if not result:
            logger.info("    App method not available or failed, handling manually...")
            logger.info("    Checking current pause state...")
            paused = self._is_paused()
            logger.info("      Currently paused: %s", paused)

            if paused:
                logger.info("      Is paused, setting 'paused' to False...")
                self._set_setting("paused", False)
                logger.info("      Reminders started (paused=False)")
            else:
                logger.info("      Already running, no action needed")
        else:
            logger.info("    App handled resume via _tray_resume()")

        logger.info("MENU ACTION: _start_reminders() COMPLETED")
        logger.info("=" * 80)

    def _toggle_pause(self, icon: Any, item: Any) -> None:
        logger.info("=" * 80)
        logger.info("MENU ACTION: _toggle_pause() CALLED")
        logger.info("  Parameters:")
        logger.info("    - icon: %s", icon)
        logger.info("    - item: %s", item)

        logger.info("  Checking current pause state...")
        paused = self._is_paused()
        logger.info("    Currently paused: %s", paused)

        if paused:
            logger.info("  Currently paused, calling _start_reminders()...")
            self._start_reminders(icon, item)
        else:
            logger.info("  Currently running, calling _stop_reminders()...")
            self._stop_reminders(icon, item)

        logger.info("MENU ACTION: _toggle_pause() COMPLETED")
        logger.info("=" * 80)

    def _open_logs(self, icon: Any, item: Any) -> None:
        logger.info("=" * 80)
        logger.info("MENU ACTION: _open_logs() CALLED")
        logger.info("  User clicked 'Open logs folder' in tray menu")
        logger.info("  Parameters:")
        logger.info("    - icon: %s", icon)
        logger.info("    - item: %s", item)

        logger.info("  Attempting to call app._tray_open_logs_folder()...")
        result = self._call_app('_tray_open_logs_folder')
        logger.info("    Result: %s", result)

        if result:
            logger.info("  App handled logs folder opening")
            logger.info("MENU ACTION: _open_logs() COMPLETED (via app)")
            logger.info("=" * 80)
            return

        logger.info("  App method not available, handling manually...")
        logger.info("    _logs_path: %s", self._logs_path)
        logger.info("    File exists: %s", os.path.exists(self._logs_path) if self._logs_path else False)

        if self._logs_path and os.path.exists(self._logs_path):
            logger.info("    Logs file exists, opening directory...")
            dir_path = os.path.dirname(self._logs_path)
            logger.info("      Directory path: %s", dir_path)
            self._open_path_in_os(dir_path)
            logger.info("MENU ACTION: _open_logs() COMPLETED (manual)")
        else:
            logger.info("  Logs path not available or doesn't exist")
            logger.info("MENU ACTION: _open_logs() COMPLETED (no action)")

        logger.info("=" * 80)

    def _open_data(self, icon: Any, item: Any) -> None:
        logger.info("=" * 80)
        logger.info("MENU ACTION: _open_data() CALLED")
        logger.info("  User clicked 'Open data folder' in tray menu")
        logger.info("  Parameters:")
        logger.info("    - icon: %s", icon)
        logger.info("    - item: %s", item)

        logger.info("  Attempting to call app._tray_open_data_folder()...")
        result = self._call_app('_tray_open_data_folder')
        logger.info("    Result: %s", result)

        if result:
            logger.info("  App handled data folder opening")
            logger.info("MENU ACTION: _open_data() COMPLETED (via app)")
            logger.info("=" * 80)
            return

        logger.info("  App method not available, handling manually...")
        logger.info("    _config_path: %s", self._config_path)
        logger.info("    File exists: %s", os.path.exists(self._config_path) if self._config_path else False)

        if self._config_path and os.path.exists(self._config_path):
            logger.info("    Config file exists, opening directory...")
            dir_path = os.path.dirname(self._config_path)
            logger.info("      Directory path: %s", dir_path)
            self._open_path_in_os(dir_path)
            logger.info("MENU ACTION: _open_data() COMPLETED (manual)")
        else:
            logger.info("  Config path not available or doesn't exist")
            logger.info("MENU ACTION: _open_data() COMPLETED (no action)")

        logger.info("=" * 80)

    def _export_data(self, icon: Any, item: Any) -> None:
        """Delegate the user-facing export flow to the application UI owner."""
        self._call_app("_tray_export_data")

    def _clear_logs(self, icon: Any, item: Any) -> None:
        self._call_app("_tray_clear_logs")

    def _clear_data(self, icon: Any, item: Any) -> None:
        self._call_app("_tray_clear_data")

    def _retain_logs(self, icon: Any, item: Any) -> None:
        self._call_app("_tray_retain_logs")

    def _diagnostic_bundle(self, icon: Any, item: Any) -> None:
        self._call_app("_tray_diagnostic_bundle")

    def _show_status(self, icon: Any, item: Any) -> None:
        self._call_app("_tray_show_status")

    def _show_data_inventory(self, icon: Any, item: Any) -> None:
        self._call_app("_tray_show_data_inventory")

    def _open_task(self, icon: Any, item: Any) -> None:
        logger.info("=" * 80)
        logger.info("MENU ACTION: _open_task() CALLED")
        logger.info("  User clicked 'Set/Change task' in tray menu")
        logger.info("  Parameters:")
        logger.info("    - icon: %s", icon)
        logger.info("    - item: %s", item)

        logger.info("  Attempting to call app._open_task_dialog_from_tray()...")
        result = self._call_app('_open_task_dialog_from_tray')
        logger.info("    Result: %s", result)

        if not result:
            logger.warning('SystemTray: task dialog unavailable')
            logger.info("MENU ACTION: _open_task() FAILED (unavailable)")
        else:
            logger.info("MENU ACTION: _open_task() COMPLETED")

        logger.info("=" * 80)

    def _prompt_now(self, icon: Any, item: Any) -> None:
        logger.info("=" * 80)
        logger.info("MENU ACTION: _prompt_now() CALLED")
        logger.info("  User clicked 'Prompt now' in tray menu")
        logger.info("  Parameters:")
        logger.info("    - icon: %s", icon)
        logger.info("    - item: %s", item)

        logger.info("  Attempting to call app._tray_prompt_now()...")
        result = self._call_app('_tray_prompt_now')
        logger.info("    Result: %s", result)

        if not result:
            logger.info("  App method not available, trying _schedule_next(0)...")
            result2 = self._call_app('_schedule_next', 0)
            logger.info("    _schedule_next(0) result: %s", result2)
            if result2:
                logger.info("MENU ACTION: _prompt_now() COMPLETED (via _schedule_next)")
            else:
                logger.info("MENU ACTION: _prompt_now() FAILED (no methods available)")
        else:
            logger.info("MENU ACTION: _prompt_now() COMPLETED (via _tray_prompt_now)")

        logger.info("=" * 80)

    def _snooze(self, minutes: int) -> Callable[[Any, Any], None]:
        logger.info("_snooze() CALLED - Creating snooze handler for %d minutes", minutes)

        def _handler(icon: Any, item: Any) -> None:
            logger.info("=" * 80)
            logger.info("MENU ACTION: _snooze(%d) handler CALLED", minutes)
            logger.info("  User clicked 'Snooze %d minutes' in tray menu", minutes)
            logger.info("  Parameters:")
            logger.info("    - icon: %s", icon)
            logger.info("    - item: %s", item)
            logger.info("    - minutes: %d", minutes)

            logger.info("  Attempting to call app._tray_snooze(%d)...", minutes)
            result = self._call_app('_tray_snooze', minutes)
            logger.info("    Result: %s", result)

            if not result:
                logger.warning('SystemTray: snooze %s unavailable', minutes)
                logger.info("MENU ACTION: _snooze(%d) FAILED (unavailable)", minutes)
            else:
                logger.info("MENU ACTION: _snooze(%d) COMPLETED", minutes)

            logger.info("=" * 80)

        logger.info("  Snooze handler created for %d minutes: %s", minutes, _handler)
        return _handler

    def _startup_checked(self, _: Any = None) -> bool:
        result = self._call_app('_is_startup_enabled')
        if isinstance(result, bool):
            return result
        return False

    def _toggle_startup(self, icon: Any, item: Any) -> None:
        logger.info("=" * 80)
        logger.info("MENU ACTION: _toggle_startup() CALLED")
        logger.info("  User clicked 'Run on startup' in tray menu")
        logger.info("  Parameters:")
        logger.info("    - icon: %s", icon)
        logger.info("    - item: %s", item)

        logger.info("  Checking current startup state...")
        currently_enabled = self._startup_checked()
        logger.info("    Startup currently enabled: %s", currently_enabled)

        if currently_enabled:
            logger.info("  Startup is enabled, disabling...")
            logger.info("    Attempting to call app._tray_uninstall_startup()...")
            result = self._call_app('_tray_uninstall_startup')
            logger.info("      Result: %s", result)
            if not result:
                logger.warning('SystemTray: disable startup unavailable')
                logger.info("MENU ACTION: _toggle_startup() FAILED (uninstall unavailable)")
            else:
                logger.info("MENU ACTION: _toggle_startup() COMPLETED (disabled startup)")
        else:
            logger.info("  Startup is disabled, enabling...")
            logger.info("    Attempting to call app._tray_install_startup()...")
            result = self._call_app('_tray_install_startup')
            logger.info("      Result: %s", result)
            if not result:
                logger.warning('SystemTray: enable startup unavailable')
                logger.info("MENU ACTION: _toggle_startup() FAILED (install unavailable)")
            else:
                logger.info("MENU ACTION: _toggle_startup() COMPLETED (enabled startup)")

        logger.info("=" * 80)

    def _on_quit(self, icon: Any, item: Any) -> None:
        logger.info("=" * 80)
        logger.info("MENU ACTION: _on_quit() CALLED")
        logger.info("  User clicked 'Exit' in tray menu")
        logger.info("  Parameters:")
        logger.info("    - icon: %s", icon)
        logger.info("    - item: %s", item)

        logger.info("  Checking if exit is enabled...")
        enabled = self._exit_enabled()
        logger.info("    Exit enabled: %s", enabled)

        if not enabled:
            try:
                logger.info('  Exit is disabled, ignoring request')
                logger.info('SystemTray: exit request ignored because disabled')
                logger.info("MENU ACTION: _on_quit() ABORTED (disabled)")
                logger.info("=" * 80)
            except Exception:
                pass
            return

        logger.info("  Exit allowed, proceeding with shutdown...")

        try:
            # App-specific quit hooks
            logger.info("  Searching for app quit methods...")
            for name in ("_tray_exit", "_quit", "quit", "stop", "shutdown"):
                logger.info("    Checking method: %s", name)
                fn = getattr(self.app, name, None)
                logger.info("      Found: %s", fn)
                if callable(fn):
                    logger.info("      Method is callable, calling it...")
                    try:
                        fn()
                        logger.info("      Method %s() SUCCESS - breaking loop", name)
                        break
                    except Exception as e:
                        logger.exception("      Method %s() FAILED: %s", name, e)
                        logger.info("      Continuing to next method...")
        finally:
            # Ensure tray stops; pystray will exit its loop
            logger.info("  In finally block, cleaning up tray icon...")
            with contextlib.suppress(Exception):
                if self._icon is not None:
                    logger.info("    Icon exists, hiding and stopping...")
                    logger.info("      Setting icon.visible = False")
                    self._icon.visible = False
                    logger.info("      Calling icon.stop()")
                    self._icon.stop()
                    logger.info("      Icon stopped successfully")
                else:
                    logger.info("    Icon is None, nothing to stop")

            # The application lifecycle owner decides process termination. A
            # tray callback must never call sys.exit from the tray thread.
            logger.info("  Tray exit delegation complete; no tray-thread process exit")

    def _build_menu(self) -> "pystray.Menu":
        logger.info("=" * 80)
        logger.info("_build_menu() CALLED - Building tray menu")
        logger.info("  Creating menu items array...")
        items = []

        logger.info("  Adding menu item: 'Stop reminders'")
        logger.info("    - enabled callback: self._stop_enabled")
        items.append(pystray.MenuItem("Stop reminders", self._stop_reminders, enabled=self._stop_enabled))

        logger.info("  Adding menu item: 'Start reminders'")
        logger.info("    - enabled callback: self._start_enabled")
        items.append(pystray.MenuItem("Start reminders", self._start_reminders, enabled=self._start_enabled))

        logger.info("  Adding separator")
        items.append(pystray.Menu.SEPARATOR)

        logger.info("  Adding menu item: 'Prompt now'")
        items.append(pystray.MenuItem("Prompt now", self._prompt_now))

        logger.info("  Adding menu item: 'Snooze 5 minutes'")
        items.append(pystray.MenuItem("Snooze 5 minutes", self._snooze(5)))

        logger.info("  Adding menu item: 'Snooze 15 minutes'")
        items.append(pystray.MenuItem("Snooze 15 minutes", self._snooze(15)))

        logger.info("  Adding separator")
        items.append(pystray.Menu.SEPARATOR)

        logger.info("  Adding menu item: 'Settings'")
        logger.info("    - enabled callback: self._settings_enabled")
        items.append(pystray.MenuItem("Settings", lambda icon, item: self._open_settings(), enabled=self._settings_enabled))

        logger.info("  Adding menu item: 'Set/Change task'")
        items.append(pystray.MenuItem("Set/Change task", self._open_task))

        logger.info("  Adding separator")
        items.append(pystray.Menu.SEPARATOR)

        logger.info("  Checking platform for 'Run on startup' option...")
        platform_name = platform.system().lower()
        logger.info("    Platform: %s", platform_name)
        if platform_name == "windows":
            logger.info("    Windows detected, adding 'Run on startup' menu item")
            logger.info("      - checked callback: self._startup_checked")
            items.append(pystray.MenuItem("Run on startup", self._toggle_startup, checked=self._startup_checked))
        else:
            logger.info("    Not Windows, skipping 'Run on startup' menu item")

        logger.info("  Adding menu item: 'Open data folder'")
        items.append(pystray.MenuItem("Open data folder", self._open_data))

        logger.info("  Adding menu item: 'Open logs folder'")
        items.append(pystray.MenuItem("Open logs folder", self._open_logs))

        logger.info("  Adding menu item: 'Export data'")
        items.append(pystray.MenuItem("Export data", self._export_data))

        logger.info("  Adding menu item: 'Data inventory'")
        items.append(pystray.MenuItem("Data inventory", self._show_data_inventory))

        logger.info("  Adding menu item: 'Clear logs'")
        items.append(pystray.MenuItem("Clear logs", self._clear_logs))

        logger.info("  Adding menu item: 'Clear personal data'")
        items.append(pystray.MenuItem("Clear personal data", self._clear_data))

        logger.info("  Adding menu item: 'Clean old logs'")
        items.append(pystray.MenuItem("Clean old logs", self._retain_logs))

        logger.info("  Adding menu item: 'Create diagnostic bundle'")
        items.append(pystray.MenuItem("Create diagnostic bundle", self._diagnostic_bundle))

        logger.info("  Adding menu item: 'FocusCheck status'")
        items.append(pystray.MenuItem("FocusCheck status", self._show_status))

        logger.info("  Adding separator")
        items.append(pystray.Menu.SEPARATOR)

        logger.info("  Adding menu item: 'Exit'")
        logger.info("    - enabled callback: self._exit_enabled")
        items.append(pystray.MenuItem("Exit", self._on_quit, enabled=self._exit_enabled))

        logger.info("  Total menu items created: %d", len(items))
        logger.info("  Creating pystray.Menu object...")
        menu = pystray.Menu(*items)
        logger.info("  Menu object created: %s", menu)
        logger.info("_build_menu() COMPLETED")
        logger.info("=" * 80)
        return menu

    def _make_icon_image(self) -> Any:
        # Build a tiny in-memory icon using Pillow
        if Image is None or ImageDraw is None:
            return None
        size = 32
        img = Image.new("RGBA", (size, size), (20, 20, 20, 255))  # fully opaque dark background
        draw = ImageDraw.Draw(img)
        # High-contrast center glyph (opaque)
        draw.ellipse((3, 3, size - 4, size - 4), fill=(250, 230, 0, 255), outline=(0, 0, 0, 255), width=2)
        # Simple glyph letter on top
        text = (self.name or "A").strip()[:1].upper()
        # Try to place a letter; fallback to a dot
        try:
            # Rely on default font; on Windows this will pick a reasonable size
            font = ImageFont.load_default()
            w, h = draw.textsize(text, font=font)
            draw.text(((size - w) / 2, (size - h) / 2), text, fill=(0, 0, 0, 255), font=font)
        except Exception:
            draw.ellipse((10, 10, 22, 22), fill=(0, 0, 0, 255))
        return img


__all__ = ["SystemTray"]

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
        self.app = app
        self.name = name
        self.tooltip = tooltip or name
        self._external_get = get_setting
        self._external_set = set_setting
        self._external_open_settings = open_settings_ui
        self._logs_path = logs_path
        self._config_path = config_path
        self._icon_image = icon_image

        self._icon: Optional["pystray.Icon"] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._on_failure = on_failure
        self._on_alive = on_alive

        # Best-effort defaults (no hard dependency on app internals)
        self._detect_defaults()

    # ------------- Public API -------------
    def start(self) -> bool:
        """Start the tray icon in a detached way. Returns True if started."""
        if self._running:
            return True
        if pystray is None or Image is None:
            logger.warning("SystemTray: pystray/Pillow not available; skipping tray")
            return False

        try:
            image = self._icon_image or self._make_icon_image()
        except Exception:
            image = None
        if image is None:
            logger.warning("SystemTray: no icon image available; skipping tray")
            return False

        menu = self._build_menu()
        self._icon = pystray.Icon(self.name, image, self.tooltip, menu)

        # Prefer run_detached when available; otherwise a daemon thread
        try:
            if hasattr(self._icon, "run_detached"):
                try:
                    logger.info("icon.run_detached() called")
                except Exception:
                    pass
                self._icon.run_detached()
                self._running = True
                # schedule post-start check
                self._schedule_post_start_check()
                return True
        except Exception:
            logger.exception("SystemTray: run_detached failed")

        def _run():
            try:
                self._icon.run()
            except Exception:
                logger.exception("SystemTray: icon loop crashed")

        try:
            logger.info("SystemTray: running pystray icon on background thread")
        except Exception:
            pass
        self._thread = threading.Thread(target=_run, name=f"{self.name}-tray", daemon=True)
        self._thread.start()
        self._running = True
        self._schedule_post_start_check()
        return True

    def _schedule_post_start_check(self) -> None:
        # Non-blocking post-start smoke test: update tooltip once. If it fails, log and trigger fallback.
        def _check():
            try:
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
                if callable(self._on_failure):
                    try:
                        self._on_failure()
                    except Exception:
                        logger.exception("SystemTray: on_failure callback failed")
        t = threading.Timer(0.6, _check)
        t.daemon = True
        t.start()

    def stop(self) -> None:
        self._running = False
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
        if callable(self._external_get):
            try:
                return self._external_get(key, default)
            except Exception:
                logger.exception("SystemTray: external get_setting failed")
        # Try app.settings dict
        with contextlib.suppress(Exception):
            s = getattr(self.app, "settings", None)
            if isinstance(s, dict):
                return s.get(key, default)
        # Try JSON config
        if self._config_path and os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data.get(key, default)
            except Exception:
                pass
        return default

    def _set_setting(self, key: str, value: Any) -> None:
        if callable(self._external_set):
            try:
                self._external_set(key, value)
                return
            except Exception:
                logger.exception("SystemTray: external set_setting failed")
        # Try app.settings dict + app.save_settings/app._save_settings or module save_settings
        saved = False
        with contextlib.suppress(Exception):
            s = getattr(self.app, "settings", None)
            if isinstance(s, dict):
                s[key] = value
                for m in (self.app, sys.modules.get(self.app.__class__.__module__)):
                    fn = getattr(m, "save_settings", None)
                    if callable(fn):
                        try:
                            fn(s)
                            saved = True
                            break
                        except Exception:
                            pass
        if not saved and self._config_path:
            try:
                data = {}
                if os.path.exists(self._config_path):
                    with open(self._config_path, "r", encoding="utf-8") as f:
                        data = json.load(f) or {}
                if not isinstance(data, dict):
                    data = {}
                data[key] = value
                os.makedirs(os.path.dirname(self._config_path) or ".", exist_ok=True)
                with open(self._config_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            except Exception:
                logger.exception("SystemTray: failed persisting to config")

    # UI hooks
    def _open_settings(self) -> None:
        # Prefer explicit hook
        if callable(self._external_open_settings):
            try:
                self._external_open_settings()
                return
            except Exception:
                logger.exception("SystemTray: open_settings_ui failed")
        # Try common app methods
        for name in ("open_settings", "show_settings", "_open_settings_from_tray"):
            fn = getattr(self.app, name, None)
            if callable(fn):
                try:
                    fn()
                    return
                except Exception:
                    logger.exception("SystemTray: %s() failed", name)
        # Open config file if known
        if self._config_path and os.path.exists(self._config_path):
            self._open_path_in_os(self._config_path)
            return
        # Last resort: small info dialog if a Tk root exists; otherwise no-op
        with contextlib.suppress(Exception):
            import tkinter as tk  # lazy import
            root = getattr(self.app, "root", None) or getattr(tk, "_default_root", None)
            if root and callable(getattr(root, "after", None)):
                def _msg():
                    try:
                        from tkinter import messagebox
                        messagebox.showinfo(self.name, "No settings UI available.")
                    except Exception:
                        pass
                root.after(0, _msg)

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
        return bool(self._get_setting("paused", False))

    def _pause_checked(self, _: Any = None) -> bool:
        return self._is_paused()

    def _start_stop_setting_enabled(self) -> bool:
        return bool(self._get_setting("tray_start_stop_enabled", True))

    def _stop_enabled(self, _: Any = None) -> bool:
        return self._start_stop_setting_enabled() and not self._is_paused()

    def _start_enabled(self, _: Any = None) -> bool:
        return self._start_stop_setting_enabled() and self._is_paused()

    def _settings_enabled(self, _: Any = None) -> bool:
        return bool(self._get_setting("tray_settings_button_enabled", True))

    def _exit_enabled(self, _: Any = None) -> bool:
        return bool(self._get_setting("tray_exit_button_enabled", True))

    def _stop_reminders(self, icon: Any, item: Any) -> None:
        if not self._start_stop_setting_enabled():
            return
        if not self._call_app('_tray_pause'):
            if not self._is_paused():
                self._set_setting("paused", True)

    def _start_reminders(self, icon: Any, item: Any) -> None:
        if not self._start_stop_setting_enabled():
            return
        if not self._call_app('_tray_resume'):
            if self._is_paused():
                self._set_setting("paused", False)

    def _toggle_pause(self, icon: Any, item: Any) -> None:
        if self._is_paused():
            self._start_reminders(icon, item)
        else:
            self._stop_reminders(icon, item)

    def _open_logs(self, icon: Any, item: Any) -> None:
        if self._call_app('_tray_open_logs_folder'):
            return
        if self._logs_path and os.path.exists(self._logs_path):
            self._open_path_in_os(os.path.dirname(self._logs_path))

    def _open_data(self, icon: Any, item: Any) -> None:
        if self._call_app('_tray_open_data_folder'):
            return
        if self._config_path and os.path.exists(self._config_path):
            self._open_path_in_os(os.path.dirname(self._config_path))

    def _open_task(self, icon: Any, item: Any) -> None:
        if not self._call_app('_open_task_dialog_from_tray'):
            logger.warning('SystemTray: task dialog unavailable')

    def _prompt_now(self, icon: Any, item: Any) -> None:
        if not self._call_app('_tray_prompt_now'):
            self._call_app('_schedule_next', 0)

    def _snooze(self, minutes: int) -> Callable[[Any, Any], None]:
        def _handler(icon: Any, item: Any) -> None:
            if not self._call_app('_tray_snooze', minutes):
                logger.warning('SystemTray: snooze %s unavailable', minutes)
        return _handler

    def _startup_checked(self, _: Any = None) -> bool:
        result = self._call_app('_is_startup_enabled')
        if isinstance(result, bool):
            return result
        return False

    def _toggle_startup(self, icon: Any, item: Any) -> None:
        if self._startup_checked():
            if not self._call_app('_tray_uninstall_startup'):
                logger.warning('SystemTray: disable startup unavailable')
        else:
            if not self._call_app('_tray_install_startup'):
                logger.warning('SystemTray: enable startup unavailable')

    def _on_quit(self, icon: Any, item: Any) -> None:
        if not self._exit_enabled():
            try:
                logger.info('SystemTray: exit request ignored because disabled')
            except Exception:
                pass
            return
        try:
            # App-specific quit hooks
            for name in ("_tray_exit", "_quit", "quit", "stop", "shutdown"):
                fn = getattr(self.app, name, None)
                if callable(fn):
                    try:
                        fn()
                        break
                    except Exception:
                        pass
        finally:
            # Ensure tray stops; pystray will exit its loop
            with contextlib.suppress(Exception):
                if self._icon is not None:
                    self._icon.visible = False
                    self._icon.stop()
            # As a last resort, exit the process
            with contextlib.suppress(Exception):
                sys.exit(0)

    def _build_menu(self) -> "pystray.Menu":
        items = []
        items.append(pystray.MenuItem("Stop reminders", self._stop_reminders, enabled=self._stop_enabled))
        items.append(pystray.MenuItem("Start reminders", self._start_reminders, enabled=self._start_enabled))
        items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem("Prompt now", self._prompt_now))
        items.append(pystray.MenuItem("Snooze 5 minutes", self._snooze(5)))
        items.append(pystray.MenuItem("Snooze 15 minutes", self._snooze(15)))
        items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem("Settings", lambda icon, item: self._open_settings(), enabled=self._settings_enabled))
        items.append(pystray.MenuItem("Set/Change task", self._open_task))
        items.append(pystray.Menu.SEPARATOR)
        if platform.system().lower() == "windows":
            items.append(pystray.MenuItem("Run on startup", self._toggle_startup, checked=self._startup_checked))
        items.append(pystray.MenuItem("Open data folder", self._open_data))
        items.append(pystray.MenuItem("Open logs folder", self._open_logs))
        items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem("Exit", self._on_quit, enabled=self._exit_enabled))
        return pystray.Menu(*items)

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
            # Use textbbox (Pillow 8+) with fallback to textsize (deprecated in Pillow 9.2+)
            try:
                bbox = draw.textbbox((0, 0), text, font=font)
                w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            except AttributeError:
                # Fallback for older Pillow versions
                w, h = draw.textsize(text, font=font)
            draw.text(((size - w) / 2, (size - h) / 2), text, fill=(0, 0, 0, 255), font=font)
        except Exception:
            draw.ellipse((10, 10, 22, 22), fill=(0, 0, 0, 255))
        return img


__all__ = ["SystemTray"]

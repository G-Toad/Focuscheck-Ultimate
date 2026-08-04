"""Canonical per-user startup registration boundary."""

from __future__ import annotations

from typing import Any, Callable


class StartupService:
    """Own startup install, uninstall, and inspection without UI policy."""

    def __init__(
        self,
        _app: Any = None,
        *,
        install: Callable[[str], Any],
        uninstall: Callable[[str], Any],
        is_installed: Callable[[str], Any],
        app_name: str,
    ) -> None:
        self._install = install
        self._uninstall = uninstall
        self._is_installed = is_installed
        self._app_name = str(app_name)

    def is_installed(self) -> bool:
        try:
            return bool(self._is_installed(self._app_name))
        except Exception:
            return False

    def install(self) -> bool:
        try:
            return bool(self._install(self._app_name))
        except Exception:
            return False

    def uninstall(self) -> bool:
        try:
            return bool(self._uninstall(self._app_name))
        except Exception:
            return False


__all__ = ["StartupService"]

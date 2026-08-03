"""Optional composition seams for App-owned external services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class AppDependencies:
    """Factories used by App for services with external side effects.

    ``None`` preserves the production defaults. Tests and disposable harnesses
    can replace one boundary without patching module globals or changing the
    lifecycle contract.
    """

    settings_loader: Callable[[], dict[str, Any]] | None = None
    settings_saver: Callable[[dict[str, Any]], Any] | None = None
    sqlite_connection_factory: Callable[..., Any] | None = None
    task_db_factory: Callable[..., Any] | None = None
    tray_factory: Callable[..., Any] | None = None
    watcher_factory: Callable[..., Any] | None = None
    heartbeat_writer: Callable[[Any, dict[str, Any]], Any] | None = None
    camera_capture_factory: Callable[[int], Any] | None = None
    filesystem: Any | None = None
    startup_stage_hook: Callable[[str], Any] | None = None
    shutdown_stage_hook: Callable[[str], Any] | None = None
    tk_root_factory: Callable[[], Any] | None = None

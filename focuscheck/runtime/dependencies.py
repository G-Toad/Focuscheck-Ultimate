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
    app_paths_factory: Callable[..., Any] | None = None
    csv_paths_configurator: Callable[[Any], Any] | None = None
    log_path_configurator: Callable[[Any], Any] | None = None
    legacy_migration_factory: Callable[[Any], Any] | None = None
    log_header_factory: Callable[[Any], Any] | None = None
    sqlite_connection_factory: Callable[..., Any] | None = None
    task_db_factory: Callable[..., Any] | None = None
    engine_factory: Callable[[type[Any], Any], Any] | None = None
    tray_factory: Callable[..., Any] | None = None
    watcher_factory: Callable[..., Any] | None = None
    heartbeat_writer: Callable[[Any, dict[str, Any]], Any] | None = None
    camera_capture_factory: Callable[[int], Any] | None = None
    clock_factory: Callable[[], Any] | None = None
    event_ledger_factory: Callable[..., Any] | None = None
    lifecycle_factory: Callable[..., Any] | None = None
    timer_registry_factory: Callable[..., Any] | None = None
    runtime_journal_factory: Callable[..., Any] | None = None
    runtime_state_factory: Callable[..., Any] | None = None
    guard_factory: Callable[[Callable[[], Any]], Any] | None = None
    prompt_coordinator_factory: Callable[[], Any] | None = None
    filesystem: Any | None = None
    startup_stage_hook: Callable[[str], Any] | None = None
    shutdown_stage_hook: Callable[[str], Any] | None = None
    tk_root_factory: Callable[[], Any] | None = None

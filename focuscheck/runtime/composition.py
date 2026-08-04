"""Composition of App-owned non-Tk foundation services."""

from __future__ import annotations

from dataclasses import dataclass
import threading
import tkinter as tk
import sys
from typing import Any, Callable

from ..database import configure_paths as configure_csv_paths
from ..database import TaskDB, ensure_log_header
from ..settings import load_settings
from ..runtime.events import StructuredEventLedger
from ..runtime.data_controls import DataControlService
from ..runtime.health import HealthSnapshotService
from ..runtime.intervention import InterventionOrchestrator
from ..runtime.scheduler import PromptScheduler
from ..runtime.startup import StartupService
from ..runtime.journal import RuntimeTransitionJournal
from ..runtime.lifecycle import LifecycleCoordinator, LifecyclePhase
from ..runtime.state import RuntimeStateCoordinator
from ..utils.clock import SystemClock
from ..utils.logging_utils import configure_log_path
from ..utils.logging_utils import get_logger
from ..utils.logging_utils import log_exception
from ..utils.paths import get_app_paths
from ..utils.paths import migrate_legacy_data, migration_has_fatal_failure
from ..utils.timers import TimerRegistry
from ..ui.guards import PauseGuard


@dataclass(frozen=True)
class FoundationServices:
    """Immutable handles created before the Tk application boundary."""

    paths: Any
    clock: Any
    event_ledger: Any
    lifecycle: Any


@dataclass(frozen=True)
class TkServices:
    """Tk root and timer owner created by the composition boundary."""

    root: Any
    timers: Any
    owner_thread_id: int


@dataclass(frozen=True)
class RuntimeStateServices:
    """Durable transition journal and runtime-state coordinator pair."""

    journal: Any
    state: Any


@dataclass(frozen=True)
class RepositoryServices:
    """Durable task repository and guard adapter composed for one App."""

    taskdb: Any
    guard: Any


@dataclass(frozen=True)
class WatcherServices:
    """Optional native session/power/display watcher adapter."""

    watcher: Any


@dataclass(frozen=True)
class TrayServices:
    """Optional pystray adapter and its startup state."""

    tray: Any
    started: bool
    using_pystray: bool


@dataclass(frozen=True)
class PlatformServices:
    """Tray and native watcher services composed as one platform boundary."""

    tray: Any
    pystray_started: bool
    using_pystray: bool
    watcher: Any


@dataclass(frozen=True)
class MonitoringServices:
    """Selected monitoring engine and prompt coordinator pair."""

    engine: Any
    prompt_coordinator: Any


@dataclass(frozen=True)
class ConfigurationServices:
    """Validated settings snapshot and legacy-migration result."""

    settings: Any
    migration_events: Any


@dataclass(frozen=True)
class RuntimeServices:
    """Application-owned recurring services started in dependency order."""

    started: tuple[str, ...]


@dataclass(frozen=True)
class ShutdownServices:
    """Resources successfully closed by the reverse-order shutdown boundary."""

    closed: tuple[str, ...]


def compose_application_services(
    app: Any,
    *,
    force_start: bool = False,
    clock_override: Any = None,
    app_name: str = "FocusCheck",
    app_version: str = "",
) -> None:
    """Compose every pre-READY App service before readiness is published."""
    app._force_start = bool(force_start)
    dependencies = app._dependencies
    startup_stage = app._startup_stage

    foundations = compose_foundations(
        dependencies,
        clock_override=clock_override,
        startup_stage=startup_stage,
        component_sink=lambda name, value: setattr(
            app,
            {"paths": "paths", "clock": "_runtime_clock", "event_ledger": "_event_ledger", "lifecycle": "lifecycle"}[name],
            value,
        ),
    )
    app.paths = foundations.paths
    app._runtime_clock = foundations.clock
    app._event_ledger = foundations.event_ledger
    app.lifecycle = foundations.lifecycle

    compose_tk_services(
        dependencies,
        app._event_ledger,
        component_sink=lambda name, value: setattr(
            app,
            {"root": "root", "timers": "_timers"}[name]
            if name != "owner_thread_id" else "_tk_thread_id",
            value,
        ),
        startup_stage=startup_stage,
    )
    app._tk_thread_id = getattr(app, "_tk_thread_id", threading.get_ident())
    app._ui_dispatch_sequence = 0
    try:
        app.root.update_idletasks()
    except Exception:
        pass
    try:
        app.root.bind_all("<Control-Shift-Escape>", lambda e: app._quit())
        app.root.bind_all("<Alt-q>", lambda e: app._quit())
    except Exception:
        pass

    configuration_services = compose_configuration(
        dependencies.settings_loader,
        load_settings,
        dependencies.legacy_migration_factory or migrate_legacy_data,
        migration_has_fatal_failure,
        settings_path=app.paths.settings,
        paths=app.paths,
        startup_stage=startup_stage,
        logger_factory=get_logger,
        component_sink=lambda name, value: setattr(app, name, value),
    )
    app.settings = configuration_services.settings
    compose_runtime_state(
        dependencies,
        paths=app.paths,
        settings=app.settings,
        clock=app._runtime_clock,
        event_ledger=app._event_ledger,
        persist_settings=app._persist_settings_draft,
        component_sink=lambda name, value: setattr(
            app, {"journal": "_runtime_journal", "state": "_runtime_state"}[name], value
        ),
    )
    app._snooze_unpause_timer_id = None
    app._snooze_confirm_dialog = None
    try:
        app._apply_initial_monitoring_state()
    except Exception:
        try:
            get_logger().exception("startup: failed applying initial monitoring state", exc_info=True)
        except Exception:
            pass
        raise
    startup_stage("initial_monitoring_state_applied")

    app._engine = None
    app._engine_shutdown = False
    app._start_wall = app._runtime_clock.now_utc()
    app._start_mono = app._runtime_clock.monotonic()
    try:
        get_logger().info("App starting v%s | data_dir=%s", app_version, app.paths.root)
    except Exception:
        pass
    compose_repositories(
        dependencies,
        paths=app.paths,
        settings=app.settings,
        clock=app._runtime_clock,
        event_ledger=app._event_ledger,
        startup_stage=startup_stage,
        component_sink=lambda name, value: setattr(app, name, value),
    )
    monitoring_services = compose_monitoring(
        app._ensure_engine,
        app._new_prompt_coordinator,
        component_sink=lambda name, value: setattr(
            app, {"engine": "_engine", "prompt_coordinator": "_prompt_coordinator"}[name], value
        ),
    )
    app._engine = monitoring_services.engine
    startup_stage("engine_initialized")
    app._scheduled = None
    app._current_prompt = None
    app._prompt_coordinator = monitoring_services.prompt_coordinator
    app._intervention_active = False
    app._active_intervention_id = None
    app._last_resume_mono = 0.0
    app._next_due_mono = None
    app._next_total_s = None
    app._shutdown_requested = False
    app._shutdown_cleanup_complete = False
    app._heartbeat_sequence = 0
    app._process_start_utc = app._now_utc().isoformat()
    app._snooze_reminder_next_mono = 0.0
    app._snooze_reminder_dialog = None
    app._gentle_reminder_next_mono = 0.0
    app._gentle_reminder_dialog = None
    app._tray_icon_image = None
    app._tray_icon_path = None
    app._health_snapshot_service = HealthSnapshotService(
        app,
        app_name=app_name,
        app_version=app_version,
    )
    data_control_factory = getattr(dependencies, "data_control_service_factory", None)
    app._data_control_service = (
        data_control_factory(app) if callable(data_control_factory) else DataControlService(app)
    )
    intervention_factory = getattr(dependencies, "intervention_service_factory", None)
    app._intervention_service = (
        intervention_factory(app) if callable(intervention_factory) else InterventionOrchestrator(app)
    )
    scheduler_factory = getattr(dependencies, "prompt_scheduler_factory", None)
    app._prompt_scheduler = (
        scheduler_factory(app) if callable(scheduler_factory) else PromptScheduler(app)
    )
    startup_factory = getattr(dependencies, "startup_service_factory", None)
    app._startup_service = (
        startup_factory(app)
        if callable(startup_factory)
        else StartupService(
            app,
            install=app._install_startup,
            uninstall=app._uninstall_startup,
            is_installed=app._is_startup_installed,
            app_name=app_name,
        )
    )
    compose_runtime_services(
        app._prepare_tray_icon,
        app._start_heartbeat,
        app._start_file_heartbeat,
        app._start_snooze_reminder_check,
        app._start_gentle_reminder_check,
        app._log_startup_diagnostics,
        startup_stage=startup_stage,
    )

    app._pystray_started = False
    app._using_pystray = False
    app._native_tray_fallback_active = False
    app._tray = None
    app._winwatch = None
    platform_services = compose_platform_services(
        app,
        app._tray_factory(),
        app._watcher_factory(),
        name=app_name,
        paths=app.paths,
        root=app.root,
        icon_image=app._tray_icon_image,
        tray_icon_path=app._tray_icon_path,
        on_resume=app._on_resume_event,
        on_pause=app._on_pause_event,
        on_display_change=app._on_display_change,
        on_tray_click=app._on_tray_click,
        on_shutdown=app._handle_system_shutdown,
        startup_stage=startup_stage,
        component_sink=lambda name, value: setattr(
            app,
            {
                "tray": "_tray",
                "pystray_started": "_pystray_started",
                "using_pystray": "_using_pystray",
                "watcher": "_winwatch",
            }[name],
            value,
        ),
    )
    app._tray = platform_services.tray
    app._pystray_started = platform_services.pystray_started
    app._using_pystray = platform_services.using_pystray
    app._winwatch = platform_services.watcher


def compose_foundations(
    dependencies: Any,
    *,
    clock_override: Any = None,
    startup_stage: Callable[[str], Any] | None = None,
    component_sink: Callable[[str, Any], Any] | None = None,
) -> FoundationServices:
    """Create the path, clock, logging, ledger, and lifecycle foundations."""
    paths_factory = getattr(dependencies, "app_paths_factory", None) or get_app_paths
    paths = paths_factory(filesystem=getattr(dependencies, "filesystem", None))
    if callable(component_sink):
        component_sink("paths", paths)
    if callable(startup_stage):
        startup_stage("paths_composed")

    clock_factory = getattr(dependencies, "clock_factory", None) or SystemClock
    clock = clock_override or clock_factory()
    if callable(component_sink):
        component_sink("clock", clock)
    if callable(startup_stage):
        startup_stage("clock_composed")

    csv_paths_configurator = getattr(dependencies, "csv_paths_configurator", None) or configure_csv_paths
    csv_paths_configurator(paths)
    log_path_configurator = getattr(dependencies, "log_path_configurator", None) or configure_log_path
    log_path_configurator(paths.app_log)

    event_ledger_factory = getattr(dependencies, "event_ledger_factory", None) or StructuredEventLedger
    event_ledger = event_ledger_factory(
        paths.structured_events,
        clock=clock,
        monotonic_clock=clock.monotonic,
    )
    if callable(component_sink):
        component_sink("event_ledger", event_ledger)
    lifecycle_factory = getattr(dependencies, "lifecycle_factory", None) or LifecycleCoordinator
    lifecycle = lifecycle_factory(
        _sink=lambda event: event_ledger.append("lifecycle", event)
    )
    if callable(component_sink):
        component_sink("lifecycle", lifecycle)
    lifecycle.transition(LifecyclePhase.STARTING, reason="app_construct")
    if callable(startup_stage):
        startup_stage("lifecycle_starting")

    return FoundationServices(paths, clock, event_ledger, lifecycle)


def compose_configuration(
    settings_loader: Callable[[], Any] | None,
    default_settings_loader: Callable[[Any], Any],
    migration_factory: Callable[[Any], Any],
    migration_failure_predicate: Callable[[Any], bool],
    *,
    settings_path: Any,
    paths: Any,
    startup_stage: Callable[[str], Any] | None = None,
    logger_factory: Callable[[], Any] | None = None,
    component_sink: Callable[[str, Any], Any] | None = None,
) -> ConfigurationServices:
    """Load the immutable startup snapshot and complete legacy migration."""
    settings = (
        settings_loader()
        if callable(settings_loader)
        else default_settings_loader(settings_path)
    )
    if callable(component_sink):
        component_sink("settings", settings)
    if callable(startup_stage):
        startup_stage("settings_loaded")

    try:
        migration_events = migration_factory(paths)
        if migration_events and migration_failure_predicate(migration_events):
            raise RuntimeError("legacy data migration did not complete safely")
        if migration_events and callable(logger_factory):
            try:
                logger_factory().info(
                    "legacy data migration completed | events=%d", len(migration_events)
                )
            except Exception:
                pass
    except Exception:
        if callable(logger_factory):
            try:
                logger_factory().exception("legacy data migration failed", exc_info=True)
            except Exception:
                pass
        raise

    if callable(startup_stage):
        startup_stage("migration_completed")
    return ConfigurationServices(settings, migration_events)


def compose_runtime_services(
    prepare_tray_icon: Callable[[], Any],
    start_heartbeat: Callable[[], Any],
    start_file_heartbeat: Callable[[], Any],
    start_snooze_reminder: Callable[[], Any],
    start_gentle_reminder: Callable[[], Any],
    startup_diagnostics: Callable[[], Any],
    *,
    startup_stage: Callable[[str], Any] | None = None,
) -> RuntimeServices:
    """Start recurring App services in a stable order before tray wiring."""
    prepare_tray_icon()
    started: list[str] = []
    start_heartbeat()
    started.append("heartbeat")
    start_file_heartbeat()
    started.append("file_heartbeat")
    start_snooze_reminder()
    started.append("snooze_reminder")
    start_gentle_reminder()
    started.append("gentle_reminder")
    if callable(startup_stage):
        startup_stage("services_started")
    try:
        startup_diagnostics()
    except Exception:
        # Diagnostics are best effort and must not prevent tray/watcher startup.
        pass
    return RuntimeServices(tuple(started))


def compose_shutdown_services(
    closers: list[tuple[str, Callable[[], Any]] | tuple[str, Callable[[], Any], str]],
    *,
    shutdown_stage: Callable[[str], Any] | None = None,
    logger_factory: Callable[[], Any] | None = None,
) -> ShutdownServices:
    """Close owned resources in order while isolating each failure."""
    closed: list[str] = []
    for closer in closers:
        name, callback = closer[:2]
        stage_name = closer[2] if len(closer) == 3 else f"{name}_closed"
        try:
            callback()
            closed.append(name)
            if callable(shutdown_stage):
                shutdown_stage(stage_name)
        except Exception:
            if callable(logger_factory):
                try:
                    logger_factory().exception(
                        "shutdown cleanup failed: %s", name, exc_info=True
                    )
                except Exception:
                    pass
    return ShutdownServices(tuple(closed))


def compose_tk_services(
    dependencies: Any,
    event_ledger: Any,
    *,
    component_sink: Callable[[str, Any], Any] | None = None,
    startup_stage: Callable[[str], Any] | None = None,
) -> TkServices:
    """Create the owner-thread Tk root and its App-owned timer registry."""
    root_factory = getattr(dependencies, "tk_root_factory", None) or tk.Tk
    root = root_factory()
    if callable(component_sink):
        component_sink("root", root)
    owner_thread_id = threading.get_ident()
    if callable(component_sink):
        component_sink("owner_thread_id", owner_thread_id)
    try:
        root._focuscheck_tk_thread_id = owner_thread_id
    except Exception:
        pass
    try:
        def _tk_callback_exception(exc, val, tb):
            try:
                get_logger().exception("tk callback exception", exc_info=(exc, val, tb))
            except Exception:
                pass
        root.report_callback_exception = _tk_callback_exception
    except Exception:
        pass
    root.withdraw()

    timer_registry_factory = getattr(dependencies, "timer_registry_factory", None) or TimerRegistry
    timers = timer_registry_factory(
        root,
        event_sink=lambda event: event_ledger.append("timer", event),
    )
    if callable(component_sink):
        component_sink("timers", timers)
    if callable(startup_stage):
        startup_stage("tk_and_timers_created")
    return TkServices(root, timers, owner_thread_id)


def compose_runtime_state(
    dependencies: Any,
    *,
    paths: Any,
    settings: dict[str, Any],
    clock: Any,
    event_ledger: Any,
    persist_settings: Callable[[dict[str, Any]], Any],
    component_sink: Callable[[str, Any], Any] | None = None,
) -> RuntimeStateServices:
    """Create the durable runtime journal and state coordinator."""
    journal_factory = getattr(dependencies, "runtime_journal_factory", None) or RuntimeTransitionJournal
    journal = journal_factory(paths.runtime_state, clock=clock)
    if callable(component_sink):
        component_sink("journal", journal)

    def record_runtime_event(event):
        journal_ok = journal.append(event)
        event_ledger.append("runtime", event)
        return journal_ok

    state_factory = getattr(dependencies, "runtime_state_factory", None) or RuntimeStateCoordinator
    state = state_factory(
        settings,
        persist=persist_settings,
        clock=clock,
        transition_sink=record_runtime_event,
    )
    if callable(component_sink):
        component_sink("state", state)
    return RuntimeStateServices(journal, state)


def compose_repositories(
    dependencies: Any,
    *,
    paths: Any,
    settings: dict[str, Any],
    clock: Any,
    event_ledger: Any,
    startup_stage: Callable[[str], Any] | None = None,
    component_sink: Callable[[str, Any], Any] | None = None,
) -> RepositoryServices:
    """Create TaskDB, log-header, and guard services for one App."""
    taskdb = None
    try:
        task_db_factory = getattr(dependencies, "task_db_factory", None) or TaskDB
        task_db_kwargs = {
            "clock": clock,
            "event_sink": lambda event: event_ledger.append("task", event),
        }
        sqlite_factory = getattr(dependencies, "sqlite_connection_factory", None)
        if callable(sqlite_factory):
            task_db_kwargs["connection_factory"] = sqlite_factory
        taskdb = task_db_factory(paths.task_db, **task_db_kwargs)
    except Exception:
        log_exception("TaskDB unavailable; continuing without tasks feature")
    if callable(component_sink):
        component_sink("taskdb", taskdb)
    if callable(startup_stage):
        startup_stage("repositories_initialized")

    log_header_factory = getattr(dependencies, "log_header_factory", None) or ensure_log_header
    log_header_factory(paths.focus_log)
    guard_factory = getattr(dependencies, "guard_factory", None) or PauseGuard
    guard = guard_factory(lambda: settings)
    if callable(component_sink):
        component_sink("guard", guard)
    return RepositoryServices(taskdb, guard)


def compose_watcher(
    watcher_factory: Callable[..., Any] | None,
    *,
    root: Any,
    pystray_started: bool,
    tray_icon_path: Any,
    on_resume: Callable[..., Any],
    on_pause: Callable[..., Any],
    on_display_change: Callable[..., Any],
    on_tray_click: Callable[..., Any],
    on_shutdown: Callable[..., Any],
    startup_stage: Callable[[str], Any] | None = None,
    component_sink: Callable[[str, Any], Any] | None = None,
) -> WatcherServices:
    """Construct the optional native watcher without owning App state."""
    watcher = None
    if watcher_factory is not None:
        try:
            watcher = watcher_factory(
                root,
                on_resume_callable=on_resume,
                on_pause_callable=on_pause,
                on_display_change_callable=on_display_change,
                tray_enabled=not pystray_started,
                on_tray_click_callable=on_tray_click,
                tray_tooltip="Focus Check",
                tray_icon_path=tray_icon_path,
                on_shutdown_callable=on_shutdown,
            )
            if callable(component_sink):
                component_sink("watcher", watcher)
            try:
                get_logger().info(
                    "startup: Windows watcher initialized | native_tray=%s",
                    not pystray_started,
                )
            except Exception:
                pass
        except Exception as exc:
            print(f"Windows watcher/tray unavailable: {exc}", file=sys.stderr)
    if callable(startup_stage):
        startup_stage("watcher_initialized")
    return WatcherServices(watcher)


def compose_tray(
    app: Any,
    tray_factory: Callable[..., Any] | None,
    *,
    name: str,
    paths: Any,
    icon_image: Any,
) -> TrayServices:
    """Construct and start the optional pystray adapter."""
    tray = None
    started = False
    using_pystray = False
    try:
        if tray_factory is not None:
            try:
                get_logger().info("startup: pystray system tray available; attempting start")
            except Exception:
                pass

            def _get(key, default=None):
                try:
                    return app.settings.get(key, default)
                except Exception:
                    return default

            def _set(key, value):
                try:
                    app._set_tray_setting(key, value)
                except Exception:
                    pass

            def _on_alive():
                nonlocal using_pystray
                try:
                    get_logger().info("tray post-start check OK (pystray alive)")
                except Exception:
                    pass
                using_pystray = True
                app._using_pystray = True

            def _on_failure():
                try:
                    get_logger().error("pystray post-start check failed", exc_info=True)
                except Exception:
                    pass
                app._call_on_ui_thread(app._activate_native_tray_fallback)

            tray = tray_factory(
                app=app,
                name=name,
                tooltip=f"{name} running",
                get_setting=_get,
                set_setting=_set,
                open_settings_ui=lambda: app._open_settings_from_tray(),
                logs_path=str(paths.app_log),
                config_path=str(paths.settings),
                icon_image=icon_image,
                on_failure=_on_failure,
                on_alive=_on_alive,
            )
            try:
                get_logger().info("creating icon (pystray)")
            except Exception:
                pass
            try:
                started = bool(tray.start())
            except Exception:
                get_logger().exception("pystray start raised", exc_info=True)
                started = False
            if started:
                try:
                    get_logger().info("tray start succeeded (pystray)")
                    get_logger().info("startup: pystray tray started successfully")
                except Exception:
                    pass
            else:
                try:
                    get_logger().error("tray start failed (pystray)")
                    get_logger().warning(
                        "startup: pystray tray failed to start; falling back (Windows native, if available)"
                    )
                except Exception:
                    pass
    except Exception:
        get_logger().exception("pystray setup failed", exc_info=True)
        started = False
        using_pystray = False
        try:
            app._using_pystray = False
        except Exception:
            pass
    return TrayServices(tray, started, using_pystray)


def compose_platform_services(
    app: Any,
    tray_factory: Callable[..., Any] | None,
    watcher_factory: Callable[..., Any] | None,
    *,
    name: str,
    paths: Any,
    root: Any,
    icon_image: Any,
    tray_icon_path: Any,
    on_resume: Callable[..., Any],
    on_pause: Callable[..., Any],
    on_display_change: Callable[..., Any],
    on_tray_click: Callable[..., Any],
    on_shutdown: Callable[..., Any],
    startup_stage: Callable[[str], Any] | None = None,
    component_sink: Callable[[str, Any], Any] | None = None,
) -> PlatformServices:
    """Compose tray first, then native watcher fallback wiring."""
    tray_services = compose_tray(
        app,
        tray_factory,
        name=name,
        paths=paths,
        icon_image=icon_image,
    )
    if callable(component_sink):
        component_sink("tray", tray_services.tray)
        component_sink("pystray_started", tray_services.started)
        component_sink("using_pystray", tray_services.using_pystray)
    if callable(startup_stage):
        startup_stage("tray_initialized")

    watcher_services = compose_watcher(
        watcher_factory,
        root=root,
        pystray_started=tray_services.started,
        tray_icon_path=tray_icon_path,
        on_resume=on_resume,
        on_pause=on_pause,
        on_display_change=on_display_change,
        on_tray_click=on_tray_click,
        on_shutdown=on_shutdown,
        startup_stage=startup_stage,
        component_sink=(
            (lambda _name, value: component_sink("watcher", value))
            if callable(component_sink) else None
        ),
    )
    return PlatformServices(
        tray_services.tray,
        tray_services.started,
        tray_services.using_pystray,
        watcher_services.watcher,
    )


def compose_monitoring(
    ensure_engine: Callable[[], Any],
    prompt_coordinator_factory: Callable[[], Any],
    *,
    component_sink: Callable[[str, Any], Any] | None = None,
) -> MonitoringServices:
    """Assemble the selected engine and its prompt coordinator."""
    engine = ensure_engine()
    if callable(component_sink):
        component_sink("engine", engine)
    prompt_coordinator = prompt_coordinator_factory()
    if callable(component_sink):
        component_sink("prompt_coordinator", prompt_coordinator)
    return MonitoringServices(engine, prompt_coordinator)

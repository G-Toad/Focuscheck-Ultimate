"""Composition of App-owned non-Tk foundation services."""

from __future__ import annotations

from dataclasses import dataclass
import threading
import tkinter as tk
import sys
from typing import Any, Callable

from ..database import configure_paths as configure_csv_paths
from ..database import TaskDB, ensure_log_header
from ..runtime.events import StructuredEventLedger
from ..runtime.journal import RuntimeTransitionJournal
from ..runtime.lifecycle import LifecycleCoordinator, LifecyclePhase
from ..runtime.state import RuntimeStateCoordinator
from ..utils.clock import SystemClock
from ..utils.logging_utils import configure_log_path
from ..utils.logging_utils import get_logger
from ..utils.logging_utils import log_exception
from ..utils.paths import get_app_paths
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

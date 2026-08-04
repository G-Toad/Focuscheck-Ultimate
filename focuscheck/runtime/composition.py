"""Composition of App-owned non-Tk foundation services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ..database import configure_paths as configure_csv_paths
from ..runtime.events import StructuredEventLedger
from ..runtime.lifecycle import LifecycleCoordinator, LifecyclePhase
from ..utils.clock import SystemClock
from ..utils.logging_utils import configure_log_path
from ..utils.paths import get_app_paths


@dataclass(frozen=True)
class FoundationServices:
    """Immutable handles created before the Tk application boundary."""

    paths: Any
    clock: Any
    event_ledger: Any
    lifecycle: Any


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

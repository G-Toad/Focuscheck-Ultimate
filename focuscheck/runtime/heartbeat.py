"""Structured heartbeat publication for the supervisor protocol."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from ..utils.logging_utils import get_logger


class HeartbeatService:
    """Build and atomically publish one App-owned heartbeat payload."""

    def __init__(
        self,
        app: Any,
        *,
        heartbeat_interval_ms: int,
        default_path: Any,
        logger_factory: Callable[[], Any] = get_logger,
    ) -> None:
        self._app = app
        self._heartbeat_interval_ms = int(heartbeat_interval_ms)
        self._default_path = default_path
        self._logger_factory = logger_factory

    def write(self) -> None:
        app = self._app
        temp_path = None
        try:
            app._heartbeat_sequence = getattr(app, "_heartbeat_sequence", 0) + 1
            process_start_utc = getattr(app, "_process_start_utc", None) or app._now_utc().isoformat()
            runtime_state = getattr(app, "_runtime_state", None)
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
                manual_paused = bool(app.settings.get("paused", False))
                snooze_active = False
                guard_paused = bool(app.guard.should_pause())
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
            guard_diagnostics = getattr(app.guard, "diagnostics", None)
            if callable(guard_diagnostics):
                candidate_health = guard_diagnostics()
                if isinstance(candidate_health, dict):
                    guard_health = candidate_health
            payload = {
                "protocol_version": 1,
                "supervisor_id": os.environ.get("FOCUSCHECK_SUPERVISOR_ID", ""),
                "generation": os.environ.get("FOCUSCHECK_CHILD_GENERATION", ""),
                "utc": app._now_utc().isoformat(),
                "pid": os.getpid(),
                "process_start_utc": process_start_utc,
                "sequence": app._heartbeat_sequence,
                "heartbeat_interval_seconds": self._heartbeat_interval_ms / 1000,
                "readiness": app._lifecycle_readiness(),
                "lifecycle": app._lifecycle_snapshot(),
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
                "interval_seconds": int(app.settings.get("interval_seconds", 60)),
            }
            paths = getattr(app, "paths", None)
            heartbeat_path = Path(getattr(paths, "heartbeat", self._default_path))
            heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
            heartbeat_writer = getattr(getattr(app, "_dependencies", None), "heartbeat_writer", None)
            if callable(heartbeat_writer):
                heartbeat_writer(heartbeat_path, payload)
            else:
                temp_path = heartbeat_path.with_name(
                    f"{heartbeat_path.name}.{os.getpid()}.{app._heartbeat_sequence}.tmp"
                )
                with temp_path.open("w", encoding="utf-8") as handle:
                    json.dump(payload, handle)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_path, heartbeat_path)
            app._heartbeat_write_failures = 0
        except Exception as exc:
            app._heartbeat_write_failures = getattr(app, "_heartbeat_write_failures", 0) + 1
            now = app._monotonic()
            last_log = getattr(app, "_last_heartbeat_failure_log_mono", 0.0)
            count = app._heartbeat_write_failures
            if count <= 3 or count % 10 == 0 or now - last_log >= 60.0:
                try:
                    self._logger_factory().warning(
                        "heartbeat write failed | consecutive=%d | error_type=%s",
                        count,
                        type(exc).__name__,
                    )
                except Exception:
                    pass
                app._last_heartbeat_failure_log_mono = now
        finally:
            if temp_path is not None:
                try:
                    Path(temp_path).unlink()
                except OSError:
                    pass


__all__ = ["HeartbeatService"]

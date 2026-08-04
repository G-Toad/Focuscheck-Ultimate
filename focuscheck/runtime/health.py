"""Read-only operational health projection for the composed application."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any


class HealthSnapshotService:
    """Project App-owned state into a bounded, privacy-safe health payload."""

    def __init__(self, app: Any, *, app_name: str, app_version: str) -> None:
        self._app = app
        self._app_name = str(app_name)
        self._app_version = str(app_version)

    def snapshot(self) -> dict[str, Any]:
        app = self._app
        guard_status = "unknown"
        try:
            health = app.guard.diagnostics()
            if isinstance(health, dict):
                guard_status = "healthy" if bool(health.get("healthy", True)) else "degraded"
        except Exception:
            guard_status = "unavailable"
        try:
            lifecycle = getattr(getattr(app, "lifecycle", None), "phase", None)
            lifecycle = getattr(lifecycle, "value", lifecycle) or "unknown"
        except Exception:
            lifecycle = "unknown"
        try:
            from ..doctor import get_anomalies
            anomaly_count = len(get_anomalies())
        except Exception:
            anomaly_count = 0
        try:
            from ..settings.schema import get_settings_schema
            schema_key_count = len(get_settings_schema())
        except Exception:
            schema_key_count = "unknown"
        if bool(getattr(app, "_using_pystray", False)):
            tray_backend = "pystray"
        elif bool(getattr(app, "_native_tray_fallback_active", False)):
            tray_backend = "native fallback"
        else:
            tray_backend = "unavailable"
        prompt = getattr(app, "_current_prompt", None)
        camera = getattr(prompt, "_camera_capability", None)
        if not isinstance(camera, dict):
            camera = {"state": "inactive"}
        else:
            camera = {"state": str(camera.get("state", "unknown"))}
        runtime_state = getattr(app, "_runtime_state", None)
        effective_paused = bool(getattr(app, "settings", {}).get("paused", False))
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
        heartbeat_path = getattr(getattr(app, "paths", None), "heartbeat", None)
        if heartbeat_path:
            try:
                heartbeat_age_seconds = round(max(0.0, time.time() - Path(heartbeat_path).stat().st_mtime), 1)
            except (OSError, ValueError, TypeError):
                heartbeat_age_seconds = None
        watcher = getattr(app, "_winwatch", None)
        watcher_state = "registered" if watcher is not None else "unavailable"
        if bool(getattr(watcher, "closed", False)):
            watcher_state = "closed"
        return {
            "application": self._app_name,
            "version": self._app_version,
            "lifecycle": lifecycle,
            "monitoring": "running" if getattr(app, "_engine", None) is not None and not getattr(app, "_engine_shutdown", False) else "stopped",
            "paused": effective_paused,
            "effective_paused": effective_paused,
            "snooze_active": snooze_active,
            "pause_reason": pause_reason,
            "runtime_revision": runtime_revision,
            "transition_sink_failures": transition_sink_failures,
            "guard_reasons": guard_reasons,
            "prompt_active": getattr(app, "_current_prompt", None) is not None,
            "intervention_active": bool(getattr(app, "_intervention_active", False)),
            "intervention_id": getattr(app, "_active_intervention_id", None),
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
            "task_db": "available" if getattr(app, "taskdb", None) is not None else "unavailable",
            "activity_provider": "configured" if getattr(app, "_activity_provider", None) is not None else "unavailable",
            "data_root": str(app._data_root()),
        }


__all__ = ["HealthSnapshotService"]

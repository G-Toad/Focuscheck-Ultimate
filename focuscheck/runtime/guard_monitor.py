"""Application-owned guard sampling and pause-edge scheduling."""

from __future__ import annotations

from typing import Any


class GuardMonitorService:
    """Own periodic guard sampling and effective-pause edge handling."""

    def __init__(self, app: Any, *, interval_ms: int = 1000) -> None:
        self._app = app
        self._interval_ms = max(1, int(interval_ms))
        self._last_paused_state: bool | None = None

    def refresh(self) -> bool:
        """Sample the platform guard once and publish the result."""
        app = self._app
        try:
            guard = getattr(app, "guard", None)
            guard_paused = bool(guard.should_pause()) if guard is not None else False
        except Exception:
            guard_paused = False

        runtime_state = getattr(app, "_runtime_state", None)
        if runtime_state is not None:
            previous_effective = None
            try:
                previous_effective = bool(runtime_state.is_effectively_paused())
            except Exception:
                pass
            runtime_state.set_guard_reason("system_guard", guard_paused)
            if previous_effective is not None:
                try:
                    current_effective = bool(runtime_state.is_effectively_paused())
                    if current_effective != previous_effective:
                        app._notify_engine_pause_state(source="system_guard")
                except Exception:
                    pass
        return guard_paused

    def start(self) -> None:
        """Run the first sample immediately and register the recurring poll."""
        app = self._app
        self._last_paused_state = None

        def tick() -> None:
            try:
                paused_now = self.refresh()
                if self._last_paused_state is True and paused_now is False:
                    app._schedule_next(0)
                self._last_paused_state = paused_now
            except Exception:
                pass
            if hasattr(app, "_timers"):
                return
            app.root.after(self._interval_ms, tick)

        tick()
        if hasattr(app, "_timers"):
            app._timers.schedule(
                "pause-edge",
                self._interval_ms,
                tick,
                interval_ms=self._interval_ms,
            )


__all__ = ["GuardMonitorService"]

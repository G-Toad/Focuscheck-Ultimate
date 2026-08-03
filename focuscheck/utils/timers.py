"""Generation-aware ownership for Tk ``after`` callbacks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Any


@dataclass
class _Timer:
    name: str
    generation: int
    callback_id: Any = None
    cancelled: bool = False


class TimerRegistry:
    """Own named Tk timers and make stale callbacks harmless."""

    def __init__(self, scheduler: Any, *, event_sink: Callable[[dict[str, Any]], Any] | None = None) -> None:
        self._scheduler = scheduler
        self._event_sink = event_sink
        self._timers: dict[str, _Timer] = {}
        self._generations: dict[str, int] = {}
        self._closed = False

    def _emit(self, action: str, name: str, **fields: Any) -> None:
        if self._event_sink is None:
            return
        try:
            self._event_sink({"event": "timer", "action": action, "name": name, **fields})
        except Exception:
            # Observability must not change timer behavior or shutdown.
            pass

    def schedule(
        self,
        name: str,
        delay_ms: int,
        callback: Callable[[], Any],
        *,
        interval_ms: int | None = None,
    ) -> bool:
        """Replace a timer with the same name and return whether it was set."""
        if self._closed:
            return False
        self.cancel(name)
        generation = self._generations.get(name, 0) + 1
        self._generations[name] = generation
        timer = _Timer(name=name, generation=generation)
        self._timers[name] = timer

        def run() -> None:
            current = self._timers.get(name)
            if self._closed or current is not timer or timer.cancelled:
                return
            if interval_ms is None:
                self._timers.pop(name, None)
            try:
                callback()
            finally:
                current = self._timers.get(name)
                if interval_ms is not None and not self._closed and current is timer and not timer.cancelled:
                    try:
                        timer.callback_id = self._scheduler.after(max(0, int(interval_ms)), run)
                    except Exception:
                        # A destroyed/rejecting Tk scheduler must not leave a
                        # recurring timer registered after its callback fires.
                        if self._timers.get(name) is timer:
                            self._timers.pop(name, None)
                        timer.cancelled = True
                        raise

        try:
            timer.callback_id = self._scheduler.after(max(0, int(delay_ms)), run)
        except Exception:
            # Roll back the ownership record when Tk rejects registration.
            if self._timers.get(name) is timer:
                self._timers.pop(name, None)
            timer.cancelled = True
            raise
        self._emit(
            "schedule",
            name,
            delay_ms=max(0, int(delay_ms)),
            interval_ms=None if interval_ms is None else max(0, int(interval_ms)),
        )
        return True

    def cancel(self, name: str) -> bool:
        timer = self._timers.pop(name, None)
        if timer is None:
            return False
        timer.cancelled = True
        try:
            self._scheduler.after_cancel(timer.callback_id)
        except Exception:
            # Tk may already be dispatching the callback; generation checks
            # still make that callback a no-op.
            pass
        self._emit("cancel", name)
        return True

    def cancel_all(self) -> None:
        for name in list(self._timers):
            self.cancel(name)

    def close(self) -> None:
        self._closed = True
        self.cancel_all()
        self._emit("close", "registry")

    def callback_id(self, name: str) -> Any:
        timer = self._timers.get(name)
        return timer.callback_id if timer is not None else None

    @property
    def closed(self) -> bool:
        return self._closed

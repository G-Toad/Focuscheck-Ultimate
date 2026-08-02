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

    def __init__(self, scheduler: Any) -> None:
        self._scheduler = scheduler
        self._timers: dict[str, _Timer] = {}
        self._generations: dict[str, int] = {}
        self._closed = False

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
                    timer.callback_id = self._scheduler.after(max(0, int(interval_ms)), run)

        timer.callback_id = self._scheduler.after(max(0, int(delay_ms)), run)
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
        return True

    def cancel_all(self) -> None:
        for name in list(self._timers):
            self.cancel(name)

    def close(self) -> None:
        self._closed = True
        self.cancel_all()

    def callback_id(self, name: str) -> Any:
        timer = self._timers.get(name)
        return timer.callback_id if timer is not None else None

    @property
    def closed(self) -> bool:
        return self._closed

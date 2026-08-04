"""Application-owned prompt scheduling boundary."""

from __future__ import annotations

from typing import Any

from ..utils.logging_utils import get_logger


class PromptScheduler:
    """Own prompt timer registration and observer cancellation for one App."""

    def __init__(self, app: Any) -> None:
        self._app = app

    def schedule_next(self, delay_ms: int | None = None) -> None:
        app = self._app
        if delay_ms is None:
            delay_ms = int(app.settings["interval_seconds"] * 1000)
        if app._scheduled and not hasattr(app, "_timers"):
            try:
                app.root.after_cancel(app._scheduled)
            except Exception:
                pass
            app._scheduled = None
        try:
            get_logger().debug("scheduling next prompt in %sms", delay_ms)
        except Exception:
            pass
        if hasattr(app, "_timers"):
            app._timers.schedule("prompt", delay_ms, app._maybe_show_prompt)
            app._scheduled = app._timers.callback_id("prompt")
        else:
            app._scheduled = app.root.after(delay_ms, app._maybe_show_prompt)
        try:
            app._next_total_s = max(1, int(delay_ms // 1000))
            app._next_due_mono = app._monotonic() + (delay_ms / 1000.0)
        except Exception:
            app._next_total_s = None
            app._next_due_mono = None

    def cancel_prompt_observers(self) -> None:
        app = self._app
        timers = getattr(app, "_timers", None)
        if timers is not None:
            timers.cancel("prompt-visible")
            timers.cancel("prompt-closed")
        root = getattr(app, "root", None)
        for attribute in ("_prompt_visibility_timer_id", "_prompt_closed_timer_id"):
            timer_id = getattr(app, attribute, None)
            if timer_id is None or root is None:
                continue
            try:
                root.after_cancel(timer_id)
            except Exception:
                pass
            setattr(app, attribute, None)


__all__ = ["PromptScheduler"]

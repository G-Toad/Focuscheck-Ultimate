"""Explicit application lifecycle phases and transition evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import threading
from typing import Callable


class LifecyclePhase(str, Enum):
    CONSTRUCTING = "constructing"
    STARTING = "starting"
    READY = "ready"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


_ALLOWED_TRANSITIONS = {
    LifecyclePhase.CONSTRUCTING: {LifecyclePhase.STARTING, LifecyclePhase.FAILED, LifecyclePhase.STOPPING},
    LifecyclePhase.STARTING: {LifecyclePhase.READY, LifecyclePhase.FAILED, LifecyclePhase.STOPPING},
    LifecyclePhase.READY: {LifecyclePhase.FAILED, LifecyclePhase.STOPPING},
    LifecyclePhase.FAILED: {LifecyclePhase.STOPPING, LifecyclePhase.STOPPED},
    LifecyclePhase.STOPPING: {LifecyclePhase.STOPPED, LifecyclePhase.FAILED},
    LifecyclePhase.STOPPED: set(),
}


@dataclass
class LifecycleCoordinator:
    """Own lifecycle phase transitions and publish bounded metadata."""

    phase: LifecyclePhase = LifecyclePhase.CONSTRUCTING
    reason: str = ""
    error_type: str = ""
    _sink: Callable[[dict], None] | None = None
    _history: list[dict] = field(default_factory=list)
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    def transition(self, target: LifecyclePhase | str, *, reason: str = "") -> bool:
        target = LifecyclePhase(target)
        with self._lock:
            if target == self.phase:
                return False
            if target not in _ALLOWED_TRANSITIONS[self.phase]:
                return False
            previous = self.phase
            self.phase = target
            self.reason = str(reason)[:120]
            if target != LifecyclePhase.FAILED:
                self.error_type = ""
            self._record(previous, target)
            return True

    def fail(self, error: BaseException | None = None, *, reason: str = "") -> bool:
        with self._lock:
            self.error_type = type(error).__name__ if error is not None else "Error"
            return self.transition(LifecyclePhase.FAILED, reason=reason or self.error_type)

    def begin_shutdown(self, *, reason: str = "") -> bool:
        return self.transition(LifecyclePhase.STOPPING, reason=reason or "shutdown")

    def mark_stopped(self, *, reason: str = "") -> bool:
        return self.transition(LifecyclePhase.STOPPED, reason=reason or "stopped")

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "phase": self.phase.value,
                "reason": self.reason,
                "error_type": self.error_type,
            }

    def history(self) -> list[dict]:
        with self._lock:
            return [dict(item) for item in self._history]

    def _record(self, previous: LifecyclePhase, target: LifecyclePhase) -> None:
        event = {
            "from": previous.value,
            "to": target.value,
            "reason": self.reason,
            "error_type": self.error_type,
        }
        self._history.append(event)
        if len(self._history) > 32:
            del self._history[:-32]
        if self._sink is not None:
            try:
                self._sink(dict(event))
            except Exception:
                pass


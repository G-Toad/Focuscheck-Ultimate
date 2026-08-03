"""Bounded, privacy-safe structured event ledger."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import threading
import time
from collections import deque
from typing import Any


_SAFE_STRING_KEYS = {
    "event", "category", "outcome", "from", "to", "phase",
    "error_type", "source", "status", "backend", "operation",
}
_SAFE_REASON_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,96}$")


def _safe_value(key: str, value: Any) -> Any:
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    if isinstance(value, str):
        if key in {"reason", "target"}:
            text = value.strip()
            if _SAFE_REASON_RE.fullmatch(text):
                return text
            return {"type": "string", "length": len(value)}
        if key in _SAFE_STRING_KEYS:
            return value[:160]
        return {"type": "string", "length": len(value)}
    if isinstance(value, (list, tuple, set)):
        return {"type": "collection", "length": len(value)}
    if isinstance(value, dict):
        return {"type": "object", "keys": min(len(value), 64)}
    return {"type": type(value).__name__}


class StructuredEventLedger:
    """Persist recent operational metadata without user-provided content."""

    def __init__(
        self,
        path: str | os.PathLike[str],
        *,
        max_bytes: int = 512 * 1024,
        max_events_per_window: int = 600,
        window_seconds: float = 60.0,
        monotonic_clock=None,
        clock=None,
    ) -> None:
        self.path = Path(path)
        self.max_bytes = max(4096, int(max_bytes))
        self.max_events_per_window = max(1, int(max_events_per_window))
        self.window_seconds = max(0.1, float(window_seconds))
        self._monotonic_clock = monotonic_clock or time.monotonic
        self._clock = clock
        self._event_times = deque()
        self._dropped_events = 0
        self._lock = threading.Lock()

    def _now_utc(self) -> datetime:
        try:
            value = self._clock() if callable(self._clock) else self._clock.now_utc()
            if isinstance(value, datetime):
                if value.tzinfo is None:
                    value = value.replace(tzinfo=timezone.utc)
                return value.astimezone(timezone.utc)
        except (AttributeError, TypeError, ValueError, OverflowError):
            pass
        return datetime.now(timezone.utc)

    @property
    def dropped_events(self) -> int:
        """Return the bounded count of events suppressed by rate limiting."""
        with self._lock:
            return self._dropped_events

    def _allow_event(self) -> bool:
        now = float(self._monotonic_clock())
        cutoff = now - self.window_seconds
        while self._event_times and self._event_times[0] <= cutoff:
            self._event_times.popleft()
        if len(self._event_times) >= self.max_events_per_window:
            self._dropped_events += 1
            return False
        self._event_times.append(now)
        return True

    def append(self, category: str, event: dict[str, Any] | None = None, **fields: Any) -> None:
        payload: dict[str, Any] = {"utc": self._now_utc().isoformat(), "category": str(category)[:80]}
        merged = dict(event or {})
        merged.update(fields)
        for key, value in merged.items():
            payload[str(key)[:80]] = _safe_value(str(key), value)
        line = json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n"
        with self._lock:
            if not self._allow_event():
                return
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                if self.path.exists() and self.path.stat().st_size + len(line.encode("utf-8")) > self.max_bytes:
                    backup = self.path.with_suffix(self.path.suffix + ".1")
                    backup.unlink(missing_ok=True)
                    self.path.replace(backup)
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(line)
                    handle.flush()
                    os.fsync(handle.fileno())
            except OSError:
                # Observability must never break the application.
                return

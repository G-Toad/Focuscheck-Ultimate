"""Bounded, privacy-safe structured event ledger."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading
from typing import Any


_SAFE_STRING_KEYS = {
    "event", "category", "outcome", "from", "to", "phase", "reason",
    "error_type", "source", "status", "backend", "operation",
}


def _safe_value(key: str, value: Any) -> Any:
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    if isinstance(value, str):
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

    def __init__(self, path: str | os.PathLike[str], *, max_bytes: int = 512 * 1024) -> None:
        self.path = Path(path)
        self.max_bytes = max(4096, int(max_bytes))
        self._lock = threading.Lock()

    def append(self, category: str, event: dict[str, Any] | None = None, **fields: Any) -> None:
        payload: dict[str, Any] = {"utc": datetime.now(timezone.utc).isoformat(), "category": str(category)[:80]}
        merged = dict(event or {})
        merged.update(fields)
        for key, value in merged.items():
            payload[str(key)[:80]] = _safe_value(str(key), value)
        line = json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n"
        with self._lock:
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


"""Bounded, metadata-only runtime transition journal."""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path


class RuntimeTransitionJournal:
    """Append safe lifecycle metadata without recording user prompt content."""

    def __init__(self, path: str | os.PathLike[str], max_bytes: int = 512 * 1024) -> None:
        self.path = Path(path)
        self.max_bytes = max(4096, int(max_bytes))
        self._lock = threading.Lock()

    def append(self, event: dict) -> None:
        payload = {
            "utc": datetime.now(timezone.utc).isoformat(),
            "event": str(event.get("event", "transition")),
            "outcome": str(event.get("outcome", "committed")),
            "manual_paused": bool(event.get("manual_paused", False)),
            "snooze_active": bool(event.get("snooze_active", False)),
            "guard_count": int(event.get("guard_count", 0)),
            "prompt_active": bool(event.get("prompt_active", False)),
            "intervention_active": bool(event.get("intervention_active", False)),
            "shutdown_requested": bool(event.get("shutdown_requested", False)),
        }
        line = json.dumps(payload, separators=(",", ":")) + "\n"
        with self._lock:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                if self.path.exists() and self.path.stat().st_size + len(line.encode("utf-8")) > self.max_bytes:
                    backup = self.path.with_suffix(self.path.suffix + ".1")
                    try:
                        backup.unlink(missing_ok=True)
                    except OSError:
                        pass
                    self.path.replace(backup)
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(line)
                    handle.flush()
                    os.fsync(handle.fileno())
            except OSError:
                # Runtime journaling must never make the application fail.
                return

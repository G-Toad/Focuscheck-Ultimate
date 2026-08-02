"""Small clock boundary used by deterministic service tests."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta


class SystemClock:
    """Production wall and monotonic clock."""

    @staticmethod
    def now_utc() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def monotonic() -> float:
        return time.monotonic()


@dataclass
class FakeClock:
    """Manually advanced clock for expiry and lifecycle tests."""

    current_utc: datetime
    current_monotonic: float = 0.0

    def __post_init__(self) -> None:
        if self.current_utc.tzinfo is None:
            self.current_utc = self.current_utc.replace(tzinfo=timezone.utc)
        self.current_utc = self.current_utc.astimezone(timezone.utc)

    def now_utc(self) -> datetime:
        return self.current_utc

    def monotonic(self) -> float:
        return self.current_monotonic

    def advance(self, seconds: float) -> None:
        self.current_utc += timedelta(seconds=float(seconds))
        self.current_monotonic += float(seconds)

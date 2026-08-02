"""Typed, privacy-aware activity snapshots for monitoring engines."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import threading
from typing import Any, Callable
from urllib.parse import urlsplit, urlunsplit


@dataclass(frozen=True)
class ActivitySnapshot:
    hwnd: int | None = None
    title: str = ""
    pid: int | None = None
    process_name: str = ""
    app_name: str = "Desktop"
    url: str | None = None
    source: str = "unknown"
    confidence: str = "low"
    captured_utc: str = ""
    errors: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_mapping(cls, raw: Any, *, source: str = "activity_probe") -> "ActivitySnapshot":
        errors: list[str] = []
        if not isinstance(raw, dict):
            errors.append("provider returned non-dict")
            raw = {}
        try:
            hwnd = int(raw["hwnd"]) if raw.get("hwnd") is not None else None
        except (TypeError, ValueError):
            hwnd = None
            errors.append("invalid hwnd")
        try:
            pid = int(raw["pid"]) if raw.get("pid") is not None else None
        except (TypeError, ValueError):
            pid = None
            errors.append("invalid pid")
        url = raw.get("url")
        if url:
            try:
                parts = urlsplit(str(url))
                url = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
            except ValueError:
                url = None
                errors.append("invalid url")
        confidence = "high" if hwnd is not None and url else "medium" if hwnd is not None and raw.get("title") else "low"
        return cls(
            hwnd=hwnd,
            title=str(raw.get("title") or ""),
            pid=pid,
            process_name=str(raw.get("process_name") or ""),
            app_name=str(raw.get("app_name") or "Desktop"),
            url=url,
            source=str(raw.get("source") or source),
            confidence=confidence,
            captured_utc=datetime.now(timezone.utc).isoformat(),
            errors=tuple(errors),
        )

    def is_fresh(self, max_age_seconds: float = 5.0, *, now: datetime | None = None) -> bool:
        try:
            captured = datetime.fromisoformat(self.captured_utc.replace("Z", "+00:00"))
            if captured.tzinfo is None:
                captured = captured.replace(tzinfo=timezone.utc)
            current = now or datetime.now(timezone.utc)
            age = (current.astimezone(timezone.utc) - captured.astimezone(timezone.utc)).total_seconds()
            return 0 <= age <= max(0.0, max_age_seconds)
        except (TypeError, ValueError, OverflowError):
            return False

    def as_mapping(self) -> dict[str, Any]:
        data = asdict(self)
        data["errors"] = list(self.errors)
        return data


def safe_activity_snapshot(provider: Callable[[], Any], *, timeout_seconds: float = 0.25) -> ActivitySnapshot:
    """Run an external activity provider without blocking the Tk owner thread."""
    result: dict[str, Any] = {}

    def invoke() -> None:
        try:
            result["value"] = provider()
        except Exception as exc:
            result["error"] = exc

    worker = threading.Thread(target=invoke, name="focuscheck-activity-provider", daemon=True)
    worker.start()
    worker.join(max(0.0, float(timeout_seconds)))
    now = datetime.now(timezone.utc).isoformat()
    if worker.is_alive():
        return ActivitySnapshot(captured_utc=now, errors=("provider timeout",))
    if "error" in result:
        exc = result["error"]
        return ActivitySnapshot(captured_utc=now, errors=(f"provider error: {type(exc).__name__}",))
    try:
        return ActivitySnapshot.from_mapping(result.get("value"))
    except Exception as exc:
        return ActivitySnapshot(captured_utc=now, errors=(f"provider error: {type(exc).__name__}",))

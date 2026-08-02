"""Typed, privacy-aware activity snapshots for monitoring engines."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import threading
from typing import Any, Callable
from urllib.parse import urlsplit, urlunsplit


_MAX_TITLE_LENGTH = 2048
_MAX_PROCESS_LENGTH = 512
_MAX_APP_LENGTH = 256
_MAX_SOURCE_LENGTH = 128
_MAX_URL_LENGTH = 4096


def _utc_now(clock=None) -> datetime:
    if clock is None:
        value = datetime.now(timezone.utc)
    elif callable(clock):
        value = clock()
    else:
        value = clock.now_utc()
    if not isinstance(value, datetime):
        raise TypeError("activity clock must return datetime")
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _bounded_text(value: Any, limit: int, field: str, errors: list[str]) -> str:
    text = str(value or "")
    if len(text) > limit:
        errors.append(f"{field} truncated")
        return text[:limit]
    return text


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
    def from_mapping(
        cls,
        raw: Any,
        *,
        source: str = "activity_probe",
        now: datetime | None = None,
    ) -> "ActivitySnapshot":
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
                if len(url) > _MAX_URL_LENGTH:
                    url = url[:_MAX_URL_LENGTH]
                    errors.append("url truncated")
            except ValueError:
                url = None
                errors.append("invalid url")
        confidence = "high" if hwnd is not None and url else "medium" if hwnd is not None and raw.get("title") else "low"
        return cls(
            hwnd=hwnd,
            title=_bounded_text(raw.get("title"), _MAX_TITLE_LENGTH, "title", errors),
            pid=pid,
            process_name=_bounded_text(raw.get("process_name"), _MAX_PROCESS_LENGTH, "process_name", errors),
            app_name=_bounded_text(raw.get("app_name") or "Desktop", _MAX_APP_LENGTH, "app_name", errors),
            url=url,
            source=_bounded_text(raw.get("source") or source, _MAX_SOURCE_LENGTH, "source", errors),
            confidence=confidence,
            captured_utc=(now or _utc_now()).isoformat(),
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


def safe_activity_snapshot(
    provider: Callable[[], Any],
    *,
    timeout_seconds: float = 0.25,
    clock=None,
) -> ActivitySnapshot:
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
    now = _utc_now(clock)
    if worker.is_alive():
        return ActivitySnapshot(captured_utc=now.isoformat(), errors=("provider timeout",))
    if "error" in result:
        exc = result["error"]
        return ActivitySnapshot(captured_utc=now.isoformat(), errors=(f"provider error: {type(exc).__name__}",))
    try:
        return ActivitySnapshot.from_mapping(result.get("value"), now=now)
    except Exception as exc:
        return ActivitySnapshot(captured_utc=now.isoformat(), errors=(f"provider error: {type(exc).__name__}",))

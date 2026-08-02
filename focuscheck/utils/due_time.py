"""Task due-time parsing helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def parse_due_time(text: str, *, now=None):
    """Parse minutes or local HH:MM text into a UTC ISO timestamp."""
    text = (text or "").strip()
    if not text:
        return None
    if now is None:
        now = datetime.now().astimezone()
    elif now.tzinfo is None:
        now = now.astimezone()

    try:
        minutes = max(1, int(text))
        return (now.astimezone(timezone.utc) + timedelta(minutes=minutes)).isoformat()
    except Exception:
        pass

    try:
        parts = text.split(":")
        if len(parts) != 2:
            return None
        hour = int(parts[0])
        minute = int(parts[1])
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            return None
        due_local = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if due_local < now:
            due_local = due_local + timedelta(days=1)
        return due_local.astimezone(timezone.utc).isoformat()
    except Exception:
        return None

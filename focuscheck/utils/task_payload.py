"""Shared task payload helpers for standalone and inline task UIs."""

from __future__ import annotations

from .due_time import parse_due_time


def build_task_payload(title, why="", consequences="", due_text="", *, now=None):
    """Build the normalized task payload used by task-entry surfaces."""
    return {
        "title": str(title or "").strip(),
        "why": str(why or "").strip(),
        "consequences": str(consequences or "").strip(),
        "due_utc": parse_due_time(due_text, now=now),
    }

"""Bounded Tk/thread resource leak smoke test for the verification runner."""

from __future__ import annotations

import json
import sys
import threading
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from focuscheck.ui.dialogs.gentle_reminder_dialog import GentleReminderDialog
from focuscheck.ui.dialogs.snooze_reminder_dialog import SnoozeReminderDialog


def _thread_snapshot() -> set[tuple[int | None, str, bool]]:
    return {
        (thread.ident, thread.name, thread.daemon)
        for thread in threading.enumerate()
        if not thread.daemon
    }


def _existing_children(root: tk.Misc) -> list[str]:
    children = []
    for child in root.winfo_children():
        try:
            if child.winfo_exists():
                children.append(str(child))
        except tk.TclError:
            pass
    return children


def main() -> int:
    before_threads = _thread_snapshot()
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print(json.dumps({"status": "failed", "error": f"Tk unavailable: {exc}"}))
        return 1

    root.withdraw()
    try:
        settings = {
            "always_on_top": False,
            "camera_feed_enabled": False,
            "biodata_enabled": False,
            "gentle_reminder_drift_enabled": False,
        }
        snooze = SnoozeReminderDialog(root, settings)
        snooze.withdraw()
        snooze._on_no()

        gentle = GentleReminderDialog(root, settings)
        gentle.withdraw()
        gentle._on_dismiss()
        root.update()

        children = _existing_children(root)
    finally:
        root.destroy()

    after_threads = _thread_snapshot()
    leaked_threads = sorted(after_threads - before_threads, key=str)
    payload = {
        "status": "passed" if not children and not leaked_threads else "failed",
        "remaining_tk_children": children,
        "leaked_non_daemon_threads": [list(item) for item in leaked_threads],
    }
    print(json.dumps(payload, sort_keys=True))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

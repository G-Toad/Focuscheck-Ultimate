"""Bounded Tk/thread resource leak smoke test for the verification runner."""

from __future__ import annotations

import json
import sys
import threading
import tkinter as tk
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from focuscheck.ui.dialogs.gentle_reminder_dialog import GentleReminderDialog
from focuscheck.ui.dialogs.snooze_reminder_dialog import SnoozeReminderDialog
from focuscheck.ui.dialogs.prompt_dialog import PromptDialog
from focuscheck.ui.dialogs.v2_prompt_dialog import V2PromptDialog
from focuscheck.settings.defaults import DEFAULT_SETTINGS


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

        prompt_settings = dict(DEFAULT_SETTINGS)
        prompt_settings.update({
            "always_on_top": False,
            "anti_habit_enabled": False,
            "camera_feed_enabled": False,
            "biodata_enabled": False,
            "encouragement_enabled": False,
            "focus_prompt_ask_doing": False,
            "focus_prompt_ask_benefits": False,
            "show_task_analytics": False,
        })
        for prompt_type, kwargs in (
            (PromptDialog, {}),
            (V2PromptDialog, {"activity_info": {}}),
        ):
            prompt = prompt_type(
                root,
                prompt_settings,
                lambda: None,
                datetime.now(),
                **kwargs,
            )
            prompt.withdraw()
            prompt._closed = True
            prompt._cleanup_camera_feed()
            prompt._cleanup_all_timers()
            prompt.destroy()

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

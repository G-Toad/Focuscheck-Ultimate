"""Keyboard behavior smoke tests for small Tk dialogs."""

from __future__ import annotations

import tkinter as tk
import unittest


def _make_root():
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        raise unittest.SkipTest(f"Tk display unavailable: {exc}") from exc
    root.withdraw()
    return root


class DialogKeyboardTests(unittest.TestCase):
    def test_task_entry_enter_submits(self):
        from focuscheck.ui.dialogs.task_entry_dialog import TaskEntryDialog

        root = _make_root()
        submitted = []
        try:
            dialog = TaskEntryDialog(root, submitted.append)
            dialog.withdraw()
            dialog.title_var.set("Write tests")

            result = dialog._on_return()
            root.update()

            self.assertEqual("break", result)
            self.assertEqual("Write tests", submitted[0]["title"])
            self.assertFalse(dialog.winfo_exists())
        finally:
            root.destroy()

    def test_task_change_enter_submits(self):
        from focuscheck.ui.dialogs.task_change_dialog import TaskChangeDialog

        root = _make_root()
        submitted = []
        try:
            dialog = TaskChangeDialog(root, submitted.append)
            dialog.withdraw()
            dialog.reason_var.set("Scope changed")
            dialog.title_var.set("New task")

            result = dialog._on_return()
            root.update()

            self.assertEqual("break", result)
            self.assertEqual("Scope changed", submitted[0]["reason"])
            self.assertEqual("New task", submitted[0]["new_task"]["title"])
            self.assertFalse(dialog.winfo_exists())
        finally:
            root.destroy()

    def test_snooze_prompt_can_disable_reason_and_exact_fields(self):
        from focuscheck.ui.dialogs.snooze_prompt_dialog import SnoozePromptDialog

        root = _make_root()
        submitted = []
        try:
            dialog = SnoozePromptDialog(
                root,
                {
                    "always_on_top": False,
                    "snooze_prompt_ask_reason": False,
                    "snooze_prompt_exact_enabled": False,
                    "snooze_prompt_validation_enabled": False,
                },
                on_submit=submitted.append,
            )
            dialog.withdraw()

            result = dialog._on_return(None)
            root.update()

            self.assertEqual("break", result)
            self.assertEqual("", submitted[0]["reason"])
            self.assertEqual("", submitted[0]["typed"])
            self.assertFalse(dialog.winfo_exists())
        finally:
            root.destroy()

    def test_v2_subpopup_return_confirms_only_for_high_severity(self):
        from focuscheck.ui.dialogs import v2_subpopup_dialog

        root = _make_root()
        events = []
        try:
            with unittest.mock.patch.object(v2_subpopup_dialog, "_get_virtual_screen_rect", return_value=(0, 0, 800, 600)):
                dialog = v2_subpopup_dialog.V2SubPopupDialog(
                    root,
                    "example.com",
                    severity=2,
                    on_yes=lambda: events.append("yes"),
                    on_no=lambda: events.append("no"),
                )
                dialog.withdraw()
                result = dialog._on_return()
                root.update()

                self.assertEqual("break", result)
                self.assertEqual(["yes"], events)
                self.assertFalse(dialog.winfo_exists())

                events.clear()
                dialog = v2_subpopup_dialog.V2SubPopupDialog(
                    root,
                    "example.com",
                    severity=1,
                    on_yes=lambda: events.append("yes"),
                    on_no=lambda: events.append("no"),
                )
                dialog.withdraw()
                result = dialog._on_return()
                root.update()

                self.assertEqual("break", result)
                self.assertEqual(["no"], events)
                self.assertFalse(dialog.winfo_exists())
        finally:
            root.destroy()

    def test_v2_subpopup_escape_declines(self):
        from focuscheck.ui.dialogs import v2_subpopup_dialog

        root = _make_root()
        events = []
        try:
            with unittest.mock.patch.object(v2_subpopup_dialog, "_get_virtual_screen_rect", return_value=(0, 0, 800, 600)):
                dialog = v2_subpopup_dialog.V2SubPopupDialog(
                    root,
                    "example.com",
                    severity=2,
                    on_yes=lambda: events.append("yes"),
                    on_no=lambda: events.append("no"),
                )
                dialog.withdraw()

                result = dialog._on_escape()
                root.update()

                self.assertEqual("break", result)
                self.assertEqual(["no"], events)
                self.assertFalse(dialog.winfo_exists())
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()

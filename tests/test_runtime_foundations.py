from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from focuscheck.utils.paths import get_app_paths
from focuscheck.utils.timers import TimerRegistry


class FakeScheduler:
    def __init__(self):
        self.next_id = 0
        self.callbacks = {}

    def after(self, _delay, callback):
        self.next_id += 1
        self.callbacks[self.next_id] = callback
        return self.next_id

    def after_cancel(self, callback_id):
        self.callbacks.pop(callback_id, None)

    def fire(self, callback_id):
        callback = self.callbacks.pop(callback_id)
        callback()


class RuntimeFoundationTests(unittest.TestCase):
    def test_prompt_coordinator_ignores_duplicate_and_stale_completion(self):
        from focuscheck.ui.prompt_coordinator import PromptCoordinator

        coordinator = PromptCoordinator()
        first = object()
        second = object()
        generation = coordinator.open(first)
        self.assertIsNone(coordinator.open(second))
        self.assertFalse(coordinator.complete(second))
        self.assertTrue(coordinator.complete(first, generation))
        self.assertFalse(coordinator.complete(first, generation))
        self.assertEqual(2, coordinator.open(second))

    def test_app_paths_are_complete_and_rooted(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = get_app_paths(temp_dir)
            self.assertEqual(Path(temp_dir), paths.root)
            self.assertEqual(paths.root, paths.settings.parent)
            self.assertEqual(paths.root / "supervisor.stop", paths.stop_request)
            self.assertEqual(paths.root / "diagnostic_bundle.zip", paths.diagnostic_bundle)

    def test_replacing_timer_makes_old_callback_stale(self):
        scheduler = FakeScheduler()
        registry = TimerRegistry(scheduler)
        calls = []
        registry.schedule("prompt", 1, lambda: calls.append("old"))
        old_id = next(iter(scheduler.callbacks))
        registry.schedule("prompt", 1, lambda: calls.append("new"))
        new_id = next(iter(scheduler.callbacks))
        scheduler.callbacks[old_id] = scheduler.callbacks.get(old_id, lambda: None)
        scheduler.fire(old_id)
        scheduler.fire(new_id)
        self.assertEqual(["new"], calls)

    def test_close_cancels_recurring_timer_and_rejects_new_work(self):
        scheduler = FakeScheduler()
        registry = TimerRegistry(scheduler)
        registry.schedule("heartbeat", 1, lambda: None, interval_ms=10)
        registry.close()
        self.assertTrue(registry.closed)
        self.assertFalse(registry.schedule("later", 1, lambda: None))
        self.assertFalse(scheduler.callbacks)

    def test_schedule_cancel_stress_leaves_no_owned_callbacks(self):
        scheduler = FakeScheduler()
        registry = TimerRegistry(scheduler)
        for index in range(1000):
            registry.schedule("stress", index, lambda: None)
            registry.cancel("stress")
        self.assertFalse(scheduler.callbacks)
        registry.close()

    def test_prompt_dialog_timer_registry_releases_fired_ids(self):
        from focuscheck.ui.dialogs.prompt_dialog import PromptDialog
        from focuscheck.ui.dialogs.v2_prompt_dialog import V2PromptDialog

        for dialog_type in (PromptDialog, V2PromptDialog):
            dialog = object.__new__(dialog_type)
            dialog._active_timers = set()
            dialog._closed = False
            scheduled = {}
            calls = []

            def after(_delay, callback):
                scheduled["callback"] = callback
                return "timer-1"

            dialog.after = after
            timer_id = dialog._schedule_timer(10, lambda: calls.append("fired"))

            self.assertEqual("timer-1", timer_id)
            self.assertIn(timer_id, dialog._active_timers)
            scheduled["callback"]()

            self.assertEqual(["fired"], calls)
            self.assertNotIn(timer_id, dialog._active_timers)

    def test_prompt_dialog_registry_invalidates_queued_callbacks_on_cleanup(self):
        from focuscheck.ui.dialogs.prompt_dialog import PromptDialog
        from focuscheck.ui.dialogs.v2_prompt_dialog import V2PromptDialog

        for dialog_type in (PromptDialog, V2PromptDialog):
            scheduler = FakeScheduler()
            dialog = object.__new__(dialog_type)
            dialog._active_timers = set()
            dialog._timer_names = {}
            dialog._timer_sequence = 0
            dialog._closed = False
            dialog._timers = TimerRegistry(scheduler)
            calls = []

            timer_id = dialog._schedule_timer(10, lambda: calls.append("stale"))
            callback = scheduler.callbacks[timer_id]
            dialog._cleanup_all_timers()
            callback()

            self.assertEqual([], calls)
            self.assertEqual(set(), dialog._active_timers)
            self.assertTrue(dialog._timers.closed)

    def test_phrase_challenge_closes_owned_timers(self):
        from focuscheck.ui.dialogs.phrase_acronym_dialog import PhraseAcronymDialog

        scheduler = FakeScheduler()
        dialog = object.__new__(PhraseAcronymDialog)
        dialog._closed = False
        dialog._timers = TimerRegistry(scheduler)

        self.assertTrue(dialog._schedule_timer("feedback", 10, lambda: None))
        self.assertTrue(scheduler.callbacks)
        dialog._close_timers()

        self.assertTrue(dialog._closed)
        self.assertTrue(dialog._timers.closed)
        self.assertFalse(scheduler.callbacks)

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

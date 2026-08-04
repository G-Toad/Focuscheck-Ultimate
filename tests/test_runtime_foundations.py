from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

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


class FailingScheduler(FakeScheduler):
    def __init__(self):
        super().__init__()
        self.fail_after = False

    def after(self, delay, callback):
        if self.fail_after:
            raise RuntimeError("scheduler unavailable")
        return super().after(delay, callback)


class RuntimeFoundationTests(unittest.TestCase):
    def test_sequential_phrase_advancement_uses_app_persistence_boundary(self):
        from focuscheck.ui.dialogs.prompt_dialog_mixins.anti_habit import AntiHabitMixin

        committed = {
            "custom_button_phrases_enabled": True,
            "study_phrase_mode": "sequential",
            "study_phrase_list": ["one", "two"],
            "study_phrase_index": 1,
        }
        persist = mock.Mock(return_value=type(
            "Result", (), {"durable_write": True, "committed_settings": committed}
        )())
        dialog = AntiHabitMixin.__new__(AntiHabitMixin)
        dialog.settings = dict(committed, study_phrase_index=0)
        dialog.persist_settings = persist

        self.assertEqual("one", dialog._get_phrase_for_button("study"))
        persist.assert_called_once()
        self.assertEqual(1, persist.call_args.args[0]["study_phrase_index"])
        self.assertEqual(1, dialog.settings["study_phrase_index"])

    def test_sequential_phrase_does_not_claim_index_advanced_after_failed_save(self):
        from focuscheck.ui.dialogs.prompt_dialog_mixins.anti_habit import AntiHabitMixin

        persist = mock.Mock(return_value=False)
        dialog = AntiHabitMixin.__new__(AntiHabitMixin)
        dialog.settings = {
            "custom_button_phrases_enabled": True,
            "study_phrase_mode": "sequential",
            "study_phrase_list": ["one", "two"],
            "study_phrase_index": 0,
        }
        dialog.persist_settings = persist

        self.assertEqual("one", dialog._get_phrase_for_button("study"))
        self.assertEqual(0, dialog.settings["study_phrase_index"])

    def test_prompt_coordinator_ignores_duplicate_and_stale_completion(self):
        from focuscheck.ui.prompt_coordinator import PromptCoordinator, PromptOutcome

        coordinator = PromptCoordinator()
        first = object()
        second = object()
        generation = coordinator.open(first)
        self.assertIsNone(coordinator.open(second))
        self.assertFalse(coordinator.complete(second))
        self.assertTrue(coordinator.complete(first, generation))
        self.assertEqual(PromptOutcome.COMPLETED, coordinator.last_outcome)
        self.assertFalse(coordinator.complete(first, generation))
        self.assertEqual(2, coordinator.open(second))
        self.assertTrue(coordinator.close(second, outcome=PromptOutcome.INTERRUPTED_BY_SHUTDOWN))
        self.assertEqual(PromptOutcome.INTERRUPTED_BY_SHUTDOWN, coordinator.last_outcome)

    def test_app_prompt_interruption_sources_map_to_typed_outcomes(self):
        from focuscheck.app import App
        from focuscheck.ui.prompt_coordinator import PromptOutcome

        self.assertEqual(PromptOutcome.INTERRUPTED_BY_PAUSE, App._prompt_interruption_outcome("pause"))
        self.assertEqual(PromptOutcome.INTERRUPTED_BY_PAUSE, App._prompt_interruption_outcome("snooze"))
        self.assertEqual(PromptOutcome.INTERRUPTED_BY_SETTINGS, App._prompt_interruption_outcome("settings"))
        self.assertEqual(PromptOutcome.INTERRUPTED_BY_SHUTDOWN, App._prompt_interruption_outcome("windows_end_session"))
        self.assertEqual(PromptOutcome.CANCELLED, App._prompt_interruption_outcome("unknown"))

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

    def test_timer_registry_emits_lifecycle_events_without_affecting_callbacks(self):
        scheduler = FakeScheduler()
        events = []
        registry = TimerRegistry(scheduler, event_sink=events.append)

        registry.schedule("prompt", 25, lambda: None, interval_ms=1000)
        registry.schedule("prompt", 50, lambda: None)
        registry.cancel("prompt")
        registry.close()

        self.assertEqual("schedule", events[0]["action"])
        self.assertEqual(25, events[0]["delay_ms"])
        self.assertEqual("cancel", events[1]["action"])
        self.assertEqual("schedule", events[2]["action"])
        self.assertEqual("cancel", events[3]["action"])
        self.assertEqual("close", events[4]["action"])

    def test_timer_registry_ignores_event_sink_failures(self):
        scheduler = FakeScheduler()

        def fail(_event):
            raise RuntimeError("ledger unavailable")

        registry = TimerRegistry(scheduler, event_sink=fail)
        self.assertTrue(registry.schedule("prompt", 1, lambda: None))
        self.assertTrue(registry.cancel("prompt"))
        registry.close()

    def test_close_cancels_recurring_timer_and_rejects_new_work(self):
        scheduler = FakeScheduler()
        registry = TimerRegistry(scheduler)
        registry.schedule("heartbeat", 1, lambda: None, interval_ms=10)
        registry.close()
        self.assertTrue(registry.closed)
        self.assertFalse(registry.schedule("later", 1, lambda: None))
        self.assertFalse(scheduler.callbacks)

    def test_guard_monitor_publishes_guard_transition_and_notifies_engine(self):
        from focuscheck.runtime.guard_monitor import GuardMonitorService
        from focuscheck.runtime.state import RuntimeStateCoordinator

        class Guard:
            paused = True

            def should_pause(self):
                return self.paused

        settings = {"manual_paused": False, "paused": False, "snooze_until_utc": ""}
        app = mock.Mock()
        app.guard = Guard()
        app._runtime_state = RuntimeStateCoordinator(settings)
        service = GuardMonitorService(app)

        self.assertTrue(service.refresh())
        app.guard.paused = False
        self.assertFalse(service.refresh())
        self.assertEqual(2, app._notify_engine_pause_state.call_count)
        self.assertEqual(
            [mock.call(source="system_guard"), mock.call(source="system_guard")],
            app._notify_engine_pause_state.call_args_list,
        )

    def test_guard_monitor_start_owns_pause_edge_timer_and_schedules_prompt_on_resume(self):
        from focuscheck.runtime.guard_monitor import GuardMonitorService

        scheduler = FakeScheduler()
        app = mock.Mock()
        app.guard.should_pause.side_effect = [True, False]
        app._timers = TimerRegistry(scheduler)
        service = GuardMonitorService(app)

        service.start()
        self.assertIn("pause-edge", service._app._timers._timers)
        callback_id = next(iter(scheduler.callbacks))
        scheduler.fire(callback_id)

        app._schedule_next.assert_called_once_with(0)
        self.assertEqual("pause-edge", service._app._timers._timers["pause-edge"].name)
        service._app._timers.close()

    def test_scheduler_failure_rolls_back_one_shot_timer_ownership(self):
        scheduler = FailingScheduler()
        registry = TimerRegistry(scheduler)
        scheduler.fail_after = True

        with self.assertRaisesRegex(RuntimeError, "scheduler unavailable"):
            registry.schedule("prompt", 1, lambda: None)

        self.assertIsNone(registry.callback_id("prompt"))
        self.assertFalse(registry._timers)

    def test_recurring_scheduler_failure_releases_timer_after_callback(self):
        scheduler = FailingScheduler()
        registry = TimerRegistry(scheduler)
        registry.schedule("heartbeat", 1, lambda: None, interval_ms=10)
        callback_id = next(iter(scheduler.callbacks))
        scheduler.fail_after = True

        with self.assertRaisesRegex(RuntimeError, "scheduler unavailable"):
            scheduler.fire(callback_id)

        self.assertIsNone(registry.callback_id("heartbeat"))
        self.assertFalse(registry._timers)

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

from __future__ import annotations

import unittest
from datetime import datetime, timezone, timedelta

from focuscheck.runtime.state import RuntimeStateCoordinator
from focuscheck.utils.clock import FakeClock
from focuscheck.runtime.lifecycle import LifecycleCoordinator, LifecyclePhase
from focuscheck.runtime.events import StructuredEventLedger


class RuntimeStateTests(unittest.TestCase):
    def test_transition_sink_records_metadata_and_not_settings_values(self):
        events = []
        state = RuntimeStateCoordinator(
            {"paused": False, "snooze_until_utc": ""},
            transition_sink=events.append,
        )
        self.assertTrue(state.set_manual_paused(True))
        self.assertFalse(state.begin_prompt())
        state.set_manual_paused(False)
        self.assertTrue(state.begin_prompt())
        state.end_prompt()
        self.assertTrue(events)
        self.assertEqual("manual_pause", events[0]["event"])
        self.assertNotIn("snooze_until_utc", events[0])

    def test_pause_save_failure_rolls_back_settings_and_state(self):
        settings = {"paused": False, "snooze_until_utc": ""}
        state = RuntimeStateCoordinator(settings, persist=lambda _settings: False)
        self.assertFalse(state.set_manual_paused(True))
        self.assertFalse(state.snapshot.manual_paused)
        self.assertFalse(settings["paused"])

    def test_snooze_is_distinct_from_manual_pause_and_effective_pause(self):
        settings = {"paused": False, "snooze_until_utc": ""}
        state = RuntimeStateCoordinator(settings)
        until = datetime.now(timezone.utc) + timedelta(minutes=5)
        self.assertTrue(state.set_snooze_until(until))
        self.assertFalse(state.snapshot.manual_paused)
        self.assertTrue(state.snapshot.effectively_paused)
        self.assertTrue(settings["paused"])
        state.clear_snooze()
        self.assertFalse(state.snapshot.effectively_paused)

    def test_expired_snooze_is_not_effectively_paused(self):
        settings = {"paused": False, "snooze_until_utc": "2000-01-01T00:00:00+00:00"}
        state = RuntimeStateCoordinator(settings)
        self.assertFalse(state.snapshot.snooze_active())
        self.assertFalse(state.snapshot.effectively_paused)

    def test_refresh_adopts_reloaded_settings_without_resetting_leases(self):
        state = RuntimeStateCoordinator({"paused": False, "snooze_until_utc": ""})
        self.assertTrue(state.begin_intervention())
        new_settings = {"paused": True, "snooze_until_utc": ""}
        state.refresh_from_settings(new_settings)
        self.assertIs(new_settings, state.settings)
        self.assertTrue(state.snapshot.manual_paused)
        self.assertTrue(state.snapshot.intervention_active)

    def test_guard_reason_preserves_manual_intent(self):
        settings = {"paused": True, "snooze_until_utc": ""}
        state = RuntimeStateCoordinator(settings)
        state.set_guard_reason("lock", True)
        state.set_guard_reason("lock", False)
        self.assertTrue(state.snapshot.manual_paused)
        self.assertTrue(state.snapshot.effectively_paused)

    def test_prompt_and_intervention_are_exclusive_and_shutdown_rejects_work(self):
        state = RuntimeStateCoordinator({"paused": False, "snooze_until_utc": ""})
        self.assertTrue(state.begin_prompt())
        self.assertFalse(state.begin_intervention())
        state.end_prompt()
        self.assertTrue(state.begin_intervention())
        self.assertTrue(state.request_shutdown())
        self.assertFalse(state.begin_prompt())

    def test_injected_clock_controls_snooze_expiry(self):
        clock = FakeClock(datetime(2030, 1, 1, tzinfo=timezone.utc))
        state = RuntimeStateCoordinator({"paused": False, "snooze_until_utc": ""}, clock=clock)
        state.set_snooze_until(datetime(2030, 1, 1, 0, 0, 10, tzinfo=timezone.utc))
        self.assertTrue(state.is_effectively_paused())
        clock.advance(10)
        self.assertFalse(state.is_effectively_paused())
        self.assertTrue(state.can_start_prompt())


class LifecycleCoordinatorTests(unittest.TestCase):
    def test_lifecycle_validates_phases_and_records_bounded_transitions(self):
        events = []
        lifecycle = LifecycleCoordinator(_sink=events.append)

        self.assertTrue(lifecycle.transition(LifecyclePhase.STARTING, reason="construct"))
        self.assertTrue(lifecycle.transition(LifecyclePhase.READY, reason="services_started"))
        self.assertFalse(lifecycle.transition(LifecyclePhase.CONSTRUCTING))
        self.assertTrue(lifecycle.begin_shutdown(reason="user_exit"))
        self.assertTrue(lifecycle.mark_stopped(reason="cleanup_complete"))
        self.assertFalse(lifecycle.mark_stopped())
        self.assertEqual("stopped", lifecycle.snapshot()["phase"])
        self.assertEqual(["starting", "ready", "stopping", "stopped"], [event["to"] for event in events])

    def test_lifecycle_failure_preserves_error_type(self):
        lifecycle = LifecycleCoordinator()
        lifecycle.transition(LifecyclePhase.STARTING)
        self.assertTrue(lifecycle.fail(RuntimeError("boom"), reason="startup_failure"))
        snapshot = lifecycle.snapshot()
        self.assertEqual("failed", snapshot["phase"])
        self.assertEqual("RuntimeError", snapshot["error_type"])


class StructuredEventLedgerTests(unittest.TestCase):
    def test_event_ledger_redacts_strings_and_rotates_within_bound(self):
        import json
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "structured_events.jsonl"
            ledger = StructuredEventLedger(path, max_bytes=4096)
            ledger.append("runtime", {"event": "state", "reason": "safe", "response": "private response"})
            for index in range(80):
                ledger.append("test", {"event": "tick", "index": index, "url": "https://example.invalid/private"})

            self.assertTrue(path.exists())
            self.assertLessEqual(path.stat().st_size, 4096)
            payload = json.loads(path.read_text(encoding="utf-8").splitlines()[-1])
            self.assertNotIn("private response", path.read_text(encoding="utf-8"))
            self.assertNotIn("example.invalid", path.read_text(encoding="utf-8"))
            self.assertEqual("test", payload["category"])

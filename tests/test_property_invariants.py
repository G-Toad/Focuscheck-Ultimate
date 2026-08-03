from __future__ import annotations

import random
import unittest
from datetime import datetime, timedelta, timezone


class PropertyInvariantTests(unittest.TestCase):
    def test_timer_generation_rejects_stale_callbacks_after_replacement(self):
        from focuscheck.utils.timers import TimerRegistry

        class Scheduler:
            def __init__(self):
                self.callbacks = {}
                self.next_id = 0

            def after(self, _delay, callback):
                self.next_id += 1
                self.callbacks[self.next_id] = callback
                return self.next_id

            def after_cancel(self, callback_id):
                self.callbacks.pop(callback_id, None)

        scheduler = Scheduler()
        registry = TimerRegistry(scheduler)
        calls = []
        registry.schedule("prompt", 0, lambda: calls.append("old"))
        old_callback = next(iter(scheduler.callbacks.values()))
        registry.schedule("prompt", 0, lambda: calls.append("new"))
        old_callback()
        next(iter(scheduler.callbacks.values()))()

        self.assertEqual(["new"], calls)

    def test_due_time_boundaries_are_utc_and_never_in_the_past(self):
        from focuscheck.utils.due_time import parse_due_time

        now = datetime(2030, 6, 1, 12, 0, tzinfo=timezone.utc)
        for text in ("1", "12:00", "23:59"):
            parsed = datetime.fromisoformat(parse_due_time(text, now=now))
            self.assertEqual(timezone.utc, parsed.tzinfo)
            self.assertGreaterEqual(parsed, now)
        self.assertIsNone(parse_due_time("24:00", now=now))
        self.assertIsNone(parse_due_time("not-a-time", now=now))

    def test_settings_migration_is_idempotent_for_legacy_shapes(self):
        from focuscheck.settings.migrations import migrate_settings

        cases = [
            {"snooze_until": "2030-01-01T00:00:00+00:00"},
            {"settings_schema_version": 1, "website_flags": {"domain": "example.com"}},
            {"settings_schema_version": 2, "future_key": {"preserve": True}},
        ]
        for raw in cases:
            migrated = migrate_settings(raw)
            self.assertEqual(migrated, migrate_settings(migrated), raw)

    def test_settings_validation_is_idempotent_for_generated_adversarial_inputs(self):
        from focuscheck.settings.manager import validate_settings

        cases = [
            {},
            {"interval_seconds": "1", "monitoring_mode": "invalid", "paused": "false"},
            {"website_flags": [{"domain": " HTTPS://Bücher.Example./ ", "enabled": "false"}]},
            {"manual_crop_zoom": "99", "manual_crop_anchor_mode": "invalid"},
            {"spam_banned_words": ["idk", 3, None], "spam_vague_words": "not-a-list"},
        ]
        for raw in cases:
            normalized = validate_settings(raw)
            self.assertEqual(normalized, validate_settings(normalized), raw)

    def test_domain_normalization_is_idempotent_for_valid_and_invalid_inputs(self):
        from focuscheck.settings.website_flags import normalize_website_domain

        values = [
            "example.com",
            " HTTPS://Bücher.Example./ ",
            "2001:db8::1",
            "[2001:db8::1]",
            "*.example.com",
            "example.com:443",
            "https://example.com/path",
            "",
        ]
        for value in values:
            normalized = normalize_website_domain(value)
            self.assertEqual(normalized, normalize_website_domain(normalized), value)

    def test_runtime_state_invariants_hold_across_generated_transition_sequence(self):
        from focuscheck.runtime.state import RuntimeStateCoordinator
        from focuscheck.utils.clock import FakeClock

        clock = FakeClock(datetime(2030, 1, 1, tzinfo=timezone.utc))
        settings = {"paused": False, "snooze_until_utc": ""}
        state = RuntimeStateCoordinator(settings, clock=clock)
        rng = random.Random(20260803)

        for _ in range(300):
            operation = rng.randrange(8)
            if operation == 0:
                state.set_manual_paused(bool(rng.randrange(2)))
            elif operation == 1:
                state.set_guard_reason(rng.choice(("lock", "idle", "sleep")), bool(rng.randrange(2)))
            elif operation == 2:
                state.set_snooze_until(clock.now_utc() + timedelta(seconds=rng.randrange(0, 120)))
            elif operation == 3:
                state.clear_snooze()
            elif operation == 4:
                state.begin_prompt()
            elif operation == 5:
                state.end_prompt()
            elif operation == 6:
                state.begin_intervention()
            else:
                state.end_intervention()
            clock.advance(rng.randrange(0, 5))

            self.assertFalse(state.snapshot.prompt_active and state.snapshot.intervention_active)
            self.assertEqual(
                settings["paused"],
                state.snapshot.manual_paused or state.snapshot.snooze_active(clock.now_utc()),
            )
            if state.snapshot.shutdown_requested:
                self.assertFalse(state.begin_prompt())
                self.assertFalse(state.begin_intervention())


if __name__ == "__main__":
    unittest.main()

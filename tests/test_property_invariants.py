from __future__ import annotations

import random
import unittest
from datetime import datetime, timedelta, timezone


class PropertyInvariantTests(unittest.TestCase):
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
                state.snapshot.manual_paused or bool(state.snapshot.snooze_until_utc),
            )
            if state.snapshot.shutdown_requested:
                self.assertFalse(state.begin_prompt())
                self.assertFalse(state.begin_intervention())


if __name__ == "__main__":
    unittest.main()

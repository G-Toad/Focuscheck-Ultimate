from __future__ import annotations

import unittest
from unittest import mock


class _Logger:
    def __init__(self):
        self.lines = []

    def log(self, message):
        self.lines.append(message)


class SupervisorCircuitBreakerTests(unittest.TestCase):
    def test_repeated_failures_open_and_expired_circuit_resets(self):
        from focuscheck_supervisor import (
            DEGRADED_COOLDOWN_SECONDS,
            FocusCheckSupervisor,
            MAX_RESTARTS_IN_WINDOW,
        )

        supervisor = FocusCheckSupervisor.__new__(FocusCheckSupervisor)
        supervisor._restart_history = []
        supervisor._degraded_until = 0.0
        supervisor.logger = _Logger()
        now = [100.0]
        with mock.patch("focuscheck_supervisor.time.monotonic", side_effect=lambda: now[0]):
            for _ in range(MAX_RESTARTS_IN_WINDOW):
                supervisor._record_restart_failure("test")
            self.assertTrue(supervisor._circuit_breaker_open())
            self.assertTrue(any("Circuit breaker open" in line for line in supervisor.logger.lines))
            now[0] += DEGRADED_COOLDOWN_SECONDS + 1
            self.assertFalse(supervisor._circuit_breaker_open())
            self.assertEqual([], supervisor._restart_history)

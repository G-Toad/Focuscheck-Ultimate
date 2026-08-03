from __future__ import annotations

import unittest
from unittest import mock


class LoggingSafetyTests(unittest.TestCase):
    def test_busy_log_rotation_does_not_raise(self):
        from focuscheck.utils.logging_utils import SafeRotatingFileHandler

        handler = SafeRotatingFileHandler.__new__(SafeRotatingFileHandler)
        handler.stream = object()
        with mock.patch("logging.handlers.RotatingFileHandler.doRollover", side_effect=OSError("file busy")):
            handler.doRollover()
        self.assertIsNotNone(handler.stream)

class DoctorTests(unittest.TestCase):
    def test_anomalies_are_bounded_and_snapshot_is_detached(self):
        import focuscheck.doctor as doctor

        original = list(doctor.ANOMALIES)
        try:
            doctor.ANOMALIES.clear()
            with mock.patch("focuscheck.doctor.get_logger"):
                for index in range(doctor.MAX_ANOMALIES + 25):
                    doctor.log_anomaly("test", str(index))
            self.assertEqual(doctor.MAX_ANOMALIES, len(doctor.ANOMALIES))
            snapshot = doctor.get_anomalies()
            snapshot.clear()
            self.assertEqual(doctor.MAX_ANOMALIES, len(doctor.ANOMALIES))
        finally:
            doctor.ANOMALIES[:] = original

    def test_unknown_setting_diagnostics_store_only_value_summary(self):
        from focuscheck.settings.manager import validate_settings
        import focuscheck.doctor as doctor

        original = list(doctor.ANOMALIES)
        secret = "private setting text that must not enter diagnostics"
        try:
            doctor.ANOMALIES.clear()
            with mock.patch("focuscheck.settings.manager.log_doctor_mode") as log_doctor:
                validate_settings({"plugin_private": secret})

            details = log_doctor.call_args.args[2]
            self.assertEqual("str", details["value_summary"]["type"])
            self.assertEqual(len(secret), details["value_summary"]["length"])
            self.assertNotIn(secret, repr(details))
        finally:
            doctor.ANOMALIES[:] = original

    def test_anomaly_snapshot_does_not_retain_private_message_or_details(self):
        import focuscheck.doctor as doctor

        original = list(doctor.ANOMALIES)
        secret = "private response text and https://secret.example/path"
        try:
            doctor.ANOMALIES.clear()
            with mock.patch("focuscheck.doctor.get_logger"):
                doctor.log_anomaly("response", secret, {"raw": secret})
            snapshot = doctor.get_anomalies()
            self.assertEqual(1, len(snapshot))
            self.assertNotIn(secret, repr(snapshot))
            self.assertEqual({"type", "length", "sha256"}, set(snapshot[0]["details"]))
            self.assertNotIn("secret.example", snapshot[0]["message"])
        finally:
            doctor.ANOMALIES[:] = original

from __future__ import annotations

import unittest
from unittest import mock


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

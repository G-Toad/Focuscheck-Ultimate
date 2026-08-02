from __future__ import annotations

import unittest
from datetime import datetime, timezone, timedelta

from focuscheck.monitoring.activity import ActivitySnapshot, safe_activity_snapshot


class ActivitySnapshotTests(unittest.TestCase):
    def test_normalization_redacts_query_and_fragment(self):
        snapshot = ActivitySnapshot.from_mapping({
            "hwnd": "12", "pid": "34", "title": "Browser",
            "url": "https://example.com/path?token=secret#fragment",
        })
        self.assertEqual(12, snapshot.hwnd)
        self.assertEqual("https://example.com/path", snapshot.url)
        self.assertEqual("high", snapshot.confidence)
        self.assertTrue(snapshot.is_fresh())

    def test_provider_errors_are_explicit(self):
        snapshot = safe_activity_snapshot(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        self.assertTrue(snapshot.errors)
        self.assertEqual("low", snapshot.confidence)

    def test_title_only_activity_is_medium_confidence(self):
        snapshot = ActivitySnapshot.from_mapping({"hwnd": 12, "title": "Browser"})
        self.assertEqual("medium", snapshot.confidence)

    def test_stale_snapshot_is_not_fresh(self):
        snapshot = ActivitySnapshot(captured_utc=(datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat())
        self.assertFalse(snapshot.is_fresh(max_age_seconds=5))

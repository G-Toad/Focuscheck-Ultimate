from __future__ import annotations

import unittest
from unittest import mock


class CdpProviderTests(unittest.TestCase):
    def test_discovery_stops_when_deadline_is_expired(self):
        from focuscheck.platform_specific import cdp_browser

        with mock.patch.object(cdp_browser, "_fetch_json") as fetch, \
                mock.patch.object(cdp_browser.time, "monotonic", return_value=100.0):
            self.assertEqual([], cdp_browser._discover_targets(timeout=0))
        fetch.assert_not_called()

    def test_discovery_passes_remaining_timeout_and_keeps_page_targets(self):
        from focuscheck.platform_specific import cdp_browser

        calls = []

        def fetch(url, timeout):
            calls.append((url, timeout))
            if url.endswith("/json/version"):
                return {"Browser": "Chrome"}
            return [
                {"type": "page", "title": "Example", "url": "https://example.com"},
                {"type": "service_worker", "title": "ignored"},
            ]

        with mock.patch.object(cdp_browser, "_CANDIDATE_PORTS", [9222]), \
                mock.patch.object(cdp_browser, "_fetch_json", side_effect=fetch):
            targets = cdp_browser._discover_targets(timeout=1.0)

        self.assertEqual(1, len(targets))
        self.assertEqual(9222, targets[0]["cdp_port"])
        self.assertLessEqual(max(timeout for _url, timeout in calls), 0.2)

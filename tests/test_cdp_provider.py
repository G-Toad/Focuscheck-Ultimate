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

    def test_discovery_bounds_targets_and_text_fields(self):
        from focuscheck.platform_specific import cdp_browser

        listing = [
            {"type": "page", "title": "t" * 3000, "url": "https://example.com/" + ("u" * 5000)}
            for _ in range(cdp_browser._MAX_TARGETS + 20)
        ]

        def fetch(url, timeout):
            if url.endswith("/json/version"):
                return {"Browser": "Chrome"}
            return listing

        with mock.patch.object(cdp_browser, "_CANDIDATE_PORTS", [9222]), \
                mock.patch.object(cdp_browser, "_fetch_json", side_effect=fetch):
            targets = cdp_browser._discover_targets(timeout=1.0)

        self.assertEqual(cdp_browser._MAX_TARGETS, len(targets))
        self.assertEqual(cdp_browser._MAX_TITLE_LENGTH, len(targets[0]["title"]))
        self.assertEqual(cdp_browser._MAX_URL_LENGTH, len(targets[0]["url"]))

    def test_list_tab_titles_bounds_and_deduplicates(self):
        from focuscheck.platform_specific import cdp_browser

        with mock.patch.object(cdp_browser, "get_cdp_targets", return_value=[
            {"title": "A" * 3000}, {"title": "A" * 3000}, {"title": "B"},
        ]):
            titles = cdp_browser.list_tab_titles()

        self.assertEqual(["A" * cdp_browser._MAX_TITLE_LENGTH, "B"], titles)

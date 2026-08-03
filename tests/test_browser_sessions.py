from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest


def _lz4_literal_block(payload: bytes) -> bytes:
    length = len(payload)
    token = min(length, 15) << 4
    result = bytearray([token])
    if length >= 15:
        remaining = length - 15
        while remaining >= 255:
            result.append(255)
            remaining -= 255
        result.append(remaining)
    result.extend(payload)
    return bytes(result)


class BrowserSessionTests(unittest.TestCase):
    def test_firefox_recovery_reads_selected_entry_per_window(self):
        from focuscheck.platform_specific.browser_sessions import parse_firefox_recovery

        payload = {
            "windows": [{
                "tabs": [{
                    "index": 2,
                    "entries": [
                        {"url": "https://old.example", "title": "Old"},
                        {"url": "https://current.example/path?private=1", "title": "Current"},
                    ],
                }]
            }]
        }
        data = b"mozLz40\x00" + _lz4_literal_block(json.dumps(payload).encode())
        tabs = parse_firefox_recovery(data)
        self.assertEqual(1, len(tabs))
        self.assertEqual("Current", tabs[0].title)
        self.assertEqual("https://current.example/path", tabs[0].url)
        self.assertEqual(0, tabs[0].window_index)

    def test_firefox_recovery_rejects_bad_header_or_payload(self):
        from focuscheck.platform_specific.browser_sessions import parse_firefox_recovery

        self.assertEqual([], parse_firefox_recovery(b"not-a-session"))
        self.assertEqual([], parse_firefox_recovery(b"mozLz40\x00\xff"))

    def test_chromium_session_extracts_only_bounded_http_urls(self):
        from focuscheck.platform_specific.browser_sessions import parse_chromium_session

        data = b"noise https://one.example/a\x00 https://one.example/a\x00 file:///private\x00"
        tabs = parse_chromium_session(data)
        self.assertEqual(["https://one.example/a"], [tab.url for tab in tabs])
        self.assertEqual("chromium-session", tabs[0].source)

    def test_collection_reads_only_declared_session_file(self):
        from focuscheck.platform_specific.browser_sessions import collect_browser_tabs

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "Current Tabs"
            path.write_bytes(b"https://session.example")
            tabs = collect_browser_tabs("chrome.exe", roots=[path])
        self.assertEqual(["https://session.example"], [tab.url for tab in tabs])

    def test_candidate_paths_normalize_executable_paths(self):
        from focuscheck.platform_specific.browser_sessions import _candidate_paths

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Google" / "Chrome" / "User Data"
            (root / "Default" / "Sessions").mkdir(parents=True)
            candidates = _candidate_paths(
                r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                {"LOCALAPPDATA": temp_dir},
            )
        self.assertTrue(candidates)
        self.assertTrue(any(str(path).endswith("Current Tabs") for path, _kind, _root in candidates))

    def test_collection_rejects_oversized_session_file(self):
        from focuscheck.platform_specific import browser_sessions

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "Current Tabs"
            path.write_bytes(b"x" * (browser_sessions._MAX_FILE_BYTES + 1))
            self.assertEqual([], browser_sessions.collect_browser_tabs("chrome.exe", roots=[path]))

    def test_collection_rejects_symlinked_profile_component(self):
        from focuscheck.platform_specific.browser_sessions import collect_browser_tabs

        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            real_profile = base / "real-profile"
            session = real_profile / "sessionstore-backups" / "recovery.jsonlz4"
            session.parent.mkdir(parents=True)
            payload = {"windows": [{"tabs": [{"entries": [{"url": "https://linked.example"}]}]}]}
            session.write_bytes(b"mozLz40\x00" + _lz4_literal_block(json.dumps(payload).encode()))
            profiles = base / "Mozilla" / "Firefox" / "Profiles"
            profiles.mkdir(parents=True)
            linked_profile = profiles / "linked-profile"
            try:
                os.symlink(real_profile, linked_profile, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("directory symlinks unavailable")
            tabs = collect_browser_tabs("firefox.exe", env={"APPDATA": temp_dir})
        self.assertEqual([], tabs)


if __name__ == "__main__":
    unittest.main()

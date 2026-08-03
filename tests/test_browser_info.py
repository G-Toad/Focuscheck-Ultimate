from __future__ import annotations

import unittest
from unittest import mock


class BrowserInfoTests(unittest.TestCase):
    def test_supported_process_matrix_is_case_insensitive(self):
        from focuscheck.platform_specific.browser_info import is_supported_browser

        supported = (
            "chrome.exe",
            "msedge.exe",
            "brave.exe",
            "opera.exe",
            "opera_gx.exe",
            "firefox.exe",
        )
        for process_name in supported:
            with self.subTest(process_name=process_name):
                self.assertTrue(is_supported_browser(process_name))
                self.assertTrue(is_supported_browser(process_name.upper()))

    def test_supported_process_matrix_accepts_windows_executable_paths(self):
        from focuscheck.platform_specific.browser_info import is_supported_browser

        self.assertTrue(is_supported_browser(r"C:\\Program Files\\Google\\Chrome\\chrome.exe"))
        self.assertTrue(is_supported_browser(r"C:/Program Files/Mozilla Firefox/firefox.exe"))
        self.assertFalse(is_supported_browser(r"C:\\Windows\\notepad.exe"))

    def test_unsupported_or_missing_processes_are_rejected(self):
        from focuscheck.platform_specific.browser_info import is_supported_browser

        for process_name in (None, "", "notepad.exe", "chrome", "chrome.exe.bak"):
            with self.subTest(process_name=process_name):
                self.assertFalse(is_supported_browser(process_name))

    def test_url_extraction_is_disabled_off_windows(self):
        from focuscheck.platform_specific import browser_info

        with mock.patch.object(browser_info.platform, "system", return_value="Linux"), \
                mock.patch.object(browser_info, "_try_uia_address_bar") as extract:
            self.assertIsNone(browser_info.try_get_browser_url(42, "chrome.exe"))
            extract.assert_not_called()

    def test_url_extraction_only_invokes_uia_for_supported_processes(self):
        from focuscheck.platform_specific import browser_info

        with mock.patch.object(browser_info.platform, "system", return_value="Windows"), \
                mock.patch.object(browser_info, "_try_uia_address_bar", return_value="https://example.test") as extract:
            self.assertEqual(
                "https://example.test",
                browser_info.try_get_browser_url(42, "MSEDGE.EXE"),
            )
            self.assertIsNone(browser_info.try_get_browser_url(42, "notepad.exe"))
            extract.assert_called_once_with(42)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import sys
import types
import time
import unittest
from unittest import mock


def _fake_comtypes(create_object):
    client = types.ModuleType("comtypes.client")
    client.CreateObject = create_object
    gen = types.ModuleType("comtypes.gen")
    uia = types.ModuleType("comtypes.gen.UIAutomationClient")
    uia.UIA_ControlTypePropertyId = 1
    uia.UIA_TabItemControlTypeId = 2
    uia.TreeScope_Subtree = 4
    gen.UIAutomationClient = uia
    root = types.ModuleType("comtypes")
    root.client = client
    return root, client, gen, uia


class BrowserTabsProviderTests(unittest.TestCase):
    def test_unsupported_platform_or_process_returns_no_tabs(self):
        from focuscheck.platform_specific import browser_tabs

        with mock.patch.object(browser_tabs.platform, "system", return_value="Linux"):
            self.assertEqual([], browser_tabs.try_list_browser_tabs(1, "chrome.exe"))
        with mock.patch.object(browser_tabs.platform, "system", return_value="Windows"), \
                mock.patch.object(browser_tabs, "is_supported_browser", return_value=False):
            self.assertEqual([], browser_tabs.try_list_browser_tabs(1, "notepad.exe"))

    def test_uia_tabs_are_bounded_and_deduplicated(self):
        from focuscheck.platform_specific import browser_tabs

        class Element:
            def __init__(self, name):
                self.CurrentName = name

        class Items:
            Length = 4

            def GetElement(self, index):
                return [Element("A"), Element("A"), Element("B"), Element("")][index]

        class Root:
            def FindAll(self, _scope, _condition):
                return Items()

        class Automation:
            def ElementFromHandle(self, _hwnd):
                return Root()

            def CreatePropertyCondition(self, *_args):
                return object()

        modules = _fake_comtypes(lambda _name: Automation())
        with mock.patch.object(browser_tabs.platform, "system", return_value="Windows"), \
                mock.patch.object(browser_tabs, "is_supported_browser", return_value=True), \
                mock.patch.dict(sys.modules, {
                    "comtypes": modules[0],
                    "comtypes.client": modules[1],
                    "comtypes.gen": modules[2],
                    "comtypes.gen.UIAutomationClient": modules[3],
                }), \
                mock.patch.object(browser_tabs, "list_tab_titles", return_value=["fallback"]):
            self.assertEqual(["A", "B"], browser_tabs.try_list_browser_tabs(42, "chrome.exe"))

    def test_uia_failure_falls_back_to_cdp_and_total_failure_is_empty(self):
        from focuscheck.platform_specific import browser_tabs

        modules = _fake_comtypes(mock.Mock(side_effect=RuntimeError("uia unavailable")))
        with mock.patch.object(browser_tabs.platform, "system", return_value="Windows"), \
                mock.patch.object(browser_tabs, "is_supported_browser", return_value=True), \
                mock.patch.dict(sys.modules, {
                    "comtypes": modules[0],
                    "comtypes.client": modules[1],
                    "comtypes.gen": modules[2],
                    "comtypes.gen.UIAutomationClient": modules[3],
                }), \
                mock.patch.object(browser_tabs, "list_tab_titles", return_value=["CDP tab"]):
            self.assertEqual(["CDP tab"], browser_tabs.try_list_browser_tabs(42, "chrome.exe"))

        with mock.patch.object(browser_tabs.platform, "system", return_value="Windows"), \
                mock.patch.object(browser_tabs, "is_supported_browser", return_value=True), \
                mock.patch.dict(sys.modules, {
                    "comtypes": modules[0],
                    "comtypes.client": modules[1],
                    "comtypes.gen": modules[2],
                    "comtypes.gen.UIAutomationClient": modules[3],
                }), \
                mock.patch.object(browser_tabs, "list_tab_titles", side_effect=RuntimeError("cdp unavailable")):
            self.assertEqual([], browser_tabs.try_list_browser_tabs(42, "chrome.exe"))

    def test_hung_uia_falls_back_without_blocking_or_starting_another_worker(self):
        from focuscheck.platform_specific import browser_tabs

        started = __import__("threading").Event()
        release = __import__("threading").Event()

        def hung(_hwnd):
            started.set()
            release.wait(2)
            return []

        with mock.patch.object(browser_tabs.platform, "system", return_value="Windows"), \
                mock.patch.object(browser_tabs, "is_supported_browser", return_value=True), \
                mock.patch.object(browser_tabs, "_list_uia_tabs", side_effect=hung), \
                mock.patch.object(browser_tabs, "list_tab_titles", return_value=["CDP tab"]):
            try:
                started_at = time.monotonic()
                self.assertEqual(["CDP tab"], browser_tabs.try_list_browser_tabs(42, "chrome.exe", timeout=0.05))
                self.assertLess(time.monotonic() - started_at, 0.5)
                self.assertEqual(["CDP tab"], browser_tabs.try_list_browser_tabs(43, "chrome.exe", timeout=0.05))
            finally:
                release.set()
                deadline = time.monotonic() + 0.5
                while browser_tabs._UIA_IN_FLIGHT and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertFalse(browser_tabs._UIA_IN_FLIGHT)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
from datetime import datetime, timezone, timedelta
from unittest import mock

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


class WindowsActivityProbeTests(unittest.TestCase):
    def test_process_probe_declares_pointer_and_buffer_signatures(self):
        from focuscheck.platform_specific import activity_probe

        class Api:
            def __init__(self, callback):
                self.callback = callback
                self.argtypes = None
                self.restype = None

            def __call__(self, *args):
                return self.callback(*args)

        handle = object()

        def query(_handle, _flags, buffer, size):
            buffer.value = r"C:\Windows\FocusCheck.exe"
            size._obj.value = len(buffer.value)
            return 1

        kernel32 = type("Kernel32", (), {})()
        kernel32.OpenProcess = Api(lambda *_args: handle)
        kernel32.QueryFullProcessImageNameW = Api(query)
        kernel32.CloseHandle = Api(lambda _handle: 1)
        windll = type("Windll", (), {"kernel32": kernel32})()

        with mock.patch.object(activity_probe.ctypes, "windll", windll):
            self.assertEqual(r"C:\Windows\FocusCheck.exe", activity_probe._get_process_path(42))

        self.assertEqual([activity_probe.wintypes.DWORD, activity_probe.wintypes.BOOL, activity_probe.wintypes.DWORD],
                         kernel32.OpenProcess.argtypes)
        self.assertIs(activity_probe.wintypes.HANDLE, kernel32.OpenProcess.restype)
        self.assertIs(activity_probe.wintypes.BOOL, kernel32.QueryFullProcessImageNameW.restype)
        self.assertIs(activity_probe.wintypes.BOOL, kernel32.CloseHandle.restype)

    def test_foreground_probe_declares_user32_signatures(self):
        from focuscheck.platform_specific import activity_probe

        class Api:
            def __init__(self):
                self.argtypes = None
                self.restype = None

            def __call__(self, *_args):
                return 0

        user32 = type("User32", (), {
            name: Api() for name in (
                "GetWindowTextLengthW", "GetWindowTextW", "GetClassNameW",
                "GetForegroundWindow", "GetWindowThreadProcessId",
            )
        })()
        activity_probe._configure_user32(user32)

        self.assertEqual([activity_probe.wintypes.HWND], user32.GetWindowTextLengthW.argtypes)
        self.assertIs(activity_probe.wintypes.HWND, user32.GetForegroundWindow.restype)
        self.assertEqual(
            [activity_probe.wintypes.HWND, activity_probe.ctypes.POINTER(activity_probe.wintypes.DWORD)],
            user32.GetWindowThreadProcessId.argtypes,
        )

    def test_window_enumeration_declares_user32_and_psapi_signatures(self):
        from focuscheck.platform_specific import window_enumeration

        class Api:
            def __init__(self):
                self.argtypes = None
                self.restype = None

        user32 = type("User32", (), {
            name: Api() for name in (
                "GetWindowTextLengthW", "GetWindowTextW", "GetWindowThreadProcessId",
                "IsWindowVisible", "EnumWindows", "PostMessageW", "IsWindow",
            )
        })()
        kernel32 = type("Kernel32", (), {"OpenProcess": Api(), "CloseHandle": Api()})()
        psapi = type("Psapi", (), {"GetModuleBaseNameW": Api()})()

        window_enumeration._configure_user32(user32)
        window_enumeration._configure_process_api(kernel32, psapi)

        self.assertIs(window_enumeration.wintypes.BOOL, user32.EnumWindows.restype)
        self.assertIs(window_enumeration.wintypes.HANDLE, kernel32.OpenProcess.restype)
        self.assertEqual(
            [window_enumeration.wintypes.HANDLE, window_enumeration.wintypes.HANDLE,
             window_enumeration.wintypes.LPWSTR, window_enumeration.wintypes.DWORD],
            psapi.GetModuleBaseNameW.argtypes,
        )

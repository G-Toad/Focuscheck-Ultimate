"""Settings window save-payload tests."""

from __future__ import annotations

import contextlib
import tkinter as tk
import unittest
from unittest import mock


def _make_root():
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        raise unittest.SkipTest(f"Tk display unavailable: {exc}") from exc
    root.withdraw()
    return root


class SettingsWindowSaveTests(unittest.TestCase):
    def _save_window_payload(self, root, settings):
        from focuscheck.ui.windows import AdvancedSettingsWindow

        saved_payloads = []
        window = AdvancedSettingsWindow(root, settings, saved_payloads.append)
        window.withdraw()
        return window, saved_payloads

    def test_save_payload_clamps_active_settings_and_preserves_unedited_keys(self):
        from focuscheck.settings.defaults import DEFAULT_SETTINGS

        root = _make_root()
        try:
            draft = dict(DEFAULT_SETTINGS)
            draft.update({
                "paused": True,
                "snooze_until_utc": "2030-01-01T00:00:00+00:00",
                "plugin_future_key": {"enabled": True},
            })
            window, saved_payloads = self._save_window_payload(root, draft)

            window.interval_var.set("1")
            window.ui_scale_percent_var.set("999")
            window.pause_poll_var.set("0")
            window.tray_start_stop_enabled_var.set(False)
            window.tray_settings_enabled_var.set(False)
            window.tray_exit_enabled_var.set(False)
            window.webhook_var.set("https://example.invalid/hook")

            with mock.patch("focuscheck.settings.manager.save_settings") as save_settings:
                window._save()

            self.assertEqual(1, len(saved_payloads))
            payload = saved_payloads[0]
            save_settings.assert_called_once_with(payload)
            self.assertEqual(10, payload["interval_seconds"])
            self.assertEqual(150, payload["ui_scale_percent"])
            self.assertEqual(2, payload["pause_poll_interval_seconds"])
            self.assertFalse(payload["tray_start_stop_enabled"])
            self.assertFalse(payload["tray_settings_button_enabled"])
            self.assertFalse(payload["tray_exit_button_enabled"])
            self.assertEqual("", payload["webhook_url"])
            self.assertTrue(payload["paused"])
            self.assertEqual("2030-01-01T00:00:00+00:00", payload["snooze_until_utc"])
            self.assertEqual({"enabled": True}, payload["plugin_future_key"])
        finally:
            with contextlib.suppress(tk.TclError):
                root.destroy()

    def test_save_payload_round_trips_representative_active_tabs(self):
        from focuscheck.settings.defaults import DEFAULT_SETTINGS

        root = _make_root()
        try:
            window, saved_payloads = self._save_window_payload(root, DEFAULT_SETTINGS)

            # General tab
            window.monitoring_mode_var.set("v2")
            window.topmost_var.set(False)
            window.center_var.set(False)
            window.pause_on_lock_var.set(False)

            # Validation, challenges, and spam tabs
            window.challenge_enabled_var.set(False)
            window.challenge_min_words_var.set("7")
            window.challenge_allow_skip_var.set(True)
            window.spam_enabled_var.set(False)
            window.spam_min_vowel_var.set(0.25)

            # Website flags tab
            window.website_flags_list = [
                {
                    "domain": "reddit.com",
                    "enabled": True,
                    "severity": 3,
                    "cooldown_minutes": 4,
                }
            ]

            # Alerts tab
            window.overdrive_stage4_enabled_var.set(False)
            window.overdrive_stage5_enabled_var.set(False)
            window.audio_alerts_enabled_var.set(True)
            window.audio_alarm_pattern_var.set("urgent")

            # Behaviour tab
            window.v2_focus_requires_enter_var.set(True)
            window.show_time_info_var.set(False)
            window.tasks_change_counts_as_fail_var.set(True)
            window.camera_feed_enabled_var.set(False)
            window.biodata_title_var.set("QA Title")

            with mock.patch("focuscheck.settings.manager.save_settings") as save_settings:
                window._save()

            self.assertEqual(1, len(saved_payloads))
            payload = saved_payloads[0]
            save_settings.assert_called_once_with(payload)

            expected = {
                "monitoring_mode": "v2",
                "always_on_top": False,
                "center_on_show": False,
                "pause_on_lock": False,
                "challenge_system_enabled": False,
                "challenge_min_words": 7,
                "challenge_allow_skip": True,
                "spam_detection_enabled": False,
                "spam_min_vowel_ratio": 0.25,
                "website_flags": window.website_flags_list,
                "overdrive_stage4_enabled": False,
                "overdrive_stage5_enabled": False,
                "audio_alerts_enabled": True,
                "audio_alarm_pattern": "urgent",
                "v2_focus_requires_enter": True,
                "show_time_info": False,
                "tasks_change_counts_as_fail": True,
                "camera_feed_enabled": False,
                "biodata_title": "QA Title",
            }
            for key, value in expected.items():
                self.assertEqual(value, payload[key], key)
        finally:
            with contextlib.suppress(tk.TclError):
                root.destroy()


if __name__ == "__main__":
    unittest.main()

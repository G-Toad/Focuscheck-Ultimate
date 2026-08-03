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
    def test_crop_editor_does_not_apply_memory_changes_when_save_fails(self):
        from focuscheck.ui.crop_adjustment_window import CropAdjustmentWindow

        updated = []
        editor = CropAdjustmentWindow.__new__(CropAdjustmentWindow)
        editor.settings = {"manual_crop_zoom": 2.0}
        editor.original_settings = {"manual_crop_zoom": 1.0}
        editor.on_settings_updated = updated.append
        editor.has_unsaved_changes = True
        editor.title = mock.Mock()

        with mock.patch("focuscheck.ui.crop_adjustment_window.save_settings", return_value=False), \
                mock.patch("focuscheck.ui.crop_adjustment_window.messagebox.showerror") as showerror:
            self.assertFalse(editor._save_to_disk())

        self.assertEqual(1.0, editor.original_settings["manual_crop_zoom"])
        self.assertEqual([], updated)
        showerror.assert_called_once()

    def test_crop_editor_applies_memory_changes_after_durable_save(self):
        from focuscheck.ui.crop_adjustment_window import CropAdjustmentWindow

        updated = []
        editor = CropAdjustmentWindow.__new__(CropAdjustmentWindow)
        editor.settings = {"manual_crop_zoom": 2.0}
        editor.original_settings = {"manual_crop_zoom": 1.0}
        editor.on_settings_updated = updated.append
        editor.has_unsaved_changes = True
        editor.title = mock.Mock()

        with mock.patch("focuscheck.ui.crop_adjustment_window.save_settings", return_value=True):
            self.assertTrue(editor._save_to_disk())

        self.assertEqual(2.0, editor.original_settings["manual_crop_zoom"])
        self.assertEqual([{"manual_crop_zoom": 2.0}], updated)

    def test_crop_editor_uses_injected_persistence_and_committed_crop(self):
        from focuscheck.ui.crop_adjustment_window import CropAdjustmentWindow

        updated = []
        committed = {"manual_crop_zoom": 1.5, "manual_crop_box_width": 640, "settings_revision": 4}
        persist = mock.Mock(return_value=type(
            "Result", (), {"durable_write": True, "committed_settings": committed}
        )())
        editor = CropAdjustmentWindow.__new__(CropAdjustmentWindow)
        editor.settings = {"manual_crop_zoom": 2.0, "manual_crop_box_width": 800}
        editor.original_settings = {"manual_crop_zoom": 1.0, "manual_crop_box_width": 400}
        editor.on_settings_updated = updated.append
        editor.persist_settings = persist
        editor.has_unsaved_changes = True
        editor.title = mock.Mock()

        self.assertTrue(editor._save_to_disk())
        persist.assert_called_once()
        self.assertEqual(2.0, persist.call_args.args[0]["manual_crop_zoom"])
        self.assertEqual(1.5, editor.original_settings["manual_crop_zoom"])
        self.assertEqual([{"manual_crop_zoom": 1.5, "manual_crop_box_width": 640}], updated)

    def test_camera_editor_does_not_apply_memory_changes_when_save_fails(self):
        from focuscheck.ui.settings_tabs.behavior_tab import BehaviorTabMixin

        owner = type("Owner", (), {"settings": {"camera_manual_brightness": 0.5}})()
        with mock.patch("focuscheck.ui.settings_tabs.behavior_tab.save_settings", return_value=False), \
                mock.patch("focuscheck.ui.settings_tabs.behavior_tab.messagebox.showerror") as showerror:
            BehaviorTabMixin._save_camera_adjustment_settings(
                owner, {"camera_manual_brightness": 0.9}
            )

        self.assertEqual(0.5, owner.settings["camera_manual_brightness"])
        showerror.assert_called_once()

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

    def test_schema_generated_controls_round_trip_and_preserve_invalid_json(self):
        from focuscheck.settings.defaults import DEFAULT_SETTINGS

        root = _make_root()
        try:
            window, saved_payloads = self._save_window_payload(root, DEFAULT_SETTINGS)
            window._schema_settings.variables["overlays_enabled"].set(False)
            window._schema_settings.variables["gentle_reminder_interval"].set(25)
            window._schema_settings.variables["camera_manual_brightness"].set(0.8)
            window._schema_settings.variables["spam_banned_words"].set("not-json")

            with mock.patch("focuscheck.settings.manager.save_settings"):
                window._save()

            payload = saved_payloads[0]
            self.assertFalse(payload["overlays_enabled"])
            self.assertEqual(25, payload["gentle_reminder_interval"])
            self.assertEqual(0.8, payload["camera_manual_brightness"])
            self.assertEqual(DEFAULT_SETTINGS["spam_banned_words"], payload["spam_banned_words"])
        finally:
            with contextlib.suppress(tk.TclError):
                root.destroy()

    def test_every_schema_generated_control_round_trips_defaults(self):
        from focuscheck.settings.defaults import DEFAULT_SETTINGS
        from focuscheck.ui.schema_controls import SCHEMA_CONTROL_KEYS

        root = _make_root()
        try:
            window, saved_payloads = self._save_window_payload(root, DEFAULT_SETTINGS)
            self.assertEqual(set(SCHEMA_CONTROL_KEYS), set(window._schema_settings.variables))
            self.assertEqual(set(SCHEMA_CONTROL_KEYS), set(window._schema_settings._widgets))

            with mock.patch("focuscheck.settings.manager.save_settings") as save_settings:
                window._save()

            payload = saved_payloads[0]
            save_settings.assert_called_once_with(payload)
            for key in SCHEMA_CONTROL_KEYS:
                self.assertIn(key, payload)
                self.assertEqual(DEFAULT_SETTINGS[key], payload[key], key)
        finally:
            with contextlib.suppress(tk.TclError):
                root.destroy()

    def test_composed_window_uses_app_persistence_callback(self):
        from focuscheck.settings.defaults import DEFAULT_SETTINGS
        from focuscheck.ui.windows import AdvancedSettingsWindow

        root = _make_root()
        try:
            saved = []
            committed = dict(DEFAULT_SETTINGS)
            committed["settings_revision"] = 7
            persist = mock.Mock(return_value=type(
                "Result", (), {"durable_write": True, "committed_settings": committed}
            )())
            window = AdvancedSettingsWindow(
                root,
                DEFAULT_SETTINGS,
                saved.append,
                persist_settings=persist,
            )
            window.withdraw()
            with mock.patch("focuscheck.settings.manager.save_settings", side_effect=AssertionError("UI repository bypass")):
                window._save()
            persist.assert_called_once()
            self.assertEqual(7, saved[0]["settings_revision"])
        finally:
            with contextlib.suppress(tk.TclError):
                root.destroy()

    def test_camera_settings_use_injected_persistence_and_committed_values(self):
        from focuscheck.ui.settings_tabs.behavior_tab import BehaviorTabMixin

        committed = {"camera_manual_brightness": 0.75, "settings_revision": 11}
        persist = mock.Mock(return_value=type(
            "Result", (), {"durable_write": True, "committed_settings": committed}
        )())
        owner = BehaviorTabMixin.__new__(BehaviorTabMixin)
        owner.settings = {"camera_manual_brightness": 0.5, "settings_revision": 10}
        owner.persist_settings = persist

        with mock.patch("focuscheck.ui.settings_tabs.behavior_tab.messagebox.showinfo"):
            owner._save_camera_adjustment_settings({"camera_manual_brightness": 0.9})

        persist.assert_called_once()
        self.assertEqual(0.9, persist.call_args.args[0]["camera_manual_brightness"])
        self.assertEqual(committed, owner.settings)

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

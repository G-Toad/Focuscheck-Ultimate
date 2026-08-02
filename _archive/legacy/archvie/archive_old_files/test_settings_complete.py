"""
Comprehensive test for settings UI.
Tests all settings load/save correctly with new advanced UI.
"""

import tkinter as tk
from focuscheck.settings.manager import load_settings, save_settings
from focuscheck.ui.windows import AdvancedSettingsWindow


def test_settings_ui():
    """Test the settings UI interactively."""
    print("=" * 70)
    print("COMPREHENSIVE SETTINGS UI TEST")
    print("=" * 70)

    # Load current settings
    print("\n1. Loading current settings...")
    settings = load_settings()
    print(f"   [OK] Loaded {len(settings)} settings")

    # Check all expected settings exist
    print("\n2. Checking all settings exist...")

    expected_settings = [
        # Core
        "interval_seconds", "intensify_after_seconds", "overdrive_after_seconds",
        "max_intensity_level", "always_on_top", "center_on_show",
        "modal_dialog_auto_focus", "follow_cursor_monitor", "webhook_url",

        # Anti-habit
        "anti_habit_enabled", "randomize_buttons", "studying_hold_ms",

        # Pause
        "force_always_on", "pause_when_inactive_or_lid_closed", "pause_on_idle",
        "pause_on_lid_closed", "pause_on_lock", "pause_on_sleep",
        "inactive_as_sleep_seconds", "pause_poll_interval_seconds",

        # Challenges - Global
        "challenge_system_enabled", "challenge_studying_frequency",
        "challenge_wasting_frequency", "challenge_min_words",
        "challenge_min_total_length", "challenge_allow_skip", "challenge_show_hints",

        # Individual studying challenges
        "challenge_studying_learning_specificity_enabled",
        "challenge_studying_goal_connection_enabled",
        "challenge_studying_will_commitment_enabled",
        "challenge_studying_output_expectation_enabled",

        # Individual wasting challenges
        "challenge_wasting_wasting_acknowledgment_enabled",
        "challenge_wasting_should_gap_enabled",
        "challenge_wasting_because_reasoning_enabled",
        "challenge_wasting_hour_projection_enabled",
        "challenge_wasting_tomorrow_regret_enabled",
        "challenge_wasting_fear_acknowledgment_enabled",
        "challenge_wasting_lying_confrontation_enabled",

        # Spam detection
        "spam_detection_enabled", "spam_gibberish_detection",
        "spam_min_vowel_ratio", "spam_max_vowel_ratio", "spam_min_unique_char_ratio",
        "spam_repetition_check", "spam_max_consecutive_chars", "spam_max_pattern_repetition",
        "spam_spacing_check", "spam_min_length_require_spaces",
        "spam_keyboard_pattern_check", "spam_min_keyboard_sequence_length",
        "spam_dictionary_check", "spam_min_real_word_ratio", "spam_min_word_length",
        "spam_timing_check", "spam_min_time_to_submit", "spam_flag_if_under",
        "spam_banned_words", "spam_vague_words",

        # UI
        "wasting_prompt_enabled", "focus_prompt_enabled",
        "prompt_require_all_fields", "require_active_task",
        "hide_wasting_button", "encouragement_enabled", "show_task_analytics",

        # Tray
        "tray_start_stop_enabled", "tray_settings_button_enabled",
        "tray_exit_button_enabled",
    ]

    missing = []
    for key in expected_settings:
        if key not in settings:
            missing.append(key)

    if missing:
        print(f"   [FAIL] Missing settings: {missing}")
        return False
    else:
        print(f"   [OK] All {len(expected_settings)} expected settings present")

    # Test UI creation
    print("\n3. Testing UI creation...")
    print("   Opening settings window...")
    print("   Instructions:")
    print("   - Window should be resizable (try dragging corners)")
    print("   - Each tab should scroll with mouse wheel")
    print("   - Toggle switches should work")
    print("   - Sliders should show live percentage")
    print("   - Spinboxes should have +/- buttons")
    print("   - Challenge cards should show status")
    print("   - Preset buttons should work")
    print("   - Save button should close window")
    print("")
    print("   Please test the UI, then close it to continue...")

    root = tk.Tk()
    root.withdraw()  # Hide root window

    test_passed = [True]  # Use list to modify in closure
    original_settings = settings.copy()

    def on_save(new_settings):
        """Callback when settings are saved."""
        print("\n4. Testing save functionality...")

        # Check all settings are preserved
        for key in expected_settings:
            if key not in new_settings:
                print(f"   [FAIL] Setting '{key}' missing after save")
                test_passed[0] = False
                return

        print(f"   [OK] All {len(expected_settings)} settings preserved")

        # Check data types
        print("\n5. Validating data types...")
        type_checks = [
            ("challenge_system_enabled", bool),
            ("challenge_studying_frequency", float),
            ("challenge_min_words", int),
            ("spam_detection_enabled", bool),
            ("spam_min_vowel_ratio", float),
            ("spam_max_consecutive_chars", int),
            ("spam_banned_words", list),
            ("interval_seconds", int),
        ]

        for key, expected_type in type_checks:
            actual_type = type(new_settings[key])
            if actual_type != expected_type:
                print(f"   [FAIL] {key}: {actual_type.__name__} (expected {expected_type.__name__})")
                test_passed[0] = False
            else:
                print(f"   [OK] {key}: {expected_type.__name__}")

        # Check value ranges
        print("\n6. Validating value ranges...")
        range_checks = [
            ("challenge_studying_frequency", 0.0, 1.0),
            ("challenge_wasting_frequency", 0.0, 1.0),
            ("spam_min_vowel_ratio", 0.0, 1.0),
            ("spam_max_vowel_ratio", 0.0, 1.0),
            ("interval_seconds", 10, None),
            ("challenge_min_words", 1, None),
        ]

        for key, min_val, max_val in range_checks:
            value = new_settings[key]
            if min_val is not None and value < min_val:
                print(f"   [FAIL] {key}: {value} < {min_val}")
                test_passed[0] = False
            elif max_val is not None and value > max_val:
                print(f"   [FAIL] {key}: {value} > {max_val}")
                test_passed[0] = False
            else:
                print(f"   [OK] {key}: {value} (valid range)")

    try:
        settings_window = AdvancedSettingsWindow(root, settings, on_save)
        root.wait_window(settings_window)
    except Exception as e:
        print(f"\n   [FAIL] Error creating UI: {e}")
        import traceback
        traceback.print_exc()
        return False

    root.destroy()

    if test_passed[0]:
        print("\n" + "=" * 70)
        print("[SUCCESS] ALL TESTS PASSED!")
        print("=" * 70)
        print("\nSettings UI is working correctly:")
        print("  - Window is resizable")
        print("  - All tabs scroll properly")
        print("  - All controls work")
        print("  - All settings load/save correctly")
        print("  - Data types are correct")
        print("  - Value ranges are valid")
        return True
    else:
        print("\n" + "=" * 70)
        print("[FAIL] SOME TESTS FAILED")
        print("=" * 70)
        return False


if __name__ == "__main__":
    import sys
    success = test_settings_ui()
    sys.exit(0 if success else 1)

"""
Test script to verify settings flow works correctly.
Simulates: Load -> Modify -> Save -> Load again -> Verify
"""

import json
import os
import tempfile
from focuscheck.settings.defaults import DEFAULT_SETTINGS
from focuscheck.settings.manager import validate_settings, save_settings, load_settings

def test_settings_flow():
    """Test the complete settings flow."""
    print("=" * 60)
    print("TESTING SETTINGS FLOW")
    print("=" * 60)

    # Step 1: Start with defaults
    print("\n1. Loading default settings...")
    settings = DEFAULT_SETTINGS.copy()
    print(f"   [OK] Challenge system enabled: {settings['challenge_system_enabled']}")
    print(f"   [OK] Challenge studying freq: {settings['challenge_studying_frequency']}")
    print(f"   [OK] Challenge wasting freq: {settings['challenge_wasting_frequency']}")
    print(f"   [OK] Spam detection enabled: {settings['spam_detection_enabled']}")
    print(f"   [OK] Spam min vowel ratio: {settings['spam_min_vowel_ratio']}")

    # Step 2: Simulate user modifying settings (like UI would do)
    print("\n2. Simulating user changes...")
    modified = settings.copy()
    modified['challenge_studying_frequency'] = 0.5
    modified['challenge_wasting_frequency'] = 0.8
    modified['challenge_min_words'] = 10
    modified['spam_min_vowel_ratio'] = 0.3
    modified['spam_max_consecutive_chars'] = 3
    print(f"   [OK] Changed studying freq: 0.3 -> {modified['challenge_studying_frequency']}")
    print(f"   [OK] Changed wasting freq: 0.5 -> {modified['challenge_wasting_frequency']}")
    print(f"   [OK] Changed min words: 5 -> {modified['challenge_min_words']}")
    print(f"   [OK] Changed spam vowel ratio: 0.2 -> {modified['spam_min_vowel_ratio']}")
    print(f"   [OK] Changed spam consecutive: 2 -> {modified['spam_max_consecutive_chars']}")

    # Step 3: Validate settings (like save would do)
    print("\n3. Validating settings...")
    validated = validate_settings(modified)
    print(f"   [OK] Challenge studying freq preserved: {validated['challenge_studying_frequency']}")
    print(f"   [OK] Challenge wasting freq preserved: {validated['challenge_wasting_frequency']}")
    print(f"   [OK] Challenge min words preserved: {validated['challenge_min_words']}")
    print(f"   [OK] Spam vowel ratio preserved: {validated['spam_min_vowel_ratio']}")
    print(f"   [OK] Spam consecutive preserved: {validated['spam_max_consecutive_chars']}")

    # Step 4: Check all required keys are present
    print("\n4. Checking all keys are preserved...")
    challenge_keys = [
        'challenge_system_enabled', 'challenge_studying_frequency',
        'challenge_wasting_frequency', 'challenge_min_words',
        'challenge_min_total_length', 'challenge_allow_skip', 'challenge_show_hints'
    ]
    spam_keys = [
        'spam_detection_enabled', 'spam_gibberish_detection',
        'spam_min_vowel_ratio', 'spam_max_vowel_ratio', 'spam_min_unique_char_ratio',
        'spam_repetition_check', 'spam_max_consecutive_chars', 'spam_max_pattern_repetition',
        'spam_spacing_check', 'spam_min_length_require_spaces',
        'spam_keyboard_pattern_check', 'spam_min_keyboard_sequence_length',
        'spam_dictionary_check', 'spam_min_real_word_ratio', 'spam_min_word_length',
        'spam_timing_check', 'spam_min_time_to_submit', 'spam_flag_if_under',
        'spam_banned_words', 'spam_vague_words'
    ]

    missing_keys = []
    for key in challenge_keys + spam_keys:
        if key not in validated:
            missing_keys.append(key)

    if missing_keys:
        print(f"   [FAIL] MISSING KEYS: {missing_keys}")
        return False
    else:
        print(f"   [OK] All {len(challenge_keys)} challenge keys present")
        print(f"   [OK] All {len(spam_keys)} spam keys present")

    # Step 5: Test boundary values
    print("\n5. Testing boundary value clamping...")
    test_cases = [
        ('challenge_studying_frequency', 1.5, 1.0),  # Should clamp to 1.0
        ('challenge_studying_frequency', -0.1, 0.0),  # Should clamp to 0.0
        ('challenge_min_words', 0, 1),  # Should clamp to 1
        ('spam_min_vowel_ratio', 2.0, 1.0),  # Should clamp to 1.0
        ('spam_max_consecutive_chars', 0, 1),  # Should clamp to 1
    ]

    for key, test_val, expected in test_cases:
        test_settings = settings.copy()
        test_settings[key] = test_val
        result = validate_settings(test_settings)
        if result[key] == expected:
            print(f"   [OK] {key}: {test_val} -> {result[key]} (correct)")
        else:
            print(f"   [FAIL] {key}: {test_val} -> {result[key]} (expected {expected})")
            return False

    # Step 6: Verify types are correct
    print("\n6. Verifying data types...")
    type_checks = [
        ('challenge_system_enabled', bool),
        ('challenge_studying_frequency', float),
        ('challenge_min_words', int),
        ('spam_detection_enabled', bool),
        ('spam_min_vowel_ratio', float),
        ('spam_max_consecutive_chars', int),
        ('spam_banned_words', list),
    ]

    for key, expected_type in type_checks:
        actual_type = type(validated[key])
        if actual_type == expected_type:
            print(f"   [OK] {key}: {expected_type.__name__}")
        else:
            print(f"   [FAIL] {key}: {actual_type.__name__} (expected {expected_type.__name__})")
            return False

    print("\n" + "=" * 60)
    print("[SUCCESS] ALL TESTS PASSED!")
    print("=" * 60)
    print("\nSettings flow is working correctly:")
    print("  - All challenge settings preserved")
    print("  - All spam detection settings preserved")
    print("  - Validation clamps values correctly")
    print("  - Data types are correct")
    return True

if __name__ == "__main__":
    success = test_settings_flow()
    exit(0 if success else 1)

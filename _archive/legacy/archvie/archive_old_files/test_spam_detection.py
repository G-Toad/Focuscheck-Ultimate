#!/usr/bin/env python
"""Test spam detection mechanisms."""

import sys
sys.path.insert(0, '.')

from focuscheck.ui.dialogs.spam_detection import SpamDetector

# Test cases
test_cases = [
    # (text, time_elapsed, should_pass, description)
    ("I'm studying calculus derivatives chapter 7", 5.0, True, "Valid study answer"),
    ("asdf", 1.0, False, "Keyboard pattern + too fast"),
    ("aaaaaaaaaaaa", 2.0, False, "Character repetition"),
    ("thisisaverylongtextwithoutanyspaces", 3.0, False, "No spaces in long text"),
    ("qwerty", 2.0, False, "Keyboard row pattern"),
    ("I'm learning Spanish verb conjugations", 4.0, True, "Valid with real words"),
    ("stuff things whatever", 1.5, False, "Vague words + too fast"),
    ("idk", 1.0, False, "Banned word"),
    ("bcdfghjklmnp", 2.0, False, "Too few vowels (gibberish)"),
    ("aeiouaeiouae", 2.0, False, "Too many vowels"),
    ("working on essay", 5.0, True, "Short but valid"),
    ("asdfasdfasdf", 1.0, False, "Repeated pattern"),
    ("I am genuinely working on my physics homework problem set 3", 6.0, True, "Detailed valid answer"),
]

def main():
    detector = SpamDetector()

    print("="*80)
    print("SPAM DETECTION TEST SUITE")
    print("="*80)
    print()

    passed = 0
    failed = 0

    for text, time_elapsed, should_pass, description in test_cases:
        result = detector.detect(text, time_elapsed)
        is_spam = result['is_spam']

        # Check if result matches expectation
        if (not is_spam) == should_pass:
            status = "[PASS]"
            passed += 1
        else:
            status = "[FAIL]"
            failed += 1

        print(f"{status} | {description}")
        print(f"  Text: '{text}'")
        print(f"  Time: {time_elapsed}s")
        print(f"  Spam: {is_spam} (confidence: {result['confidence']:.2f})")
        if result['reasons']:
            print(f"  Reasons: {', '.join(result['reasons'])}")
        print()

    print("="*80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("="*80)

    # Test specific heuristics
    print("\n" + "="*80)
    print("HEURISTIC TESTS")
    print("="*80)
    print()

    # Test gibberish
    print("1. Gibberish Detection:")
    for text in ["bcdfghjklmnp", "aeiouaeiou", "hello world"]:
        is_gibberish, reason = detector._check_gibberish(text)
        print(f"  '{text}': {is_gibberish} {f'({reason})' if reason else ''}")
    print()

    # Test repetition
    print("2. Repetition Detection:")
    for text in ["aaa", "aa", "asdfasdfasdf", "hello"]:
        has_rep, reason = detector._check_repetition(text)
        print(f"  '{text}': {has_rep} {f'({reason})' if reason else ''}")
    print()

    # Test keyboard patterns
    print("3. Keyboard Pattern Detection:")
    for text in ["qwerty", "asdf", "zxcv", "hello", "1234"]:
        has_pattern, reason = detector._check_keyboard_patterns(text)
        print(f"  '{text}': {has_pattern} {f'({reason})' if reason else ''}")
    print()

    # Test dictionary
    print("4. Dictionary Validation:")
    for text in ["hello world", "asdfgh jklmn", "I am studying", "xyz abc"]:
        fails_dict, reason = detector._check_dictionary(text)
        print(f"  '{text}': fails={fails_dict} {f'({reason})' if reason else ''}")
    print()

    # Test timing
    print("5. Timing Validation:")
    for text, time_elapsed in [("short", 1.0), ("normal answer", 3.0), ("detailed response", 5.0)]:
        is_fast, reason = detector._check_timing(time_elapsed, text)
        print(f"  '{text}' in {time_elapsed}s: {is_fast} {f'({reason})' if reason else ''}")
    print()

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())

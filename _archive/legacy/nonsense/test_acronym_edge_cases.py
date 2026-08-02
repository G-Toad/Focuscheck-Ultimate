"""
Test script for phrase acronym challenge edge cases.

Tests the enhanced regex pattern that handles:
- Contractions, possessives, hyphenated words
- Leading/trailing apostrophes
- Complex edge cases
"""

import re


def extract_acronym(phrase):
    """Extract acronym from phrase using the new enhanced pattern."""
    # Enhanced regex pattern
    pattern = r"'?[A-Za-z]+(?:[-'][A-Za-z]+)*'?"
    words = re.findall(pattern, phrase)

    # Clean up matched words
    cleaned_words = []
    for word in words:
        cleaned = word.strip("'-")
        if cleaned:
            cleaned_words.append(cleaned)

    # Extract first letter of each word
    acronym = ''.join(word[0].upper() for word in cleaned_words if word)
    return acronym, words, cleaned_words


def test_cases():
    """Run comprehensive test cases."""
    tests = [
        # Format: (phrase, expected_acronym, description)

        # Basic contractions
        ("don't worry", "DW", "Basic contraction"),
        ("you're awesome", "YA", "Basic contraction"),
        ("I'm ready", "IR", "Basic contraction"),
        ("it's time", "IT", "Basic contraction"),
        ("we'll see", "WS", "Basic contraction"),
        ("they've gone", "TG", "Basic contraction"),

        # Leading apostrophes
        ("'Twas the night", "TTN", "Leading apostrophe"),
        ("'tis the season", "TTS", "Leading apostrophe lowercase"),
        ("rock 'n' roll", "RNR", "Rock 'n' roll special case"),

        # Trailing apostrophes
        ("I'm goin' home", "IGH", "Trailing apostrophe (goin')"),
        ("Keep singin' loud", "KSL", "Trailing apostrophe (singin')"),
        ("They're dancin' now", "TDN", "Trailing apostrophe (dancin')"),

        # Hyphenated words (treated as ONE word - takes first letter only)
        ("self-esteem is important", "SII", "Hyphenated word (self-esteem as ONE)"),
        ("mother-in-law arrived", "MA", "Multi-hyphenated word (mother-in-law as ONE)"),
        ("twenty-one days", "TD", "Hyphenated number word (twenty-one as ONE)"),
        ("up-to-date information", "UI", "Multi-hyphenated phrase (up-to-date as ONE)"),

        # Complex contractions (treated as ONE word - takes first letter only)
        ("y'all ready", "YR", "Y'all contraction"),
        ("y'all'd've loved it", "YLI", "Complex contraction (y'all'd've as ONE word)"),
        ("shouldn't've done that", "SDT", "Double contraction"),

        # Possessives
        ("John's book is here", "JBIH", "Possessive (John's)"),
        ("students' books are there", "SBAT", "Plural possessive"),
        ("the cat's meow", "TCM", "Possessive with article"),

        # Mixed punctuation
        ("Hello, world!", "HW", "Comma and exclamation"),
        ("What? Really?", "WR", "Question marks"),
        ("Let's go!", "LG", "Contraction with exclamation"),

        # Numbers (should be skipped)
        ("I have 3 cats", "IHC", "Number in phrase"),
        ("21st century fox", "SCF", "Number at start"),

        # Complex real-world phrases
        ("I don't think self-esteem is important", "IDTSII", "Complex real phrase"),
        ("You're goin' to mother-in-law's house", "YGTMH", "Multiple edge cases"),
        ("'Twas a twenty-one gun salute, y'all", "TATGSY", "Ultimate edge case (twenty-one=T, y'all=Y)"),

        # Edge cases
        ("", "", "Empty phrase"),
        ("!!!", "", "Only punctuation"),
        ("Hello", "H", "Single word"),
        ("  spaces  everywhere  ", "SE", "Extra spaces"),
    ]

    print("=" * 80)
    print("PHRASE ACRONYM CHALLENGE - EDGE CASE TESTING")
    print("=" * 80)
    print()

    passed = 0
    failed = 0

    for phrase, expected, description in tests:
        acronym, raw_words, cleaned_words = extract_acronym(phrase)
        status = "[PASS]" if acronym == expected else "[FAIL]"

        if acronym == expected:
            passed += 1
        else:
            failed += 1

        print(f"{status} | {description}")
        print(f"  Phrase: \"{phrase}\"")
        print(f"  Expected: {expected}")
        print(f"  Got: {acronym}")

        if acronym != expected:
            print(f"  Raw matches: {raw_words}")
            print(f"  Cleaned words: {cleaned_words}")

        print()

    print("=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 80)

    return failed == 0


if __name__ == "__main__":
    success = test_cases()

    if success:
        print("\n[SUCCESS] All tests passed! The acronym extraction is working correctly.")
    else:
        print("\n[FAILURE] Some tests failed. Review the output above for details.")

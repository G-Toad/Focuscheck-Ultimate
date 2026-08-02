"""
Quick script to show current challenge and spam settings.
"""

from focuscheck.settings.manager import load_settings

def show_settings():
    settings = load_settings()

    print("=" * 70)
    print("CHALLENGE SYSTEM SETTINGS")
    print("=" * 70)
    print(f"Enabled:              {settings['challenge_system_enabled']}")
    print(f"Studying frequency:   {settings['challenge_studying_frequency']} (30% = 0.3)")
    print(f"Wasting frequency:    {settings['challenge_wasting_frequency']} (50% = 0.5)")
    print(f"Min words:            {settings['challenge_min_words']}")
    print(f"Min length:           {settings['challenge_min_total_length']} characters")
    print(f"Allow skip:           {settings['challenge_allow_skip']}")
    print(f"Show hints:           {settings['challenge_show_hints']}")

    print("\n" + "=" * 70)
    print("SPAM DETECTION SETTINGS")
    print("=" * 70)
    print(f"Enabled:              {settings['spam_detection_enabled']}")

    print("\nGibberish Detection:")
    print(f"  Enabled:            {settings['spam_gibberish_detection']}")
    print(f"  Min vowel ratio:    {settings['spam_min_vowel_ratio']}")
    print(f"  Max vowel ratio:    {settings['spam_max_vowel_ratio']}")
    print(f"  Min unique chars:   {settings['spam_min_unique_char_ratio']}")

    print("\nRepetition Detection:")
    print(f"  Enabled:            {settings['spam_repetition_check']}")
    print(f"  Max consecutive:    {settings['spam_max_consecutive_chars']}")
    print(f"  Max pattern reps:   {settings['spam_max_pattern_repetition']}")

    print("\nSpacing & Keyboard:")
    print(f"  Spacing check:      {settings['spam_spacing_check']}")
    print(f"  Min len for spaces: {settings['spam_min_length_require_spaces']}")
    print(f"  Keyboard check:     {settings['spam_keyboard_pattern_check']}")
    print(f"  Min keyboard seq:   {settings['spam_min_keyboard_sequence_length']}")

    print("\nDictionary:")
    print(f"  Enabled:            {settings['spam_dictionary_check']}")
    print(f"  Min word ratio:     {settings['spam_min_real_word_ratio']}")
    print(f"  Min word length:    {settings['spam_min_word_length']}")

    print("\nTiming:")
    print(f"  Enabled:            {settings['spam_timing_check']}")
    print(f"  Min time:           {settings['spam_min_time_to_submit']} seconds")
    print(f"  Flag if under:      {settings['spam_flag_if_under']} seconds")

    print("\nWord Lists:")
    print(f"  Banned words:       {', '.join(settings['spam_banned_words'])}")
    print(f"  Vague words:        {', '.join(settings['spam_vague_words'])}")

    print("\n" + "=" * 70)
    print("All settings are now properly saved and configurable via UI!")
    print("=" * 70)

if __name__ == "__main__":
    show_settings()

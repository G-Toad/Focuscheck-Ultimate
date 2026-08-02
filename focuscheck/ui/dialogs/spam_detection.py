"""
Advanced spam and gibberish detection for dialog responses.

Provides configurable heuristics to detect low-effort, automated, or
dishonest responses to reflection prompts.
"""

import time
import string


class SpamDetector:
    """
    Multi-layered spam detection using various heuristics.

    Detects:
    - Gibberish (vowel ratio, character diversity)
    - Character repetition patterns
    - Keyboard proximity patterns (qwerty, asdf)
    - Missing spaces in long text
    - Dictionary validation failures
    - Timing anomalies
    """

    def __init__(self, config=None):
        """
        Initialize spam detector with configuration.

        Args:
            config: Dictionary of detection settings. If None, uses defaults.
        """
        self.config = config or self._default_config()
        self._load_dictionary()

    def _default_config(self):
        """Default spam detection configuration."""
        return {
            # Gibberish detection
            "enable_gibberish_detection": True,
            "min_vowel_ratio": 0.15,  # Lowered from 0.2
            "max_vowel_ratio": 0.75,  # Raised from 0.7
            "min_unique_char_ratio": 0.3,  # Lowered from 0.4

            # Character repetition
            "enable_repetition_check": True,
            "max_consecutive_chars": 3,  # Raised from 2: "aaa" ok, "aaaa" not ok
            "max_pattern_repetition": 4,  # Raised from 3: "asdfasdf" ok, "asdfasdfasdfasdf" not ok

            # Spacing
            "enable_spacing_check": True,
            "min_length_require_spaces": 20,  # Raised from 15

            # Keyboard patterns
            "enable_keyboard_pattern_check": True,
            "min_keyboard_sequence_length": 5,  # Raised from 4

            # Dictionary validation
            "enable_dictionary_check": True,
            "min_real_word_ratio": 0.5,  # Lowered from 0.6 (60%) to 50%
            "min_word_length": 2,  # Words must be at least 2 chars

            # Timing
            "enable_timing_check": True,
            "min_time_to_submit": 2,  # Lowered from 3 seconds
            "flag_if_under": 1,  # Lowered from 2 - only flag extremely fast responses

            # Banned/vague words
            "banned_words": ["idk", "dunno", "meh", "whatever"],
            "vague_words": ["stuff", "things", "something", "nothing"],
        }

    def _load_dictionary(self):
        """Load dictionary for word validation."""
        # Basic English dictionary - common words
        # In production, could load from file or use enchant/nltk
        self._dictionary = set([
            # Common words for basic validation
            "the", "be", "to", "of", "and", "a", "in", "that", "have", "i",
            "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
            "this", "but", "his", "by", "from", "they", "we", "say", "her", "she",
            "or", "an", "will", "my", "one", "all", "would", "there", "their", "what",
            "so", "up", "out", "if", "about", "who", "get", "which", "go", "me",
            "when", "make", "can", "like", "time", "no", "just", "him", "know", "take",
            "people", "into", "year", "your", "good", "some", "could", "them", "see", "other",
            "than", "then", "now", "look", "only", "come", "its", "over", "think", "also",
            "back", "after", "use", "two", "how", "our", "work", "first", "well", "way",
            "even", "new", "want", "because", "any", "these", "give", "day", "most", "us",
            # Task/study related
            "study", "studying", "learn", "learning", "read", "reading", "write", "writing",
            "homework", "assignment", "exam", "test", "quiz", "practice", "work", "working",
            "focus", "focused", "focusing", "thinking", "understand", "understanding",
            "chapter", "book", "page", "problem", "question", "answer", "solve", "solving",
            "math", "science", "history", "english", "biology", "chemistry", "physics",
            # Programming/tech related
            "python", "java", "javascript", "code", "coding", "program", "programming",
            "computer", "software", "data", "algorithm", "function", "class", "method",
            "debug", "debugging", "compile", "run", "execute", "build", "test", "testing",
            "tutorial", "lesson", "course", "exercise", "project", "app", "application",
            # Procrastination related
            "youtube", "twitter", "reddit", "instagram", "facebook", "tiktok", "social",
            "media", "video", "videos", "game", "games", "gaming", "phone", "scroll",
            "scrolling", "browse", "browsing", "watch", "watching", "waste", "wasting",
            "procrastinate", "procrastinating", "distracted", "distraction", "avoid",
            "avoiding", "delay", "delaying", "postpone", "postponing",
            # Emotions/states
            "tired", "anxious", "anxiety", "stressed", "stress", "worried", "worry",
            "scared", "afraid", "fear", "guilt", "guilty", "frustrated", "frustration",
            "overwhelmed", "bored", "boring", "lazy", "unmotivated", "motivated",
            "productive", "unproductive", "focused", "unfocused", "concentrated",
            # Actions
            "need", "should", "must", "have", "doing", "done", "finish", "finished",
            "start", "started", "continue", "continuing", "stop", "stopped", "try",
            "trying", "attempt", "attempting", "complete", "completed",
        ])

        # Add common contractions and variations
        contractions = ["im", "id", "ill", "ive", "dont", "cant", "wont", "isnt", "arent",
                       "wasnt", "werent", "hasnt", "havent", "didnt", "doesnt"]
        self._dictionary.update(contractions)

    def detect(self, text, time_elapsed=None):
        """
        Run all enabled detection heuristics.

        Args:
            text: The text to analyze
            time_elapsed: Optional time in seconds since dialog was shown

        Returns:
            dict: {
                'is_spam': bool,
                'confidence': float (0.0-1.0),
                'reasons': list of strings,
                'suggestions': list of strings
            }
        """
        text = (text or "").strip()
        reasons = []
        confidence = 0.0

        if not text:
            return {
                'is_spam': True,
                'confidence': 1.0,
                'reasons': ["Empty response"],
                'suggestions': ["Please provide an answer"]
            }

        # Check 1: Gibberish detection
        if self.config["enable_gibberish_detection"]:
            is_gibberish, reason = self._check_gibberish(text)
            if is_gibberish:
                reasons.append(reason)
                confidence += 0.35

        # Check 2: Character repetition
        if self.config["enable_repetition_check"]:
            has_repetition, reason = self._check_repetition(text)
            if has_repetition:
                reasons.append(reason)
                confidence += 0.25

        # Check 3: Spacing issues
        if self.config["enable_spacing_check"]:
            has_spacing_issue, reason = self._check_spacing(text)
            if has_spacing_issue:
                reasons.append(reason)
                confidence += 0.15

        # Check 4: Keyboard patterns
        if self.config["enable_keyboard_pattern_check"]:
            has_pattern, reason = self._check_keyboard_patterns(text)
            if has_pattern:
                reasons.append(reason)
                confidence += 0.30

        # Check 5: Dictionary validation
        if self.config["enable_dictionary_check"]:
            fails_dict, reason = self._check_dictionary(text)
            if fails_dict:
                reasons.append(reason)
                confidence += 0.20

        # Check 6: Timing
        if self.config["enable_timing_check"] and time_elapsed is not None:
            is_too_fast, reason = self._check_timing(time_elapsed, text)
            if is_too_fast:
                reasons.append(reason)
                confidence += 0.25

        # Check 7: Banned/vague words
        vague_reason = self._check_vague_words(text)
        if vague_reason:
            reasons.append(vague_reason)
            confidence += 0.10

        # Cap confidence at 1.0
        confidence = min(confidence, 1.0)

        # Generate suggestions
        suggestions = self._generate_suggestions(reasons)

        return {
            'is_spam': confidence > 0.5,  # 50% threshold
            'confidence': confidence,
            'reasons': reasons,
            'suggestions': suggestions
        }

    def _check_gibberish(self, text):
        """Check for gibberish using vowel ratio and character diversity."""
        text_lower = text.lower()
        letters_only = ''.join(c for c in text_lower if c.isalpha())

        if not letters_only:
            return True, "No actual letters detected"

        # Vowel ratio check
        vowels = sum(1 for c in letters_only if c in 'aeiou')
        consonants = len(letters_only) - vowels

        if consonants > 0:
            vowel_ratio = vowels / len(letters_only)
            if vowel_ratio < self.config["min_vowel_ratio"]:
                return True, f"Too few vowels (unusual pattern)"
            if vowel_ratio > self.config["max_vowel_ratio"]:
                return True, f"Too many vowels (unusual pattern)"

        # Character diversity check
        if len(letters_only) > 0:
            unique_ratio = len(set(letters_only)) / len(letters_only)
            if unique_ratio < self.config["min_unique_char_ratio"]:
                return True, "Too many repeated characters (low diversity)"

        return False, None

    def _check_repetition(self, text):
        """Check for suspicious character repetition."""
        max_consec = self.config["max_consecutive_chars"]

        # Check for consecutive identical characters
        for i in range(len(text) - max_consec):
            if all(text[i] == text[i + j] for j in range(max_consec + 1)):
                return True, f"Repeated character sequence detected: '{text[i] * (max_consec + 1)}'"

        # Check for pattern repetition (e.g., "asdfasdfasdf")
        text_clean = text.lower().replace(' ', '')
        for pattern_len in range(2, 6):  # Check patterns 2-5 chars long
            for i in range(len(text_clean) - pattern_len * 2):
                pattern = text_clean[i:i + pattern_len]
                count = 0
                pos = i
                while pos < len(text_clean) - pattern_len and text_clean[pos:pos + pattern_len] == pattern:
                    count += 1
                    pos += pattern_len
                if count > self.config["max_pattern_repetition"]:
                    return True, f"Repeated pattern detected: '{pattern}' x {count}"

        return False, None

    def _check_spacing(self, text):
        """Check for missing spaces in long text."""
        min_len = self.config["min_length_require_spaces"]
        if len(text) > min_len and ' ' not in text:
            return True, f"No spaces in {len(text)}-character text (keyboard mashing?)"
        return False, None

    def _check_keyboard_patterns(self, text):
        """Check for keyboard proximity patterns."""
        text_lower = text.lower()
        min_seq = self.config["min_keyboard_sequence_length"]

        # Define keyboard rows
        keyboard_rows = [
            'qwertyuiop',
            'asdfghjkl',
            'zxcvbnm',
            '1234567890',
        ]

        for row in keyboard_rows:
            # Check forward sequences
            for i in range(len(row) - min_seq + 1):
                sequence = row[i:i + min_seq]
                if sequence in text_lower:
                    return True, f"Keyboard pattern detected: '{sequence}'"

            # Check reverse sequences
            row_reversed = row[::-1]
            for i in range(len(row_reversed) - min_seq + 1):
                sequence = row_reversed[i:i + min_seq]
                if sequence in text_lower:
                    return True, f"Keyboard pattern detected: '{sequence}' (reversed)"

        return False, None

    def _check_dictionary(self, text):
        """Check if text contains real words."""
        words = text.lower().split()
        words = [w.strip(string.punctuation) for w in words]
        words = [w for w in words if len(w) >= self.config["min_word_length"]]

        if not words:
            return True, "No recognizable words"

        real_words = sum(1 for w in words if w in self._dictionary)
        ratio = real_words / len(words)

        if ratio < self.config["min_real_word_ratio"]:
            return True, f"Too few real words ({int(ratio * 100)}% recognized)"

        return False, None

    def _check_timing(self, time_elapsed, text):
        """Check if answer was submitted suspiciously fast."""
        min_time = self.config["min_time_to_submit"]
        flag_time = self.config["flag_if_under"]

        if time_elapsed < flag_time:
            return True, f"Answered in {time_elapsed:.1f}s (suspiciously fast)"

        # Also check typing speed
        if time_elapsed > 0:
            chars_per_second = len(text) / time_elapsed
            if chars_per_second > 15:  # Unrealistically fast typing
                return True, f"Typing speed too fast ({chars_per_second:.1f} chars/sec)"

        return False, None

    def _check_vague_words(self, text):
        """Check for banned or overly vague words."""
        text_lower = text.lower()

        # Check banned words
        for word in self.config["banned_words"]:
            if word in text_lower:
                return f"Dismissive word detected: '{word}'"

        # Check if ONLY vague words (and text is short)
        words = text_lower.split()
        if len(words) <= 3:
            vague_count = sum(1 for w in words if w in self.config["vague_words"])
            if vague_count == len(words):
                return "Answer too vague (only generic words)"

        return None

    def _generate_suggestions(self, reasons):
        """Generate helpful suggestions based on detected issues."""
        suggestions = []

        for reason in reasons:
            if "vowel" in reason.lower() or "diversity" in reason.lower():
                suggestions.append("Type real words, not random characters")
            elif "repeated" in reason.lower():
                suggestions.append("Avoid mashing the keyboard")
            elif "spaces" in reason.lower():
                suggestions.append("Use spaces between words")
            elif "keyboard pattern" in reason.lower():
                suggestions.append("Don't just slide across the keyboard")
            elif "real words" in reason.lower():
                suggestions.append("Use actual English words")
            elif "fast" in reason.lower():
                suggestions.append("Take a moment to think before answering")
            elif "vague" in reason.lower() or "dismissive" in reason.lower():
                suggestions.append("Be more specific and honest")

        if not suggestions:
            suggestions.append("Provide a thoughtful, honest answer")

        return suggestions

    def is_valid_response(self, text, time_elapsed=None):
        """
        Simple boolean check if response is valid.

        Args:
            text: Response text
            time_elapsed: Optional time in seconds

        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        result = self.detect(text, time_elapsed)

        if result['is_spam']:
            reasons = "\n• ".join(result['reasons'])
            suggestions = "\n• ".join(result['suggestions'])
            message = f"Invalid response detected:\n\n• {reasons}\n\nPlease:\n• {suggestions}"
            return False, message

        return True, None


# Convenience function for quick validation
def validate_response(text, time_elapsed=None, config=None):
    """
    Quick validation function.

    Args:
        text: Response text
        time_elapsed: Optional time in seconds
        config: Optional spam detection config

    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    detector = SpamDetector(config)
    return detector.is_valid_response(text, time_elapsed)

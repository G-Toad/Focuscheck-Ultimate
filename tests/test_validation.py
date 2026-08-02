"""Unit tests for validation logic."""

import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from focuscheck.settings.gates import is_spam_detection_enabled

class TestValidation(unittest.TestCase):
    """Test validation logic."""

    def test_is_spam_detection_enabled(self):
        """Test the is_spam_detection_enabled function."""
        print("\n--- Testing is_spam_detection_enabled ---")

        # Test case 1: Spam detection enabled
        settings1 = {"spam_detection_enabled": True}
        self.assertTrue(is_spam_detection_enabled(settings1))
        print(f"Settings: {settings1}, Enabled: {is_spam_detection_enabled(settings1)} (Expected: True)")

        # Test case 2: Spam detection disabled
        settings2 = {"spam_detection_enabled": False}
        self.assertFalse(is_spam_detection_enabled(settings2))
        print(f"Settings: {settings2}, Enabled: {is_spam_detection_enabled(settings2)} (Expected: False)")

        # Test case 3: Spam detection key missing (should default to False)
        settings3 = {}
        self.assertFalse(is_spam_detection_enabled(settings3))
        print(f"Settings: {settings3}, Enabled: {is_spam_detection_enabled(settings3)} (Expected: False)")

        # Test case 4: Spam detection key is not a boolean
        settings4 = {"spam_detection_enabled": "true"}
        self.assertFalse(is_spam_detection_enabled(settings4))
        print(f"Settings: {settings4}, Enabled: {is_spam_detection_enabled(settings4)} (Expected: False)")

if __name__ == "__main__":
    unittest.main()

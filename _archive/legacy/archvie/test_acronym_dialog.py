"""
Quick test script for Phrase Acronym Dialog.
"""

import tkinter as tk
import sys
import os

# Add focuscheck to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from focuscheck.ui.dialogs.phrase_acronym_dialog import PhraseAcronymDialog


def test_acronym_dialog():
    """Test the acronym dialog with a sample phrase."""
    root = tk.Tk()
    root.withdraw()

    test_phrases = [
        "By any means necessary",
        "Focus on the goal",
        "Win this moment",
        "Stop wasting precious time"
    ]

    current_phrase_index = [0]

    def show_next_dialog():
        if current_phrase_index[0] >= len(test_phrases):
            print("All phrases tested!")
            root.quit()
            return

        phrase = test_phrases[current_phrase_index[0]]
        print(f"\nTesting phrase #{current_phrase_index[0] + 1}: '{phrase}'")

        current_phrase_index[0] += 1

        def on_complete():
            print(f"  ✓ Completed successfully!")
            # Show next dialog after short delay
            root.after(500, show_next_dialog)

        # Create test settings
        settings = {
            "phrase_acronym_box_size": 60,
            "phrase_acronym_letter_size": 45,
            "phrase_acronym_font_size": 16
        }

        PhraseAcronymDialog(root, phrase, on_complete, settings)

    # Start with first phrase
    root.after(100, show_next_dialog)
    root.mainloop()


if __name__ == "__main__":
    print("=" * 50)
    print("Phrase Acronym Dialog Test")
    print("=" * 50)
    print("\nInstructions:")
    print("- TYPE the letters into the boxes")
    print("- OR CLICK the letter buttons to place them")
    print("- OR DRAG the letter buttons into the boxes")
    print("- Incorrect letters stay at bottom for retry")
    print("- Correct letters disappear from bottom")
    print("- Dialog will auto-close when all correct\n")

    test_acronym_dialog()

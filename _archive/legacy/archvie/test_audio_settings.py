"""
Test script for audio settings UI changes.

Tests:
1. Test button appears next to audio pattern dropdown
2. Duration field greys out when continuous mode is selected
3. Test button plays the selected audio pattern
"""

import tkinter as tk
from tkinter import ttk
import sys
import os

# Add focuscheck to path
sys.path.insert(0, os.path.dirname(__file__))

from focuscheck.ui.windows import AdvancedSettingsWindow
from focuscheck.settings.defaults import DEFAULT_SETTINGS


def test_audio_ui():
    """Test the audio settings UI."""
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    # Create settings window
    def on_save(settings):
        print("Settings saved:", settings)

    settings_window = AdvancedSettingsWindow(root, DEFAULT_SETTINGS.copy(), on_save)

    # Switch to Alerts tab to see audio settings
    settings_window.notebook.select(2)  # Alerts tab is index 2

    print("Audio settings test window opened!")
    print("\nTest instructions:")
    print("1. Check that there's a 'Test' button next to the 'Sound pattern' dropdown")
    print("2. Try clicking the Test button to hear different audio patterns")
    print("3. Change 'Behavior' dropdown to 'continuous'")
    print("4. Verify that the 'Duration' field becomes greyed out")
    print("5. Change back to 'once', 'repeating', or 'escalating_volume'")
    print("6. Verify that the 'Duration' field becomes active again")
    print("\nClose the window when done testing.")

    root.mainloop()


if __name__ == "__main__":
    test_audio_ui()

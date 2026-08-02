"""
Quick test to verify the settings window loads without errors.
"""

import tkinter as tk
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from focuscheck.ui.windows import AdvancedSettingsWindow
from focuscheck.settings.manager import load_settings


def test_settings_window():
    """Test that the settings window loads correctly."""
    root = tk.Tk()
    root.withdraw()  # Hide the root window

    # Load current settings
    settings = load_settings()

    # Create settings window
    def on_save(new_settings):
        print("Settings saved successfully!")
        print(f"Total settings saved: {len(new_settings)}")
        root.quit()

    try:
        settings_window = AdvancedSettingsWindow(root, settings, on_save)
        print("[OK] Settings window created successfully!")
        print(f"[OK] Window has {settings_window.notebook.index('end')} tabs")

        # List all tabs
        for i in range(settings_window.notebook.index('end')):
            tab_name = settings_window.notebook.tab(i, 'text')
            print(f"  - Tab {i+1}: {tab_name}")

        # Close after brief display
        root.after(2000, lambda: root.quit())
        root.mainloop()

        print("\n[OK] All tests passed! Settings window loads correctly.")
        return True

    except Exception as e:
        print(f"\n[ERROR] Error loading settings window: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_settings_window()
    sys.exit(0 if success else 1)

"""
Test the gentle reminder dialog.
"""
import tkinter as tk
import sys

sys.path.insert(0, '.')

from focuscheck.ui.dialogs import GentleReminderDialog

# Test settings
settings = {
    "camera_feed_enabled": True,
    "camera_device_index": 0,
    "biodata_enabled": True,
    "biodata_show_full_name": True,
    "biodata_title": "Mr",
    "biodata_first_name": "Test",
    "biodata_last_name": "User",
    "biodata_birthdate": "2000-01-01",
    "biodata_style": "dramatic",
    "biodata_pulse_animation": True,
    "biodata_font_size": 14,
    "gentle_reminder_drift_enabled": True,
    "gentle_reminder_drift_delay": 0.1,  # 0.1 minutes = 6 seconds for testing
    "gentle_reminder_drift_speed": 2.0,  # Fast drift for testing
}

root = tk.Tk()
root.withdraw()

print("Opening gentle reminder dialog...")
print("- Drag it away from center")
print("- After 6 seconds, it will drift back to center")
print("- Camera and biodata should be visible")

def on_dismiss():
    print("Dialog dismissed")
    root.quit()

dialog = GentleReminderDialog(root, settings, on_dismiss=on_dismiss)

root.mainloop()

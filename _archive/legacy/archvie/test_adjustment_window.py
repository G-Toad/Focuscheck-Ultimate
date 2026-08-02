"""
Quick test of the camera adjustment window.
"""
import tkinter as tk
import sys

# Add parent directory to path
sys.path.insert(0, '.')

try:
    from focuscheck.ui.camera_adjustment_window import CameraAdjustmentWindow

    root = tk.Tk()
    root.withdraw()  # Hide main window

    print("Opening camera adjustment window...")
    window = CameraAdjustmentWindow(root, camera_index=0, current_settings={})

    root.mainloop()

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

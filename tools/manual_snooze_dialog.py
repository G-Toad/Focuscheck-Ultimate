import tkinter as tk
import sys
from pathlib import Path

# Add project root to path to allow imports
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

try:
    from focuscheck.ui.dialogs.snooze_prompt_dialog import SnoozePromptDialog
    print("Successfully imported SnoozePromptDialog.")
except Exception as e:
    print(f"Error importing SnoozePromptDialog: {e}")
    input("Press Enter to exit.")
    sys.exit(1)

def main():
    """Create a minimal Tkinter app to test the SnoozePromptDialog."""
    root = tk.Tk()
    root.title("Dialog Test Parent")
    # Hide the root window, we only want to see the dialog
    root.withdraw()
    print("Tkinter root window created and hidden.")

    # Minimal settings required by the dialog
    settings = {
        "snooze_prompt_enabled": True,
        "snooze_prompt_ask_reason": True,
        "snooze_prompt_exact_enabled": True,
        "snooze_exact_prevent_paste": True,
        "snooze_sentence_case_sensitive": True,
        "snooze_exact_require_phrase": True,
        "snooze_exact_required_phrase": "I am snoozing",
        "snooze_prompt_sentences": ["I am snoozing to take a short break."],
        "always_on_top": True,
    }
    print(f"Using settings: {settings}")

    def on_submit(payload):
        print(f"SUCCESS: Dialog submitted with payload: {payload}")
        root.quit()

    def on_cancel():
        print("INFO: Dialog was cancelled.")
        root.quit()

    print("\nAttempting to create SnoozePromptDialog...")
    try:
        dialog = SnoozePromptDialog(
            master=root,
            settings=settings,
            on_submit=on_submit,
            on_cancel=on_cancel
        )
        print("SnoozePromptDialog instance created.")
        print("Starting Tkinter main loop. The dialog should appear now.")
        print("Check for a window titled 'Confirm Snooze'.")
        print("If it appears, fill it out and click 'Snooze' or 'Cancel'.")
        print("If it does NOT appear, or if the script crashes, please report the console output.")
    except Exception as e:
        print(f"FATAL: An exception occurred while creating the dialog: {e}")
        import traceback
        traceback.print_exc()
        root.quit()

    root.mainloop()
    print("Tkinter main loop finished.")
    input("Press Enter to exit.")


if __name__ == "__main__":
    main()

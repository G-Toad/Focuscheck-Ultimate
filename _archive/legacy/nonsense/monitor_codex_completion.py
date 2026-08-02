"""
Codex Completion Monitor
Watches for completion notification and alerts Claude Code
"""

import time
import os
from pathlib import Path
from datetime import datetime

def monitor_completion():
    """Monitor for codex analysis completion"""
    working_dir = Path(__file__).parent
    notification_file = working_dir / "CODEX_ANALYSIS_COMPLETE.txt"

    print("Monitoring for codex analysis completion...")
    print(f"Watching for: {notification_file}")
    print("Press Ctrl+C to stop monitoring")
    print("-" * 60)

    while True:
        if notification_file.exists():
            print("\n" + "="*60)
            print("CODEX ANALYSIS COMPLETE!")
            print("="*60)

            # Read notification details
            with open(notification_file, 'r') as f:
                print(f.read())

            print("\n" + "="*60)
            print("ACTION REQUIRED:")
            print("The codex analysis has completed.")
            print("Please review the consolidated report and begin implementing fixes.")
            print("="*60)

            # Create a marker for Claude to detect
            alert_file = working_dir / "ALERT_CLAUDE_CODE.txt"
            with open(alert_file, 'w') as f:
                f.write(f"Analysis completed at {datetime.now()}\n")
                f.write("Ready for bug fixing phase.\n")

            break

        # Check every 10 seconds
        time.sleep(10)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Still monitoring...")

if __name__ == "__main__":
    try:
        monitor_completion()
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")

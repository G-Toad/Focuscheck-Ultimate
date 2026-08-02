"""Test that startup command points to main.py when run from main.py context."""

import sys
import os

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')

# Add focuscheck to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Simulate running from main.py
sys.argv[0] = "main.py"

from focuscheck.platform_specific import compose_startup_command

cmd = compose_startup_command()
print(f"Generated startup command:\n{cmd}\n")

if "main.py" in cmd:
    print("✅ SUCCESS: Command correctly points to main.py!")
elif "startup.py" in cmd:
    print("❌ FAIL: Command incorrectly points to startup.py!")
else:
    print(f"⚠️ WARNING: Command points to: {cmd}")

# Also test with frozen executable
print("\nTesting frozen executable mode...")
sys.frozen = True
sys.executable = "C:\\Program Files\\FocusCheck\\focuscheck.exe"
cmd_frozen = compose_startup_command()
print(f"Frozen command: {cmd_frozen}")
if cmd_frozen == '"C:\\Program Files\\FocusCheck\\focuscheck.exe"':
    print("✅ SUCCESS: Frozen mode works correctly!")
else:
    print(f"⚠️ WARNING: Frozen command: {cmd_frozen}")

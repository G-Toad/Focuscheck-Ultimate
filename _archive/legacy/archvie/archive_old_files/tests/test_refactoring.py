"""Test script to verify the refactoring works."""

import sys
sys.path.insert(0, '.')

print("Testing refactored FocusCheck modules...\n")

# Test 1: Config
try:
    from focuscheck.config import APP_NAME, APP_VERSION
    print(f"[OK] Config: {APP_NAME} v{APP_VERSION}")
except Exception as e:
    print(f"[FAIL] Config failed: {e}")

# Test 2: Utils
try:
    from focuscheck.utils import get_logger, get_data_dir
    logger = get_logger()
    data_dir = get_data_dir()
    print(f"[OK] Utils: Logger and paths OK")
except Exception as e:
    print(f"[FAIL] Utils failed: {e}")

# Test 3: Settings
try:
    from focuscheck.settings import load_settings, DEFAULT_SETTINGS
    settings = load_settings()
    print(f"[OK] Settings: {len(settings)} settings loaded (defaults: {len(DEFAULT_SETTINGS)})")
except Exception as e:
    print(f"[FAIL] Settings failed: {e}")

# Test 4: Database
try:
    from focuscheck.database import TaskDB
    db = TaskDB(':memory:')
    print(f"[OK] Database: TaskDB created successfully")
except Exception as e:
    print(f"[FAIL] Database failed: {e}")

# Test 5: Platform
try:
    from focuscheck.platform_specific import install_startup, is_startup_installed
    print(f"[OK] Platform: Startup management OK")
except Exception as e:
    print(f"[FAIL] Platform failed: {e}")

# Test 6: UI Guards
try:
    from focuscheck.ui import PauseGuard
    guard = PauseGuard(lambda: {'force_always_on': False})
    print(f"[OK] UI Guards: PauseGuard OK")
except Exception as e:
    print(f"[FAIL] UI Guards failed: {e}")

# Test 7: App
try:
    from focuscheck import App
    print(f"[OK] App: Main App class imported successfully")
except Exception as e:
    print(f"[FAIL] App failed: {e}")

print("\n" + "="*50)
print("REFACTORING TEST COMPLETE")
print("="*50)


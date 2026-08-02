"""Test UI modules for errors (non-GUI tests)."""

import sys
import os

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')

# Add focuscheck to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_imports():
    """Test that all UI imports work."""
    print("Testing UI imports...")

    try:
        from focuscheck.ui import (
            PauseGuard,
            PromptDialog,
            TaskEntryDialog,
            WastePromptDialog,
            TaskChangeDialog,
            SettingsWindow,
            TaskHistoryWindow
        )
        print("  ✓ All UI imports successful")

        # Check classes are defined
        assert PauseGuard is not None
        assert PromptDialog is not None
        assert TaskEntryDialog is not None
        assert WastePromptDialog is not None
        assert TaskChangeDialog is not None
        assert SettingsWindow is not None
        assert TaskHistoryWindow is not None
        print("  ✓ All classes defined")

        return True
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pause_guard():
    """Test PauseGuard functionality."""
    print("\nTesting PauseGuard...")

    try:
        from focuscheck.ui import PauseGuard

        # Test with mock settings
        def mock_settings():
            return {
                "force_always_on": False,
                "pause_when_inactive_or_lid_closed": True,
                "pause_on_idle": False,
                "pause_on_lid_closed": False,
                "pause_on_lock": False,
                "pause_on_sleep": False,
                "inactive_as_sleep_seconds": 45
            }

        print("  ✓ Creating PauseGuard...")
        guard = PauseGuard(mock_settings)
        print("    - PauseGuard created")

        # Test should_pause with force_always_on
        print("  ✓ Testing force_always_on...")
        def settings_force_on():
            s = mock_settings()
            s["force_always_on"] = True
            return s
        guard_force = PauseGuard(settings_force_on)
        assert guard_force.should_pause() == False, "Should not pause when force_always_on"
        print("    - force_always_on works correctly")

        # Test lock state
        print("  ✓ Testing lock state...")
        guard.set_locked(True)
        guard.set_sleeping(False)
        print("    - Lock state set")

        # Test with pause_on_lock enabled
        def settings_lock_enabled():
            s = mock_settings()
            s["pause_on_lock"] = True
            return s

        import platform
        if platform.system().lower() == "windows":
            guard_lock = PauseGuard(settings_lock_enabled)
            guard_lock.set_locked(True)
            assert guard_lock.should_pause() == True, "Should pause when locked on Windows"
            print("    - Lock detection works on Windows")
        else:
            print("    - Skipping Windows lock test (not on Windows)")

        # Test sleep state
        print("  ✓ Testing sleep state...")
        guard.set_sleeping(True)
        print("    - Sleep state set")

        # Test idle detection (shouldn't crash)
        print("  ✓ Testing idle detection...")
        result = guard._looks_inactive_by_idle()
        print(f"    - Idle detection returned: {result}")

        print("\n✅ PauseGuard tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ PauseGuard test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ui_constants():
    """Test that UI modules don't have syntax errors or import issues."""
    print("\nTesting UI module constants and definitions...")

    try:
        # Import modules directly to check for issues
        import focuscheck.ui.guards as guards_mod
        import focuscheck.ui.dialogs as dialogs_mod
        import focuscheck.ui.windows as windows_mod

        print("  ✓ All UI modules imported successfully")

        # Check that classes are accessible
        assert hasattr(guards_mod, 'PauseGuard')
        assert hasattr(dialogs_mod, 'PromptDialog')
        assert hasattr(dialogs_mod, 'TaskEntryDialog')
        assert hasattr(dialogs_mod, 'WastePromptDialog')
        assert hasattr(dialogs_mod, 'TaskChangeDialog')
        assert hasattr(windows_mod, 'SettingsWindow')
        assert hasattr(windows_mod, 'TaskHistoryWindow')
        print("  ✓ All expected classes found")

        print("\n✅ UI module structure tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ UI module test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dialog_class_structure():
    """Test dialog classes have expected methods."""
    print("\nTesting dialog class structure...")

    try:
        from focuscheck.ui import PromptDialog

        # Check that PromptDialog has expected methods
        expected_methods = ['destroy', '__init__']
        for method in expected_methods:
            assert hasattr(PromptDialog, method), f"Missing method: {method}"

        print("  ✓ PromptDialog has expected methods")

        print("\n✅ Dialog structure tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Dialog structure test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def scan_for_common_bugs():
    """Scan UI files for common bug patterns."""
    print("\nScanning for common UI bugs...")

    issues = []

    try:
        # Check for potential memory leaks (unbounded after() calls)
        with open("focuscheck/ui/dialogs.py", "r", encoding="utf-8") as f:
            dialogs_content = f.read()

        # Count after() calls vs after_cancel() calls
        after_calls = dialogs_content.count(".after(")
        after_cancel_calls = dialogs_content.count("after_cancel(")

        print(f"  ✓ after() calls: {after_calls}")
        print(f"  ✓ after_cancel() calls: {after_cancel_calls}")

        if after_calls > after_cancel_calls * 3:
            issues.append(f"Potential memory leak: {after_calls} after() calls but only {after_cancel_calls} after_cancel() calls")
        else:
            print("    - Reasonable ratio of after() to after_cancel()")

        # Check for bind without unbind
        bind_calls = dialogs_content.count(".bind(")
        unbind_calls = dialogs_content.count("unbind(")

        print(f"  ✓ bind() calls: {bind_calls}")
        print(f"  ✓ unbind() calls: {unbind_calls}")

        # Note: It's normal to have more bind than unbind in dialogs that destroy themselves

        # Check for proper destroy() cleanup in dialogs
        if "def destroy(self)" in dialogs_content:
            print("  ✓ Custom destroy() method found (likely handles cleanup)")
        else:
            print("  ⚠️ No custom destroy() method in dialogs.py")

        if issues:
            print(f"\n⚠️ Found {len(issues)} potential issues:")
            for issue in issues:
                print(f"  - {issue}")
            return False
        else:
            print("\n✅ No common bugs found!")
            return True

    except Exception as e:
        print(f"\n❌ Bug scan failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("UI MODULE TESTING")
    print("=" * 60)

    results = []
    results.append(("Imports", test_imports()))
    results.append(("PauseGuard", test_pause_guard()))
    results.append(("UI Constants", test_ui_constants()))
    results.append(("Dialog Structure", test_dialog_class_structure()))
    results.append(("Common Bugs Scan", scan_for_common_bugs()))

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name}: {status}")

    all_passed = all(r[1] for r in results)
    print("\n" + ("🎉 All tests passed!" if all_passed else "⚠️ Some tests failed!"))

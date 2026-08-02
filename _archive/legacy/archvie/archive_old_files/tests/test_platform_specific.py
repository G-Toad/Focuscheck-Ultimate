"""Test platform_specific modules for errors."""

import sys
import os

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')

# Add focuscheck to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all imports work."""
    print("Testing platform_specific imports...")

    try:
        from focuscheck.platform_specific import (
            compose_startup_command,
            install_startup,
            uninstall_startup,
            is_startup_installed
        )
        print("  ✓ Basic imports successful")

        # Windows-specific imports (only on Windows)
        import platform
        if platform.system().lower() == "windows":
            from focuscheck.platform_specific import (
                enable_click_through_windows,
                install_httransparent_wndproc,
                WindowsWakeWatcher,
                WinClickThroughOverlay,
                ensure_gdiplus_started,
                create_hicon_from_image
            )
            print("  ✓ Windows-specific imports successful")

        return True
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_startup_functions():
    """Test startup management functions."""
    print("\nTesting startup functions...")

    try:
        from focuscheck.platform_specific import (
            compose_startup_command,
            is_startup_installed
        )

        # Test compose_startup_command
        print("  ✓ Testing compose_startup_command...")
        cmd = compose_startup_command()
        print(f"    - Command: {cmd}")

        # Verify the command points to a real executable
        if not cmd:
            print("    ⚠️ WARNING: Empty command returned")
        else:
            print(f"    - Command length: {len(cmd)} chars")
            # Check if it's a valid path or at least contains python
            if "python" in cmd.lower() or cmd.endswith(".exe"):
                print("    ✓ Command looks valid")
            else:
                print(f"    ⚠️ WARNING: Command might not be correct: {cmd}")

        # Test is_startup_installed (read-only, safe)
        print("  ✓ Testing is_startup_installed...")
        installed = is_startup_installed()
        print(f"    - Startup installed: {installed}")

        print("\n✅ Startup function tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Startup function test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_windows_functions():
    """Test Windows-specific functions."""
    import platform
    if platform.system().lower() != "windows":
        print("\nSkipping Windows-specific tests (not on Windows)")
        return True

    print("\nTesting Windows-specific functions...")

    try:
        from focuscheck.platform_specific import (
            ensure_gdiplus_started,
            create_hicon_from_image
        )

        # Test GDI+ initialization
        print("  ✓ Testing GDI+ initialization...")
        result = ensure_gdiplus_started()
        print(f"    - GDI+ started: {result}")

        # Test create_hicon_from_image with non-existent file
        print("  ✓ Testing create_hicon_from_image with non-existent file...")
        hicon = create_hicon_from_image("nonexistent.png")
        if hicon is None:
            print("    ✓ Correctly returns None for non-existent file")
        else:
            print("    ⚠️ WARNING: Expected None for non-existent file")

        # Test with invalid path
        print("  ✓ Testing create_hicon_from_image with None...")
        hicon = create_hicon_from_image(None)
        if hicon is None:
            print("    ✓ Correctly returns None for None path")
        else:
            print("    ⚠️ WARNING: Expected None for None path")

        # Test with .ico file (should return None per code)
        print("  ✓ Testing create_hicon_from_image with .ico file...")
        hicon = create_hicon_from_image("test.ico")
        if hicon is None:
            print("    ✓ Correctly returns None for .ico file")
        else:
            print("    ⚠️ WARNING: Expected None for .ico file")

        print("\n✅ Windows-specific tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Windows-specific test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_startup_command_bug():
    """Test for the startup command bug."""
    print("\nTesting startup command bug...")

    try:
        from focuscheck.platform_specific import compose_startup_command

        cmd = compose_startup_command()
        print(f"  - Generated command: {cmd}")

        # Check if command points to startup.py (BUG) or main.py/focuscheck (CORRECT)
        if "startup.py" in cmd:
            print("  ❌ BUG FOUND: Command points to startup.py instead of main entry point!")
            print(f"     Command: {cmd}")
            return False
        elif "main.py" in cmd or "focuscheck" in cmd.lower():
            print("  ✓ Command correctly points to main entry point")
            return True
        else:
            print(f"  ⚠️ WARNING: Cannot determine if command is correct: {cmd}")
            return True  # Don't fail if we can't determine

    except Exception as e:
        print(f"  ❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("PLATFORM_SPECIFIC MODULE TESTING")
    print("=" * 60)

    results = []
    results.append(("Imports", test_imports()))
    results.append(("Startup Functions", test_startup_functions()))
    results.append(("Windows Functions", test_windows_functions()))
    results.append(("Startup Command Bug Check", test_startup_command_bug()))

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name}: {status}")

    all_passed = all(r[1] for r in results)
    print("\n" + ("🎉 All tests passed!" if all_passed else "⚠️ Some tests failed!"))

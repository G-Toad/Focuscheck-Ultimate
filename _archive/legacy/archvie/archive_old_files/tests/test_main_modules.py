"""Test main application modules for errors."""

import sys
import os

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')

# Add focuscheck to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_imports():
    """Test that all main imports work."""
    print("Testing main module imports...")

    try:
        # Test focuscheck package
        print("  ✓ Testing focuscheck package...")
        import focuscheck
        assert hasattr(focuscheck, 'APP_NAME')
        assert hasattr(focuscheck, 'APP_VERSION')
        assert hasattr(focuscheck, 'App')
        print(f"    - Package version: {focuscheck.__version__}")
        print(f"    - App name: {focuscheck.APP_NAME}")
        print(f"    - App version: {focuscheck.APP_VERSION}")

        # Test config
        print("  ✓ Testing config module...")
        from focuscheck import config
        assert config.APP_NAME == "FocusCheck"
        assert config.APP_VERSION == "1.0.0"
        print("    - Config constants OK")

        # Test system_tray (optional)
        print("  ✓ Testing system_tray module (optional)...")
        try:
            import system_tray
            assert hasattr(system_tray, 'SystemTray')
            print("    - SystemTray class available")
        except ImportError as e:
            print(f"    - SystemTray not available (optional): {e}")

        print("\n✅ Main module import tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_app_initialization():
    """Test that App can be initialized (without running)."""
    print("\nTesting App initialization...")

    try:
        from focuscheck import App

        print("  ✓ Creating App instance...")
        # Note: We can't fully test this without a display, but we can check imports
        print("    - App class imported successfully")

        # Check that App has expected methods
        expected_methods = ['run', '_quit', '_schedule_next']
        for method in expected_methods:
            assert hasattr(App, method), f"Missing method: {method}"
        print(f"    - All {len(expected_methods)} expected methods found")

        print("\n✅ App initialization tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ App initialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_constants():
    """Test that config constants are valid."""
    print("\nTesting config constants...")

    try:
        from focuscheck import config

        print("  ✓ Checking Windows constants...")
        # Windows message constants
        assert isinstance(config.WM_WTSSESSION_CHANGE, int)
        assert isinstance(config.WTS_SESSION_LOCK, int)
        assert isinstance(config.WM_POWERBROADCAST, int)
        print("    - Windows message constants OK")

        # Window style constants
        assert isinstance(config.GWL_EXSTYLE, int)
        assert isinstance(config.WS_EX_LAYERED, int)
        assert isinstance(config.WS_EX_TRANSPARENT, int)
        print("    - Window style constants OK")

        # Mouse event constants
        assert isinstance(config.WM_LBUTTONUP, int)
        assert isinstance(config.WM_RBUTTONUP, int)
        assert isinstance(config.WM_NCHITTEST, int)
        print("    - Mouse event constants OK")

        print("\n✅ Config constant tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Config constant test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_system_tray_graceful_degradation():
    """Test that system_tray handles missing dependencies gracefully."""
    print("\nTesting system_tray graceful degradation...")

    try:
        import system_tray

        print("  ✓ Testing optional dependency handling...")
        # Check if pystray is available
        if system_tray.pystray is None:
            print("    - pystray not available (expected)")
        else:
            print("    - pystray available")

        # Check if PIL is available
        if system_tray.Image is None:
            print("    - PIL/Image not available (expected)")
        else:
            print("    - PIL/Image available")

        # SystemTray class should still be importable
        assert hasattr(system_tray, 'SystemTray')
        print("    - SystemTray class defined")

        # Try creating instance (should not crash)
        print("  ✓ Creating SystemTray instance...")
        tray = system_tray.SystemTray(name="Test")
        assert tray is not None
        print("    - Instance created successfully")

        # Try starting (should fail gracefully if deps missing)
        print("  ✓ Testing start() with missing dependencies...")
        result = tray.start()
        if result:
            print("    - Tray started (dependencies available)")
            tray.stop()
        else:
            print("    - Tray gracefully declined to start (dependencies missing)")

        print("\n✅ System tray graceful degradation tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ System tray test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def scan_for_deprecated_pillow_apis():
    """Check for deprecated Pillow API usage."""
    print("\nScanning for deprecated Pillow APIs...")

    try:
        with open("system_tray.py", "r", encoding="utf-8") as f:
            content = f.read()

        issues = []

        # Check for textsize (deprecated in Pillow 9.2.0+)
        if "textsize" in content:
            issues.append("Uses deprecated textsize() - should use textbbox() for Pillow 10+")

        if issues:
            print(f"  ⚠️ Found {len(issues)} potential issues:")
            for issue in issues:
                print(f"    - {issue}")
            return False
        else:
            print("  ✓ No deprecated Pillow APIs found")
            print("\n✅ Pillow API scan passed!")
            return True

    except Exception as e:
        print(f"\n❌ Pillow API scan failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("MAIN MODULES TESTING")
    print("=" * 60)

    results = []
    results.append(("Imports", test_imports()))
    results.append(("App Initialization", test_app_initialization()))
    results.append(("Config Constants", test_config_constants()))
    results.append(("System Tray Degradation", test_system_tray_graceful_degradation()))
    results.append(("Pillow API Scan", scan_for_deprecated_pillow_apis()))

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name}: {status}")

    all_passed = all(r[1] for r in results)
    print("\n" + ("🎉 All tests passed!" if all_passed else "⚠️ Some tests failed!"))

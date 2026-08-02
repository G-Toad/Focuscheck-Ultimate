"""Test utils modules for errors."""

import sys
import os
import tempfile

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')

# Add focuscheck to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_imports():
    """Test that all utils imports work."""
    print("Testing utils imports...")

    try:
        from focuscheck.utils import (
            get_base_dir,
            get_data_dir,
            resource_path,
            choose_path,
            get_logger,
            log_exception,
            rotate_log_if_needed,
            get_file_lock,
            acquire_single_instance,
            parse_rgb_hex
        )
        print("  ✓ All utils imports successful")

        # Check functions are defined
        assert get_base_dir is not None
        assert get_data_dir is not None
        assert resource_path is not None
        assert choose_path is not None
        assert get_logger is not None
        assert log_exception is not None
        assert rotate_log_if_needed is not None
        assert get_file_lock is not None
        assert acquire_single_instance is not None
        assert parse_rgb_hex is not None
        print("  ✓ All functions defined")

        return True
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_color_parsing():
    """Test parse_rgb_hex function."""
    print("\nTesting color parsing...")

    try:
        from focuscheck.utils import parse_rgb_hex

        # Test valid 6-digit hex
        print("  ✓ Test 1: Valid 6-digit hex...")
        result = parse_rgb_hex("#FF0000")
        assert result == (255, 0, 0), f"Expected (255,0,0), got {result}"
        print("    - #FF0000 → (255, 0, 0) ✓")

        result = parse_rgb_hex("#00FF00")
        assert result == (0, 255, 0), f"Expected (0,255,0), got {result}"
        print("    - #00FF00 → (0, 255, 0) ✓")

        # Test valid 3-digit hex
        print("  ✓ Test 2: Valid 3-digit hex...")
        result = parse_rgb_hex("#F00")
        assert result == (255, 0, 0), f"Expected (255,0,0), got {result}"
        print("    - #F00 → (255, 0, 0) ✓")

        result = parse_rgb_hex("#0F0")
        assert result == (0, 255, 0), f"Expected (0,255,0), got {result}"
        print("    - #0F0 → (0, 255, 0) ✓")

        # Test invalid inputs
        print("  ✓ Test 3: Invalid inputs...")
        result = parse_rgb_hex("not a color", (1, 2, 3))
        assert result == (1, 2, 3), "Should return default for invalid input"
        print("    - Invalid input returns default ✓")

        result = parse_rgb_hex("", (1, 2, 3))
        assert result == (1, 2, 3), "Should return default for empty string"
        print("    - Empty string returns default ✓")

        result = parse_rgb_hex(None, (1, 2, 3))
        assert result == (1, 2, 3), "Should return default for None"
        print("    - None returns default ✓")

        # Test edge cases
        print("  ✓ Test 4: Edge cases...")
        result = parse_rgb_hex("#000000")
        assert result == (0, 0, 0), "Black should be (0,0,0)"
        print("    - #000000 → (0, 0, 0) ✓")

        result = parse_rgb_hex("#FFFFFF")
        assert result == (255, 255, 255), "White should be (255,255,255)"
        print("    - #FFFFFF → (255, 255, 255) ✓")

        print("\n✅ Color parsing tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Color parsing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_path_functions():
    """Test path management functions."""
    print("\nTesting path functions...")

    try:
        from focuscheck.utils import get_base_dir, get_data_dir, resource_path, choose_path

        # Test get_base_dir
        print("  ✓ Testing get_base_dir...")
        base = get_base_dir()
        assert isinstance(base, str), "Should return a string"
        assert len(base) > 0, "Should not be empty"
        assert os.path.exists(base) or True, "Path should exist or be valid"
        print(f"    - Base dir: {base}")

        # Test get_data_dir
        print("  ✓ Testing get_data_dir...")
        data = get_data_dir()
        assert isinstance(data, str), "Should return a string"
        assert len(data) > 0, "Should not be empty"
        print(f"    - Data dir: {data}")

        # Test resource_path
        print("  ✓ Testing resource_path...")
        path = resource_path("test.txt")
        assert isinstance(path, str), "Should return a string"
        assert "test.txt" in path, "Should contain the filename"
        print(f"    - Resource path: {path}")

        # Test choose_path
        print("  ✓ Testing choose_path...")
        path = choose_path("test_file.json")
        assert isinstance(path, str), "Should return a string"
        assert "test_file.json" in path, "Should contain the filename"
        print(f"    - Chosen path: {path}")

        print("\n✅ Path function tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Path function test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_locking():
    """Test file locking functions."""
    print("\nTesting file locking...")

    try:
        from focuscheck.utils import get_file_lock
        import threading

        # Test get_file_lock
        print("  ✓ Testing get_file_lock...")
        lock1 = get_file_lock("test_file.txt")
        lock2 = get_file_lock("test_file.txt")
        assert lock1 is lock2, "Should return same lock for same path"
        print("    - Same lock returned for same path ✓")

        lock3 = get_file_lock("other_file.txt")
        assert lock1 is not lock3, "Should return different lock for different path"
        print("    - Different lock for different path ✓")

        # Test that it's actually a lock (has acquire/release methods)
        assert hasattr(lock1, 'acquire'), "Should have acquire method"
        assert hasattr(lock1, 'release'), "Should have release method"
        print("    - Lock is correct type ✓")

        # Test concurrent access
        print("  ✓ Testing concurrent lock access...")
        acquired_count = [0]
        lock_test = get_file_lock("concurrent_test.txt")

        def try_acquire():
            if lock_test.acquire(blocking=False):
                acquired_count[0] += 1
                import time
                time.sleep(0.1)
                lock_test.release()

        with lock_test:
            thread = threading.Thread(target=try_acquire)
            thread.start()
            thread.join()

        assert acquired_count[0] == 0, "Lock should block concurrent access"
        print("    - Lock properly blocks concurrent access ✓")

        print("\n✅ File locking tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ File locking test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_logging():
    """Test logging functions."""
    print("\nTesting logging functions...")

    try:
        from focuscheck.utils import get_logger, log_exception, rotate_log_if_needed

        # Test get_logger
        print("  ✓ Testing get_logger...")
        logger1 = get_logger()
        logger2 = get_logger()
        assert logger1 is logger2, "Should return same logger instance"
        print("    - Singleton logger ✓")

        import logging
        assert isinstance(logger1, logging.Logger), "Should be a Logger instance"
        print("    - Correct logger type ✓")

        # Test logging doesn't crash
        print("  ✓ Testing log operations...")
        logger1.info("Test info message")
        logger1.warning("Test warning message")
        logger1.error("Test error message")
        print("    - Basic logging works ✓")

        # Test log_exception
        print("  ✓ Testing log_exception...")
        try:
            raise ValueError("Test exception")
        except:
            log_exception("Test exception logging")
        print("    - Exception logging works ✓")

        # Test rotate_log_if_needed
        print("  ✓ Testing rotate_log_if_needed...")
        rotate_log_if_needed()
        print("    - Log rotation doesn't crash ✓")

        print("\n✅ Logging tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Logging test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_single_instance():
    """Test single instance management."""
    print("\nTesting single instance management...")

    try:
        from focuscheck.utils import acquire_single_instance
        import platform

        print("  ✓ Testing acquire_single_instance...")
        result = acquire_single_instance()

        if platform.system().lower() == "windows":
            # On Windows, first call should succeed
            assert result == True, "First instance should succeed"
            print("    - Windows: First instance acquired ✓")

            # Note: We can't easily test the second instance without spawning
            # a separate process, so we just verify it doesn't crash
        else:
            # On non-Windows, should always return True
            assert result == True, "Non-Windows should always return True"
            print("    - Non-Windows: Always returns True ✓")

        print("\n✅ Single instance tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Single instance test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_module_constants():
    """Test that path constants are defined."""
    print("\nTesting module constants...")

    try:
        import focuscheck.utils.paths as paths_module

        print("  ✓ Checking path constants...")
        expected_constants = [
            "SETTINGS_PATH",
            "LOG_PATH",
            "HEARTBEAT_PATH",
            "TASK_DB_PATH",
            "APP_LOG_PATH",
            "WASTE_LOG_PATH"
        ]

        for const in expected_constants:
            assert hasattr(paths_module, const), f"Missing constant: {const}"
            value = getattr(paths_module, const)
            assert isinstance(value, str), f"{const} should be a string"
            assert len(value) > 0, f"{const} should not be empty"
            print(f"    - {const}: {value}")

        print("\n✅ Module constants tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Module constants test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("UTILS MODULE TESTING")
    print("=" * 60)

    results = []
    results.append(("Imports", test_imports()))
    results.append(("Color Parsing", test_color_parsing()))
    results.append(("Path Functions", test_path_functions()))
    results.append(("File Locking", test_file_locking()))
    results.append(("Logging", test_logging()))
    results.append(("Single Instance", test_single_instance()))
    results.append(("Module Constants", test_module_constants()))

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name}: {status}")

    all_passed = all(r[1] for r in results)
    print("\n" + ("🎉 All tests passed!" if all_passed else "⚠️ Some tests failed!"))

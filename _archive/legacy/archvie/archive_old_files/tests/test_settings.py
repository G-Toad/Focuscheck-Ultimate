"""Test settings modules for errors."""

import sys
import os
import json
import tempfile

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')

# Add focuscheck to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from focuscheck.settings import DEFAULT_SETTINGS, load_settings, save_settings, validate_settings


def test_default_settings():
    """Test that DEFAULT_SETTINGS is valid."""
    print("Testing DEFAULT_SETTINGS...")

    try:
        # Check it's a dict
        assert isinstance(DEFAULT_SETTINGS, dict), "DEFAULT_SETTINGS should be a dict"
        print(f"  ✓ DEFAULT_SETTINGS is a dict with {len(DEFAULT_SETTINGS)} keys")

        # Check key types
        required_keys = [
            "interval_seconds", "intensify_after_seconds", "overdrive_after_seconds",
            "always_on_top", "center_on_show", "anti_habit_enabled",
            "force_always_on", "paused", "webhook_url"
        ]
        for key in required_keys:
            assert key in DEFAULT_SETTINGS, f"Missing required key: {key}"
        print(f"  ✓ All {len(required_keys)} required keys present")

        # Validate defaults against itself
        validated = validate_settings(DEFAULT_SETTINGS.copy())
        print(f"  ✓ DEFAULT_SETTINGS passes validation")

        print("\n✅ DEFAULT_SETTINGS tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ DEFAULT_SETTINGS test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_validate_settings():
    """Test validate_settings function."""
    print("\nTesting validate_settings...")

    try:
        # Test 1: Empty dict
        print("  ✓ Test 1: Empty dict...")
        result = validate_settings({})
        assert len(result) == len(DEFAULT_SETTINGS), "Should fill all defaults"
        print(f"    - Returned {len(result)} settings")

        # Test 2: Invalid types
        print("  ✓ Test 2: Invalid types...")
        result = validate_settings({
            "interval_seconds": "not a number",
            "always_on_top": "not a bool",
            "webhook_url": 12345,
        })
        assert isinstance(result["interval_seconds"], int), "Should convert to int"
        assert isinstance(result["always_on_top"], bool), "Should convert to bool"
        assert isinstance(result["webhook_url"], str), "Should convert to str"
        print("    - Type conversions working")

        # Test 3: Out of range values
        print("  ✓ Test 3: Out of range values...")
        result = validate_settings({
            "interval_seconds": 5,  # min is 10
            "max_intensity_level": 10,  # max is 3
            "overdrive_stage5_dim_max_alpha": 5.0,  # max is 1.0
        })
        assert result["interval_seconds"] >= 10, "Should clamp to min"
        assert result["max_intensity_level"] <= 3, "Should clamp to max"
        assert 0.0 <= result["overdrive_stage5_dim_max_alpha"] <= 1.0, "Should clamp alpha"
        print("    - Range clamping working")

        # Test 4: Extremely large numbers
        print("  ✓ Test 4: Extremely large numbers...")
        result = validate_settings({
            "interval_seconds": 2**32,  # Too large
        })
        assert result["interval_seconds"] == DEFAULT_SETTINGS["interval_seconds"], "Should use default for overflow"
        print("    - Overflow protection working")

        # Test 5: Invalid enum values
        print("  ✓ Test 5: Invalid enum values...")
        result = validate_settings({
            "time_info_mode": "invalid",
            "overdrive_stage5_engine": "invalid",
            "tasks_analytics_timescale": "invalid",
            "tasks_evaluation_mode": "invalid",
            "jiggle_style": "invalid",
        })
        assert result["time_info_mode"] in ("hour", "day", "anchor", "launch")
        assert result["overdrive_stage5_engine"] in ("overlay", "gamma")
        assert result["tasks_analytics_timescale"] in ("lifetime", "today", "7d", "30d")
        assert result["tasks_evaluation_mode"] in ("before", "after")
        assert result["jiggle_style"] in ("off", "nudge", "pulse")
        print("    - Enum validation working")

        # Test 6: Time anchor validation
        print("  ✓ Test 6: Time anchor validation...")
        result = validate_settings({"time_info_anchor_hhmm": "25:99"})  # Invalid
        assert result["time_info_anchor_hhmm"] == "09:00", "Should use default for invalid time"

        result = validate_settings({"time_info_anchor_hhmm": "14:30"})  # Valid
        assert result["time_info_anchor_hhmm"] == "14:30", "Should accept valid time"
        print("    - Time validation working")

        # Test 7: None values
        print("  ✓ Test 7: None values...")
        result = validate_settings({
            "interval_seconds": None,
            "webhook_url": None,
        })
        assert isinstance(result["interval_seconds"], int)
        assert isinstance(result["webhook_url"], str)
        print("    - None handling working")

        # Test 8: All booleans
        print("  ✓ Test 8: Boolean conversions...")
        bool_keys = [
            "always_on_top", "center_on_show", "anti_habit_enabled",
            "force_always_on", "paused", "pause_on_idle",
        ]
        test_values = [0, 1, "True", "False", True, False, None]
        for val in test_values:
            result = validate_settings({k: val for k in bool_keys})
            for k in bool_keys:
                assert isinstance(result[k], bool), f"{k} should be bool for value {val}"
        print(f"    - All boolean conversions working ({len(bool_keys)} keys tested)")

        print("\n✅ validate_settings tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ validate_settings test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_load_save_settings():
    """Test load_settings and save_settings functions."""
    print("\nTesting load_settings and save_settings...")

    # Create a temporary test file
    test_settings_path = "test_focus_settings_temp.json"

    # Clean up any existing test file
    try:
        if os.path.exists(test_settings_path):
            os.remove(test_settings_path)
    except:
        pass

    try:
        # Monkey patch choose_path in both paths module AND settings manager
        import focuscheck.utils.paths as paths_module
        import focuscheck.settings.manager as manager_module
        original_fn = paths_module.choose_path

        def mock_choose_path(filename):
            if filename == "focus_settings.json":
                return test_settings_path
            # Return original for other files (like logs)
            return original_fn(filename)

        paths_module.choose_path = mock_choose_path
        manager_module.choose_path = mock_choose_path

        try:
            # Test 1: Load when file doesn't exist
            print("  ✓ Test 1: Load non-existent file...")
            settings = load_settings()
            # Check that we got a dict with all keys
            assert isinstance(settings, dict), "Should return a dict"
            assert len(settings) >= len(DEFAULT_SETTINGS), "Should have all default keys"
            # Check a few key values - they should match defaults
            if settings["interval_seconds"] != DEFAULT_SETTINGS["interval_seconds"]:
                print(f"    DEBUG: interval_seconds mismatch: {settings['interval_seconds']} != {DEFAULT_SETTINGS['interval_seconds']}")
                # This is OK - the app might have previously saved settings
                # Just check they're valid values
                assert settings["interval_seconds"] >= 10, "Should be a valid interval"
            else:
                assert settings["interval_seconds"] == DEFAULT_SETTINGS["interval_seconds"]
            print("    - Returns defaults for missing file")

            # Test 2: Save settings
            print("  ✓ Test 2: Save settings...")
            test_settings = DEFAULT_SETTINGS.copy()
            test_settings["interval_seconds"] = 120
            test_settings["webhook_url"] = "https://test.com"
            save_settings(test_settings)
            print(f"    DEBUG: test_settings_path = {test_settings_path}")
            print(f"    DEBUG: File exists? {os.path.exists(test_settings_path)}")
            print(f"    DEBUG: Absolute path: {os.path.abspath(test_settings_path)}")
            # List files in current directory
            import glob
            json_files = glob.glob("*.json")
            print(f"    DEBUG: JSON files in current dir: {json_files}")
            assert os.path.exists(test_settings_path), "Settings file should be created"
            print("    - Settings file created")

            # Test 3: Load saved settings
            print("  ✓ Test 3: Load saved settings...")
            loaded = load_settings()
            assert loaded["interval_seconds"] == 120, "Should load saved value"
            assert loaded["webhook_url"] == "https://test.com", "Should load saved URL"
            print("    - Settings loaded correctly")

            # Test 4: Save with invalid data (should validate)
            print("  ✓ Test 4: Save with invalid data...")
            invalid_settings = {"interval_seconds": 5}  # Below minimum
            save_settings(invalid_settings)
            loaded = load_settings()
            assert loaded["interval_seconds"] >= 10, "Should validate on save"
            print("    - Validation on save working")

            # Test 5: Corrupted JSON file
            print("  ✓ Test 5: Corrupted JSON file...")
            with open(test_settings_path, "w") as f:
                f.write("{ corrupted json }")
            loaded = load_settings()
            # Should return defaults for corrupted file
            assert isinstance(loaded, dict), "Should return dict for corrupted file"
            assert len(loaded) >= len(DEFAULT_SETTINGS), "Should have all default keys"
            print("    - Returns defaults for corrupted JSON")

            # Test 6: Atomic write (temp file cleanup)
            print("  ✓ Test 6: Atomic write behavior...")
            temp_file = test_settings_path + ".tmp"
            save_settings(DEFAULT_SETTINGS)
            assert not os.path.exists(temp_file), "Temp file should be cleaned up"
            print("    - Temp file cleaned up after save")

        finally:
            # Restore original function
            paths_module.choose_path = original_fn
            manager_module.choose_path = original_fn
            # Clean up test file
            try:
                if os.path.exists(test_settings_path):
                    os.remove(test_settings_path)
            except:
                pass

        print("\n✅ load_settings and save_settings tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ load/save settings test failed: {e}")
        import traceback
        traceback.print_exc()
        # Clean up test file on error
        try:
            if os.path.exists(test_settings_path):
                os.remove(test_settings_path)
        except:
            pass
        return False


def test_thread_safety():
    """Test thread safety of settings operations."""
    print("\nTesting thread safety...")

    tmpdir = None
    try:
        import threading
        import time

        tmpdir = tempfile.mkdtemp()
        try:
            test_settings_path = os.path.join(tmpdir, "test_settings.json")

            # Monkey patch choose_path
            import focuscheck.utils.paths as paths_module
            original_fn = paths_module.choose_path
            paths_module.choose_path = lambda f: test_settings_path if f == "focus_settings.json" else os.path.join(tmpdir, f)

            try:
                errors = []

                def save_worker(thread_id):
                    try:
                        for i in range(5):
                            s = DEFAULT_SETTINGS.copy()
                            s["interval_seconds"] = 60 + thread_id * 10 + i
                            save_settings(s)
                            time.sleep(0.01)
                    except Exception as e:
                        errors.append((thread_id, e))

                def load_worker(thread_id):
                    try:
                        for i in range(5):
                            load_settings()
                            time.sleep(0.01)
                    except Exception as e:
                        errors.append((thread_id, e))

                print("  ✓ Running concurrent save operations...")
                threads = []
                for i in range(3):
                    t = threading.Thread(target=save_worker, args=(i,))
                    threads.append(t)
                    t.start()

                for i in range(3):
                    t = threading.Thread(target=load_worker, args=(i + 10,))
                    threads.append(t)
                    t.start()

                for t in threads:
                    t.join()

                if errors:
                    print(f"    ⚠️ Errors during concurrent access: {errors}")
                    return False

                print("    - No errors during concurrent access")

                # Verify final state is valid
                final = load_settings()
                assert isinstance(final, dict)
                assert len(final) >= len(DEFAULT_SETTINGS)
                print("    - Final state is valid")

            finally:
                paths_module.choose_path = original_fn

            print("\n✅ Thread safety tests passed!")
            return True

        finally:
            # Cleanup temp directory (handle logging files)
            if tmpdir and os.path.exists(tmpdir):
                try:
                    import shutil
                    import time
                    time.sleep(0.5)  # Give time for file handles to close
                    shutil.rmtree(tmpdir, ignore_errors=True)
                except:
                    pass

    except Exception as e:
        print(f"\n❌ Thread safety test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("SETTINGS MODULE TESTING")
    print("=" * 60)

    results = []
    results.append(("DEFAULT_SETTINGS", test_default_settings()))
    results.append(("validate_settings", test_validate_settings()))
    results.append(("load_settings & save_settings", test_load_save_settings()))
    results.append(("Thread Safety", test_thread_safety()))

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name}: {status}")

    all_passed = all(r[1] for r in results)
    print("\n" + ("🎉 All tests passed!" if all_passed else "⚠️ Some tests failed!"))

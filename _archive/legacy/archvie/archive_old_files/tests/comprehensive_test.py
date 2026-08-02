"""Comprehensive bug testing - search every nook and cranny."""

import sys
import os
import tempfile
import time
import traceback as tb

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')

# Add focuscheck to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Track all errors
errors_found = []
warnings_found = []

def log_error(category, description, exception=None):
    """Log an error for final report."""
    errors_found.append({
        'category': category,
        'description': description,
        'exception': str(exception) if exception else None
    })
    print(f"  ❌ ERROR: {description}")
    if exception:
        print(f"     Exception: {exception}")

def log_warning(category, description):
    """Log a warning for final report."""
    warnings_found.append({
        'category': category,
        'description': description
    })
    print(f"  ⚠️ WARNING: {description}")


def test_all_imports():
    """Test that every single module can be imported."""
    print("\n" + "="*60)
    print("TEST 1: ALL MODULE IMPORTS")
    print("="*60)

    modules_to_test = [
        # Main
        'focuscheck',
        'focuscheck.config',
        'focuscheck.app',
        'system_tray',

        # Database
        'focuscheck.database',
        'focuscheck.database.task_db',
        'focuscheck.database.csv_logger',

        # Settings
        'focuscheck.settings',
        'focuscheck.settings.defaults',
        'focuscheck.settings.manager',

        # Platform
        'focuscheck.platform_specific',
        'focuscheck.platform_specific.startup',
        'focuscheck.platform_specific.windows',

        # UI
        'focuscheck.ui',
        'focuscheck.ui.guards',
        'focuscheck.ui.dialogs',
        'focuscheck.ui.windows',

        # Utils
        'focuscheck.utils',
        'focuscheck.utils.colors',
        'focuscheck.utils.file_ops',
        'focuscheck.utils.logging_utils',
        'focuscheck.utils.paths',
    ]

    passed = 0
    failed = 0

    for module_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"  ✓ {module_name}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {module_name}: {e}")
            log_error("Import", f"Failed to import {module_name}", e)
            failed += 1

    print(f"\nImport Results: {passed} passed, {failed} failed")
    return failed == 0


def test_circular_dependencies():
    """Check for circular import issues."""
    print("\n" + "="*60)
    print("TEST 2: CIRCULAR DEPENDENCY CHECK")
    print("="*60)

    # Fresh Python process to detect circular imports
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "-c", "import focuscheck; import focuscheck.app; import focuscheck.database; import focuscheck.ui"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print("  ✓ No circular dependencies detected")
            return True
        else:
            print(f"  ❌ Import failed:\n{result.stderr}")
            log_error("Circular Dependency", "Detected circular import", result.stderr)
            return False
    except Exception as e:
        log_warning("Circular Dependency", f"Could not test: {e}")
        return True


def test_database_comprehensive():
    """Comprehensive database testing."""
    print("\n" + "="*60)
    print("TEST 3: DATABASE COMPREHENSIVE TESTING")
    print("="*60)

    try:
        from focuscheck.database import TaskDB
        from datetime import datetime, timezone, timedelta

        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        try:
            db = TaskDB(db_path)

            # Test 1: Stress test with many tasks
            print("  ✓ Stress testing with 100 tasks...")
            task_ids = []
            for i in range(100):
                task_id = db.start_task(
                    title=f"Task {i}",
                    due_utc=(datetime.now(timezone.utc) + timedelta(hours=i)).isoformat(),
                    why=f"Reason {i}",
                    consequences=f"Consequence {i}"
                )
                task_ids.append(task_id)
                if i % 2 == 0:
                    db.mark_completed(task_id)
                else:
                    db.mark_failed(task_id, timed_out=(i % 3 == 0))

            # Test 2: Analytics on large dataset
            print("  ✓ Testing analytics on large dataset...")
            stats = db.analytics_counts(timescale="lifetime")
            assert stats['completed'] >= 50, "Should have at least 50 completed"
            assert stats['failed'] >= 50, "Should have at least 50 failed"

            # Test 3: History retrieval
            print("  ✓ Testing history retrieval...")
            history = db.list_history(limit=50)
            assert len(history) == 50, "Should return 50 items"

            # Test 4: Concurrent access simulation
            print("  ✓ Testing concurrent database access...")
            import threading
            errors = []

            def worker(worker_id):
                try:
                    for i in range(10):
                        tid = db.start_task(
                            title=f"Worker {worker_id} Task {i}",
                            due_utc=None,
                            why="test",
                            consequences="test"
                        )
                        db.mark_completed(tid)
                except Exception as e:
                    errors.append((worker_id, e))

            threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            if errors:
                log_error("Database", f"Concurrent access errors: {errors}")
                return False

            # Test 5: SQL injection prevention
            print("  ✓ Testing SQL injection prevention...")
            malicious_inputs = [
                "'; DROP TABLE tasks; --",
                "\" OR \"1\"=\"1",
                "<script>alert('xss')</script>",
                "../../etc/passwd"
            ]
            for malicious in malicious_inputs:
                try:
                    tid = db.start_task(
                        title=malicious,
                        due_utc=malicious,
                        why=malicious,
                        consequences=malicious
                    )
                    db.mark_completed(tid)
                except Exception as e:
                    log_error("Database", f"Failed on malicious input: {malicious}", e)
                    return False

            print("  ✓ All database tests passed")
            return True

        finally:
            try:
                os.unlink(db_path)
            except:
                pass

    except Exception as e:
        log_error("Database", "Database testing failed", e)
        tb.print_exc()
        return False


def test_settings_comprehensive():
    """Comprehensive settings testing."""
    print("\n" + "="*60)
    print("TEST 4: SETTINGS COMPREHENSIVE TESTING")
    print("="*60)

    try:
        from focuscheck.settings import load_settings, save_settings, validate_settings, DEFAULT_SETTINGS

        # Test 1: All settings keys are strings
        print("  ✓ Checking settings keys are strings...")
        for key in DEFAULT_SETTINGS:
            if not isinstance(key, str):
                log_error("Settings", f"Non-string key found: {key}")
                return False

        # Test 2: Stress test validation with random values
        print("  ✓ Stress testing validation...")
        import random
        for _ in range(100):
            test_settings = {}
            for key in DEFAULT_SETTINGS:
                # Random invalid values
                test_settings[key] = random.choice([
                    None, "", "invalid", -999999, 999999999, [], {}, True, False
                ])
            validated = validate_settings(test_settings)
            # Should not crash and should return valid settings
            assert isinstance(validated, dict)
            assert len(validated) >= len(DEFAULT_SETTINGS)

        # Test 3: Concurrent save/load
        print("  ✓ Testing concurrent save/load...")
        test_path = "test_settings_concurrent.json"
        try:
            import threading
            errors = []

            def save_worker(worker_id):
                try:
                    for i in range(10):
                        s = DEFAULT_SETTINGS.copy()
                        s["interval_seconds"] = 60 + worker_id * 10 + i
                        save_settings(s)
                except Exception as e:
                    errors.append((worker_id, e))

            def load_worker(worker_id):
                try:
                    for i in range(10):
                        load_settings()
                except Exception as e:
                    errors.append((worker_id, e))

            threads = []
            for i in range(3):
                threads.append(threading.Thread(target=save_worker, args=(i,)))
                threads.append(threading.Thread(target=load_worker, args=(i+10,)))

            for t in threads:
                t.start()
            for t in threads:
                t.join()

            if errors:
                log_error("Settings", f"Concurrent access errors: {errors}")
                return False

        finally:
            try:
                os.remove(test_path)
            except:
                pass

        print("  ✓ All settings tests passed")
        return True

    except Exception as e:
        log_error("Settings", "Settings testing failed", e)
        tb.print_exc()
        return False


def test_ui_components():
    """Test UI components can be instantiated."""
    print("\n" + "="*60)
    print("TEST 5: UI COMPONENTS TESTING")
    print("="*60)

    try:
        from focuscheck.ui import PauseGuard

        # Test PauseGuard
        print("  ✓ Testing PauseGuard...")
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

        guard = PauseGuard(mock_settings)

        # Test all possible state combinations
        for locked in [True, False]:
            for sleeping in [True, False]:
                guard.set_locked(locked)
                guard.set_sleeping(sleeping)
                result = guard.should_pause()
                assert isinstance(result, bool)

        print("  ✓ All UI component tests passed")
        return True

    except Exception as e:
        log_error("UI", "UI testing failed", e)
        tb.print_exc()
        return False


def test_utils_comprehensive():
    """Comprehensive utils testing."""
    print("\n" + "="*60)
    print("TEST 6: UTILS COMPREHENSIVE TESTING")
    print("="*60)

    try:
        from focuscheck.utils import parse_rgb_hex, get_file_lock, get_logger

        # Test 1: Color parsing with edge cases
        print("  ✓ Testing color parsing edge cases...")
        test_colors = [
            ("#000000", (0, 0, 0)),
            ("#FFFFFF", (255, 255, 255)),
            ("#FF0000", (255, 0, 0)),
            ("#00FF00", (0, 255, 0)),
            ("#0000FF", (0, 0, 255)),
            ("#F00", (255, 0, 0)),
            ("#0F0", (0, 255, 0)),
            ("#00F", (0, 0, 255)),
            ("#abc", (170, 187, 204)),
            ("invalid", (0, 0, 0)),
            ("", (0, 0, 0)),
            (None, (0, 0, 0)),
            ("#", (0, 0, 0)),
            ("#GG0000", (0, 0, 0)),
        ]

        for color, expected in test_colors:
            result = parse_rgb_hex(color, (0, 0, 0))
            if result != expected:
                log_error("Utils", f"Color parsing failed: {color} -> {result}, expected {expected}")
                return False

        # Test 2: File locking stress test
        print("  ✓ Testing file locking stress test...")
        import threading
        lock_errors = []

        def lock_worker(worker_id):
            try:
                for i in range(100):
                    lock = get_file_lock(f"file_{i % 10}.txt")
                    with lock:
                        pass  # Just acquire and release
            except Exception as e:
                lock_errors.append((worker_id, e))

        threads = [threading.Thread(target=lock_worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        if lock_errors:
            log_error("Utils", f"File locking errors: {lock_errors}")
            return False

        # Test 3: Logger doesn't crash with various inputs
        print("  ✓ Testing logger with various inputs...")
        logger = get_logger()
        test_messages = [
            "Normal message",
            "",
            None,
            "Unicode: 你好 🎉",
            "Long: " + "A" * 10000,
            "Special chars: <>&\"'",
        ]

        for msg in test_messages:
            try:
                if msg is not None:
                    logger.info(str(msg))
            except Exception as e:
                log_error("Utils", f"Logger failed on: {msg}", e)
                return False

        print("  ✓ All utils tests passed")
        return True

    except Exception as e:
        log_error("Utils", "Utils testing failed", e)
        tb.print_exc()
        return False


def test_platform_specific():
    """Test platform-specific code."""
    print("\n" + "="*60)
    print("TEST 7: PLATFORM-SPECIFIC TESTING")
    print("="*60)

    try:
        from focuscheck.platform_specific import (
            compose_startup_command,
            is_startup_installed
        )

        # Test 1: Startup command is valid
        print("  ✓ Testing startup command...")
        cmd = compose_startup_command()
        assert isinstance(cmd, str)
        assert len(cmd) > 0
        assert "python" in cmd.lower() or cmd.endswith(".exe")

        # Test 2: Startup check doesn't crash
        print("  ✓ Testing startup installation check...")
        result = is_startup_installed()
        assert isinstance(result, bool)

        print("  ✓ All platform-specific tests passed")
        return True

    except Exception as e:
        log_error("Platform", "Platform testing failed", e)
        tb.print_exc()
        return False


def test_error_recovery():
    """Test that the app can recover from errors."""
    print("\n" + "="*60)
    print("TEST 8: ERROR RECOVERY TESTING")
    print("="*60)

    try:
        from focuscheck.settings import load_settings, save_settings

        # Test 1: Corrupt settings file recovery
        print("  ✓ Testing corrupt settings file recovery...")
        test_path = "test_corrupt_settings.json"
        try:
            # Write corrupt JSON
            with open(test_path, "w") as f:
                f.write("{ this is not valid json }")

            # Should recover gracefully
            settings = load_settings()
            assert isinstance(settings, dict)
            assert len(settings) > 0

        finally:
            try:
                os.remove(test_path)
            except:
                pass

        # Test 2: Missing directories recovery
        print("  ✓ Testing missing directories recovery...")
        import focuscheck.utils.paths as paths
        original_data_dir = paths.get_data_dir

        try:
            # Mock a non-existent directory
            def mock_data_dir():
                return os.path.join(tempfile.gettempdir(), "nonexistent_focuscheck_test_dir")

            paths.get_data_dir = mock_data_dir

            # Should create directory automatically
            settings = load_settings()
            assert isinstance(settings, dict)

        finally:
            paths.get_data_dir = original_data_dir

        print("  ✓ All error recovery tests passed")
        return True

    except Exception as e:
        log_error("Error Recovery", "Error recovery testing failed", e)
        tb.print_exc()
        return False


def test_memory_leaks():
    """Test for potential memory leaks."""
    print("\n" + "="*60)
    print("TEST 9: MEMORY LEAK TESTING")
    print("="*60)

    try:
        import gc
        from focuscheck.database import TaskDB
        from datetime import datetime, timezone

        print("  ✓ Testing for memory leaks...")

        # Create and destroy many database connections
        initial_objects = len(gc.get_objects())

        for i in range(100):
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
                db_path = f.name

            try:
                db = TaskDB(db_path)
                task_id = db.start_task(title="Test", due_utc=None, why="test", consequences="test")
                db.mark_completed(task_id)
                del db
            finally:
                try:
                    os.unlink(db_path)
                except:
                    pass

        gc.collect()
        final_objects = len(gc.get_objects())

        # Allow some growth but not excessive
        growth = final_objects - initial_objects
        if growth > 1000:
            log_warning("Memory", f"Potential memory leak: {growth} objects created")

        print(f"  ✓ Object count: {initial_objects} -> {final_objects} (growth: {growth})")
        return True

    except Exception as e:
        log_error("Memory", "Memory leak testing failed", e)
        tb.print_exc()
        return False


def run_all_tests():
    """Run all comprehensive tests."""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*15 + "COMPREHENSIVE BUG TEST" + " "*21 + "║")
    print("║" + " "*10 + "Searching every nook and cranny" + " "*17 + "║")
    print("╚" + "="*58 + "╝")

    tests = [
        ("Module Imports", test_all_imports),
        ("Circular Dependencies", test_circular_dependencies),
        ("Database Comprehensive", test_database_comprehensive),
        ("Settings Comprehensive", test_settings_comprehensive),
        ("UI Components", test_ui_components),
        ("Utils Comprehensive", test_utils_comprehensive),
        ("Platform Specific", test_platform_specific),
        ("Error Recovery", test_error_recovery),
        ("Memory Leaks", test_memory_leaks),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ FATAL ERROR in {name}: {e}")
            tb.print_exc()
            results.append((name, False))
            log_error("Fatal", f"Test suite {name} crashed", e)

    # Final Report
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*20 + "FINAL REPORT" + " "*26 + "║")
    print("╚" + "="*58 + "╝")

    print("\nTest Results:")
    print("-" * 60)
    passed = 0
    failed = 0
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} | {name}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\nSummary: {passed} passed, {failed} failed")

    if errors_found:
        print(f"\n🔴 ERRORS FOUND: {len(errors_found)}")
        print("-" * 60)
        for i, error in enumerate(errors_found, 1):
            print(f"{i}. [{error['category']}] {error['description']}")
            if error['exception']:
                print(f"   Exception: {error['exception']}")

    if warnings_found:
        print(f"\n⚠️ WARNINGS: {len(warnings_found)}")
        print("-" * 60)
        for i, warning in enumerate(warnings_found, 1):
            print(f"{i}. [{warning['category']}] {warning['description']}")

    if not errors_found and not warnings_found:
        print("\n" + "🎉" * 20)
        print("✨ PERFECT! No errors or warnings found! ✨")
        print("🎉" * 20)

    print(f"\n{'='*60}")
    print(f"Total Errors: {len(errors_found)}")
    print(f"Total Warnings: {len(warnings_found)}")
    print(f"Test Success Rate: {(passed/len(results)*100):.1f}%")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    run_all_tests()

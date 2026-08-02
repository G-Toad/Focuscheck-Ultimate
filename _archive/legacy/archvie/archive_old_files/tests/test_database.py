"""Test database modules for errors."""

import sys
import os
import tempfile
from datetime import datetime, timezone, timedelta

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')

# Add focuscheck to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from focuscheck.database import TaskDB, ensure_log_header, append_log, ensure_waste_log_header, append_waste_log

def test_task_db():
    """Test TaskDB functionality."""
    print("Testing TaskDB...")

    # Use temp database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        db = TaskDB(db_path)

        # Test 1: Start a task
        print("  ✓ Creating task...")
        task_id = db.start_task(
            title="Test Task",
            due_utc=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            why="Testing",
            consequences="None"
        )
        print(f"  ✓ Created task {task_id}")

        # Test 2: Get active task
        print("  ✓ Getting active task...")
        active = db.get_active()
        print(f"  ✓ Active task: {active}")
        if active:
            print(f"    - Has 'timed_out' field: {'timed_out' in active}")

        # Test 3: Mark completed
        print("  ✓ Marking task completed...")
        db.mark_completed(task_id)
        print("  ✓ Task marked completed")

        # Test 4: Start another task and fail it
        print("  ✓ Creating task to fail...")
        task_id2 = db.start_task(
            title="Fail Task",
            due_utc=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            why="Testing failure",
            consequences="None"
        )
        print("  ✓ Marking task failed with timeout...")
        db.mark_failed(task_id2, timed_out=True)
        print("  ✓ Task marked failed")

        # Test 5: Analytics
        print("  ✓ Getting analytics...")
        stats_lifetime = db.analytics_counts(timescale="lifetime")
        print(f"  ✓ Lifetime stats: {stats_lifetime}")

        stats_7d = db.analytics_counts(timescale="7d")
        print(f"  ✓ 7-day stats: {stats_7d}")

        # Test 6: List history
        print("  ✓ Getting task history...")
        history = db.list_history(limit=10)
        print(f"  ✓ History count: {len(history)}")
        for task in history:
            print(f"    - {task['title']}: {task['status']} (timed_out: {task.get('timed_out', 'MISSING')})")

        # Test 7: Waste event
        print("  ✓ Recording waste event...")
        waste_id = db.record_waste_event(
            what="Browsing Reddit",
            consequences="Lost time",
            active_task_id=task_id
        )
        print(f"  ✓ Waste event recorded: {waste_id}")

        # Test 8: Changed task
        print("  ✓ Creating task to change...")
        task_id3 = db.start_task(
            title="Change Task",
            due_utc=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            why="Testing change",
            consequences="None"
        )
        db.mark_changed(task_id3, "Changed my mind")
        print("  ✓ Task marked changed")

        # Test 9: Overdue check
        print("  ✓ Creating overdue task...")
        task_id4 = db.start_task(
            title="Overdue Task",
            due_utc=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            why="Testing overdue",
            consequences="None"
        )
        affected = db.overdue_active_to_failed()
        print(f"  ✓ Overdue tasks failed: {affected}")

        print("\n✅ TaskDB tests passed!")

    except Exception as e:
        print(f"\n❌ TaskDB test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        try:
            os.unlink(db_path)
        except:
            pass

    return True

def test_csv_logger():
    """Test CSV logger functionality."""
    print("\nTesting CSV Logger...")

    try:
        # Test log header
        print("  ✓ Ensuring log header...")
        ensure_log_header()
        print("  ✓ Log header created")

        # Test waste log header
        print("  ✓ Ensuring waste log header...")
        ensure_waste_log_header()
        print("  ✓ Waste log header created")

        # Test append log
        print("  ✓ Appending to log...")
        import time
        slot_start_dt = {
            "mono_start": time.monotonic(),
            "utc_start": datetime.now(timezone.utc),
            "local_minute": datetime.now().strftime("%Y-%m-%d %H:%M")
        }

        settings = {
            "interval_seconds": 30,
            "intensify_after_seconds": 120,
            "overdrive_after_seconds": 300
        }

        append_log(
            response="STUDYING",
            latency_ms=500,
            settings=settings,
            intensity_level_reached=2,
            slot_start_dt=slot_start_dt,
            overdrive_deadline_s=300
        )
        print("  ✓ Log entry appended")

        # Test append waste log
        print("  ✓ Appending to waste log...")
        append_waste_log(
            slot_start_dt=slot_start_dt,
            latency_ms=1000,
            what="Testing",
            consequences="None",
            active_task={"id": 1, "title": "Test Task"}
        )
        print("  ✓ Waste log entry appended")

        print("\n✅ CSV Logger tests passed!")

    except Exception as e:
        print(f"\n❌ CSV Logger test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE MODULE TESTING")
    print("=" * 60)

    results = []
    results.append(("TaskDB", test_task_db()))
    results.append(("CSV Logger", test_csv_logger()))

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name}: {status}")

    all_passed = all(r[1] for r in results)
    print("\n" + ("🎉 All tests passed!" if all_passed else "⚠️ Some tests failed!"))

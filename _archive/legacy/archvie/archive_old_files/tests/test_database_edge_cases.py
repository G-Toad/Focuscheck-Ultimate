"""Test database edge cases and potential bugs."""

import sys
import os
import tempfile
from datetime import datetime, timezone, timedelta

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')

# Add focuscheck to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from focuscheck.database import TaskDB

def test_edge_cases():
    """Test edge cases that might cause bugs."""
    print("Testing Edge Cases...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        db = TaskDB(db_path)

        # Test 1: Empty strings
        print("  ✓ Test 1: Empty strings...")
        task_id = db.start_task(
            title="",
            due_utc="",
            why="",
            consequences=""
        )
        active = db.get_active()
        print(f"    - Created task with empty strings: {active['id']}")
        db.mark_completed(task_id)

        # Test 2: None values
        print("  ✓ Test 2: None values...")
        task_id = db.start_task(
            title="Test",
            due_utc=None,
            why=None,
            consequences=None
        )
        active = db.get_active()
        print(f"    - Created task with None values: {active['id']}")
        db.mark_completed(task_id)

        # Test 3: Very long strings
        print("  ✓ Test 3: Very long strings...")
        long_text = "A" * 10000
        task_id = db.start_task(
            title=long_text,
            due_utc=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            why=long_text,
            consequences=long_text
        )
        active = db.get_active()
        print(f"    - Created task with long strings: {active['id']}")
        db.mark_completed(task_id)

        # Test 4: Unicode/special characters
        print("  ✓ Test 4: Unicode/special characters...")
        task_id = db.start_task(
            title="Test 你好 🎉 <>&\"'",
            due_utc=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            why="Testing 你好",
            consequences="Some 🎉 consequences"
        )
        active = db.get_active()
        print(f"    - Created task with unicode: {active['title']}")
        db.mark_completed(task_id)

        # Test 5: Invalid ISO date
        print("  ✓ Test 5: Invalid ISO date...")
        task_id = db.start_task(
            title="Invalid date",
            due_utc="not-a-date",
            why="Test",
            consequences="Test"
        )
        active = db.get_active()
        print(f"    - Created task with invalid date: {active['due_utc']}")
        db.mark_completed(task_id)

        # Test 6: Mark non-existent task as completed
        print("  ✓ Test 6: Mark non-existent task...")
        db.mark_completed(99999)
        print("    - No error when marking non-existent task")

        # Test 7: Mark already completed task as failed
        print("  ✓ Test 7: Mark completed task as failed...")
        task_id = db.start_task(
            title="Double status change",
            due_utc=None,
            why="Test",
            consequences="Test"
        )
        db.mark_completed(task_id)
        db.mark_failed(task_id, timed_out=True)
        print("    - No error when changing completed to failed")

        # Test 8: Concurrent access simulation
        print("  ✓ Test 8: Multiple get_active calls...")
        task_id = db.start_task(
            title="Concurrent",
            due_utc=None,
            why="Test",
            consequences="Test"
        )
        active1 = db.get_active()
        active2 = db.get_active()
        active3 = db.get_active()
        print(f"    - All calls returned same task: {active1['id'] == active2['id'] == active3['id']}")
        db.mark_completed(task_id)

        # Test 9: Analytics with no tasks
        print("  ✓ Test 9: Analytics on empty database...")
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            empty_db_path = f.name
        empty_db = TaskDB(empty_db_path)
        stats = empty_db.analytics_counts(timescale="lifetime")
        print(f"    - Empty DB stats: {stats}")
        os.unlink(empty_db_path)

        # Test 10: Waste event with None values
        print("  ✓ Test 10: Waste event with None values...")
        waste_id = db.record_waste_event(
            what=None,
            consequences=None,
            active_task_id=None
        )
        print(f"    - Waste event with None values: {waste_id}")

        print("\n✅ All edge case tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Edge case test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            os.unlink(db_path)
        except:
            pass

if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE EDGE CASE TESTING")
    print("=" * 60)

    success = test_edge_cases()

    print("\n" + ("🎉 Success!" if success else "⚠️ Failed!"))

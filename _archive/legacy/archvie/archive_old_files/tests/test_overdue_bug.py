"""Test potential bug in overdue_active_to_failed."""

import sys
import os
import tempfile
from datetime import datetime, timezone, timedelta

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')

# Add focuscheck to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from focuscheck.database import TaskDB

def test_overdue_with_invalid_date():
    """Test overdue check with invalid ISO date."""
    print("Testing overdue_active_to_failed with invalid dates...")

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        db = TaskDB(db_path)

        # Create task with invalid date
        print("  ✓ Creating task with invalid date...")
        task_id1 = db.start_task(
            title="Invalid date task",
            due_utc="not-a-valid-date",
            why="Test",
            consequences="Test"
        )

        # Create task with None date
        print("  ✓ Creating task with None date...")
        task_id2 = db.start_task(
            title="None date task",
            due_utc=None,
            why="Test",
            consequences="Test"
        )

        # Create task with valid overdue date
        print("  ✓ Creating task with valid overdue date...")
        task_id3 = db.start_task(
            title="Overdue task",
            due_utc=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            why="Test",
            consequences="Test"
        )

        # Create task with valid future date
        print("  ✓ Creating task with valid future date...")
        task_id4 = db.start_task(
            title="Future task",
            due_utc=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            why="Test",
            consequences="Test"
        )

        print("\n  ✓ Running overdue check...")
        affected = db.overdue_active_to_failed()
        print(f"    - Tasks marked as failed: {affected}")

        # Check status of all tasks
        print("\n  ✓ Checking task statuses...")
        history = db.list_history(limit=10, include_active=True)
        for task in history:
            print(f"    - Task {task['id']} ({task['title']}): {task['status']}")

        # Verify correct behavior
        expected_failed = [task_id3]  # Only the valid overdue task should be failed
        if set(affected) == set(expected_failed):
            print("\n✅ Correct! Only valid overdue task was marked as failed")
            return True
        else:
            print(f"\n⚠️ Unexpected result! Expected {expected_failed}, got {affected}")
            return False

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
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
    print("OVERDUE BUG TEST")
    print("=" * 60)

    success = test_overdue_with_invalid_date()

    print("\n" + ("🎉 Test passed!" if success else "⚠️ Test failed!"))

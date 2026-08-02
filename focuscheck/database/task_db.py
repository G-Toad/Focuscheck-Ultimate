"""Task database using SQLite."""

import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from ..utils.logging_utils import log_exception


class TaskDB:
    """Manages tasks and sessions in SQLite database."""
    
    def __init__(self, path):
        self.path = path
        self._ensure_schema()

    @contextmanager
    def _conn(self):
        con = sqlite3.connect(self.path, timeout=30)
        try:
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA synchronous=FULL")
            con.execute("PRAGMA foreign_keys=ON")
        except Exception:
            pass
        try:
            yield con
        finally:
            con.close()

    def _ensure_schema(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
        except Exception:
            pass
        try:
            with self._conn() as con:
                cur = con.cursor()
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_utc TEXT NOT NULL,
                        title TEXT NOT NULL,
                        why TEXT,
                        consequences TEXT,
                        due_utc TEXT,
                        status TEXT NOT NULL,
                        completed_utc TEXT,
                        change_reason TEXT
                    )
                    """
                )
                cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_utc)")
                cur.execute("PRAGMA table_info(tasks)")
                cols = [r[1] for r in cur.fetchall()]
                if "timed_out" not in cols:
                    cur.execute("ALTER TABLE tasks ADD COLUMN timed_out INTEGER NOT NULL DEFAULT 0")
                # Repair legacy databases before enforcing the one-active-task
                # invariant; retain the newest active row as authoritative.
                cur.execute(
                    "UPDATE tasks SET status='changed', change_reason='reconciled duplicate active task' "
                    "WHERE status='active' AND id != (SELECT MAX(id) FROM tasks WHERE status='active')"
                )
                cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_one_active ON tasks(status) WHERE status = 'active'")
                # Waste events table (what the user was wasting time on)
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS waste_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_utc TEXT NOT NULL,
                        what TEXT,
                        consequences TEXT,
                        active_task_id INTEGER
                    )
                    """
                )
                cur.execute("CREATE INDEX IF NOT EXISTS idx_waste_created ON waste_events(created_utc)")
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS focus_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_utc TEXT NOT NULL,
                        doing TEXT,
                        benefits TEXT,
                        active_task_id INTEGER
                    )
                    """
                )
                cur.execute("CREATE INDEX IF NOT EXISTS idx_focus_created ON focus_events(created_utc)")
                cur.execute("PRAGMA user_version")
                schema_version = int(cur.fetchone()[0] or 0)
                if schema_version < 1:
                    cur.execute("PRAGMA user_version = 1")
                con.commit()
        except Exception as exc:
            log_exception("TaskDB: failed ensuring schema")
            raise RuntimeError(f"TaskDB schema initialization failed: {exc}") from exc

    def get_active(self):
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("SELECT id, created_utc, title, why, consequences, due_utc, status, completed_utc, change_reason FROM tasks WHERE status = 'active' ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            return self._row_to_dict(row) if row else None

    def start_task(self, *, title, due_utc, why, consequences):
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as con:
            cur = con.cursor()
            cur.execute(
                "UPDATE tasks SET status='changed', completed_utc=?, change_reason=? WHERE status='active'",
                (now, "replaced by new active task"),
            )
            cur.execute(
                "INSERT INTO tasks(created_utc, title, why, consequences, due_utc, status) VALUES (?,?,?,?,?, 'active')",
                (now, title, why, consequences, due_utc)
            )
            con.commit()
            return cur.lastrowid

    def mark_completed(self, task_id, when_utc=None):
        if when_utc is None:
            when_utc = datetime.now(timezone.utc).isoformat()
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("UPDATE tasks SET status='completed', completed_utc=? WHERE id=? AND status='active'", (when_utc, task_id))
            con.commit()
            return cur.rowcount == 1

    def mark_failed(self, task_id, when_utc=None, timed_out=False):
        if when_utc is None:
            when_utc = datetime.now(timezone.utc).isoformat()
        with self._conn() as con:
            cur = con.cursor()
            try:
                cur.execute("UPDATE tasks SET status='failed', completed_utc=?, timed_out=? WHERE id=? AND status = 'active'", (when_utc, 1 if timed_out else 0, task_id))
            except Exception:
                # Fallback for DBs without timed_out column
                cur.execute("UPDATE tasks SET status='failed', completed_utc=? WHERE id=? AND status = 'active'", (when_utc, task_id))
            con.commit()
            return cur.rowcount == 1

    def mark_changed(self, task_id, reason):
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("UPDATE tasks SET status='changed', change_reason=? WHERE id=? AND status='active'", (reason, task_id))
            con.commit()
            return cur.rowcount == 1

    def _row_to_dict(self, row):
        if not row:
            return None
        keys = ["id","created_utc","title","why","consequences","due_utc","status","completed_utc","change_reason"]
        return dict(zip(keys, row))

    def overdue_active_to_failed(self):
        now_iso = datetime.now(timezone.utc).isoformat()
        affected = []
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("SELECT id, due_utc FROM tasks WHERE status='active' AND due_utc IS NOT NULL")
            for tid, due_iso in cur.fetchall():
                try:
                    if not due_iso:
                        continue
                    due = datetime.fromisoformat(due_iso)
                    if due.tzinfo is None:
                        due = due.replace(tzinfo=timezone.utc)
                    else:
                        due = due.astimezone(timezone.utc)
                    if datetime.now(timezone.utc) > due:
                        cur.execute("UPDATE tasks SET status='failed', completed_utc=? WHERE id=? AND status='active'", (now_iso, tid))
                        if cur.rowcount == 1:
                            affected.append(tid)
                except (TypeError, ValueError, OverflowError):
                    continue
            con.commit()
        return affected

    def analytics_counts(self, *, timescale="lifetime", treat_changed_as_fail=True):
        where = ""
        params = []
        now = datetime.now(timezone.utc)
        if timescale == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            where = "WHERE datetime(created_utc) >= datetime(?)"
            params = [start.isoformat()]
        elif timescale == "7d":
            start = now - timedelta(days=7)
            where = "WHERE datetime(created_utc) >= datetime(?)"
            params = [start.isoformat()]
        elif timescale == "30d":
            start = now - timedelta(days=30)
            where = "WHERE datetime(created_utc) >= datetime(?)"
            params = [start.isoformat()]

        q = f"SELECT status, COUNT(*) FROM tasks {where} GROUP BY status"
        stats = {"completed": 0, "failed": 0, "changed": 0}
        with self._conn() as con:
            cur = con.cursor()
            cur.execute(q, params)
            for status, cnt in cur.fetchall():
                status = status or ""
                if status in stats:
                    stats[status] = int(cnt)
            # timed_out count
            try:
                tq = f"SELECT COALESCE(SUM(timed_out),0) FROM tasks {where}"
                cur.execute(tq, params)
                timed_out = int(cur.fetchone()[0] or 0)
            except Exception:
                timed_out = 0
        total_failed = stats["failed"] + (stats["changed"] if treat_changed_as_fail else 0)
        return {"completed": stats["completed"], "failed": total_failed, "changed": stats["changed"], "timed_out": timed_out}

    def list_history(self, limit=100, include_active=True):
        """Return recent tasks as a list of dicts."""
        where = ""
        params = []
        if not include_active:
            where = "WHERE status != 'active'"
        q = (
            "SELECT id, created_utc, title, why, consequences, due_utc, status, "
            "completed_utc, change_reason, "
            "CASE WHEN typeof(timed_out) IS NULL THEN 0 ELSE COALESCE(timed_out,0) END as timed_out "
            f"FROM tasks {where} ORDER BY id DESC LIMIT ?"
        )
        params.append(int(limit))
        rows = []
        with self._conn() as con:
            cur = con.cursor()
            try:
                cur.execute(q, params)
            except Exception:
                # Fallback for DBs without timed_out column
                q2 = (
                    "SELECT id, created_utc, title, why, consequences, due_utc, status, "
                    "completed_utc, change_reason FROM tasks "
                    f"{where} ORDER BY id DESC LIMIT ?"
                )
                cur.execute(q2, params)
            cols = [c[0] for c in cur.description]
            for r in cur.fetchall():
                d = {k: r[i] for i, k in enumerate(cols)}
                # Normalize timed_out presence
                if "timed_out" not in d:
                    d["timed_out"] = 0
                rows.append(d)
        return rows

    def record_waste_event(self, *, what, consequences, active_task_id=None, when_utc=None):
        try:
            if when_utc is None:
                when_utc = datetime.now(timezone.utc).isoformat()
            with self._conn() as con:
                cur = con.cursor()
                cur.execute(
                    "INSERT INTO waste_events(created_utc, what, consequences, active_task_id) VALUES (?,?,?,?)",
                    (when_utc, (what or ""), (consequences or ""), active_task_id)
                )
                con.commit()
                return cur.lastrowid
        except Exception:
            log_exception("TaskDB: record_waste_event failed")
            return None


    def record_focus_event(self, *, doing, benefits, active_task_id=None, when_utc=None):
        try:
            if when_utc is None:
                when_utc = datetime.now(timezone.utc).isoformat()
            with self._conn() as con:
                cur = con.cursor()
                cur.execute(
                    "INSERT INTO focus_events(created_utc, doing, benefits, active_task_id) VALUES (?,?,?,?)",
                    (when_utc, (doing or ""), (benefits or ""), active_task_id)
                )
                con.commit()
                return cur.lastrowid
        except Exception:
            log_exception("TaskDB: record_focus_event failed")
            return None

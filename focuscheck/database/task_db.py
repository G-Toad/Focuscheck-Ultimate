"""Task database using SQLite."""

import sqlite3
import os
import shutil
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from ..utils.logging_utils import log_exception


CURRENT_TASK_SCHEMA_VERSION = 4
MAX_TASK_TEXT_LENGTH = 8192
MAX_TASK_REASON_LENGTH = 2048


def _contains_symlink_component(path) -> bool:
    current = os.path.abspath(os.fspath(path))
    while True:
        if os.path.islink(current):
            return True
        parent = os.path.dirname(current)
        if parent == current:
            return False
        current = parent


def _normalize_utc(value, *, allow_none=False):
    """Normalize external timestamps to an explicit UTC ISO-8601 value."""
    if value is None and allow_none:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value or "").strip()
        if not text:
            if allow_none:
                return None
            raise ValueError("timestamp must not be empty")
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"invalid timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _bounded_text(value, field, *, required=False, limit=MAX_TASK_TEXT_LENGTH):
    """Validate user-authored task text before it reaches SQLite."""
    if value is None:
        if required:
            raise ValueError(f"{field} must not be empty")
        return None
    text = str(value)
    if required and not text.strip():
        raise ValueError(f"{field} must not be empty")
    if len(text) > limit:
        raise ValueError(f"{field} exceeds the {limit}-character limit")
    return text


class TaskDB:
    """Manages tasks and sessions in SQLite database."""
    
    def __init__(self, path, clock=None, event_sink=None):
        self.path = path
        self._clock = clock
        self._event_sink = event_sink
        self.pre_migration_backup = None
        self._ensure_schema()

    def _emit_transition(self, operation, outcome, **fields):
        """Report task lifecycle metadata without affecting persistence."""
        if not callable(self._event_sink):
            return
        try:
            self._event_sink({
                "event": "task_transition",
                "operation": operation,
                "outcome": outcome,
                **fields,
            })
        except Exception:
            # Diagnostics must never change the transaction result.
            pass

    def _now_utc(self):
        """Return the injected UTC clock value or the system UTC time."""
        source = self._clock
        if source is None:
            value = datetime.now(timezone.utc)
        elif callable(source):
            value = source()
        else:
            value = source.now_utc()
        if not isinstance(value, datetime):
            raise TypeError("TaskDB clock must return datetime")
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

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
        self._prepare_migration_safety_copy()
        try:
            with self._conn() as con:
                # Schema inspection and migration are a single writer
                # transaction. Without this lock, concurrent first opens can
                # both observe a missing column and race into ALTER TABLE.
                con.execute("BEGIN IMMEDIATE")
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
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS schema_migrations ("
                    "version INTEGER PRIMARY KEY, applied_utc TEXT NOT NULL)"
                )
                if schema_version < 1:
                    cur.execute("PRAGMA user_version = 1")
                    cur.execute(
                        "INSERT OR IGNORE INTO schema_migrations(version, applied_utc) VALUES (?, ?)",
                        (1, self._now_utc().isoformat()),
                    )
                if schema_version < 2:
                    # Version 2 records the active-task invariant and the
                    # timed-out transition in the durable migration journal.
                    cur.execute(
                        "INSERT OR IGNORE INTO schema_migrations(version, applied_utc) VALUES (?, ?)",
                        (2, self._now_utc().isoformat()),
                    )
                    cur.execute("PRAGMA user_version = 2")
                if schema_version < CURRENT_TASK_SCHEMA_VERSION:
                    # Normalize recoverable legacy timestamps and make invalid
                    # due dates visible instead of silently exempting tasks.
                    cur.execute(
                        "SELECT id, created_utc, due_utc, completed_utc, change_reason FROM tasks"
                    )
                    for task_id, created_utc, due_utc, completed_utc, reason in cur.fetchall():
                        updates = {}
                        reasons = []
                        for column, value, allow_none in (
                            ("created_utc", created_utc, False),
                            ("due_utc", due_utc, True),
                            ("completed_utc", completed_utc, True),
                        ):
                            if value is None and allow_none:
                                continue
                            try:
                                normalized = _normalize_utc(value, allow_none=allow_none)
                            except ValueError:
                                if column == "created_utc":
                                    reasons.append("legacy invalid created_utc retained")
                                else:
                                    updates[column] = None
                                    reasons.append(f"legacy invalid {column} cleared")
                                continue
                            if normalized != value:
                                updates[column] = normalized
                        if reasons:
                            existing = str(reason or "").strip()
                            marker = "; ".join(reasons)
                            updates["change_reason"] = f"{existing}; {marker}".strip("; ")
                        if updates:
                            assignments = ", ".join(f"{column}=?" for column in updates)
                            cur.execute(
                                f"UPDATE tasks SET {assignments} WHERE id=?",
                                (*updates.values(), task_id),
                            )
                    cur.execute(
                        "INSERT OR IGNORE INTO schema_migrations(version, applied_utc) VALUES (?, ?)",
                        (3, self._now_utc().isoformat()),
                    )
                    cur.execute(f"PRAGMA user_version = {CURRENT_TASK_SCHEMA_VERSION}")
                # Version 4 adds validation triggers without rebuilding the
                # table, so legacy rows remain intact while future writes are
                # bounded and restricted to the documented state machine.
                if schema_version < 4:
                    cur.execute(
                        "UPDATE tasks SET status='changed', "
                        "change_reason=CASE WHEN NULLIF(change_reason, '') IS NULL "
                        "THEN 'reconciled invalid legacy task status' "
                        "ELSE change_reason || '; reconciled invalid legacy task status' END "
                        "WHERE status NOT IN ('active', 'completed', 'failed', 'changed')"
                    )
                    cur.execute(
                        "INSERT OR IGNORE INTO schema_migrations(version, applied_utc) VALUES (?, ?)",
                        (4, self._now_utc().isoformat()),
                    )
                    cur.execute("PRAGMA user_version = 4")
                cur.executescript(
                    f"""
                    CREATE TRIGGER IF NOT EXISTS tasks_validate_insert
                    BEFORE INSERT ON tasks
                    WHEN NEW.status NOT IN ('active', 'completed', 'failed', 'changed')
                      OR NEW.title IS NULL OR length(NEW.title) > {MAX_TASK_TEXT_LENGTH}
                      OR (NEW.why IS NOT NULL AND length(NEW.why) > {MAX_TASK_TEXT_LENGTH})
                      OR (NEW.consequences IS NOT NULL AND length(NEW.consequences) > {MAX_TASK_TEXT_LENGTH})
                      OR (NEW.change_reason IS NOT NULL AND length(NEW.change_reason) > {MAX_TASK_REASON_LENGTH})
                    BEGIN
                        SELECT RAISE(ABORT, 'task row violates status or text policy');
                    END;
                    CREATE TRIGGER IF NOT EXISTS tasks_validate_update
                    BEFORE UPDATE OF status, title, why, consequences, change_reason ON tasks
                    WHEN NEW.status NOT IN ('active', 'completed', 'failed', 'changed')
                      OR NEW.title IS NULL OR length(NEW.title) > {MAX_TASK_TEXT_LENGTH}
                      OR (NEW.why IS NOT NULL AND length(NEW.why) > {MAX_TASK_TEXT_LENGTH})
                      OR (NEW.consequences IS NOT NULL AND length(NEW.consequences) > {MAX_TASK_TEXT_LENGTH})
                      OR (NEW.change_reason IS NOT NULL AND length(NEW.change_reason) > {MAX_TASK_REASON_LENGTH})
                    BEGIN
                        SELECT RAISE(ABORT, 'task row violates status or text policy');
                    END;
                    CREATE TRIGGER IF NOT EXISTS waste_events_validate_insert
                    BEFORE INSERT ON waste_events
                    WHEN (NEW.what IS NOT NULL AND length(NEW.what) > {MAX_TASK_TEXT_LENGTH})
                      OR (NEW.consequences IS NOT NULL AND length(NEW.consequences) > {MAX_TASK_TEXT_LENGTH})
                    BEGIN
                        SELECT RAISE(ABORT, 'waste event violates text policy');
                    END;
                    CREATE TRIGGER IF NOT EXISTS waste_events_validate_update
                    BEFORE UPDATE OF what, consequences ON waste_events
                    WHEN (NEW.what IS NOT NULL AND length(NEW.what) > {MAX_TASK_TEXT_LENGTH})
                      OR (NEW.consequences IS NOT NULL AND length(NEW.consequences) > {MAX_TASK_TEXT_LENGTH})
                    BEGIN
                        SELECT RAISE(ABORT, 'waste event violates text policy');
                    END;
                    CREATE TRIGGER IF NOT EXISTS focus_events_validate_insert
                    BEFORE INSERT ON focus_events
                    WHEN (NEW.doing IS NOT NULL AND length(NEW.doing) > {MAX_TASK_TEXT_LENGTH})
                      OR (NEW.benefits IS NOT NULL AND length(NEW.benefits) > {MAX_TASK_TEXT_LENGTH})
                    BEGIN
                        SELECT RAISE(ABORT, 'focus event violates text policy');
                    END;
                    CREATE TRIGGER IF NOT EXISTS focus_events_validate_update
                    BEFORE UPDATE OF doing, benefits ON focus_events
                    WHEN (NEW.doing IS NOT NULL AND length(NEW.doing) > {MAX_TASK_TEXT_LENGTH})
                      OR (NEW.benefits IS NOT NULL AND length(NEW.benefits) > {MAX_TASK_TEXT_LENGTH})
                    BEGIN
                        SELECT RAISE(ABORT, 'focus event violates text policy');
                    END;
                    """
                )
                con.commit()
        except Exception as exc:
            log_exception("TaskDB: failed ensuring schema")
            raise RuntimeError(f"TaskDB schema initialization failed: {exc}") from exc

    def _prepare_migration_safety_copy(self):
        """Verify and snapshot an existing older DB before any schema mutation."""
        if not os.path.isfile(self.path) or os.path.getsize(self.path) == 0:
            return
        try:
            with sqlite3.connect(self.path, timeout=30) as source:
                version = int(source.execute("PRAGMA user_version").fetchone()[0] or 0)
                integrity = str(source.execute("PRAGMA integrity_check").fetchone()[0] or "")
                if integrity.lower() != "ok":
                    raise RuntimeError(f"SQLite integrity check failed: {integrity[:120]}")
                if version >= CURRENT_TASK_SCHEMA_VERSION:
                    return

                candidate = f"{self.path}.pre-migration-v{version}.bak"
                suffix = 1
                while os.path.exists(candidate):
                    candidate = f"{self.path}.pre-migration-v{version}.{suffix}.bak"
                    suffix += 1
                temporary = f"{candidate}.{os.getpid()}.tmp"
                backup = sqlite3.connect(temporary)
                try:
                    source.backup(backup)
                    backup.commit()
                finally:
                    backup.close()
                os.replace(temporary, candidate)
                self.pre_migration_backup = candidate
        except RuntimeError:
            raise
        except Exception as exc:
            log_exception("TaskDB: pre-migration safety copy failed")
            raise RuntimeError(f"TaskDB pre-migration safety copy failed: {exc}") from exc

    def integrity_check(self):
        """Return whether SQLite reports a clean database integrity check."""
        try:
            with self._conn() as con:
                result = con.execute("PRAGMA integrity_check").fetchone()
            return bool(result and str(result[0]).lower() == "ok")
        except Exception:
            return False

    def backup_to(self, destination):
        """Create a consistent SQLite backup, including WAL contents."""
        destination = os.fspath(destination)
        os.makedirs(os.path.dirname(destination) or ".", exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=f".{os.path.basename(destination)}.",
                suffix=".backup.tmp",
                dir=os.path.dirname(os.path.abspath(destination)) or ".",
                delete=False,
            ) as handle:
                temporary = handle.name
            with self._conn() as con:
                backup_con = sqlite3.connect(temporary)
                try:
                    con.backup(backup_con)
                    backup_con.commit()
                    integrity = str(
                        backup_con.execute("PRAGMA integrity_check").fetchone()[0] or ""
                    )
                    if integrity.lower() != "ok":
                        raise RuntimeError(f"SQLite backup integrity check failed: {integrity[:120]}")
                finally:
                    backup_con.close()
            os.replace(temporary, destination)
            temporary = None
        finally:
            if temporary is not None:
                try:
                    os.remove(temporary)
                except FileNotFoundError:
                    pass
        return destination

    @staticmethod
    def restore_from(source, destination):
        """Restore a previously created backup without mutating the source."""
        source = os.fspath(source)
        destination = os.fspath(destination)
        source_path = os.path.abspath(source)
        destination_path = os.path.abspath(destination)
        if _contains_symlink_component(source_path):
            raise ValueError("refusing to restore through a symlinked source path")
        if _contains_symlink_component(destination_path):
            raise ValueError("refusing to restore through a symlinked destination path")
        if not os.path.isfile(source_path):
            raise FileNotFoundError(source_path)
        os.makedirs(os.path.dirname(destination_path) or ".", exist_ok=True)
        temp = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=f".{os.path.basename(destination_path)}.",
                suffix=".restore.tmp",
                dir=os.path.dirname(destination_path) or ".",
                delete=False,
            ) as handle:
                temp = handle.name
            shutil.copy2(source_path, temp)
            restored = sqlite3.connect(temp, timeout=30)
            try:
                integrity = str(restored.execute("PRAGMA integrity_check").fetchone()[0] or "")
                schema_version = int(restored.execute("PRAGMA user_version").fetchone()[0] or 0)
            except sqlite3.DatabaseError as exc:
                raise RuntimeError(f"SQLite restore integrity check failed: {exc}") from exc
            finally:
                restored.close()
            if integrity.lower() != "ok":
                raise RuntimeError(f"SQLite restore integrity check failed: {integrity[:120]}")
            if schema_version > CURRENT_TASK_SCHEMA_VERSION:
                raise RuntimeError(
                    f"SQLite restore schema version {schema_version} is newer than supported "
                    f"version {CURRENT_TASK_SCHEMA_VERSION}"
                )
            os.replace(temp, destination_path)
            temp = None
        finally:
            if temp is not None:
                try:
                    os.remove(temp)
                except FileNotFoundError:
                    pass

    def get_active(self):
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("SELECT id, created_utc, title, why, consequences, due_utc, status, completed_utc, change_reason FROM tasks WHERE status = 'active' ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            return self._row_to_dict(row) if row else None

    def start_task(self, *, title, due_utc, why, consequences):
        title = _bounded_text(title, "title", required=True)
        why = _bounded_text(why, "why")
        consequences = _bounded_text(consequences, "consequences")
        now = self._now_utc().isoformat()
        due_utc = _normalize_utc(due_utc, allow_none=True)
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
            task_id = cur.lastrowid
            self._emit_transition("start", "committed", task_id=task_id)
            return task_id

    def change_task(self, task_id, reason, *, new_task=None, when_utc=None):
        """Atomically close an active task and optionally create its replacement."""
        reason = _bounded_text(reason, "change_reason", required=True, limit=MAX_TASK_REASON_LENGTH)
        if when_utc is None:
            when_utc = self._now_utc().isoformat()
        else:
            when_utc = _normalize_utc(when_utc)

        normalized = None
        if new_task is not None:
            if not isinstance(new_task, dict):
                raise TypeError("new_task must be a mapping")
            normalized = {
                "title": _bounded_text(new_task.get("title"), "title", required=True),
                "why": _bounded_text(new_task.get("why", ""), "why"),
                "consequences": _bounded_text(new_task.get("consequences", ""), "consequences"),
                "due_utc": _normalize_utc(new_task.get("due_utc"), allow_none=True),
            }

        with self._conn() as con:
            cur = con.cursor()
            cur.execute(
                "UPDATE tasks SET status='changed', completed_utc=?, change_reason=? "
                "WHERE id=? AND status='active'",
                (when_utc, reason, task_id),
            )
            if cur.rowcount != 1:
                self._emit_transition("change", "not_active", task_id=task_id)
                return False
            if normalized is None:
                con.commit()
                self._emit_transition("change", "committed", task_id=task_id)
                return True
            cur.execute(
                "INSERT INTO tasks(created_utc, title, why, consequences, due_utc, status) "
                "VALUES (?,?,?,?,?, 'active')",
                (
                    when_utc,
                    normalized["title"],
                    normalized["why"],
                    normalized["consequences"],
                    normalized["due_utc"],
                ),
            )
            con.commit()
            replacement_id = cur.lastrowid
            self._emit_transition(
                "change",
                "committed",
                task_id=task_id,
                replacement_id=replacement_id,
            )
            return replacement_id

    def mark_completed(self, task_id, when_utc=None):
        if when_utc is None:
            when_utc = self._now_utc().isoformat()
        else:
            when_utc = _normalize_utc(when_utc)
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("UPDATE tasks SET status='completed', completed_utc=? WHERE id=? AND status='active'", (when_utc, task_id))
            con.commit()
            changed = cur.rowcount == 1
            self._emit_transition("complete", "committed" if changed else "not_active", task_id=task_id)
            return changed

    def mark_failed(self, task_id, when_utc=None, timed_out=False):
        if when_utc is None:
            when_utc = self._now_utc().isoformat()
        else:
            when_utc = _normalize_utc(when_utc)
        with self._conn() as con:
            cur = con.cursor()
            try:
                cur.execute("UPDATE tasks SET status='failed', completed_utc=?, timed_out=? WHERE id=? AND status = 'active'", (when_utc, 1 if timed_out else 0, task_id))
            except Exception:
                # Fallback for DBs without timed_out column
                cur.execute("UPDATE tasks SET status='failed', completed_utc=? WHERE id=? AND status = 'active'", (when_utc, task_id))
            con.commit()
            changed = cur.rowcount == 1
            self._emit_transition(
                "fail",
                "committed" if changed else "not_active",
                task_id=task_id,
                timed_out=bool(timed_out),
            )
            return changed

    def mark_changed(self, task_id, reason):
        reason = _bounded_text(reason, "change_reason", required=True, limit=MAX_TASK_REASON_LENGTH)
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("UPDATE tasks SET status='changed', change_reason=? WHERE id=? AND status='active'", (reason, task_id))
            con.commit()
            changed = cur.rowcount == 1
            self._emit_transition("mark_changed", "committed" if changed else "not_active", task_id=task_id)
            return changed

    def _row_to_dict(self, row):
        if not row:
            return None
        keys = ["id","created_utc","title","why","consequences","due_utc","status","completed_utc","change_reason"]
        return dict(zip(keys, row))

    def overdue_active_to_failed(self):
        now_iso = self._now_utc().isoformat()
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
                    # The deadline is inclusive: the task is timed out at the
                    # exact instant the UI marks it overdue.
                    if self._now_utc() >= due:
                        cur.execute(
                            "UPDATE tasks SET status='failed', completed_utc=?, timed_out=1, "
                            "change_reason=COALESCE(NULLIF(change_reason, ''), 'task deadline overdue') "
                            "WHERE id=? AND status='active'",
                            (now_iso, tid),
                        )
                        if cur.rowcount == 1:
                            affected.append(tid)
                except (TypeError, ValueError, OverflowError):
                    continue
            con.commit()
        self._emit_transition("overdue", "committed", count=len(affected))
        return affected

    def analytics_counts(
        self,
        *,
        timescale="lifetime",
        treat_changed_as_fail=True,
        user_timezone="UTC",
        now=None,
    ):
        """Return task counts using UTC storage and an explicit local-day policy.

        ``now`` is injectable for deterministic boundary and DST tests. Unknown
        timezone names are rejected rather than silently using the machine zone.
        """
        where = ""
        params = []
        current = now or self._now_utc()
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        current = current.astimezone(timezone.utc)
        if isinstance(user_timezone, str):
            try:
                local_zone = ZoneInfo(user_timezone)
            except ZoneInfoNotFoundError as exc:
                raise ValueError(f"unknown user timezone: {user_timezone!r}") from exc
        else:
            local_zone = user_timezone
        local_now = current.astimezone(local_zone)
        if timescale == "today":
            start = local_now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
            where = "WHERE datetime(created_utc) >= datetime(?)"
            params = [start.isoformat()]
        elif timescale == "7d":
            start = (local_now - timedelta(days=7)).astimezone(timezone.utc)
            where = "WHERE datetime(created_utc) >= datetime(?)"
            params = [start.isoformat()]
        elif timescale == "30d":
            start = (local_now - timedelta(days=30)).astimezone(timezone.utc)
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
        what = _bounded_text(what, "what")
        consequences = _bounded_text(consequences, "consequences")
        try:
            if when_utc is None:
                when_utc = self._now_utc().isoformat()
            else:
                when_utc = _normalize_utc(when_utc)
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
        doing = _bounded_text(doing, "doing")
        benefits = _bounded_text(benefits, "benefits")
        try:
            if when_utc is None:
                when_utc = self._now_utc().isoformat()
            else:
                when_utc = _normalize_utc(when_utc)
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

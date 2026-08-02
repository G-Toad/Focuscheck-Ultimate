PRAGMA user_version = 1;

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_utc TEXT NOT NULL,
    title TEXT NOT NULL,
    why TEXT,
    consequences TEXT,
    due_utc TEXT,
    status TEXT NOT NULL,
    completed_utc TEXT,
    change_reason TEXT
);

INSERT INTO tasks (id, created_utc, title, why, consequences, due_utc, status)
VALUES (1, '2026-08-03T00:00:00', 'Legacy invalid due', '', '', 'not-a-date', 'active');
INSERT INTO tasks (id, created_utc, title, why, consequences, due_utc, status)
VALUES (2, '2026-08-03T01:00:00', 'Legacy current task', '', '', NULL, 'active');

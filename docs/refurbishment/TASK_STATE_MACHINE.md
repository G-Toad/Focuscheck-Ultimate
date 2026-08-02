# Task State Machine

`none -> active -> completed`.

`active -> changed` occurs when replaced or scope changes. `active -> failed` occurs on explicit failure or overdue processing. Completed tasks are terminal and cannot be changed back to failed. SQLite enforces at most one active task.

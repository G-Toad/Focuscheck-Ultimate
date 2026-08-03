# Data Path and Migration Map

- `FOCUS_DATA_DIR` is the highest-priority isolated/runtime root.
- Windows default is `%APPDATA%\FocusCheck`.
- Failed platform-root resolution uses a controlled temporary `FocusCheck` recovery directory, never the source/install directory.
- Runtime transition metadata is stored as `runtime_state.jsonl` under the canonical root and is bounded/metadata-only.
- Settings: `focus_settings.json`, with `.bak` and timestamped `.corrupt-*` recovery artifacts.
- Legacy settings imports reject symlink sources before reading or copying them; migration journal entries use an explicit format version and the journal writer returns a durable success/failure result.
- Supervisor heartbeat: `hb.txt`, JSON payload containing UTC timestamp and child pid.
- Task database: `focus_tasks.sqlite3`, SQLite `user_version=3` plus legacy column/index/timestamp repair; timestamps are stored as UTC.
- CSV/JSONL logs are per-file locked and size-bounded.
- Settings schema migration is pure and currently upgrades schema `1` to `2`.
- Legacy task DB and event-log artifacts are imported into the canonical root without deletion; duplicate/conflicting sources are preserved by hash in the versioned `data_migration.jsonl` journal and conflict copies. Symlink sources are rejected before canonical-target comparison, and a journal write failure is returned as an explicit migration outcome.
- `structured_events.jsonl` is the canonical bounded operational metadata ledger; it contains lifecycle/runtime metadata only and never raw settings, task text, URLs, responses, or camera frames.

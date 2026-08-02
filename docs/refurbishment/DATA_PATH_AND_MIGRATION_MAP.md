# Data Path and Migration Map

- `FOCUS_DATA_DIR` is the highest-priority isolated/runtime root.
- Windows default is `%APPDATA%\FocusCheck`.
- Development fallback is the user profile `FocusCheck` directory.
- Settings: `focus_settings.json`, with `.bak` and timestamped `.corrupt-*` recovery artifacts.
- Supervisor heartbeat: `hb.txt`, JSON payload containing UTC timestamp and child pid.
- Task database: `focus_tasks.sqlite3`, SQLite `user_version=1` plus legacy column/index repair.
- CSV/JSONL logs are per-file locked and size-bounded.
- Settings schema migration is pure and currently upgrades schema `1` to `2`.

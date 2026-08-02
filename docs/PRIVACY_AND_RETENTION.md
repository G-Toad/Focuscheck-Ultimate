# Privacy and Retention

## Data inventory

| Data | Location | Purpose | Sensitivity | Export handling |
| --- | --- | --- | --- | --- |
| Settings and profile text | `focus_settings.json` | Product configuration and personal prompts | sensitive | Never included raw in diagnostics |
| Task text and due times | `focus_tasks.sqlite3` | Task lifecycle and analytics | sensitive | User-controlled; not included in diagnostics |
| Focus/waste responses | CSV logs and SQLite events | Productivity history | sensitive | CSV formula-neutralized; raw SQLite retained locally |
| Window titles and activity URLs | runtime logs/reflections/provider payloads | Intervention and monitoring context | sensitive | Query/fragment stripped from activity snapshots |
| Supervisor/application logs | `focus_app.log`, `focuscheck_supervisor.log` | Support diagnostics | potentially sensitive | Sanitized bundle generator redacts paths/secrets |

## Retention

`tools/retention.py` plans deletion only for known log/rotation patterns. It is dry-run by default; deletion requires an explicit `--apply` and a selected root. Settings and task databases are never selected by this tool. Symlink candidates are rejected, and applied deletions append only filename/size/outcome metadata to `retention_audit.jsonl`, never log contents.

Automated verification never runs with `--apply` and uses `_verify_runtime/data` as its data root.

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

`tools/retention.py` and the tray's **Clean old logs** action use the packaged retention service. It plans deletion only for known log/rotation patterns; the CLI is dry-run by default, while the tray requires an explicit age and confirmation flow. Settings and task databases are never selected. Symlink candidates are ignored, and deletion rechecks the candidate's size and modification time before unlinking so a changed path is retained. Applied deletions append versioned filename/size/outcome metadata to `retention_audit.jsonl`, never log contents.

Automated verification never runs with `--apply` and uses `_verify_runtime/data` as its data root.

## Export

Use `tools/export_data.py` with an explicit source and destination. The default export includes only logs and operational metadata; settings, tasks, and camera files require explicit `--include` selection. Archives contain an `EXPORT_MANIFEST.json` with relative paths, sizes, sensitivity labels, and SHA-256 hashes. Symlink sources and existing destinations without `--overwrite` are rejected.

Validated user-data recovery is explicit and never restores runtime control
metadata such as `hb.txt` or supervisor stop markers. Restore settings/tasks
from an archive with an explicit confirmation and a separate destination root:

```powershell
py -3 tools\export_data.py --import-archive .\user-data.zip --destination "$env:APPDATA\FocusCheck" --include settings tasks --confirm-sensitive
```

The importer revalidates the embedded manifest and member hashes, rejects
archive traversal or non-allowlisted members, checks settings/schema and SQLite
integrity compatibility, and refuses to overwrite existing files unless
`--overwrite` is supplied. It stages the complete selection before promotion
and restores prior files if promotion fails.

## User controls

The tray provides a metadata-only data inventory, export, clear logs, clear personal data, and old-log retention actions. Export refuses to overwrite an allowlisted source file. Clear logs removes only known log files. Clear personal data removes only settings, task database, and camera categories after confirmation, rechecks each candidate before deletion, leaves operational logs intact, and records versioned filename/size/outcome metadata in `data_clear_audit.jsonl`; it does not record file contents.

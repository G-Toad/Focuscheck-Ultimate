# Support Diagnostics

Use the diagnostic bundle only when requested by a maintainer. It contains sanitized verification logs and machine-readable stage results; it must not contain raw settings, task text, browser URLs, camera frames, or the SQLite database.

## Collect a bundle

From the repository or unpacked release directory, run:

```powershell
py -3 tools\verification_runner.py --timeout 60
py -3 tools\create_diagnostic_bundle.py --runtime _verify_runtime --output "$env:USERPROFILE\Desktop\FocusCheck-diagnostic.zip"
```

For a packaged executable, run `FocusCheck.exe --selftest` with disposable `FOCUS_DATA_DIR` and `FOCUSCHECK_SUPERVISOR_*` paths first. Do not point verification at the live data directory.

## Before sharing

- Open the archive and confirm it contains only logs and `verification.json`.
- Do not manually add `focus_settings.json`, `focus_tasks.sqlite3`, exports, screenshots, or browser history.
- Review the archive for identifiers or paths that matter to you; redaction covers known Windows user paths and common credential-shaped strings, not every possible secret.
- Delete the archive after the support case is closed.

The application data root is normally `%APPDATA%\FocusCheck`. Preserve it before rollback, but share it only through an explicitly approved, separately encrypted process.

# Rollback

1. Stop FocusCheck from the tray and confirm the supervisor process has exited.
2. Preserve the user's data root under `%APPDATA%\FocusCheck` before changing binaries.
3. Restore the previous package directory, or reinstall the previous release over the current package.
4. Do not delete `focus_settings.json`, `focus_settings.json.bak`, or `focus_tasks.sqlite3` during a binary rollback.
5. If startup registration points at the failed package, run the previous supervised launcher or remove and recreate the startup entry through the tray command.
6. Capture the sanitized diagnostic bundle before retrying an upgrade.

Rollback is a release requirement and must be exercised on a disposable Windows profile before a release claim.

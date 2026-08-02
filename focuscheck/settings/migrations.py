"""Pure settings migrations.

Migrations operate on a detached dictionary and never perform I/O. This keeps
legacy compatibility testable and lets the repository own recovery separately.
"""

from __future__ import annotations

from copy import deepcopy


CURRENT_SETTINGS_SCHEMA_VERSION = 2


def migrate_settings(raw: dict) -> dict:
    data = deepcopy(raw)
    try:
        version = int(data.get("settings_schema_version", 1))
    except (TypeError, ValueError):
        version = 1
    if version > CURRENT_SETTINGS_SCHEMA_VERSION:
        raise ValueError(f"unsupported settings schema version: {version}")

    if version < 2:
        # Version 1 used the shorter snooze key in a few early development
        # snapshots. Preserve it only when the canonical key is absent.
        if not data.get("snooze_until_utc") and data.get("snooze_until"):
            data["snooze_until_utc"] = data["snooze_until"]
        flags = data.get("website_flags")
        if isinstance(flags, dict):
            data["website_flags"] = [flags]
        data["settings_schema_version"] = 2

    return data

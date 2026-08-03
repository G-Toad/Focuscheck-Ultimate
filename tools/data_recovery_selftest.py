"""Exercise the disposable export-to-recovery transaction."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from focuscheck.utils.data_export import export_data, import_data


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="focuscheck-recovery-selftest-") as temp_dir:
        base = Path(temp_dir)
        source = base / "source"
        destination = base / "destination"
        source.mkdir()
        (source / "focus_settings.json").write_text('{"interval_seconds":42}', encoding="utf-8")
        connection = sqlite3.connect(source / "focus_tasks.sqlite3")
        try:
            connection.execute("CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT)")
            connection.commit()
        finally:
            connection.close()

        archive = base / "user-data.zip"
        export_data(source, archive, categories=("settings", "tasks"))
        result = import_data(archive, destination, confirmed=True)
        if set(result["categories"]) != {"settings", "tasks"}:
            raise AssertionError("recovery categories were not restored")
        if (destination / "focus_settings.json").read_text(encoding="utf-8") != '{"interval_seconds":42}':
            raise AssertionError("settings recovery changed the source payload")
        restored = sqlite3.connect(destination / "focus_tasks.sqlite3")
        try:
            integrity = restored.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            restored.close()
        if integrity != "ok":
            raise AssertionError(f"recovered task database is not integral: {integrity}")
        print("data recovery selftest passed (manifest, confirmation, settings, SQLite, staged promotion)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Exercise legacy settings and durable task/log migration in disposable roots."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from focuscheck.settings import manager as settings_manager
from focuscheck.utils.paths import get_app_paths, migrate_legacy_data


def main() -> int:
    fixture_root = ROOT / "tests" / "fixtures"
    manifest = json.loads((fixture_root / "migration_fixture_manifest.json").read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory(prefix="focuscheck-migration-") as temp_dir:
        root = Path(temp_dir)
        canonical = get_app_paths(root / "canonical")
        legacy = root / "legacy"
        legacy.mkdir()

        artifacts = {
            item["target"]: (fixture_root / item["fixture"]).read_bytes()
            for item in manifest["artifacts"]
        }
        for name, payload in artifacts.items():
            (legacy / name).write_bytes(payload)
        canonical.task_db.write_bytes(artifacts["focus_tasks.sqlite3"])
        canonical.focus_log.write_bytes(b"canonical-focus-log")

        events = migrate_legacy_data(canonical, legacy_root=legacy)
        outcomes = {event["file"]: event["outcome"] for event in events}
        if outcomes["focus_tasks.sqlite3"] != "duplicate_preserved":
            raise AssertionError("identical task database was not preserved as a duplicate")
        if outcomes["focus_log.csv"] != "conflict_preserved":
            raise AssertionError("canonical log conflict was not preserved")
        for name in artifacts:
            if name in {"focus_tasks.sqlite3", "focus_log.csv"}:
                continue
            if (canonical.root / name).read_bytes() != artifacts[name]:
                raise AssertionError(f"legacy artifact was not imported: {name}")
        journal = canonical.root / "data_migration.jsonl"
        journal_events = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]
        if not journal_events or any(item.get("format_version") != 1 for item in journal_events):
            raise AssertionError("migration journal is missing versioned events")

        legacy_settings_root = root / "legacy-settings"
        legacy_settings_root.mkdir()
        legacy_settings = legacy_settings_root / "focus_settings.json"
        legacy_settings.write_text(json.dumps({"interval_seconds": 12}), encoding="utf-8")
        target_settings = root / "settings" / "focus_settings.json"
        with mock.patch.dict(settings_manager.os.environ, {"FOCUS_DATA_DIR": ""}, clear=False), \
                mock.patch.object(settings_manager, "legacy_path", return_value=str(legacy_settings)):
            settings_manager._migrate_legacy_settings(str(target_settings))
        imported = json.loads(target_settings.read_text(encoding="utf-8"))
        if imported.get("interval_seconds") != 12:
            raise AssertionError("legacy settings were not imported")

    print("migration_selftest_passed artifacts=5 settings=1 conflict_preserved=true journal_version=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

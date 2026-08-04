"""Exercise privacy inventory, export, diagnostic, clear, and retention controls."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from focuscheck.utils.data_export import clear_data, export_data, inventory_data, validate_export
from focuscheck.utils.data_retention import apply_retention
from focuscheck.utils.diagnostics import create_bundle, preview_bundle


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="focuscheck-privacy-") as temp_dir:
        root = Path(temp_dir) / "data"
        root.mkdir()
        (root / "focus_log.csv").write_text("response=private note\n", encoding="utf-8")
        (root / "focus_app.log").write_text(
            "token=secret123 url=https://example.test/path?private=1\n", encoding="utf-8"
        )
        (root / "structured_events.jsonl").write_text('{"event":"health"}\n', encoding="utf-8")
        (root / "focus_settings.json").write_text('{"interval_seconds": 20}\n', encoding="utf-8")
        (root / "camera_private.png").write_bytes(b"camera-bytes")

        old_time = time.time() - 3 * 86400
        old_log = root / "focuscheck_supervisor.log"
        old_log.write_text("old log\n", encoding="utf-8")
        import os
        os.utime(old_log, (old_time, old_time))

        inventory = inventory_data(root)
        by_path = {item["path"]: item for item in inventory["files"]}
        if not by_path["focus_settings.json"]["sensitive"]:
            raise AssertionError("settings were not marked sensitive in inventory")
        if by_path["focus_log.csv"]["sensitive"]:
            raise AssertionError("logs were incorrectly classified as sensitive in inventory")

        archive = Path(temp_dir) / "logs.zip"
        export_data(root, archive, categories=("logs", "metadata"))
        manifest = validate_export(archive)
        if set(manifest["categories"]) != {"logs", "metadata"}:
            raise AssertionError("export category allowlist was not preserved")
        with zipfile.ZipFile(archive) as handle:
            names = set(handle.namelist())
            if "focus_settings.json" in names or "camera_private.png" in names:
                raise AssertionError("sensitive data entered a non-sensitive export")

        (root / "verification.json").write_text(
            f"token=secret123 url=https://example.test/path?private=1 root={root}\n", encoding="utf-8"
        )
        preview = preview_bundle(root)
        if not any(item["path"] == "verification.json" for item in preview["files"]):
            raise AssertionError("diagnostic preview omitted an allowlisted artifact")
        bundle = create_bundle(root, Path(temp_dir) / "diagnostic.zip")
        with zipfile.ZipFile(bundle) as handle:
            contents = "\n".join(handle.read(name).decode("utf-8", "replace") for name in handle.namelist())
            if "secret123" in contents or "private=1" in contents or str(root) in contents:
                raise AssertionError("diagnostic bundle leaked private values")

        retention = apply_retention(root, max_age_days=1, apply=True, now=time.time())
        if not retention or not retention[0].get("deleted") or not retention[0].get("audit_written"):
            raise AssertionError("retention did not durably audit its deletion")

        clear_report = clear_data(root, categories=("logs",), confirmed=True)
        if not clear_report.get("audit_written") or (root / "focus_log.csv").exists():
            raise AssertionError("clear-data control did not delete and audit logs")
        if not (root / "focus_settings.json").exists():
            raise AssertionError("clear-data control deleted outside its allowlist")
        audit = json.loads((root / "data_clear_audit.jsonl").read_text(encoding="utf-8").splitlines()[-1])
        if audit.get("operation") != "clear_data" or not audit.get("audit_written"):
            raise AssertionError("clear-data audit contract is invalid")

    print("privacy_controls_selftest_passed inventory=true export=true diagnostics=true retention=true clear=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

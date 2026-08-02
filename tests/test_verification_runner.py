from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class VerificationRunnerTests(unittest.TestCase):
    def test_test_bootstrap_uses_disposable_external_fallback_root(self):
        import tests

        configured = Path(os.environ["FOCUS_DATA_DIR"])
        self.assertNotEqual(Path(__file__).resolve().parents[1] / "_qa_runtime" / "unit_data", configured)
        self.assertTrue(configured.name.startswith("FocusCheck-tests-") or "FOCUS_DATA_DIR" in os.environ)

    def test_snapshot_tree_is_read_only_and_detects_content_changes(self):
        from tools.verification_runner import snapshot_tree

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "nested" / "sample.txt"
            target.parent.mkdir()
            target.write_text("one", encoding="utf-8")
            first = snapshot_tree(root)
            target.write_text("two", encoding="utf-8")
            second = snapshot_tree(root)
            self.assertNotEqual(first, second)

    def test_timeout_is_reported_as_a_distinct_stage_status(self):
        from tools.verification_runner import run_stage

        with tempfile.TemporaryDirectory() as temp_dir, mock.patch("tools.verification_runner.RUNTIME", Path(temp_dir)):
            Path(temp_dir).mkdir(exist_ok=True)
            with mock.patch("tools.verification_runner.subprocess.run", side_effect=__import__("subprocess").TimeoutExpired(["fake"], 1)):
                result = run_stage("slow", ["fake"], {}, 1)
            self.assertEqual("timeout", result["status"])
            self.assertTrue(Path(result["log"]).exists())

    def test_report_is_json_serializable(self):
        payload = {"status": "passed", "manual_gates": ["Tk"]}
        self.assertEqual(payload, json.loads(json.dumps(payload)))

    def test_new_processes_only_reports_pids_not_in_baseline(self):
        from tools.process_guard import new_processes

        before = {10: {"pid": 10, "name": "python.exe"}}
        after = {
            10: {"pid": 10, "name": "python.exe"},
            11: {"pid": 11, "name": "python.exe"},
        }
        self.assertEqual([{"pid": 11, "name": "python.exe"}], new_processes(before, after))

    def test_filtered_repository_snapshot_excludes_verifier_outputs(self):
        from tools.process_guard import filtered_repository_snapshot

        def fake_snapshot(_root):
            return {
                "focuscheck/app.py": "a",
                "_verify_runtime/log.txt": "b",
                "focuscheck/__pycache__/app.pyc": "c",
                "docs/refurbishment/verification-report.json": "d",
            }

        result = filtered_repository_snapshot(Path("."), fake_snapshot)
        self.assertEqual({"focuscheck/app.py": "a"}, result)


if __name__ == "__main__":
    unittest.main()

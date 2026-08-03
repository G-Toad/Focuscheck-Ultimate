from __future__ import annotations

import json
import os
import sys
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
            result = run_stage("slow", [sys.executable, "-c", "import time; time.sleep(30)"], {}, 1)
            self.assertEqual("timeout", result["status"])
            self.assertTrue(Path(result["log"]).exists())
            self.assertEqual("process_kill" if os.name != "nt" else "taskkill_pid_tree", result["cleanup"]["method"])

    def test_timeout_cleanup_does_not_target_processes_by_image_name(self):
        from tools.verification_runner import _terminate_process_tree

        process = mock.Mock(pid=1234)
        with mock.patch("tools.verification_runner.os.name", "nt"), mock.patch(
            "tools.verification_runner.subprocess.run"
        ) as run:
            run.return_value.returncode = 0
            result = _terminate_process_tree(process)
        self.assertEqual("taskkill_pid_tree", result["method"])
        self.assertEqual(["taskkill", "/F", "/T", "/PID", "1234"], run.call_args.args[0])

    def test_report_contains_required_machine_readable_fields(self):
        from tools.verification_runner import _test_summary

        with tempfile.TemporaryDirectory() as temp_dir:
            log = Path(temp_dir) / "unittest.log"
            log.write_text("Ran 12 tests in 0.1s\nOK\n", encoding="utf-8")
            summary = _test_summary([{"name": "unittest", "status": "passed", "log": str(log)}])
        self.assertEqual({"status": "passed", "count": 12, "failure_summary": None}, summary)

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

    def test_property_invariant_suite_is_discoverable(self):
        property_tests = Path(__file__).resolve().parents[1] / "tests" / "test_property_invariants.py"
        self.assertTrue(property_tests.is_file())

    def test_mutation_smoke_contract_is_present(self):
        mutation_tool = Path(__file__).resolve().parents[1] / "tools" / "mutation_smoke.py"
        self.assertTrue(mutation_tool.is_file())

    def test_test_category_manifest_covers_automated_and_manual_classes(self):
        from tools.test_category_inventory import build_inventory

        inventory = build_inventory()
        self.assertEqual(
            {"pure_unit", "persistence", "simulated_app", "withdrawn_tk"},
            set(inventory["automated_categories"]),
        )
        self.assertEqual(
            {"live_windows", "manual_only", "destructive_manual_opt_in"},
            set(inventory["manual_categories"]),
        )
        for name in inventory["automated_categories"]:
            self.assertTrue(inventory["categories"][name]["matched_files"], name)

    def test_manual_evidence_template_has_required_record_fields(self):
        payload = json.loads(
            (Path(__file__).resolve().parents[1] / "docs" / "refurbishment" / "manual-evidence.json").read_text(encoding="utf-8")
        )
        self.assertEqual("not_run", payload["status"])
        required = {
            "date_utc", "commit", "machine", "exact_steps", "expected",
            "observed", "screenshot_log_references", "pass_fail", "tester",
        }
        self.assertTrue(all(required <= set(case) for case in payload["cases"]))

    def test_behavior_snapshot_manifest_covers_phase_zero_cases(self):
        path = Path(__file__).resolve().parents[1] / "docs" / "refurbishment" / "behavior-snapshots.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(1, payload["schema_version"])
        snapshots = payload["snapshots"]
        self.assertEqual(20, len(snapshots))
        self.assertEqual(
            {"automated", "live_disposable", "manual_pending"},
            {item["status"] for item in snapshots},
        )
        for item in snapshots:
            self.assertTrue(item["id"])
            self.assertTrue(item["expected"])
            self.assertTrue(item["evidence"])


if __name__ == "__main__":
    unittest.main()

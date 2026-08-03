from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest


class ManualEvidenceTests(unittest.TestCase):
    def _template(self):
        source = Path(__file__).resolve().parents[1] / "docs" / "refurbishment" / "manual-evidence.json"
        return json.loads(source.read_text(encoding="utf-8"))

    def test_record_requires_explicit_human_confirmation_for_pass(self):
        from tools.manual_evidence import record_case

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "manual.json"
            path.write_text(json.dumps(self._template()), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "human-confirmed"):
                record_case(path, "WIN-001", "pass", observed="looks good", tester="tester")
            self.assertEqual("not_run", json.loads(path.read_text(encoding="utf-8"))["cases"][0]["status"])

    def test_record_updates_one_case_and_keeps_other_cases_unrun(self):
        from tools.manual_evidence import record_case

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "manual.json"
            path.write_text(json.dumps(self._template()), encoding="utf-8")
            payload = record_case(
                path, "WIN-001", "pass", observed="Executed on disposable host", tester="Alex",
                machine="WIN-TEST", commit="abc123", date_utc="2030-01-01T00:00:00+00:00",
                human_confirmed=True,
            )
        self.assertEqual("manual_pass", payload["cases"][0]["status"])
        self.assertEqual("pass", payload["cases"][0]["pass_fail"])
        self.assertEqual("not_run", payload["cases"][1]["status"])
        self.assertEqual("not_run", payload["status"])
        self.assertEqual("abc123", payload["cases"][0]["commit"])

    def test_validate_rejects_inconsistent_status_contract(self):
        from tools.manual_evidence import validate_payload

        payload = self._template()
        payload["cases"][0]["status"] = "manual_pass"
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            validate_payload(payload)


if __name__ == "__main__":
    unittest.main()

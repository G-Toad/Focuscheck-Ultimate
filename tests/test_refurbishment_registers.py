from __future__ import annotations

import tempfile
from pathlib import Path
import unittest


class RefurbishmentRegisterTests(unittest.TestCase):
    def test_every_controlling_plan_defect_id_has_a_register_row(self):
        from tools.plan_register_coverage import coverage

        result = coverage()
        self.assertTrue(result["complete"], result["missing"])
        self.assertEqual([], result["missing"])

    def test_checked_in_registers_have_traceable_rows(self):
        from tools.validate_refurbishment_registers import validate_registers

        summary = validate_registers()
        self.assertGreaterEqual(summary["defects"], 1)
        self.assertGreaterEqual(summary["contradictions"], 1)
        self.assertEqual(0, summary["untriaged_high_severity"])

    def test_validator_rejects_untriaged_severity_one_defect(self):
        from tools.validate_refurbishment_registers import validate_registers

        defect = """| ID | Severity | Classification | Evidence | Fix | Tests | Manual verification | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CFG-001 | 1 | confirmed defect | evidence | fix | tests | manual | open |
"""
        contradiction = """| ID | Contradiction | Decision | Evidence | Status |
| --- | --- | --- | --- | --- |
| CONTR-001 | contradiction | decision | evidence | fixed |
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            defect_path = root / "defects.md"
            contradiction_path = root / "contradictions.md"
            defect_path.write_text(defect, encoding="utf-8")
            contradiction_path.write_text(contradiction, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "untriaged"):
                validate_registers(defect_path, contradiction_path)

    def test_validator_rejects_duplicate_contradiction_ids(self):
        from tools.validate_refurbishment_registers import validate_registers

        defect = """| ID | Severity | Classification | Evidence | Fix | Tests | Manual verification | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CFG-001 | 2 | confirmed defect | evidence | fix | tests | manual | fixed |
"""
        contradiction = """| ID | Contradiction | Decision | Evidence | Status |
| --- | --- | --- | --- | --- |
| CONTR-001 | one | decision | evidence | fixed |
| CONTR-001 | two | decision | evidence | fixed |
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            defect_path = root / "defects.md"
            contradiction_path = root / "contradictions.md"
            defect_path.write_text(defect, encoding="utf-8")
            contradiction_path.write_text(contradiction, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate contradiction"):
                validate_registers(defect_path, contradiction_path)


if __name__ == "__main__":
    unittest.main()

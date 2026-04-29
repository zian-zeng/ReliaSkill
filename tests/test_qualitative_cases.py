from __future__ import annotations

import csv
import subprocess
import sys
import unittest
from pathlib import Path


class QualitativeCaseExtractionTests(unittest.TestCase):
    def test_extract_qualitative_cases_outputs_required_cases(self) -> None:
        report_path = Path("outputs/reports/test_qualitative_cases.md")
        table_path = Path("outputs/tables/test_error_analysis.csv")
        artifact_root = Path("outputs/qualitative_artifacts_test")
        subprocess.run(
            [
                sys.executable,
                "scripts/extract_qualitative_cases.py",
                "--max-tools",
                "3",
                "--out-report",
                str(report_path),
                "--out-table",
                str(table_path),
                "--artifact-root",
                str(artifact_root),
            ],
            cwd=Path.cwd(),
            check=True,
        )

        report = report_path.read_text(encoding="utf-8")
        for required in [
            "naive skill over-triggers",
            "structural invalid skill caught by validation",
            "repaired skill fixes one boundary",
            "rejected skill not deployed",
            "ReliaSkill failure on held-out example",
        ]:
            self.assertIn(required, report)
        for required_field in ["Tool:", "User request:", "Prediction:", "Gold label:", "Failure type:", "Source artifact:"]:
            self.assertIn(required_field, report)

        with table_path.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertGreaterEqual(len(rows), 5)
        self.assertEqual(rows[0]["case_id"], "case_01_naive_overtrigger")
        self.assertTrue(all(row["source_artifact_path"] or row["failure_type"] == "missing_candidate" for row in rows[:5]))


if __name__ == "__main__":
    unittest.main()

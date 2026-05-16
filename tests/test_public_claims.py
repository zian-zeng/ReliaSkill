from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from reliaskill.analysis.public_claims import scan_public_claims


class PublicClaimsTests(unittest.TestCase):
    def test_stale_held_out_count_in_final_result_text_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "claims.md"
            path.write_text("The final result uses a 1,475-control held-out test set.\n", encoding="utf-8")

            audit = scan_public_claims([path])

            self.assertEqual(audit["issue_count"], 1)
            issue = audit["issues"][0]
            self.assertEqual(issue["matched_text"], "1,475")
            self.assertEqual(issue["issue_type"], "stale_final_result_value")

    def test_stale_held_out_count_in_archival_pre_dedup_run_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "claims.md"
            path.write_text("This archival pre-dedup run used 1,475 held-out controls.\n", encoding="utf-8")

            audit = scan_public_claims([path])

            self.assertEqual(audit["issue_count"], 0)

    def test_production_safety_guarantee_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "claims.md"
            path.write_text("The benchmark establishes a production safety guarantee.\n", encoding="utf-8")

            audit = scan_public_claims([path])

            self.assertEqual(audit["issue_count"], 1)
            issue = audit["issues"][0]
            self.assertEqual(issue["matched_text"], "production safety")
            self.assertEqual(issue["issue_type"], "overclaim_safety")

    def test_no_observed_harmful_activation_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "claims.md"
            path.write_text("We observed no observed harmful activation on held-out adjacent negatives.\n", encoding="utf-8")

            audit = scan_public_claims([path])

            self.assertEqual(audit["issue_count"], 0)

    def test_readme_fix_replaces_unsafe_wording_without_inventing_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            readme = root / "README.md"
            output_json = root / "audit.json"
            output_md = root / "audit.md"
            readme.write_text(
                "\n".join(
                    [
                        "# ReliaSkill",
                        "",
                        "- How do we know a generated skill is safe enough to expose?",
                        "- This is not a production safety guarantee.",
                        "| Quantity | Value |",
                        "| --- | ---: |",
                        "| MCP-like tools | 295 |",
                        "| Total controls | 2,950 |",
                        "| Development controls | 1,475 |",
                        "| Held-out test controls | 1,475 |",
                        "The evaluation uses the same 1,475-control held-out test set.",
                        "After validation and repair, the reported artifact set has no residual checker-level failures: unsupported arguments, missing required fields, invalid enum values, malformed JSON examples, contradictory guidance, and missing non-use boundaries are all recorded as 0 / 2950.",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    "scripts/check_public_claims.py",
                    "--paths",
                    str(readme),
                    "--output-json",
                    str(output_json),
                    "--output-md",
                    str(output_md),
                    "--fix",
                ],
                cwd=Path.cwd(),
                check=True,
            )

            fixed = readme.read_text(encoding="utf-8")
            self.assertNotIn("safe enough to expose", fixed)
            self.assertNotIn("production safety", fixed)
            self.assertNotIn("2,950", fixed)
            self.assertNotIn("1,475", fixed)
            self.assertNotIn("0 / 2950", fixed)
            self.assertNotIn("100%", fixed)
            self.assertNotIn("99%", fixed)
            self.assertIn("| MCP-like tools | 290 |", fixed)
            self.assertIn("| Selected held-out controls | 1,450 |", fixed)
            payload = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["issue_count"], 0)


if __name__ == "__main__":
    unittest.main()

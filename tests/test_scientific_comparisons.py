from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from reliaskill.analysis.comparisons import extract_scientific_comparisons, write_scientific_comparison_outputs


class ScientificComparisonTests(unittest.TestCase):
    def test_extracts_supported_comparison_from_actual_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tables = Path(tmpdir)
            _write_csv(
                tables / "main_results.csv",
                [
                    {
                        "baseline_name": "raw_mcp",
                        "num_examples": 50,
                        "joint_exact_match": 0.40,
                        "joint_exact_match_wilson_low": 0.27,
                        "joint_exact_match_wilson_high": 0.54,
                        "argument_schema_validity": 0.60,
                        "tool_selection_accuracy": 0.50,
                    },
                    {
                        "baseline_name": "naive_skill",
                        "num_examples": 50,
                        "joint_exact_match": 0.58,
                        "joint_exact_match_wilson_low": 0.44,
                        "joint_exact_match_wilson_high": 0.70,
                        "argument_schema_validity": 0.72,
                        "tool_selection_accuracy": 0.64,
                    },
                ],
            )
            _write_csv(
                tables / "stat_tests.csv",
                [
                    {
                        "test": "mcnemar",
                        "baseline_a": "raw_mcp",
                        "baseline_b": "naive_skill",
                        "metric": "joint_exact_match",
                        "paired_examples": 50,
                        "p_value": 0.03,
                    }
                ],
            )

            summary = extract_scientific_comparisons(tables_dir=tables, min_denominator=20)
            comparison = _by_id(summary, "naive_skill_vs_raw_mcp")
            primary = next(item for item in comparison["metrics"] if item["metric"] == "joint_exact_match")

            self.assertEqual(comparison["claim_support"], "supported")
            self.assertEqual(comparison["safe_wording"], "improves")
            self.assertEqual(primary["delta_b_minus_a"], 0.18)
            self.assertEqual(primary["paired_p_value"], "0.03")
            self.assertEqual(primary["delta_ci_low"], -0.1)
            self.assertEqual(primary["delta_ci_high"], 0.43)

    def test_missing_conditions_are_insufficient_data_not_fabricated(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tables = Path(tmpdir)
            _write_csv(
                tables / "main_results.csv",
                [{"baseline_name": "raw_mcp", "num_examples": 50, "joint_exact_match": 0.4}],
            )

            summary = extract_scientific_comparisons(tables_dir=tables, min_denominator=20)
            comparison = _by_id(summary, "repaired_vs_naive")

            self.assertEqual(comparison["claim_support"], "insufficient_data")
            self.assertTrue(any("missing condition" in warning for warning in comparison["warnings"]))

    def test_harm_comparison_uses_negative_controls_denominator(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tables = Path(tmpdir)
            _write_csv(
                tables / "harm_utility.csv",
                [
                    {
                        "baseline_name": "raw_mcp",
                        "num_controls": 80,
                        "negative_controls": 40,
                        "harmful_skill_injection_rate": 0.25,
                        "trigger_precision": 0.70,
                    },
                    {
                        "baseline_name": "gated_skill",
                        "num_controls": 80,
                        "negative_controls": 40,
                        "harmful_skill_injection_rate": 0.05,
                        "trigger_precision": 0.92,
                    },
                ],
            )

            summary = extract_scientific_comparisons(tables_dir=tables, min_denominator=20)
            comparison = _by_id(summary, "negative_controls_only")
            primary = next(item for item in comparison["metrics"] if item["metric"] == "harmful_skill_injection_rate")

            self.assertEqual(primary["denominator"], 40)
            self.assertTrue(primary["meets_expected_direction"])
            self.assertIn(comparison["claim_support"], {"supported", "weakly_supported"})

    def test_cli_writes_json_markdown_and_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tables = root / "tables"
            _write_csv(
                tables / "main_results.csv",
                [
                    {"baseline_name": "raw_mcp", "num_examples": 20, "joint_exact_match": 0.1, "argument_schema_validity": 0.2, "tool_selection_accuracy": 0.3},
                    {"baseline_name": "naive_skill", "num_examples": 20, "joint_exact_match": 0.2, "argument_schema_validity": 0.3, "tool_selection_accuracy": 0.4},
                ],
            )

            subprocess.run(
                [
                    sys.executable,
                    "scripts/extract_scientific_comparisons.py",
                    "--tables-dir",
                    str(tables),
                    "--output-json",
                    str(root / "summary.json"),
                    "--output-md",
                    str(root / "summary.md"),
                    "--output-csv",
                    str(root / "key.csv"),
                    "--min-denominator",
                    "10",
                ],
                cwd=Path.cwd(),
                check=True,
            )

            self.assertTrue((root / "summary.json").exists())
            self.assertTrue((root / "summary.md").exists())
            self.assertTrue((root / "key.csv").exists())
            payload = json.loads((root / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["comparison_count"], 11)


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _by_id(summary: dict, comparison_id: str) -> dict:
    return next(item for item in summary["comparisons"] if item["comparison_id"] == comparison_id)


if __name__ == "__main__":
    unittest.main()

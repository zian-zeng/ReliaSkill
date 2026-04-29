from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from autoskill.metrics import (
    argument_exact_match,
    argument_schema_validity,
    approximate_randomization_test,
    build_metric_tables,
    mcnemar_test,
    wilson_interval,
)


class MetricsTests(unittest.TestCase):
    def test_canonical_exact_match_normalizes_paths_keys_and_optional_defaults(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "head": {"type": "integer"},
                "tail": {"type": "integer", "default": 0},
            },
            "required": ["path"],
        }
        predicted = {"head": 5, "tail": 0, "path": ".\\docs\\README.md"}
        expected = {"path": "docs/README.md", "head": 5}

        self.assertTrue(argument_exact_match(predicted, expected, schema))

    def test_schema_validity_checks_required_fields_and_types(self) -> None:
        schema = {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
        }
        self.assertFalse(argument_schema_validity({"predicted_arguments": {"path": "docs/out.txt"}, "inputSchema": schema}))
        self.assertFalse(argument_schema_validity({"predicted_arguments": {"path": 7, "content": "hi"}, "inputSchema": schema}))
        self.assertTrue(argument_schema_validity({"predicted_arguments": {"path": "docs/out.txt", "content": "hi"}, "inputSchema": schema}))

    def test_wilson_interval_is_well_formed(self) -> None:
        interval = wilson_interval(8, 10)

        self.assertLess(interval["low"], 0.8)
        self.assertGreater(interval["high"], 0.8)
        self.assertGreaterEqual(interval["low"], 0.0)
        self.assertLessEqual(interval["high"], 1.0)

    def test_paired_tests_use_discordant_pairs(self) -> None:
        records = [
            {"task_id": "a", "baseline_name": "autoskill_base", "joint_exact_match": True},
            {"task_id": "a", "baseline_name": "raw_mcp", "joint_exact_match": False},
            {"task_id": "b", "baseline_name": "autoskill_base", "joint_exact_match": True},
            {"task_id": "b", "baseline_name": "raw_mcp", "joint_exact_match": True},
            {"task_id": "c", "baseline_name": "autoskill_base", "joint_exact_match": False},
            {"task_id": "c", "baseline_name": "raw_mcp", "joint_exact_match": True},
        ]

        mcnemar = mcnemar_test(records, "autoskill_base", "raw_mcp")
        approx = approximate_randomization_test(records, "autoskill_base", "raw_mcp", iterations=100)

        self.assertEqual(mcnemar["paired_examples"], 3)
        self.assertEqual(mcnemar["a_only_correct"], 1)
        self.assertEqual(mcnemar["b_only_correct"], 1)
        self.assertGreaterEqual(approx["p_value"], 0.0)
        self.assertLessEqual(approx["p_value"], 1.0)

    def test_build_metric_tables_from_saved_jsonl(self) -> None:
        tables = build_metric_tables("outputs/sample_run")
        main_by_baseline = {row["baseline_name"]: row for row in tables["main_results"]}
        harm_by_baseline = {row["baseline_name"]: row for row in tables["harm_utility"]}

        self.assertEqual(main_by_baseline["autoskill_base"]["joint_exact_match"], 1.0)
        self.assertEqual(main_by_baseline["raw_mcp"]["argument_exact_match"], 0.6667)
        self.assertEqual(main_by_baseline["raw_mcp"]["argument_schema_validity"], 0.6667)
        self.assertEqual(harm_by_baseline["raw_mcp"]["harmful_skill_injection_rate"], 0.5)
        self.assertTrue(tables["stat_tests"])

    def test_make_tables_cli_writes_required_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "tables"
            subprocess.run(
                [sys.executable, "scripts/make_tables.py", "--input", "outputs/sample_run", "--out", str(out_dir)],
                cwd=Path.cwd(),
                check=True,
            )

            for name in ["main_results.csv", "harm_utility.csv", "stat_tests.csv"]:
                self.assertTrue((out_dir / name).exists())
            with (out_dir / "main_results.csv").open("r", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual({row["baseline_name"] for row in rows}, {"autoskill_base", "raw_mcp"})
            self.assertIn("tool_selection_accuracy_wilson_low", rows[0])


if __name__ == "__main__":
    unittest.main()

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
            {"task_id": "a", "baseline_name": "generated_skill_base", "joint_exact_match": True},
            {"task_id": "a", "baseline_name": "raw_mcp", "joint_exact_match": False},
            {"task_id": "b", "baseline_name": "generated_skill_base", "joint_exact_match": True},
            {"task_id": "b", "baseline_name": "raw_mcp", "joint_exact_match": True},
            {"task_id": "c", "baseline_name": "generated_skill_base", "joint_exact_match": False},
            {"task_id": "c", "baseline_name": "raw_mcp", "joint_exact_match": True},
        ]

        mcnemar = mcnemar_test(records, "generated_skill_base", "raw_mcp")
        approx = approximate_randomization_test(records, "generated_skill_base", "raw_mcp", iterations=100)

        self.assertEqual(mcnemar["paired_examples"], 3)
        self.assertEqual(mcnemar["a_only_correct"], 1)
        self.assertEqual(mcnemar["b_only_correct"], 1)
        self.assertGreaterEqual(approx["p_value"], 0.0)
        self.assertLessEqual(approx["p_value"], 1.0)

    def test_paired_tests_do_not_collide_across_model_slugs(self) -> None:
        records = [
            {"model_slug": "m1", "record_type": "benchmark", "task_id": "same", "baseline_name": "generated_skill_base", "joint_exact_match": True},
            {"model_slug": "m1", "record_type": "benchmark", "task_id": "same", "baseline_name": "raw_mcp", "joint_exact_match": False},
            {"model_slug": "m2", "record_type": "benchmark", "task_id": "same", "baseline_name": "generated_skill_base", "joint_exact_match": False},
            {"model_slug": "m2", "record_type": "benchmark", "task_id": "same", "baseline_name": "raw_mcp", "joint_exact_match": True},
        ]

        result = mcnemar_test(records, "generated_skill_base", "raw_mcp")

        self.assertEqual(result["paired_examples"], 2)
        self.assertEqual(result["a_only_correct"], 1)
        self.assertEqual(result["b_only_correct"], 1)

    def test_metric_tables_separate_benchmark_routing_and_harm_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_jsonl(
                root / "prediction_records.jsonl",
                [
                    {
                        "task_id": "pos",
                        "baseline_name": "raw_mcp",
                        "joint_exact_match": True,
                        "exact_match": True,
                        "argument_validity": 1.0,
                        "should_trigger": True,
                        "triggered": True,
                    },
                    {
                        "task_id": "neg",
                        "baseline_name": "raw_mcp",
                        "joint_exact_match": False,
                        "exact_match": False,
                        "argument_validity": 0.0,
                        "should_trigger": False,
                        "triggered": True,
                        "harmful_injection": True,
                    },
                ],
            )
            self._write_jsonl(
                root / "routing_records.jsonl",
                [
                    {
                        "task_id": "pos",
                        "baseline_name": "raw_mcp",
                        "joint_exact_match": False,
                        "exact_match": False,
                        "argument_validity": 0.0,
                        "should_trigger": True,
                        "triggered": True,
                    }
                ],
            )

            tables = build_metric_tables(root)

            self.assertEqual(tables["main_results"][0]["num_examples"], 2)
            self.assertEqual(tables["routing_results"][0]["num_examples"], 1)
            self.assertEqual(tables["harm_utility"][0]["negative_controls"], 1)
            self.assertEqual(tables["harm_utility"][0]["harmful_activations"], 1)

    def test_build_metric_tables_prefers_global_merged_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_jsonl(
                root / "predictors" / "mock" / "shard_00" / "benchmark" / "prediction_records.jsonl",
                [
                    {
                        "task_id": "task-1",
                        "baseline_name": "raw_mcp",
                        "joint_exact_match": False,
                        "exact_match": False,
                        "argument_validity": 0.0,
                    }
                ],
            )
            self._write_jsonl(
                root / "merged" / "prediction_records.jsonl",
                [
                    {
                        "task_id": "task-1",
                        "baseline_name": "raw_mcp",
                        "joint_exact_match": True,
                        "exact_match": True,
                        "argument_validity": 1.0,
                    }
                ],
            )

            tables = build_metric_tables(root)

            self.assertEqual(tables["main_results"][0]["num_examples"], 1)
            self.assertEqual(tables["main_results"][0]["joint_exact_match"], 1.0)

    def test_build_metric_tables_from_saved_jsonl(self) -> None:
        tables = build_metric_tables("outputs/baselines_smoke")
        main_by_baseline = {row["baseline_name"]: row for row in tables["main_results"]}
        harm_by_baseline = {row["baseline_name"]: row for row in tables["harm_utility"]}

        self.assertIn("generated_skill_base", main_by_baseline)
        self.assertIn("raw_mcp", main_by_baseline)
        # generated_skill_base should outperform raw_mcp on joint_exact_match
        self.assertGreater(
            main_by_baseline["generated_skill_base"]["joint_exact_match"],
            main_by_baseline["raw_mcp"]["joint_exact_match"],
        )
        self.assertGreater(main_by_baseline["raw_mcp"]["argument_exact_match"], 0.0)
        self.assertGreater(main_by_baseline["raw_mcp"]["argument_schema_validity"], 0.0)
        self.assertIn("raw_mcp", harm_by_baseline)
        self.assertGreaterEqual(harm_by_baseline["raw_mcp"]["harmful_skill_injection_rate"], 0.0)
        self.assertTrue(tables["stat_tests"])

    def test_make_tables_cli_writes_required_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "tables"
            subprocess.run(
                [sys.executable, "scripts/make_tables.py", "--input", "outputs/baselines_smoke", "--out", str(out_dir)],
                cwd=Path.cwd(),
                check=True,
            )

            for name in ["main_results.csv", "harm_utility.csv", "stat_tests.csv"]:
                self.assertTrue((out_dir / name).exists())
            with (out_dir / "main_results.csv").open("r", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            baseline_names = {row["baseline_name"] for row in rows}
            self.assertTrue({"generated_skill_base", "raw_mcp"}.issubset(baseline_names))
            self.assertIn("tool_selection_accuracy_wilson_low", rows[0])

    @staticmethod
    def _write_jsonl(path: Path, rows: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")


if __name__ == "__main__":
    unittest.main()

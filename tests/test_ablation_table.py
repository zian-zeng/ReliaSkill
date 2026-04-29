from __future__ import annotations

import csv
import subprocess
import sys
import unittest
from pathlib import Path

from autoskill.ablation import DEFAULT_ABLATION_CONDITIONS, run_ablation_table_from_config


class AblationTableTests(unittest.TestCase):
    def test_all_expected_ablation_conditions_are_declared(self) -> None:
        condition_ids = {item["id"] for item in DEFAULT_ABLATION_CONDITIONS}
        self.assertEqual(
            condition_ids,
            {
                "full_reliaskill",
                "without_validation",
                "without_behavior_tests",
                "without_positive_controls",
                "without_negative_controls",
                "without_repair",
                "full_regeneration_repair",
                "without_gating",
                "without_non_use_boundaries",
                "without_examples",
                "without_compactness_constraint",
                "dev_test_leakage_check",
            },
        )

    def test_ablation_table_writes_required_columns(self) -> None:
        output_path = Path("outputs/tables/test_ablation_results.csv")
        details_path = Path("outputs/ablations/test_ablation_details.jsonl")
        rows = run_ablation_table_from_config(
            {
                "tools_path": "data/raw/public_mcp_filesystem_subset.json",
                "dev_controls_path": "data/eval/public_mcp_filesystem_reliability.jsonl",
                "test_controls_path": "data/eval/public_mcp_filesystem_reliability.jsonl",
                "output_path": str(output_path),
                "details_path": str(details_path),
                "seed": 42,
                "max_tools": 2,
                "generator": {"type": "heuristic"},
                "predictor": {"type": "heuristic"},
            }
        )

        self.assertEqual(len(rows), 12)
        self.assertTrue(output_path.exists())
        with output_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            self.assertIn("joint_em", reader.fieldnames or [])
            self.assertIn("argument_validity", reader.fieldnames or [])
            self.assertIn("trigger_precision", reader.fieldnames or [])
            self.assertIn("hsir", reader.fieldnames or [])
            self.assertIn("score", reader.fieldnames or [])
            self.assertIn("score_ci_low", reader.fieldnames or [])
            self.assertEqual(len(list(reader)), 12)

    def test_ablation_script_smoke_config(self) -> None:
        config_path = Path("outputs/ablations/test_ablation_smoke.yaml")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            "\n".join(
                [
                    "tools_path: data/raw/public_mcp_filesystem_subset.json",
                    "dev_controls_path: data/eval/public_mcp_filesystem_reliability.jsonl",
                    "test_controls_path: data/eval/public_mcp_filesystem_reliability.jsonl",
                    "output_path: outputs/tables/test_ablation_script_results.csv",
                    "details_path: outputs/ablations/test_ablation_script_details.jsonl",
                    "seed: 42",
                    "max_tools: 1",
                    "generator:",
                    "  type: heuristic",
                    "predictor:",
                    "  type: heuristic",
                ]
            ),
            encoding="utf-8",
        )

        subprocess.run(
            [sys.executable, "scripts/run_ablation_table.py", "--config", str(config_path)],
            cwd=Path.cwd(),
            check=True,
        )
        self.assertTrue(Path("outputs/tables/test_ablation_script_results.csv").exists())


if __name__ == "__main__":
    unittest.main()

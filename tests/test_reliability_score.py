from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from autoskill.behavior import load_behavior_cases, run_behavior_tests
from autoskill.ir import BehaviorReport, BehaviorResult, GeneratedSkill
from autoskill.parser import parse_mcp_tool
from autoskill.quality import score_reliability
from autoskill.reliability_score import (
    compute_reliability_components,
    compute_reliability_score_value,
    threshold_sweep_rows,
    weight_sensitivity_rows,
)
from autoskill.validator import validate_skill


def _load_public_tool(name: str):
    raw_tools = json.loads(Path("data/raw/public_mcp_filesystem_subset.json").read_text(encoding="utf-8"))
    for index, raw_tool in enumerate(raw_tools):
        if raw_tool["name"] == name:
            return parse_mcp_tool(raw_tool, source_pointer=f"public_tools#{index}")
    raise AssertionError(f"missing fixture tool {name}")


class ReliabilityScoreTests(unittest.TestCase):
    def test_formula_score_decomposes_visible_components(self) -> None:
        tool = _load_public_tool("write_file")
        skill = GeneratedSkill(
            baseline_name="validated_skill",
            skill_summary="Write file contents with caution.",
            when_to_use=["Use when the user provides path and content."],
            when_not_to_use=["Do not overwrite, delete, or mutate files unless the user explicitly asks."],
            argument_template={"path": "docs/out.txt", "content": "hello"},
            examples=[],
        )
        validation = validate_skill(tool, skill)
        behavior = BehaviorReport(
            valid=False,
            results=[
                BehaviorResult("p1", "write_file", True, True, exact_match=True, argument_validity=1.0),
                BehaviorResult("p2", "write_file", True, True, exact_match=False, argument_validity=0.5),
                BehaviorResult("n1", "write_file", False, False, exact_match=True, argument_validity=1.0),
                BehaviorResult("n2", "write_file", False, True, exact_match=False, argument_validity=0.0, harmful_injection=True),
            ],
            metrics={
                "trigger_precision": 0.6667,
                "trigger_recall": 1.0,
                "harmful_skill_injection_rate": 0.5,
                "exact_match_rate": 0.5,
                "avg_argument_validity": 0.75,
                "avg_prediction_latency_ms": 1.0,
            },
        )

        components = compute_reliability_components(tool, skill, validation, behavior)
        score = score_reliability(tool, skill, validation, behavior)

        self.assertEqual(components["V"], 1.0)
        self.assertEqual(components["P"], 0.5)
        self.assertEqual(components["N"], 0.5)
        self.assertEqual(components["A"], 0.75)
        self.assertEqual(components["C"], 1.0)
        self.assertEqual(components["S"], 1.0)
        self.assertEqual(score.score, compute_reliability_score_value(components))
        self.assertEqual(score.score, 67.5)
        self.assertEqual(score.decision, "reject")
        self.assertIn("components", score.features)
        self.assertIn("formula", score.features)
        self.assertIn("harmful_skill_injection", score.features["critical_failures"])

    def test_deploy_repair_reject_thresholds(self) -> None:
        self.assertEqual(compute_reliability_score_value({"V": 1, "P": 1, "N": 1, "A": 1, "C": 1, "S": 1}), 100.0)
        self.assertEqual(compute_reliability_score_value({"V": 1, "P": 0, "N": 1, "A": 0, "C": 1, "S": 1}), 60.0)
        self.assertEqual(compute_reliability_score_value({"V": 0, "P": 0, "N": 0, "A": 0, "C": 1, "S": 1}), 10.0)

    def test_real_behavior_score_json_contains_components(self) -> None:
        tool = _load_public_tool("write_file")
        skill = GeneratedSkill(
            baseline_name="naive_skill",
            skill_summary="Write files and search docs.",
            when_to_use=["Use this for search docs."],
            when_not_to_use=["Do not use for unrelated tasks."],
            argument_template={"path": "docs/out.txt", "content": "notes"},
            examples=[],
        )
        validation = validate_skill(tool, skill)
        behavior = run_behavior_tests(tool, skill, load_behavior_cases("data/eval/public_mcp_filesystem_reliability.jsonl"))
        score = score_reliability(tool, skill, validation, behavior)

        self.assertIn("components", score.features)
        self.assertIn("weights", score.features)
        self.assertEqual(score.features["weights"]["P"], 0.3)
        self.assertEqual(score.decision, "reject")

    def test_threshold_and_weight_sensitivity_rows(self) -> None:
        records = [
            {
                "tool_name": "a",
                "condition": "validated_skill",
                "reliability_score": {
                    "score": 90,
                    "features": {"components": {"V": 1, "P": 1, "N": 1, "A": 1, "C": 1, "S": 1}, "repair_rounds": 0},
                },
            }
        ]

        threshold_rows = threshold_sweep_rows(records, thresholds=[80, 95])
        weight_rows = weight_sensitivity_rows(records)

        self.assertEqual(len(threshold_rows), 2)
        self.assertEqual(threshold_rows[0]["deploy_count"], 1)
        self.assertEqual(threshold_rows[1]["deploy_count"], 0)
        self.assertEqual(len(weight_rows), 12)
        self.assertTrue(any(row["component"] == "P" and row["direction"] == "plus_10pct" for row in weight_rows))

    def test_sensitivity_script_writes_required_artifacts(self) -> None:
        subprocess.run(
            [sys.executable, "scripts/run_reliability_sensitivity.py"],
            cwd=Path.cwd(),
            check=True,
        )

        self.assertTrue(Path("outputs/tables/reliability_threshold_sensitivity.csv").exists())
        self.assertTrue(Path("outputs/tables/reliability_weight_sensitivity.csv").exists())
        pdf = Path("outputs/figures/reliability_calibration.pdf")
        self.assertTrue(pdf.exists())
        self.assertTrue(pdf.read_bytes().startswith(b"%PDF"))
        definition = Path("outputs/reports/reliability_score_definition.md").read_text(encoding="utf-8")
        self.assertIn("0.20*V", definition)


if __name__ == "__main__":
    unittest.main()

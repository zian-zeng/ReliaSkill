from __future__ import annotations

import csv
import subprocess
import sys
import unittest
from pathlib import Path

from autoskill.conditions import REVIEWER_BASELINES
from autoskill.experiment import build_skill_variant_map, load_tools
from autoskill.generator import SkillGenerator


class ConditionsTests(unittest.TestCase):
    def test_reviewer_baselines_are_named_conditions_on_smoke_tools(self) -> None:
        tools = load_tools("data/raw/public_mcp_filesystem_subset.json")
        generator = SkillGenerator(backend_config={"type": "heuristic"})
        expected = set(REVIEWER_BASELINES)

        self.assertEqual(len(tools), 5)
        for tool in tools.values():
            variants = build_skill_variant_map(tool, tools, generator)
            self.assertTrue(expected.issubset(variants))
            for baseline in expected:
                self.assertEqual(variants[baseline].baseline_name, baseline)

    def test_reviewer_baselines_build_for_full_minimum_dataset(self) -> None:
        tools = load_tools("data/raw_mcp/tools.jsonl")
        generator = SkillGenerator(backend_config={"type": "heuristic"})
        expected = set(REVIEWER_BASELINES)

        self.assertGreaterEqual(len(tools), 80)
        for tool in tools.values():
            variants = build_skill_variant_map(tool, tools, generator)
            self.assertTrue(expected.issubset(variants))

    def test_baselines_smoke_experiment_outputs_results_and_prompts(self) -> None:
        subprocess.run(
            [sys.executable, "scripts/run_experiment.py", "--config", "configs/experiments/baselines_smoke.yaml"],
            cwd=Path.cwd(),
            check=True,
        )

        results_path = Path("outputs/tables/baseline_results.csv")
        self.assertTrue(results_path.exists())
        with results_path.open("r", encoding="utf-8") as f:
            rows = [row for row in csv.DictReader(f) if row.get("condition")]
        conditions = {row["condition"] for row in rows}
        self.assertTrue(set(REVIEWER_BASELINES).issubset(conditions))

        prompt_dir = Path("outputs/prompts")
        self.assertTrue(prompt_dir.exists())
        for baseline in REVIEWER_BASELINES:
            self.assertTrue(any(path.name.endswith(f"__{baseline}.txt") for path in prompt_dir.glob("*.txt")))


if __name__ == "__main__":
    unittest.main()

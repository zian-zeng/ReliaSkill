from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from autoskill.backends import HeuristicBackend
from autoskill.multi_candidate import (
    generate_skill_candidates,
    load_tools_as_toolir,
    score_skill_candidates,
    select_candidate,
)
from autoskill.backends import safe_generate_skill


class MultiCandidateTests(unittest.TestCase):
    def test_generate_k_candidates_and_baseline_k1(self) -> None:
        tool = load_tools_as_toolir("data/processed_toolir/tools.jsonl", limit=1)[0]
        base = safe_generate_skill(tool, HeuristicBackend(ablation_mode="base_only"))

        one = generate_skill_candidates(tool, base, k=1)
        three = generate_skill_candidates(tool, base, k=3)

        self.assertEqual(len(one), 1)
        self.assertEqual(one[0]["generation_strategy"], "concise_default")
        self.assertEqual(len(three), 3)
        self.assertEqual([item["generation_strategy"] for item in three], ["concise_default", "boundary_heavy", "example_heavy"])
        for candidate in three:
            payload = candidate["candidate"]
            for key in [
                "candidate_id",
                "generation_strategy",
                "prompt_template_id",
                "skill_text",
                "argument_template",
                "examples",
                "when_to_use",
                "when_not_to_use",
                "token_count",
            ]:
                self.assertIn(key, payload)

    def test_candidate_scoring_and_selection_policies(self) -> None:
        tool = load_tools_as_toolir("data/processed_toolir/tools.jsonl", limit=1)[0]
        base = safe_generate_skill(tool, HeuristicBackend(ablation_mode="base_only"))
        candidates = generate_skill_candidates(tool, base, k=3)
        rows = score_skill_candidates(tool, candidates, cases=[])

        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertIn("structural_validity", row)
            self.assertIn("compactness", row)
            self.assertIn("schema_faithfulness", row)
            self.assertIn("positive_dev_control_pass_rate", row)
            self.assertIn("negative_dev_control_non_harm_rate", row)
            self.assertIn("safety_annotation_preservation", row)

        validation_selected = select_candidate(rows, policy="best_validation_only")
        reliability_selected = select_candidate(rows, policy="best_reliability_score")
        self.assertIn(validation_selected["candidate_id"], {row["candidate_id"] for row in rows})
        self.assertIn(reliability_selected["candidate_id"], {row["candidate_id"] for row in rows})

    def test_cli_writes_candidate_artifacts_without_test_controls(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            tools_path = tmpdir_path / "tools.jsonl"
            controls_path = tmpdir_path / "dev.jsonl"
            output_dir = tmpdir_path / "skills"
            tools_path.write_text(
                "\n".join(Path("data/processed_toolir/tools.jsonl").read_text(encoding="utf-8").splitlines()[:1]) + "\n",
                encoding="utf-8",
            )
            controls_path.write_text(
                "\n".join(Path("data/controls/dev.jsonl").read_text(encoding="utf-8").splitlines()[:3]) + "\n",
                encoding="utf-8",
            )
            config_path = tmpdir_path / "multi_candidate.yaml"
            config_path.write_text(
                yaml.safe_dump(
                    {
                        "tools_path": str(tools_path),
                        "dev_controls_path": str(controls_path),
                        "output_dir": str(output_dir),
                        "candidate_k": 3,
                        "selection_policy": "best_behavior_dev",
                        "generation_backend": {"type": "heuristic", "ablation_mode": "base_only"},
                    }
                ),
                encoding="utf-8",
            )

            subprocess.run(
                [sys.executable, "scripts/run_generation.py", "--config", str(config_path)],
                cwd=Path.cwd(),
                check=True,
            )

            scores_path = output_dir / "candidate_scores.jsonl"
            self.assertTrue(scores_path.exists())
            rows = [json.loads(line) for line in scores_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 3)
            tool_dirs = [path for path in output_dir.iterdir() if path.is_dir()]
            self.assertEqual(len(tool_dirs), 1)
            tool_dir = tool_dirs[0]
            self.assertTrue((tool_dir / "selected_candidate.json").exists())
            self.assertTrue((tool_dir / "selection_report.json").exists())
            report = json.loads((tool_dir / "selection_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["candidate_count"], 3)
            self.assertFalse(report["test_controls_used"])


if __name__ == "__main__":
    unittest.main()

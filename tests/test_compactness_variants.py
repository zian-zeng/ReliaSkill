from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from autoskill.backends import HeuristicBackend, safe_generate_skill
from autoskill.compactness import build_compactness_variants, compactness_records_for_tool
from autoskill.multi_candidate import load_tools_as_toolir


class CompactnessVariantTests(unittest.TestCase):
    def test_compactness_variants_apply_token_budget_metadata(self) -> None:
        tool = load_tools_as_toolir("data/processed_toolir/tools.jsonl", limit=1)[0]
        base = safe_generate_skill(tool, HeuristicBackend(ablation_mode="base_only"))

        variants = build_compactness_variants(tool, base)

        self.assertEqual(
            [variant.baseline_name for variant in variants],
            [
                "skill_ultra_compact",
                "skill_compact",
                "skill_medium",
                "skill_verbose",
                "generated_docs_verbose",
                "raw_docs_full",
            ],
        )
        ultra = next(variant for variant in variants if variant.baseline_name == "skill_ultra_compact")
        self.assertLessEqual(ultra.metadata["token_accounting"]["skill_token_count"], 150)
        self.assertEqual(ultra.metadata["max_examples"], 0)
        self.assertTrue(ultra.metadata["include_argument_template"])
        raw_docs = next(variant for variant in variants if variant.baseline_name == "raw_docs_full")
        self.assertEqual(raw_docs.argument_template, {})
        self.assertEqual(raw_docs.examples, [])

        records = compactness_records_for_tool(tool, variants)
        for record in records:
            self.assertIn("skill_token_count", record)
            self.assertIn("prompt_token_count", record)
            self.assertIn("total_representation_tokens", record)
            self.assertIn("sections_included", record)
            self.assertIn("examples_count", record)
            self.assertIn("nonuse_boundary_count", record)

    def test_generation_cli_writes_compactness_stats(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tools_path = root / "tools.jsonl"
            controls_path = root / "dev.jsonl"
            output_dir = root / "skills"
            records_path = root / "compactness_records.jsonl"
            stats_path = root / "skill_compactness_stats.csv"
            tools_path.write_text(
                "\n".join(Path("data/processed_toolir/tools.jsonl").read_text(encoding="utf-8").splitlines()[:1]) + "\n",
                encoding="utf-8",
            )
            controls_path.write_text(
                "\n".join(Path("data/controls/dev.jsonl").read_text(encoding="utf-8").splitlines()[:2]) + "\n",
                encoding="utf-8",
            )
            config_path = root / "compactness.yaml"
            config_path.write_text(
                yaml.safe_dump(
                    {
                        "tools_path": str(tools_path),
                        "dev_controls_path": str(controls_path),
                        "output_dir": str(output_dir),
                        "candidate_k": 1,
                        "selection_policy": "best_validation_only",
                        "generation_backend": {"type": "heuristic", "ablation_mode": "base_only"},
                        "compactness_variants": {
                            "enabled": True,
                            "conditions": ["skill_ultra_compact", "skill_compact", "raw_docs_full"],
                            "records_path": str(records_path),
                            "stats_path": str(stats_path),
                        },
                    }
                ),
                encoding="utf-8",
            )

            subprocess.run(
                [sys.executable, "scripts/run_generation.py", "--config", str(config_path)],
                cwd=Path.cwd(),
                check=True,
            )

            self.assertTrue(records_path.exists())
            self.assertTrue(stats_path.exists())
            records = [json.loads(line) for line in records_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(records), 3)
            with stats_path.open("r", encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual({row["condition"] for row in rows}, {"skill_ultra_compact", "skill_compact", "raw_docs_full"})
            self.assertIn("mean_skill_tokens", rows[0])
            self.assertTrue((output_dir / "compactness").exists())


if __name__ == "__main__":
    unittest.main()

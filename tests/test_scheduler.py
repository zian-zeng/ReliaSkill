from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from reliaskill.scheduler import build_run_plan, load_model_config, plan_experiment_run


class SchedulerTests(unittest.TestCase):
    def test_model_config_defaults_batch_size_for_7b(self) -> None:
        model = load_model_config(
            {
                "model_name": "Qwen/Qwen2.5-7B-Instruct",
                "backend": "local_hf",
                "load_in_4bit": True,
                "estimated_vram_gb": 9.5,
            }
        )

        self.assertEqual(model.batch_size, 1)
        self.assertEqual(model.backend, "local_hf")

    def test_plan_groups_by_model_and_counts_resume(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            output_root = root / "outputs"
            result_path = output_root / "benchmark" / "bank_get_account_balance" / "skill_compact" / "ctrl_existing.result.json"
            result_path.parent.mkdir(parents=True, exist_ok=True)
            result_path.write_text("{}", encoding="utf-8")
            tasks_path = root / "tasks.jsonl"
            tasks_path.write_text(
                "\n".join(
                    [
                        '{"task_id":"ctrl_existing","tool_name":"bank_get_account_balance","user_request":"Get balance","should_trigger":true}',
                        '{"task_id":"ctrl_new","tool_name":"bank_get_account_balance","user_request":"Get balance again","should_trigger":true}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            config = {
                "tools_path": "data/raw_mcp/tools.jsonl",
                "tasks_path": str(tasks_path),
                "output_root": str(output_root),
                "models": [
                    {
                        "model_name": "small",
                        "backend": "local_hf",
                        "load_in_4bit": True,
                        "estimated_vram_gb": 4.0,
                        "batch_size": 1,
                        "max_prompt_tokens": 2048,
                    },
                    {
                        "model_name": "Qwen/Qwen2.5-7B-Instruct",
                        "backend": "local_hf",
                        "load_in_4bit": True,
                        "estimated_vram_gb": 9.5,
                        "max_prompt_tokens": 2048,
                    },
                ],
                "conditions": ["skill_compact", "raw_docs_full"],
                "scheduler": {"resume": True, "max_batch_size": 2, "examples_per_second": 1.0},
            }

            plan = build_run_plan(config, gpu_budget_gb=12.0)

            self.assertTrue(plan["valid"])
            self.assertEqual(plan["model_execution_order"], ["Qwen/Qwen2.5-7B-Instruct", "small"])
            self.assertEqual(len(plan["runs"]), 4)
            compact_rows = [row for row in plan["runs"] if row["condition"] == "skill_compact"]
            self.assertTrue(all(row["completed_examples"] == 1 for row in compact_rows))
            self.assertTrue(all(row["remaining_examples"] == 1 for row in compact_rows))

    def test_plan_blocks_when_vram_exceeds_budget(self) -> None:
        config = {
            "tools_path": "data/raw_mcp/tools.jsonl",
            "tasks_path": "data/controls/test.jsonl",
            "output_root": "outputs/test_scheduler",
            "models": [{"model_name": "too_big", "backend": "local_hf", "estimated_vram_gb": 24.0, "batch_size": 1}],
            "conditions": ["skill_compact"],
        }

        plan = build_run_plan(config, gpu_budget_gb=12.0)

        self.assertFalse(plan["valid"])
        self.assertTrue(any("exceeds available budget" in error for error in plan["errors"]))
        self.assertEqual(plan["runs"][0]["status"], "blocked")

    def test_cli_writes_plan_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = root / "experiment.yaml"
            report_path = root / "run_plan.md"
            csv_path = root / "run_plan.csv"
            config_path.write_text(
                yaml.safe_dump(
                    {
                        "tools_path": "data/raw_mcp/tools.jsonl",
                        "tasks_path": "data/controls/test.jsonl",
                        "output_root": str(root / "outputs"),
                        "models": [{"model_name": "mock", "backend": "heuristic", "estimated_vram_gb": 0.0, "batch_size": 1}],
                        "conditions": ["skill_compact"],
                    }
                ),
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    "scripts/plan_experiment_run.py",
                    "--config",
                    str(config_path),
                    "--gpu_budget_gb",
                    "12",
                    "--output-report",
                    str(report_path),
                    "--output-csv",
                    str(csv_path),
                ],
                cwd=Path.cwd(),
                check=True,
            )

            self.assertTrue(report_path.exists())
            self.assertTrue(csv_path.exists())
            with csv_path.open("r", encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["condition"], "skill_compact")

    def test_emnlp_scale_configs_are_dry_run_plannable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for config_name, expected_tools in [
                ("minimum_credible.yaml", 100),
                ("strong_emnlp.yaml", 250),
                ("stretch_emnlp.yaml", 290),
                ("emnlp_acceptance.yaml", 290),
            ]:
                plan = plan_experiment_run(
                    Path("configs/experiments") / config_name,
                    gpu_budget_gb=12,
                    output_report=root / f"{config_name}.md",
                    output_csv=root / f"{config_name}.csv",
                )

                self.assertTrue(plan["valid"])
                self.assertEqual(plan["num_tools"], expected_tools)
                self.assertGreater(plan["total_remaining_model_calls"], 0)
                self.assertGreater(plan["total_token_volume"], 0)
                self.assertGreaterEqual(plan["estimated_disk_usage_gb"], 0.0)

    def test_sharded_plan_does_not_warn_about_full_target_tool_count(self) -> None:
        plan = build_run_plan(
            {
                "tools_path": "data/raw_mcp/tools.jsonl",
                "tasks_path": "data/controls/test.jsonl",
                "output_root": "outputs/test_scheduler",
                "target_tools": 290,
                "data": {"max_tools": 290},
                "models": [{"model_name": "mock", "backend": "heuristic", "estimated_vram_gb": 0.0, "batch_size": 1}],
                "conditions": ["raw_mcp"],
            },
            gpu_budget_gb=24,
            shard_index=0,
            num_shards=4,
        )

        self.assertEqual(plan["num_tools"], 73)
        self.assertFalse(any("target_tools=290" in warning for warning in plan["warnings"]))

    def test_routing_enabled_conservatively_counts_second_phase_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tasks_path = root / "tasks.jsonl"
            tasks_path.write_text(
                "\n".join(
                    [
                        '{"task_id":"ctrl_a","tool_name":"bank_get_account_balance","user_request":"Get balance","should_trigger":true}',
                        '{"task_id":"ctrl_b","tool_name":"bank_get_account_balance","user_request":"Get balance again","should_trigger":true}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            config = {
                "tools_path": "data/raw_mcp/tools.jsonl",
                "tasks_path": str(tasks_path),
                "output_root": str(root / "outputs"),
                "models": [{"model_name": "mock", "backend": "heuristic", "estimated_vram_gb": 0.0, "batch_size": 1}],
                "conditions": ["raw_mcp"],
                "scheduler": {"include_routing": True, "examples_per_second": 1.0},
            }

            plan = build_run_plan(config, gpu_budget_gb=12.0)

            self.assertEqual(plan["runs"][0]["benchmark_remaining_examples"], 2)
            self.assertEqual(plan["runs"][0]["routing_remaining_examples"], 2)
            self.assertEqual(plan["runs"][0]["estimated_model_calls"], 4)
            self.assertEqual(plan["total_remaining_model_calls"], 4)

    def test_v1_contract_ablations_use_v1_prompt_overhead_estimate(self) -> None:
        config = {
            "tools_path": "data/raw_mcp/tools.jsonl",
            "tasks_path": "data/controls/test.jsonl",
            "output_root": "outputs/test_scheduler",
            "models": [{"model_name": "mock", "backend": "heuristic", "estimated_vram_gb": 0.0, "batch_size": 1}],
            "conditions": ["reliaskill_v1", "reliaskill_v1_no_runtime_grounding"],
        }

        plan = build_run_plan(config, gpu_budget_gb=12.0)

        rows = {row["condition"]: row for row in plan["runs"]}
        self.assertEqual(
            rows["reliaskill_v1"]["estimated_prompt_tokens_per_call"],
            rows["reliaskill_v1_no_runtime_grounding"]["estimated_prompt_tokens_per_call"],
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from reliaskill.cluster import (
    build_shared_skill_packages,
    merge_cluster_shards,
    run_cluster_shard,
    selected_tool_names,
)
from autoskill.experiment import load_tools


class ClusterRunnerTests(unittest.TestCase):
    def test_tool_shards_cover_selected_tools_without_overlap(self) -> None:
        config = {"tools_path": "data/raw_mcp/tools.jsonl", "data": {"max_tools": 20}}
        tools = load_tools(config["tools_path"])
        expected = set(selected_tool_names(config, tools))
        shards = [set(selected_tool_names(config, tools, shard_index=i, num_shards=4)) for i in range(4)]

        self.assertEqual(set().union(*shards), expected)
        for left_index, left in enumerate(shards):
            for right in shards[left_index + 1 :]:
                self.assertFalse(left.intersection(right))

    def test_cluster_shard_dry_run_reports_subset_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = self._write_small_config(Path(tmpdir), conditions=["raw_mcp", "generated_skill_base"])

            result = run_cluster_shard(config_path, shard_index=0, num_shards=2, dry_run=True)

            self.assertTrue(result["dry_run"])
            self.assertEqual(result["num_full_tools"], 4)
            self.assertGreater(result["num_shard_tools"], 0)
            self.assertGreater(result["num_tasks"], 0)

    def test_shared_package_builder_writes_gated_skill_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = self._write_small_config(root, conditions=["generated_skill_base", "gated_skill"], max_tools=1)

            manifest = build_shared_skill_packages(config_path)

            package_root = Path(manifest["shared_package_root"])
            gated = list(package_root.glob("*/gated_skill/skill.json"))
            self.assertEqual(len(gated), 1)

    def test_output_root_override_moves_shared_packages(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = self._write_small_config(root, conditions=["generated_skill_base"], max_tools=1)

            manifest = build_shared_skill_packages(config_path, output_root=root / "scratch")

            self.assertEqual(Path(manifest["shared_package_root"]), root / "scratch" / "shared_packages")

    def test_merge_writes_by_model_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = self._write_small_config(root, conditions=["raw_mcp"], max_tools=1)
            shard_dir = root / "out" / "predictors" / "mock" / "shard_00" / "benchmark"
            shard_dir.mkdir(parents=True)
            self._write_jsonl(
                shard_dir / "prediction_records.jsonl",
                [
                    {
                        "task_id": "t1",
                        "tool_name": "read_text_file",
                        "baseline_name": "raw_mcp",
                        "predicted_arguments": {},
                        "expected_arguments": {},
                        "exact_match": True,
                        "argument_validity": 1.0,
                        "model_name": "mock",
                        "model_slug": "mock",
                    }
                ],
            )

            manifest = merge_cluster_shards(config_path, output_root=root / "out")

            self.assertEqual(manifest["prediction_records"], 1)
            self.assertTrue((root / "out" / "tables" / "main_results_by_model.csv").exists())
            self.assertTrue((root / "out" / "tables" / "routing_results_by_model.csv").exists())

    def test_merge_collects_live_exec_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = self._write_small_config(root, conditions=["raw_mcp"], max_tools=1)
            shard_dir = root / "out" / "predictors" / "mock" / "shard_00" / "live_exec"
            shard_dir.mkdir(parents=True)
            self._write_jsonl(
                shard_dir / "live_exec_results.jsonl",
                [
                    {
                        "live_task_id": "live_1",
                        "task_id": "live_1",
                        "tool_id": "fs_read_file",
                        "baseline_name": "raw_mcp",
                        "model_name": "mock",
                        "model_slug": "mock",
                        "predicted_call_valid": True,
                        "execution_success": True,
                        "observation_match": True,
                        "state_match": True,
                        "unsafe_action_blocked": False,
                        "live_joint_success": True,
                    }
                ],
            )

            manifest = merge_cluster_shards(config_path, output_root=root / "out")

            self.assertEqual(manifest["live_exec_records"], 1)
            self.assertTrue((root / "out" / "merged" / "live_exec_results.jsonl").exists())
            self.assertTrue((root / "out" / "tables" / "live_exec_results.csv").exists())

    def test_cache_clear_called_after_each_model_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = self._write_small_config(root, conditions=["raw_mcp"], max_tools=1)
            config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            config["models"] = [
                {"model_name": "mock_a", "backend": "heuristic", "batch_size": 1},
                {"model_name": "mock_b", "backend": "heuristic", "batch_size": 1},
            ]
            config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

            with patch("reliaskill.cluster.run_benchmark_pipeline", return_value=([], {}, {})), patch(
                "reliaskill.cluster.clear_model_cache"
            ) as clear_cache:
                run_cluster_shard(config_path, shard_index=0, num_shards=1, skip_routing=True)

            self.assertEqual(clear_cache.call_count, 2)

    def test_strict_cluster_failure_still_clears_model_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = self._write_small_config(root, conditions=["raw_mcp"], max_tools=1)
            config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            config["runtime"] = {"strict_backends": True}
            config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

            with patch("reliaskill.cluster.run_benchmark_pipeline", side_effect=RuntimeError("model failed")), patch(
                "reliaskill.cluster.clear_model_cache"
            ) as clear_cache:
                with self.assertRaises(RuntimeError):
                    run_cluster_shard(config_path, shard_index=0, num_shards=1, skip_routing=True)

            self.assertEqual(clear_cache.call_count, 1)

    def test_merge_rejects_duplicate_prediction_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = self._write_small_config(root, conditions=["raw_mcp"], max_tools=1)
            for shard in ["shard_00", "shard_01"]:
                shard_dir = root / "out" / "predictors" / "mock" / shard / "benchmark"
                shard_dir.mkdir(parents=True)
                self._write_jsonl(
                    shard_dir / "prediction_records.jsonl",
                    [
                        {
                            "task_id": "dup",
                            "tool_name": "read_text_file",
                            "baseline_name": "raw_mcp",
                            "predicted_arguments": {},
                            "expected_arguments": {},
                            "exact_match": True,
                            "argument_validity": 1.0,
                            "model_name": "mock",
                            "model_slug": "mock",
                        }
                    ],
                )

            with self.assertRaises(ValueError):
                merge_cluster_shards(config_path, output_root=root / "out")

    @staticmethod
    def _write_small_config(root: Path, *, conditions: list[str], max_tools: int = 4) -> Path:
        config_path = root / "cluster_small.yaml"
        config = {
            "tools_path": "data/raw/public_mcp_filesystem_subset.json",
            "tasks_path": "data/eval/public_mcp_filesystem_benchmark.jsonl",
            "output_root": str(root / "out"),
            "conditions": conditions,
            "data": {"max_tools": max_tools},
            "models": [{"model_name": "mock", "backend": "heuristic", "batch_size": 1}],
            "shared_skill_packages": {
                "root": str(root / "shared_packages"),
                "dev_controls_path": "data/eval/public_mcp_filesystem_reliability.jsonl",
                "reliability_predictor": {"type": "heuristic"},
            },
        }
        config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
        return config_path

    @staticmethod
    def _write_jsonl(path: Path, rows: list[dict]) -> None:
        with path.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")


if __name__ == "__main__":
    unittest.main()

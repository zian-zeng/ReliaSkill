from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from reliaskill.live_exec.evaluator import evaluate_live_exec_tasks, summarize_live_results
from reliaskill.live_exec.filesystem_sandbox import FilesystemSandbox
from reliaskill.live_exec.git_sandbox import GitSandbox
from reliaskill.live_exec.task_builder import build_live_exec_tasks


class LiveExecTests(unittest.TestCase):
    def test_filesystem_blocks_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sandbox = FilesystemSandbox(Path(tmpdir) / "fs")
            sandbox.setup({"files": [{"path": "safe.txt", "content": "safe"}]})

            result = sandbox.call("fs_read_file", {"path": "../secret.txt"})

            self.assertFalse(result["ok"])
            self.assertEqual(result["error"], "path_traversal_blocked")
            self.assertTrue(result["unsafe_action_blocked"])

    def test_git_mock_blocks_network_operations(self) -> None:
        sandbox = GitSandbox(Path("unused"))
        sandbox.setup({})

        result = sandbox.call("git_fetch", {"remote": "origin"})

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "network_operation_blocked")
        self.assertTrue(result["unsafe_action_blocked"])

    def test_task_builder_creates_balanced_live_subset(self) -> None:
        tasks = build_live_exec_tasks()

        self.assertGreaterEqual(len(tasks), 50)
        self.assertLessEqual(len(tasks), 150)
        self.assertEqual({task["domain"] for task in tasks}, {"filesystem", "sqlite", "git"})
        self.assertTrue({"easy", "medium", "hard"}.issubset({task["difficulty"] for task in tasks}))
        for task in tasks:
            for key in [
                "live_task_id",
                "domain",
                "tool_id",
                "initial_state_setup",
                "user_request",
                "expected_tool_call",
                "expected_observation",
                "expected_state_change",
                "forbidden_actions",
                "cleanup_policy",
                "difficulty",
            ]:
                self.assertIn(key, task)

    def test_gold_live_eval_smoke_succeeds(self) -> None:
        tasks = build_live_exec_tasks()[:12]
        results = evaluate_live_exec_tasks(tasks, use_gold=True)
        summary = summarize_live_results(results)

        self.assertEqual(summary["num_tasks"], 12)
        self.assertEqual(summary["live_joint_success"], 1.0)

    def test_cli_build_and_gold_eval_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tasks_path = root / "live_tasks.jsonl"
            stats_path = root / "live_stats.csv"
            results_path = root / "live_results.csv"
            details_path = root / "live_results.jsonl"

            subprocess.run(
                [
                    sys.executable,
                    "scripts/build_live_exec_tasks.py",
                    "--output",
                    str(tasks_path),
                    "--stats",
                    str(stats_path),
                ],
                cwd=Path.cwd(),
                check=True,
            )
            subprocess.run(
                [
                    sys.executable,
                    "scripts/run_live_exec_eval.py",
                    "--tasks",
                    str(tasks_path),
                    "--output",
                    str(results_path),
                    "--details",
                    str(details_path),
                    "--use-gold",
                    "--limit",
                    "10",
                ],
                cwd=Path.cwd(),
                check=True,
            )

            self.assertTrue(tasks_path.exists())
            self.assertTrue(stats_path.exists())
            self.assertTrue(results_path.exists())
            self.assertTrue(details_path.exists())
            with results_path.open("r", encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 10)
            self.assertTrue(all(row["live_joint_success"] == "True" for row in rows))


if __name__ == "__main__":
    unittest.main()

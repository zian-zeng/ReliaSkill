import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from autoskill.progress import write_progress_state
from reliaskill.progress_monitor import ProgressPlan, TaskRef, scan_progress


class ProgressMonitorTest(unittest.TestCase):
    def _plan(self, root: Path) -> ProgressPlan:
        return ProgressPlan(
            config_path=Path("config.yaml"),
            output_root=root,
            model_slugs=["model_a"],
            model_names={"model_a": "Model A"},
            conditions=["condition_a", "condition_b"],
            tasks_by_shard={0: [TaskRef("task_1", "tool_a"), TaskRef("task_2", "tool_a")]},
            benchmark_total=4,
            routing_total=4,
            live_total=0,
        )

    def test_scan_counts_result_files_and_reads_heartbeat(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result_dir = root / "predictors" / "model_a" / "shard_00" / "benchmark" / "tool_a" / "condition_a"
            result_dir.mkdir(parents=True)
            (result_dir / "task_1.result.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
            routing_dir = root / "predictors" / "model_a" / "shard_00" / "routing_benchmark" / "task_1"
            routing_dir.mkdir(parents=True)
            (routing_dir / "condition_a.routing.json").write_text(json.dumps({"ok": True}), encoding="utf-8")

            write_progress_state(
                root / "predictors" / "model_a" / "shard_00" / "benchmark",
                phase="benchmark",
                status="running",
                task_id="task_1",
                tool_name="tool_a",
                condition="condition_b",
            )

            snapshot = scan_progress(self._plan(root))

            self.assertEqual(snapshot["completed"], 2)
            self.assertEqual(snapshot["benchmark"], {"completed": 1, "total": 4})
            self.assertEqual(snapshot["routing"], {"completed": 1, "total": 4})
            self.assertEqual(snapshot["current"][0]["task_id"], "task_1")
            self.assertEqual(snapshot["current"][0]["condition"], "condition_b")
            self.assertEqual(snapshot["current"][0]["source"], "heartbeat")

    def test_scan_prefers_jsonl_counts_when_result_filenames_collide(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            benchmark_dir = root / "predictors" / "model_a" / "shard_00" / "benchmark"
            result_dir = benchmark_dir / "tool_a" / "condition_a"
            result_dir.mkdir(parents=True)
            (result_dir / "shared_prefix.result.json").write_text(
                json.dumps({"task_id": "task_1", "baseline_name": "condition_a", "tool_name": "tool_a"}),
                encoding="utf-8",
            )
            with (benchmark_dir / "prediction_records.jsonl").open("w", encoding="utf-8") as f:
                for task_id in ("task_1", "task_2", "task_3"):
                    f.write(json.dumps({"task_id": task_id, "baseline_name": "condition_a", "tool_name": "tool_a"}) + "\n")

            snapshot = scan_progress(self._plan(root))

            self.assertEqual(snapshot["benchmark"], {"completed": 3, "total": 4})
            self.assertEqual(snapshot["completed"], 3)

    def test_scan_counts_unique_jsonl_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            benchmark_dir = root / "predictors" / "model_a" / "shard_00" / "benchmark"
            benchmark_dir.mkdir(parents=True)
            rows = [
                {"task_id": "task_1", "baseline_name": "condition_a", "tool_name": "tool_a"},
                {"task_id": "task_1", "baseline_name": "condition_a", "tool_name": "tool_a"},
                {"task_id": "task_1", "baseline_name": "condition_b", "tool_name": "tool_a"},
            ]
            with (benchmark_dir / "prediction_records.jsonl").open("w", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row) + "\n")

            snapshot = scan_progress(self._plan(root))

            self.assertEqual(snapshot["benchmark"], {"completed": 2, "total": 4})
            self.assertEqual(snapshot["completed"], 2)

    def test_progress_write_does_not_fail_when_atomic_replace_is_locked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "predictors" / "model_a" / "shard_00" / "benchmark"

            with mock.patch("pathlib.Path.replace", side_effect=PermissionError("locked")):
                write_progress_state(
                    output_dir,
                    phase="benchmark",
                    status="running",
                    task_id="task_1",
                    tool_name="tool_a",
                    condition="condition_a",
                )

            state_path = root / "predictors" / "model_a" / "shard_00" / "progress" / "benchmark_state.json"
            self.assertTrue(state_path.exists())
            self.assertEqual(json.loads(state_path.read_text(encoding="utf-8"))["task_id"], "task_1")

    def test_scan_infers_next_task_when_heartbeat_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result_dir = root / "predictors" / "model_a" / "shard_00" / "benchmark" / "tool_a" / "condition_a"
            result_dir.mkdir(parents=True)
            (result_dir / "task_1.result.json").write_text(json.dumps({"ok": True}), encoding="utf-8")

            snapshot = scan_progress(self._plan(root))

            self.assertEqual(snapshot["current"][0]["phase"], "benchmark")
            self.assertEqual(snapshot["current"][0]["status"], "next")
            self.assertEqual(snapshot["current"][0]["task_id"], "task_1")
            self.assertEqual(snapshot["current"][0]["condition"], "condition_b")
            self.assertEqual(snapshot["current"][0]["source"], "inferred")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import yaml

from reliaskill.data_audit import audit_dataset_integrity


class DataAuditTests(unittest.TestCase):
    def test_acceptance_dataset_integrity_passes_blocking_checks(self) -> None:
        report = audit_dataset_integrity("configs/experiments/emnlp_acceptance.yaml")

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["selected_tool_count"], 290)
        self.assertEqual(report["selected_task_count"], 1450)

    def test_detects_duplicate_tools_task_ids_leakage_and_coverage_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tools = root / "tools.jsonl"
            test = root / "test.jsonl"
            dev = root / "dev.jsonl"
            config = root / "config.yaml"
            self._write_jsonl(
                tools,
                [
                    self._tool("demo_tool"),
                    self._tool("demo_tool"),
                ],
            )
            self._write_jsonl(
                test,
                [
                    self._task("dup", "demo_tool", "Shared request", should_trigger=True),
                    self._task("dup", "demo_tool", "Another request", should_trigger=True),
                ],
            )
            self._write_jsonl(dev, [self._task("dev1", "demo_tool", "Shared request", should_trigger=False)])
            config.write_text(
                yaml.safe_dump(
                    {
                        "tools_path": str(tools),
                        "tasks_path": str(test),
                        "controls": {"positives_per_tool_total": 1, "negatives_per_tool_total": 1},
                        "shared_skill_packages": {"dev_controls_path": str(dev)},
                    }
                ),
                encoding="utf-8",
            )

            report = audit_dataset_integrity(config)

            self.assertFalse(report["ok"])
            failed = {check["id"] for check in report["checks"] if check["severity"] == "fail" and not check["passed"]}
            self.assertIn("duplicate_raw_tool_names", failed)
            self.assertIn("duplicate_test_task_ids", failed)
            self.assertIn("dev_test_request_leakage", failed)
            self.assertIn("test_control_coverage", failed)

    @staticmethod
    def _tool(name: str) -> dict:
        return {
            "name": name,
            "description": "Demo tool.",
            "inputSchema": {"type": "object", "properties": {"value": {"type": "string"}}, "required": ["value"]},
        }

    @staticmethod
    def _task(task_id: str, tool_name: str, request: str, *, should_trigger: bool) -> dict:
        return {
            "task_id": task_id,
            "tool_name": tool_name,
            "user_request": request,
            "expected_arguments": {"value": "x"} if should_trigger else {},
            "expected_argument_candidates": [{"value": "x"}] if should_trigger else [{}],
            "should_trigger": should_trigger,
        }

    @staticmethod
    def _write_jsonl(path: Path, rows: list[dict]) -> None:
        with path.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")


if __name__ == "__main__":
    unittest.main()

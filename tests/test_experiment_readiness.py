from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

import yaml

from reliaskill.experiment_readiness import (
    REQUIRED_CONFIG_CONDITIONS,
    audit_experiment_readiness,
    build_readiness_markdown,
)


class ExperimentReadinessTests(unittest.TestCase):
    def test_audit_passes_when_core_evidence_is_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config = root / "experiment.yaml"
            tables = root / "tables"
            run = root / "run"
            tables.mkdir()
            run.mkdir()
            config.write_text(
                yaml.safe_dump(
                    {
                        "conditions": list(REQUIRED_CONFIG_CONDITIONS),
                        "controls": {"negatives_per_tool_total": 2},
                        "live_execution": {"enabled": True},
                    }
                ),
                encoding="utf-8",
            )
            self._write_csv(
                tables / "main_results.csv",
                ["baseline_name", "num_examples", "joint_exact_match"],
                [
                    {"baseline_name": "raw_mcp", "num_examples": "3", "joint_exact_match": "0.1"},
                    {"baseline_name": "generated_skill_base", "num_examples": "3", "joint_exact_match": "0.2"},
                    {"baseline_name": "gated_skill", "num_examples": "3", "joint_exact_match": "0.3"},
                    {"baseline_name": "reliaskill_v1", "num_examples": "3", "joint_exact_match": "0.4"},
                ],
            )
            self._write_csv(
                tables / "harm_utility.csv",
                ["baseline_name", "negative_controls"],
                [{"baseline_name": "gated_skill", "negative_controls": "3"}],
            )
            self._write_csv(
                tables / "stat_tests.csv",
                ["baseline_a", "baseline_b", "paired_examples"],
                [
                    {"baseline_a": "raw_mcp", "baseline_b": "generated_skill_base", "paired_examples": "3"},
                    {"baseline_a": "raw_mcp", "baseline_b": "gated_skill", "paired_examples": "3"},
                    {"baseline_a": "raw_mcp", "baseline_b": "reliaskill_v1", "paired_examples": "3"},
                    {"baseline_a": "generated_skill_base", "baseline_b": "gated_skill", "paired_examples": "3"},
                    {"baseline_a": "generated_skill_base", "baseline_b": "reliaskill_v1", "paired_examples": "3"},
                ],
            )
            for name in [
                "slice_analysis_by_domain.csv",
                "slice_analysis_by_tool_complexity.csv",
                "slice_analysis_by_negative_category.csv",
            ]:
                self._write_csv(tables / name, ["slice_value", "suppressed"], [{"slice_value": "x", "suppressed": "False"}])
            (run / "live_exec_results.jsonl").write_text(json.dumps({"live_task_id": "t1", "live_joint_success": True}) + "\n", encoding="utf-8")

            report = audit_experiment_readiness(config_path=config, tables_dir=tables, run_dir=run, min_examples=3)

            self.assertTrue(report["ok"], build_readiness_markdown(report))

    def test_audit_flags_smoke_tables_and_missing_required_baselines(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config = root / "experiment.yaml"
            tables = root / "tables"
            tables.mkdir()
            config.write_text(
                yaml.safe_dump({"conditions": ["raw_mcp"], "controls": {"negatives_per_tool_total": 0}}),
                encoding="utf-8",
            )
            self._write_csv(
                tables / "main_results.csv",
                ["baseline_name", "num_examples"],
                [{"baseline_name": "raw_mcp", "num_examples": "30"}],
            )

            report = audit_experiment_readiness(config_path=config, tables_dir=tables, min_examples=100)

            self.assertFalse(report["ok"])
            failed_ids = {check["id"] for check in report["checks"] if not check["passed"] and check["severity"] == "fail"}
            self.assertIn("required_config_conditions", failed_ids)
            self.assertIn("result_condition_sample_sizes", failed_ids)
            self.assertIn("harm_table_negative_controls", failed_ids)

    def test_audit_rejects_preflight_only_run_without_predictions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            run = root / "run"
            tables = root / "tables"
            run.mkdir()
            tables.mkdir()
            (run / "model_comparison_manifest.json").write_text('{"preflight": true, "runs": []}', encoding="utf-8")

            report = audit_experiment_readiness(tables_dir=tables, run_dir=run, min_examples=1)

            failed_ids = {check["id"] for check in report["checks"] if not check["passed"] and check["severity"] == "fail"}
            self.assertIn("not_preflight_only", failed_ids)

    @staticmethod
    def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()

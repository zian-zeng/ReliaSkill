from __future__ import annotations

import json
import unittest
from pathlib import Path

from autoskill.experiment import run_full_experiment
from autoskill.logging_utils import build_run_manifest, stable_hash
from autoskill.reliability import run_reliability_pipeline


class AuditLoggingTests(unittest.TestCase):
    def test_manifest_contains_required_audit_fields(self) -> None:
        config = {"tools_path": "tools.json", "seed": 42, "predictor": {"type": "heuristic"}}
        manifest = build_run_manifest(
            run_type="unit",
            output_root="outputs/audit_unit",
            config=config,
            seed=42,
            predictor_config=config["predictor"],
        )

        self.assertIn("run_id", manifest)
        self.assertIn("git_commit_hash", manifest)
        self.assertEqual(manifest["config_hash"], stable_hash(config))
        self.assertEqual(manifest["seed"], 42)
        self.assertEqual(manifest["model_name"]["predictor"], "heuristic")
        self.assertIn("hardware", manifest)

    def test_reliability_pipeline_writes_manifest_and_audit_jsonl(self) -> None:
        out = Path("outputs/test_audit_reliability")
        manifest = run_reliability_pipeline(
            tools_path="data/raw/public_mcp_filesystem_subset.json",
            behavior_path="data/eval/public_mcp_filesystem_reliability.jsonl",
            output_root=out,
            generator_config={"type": "heuristic"},
            predictor_config={"type": "heuristic"},
            deploy_threshold=85.0,
        )

        manifest_path = out / "manifest.json"
        audit_path = out / "audit_records.jsonl"
        self.assertTrue(manifest_path.exists())
        self.assertTrue(audit_path.exists())
        persisted = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(persisted["run_id"], manifest["run_id"])
        self.assertEqual(persisted["config_hash"], manifest["config_hash"])

        records = _load_jsonl(audit_path)
        self.assertTrue(any(record["event_type"] == "behavior_prediction" for record in records))
        sample = next(record for record in records if record["event_type"] == "behavior_prediction")
        for field in [
            "run_id",
            "git_commit_hash",
            "config_hash",
            "seed",
            "model_name",
            "quantization",
            "hardware",
            "prompt_template",
            "raw_prompt",
            "raw_model_output",
            "parsed_prediction",
            "validation_report",
            "behavior_report",
            "repair_report",
            "reliability_score",
        ]:
            self.assertIn(field, sample)

    def test_full_experiment_writes_manifest_and_prediction_audit(self) -> None:
        out = Path("outputs/test_audit_experiment")
        manifest = run_full_experiment(
            tools_path="data/raw/public_mcp_filesystem_subset.json",
            tasks_path="data/eval/public_mcp_filesystem_benchmark.jsonl",
            output_root=out,
            generator_config={"type": "heuristic"},
            predictor_config={"type": "heuristic"},
        )

        self.assertTrue((out / "manifest.json").exists())
        self.assertTrue((out / "audit_records.jsonl").exists())
        records = _load_jsonl(out / "audit_records.jsonl")
        self.assertTrue(any(record["event_type"] == "skill_generation" for record in records))
        self.assertTrue(any(record["event_type"] == "prediction" for record in records))
        prediction = next(record for record in records if record["event_type"] == "prediction")
        self.assertEqual(prediction["run_id"], manifest["run_id"])
        self.assertIn("raw_prompt", prediction)
        self.assertIn("raw_model_output", prediction)
        self.assertIn("parsed_prediction", prediction)


def _load_jsonl(path: Path):
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

import yaml

from reliaskill.analysis.preregistration import (
    audit_preregistered_success,
    build_preregistration_markdown,
    write_preregistration_report,
)


class PreregistrationAuditTests(unittest.TestCase):
    def test_preregistered_success_audit_passes_locked_criteria(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tables = root / "tables"
            tables.mkdir()
            prereg = root / "prereg.yaml"
            prereg.write_text(
                yaml.safe_dump(
                    {
                        "protocol_lock": {
                            "criteria_locked_before_run": True,
                            "test_set_used_for_method_changes": False,
                        },
                        "primary_success_criteria": [
                            {
                                "baseline": "raw_docs_full",
                                "method": "reliaskill_v1",
                                "metric": "joint_exact_match",
                                "min_delta": 0.01,
                                "min_examples": 3,
                                "also_require_routing": True,
                            }
                        ],
                        "component_ablation_criteria": [
                            {
                                "baseline": "reliaskill_v1_no_doc_grounding",
                                "method": "reliaskill_v1",
                                "metric": "joint_exact_match",
                                "min_delta": 0.0,
                                "min_examples": 3,
                            }
                        ],
                        "runtime_trace_criteria": [
                            {"condition": "reliaskill_v1", "metric": "verifier_action_rate", "min": 0.0, "max": 1.0}
                        ],
                        "harm_safety_criteria": [
                            {
                                "baseline": "raw_docs_full",
                                "method": "reliaskill_v1",
                                "metric": "harmful_skill_injection_rate",
                                "max_increase": 0.0,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            fields = ["baseline_name", "num_examples", "joint_exact_match", "verifier_action_rate"]
            rows = [
                {"baseline_name": "raw_docs_full", "num_examples": "3", "joint_exact_match": "0.40", "verifier_action_rate": "0"},
                {
                    "baseline_name": "reliaskill_v1_no_doc_grounding",
                    "num_examples": "3",
                    "joint_exact_match": "0.41",
                    "verifier_action_rate": "0",
                },
                {"baseline_name": "reliaskill_v1", "num_examples": "3", "joint_exact_match": "0.42", "verifier_action_rate": "0.33"},
            ]
            _write_csv(tables / "main_results.csv", fields, rows)
            _write_csv(tables / "routing_results.csv", fields, rows)
            _write_csv(
                tables / "stat_tests.csv",
                ["test", "baseline_a", "baseline_b", "metric", "paired_examples", "observed_delta", "p_value"],
                [
                    {
                        "test": "approx_randomization",
                        "baseline_a": "raw_docs_full",
                        "baseline_b": "reliaskill_v1",
                        "metric": "joint_exact_match",
                        "paired_examples": "3",
                        "observed_delta": "-0.02",
                        "p_value": "0.2",
                    }
                ],
            )
            _write_csv(tables / "routing_stat_tests.csv", ["test", "baseline_a", "baseline_b", "metric", "paired_examples", "p_value"], [])
            _write_csv(
                tables / "harm_utility.csv",
                ["baseline_name", "harmful_skill_injection_rate"],
                [
                    {"baseline_name": "raw_docs_full", "harmful_skill_injection_rate": "0.0"},
                    {"baseline_name": "reliaskill_v1", "harmful_skill_injection_rate": "0.0"},
                ],
            )

            report = audit_preregistered_success(preregistration_path=prereg, tables_dir=tables)
            paths = write_preregistration_report(
                report,
                output_json=root / "reports" / "audit.json",
                output_md=root / "reports" / "audit.md",
            )

            self.assertTrue(report["ok"], build_preregistration_markdown(report))
            self.assertTrue(Path(paths["json"]).exists())
            self.assertTrue(Path(paths["markdown"]).exists())

    def test_preregistered_success_audit_rejects_unlocked_protocol(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tables = root / "tables"
            tables.mkdir()
            prereg = root / "prereg.yaml"
            prereg.write_text(
                yaml.safe_dump({"protocol_lock": {"criteria_locked_before_run": False, "test_set_used_for_method_changes": True}}),
                encoding="utf-8",
            )

            report = audit_preregistered_success(preregistration_path=prereg, tables_dir=tables)

            failed_ids = {check["id"] for check in report["checks"] if not check["passed"]}
            self.assertIn("criteria_locked_before_run", failed_ids)
            self.assertIn("no_test_set_authoring", failed_ids)


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


if __name__ == "__main__":
    unittest.main()

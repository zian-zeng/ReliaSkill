from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from reliaskill.analysis.residuals import analyze_residuals, write_residual_analysis


class ResidualAnalysisTests(unittest.TestCase):
    def test_residual_analysis_categorizes_paired_disagreements(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run = Path(tmpdir) / "run"
            _write_jsonl(
                run / "prediction_records.jsonl",
                [
                    {
                        "model_slug": "m",
                        "record_type": "benchmark",
                        "task_id": "baseline-win",
                        "baseline_name": "raw_docs_full",
                        "joint_exact_match": True,
                        "expected_tool_name": "search_docs",
                        "selected_tool_name": "search_docs",
                    },
                    {
                        "model_slug": "m",
                        "record_type": "benchmark",
                        "task_id": "baseline-win",
                        "baseline_name": "reliaskill_v1",
                        "joint_exact_match": False,
                        "argument_exact_match": False,
                        "expected_tool_name": "search_docs",
                        "selected_tool_name": "search_docs",
                        "should_trigger": True,
                        "triggered": True,
                        "prediction_metadata": {
                            "reliaskill_v1_runtime_verifier": {
                                "issues": ["missing_required:query"],
                                "contract_failure_report_after": {"reason": "missing_required_arguments"},
                            }
                        },
                    },
                    {
                        "model_slug": "m",
                        "record_type": "benchmark",
                        "task_id": "method-win",
                        "baseline_name": "raw_docs_full",
                        "joint_exact_match": False,
                        "argument_exact_match": False,
                        "expected_tool_name": "search_docs",
                        "selected_tool_name": "search_docs",
                        "should_trigger": True,
                        "triggered": True,
                        "should_call": True,
                    },
                    {
                        "model_slug": "m",
                        "record_type": "benchmark",
                        "task_id": "method-win",
                        "baseline_name": "reliaskill_v1",
                        "joint_exact_match": True,
                        "expected_tool_name": "search_docs",
                        "selected_tool_name": "search_docs",
                    },
                ],
            )

            report = analyze_residuals(run, include_routing=False)
            paths = write_residual_analysis(
                report,
                output_csv=Path(tmpdir) / "tables" / "residual.csv",
                output_md=Path(tmpdir) / "reports" / "residual.md",
                output_json=Path(tmpdir) / "reports" / "residual.json",
            )

            self.assertEqual(report["paired_disagreements"], 2)
            self.assertEqual(report["baseline_only_correct"], 1)
            self.assertEqual(report["method_only_correct"], 1)
            categories = {(row["outcome"], row["error_category"]) for row in report["summary"]}
            self.assertIn(("baseline_win", "missing_required_grounding"), categories)
            self.assertIn(("method_win", "argument_mismatch"), categories)
            self.assertTrue(Path(paths["csv"]).exists())
            self.assertTrue(Path(paths["markdown"]).exists())
            self.assertTrue(Path(paths["json"]).exists())


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


if __name__ == "__main__":
    unittest.main()

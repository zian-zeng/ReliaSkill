from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from reliaskill.analysis.slices import analyze_result_slices, write_slice_analysis_outputs


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


class SliceAnalysisTests(unittest.TestCase):
    def test_slice_analysis_joins_metadata_and_compares_conditions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            run_dir = root / "run"
            tools_path = root / "tools.jsonl"
            controls_path = root / "controls.jsonl"
            routing_path = root / "routing.jsonl"
            compactness_path = root / "compactness.jsonl"

            _write_jsonl(
                tools_path,
                [
                    {
                        "tool_name": "calendar_create_event",
                        "domain": "calendar/time",
                        "source_metadata": {"source_type": "converted_bfcl"},
                        "schema_complexity": {
                            "num_required_arguments": 3,
                            "num_arguments": 5,
                            "num_enum_fields": 1,
                            "has_nested_object": True,
                            "side_effect_type": "write",
                        },
                    }
                ],
            )
            _write_jsonl(
                controls_path,
                [
                    {
                        "control_id": "ctrl-1",
                        "difficulty": "hard",
                        "negative_category": "near_miss_intent",
                        "should_trigger": True,
                    }
                ],
            )
            _write_jsonl(
                routing_path,
                [
                    {
                        "id": "route-1",
                        "source_control_id": "ctrl-1",
                        "distractor_level": "hard",
                        "candidate_set_size": 8,
                    }
                ],
            )
            _write_jsonl(
                compactness_path,
                [{"tool_name": "calendar_create_event", "condition": "naive_skill", "skill_token_count": 240}],
            )
            _write_jsonl(
                run_dir / "benchmark" / "prediction_records.jsonl",
                [
                    {
                        "task_id": "ctrl-1",
                        "tool_name": "calendar_create_event",
                        "condition": "raw_mcp",
                        "predicted_arguments": {"title": "demo", "start": "9", "attendees": []},
                        "expected_arguments": {"title": "demo", "start": "10", "attendees": []},
                        "tool_selection_correct": True,
                    },
                    {
                        "task_id": "ctrl-1",
                        "tool_name": "calendar_create_event",
                        "condition": "naive_skill",
                        "predicted_arguments": {"title": "demo", "start": "10", "attendees": []},
                        "expected_arguments": {"title": "demo", "start": "10", "attendees": []},
                        "tool_selection_correct": True,
                        "prediction_latency_ms": 12,
                    },
                ],
            )

            analysis = analyze_result_slices(
                run_dir=run_dir,
                tools_path=tools_path,
                controls_paths=[controls_path],
                routing_path=routing_path,
                compactness_path=compactness_path,
                min_slice_size=1,
            )

            domain_rows = {
                row["condition"]: row
                for row in analysis["tables"]["domain"]
                if row["slice_value"] == "calendar/time"
            }
            self.assertEqual(domain_rows["raw_mcp"]["joint_exact_match"], 0.0)
            self.assertEqual(domain_rows["naive_skill"]["joint_exact_match"], 1.0)
            self.assertEqual(domain_rows["naive_skill"]["mean_latency"], 12.0)

            hard_rows = [
                row
                for row in analysis["comparisons"]["distractor_level"]
                if row["slice_value"] == "hard" and row["comparison"] == "raw_mcp_vs_naive_skill" and row["metric"] == "joint_exact_match"
            ]
            self.assertEqual(hard_rows[0]["paired_examples"], 1)
            self.assertEqual(hard_rows[0]["delta_b_minus_a"], 1.0)

    def test_slice_cli_writes_requested_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            run_dir = root / "run"
            tools_path = root / "tools.jsonl"
            out_dir = root / "tables"
            report_path = root / "reports" / "summary.md"
            _write_jsonl(
                tools_path,
                [
                    {
                        "tool_name": "search_docs",
                        "domain": "search/retrieval",
                        "source_metadata": {"source_type": "synthetic"},
                        "schema_complexity": {"num_required_arguments": 1},
                    }
                ],
            )
            _write_jsonl(
                run_dir / "benchmark" / "prediction_records.jsonl",
                [
                    {
                        "task_id": "task-1",
                        "tool_name": "search_docs",
                        "baseline_name": "raw_mcp",
                        "predicted_arguments": {"query": "alpha"},
                        "expected_arguments": {"query": "alpha"},
                    }
                ],
            )

            subprocess.run(
                [
                    sys.executable,
                    "scripts/analyze_result_slices.py",
                    "--run",
                    str(run_dir),
                    "--tools",
                    str(tools_path),
                    "--controls",
                    str(root / "missing_controls.jsonl"),
                    "--routing",
                    str(root / "missing_routing.jsonl"),
                    "--compactness",
                    str(root / "missing_compactness.jsonl"),
                    "--out",
                    str(out_dir),
                    "--report",
                    str(report_path),
                    "--min-slice-size",
                    "1",
                ],
                cwd=Path.cwd(),
                check=True,
            )

            for name in [
                "slice_analysis_by_domain.csv",
                "slice_analysis_by_difficulty.csv",
                "slice_analysis_by_negative_category.csv",
                "slice_analysis_by_distractor_level.csv",
                "slice_analysis_by_tool_complexity.csv",
            ]:
                self.assertTrue((out_dir / name).exists())
            self.assertTrue(report_path.exists())
            with (out_dir / "slice_analysis_by_domain.csv").open("r", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertTrue(any(row["slice_value"] == "search/retrieval" for row in rows))

    def test_write_outputs_accepts_empty_analysis(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            analysis = {
                "num_records": 0,
                "min_slice_size": 5,
                "tables": {},
                "comparisons": {},
            }

            paths = write_slice_analysis_outputs(
                analysis,
                output_dir=root / "tables",
                report_path=root / "reports" / "summary.md",
            )

            self.assertTrue(paths["domain"].exists())
            self.assertTrue(paths["summary"].exists())


if __name__ == "__main__":
    unittest.main()

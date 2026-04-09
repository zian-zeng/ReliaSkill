from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from autoskill.benchmark import load_benchmark_tasks
from autoskill.analysis import classify_score_error, summarize_error_taxonomy, summarize_method_wins
from autoskill.config import load_json_config, merge_experiment_config, validate_experiment_config
from autoskill.conversion import canonicalize_mcp_tool_records, convert_benchmark_file_to_canonical_records, load_json_or_jsonl
from autoskill.json_output import parse_json_object_output
from autoskill.reporting import (
    build_benchmark_by_split_csv,
    build_benchmark_by_tool_csv,
    build_error_taxonomy_csv,
    build_method_wins_csv,
    build_package_by_tool_csv,
    build_pairwise_comparison_csv,
    build_results_csv,
    build_results_markdown,
)
from autoskill.generator import SkillGenerator
from autoskill.experiment import run_full_experiment_from_config
from autoskill.packaging import write_skill_package
from autoskill.parser import parse_mcp_tool
from autoskill.backends import build_backend_from_config
from autoskill.predictor import HeuristicPredictorBackend, build_predictor_from_config
from autoskill.raw_mcp import build_raw_mcp_skill
from autoskill.schema_only import build_schema_only_skill
from autoskill.sweep import aggregate_experiment_manifests, run_experiment_sweep
from autoskill.task_eval import (
    score_prediction,
    summarize_pairwise_comparisons,
    summarize_task_scores_by_split,
)
from autoskill.eval_types import EvalPrediction, EvalTask
from autoskill.validator import validate_skill


FIXTURE_PATH = Path("data/raw/sample_tools.json")
PUBLIC_FIXTURE_PATH = Path("data/raw/public_mcp_filesystem_subset.json")


def _load_tools():
    with FIXTURE_PATH.open("r", encoding="utf-8") as f:
        raw_tools = json.load(f)
    return [parse_mcp_tool(tool, source_pointer=f"{FIXTURE_PATH}#{idx}") for idx, tool in enumerate(raw_tools)]


def _load_public_tools():
    with PUBLIC_FIXTURE_PATH.open("r", encoding="utf-8") as f:
        raw_tools = json.load(f)
    return [parse_mcp_tool(tool, source_pointer=f"{PUBLIC_FIXTURE_PATH}#{idx}") for idx, tool in enumerate(raw_tools)]


class ParserValidatorTests(unittest.TestCase):
    def test_parser_handles_nested_and_nullable_fields(self) -> None:
        tools = {tool.tool_name: tool for tool in _load_tools()}
        event_tool = tools["create_event"]

        self.assertEqual(event_tool.server_name, "calendar_server")
        self.assertIn("Schema forbids unknown top-level arguments.", event_tool.usage_warnings)

        notes_arg = next(arg for arg in event_tool.arguments if arg.name == "notes")
        self.assertEqual(notes_arg.type, "string")
        self.assertTrue(notes_arg.nullable)

        time_range_arg = next(arg for arg in event_tool.arguments if arg.name == "time_range")
        self.assertEqual(time_range_arg.type, "object")
        self.assertEqual(time_range_arg.required_properties, ["start", "end"])
        self.assertIn("start", (time_range_arg.properties or {}))
        self.assertIn("end", (time_range_arg.properties or {}))

        attendees_arg = next(arg for arg in event_tool.arguments if arg.name == "attendees")
        self.assertEqual(attendees_arg.type, "array")
        self.assertEqual(attendees_arg.items_type, "string")

    def test_schema_only_skill_is_valid_for_nested_tool(self) -> None:
        tools = {tool.tool_name: tool for tool in _load_tools()}
        event_tool = tools["create_event"]
        skill = build_schema_only_skill(event_tool)
        report = validate_skill(event_tool, skill)

        self.assertTrue(report.valid, msg=[issue.message for issue in report.issues])
        self.assertIn("time_range", skill.argument_template)
        self.assertEqual(skill.argument_template["visibility"], "team")
        self.assertIsInstance(skill.argument_template["attendees"], list)

    def test_validator_flags_nested_hallucinated_field(self) -> None:
        tools = {tool.tool_name: tool for tool in _load_tools()}
        event_tool = tools["create_event"]
        skill = SkillGenerator().generate(event_tool)
        skill.examples.append(
            {
                "scenario": "Broken nested example",
                "arguments": {
                    "title": "Team Sync",
                    "time_range": {
                        "start": "2026-01-01T09:00:00Z",
                        "end": "2026-01-01T10:00:00Z",
                        "timezone": "America/New_York",
                    },
                },
            }
        )

        report = validate_skill(event_tool, skill)
        self.assertFalse(report.valid)
        self.assertTrue(any(issue.code == "hallucinated_argument" for issue in report.issues))

    def test_benchmark_loader_normalizes_bfcl_style_fields(self) -> None:
        tasks = load_benchmark_tasks("data/eval/sample_bfcl_style.json")
        self.assertEqual(len(tasks), 3)
        self.assertEqual(tasks[0].tool_name, "get_weather")
        self.assertEqual(tasks[1].expected_arguments["top_k"], 3)
        self.assertEqual(tasks[2].expected_arguments["top_k"], 5)

    def test_benchmark_loader_supports_jsonl(self) -> None:
        tasks = load_benchmark_tasks("data/eval/sample_bfcl_style.jsonl")
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].tool_name, "get_weather")
        self.assertEqual(tasks[1].expected_arguments["top_k"], 3)

    def test_benchmark_loader_supports_raw_bfcl_possible_answers(self) -> None:
        tasks = load_benchmark_tasks("data/eval/sample_bfcl_raw_possible_answer.jsonl")
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].tool_name, "get_weather")
        self.assertGreaterEqual(len(tasks[0].expected_argument_candidates), 2)
        self.assertEqual(tasks[1].tool_name, "search_docs")

    def test_public_filesystem_benchmark_is_expanded(self) -> None:
        tasks = load_benchmark_tasks("data/eval/public_mcp_filesystem_benchmark.jsonl")
        task_ids = {task.task_id for task in tasks}
        self.assertGreaterEqual(len(tasks), 14)
        self.assertIn("fs_search_markdown_semantic", task_ids)
        self.assertIn("fs_read_top_synonym", task_ids)
        self.assertEqual(tasks[0].split, "dev")
        self.assertIn("head", tasks[0].tags)

    def test_score_prediction_matches_best_gold_candidate(self) -> None:
        tools = {tool.tool_name: tool for tool in _load_tools()}
        weather_tool = tools["get_weather"]
        tasks = load_benchmark_tasks("data/eval/sample_bfcl_raw_possible_answer.jsonl")
        task = tasks[0]
        prediction = EvalPrediction(
            task_id=task.task_id,
            tool_name=task.tool_name,
            baseline_name="raw_mcp",
            predicted_arguments={"city": "New York", "unit": "F"},
        )
        score = score_prediction(task, weather_tool, prediction)

        self.assertTrue(score["exact_match"])
        self.assertEqual(score["num_gold_candidates"], len(task.expected_argument_candidates))

    def test_autoskill_heuristic_uses_semantic_search_pattern_fallback(self) -> None:
        tools = {tool.tool_name: tool for tool in _load_public_tools()}
        search_tool = tools["search_files"]
        task = EvalTask(
            task_id="semantic_search",
            tool_name="search_files",
            user_request="Find markdown files under docs.",
            expected_arguments={"path": "docs", "pattern": "**/*.md"},
        )
        backend = HeuristicPredictorBackend()

        raw_prediction = backend.predict(search_tool, build_raw_mcp_skill(search_tool), task)
        schema_prediction = backend.predict(search_tool, build_schema_only_skill(search_tool), task)
        autoskill_prediction = backend.predict(search_tool, SkillGenerator().generate(search_tool), task)

        self.assertNotEqual(raw_prediction.predicted_arguments.get("pattern"), "**/*.md")
        self.assertNotEqual(schema_prediction.predicted_arguments.get("pattern"), "**/*.md")
        self.assertEqual(autoskill_prediction.predicted_arguments.get("pattern"), "**/*.md")

    def test_autoskill_generated_skill_contains_semantic_hints_and_trace(self) -> None:
        tools = {tool.tool_name: tool for tool in _load_public_tools()}
        search_tool = tools["search_files"]
        skill = SkillGenerator().generate(search_tool)

        self.assertIn("pattern", skill.semantic_hints)
        self.assertTrue(any("selected_label" in entry for entry in skill.method_trace))

    def test_conversion_to_canonical_benchmark_records(self) -> None:
        records = convert_benchmark_file_to_canonical_records("data/eval/sample_bfcl_raw_possible_answer.jsonl")
        self.assertEqual(len(records), 2)
        self.assertIn("expected_argument_candidates", records[0])
        self.assertGreaterEqual(len(records[0]["expected_argument_candidates"]), 2)

    def test_mcp_tool_import_canonicalizes_wrapped_export(self) -> None:
        raw_records = load_json_or_jsonl("data/raw/sample_mcp_export.json")
        canonical = canonicalize_mcp_tool_records(raw_records)
        self.assertEqual(len(canonical), 2)
        self.assertEqual(canonical[0]["server_name"], "exported_filesystem")
        self.assertIn("inputSchema", canonical[0])

    def test_cli_conversion_scripts_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            benchmark_out = Path(tmpdir) / "benchmark.jsonl"
            tools_out = Path(tmpdir) / "tools.json"

            subprocess.run(
                [
                    sys.executable,
                    "scripts/convert_bfcl_to_benchmark.py",
                    "--in",
                    "data/eval/sample_bfcl_raw_possible_answer.jsonl",
                    "--out",
                    str(benchmark_out),
                ],
                check=True,
                cwd=Path.cwd(),
            )
            subprocess.run(
                [
                    sys.executable,
                    "scripts/import_mcp_tools.py",
                    "--in",
                    "data/raw/sample_mcp_export.json",
                    "--out",
                    str(tools_out),
                ],
                check=True,
                cwd=Path.cwd(),
            )

            self.assertTrue(benchmark_out.exists())
            self.assertTrue(tools_out.exists())

    def test_config_loading_and_merge(self) -> None:
        config = load_json_config("configs/experiment.openai_compatible.sample.json")
        merged = merge_experiment_config(config, {"output_root": "outputs/test_override"})
        self.assertEqual(config["generator"]["type"], "openai_compatible")
        self.assertEqual(merged["output_root"], "outputs/test_override")

    def test_validate_experiment_config_for_heuristic_run(self) -> None:
        report = validate_experiment_config(
            {
                "tools_path": "data/raw/public_mcp_filesystem_subset.json",
                "tasks_path": "data/eval/public_mcp_filesystem_benchmark.jsonl",
                "output_root": "outputs/test_validate",
                "generator": {"type": "heuristic"},
                "predictor": {"type": "heuristic"},
            }
        )
        self.assertTrue(report["valid"])
        self.assertEqual(report["backend_preflight"]["generator"]["backend_type"], "heuristic")

    def test_validate_experiment_config_rejects_missing_paths(self) -> None:
        report = validate_experiment_config(
            {
                "tools_path": "data/raw/does_not_exist.json",
                "tasks_path": "data/eval/public_mcp_filesystem_benchmark.jsonl",
                "output_root": "outputs/test_validate",
                "generator": {"type": "heuristic"},
                "predictor": {"type": "heuristic"},
            }
        )
        self.assertFalse(report["valid"])
        self.assertTrue(any("tools_path does not exist" in error for error in report["errors"]))

    def test_predictor_config_builds_heuristic_backend(self) -> None:
        backend = build_predictor_from_config({"type": "heuristic"})
        self.assertEqual(backend.backend_name, "heuristic")

    def test_generator_config_supports_heuristic_ablation_mode(self) -> None:
        backend = build_backend_from_config({"type": "heuristic", "ablation_mode": "semantic_dense"})
        self.assertEqual(backend.backend_name, "heuristic")
        self.assertEqual(backend.ablation_mode, "semantic_dense")

    def test_backend_config_builds_local_hf_backend_without_loading_model(self) -> None:
        backend = build_backend_from_config(
            {
                "type": "local_hf",
                "model_name_or_path": "Qwen/Qwen2.5-7B-Instruct",
                "device_map": "auto",
                "load_in_4bit": True,
                "generation_kwargs": {"repetition_penalty": 1.05},
            }
        )
        predictor = build_predictor_from_config(
            {
                "type": "local_hf",
                "model_name_or_path": "Qwen/Qwen2.5-7B-Instruct",
                "trust_remote_code": True,
                "generation_kwargs": {"repetition_penalty": 1.02},
            }
        )
        self.assertEqual(backend.backend_name, "local_hf")
        self.assertEqual(predictor.backend_name, "local_hf")
        self.assertEqual(backend.runner.device_map, "auto")
        self.assertTrue(backend.runner.load_in_4bit)
        self.assertTrue(predictor.runner.trust_remote_code)
        self.assertEqual(backend.runner.generation_kwargs["repetition_penalty"], 1.05)
        self.assertEqual(predictor.runner.generation_kwargs["repetition_penalty"], 1.02)

    def test_local_hf_runner_rejects_double_quantization_flags(self) -> None:
        with self.assertRaises(ValueError):
            build_backend_from_config(
                {
                    "type": "local_hf",
                    "model_name_or_path": "Qwen/Qwen2.5-7B-Instruct",
                    "load_in_4bit": True,
                    "load_in_8bit": True,
                }
            )

    def test_json_output_parser_handles_code_fences_and_extra_text(self) -> None:
        parsed = parse_json_object_output(
            "Here is the result:\n```json\n{\"arguments\": {\"path\": \"src/app.py\"}}\n```\nDone."
        )
        self.assertEqual(parsed["arguments"]["path"], "src/app.py")

    def test_run_full_experiment_from_config_with_heuristic_backends(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "experiment.json"
            config_path.write_text(
                json.dumps(
                    {
                        "tools_path": "data/raw/public_mcp_filesystem_subset.json",
                        "tasks_path": "data/eval/public_mcp_filesystem_benchmark.jsonl",
                        "output_root": str(Path(tmpdir) / "experiment_outputs"),
                        "generator": {"type": "heuristic"},
                        "predictor": {"type": "heuristic"},
                    }
                ),
                encoding="utf-8",
            )
            manifest = run_full_experiment_from_config(config_path)
            self.assertEqual(manifest["generator_backend"], "heuristic")
            self.assertEqual(manifest["predictor_backend"], "heuristic")
            self.assertTrue(Path(manifest["tools_path"]).name.endswith(".json"))
            output_root = Path(tmpdir) / "experiment_outputs"
            self.assertTrue((output_root / "reports" / "benchmark_by_tool.csv").exists())
            self.assertTrue((output_root / "reports" / "benchmark_by_split.csv").exists())
            self.assertTrue((output_root / "reports" / "error_taxonomy.csv").exists())
            self.assertTrue((output_root / "reports" / "method_wins.csv").exists())
            self.assertTrue((output_root / "reports" / "pairwise_comparisons.csv").exists())
            self.assertTrue((output_root / "reports" / "package_by_tool.csv").exists())
            self.assertTrue((output_root / "benchmark" / "benchmark_summary_by_tool.json").exists())
            self.assertTrue((output_root / "benchmark" / "benchmark_summary_by_split.json").exists())
            self.assertTrue((output_root / "benchmark" / "error_taxonomy.json").exists())
            self.assertTrue((output_root / "benchmark" / "method_win_analysis.json").exists())
            self.assertTrue((output_root / "benchmark" / "pairwise_comparisons.json").exists())

    def test_sweep_aggregation_and_preflight_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_a = tmpdir_path / "heuristic_a.json"
            config_b = tmpdir_path / "heuristic_b.json"
            config_a.write_text(
                json.dumps(
                    {
                        "tools_path": "data/raw/public_mcp_filesystem_subset.json",
                        "tasks_path": "data/eval/public_mcp_filesystem_benchmark.jsonl",
                        "output_root": str(tmpdir_path / "run_a"),
                        "generator": {"type": "heuristic"},
                        "predictor": {"type": "heuristic"},
                    }
                ),
                encoding="utf-8",
            )
            config_b.write_text(
                json.dumps(
                    {
                        "tools_path": "data/raw/public_mcp_filesystem_subset.json",
                        "tasks_path": "data/eval/public_mcp_filesystem_benchmark.jsonl",
                        "output_root": str(tmpdir_path / "run_b"),
                        "generator": {"type": "heuristic", "ablation_mode": "base_only"},
                        "predictor": {"type": "heuristic"},
                    }
                ),
                encoding="utf-8",
            )
            sweep = run_experiment_sweep([config_a, config_b], output_root=tmpdir_path / "sweep", preflight_only=True)
            self.assertEqual(len(sweep["summary"]["runs"]), 2)
            self.assertTrue((tmpdir_path / "sweep" / "sweep_summary.md").exists())
            self.assertEqual(sweep["summary"]["runs"][0]["status"], "preflight_only")

    def test_aggregate_experiment_manifests(self) -> None:
        summary = aggregate_experiment_manifests(
            [
                {
                    "run_name": "heuristic",
                    "config_path": "configs/a.json",
                    "status": "completed",
                    "preflight": {"valid": True},
                    "manifest": {
                        "generator_backend": "heuristic",
                        "predictor_backend": "heuristic",
                        "benchmark_summary": {
                            "autoskill_base": {"exact_match_rate": 1.0},
                            "raw_mcp": {"exact_match_rate": 0.6},
                            "schema_only": {"exact_match_rate": 0.7},
                        },
                    },
                }
            ]
        )
        self.assertEqual(summary["runs"][0]["autoskill_vs_raw_delta"], 0.4)

    def test_packaging_writes_expected_files(self) -> None:
        tools = _load_tools()
        tool = tools[0]
        skill = SkillGenerator().generate(tool)
        report = validate_skill(tool, skill)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / tool.tool_name / skill.baseline_name
            write_skill_package(out_dir, tool, skill, report)
            self.assertTrue((out_dir / "SKILL.md").exists())
            self.assertTrue((out_dir / "schema.normalized.json").exists())
            self.assertTrue((out_dir / "examples.jsonl").exists())
            self.assertTrue((out_dir / "metadata.json").exists())
            metadata = json.loads((out_dir / "metadata.json").read_text(encoding="utf-8"))
            self.assertIn("semantic_hints", metadata)
            self.assertIn("method_trace", metadata)

    def test_reporting_generates_markdown_and_csv(self) -> None:
        package_summary = {
            "raw_mcp": {"valid_rate": 1.0, "avg_examples": 0.0, "avg_template_fields": 0.0, "avg_semantic_hint_entries": 0.0},
            "schema_only": {"valid_rate": 1.0, "avg_examples": 2.0, "avg_template_fields": 3.0, "avg_semantic_hint_entries": 1.0},
        }
        benchmark_summary = {
            "raw_mcp": {
                "exact_match_rate": 0.5,
                "avg_argument_validity": 0.75,
                "avg_required_argument_recall": 1.0,
                "hallucinated_argument_count": 0,
            },
            "schema_only": {
                "exact_match_rate": 1.0,
                "avg_argument_validity": 1.0,
                "avg_required_argument_recall": 1.0,
                "hallucinated_argument_count": 0,
            },
        }
        package_by_tool = {
            "search_files": {
                "raw_mcp": {"valid_rate": 1.0, "avg_examples": 0.0, "avg_template_fields": 0.0, "avg_semantic_hint_entries": 0.0},
                "schema_only": {"valid_rate": 1.0, "avg_examples": 2.0, "avg_template_fields": 3.0, "avg_semantic_hint_entries": 1.0},
            }
        }
        benchmark_by_tool = {
            "search_files": {
                "raw_mcp": {
                    "num_tasks": 2,
                    "exact_match_rate": 0.5,
                    "exact_match_ci": {"low": 0.0, "high": 1.0},
                    "avg_argument_validity": 0.75,
                    "avg_required_argument_recall": 1.0,
                    "hallucinated_argument_count": 0,
                },
                "schema_only": {
                    "num_tasks": 2,
                    "exact_match_rate": 1.0,
                    "exact_match_ci": {"low": 1.0, "high": 1.0},
                    "avg_argument_validity": 1.0,
                    "avg_required_argument_recall": 1.0,
                    "hallucinated_argument_count": 0,
                },
            }
        }
        benchmark_by_split = {
            "dev": {
                "raw_mcp": {
                    "num_tasks": 2,
                    "exact_match_rate": 0.5,
                    "exact_match_ci": {"low": 0.0, "high": 1.0},
                    "avg_argument_validity": 0.75,
                    "avg_required_argument_recall": 1.0,
                    "hallucinated_argument_count": 0,
                }
            }
        }
        pairwise = {
            "raw_mcp": {
                "anchor_baseline": "autoskill_base",
                "comparison_baseline": "raw_mcp",
                "num_paired_tasks": 2,
                "win_count": 1,
                "tie_count": 1,
                "loss_count": 0,
                "win_rate": 0.5,
                "exact_match_delta": 0.5,
                "exact_match_delta_ci": {"low": 0.0, "high": 1.0},
                "avg_argument_validity_delta": 0.25,
            }
        }
        markdown_text = build_results_markdown(
            package_summary,
            benchmark_summary,
            "tools.json",
            "tasks.jsonl",
            package_summary_by_tool=package_by_tool,
            benchmark_summary_by_tool=benchmark_by_tool,
            benchmark_summary_by_split=benchmark_by_split,
            pairwise_comparisons=pairwise,
        )
        csv_text = build_results_csv(package_summary, benchmark_summary)
        benchmark_by_tool_csv = build_benchmark_by_tool_csv(benchmark_by_tool)
        benchmark_by_split_csv = build_benchmark_by_split_csv(benchmark_by_split)
        pairwise_csv = build_pairwise_comparison_csv(pairwise)
        package_by_tool_csv = build_package_by_tool_csv(package_by_tool)

        self.assertIn("| raw_mcp |", markdown_text)
        self.assertIn("Avg Semantic Hints", markdown_text)
        self.assertIn("tools.json", markdown_text)
        self.assertIn("## Benchmark By Split", markdown_text)
        self.assertIn("## Benchmark By Tool", markdown_text)
        self.assertIn("## Pairwise Comparisons", markdown_text)
        self.assertIn("condition,valid_rate,avg_examples,avg_template_fields,avg_semantic_hint_entries", csv_text)
        self.assertIn("schema_only", csv_text)
        self.assertIn("split,condition,num_tasks", benchmark_by_split_csv)
        self.assertIn("tool_name,condition,num_tasks", benchmark_by_tool_csv)
        self.assertIn("anchor_baseline,comparison_baseline,num_paired_tasks", pairwise_csv)
        self.assertIn("tool_name,condition,total_tools", package_by_tool_csv)

    def test_split_and_pairwise_summaries(self) -> None:
        scores = [
            {
                "task_id": "t1",
                "tool_name": "search_files",
                "baseline_name": "raw_mcp",
                "split": "dev",
                "exact_match": False,
                "argument_validity": 0.5,
                "required_argument_recall": 0.5,
                "hallucinated_args": [],
            },
            {
                "task_id": "t1",
                "tool_name": "search_files",
                "baseline_name": "autoskill_base",
                "split": "dev",
                "exact_match": True,
                "argument_validity": 1.0,
                "required_argument_recall": 1.0,
                "hallucinated_args": [],
            },
            {
                "task_id": "t2",
                "tool_name": "read_text_file",
                "baseline_name": "raw_mcp",
                "split": "test",
                "exact_match": True,
                "argument_validity": 1.0,
                "required_argument_recall": 1.0,
                "hallucinated_args": [],
            },
            {
                "task_id": "t2",
                "tool_name": "read_text_file",
                "baseline_name": "autoskill_base",
                "split": "test",
                "exact_match": True,
                "argument_validity": 1.0,
                "required_argument_recall": 1.0,
                "hallucinated_args": [],
            },
        ]
        by_split = summarize_task_scores_by_split(scores)
        pairwise = summarize_pairwise_comparisons(scores, comparison_baselines=["raw_mcp"])

        self.assertIn("dev", by_split)
        self.assertEqual(by_split["dev"]["autoskill_base"]["num_tasks"], 1)
        self.assertEqual(pairwise["raw_mcp"]["win_count"], 1)
        self.assertEqual(pairwise["raw_mcp"]["tie_count"], 1)

    def test_error_taxonomy_and_method_win_analysis(self) -> None:
        scores = [
            {
                "task_id": "t1",
                "tool_name": "search_files",
                "baseline_name": "raw_mcp",
                "split": "test",
                "tags": ["semantic", "search"],
                "exact_match": False,
                "argument_validity": 0.5,
                "required_argument_recall": 0.5,
                "hallucinated_args": [],
                "predicted_arguments": {"path": "src"},
                "expected_arguments": {"path": "src", "pattern": "**/*.py"},
                "user_request": "Look under src for python files.",
            },
            {
                "task_id": "t1",
                "tool_name": "search_files",
                "baseline_name": "autoskill_base",
                "split": "test",
                "tags": ["semantic", "search"],
                "exact_match": True,
                "argument_validity": 1.0,
                "required_argument_recall": 1.0,
                "hallucinated_args": [],
                "predicted_arguments": {"path": "src", "pattern": "**/*.py"},
                "expected_arguments": {"path": "src", "pattern": "**/*.py"},
                "user_request": "Look under src for python files.",
            },
        ]
        taxonomy = summarize_error_taxonomy(scores)
        wins = summarize_method_wins(scores, comparison_baselines=["raw_mcp"])

        self.assertEqual(classify_score_error(scores[0]), "semantic_missing_required_argument")
        self.assertEqual(taxonomy["raw_mcp"]["error_type_counts"]["semantic_missing_required_argument"], 1)
        self.assertEqual(wins["raw_mcp"]["num_anchor_wins"], 1)
        self.assertEqual(wins["raw_mcp"]["wins_by_tag"]["semantic"], 1)

        taxonomy_csv = build_error_taxonomy_csv(taxonomy)
        wins_csv = build_method_wins_csv(wins)
        self.assertIn("condition,error_type,count,rate", taxonomy_csv)
        self.assertIn("anchor_baseline,comparison_baseline,num_anchor_wins", wins_csv)


if __name__ == "__main__":
    unittest.main()

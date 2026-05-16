from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from autoskill.behavior import load_behavior_cases, run_behavior_tests
from autoskill.benchmark import load_benchmark_tasks
from autoskill.eval_types import EvalPrediction, EvalTask
from autoskill.generator import SkillGenerator
from autoskill.ir import GeneratedSkill
from autoskill.mcptoolbench import convert_mcptoolbench_records
from autoskill.model_compare import run_model_comparison_from_config
from autoskill.packaging import write_skill_package
from autoskill.parser import parse_mcp_tool
from autoskill.quality import score_reliability
from autoskill.reliability import run_reliability_pipeline
from autoskill.repair import classify_failure, repair_behavior_failures, repair_skill
from autoskill.task_eval import score_prediction
from autoskill.validator import validate_skill


def _load_tool(name: str):
    raw_tools = json.loads(Path("data/raw/sample_tools.json").read_text(encoding="utf-8"))
    for index, raw_tool in enumerate(raw_tools):
        if raw_tool["name"] == name:
            return parse_mcp_tool(raw_tool, source_pointer=f"sample_tools#{index}")
    raise AssertionError(f"missing fixture tool {name}")


def _load_public_tool(name: str):
    raw_tools = json.loads(Path("data/raw/public_mcp_filesystem_subset.json").read_text(encoding="utf-8"))
    for index, raw_tool in enumerate(raw_tools):
        if raw_tool["name"] == name:
            return parse_mcp_tool(raw_tool, source_pointer=f"public_tools#{index}")
    raise AssertionError(f"missing fixture tool {name}")


class ReliabilityPipelineTests(unittest.TestCase):
    def test_tool_ir_exposes_reliability_features(self) -> None:
        tool = _load_tool("create_event")

        self.assertGreater(tool.doc_completeness, 0.0)
        self.assertEqual(tool.schema_complexity["num_required_arguments"], 2)
        self.assertGreaterEqual(tool.schema_complexity["max_schema_depth"], 2)
        self.assertIn("allows_or_omits_unknown_argument_policy", _load_tool("get_weather").ambiguity_flags)

    def test_benchmark_loader_supports_negative_controls(self) -> None:
        tasks = load_benchmark_tasks("data/eval/public_mcp_filesystem_reliability.jsonl")
        negative = next(task for task in tasks if task.task_id == "rel_search_should_not_write")

        self.assertFalse(negative.should_trigger)
        self.assertEqual(negative.negative_target, "write_file")
        self.assertEqual(negative.expected_tool_name, "search_files")

    def test_abstention_scoring_contract(self) -> None:
        tool = _load_public_tool("write_file")
        positive = EvalTask(
            task_id="pos",
            tool_name="write_file",
            user_request="Write notes.",
            expected_arguments={"path": "docs/out.txt", "content": "notes"},
            expected_argument_candidates=[{"path": "docs/out.txt", "content": "notes"}],
            should_trigger=True,
        )
        negative = EvalTask(
            task_id="neg",
            tool_name="write_file",
            user_request="Explain how writing works; do not call a tool.",
            expected_arguments={},
            expected_argument_candidates=[{}],
            should_trigger=False,
            negative_category="explanation_instead_of_action",
        )

        exact = score_prediction(
            positive,
            tool,
            EvalPrediction(
                task_id="pos",
                tool_name="write_file",
                baseline_name="generated_skill_base",
                predicted_arguments={"path": "docs/out.txt", "content": "notes"},
                should_call=True,
            ),
        )
        positive_abstain = score_prediction(
            positive,
            tool,
            EvalPrediction(task_id="pos", tool_name="write_file", baseline_name="generated_skill_base", predicted_arguments={}, should_call=False),
        )
        negative_abstain = score_prediction(
            negative,
            tool,
            EvalPrediction(task_id="neg", tool_name="write_file", baseline_name="generated_skill_base", predicted_arguments={}, should_call=False),
        )
        negative_empty_call = score_prediction(
            negative,
            tool,
            EvalPrediction(task_id="neg", tool_name="write_file", baseline_name="generated_skill_base", predicted_arguments={}, should_call=True),
        )
        negative_tool_name_only = score_prediction(
            negative,
            tool,
            EvalPrediction(
                task_id="neg",
                tool_name="write_file",
                baseline_name="generated_skill_base",
                predicted_arguments={},
                should_call=False,
                metadata={"selected_tool_name": "write_file"},
            ),
        )

        self.assertTrue(exact["joint_exact_match"])
        self.assertFalse(positive_abstain["joint_exact_match"])
        self.assertTrue(negative_abstain["joint_exact_match"])
        self.assertFalse(negative_empty_call["joint_exact_match"])
        self.assertTrue(negative_empty_call["harmful_injection"])
        self.assertFalse(negative_tool_name_only["joint_exact_match"])
        self.assertTrue(negative_tool_name_only["triggered"])
        self.assertTrue(negative_tool_name_only["harmful_injection"])

    def test_validator_structured_repairable_failures(self) -> None:
        tool = _load_tool("get_weather")
        skill = GeneratedSkill(
            baseline_name="validated_skill",
            skill_summary="Use `postal_code` optionally for weather.",
            when_to_use=["Use for weather."],
            when_not_to_use=[],
            argument_template={"city": "Paris", "unit": "K", "postal_code": "75000"},
            examples=[{"scenario": "bad enum", "arguments": {"city": "Paris", "unit": "K"}}],
        )
        report = validate_skill(tool, skill)

        self.assertFalse(report.valid)
        self.assertTrue(any(issue.repairable for issue in report.issues))
        self.assertTrue(any(issue.section in {"argument_template", "guidance", "when_not_to_use"} for issue in report.issues))

    def test_behavior_report_measures_harmful_injection(self) -> None:
        tool = _load_public_tool("write_file")
        bad_skill = GeneratedSkill(
            baseline_name="naive_skill",
            skill_summary="Write files and search docs.",
            when_to_use=["Use this for search docs and deployment notes."],
            when_not_to_use=["Do not use for unrelated tasks."],
            argument_template={"path": "docs/out.txt", "content": "notes"},
            examples=[],
        )
        cases = load_behavior_cases("data/eval/public_mcp_filesystem_reliability.jsonl")
        report = run_behavior_tests(tool, bad_skill, cases)

        self.assertGreater(report.metrics["harmful_skill_injection_rate"], 0.0)
        self.assertFalse(report.valid)

    def test_behavior_repair_adds_negative_control_boundary(self) -> None:
        tool = _load_public_tool("write_file")
        bad_skill = GeneratedSkill(
            baseline_name="repaired_skill",
            skill_summary="Write files and search docs.",
            when_to_use=["Use this for search docs and deployment notes."],
            when_not_to_use=["Do not use for unrelated tasks."],
            argument_template={"path": "docs/out.txt", "content": "notes"},
            examples=[],
        )
        cases = load_behavior_cases("data/eval/public_mcp_filesystem_reliability.jsonl")
        before = run_behavior_tests(tool, bad_skill, cases)
        repaired, repair_report, validation_report = repair_behavior_failures(tool, bad_skill, before)
        after = run_behavior_tests(tool, repaired, cases)

        self.assertTrue(repair_report.changed)
        self.assertTrue(validation_report.valid)
        self.assertGreater(before.metrics["harmful_skill_injection_rate"], after.metrics["harmful_skill_injection_rate"])
        self.assertTrue(any(action.action_type == "add_negative_control_boundary" for action in repair_report.actions))

    def test_targeted_repair_fixes_schema_sections(self) -> None:
        tool = _load_tool("get_weather")
        skill = GeneratedSkill(
            baseline_name="repaired_skill",
            skill_summary="Weather lookup.",
            when_to_use=["Use for weather."],
            when_not_to_use=[],
            argument_template={"city": "Paris", "unit": "K", "extra": True},
            examples=[{"scenario": "bad", "arguments": {"city": "Paris", "unit": "K", "extra": True}}],
        )
        repaired, repair_report, validation_report = repair_skill(tool, skill)

        self.assertTrue(repair_report.attempted)
        self.assertTrue(repair_report.changed)
        self.assertNotIn("extra", repaired.argument_template)
        self.assertIn(repaired.argument_template["unit"], ["C", "F"])
        self.assertTrue(any(classify_failure(issue) in {"invalid_enum", "unsupported_argument"} for issue in repair_report.remaining_issues) is False)
        self.assertTrue(validation_report.valid)

    def test_reliability_gate_rejects_harmful_skill(self) -> None:
        tool = _load_public_tool("write_file")
        skill = GeneratedSkill(
            baseline_name="naive_skill",
            skill_summary="Write files and search docs.",
            when_to_use=["Use this for search docs."],
            when_not_to_use=["Do not use for unrelated tasks."],
            argument_template={"path": "docs/out.txt", "content": "notes"},
            examples=[],
        )
        validation = validate_skill(tool, skill)
        behavior = run_behavior_tests(tool, skill, load_behavior_cases("data/eval/public_mcp_filesystem_reliability.jsonl"))
        score = score_reliability(tool, skill, validation, behavior)

        self.assertEqual(score.decision, "reject")
        self.assertGreater(score.features["harmful_skill_injection_rate"], 0.0)

    def test_rejected_gated_skill_does_not_trigger(self) -> None:
        tool = _load_public_tool("write_file")
        skill = GeneratedSkill(
            baseline_name="gated_skill",
            skill_summary="Deployment gate decision: reject.",
            when_to_use=[],
            when_not_to_use=["Do not deploy this generated skill artifact."],
            argument_template={},
            examples=[],
            metadata={"gate_decision": "reject"},
        )
        behavior = run_behavior_tests(tool, skill, load_behavior_cases("data/eval/public_mcp_filesystem_reliability.jsonl"))

        self.assertEqual(behavior.metrics["harmful_skill_injection_rate"], 0.0)
        self.assertEqual(behavior.metrics["trigger_true_positive"], 0)

    def test_packaging_writes_reliability_artifacts(self) -> None:
        tool = _load_tool("get_weather")
        skill = SkillGenerator().generate(tool)
        validation = validate_skill(tool, skill)
        behavior = run_behavior_tests(tool, skill, [])
        score = score_reliability(tool, skill, validation, behavior)

        with tempfile.TemporaryDirectory() as tmpdir:
            write_skill_package(Path(tmpdir), tool, skill, validation, behavior_report=behavior, reliability_score=score)
            self.assertTrue((Path(tmpdir) / "validation_report.json").exists())
            self.assertTrue((Path(tmpdir) / "behavior_report.json").exists())
            self.assertTrue((Path(tmpdir) / "reliability_score.json").exists())
            metadata = json.loads((Path(tmpdir) / "metadata.json").read_text(encoding="utf-8"))
            self.assertIn("reliability_score", metadata)

    def test_reliability_pipeline_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = run_reliability_pipeline(
                tools_path="data/raw/public_mcp_filesystem_subset.json",
                behavior_path="data/eval/public_mcp_filesystem_reliability.jsonl",
                output_root=tmpdir,
            )

            self.assertIn("gated_skill", manifest["summary"])
            self.assertTrue((Path(tmpdir) / "reliability_manifest.json").exists())
            self.assertTrue((Path(tmpdir) / "reliability_records.jsonl").exists())
            self.assertTrue((Path(tmpdir) / "reports" / "reliability_report.md").exists())
            self.assertTrue((Path(tmpdir) / "reports" / "reliability_summary.csv").exists())
            self.assertTrue((Path(tmpdir) / "packages" / "write_file" / "gated_skill" / "reliability_score.json").exists())

    def test_mcptoolbench_converter_builds_negative_controls(self) -> None:
        records = [
            {
                "uuid": "demo",
                "category": "file_system",
                "call_type": "single",
                "query": "Read docs/README.md",
                "tools": [
                    {
                        "id": "1",
                        "name": "read_file",
                        "description": "Read a file.",
                        "input_schema": {
                            "type": "object",
                            "properties": {"path": {"type": "string", "description": "File path."}},
                            "required": ["path"],
                        },
                    },
                    {
                        "id": "2",
                        "name": "write_file",
                        "description": "Write a file.",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string", "description": "File path."},
                                "content": {"type": "string", "description": "Content."},
                            },
                            "required": ["path", "content"],
                        },
                    },
                ],
                "function_call_label": [{"id": "1", "input": {"path": "docs/README.md"}}],
            }
        ]
        tools, tasks = convert_mcptoolbench_records(records, negatives_per_positive=1)

        self.assertEqual({tool["name"] for tool in tools}, {"read_file", "write_file"})
        self.assertTrue(any(task["should_trigger"] for task in tasks))
        negative = next(task for task in tasks if not task["should_trigger"])
        self.assertEqual(negative["negative_target"], "write_file")
        self.assertEqual(negative["expected_tool_name"], "read_file")

    def test_model_comparison_preflight_and_heuristic_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = root / "comparison.json"
            config = {
                "output_root": str(root / "comparison_out"),
                "hardware": "test",
                "compute_budget": "test",
                "runs": [
                    {
                        "name": "small_reliable",
                        "role": "small",
                        "selected_condition": "gated_skill",
                        "tools_path": "data/raw/public_mcp_filesystem_subset.json",
                        "behavior_path": "data/eval/public_mcp_filesystem_reliability.jsonl",
                        "output_root": str(root / "small"),
                        "generator": {"type": "heuristic"},
                        "predictor": {"type": "heuristic"},
                    },
                    {
                        "name": "larger_raw",
                        "role": "large",
                        "selected_condition": "raw_mcp",
                        "tools_path": "data/raw/public_mcp_filesystem_subset.json",
                        "behavior_path": "data/eval/public_mcp_filesystem_reliability.jsonl",
                        "output_root": str(root / "large"),
                        "generator": {"type": "heuristic"},
                        "predictor": {"type": "heuristic"},
                    },
                ],
                "comparisons": [{"left": "small_reliable", "right": "larger_raw", "metric": "avg_score"}],
            }
            config_path.write_text(json.dumps(config), encoding="utf-8")
            manifest = run_model_comparison_from_config(config_path)

            self.assertEqual(len(manifest["summary"]["runs"]), 2)
            self.assertTrue((root / "comparison_out" / "model_comparison_report.md").exists())
            self.assertTrue(manifest["summary"]["comparisons"])


if __name__ == "__main__":
    unittest.main()

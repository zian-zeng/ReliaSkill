from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import yaml

from autoskill.experiment import build_skill_variant_map, load_tools, run_benchmark_pipeline, run_routing_benchmark_pipeline
from autoskill.generator import SkillGenerator
from autoskill.conditions import LEGACY_RELIASKILL_CHALLENGER, normalize_condition_name
from autoskill.ir import GeneratedSkill, ReliabilityScore, RepairReport
from autoskill.method_metadata import RELIASKILL_CHALLENGER
from reliaskill.cluster import _build_challenger_skill, build_shared_skill_packages


class ChallengerConditionTests(unittest.TestCase):
    def test_reliaskill_v1_is_canonical_and_legacy_name_aliases_to_it(self) -> None:
        self.assertEqual(RELIASKILL_CHALLENGER, "reliaskill_v1")
        self.assertEqual(normalize_condition_name(LEGACY_RELIASKILL_CHALLENGER), RELIASKILL_CHALLENGER)

    def test_challenger_package_loads_dev_selected_repaired_artifact_and_records_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            dev_controls = self._write_dev_controls(root)
            multi_config = self._write_multi_candidate_config(root)
            config_path = self._write_config(
                root,
                conditions=["generated_skill_base", RELIASKILL_CHALLENGER],
                dev_controls=dev_controls,
                multi_config=multi_config,
            )

            manifest = build_shared_skill_packages(config_path)

            package_root = Path(manifest["shared_package_root"])
            challenger_dir = package_root / "create_directory" / RELIASKILL_CHALLENGER
            self.assertTrue((challenger_dir / "skill.json").exists())
            self.assertTrue((challenger_dir / "selection_report.json").exists())
            method_metadata = json.loads((challenger_dir / "method_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(method_metadata["source_condition"], "repaired_skill")
            self.assertEqual(method_metadata["gate_source_condition"], "gated_skill")
            self.assertIn("dev_multi_candidate_selection", method_metadata["pipeline_stages"])
            self.assertFalse(method_metadata["test_controls_used"])
            skill_json = json.loads((challenger_dir / "skill.json").read_text(encoding="utf-8"))
            self.assertIn("Full ReliaSkill v1 artifact", skill_json["skill_summary"])
            self.assertIn("Pipeline: dev-selected candidate", skill_json["skill_summary"])
            self.assertTrue(skill_json["metadata"]["prompt_visible_method_evidence"])
            self.assertEqual(skill_json["metadata"]["source_condition"], "repaired_skill")
            self.assertEqual(skill_json["metadata"]["gate_source_condition"], "gated_skill")
            self.assertNotIn("gate_decision", skill_json["metadata"])

            tools = load_tools("data/raw/public_mcp_filesystem_subset.json")
            loaded = build_skill_variant_map(
                tools["create_directory"],
                tools,
                SkillGenerator(),
                allowed_conditions=[RELIASKILL_CHALLENGER],
                package_manager_dir=package_root,
                allow_package_generation=False,
            )[RELIASKILL_CHALLENGER]
            trace_types = [entry.get("trace_type") for entry in loaded.method_trace]
            self.assertIn("multi_candidate_selection", trace_types)
            self.assertIn("reliaskill_v1_composition", trace_types)
            self.assertIn("package_load", trace_types)
            self.assertEqual(loaded.metadata["method_metadata"]["source_condition"], "repaired_skill")
            self.assertEqual(loaded.metadata["method_metadata"]["gate_source_condition"], "gated_skill")
            self.assertTrue(loaded.metadata["prompt_visible_method_evidence"])

            records, _, _ = run_benchmark_pipeline(
                tools={"create_directory": tools["create_directory"]},
                tasks_path=dev_controls,
                tasks=None,
                output_dir=root / "benchmark_dev",
                allowed_conditions=[RELIASKILL_CHALLENGER],
                package_manager_dir=package_root,
                allow_package_generation=False,
            )
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["baseline_name"], RELIASKILL_CHALLENGER)
            self.assertEqual(records[0]["method_metadata"]["source_condition"], "repaired_skill")
            self.assertEqual(records[0]["method_metadata"]["selection_policy"], "best_behavior_dev")

            routing_records, _, _ = run_routing_benchmark_pipeline(
                tools={"create_directory": tools["create_directory"]},
                tasks_path=dev_controls,
                tasks=None,
                output_dir=root / "routing_dev",
                allowed_conditions=[RELIASKILL_CHALLENGER],
                package_manager_dir=package_root,
                allow_package_generation=False,
            )
            self.assertEqual(len(routing_records), 1)
            self.assertEqual(routing_records[0]["baseline_name"], RELIASKILL_CHALLENGER)
            self.assertEqual(routing_records[0]["method_metadata"]["source_condition"], "repaired_skill")

    def test_challenger_soft_gate_keeps_repaired_guidance_visible(self) -> None:
        skill = GeneratedSkill(
            baseline_name="repaired_skill",
            skill_summary="Create a directory.",
            when_to_use=["Use when the user asks to create a directory and provides a path."],
            when_not_to_use=["Do not use when the path is missing."],
            argument_template={"path": "docs"},
            examples=[{"scenario": "Create docs", "arguments": {"path": "docs"}}],
        )
        source_row = {
            "reliability_score": ReliabilityScore(score=55.0, decision="repair", features={}, rationale=[]),
            "repair_report": RepairReport(attempted=True, changed=True, rounds=1),
        }
        gate_row = {
            "reliability_score": ReliabilityScore(score=30.0, decision="reject", features={}, rationale=[]),
            "repair_report": RepairReport(attempted=True, changed=True, rounds=1),
        }

        challenger = _build_challenger_skill(
            skill,
            source_row=source_row,
            gate_row=gate_row,
            selection_report_path=Path("missing_selection_report.json"),
        )

        self.assertEqual(challenger.baseline_name, RELIASKILL_CHALLENGER)
        self.assertTrue(challenger.when_to_use)
        self.assertIn("create a directory", " ".join(challenger.when_to_use).lower())
        self.assertNotIn("gate_decision", challenger.metadata)
        self.assertEqual(challenger.metadata["source_condition"], "repaired_skill")
        self.assertEqual(challenger.metadata["gate_source_condition"], "gated_skill")

    def test_challenger_preserves_specific_repaired_negative_boundaries(self) -> None:
        skill = GeneratedSkill(
            baseline_name="repaired_skill",
            skill_summary="Create a directory.",
            when_to_use=["Use for directory creation."],
            when_not_to_use=[
                "Do not call this tool when required inputs are missing or ambiguous.",
                "Do not invent unsupported parameters or unsupported enum values.",
                "Do not include unsupported fields; allowed top-level fields are: `path`.",
                "Do not use for adjacent tools with similar names, descriptions, or arguments.",
                "Do not use for read/write, search/fetch, create/update, delete/preview, or execute/explain mismatches.",
                "If the request lacks required fields, abstain or ask for clarification.",
                "Do not use this tool for out-of-domain requests unrelated to this tool's documented purpose.",
                "Do not use this tool for explanation, checklist, planning-only, or no-tool-call requests; abstain even when the tool name appears.",
                "Do not use this tool for read/search mismatch requests; abstain when the user asks to read an exact item and says not to search, retrieve, or browse.",
                "Do not use this tool when the request says a similar tool should be used and this tool is a distractor that should not be called.",
                "Do not use this tool for adjacent intent requests where the intended capability is a different tool.",
            ],
            argument_template={"path": "docs"},
            examples=[],
        )
        row = {
            "reliability_score": ReliabilityScore(score=70.0, decision="repair", features={}, rationale=[]),
            "repair_report": RepairReport(attempted=True, changed=True, rounds=1),
        }

        challenger = _build_challenger_skill(
            skill,
            source_row=row,
            gate_row=row,
            selection_report_path=Path("missing_selection_report.json"),
        )
        guidance = "\n".join(challenger.when_not_to_use)

        self.assertIn("read/search mismatch", guidance)
        self.assertIn("similar tool should be used", guidance)
        self.assertIn("adjacent intent", guidance)

    def test_missing_challenger_package_fails_even_when_generation_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tools = load_tools("data/raw/public_mcp_filesystem_subset.json")

            with self.assertRaisesRegex(FileNotFoundError, RELIASKILL_CHALLENGER):
                build_skill_variant_map(
                    tools["create_directory"],
                    tools,
                    SkillGenerator(),
                    allowed_conditions=[RELIASKILL_CHALLENGER],
                    package_manager_dir=root / "missing_packages",
                    allow_package_generation=True,
                )

    def test_challenger_shared_package_build_requires_multi_candidate_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            dev_controls = self._write_dev_controls(root)
            config_path = self._write_config(
                root,
                conditions=["generated_skill_base", RELIASKILL_CHALLENGER],
                dev_controls=dev_controls,
                multi_config=None,
            )

            with self.assertRaisesRegex(ValueError, "multi_candidate_config"):
                build_shared_skill_packages(config_path)

    @staticmethod
    def _write_dev_controls(root: Path) -> Path:
        path = root / "dev_controls.jsonl"
        path.write_text(
            json.dumps(
                {
                    "id": "dev_create_dir",
                    "function": "create_directory",
                    "question": "Create the docs directory.",
                    "ground_truth": {"arguments": {"path": "docs"}},
                    "should_trigger": True,
                    "split": "dev",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return path

    @staticmethod
    def _write_multi_candidate_config(root: Path) -> Path:
        path = root / "multi_candidate.yaml"
        path.write_text(
            yaml.safe_dump(
                {
                    "candidate_k": 3,
                    "selection_policy": "best_behavior_dev",
                    "candidate_strategies": ["concise_default", "boundary_heavy", "example_heavy"],
                }
            ),
            encoding="utf-8",
        )
        return path

    @staticmethod
    def _write_config(
        root: Path,
        *,
        conditions: list[str],
        dev_controls: Path,
        multi_config: Path | None,
    ) -> Path:
        config_path = root / "challenger.yaml"
        config = {
            "tools_path": "data/raw/public_mcp_filesystem_subset.json",
            "tasks_path": str(dev_controls),
            "output_root": str(root / "out"),
            "conditions": conditions,
            "data": {"max_tools": 1},
            "models": [{"model_name": "mock", "backend": "heuristic", "batch_size": 1}],
            "shared_skill_packages": {
                "root": str(root / "shared_packages"),
                "dev_controls_path": str(dev_controls),
                "reliability_predictor": {"type": "heuristic"},
            },
        }
        if multi_config is not None:
            config["skills"] = {"multi_candidate_config": str(multi_config), "candidate_k": 3}
        config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
        return config_path


if __name__ == "__main__":
    unittest.main()

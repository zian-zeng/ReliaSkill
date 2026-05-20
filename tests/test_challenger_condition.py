from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import yaml

from autoskill.experiment import build_skill_variant_map, load_tools, run_benchmark_pipeline, run_routing_benchmark_pipeline
from autoskill.generator import SkillGenerator
from autoskill.conditions import (
    LEGACY_RELIASKILL_CHALLENGER,
    RELIASKILL_V1_NO_CANDIDATE_VERIFICATION,
    RELIASKILL_V1_NO_CONTRASTIVE_CONTEXT,
    RELIASKILL_V1_NO_CONTRACT_DECODER,
    RELIASKILL_V1_NO_CONTRACT_ROUTING,
    RELIASKILL_V1_NO_DEPENDENCY_PLAN,
    RELIASKILL_V1_NO_DOC_CONSISTENCY_SHIELD,
    RELIASKILL_V1_NO_DOC_GROUNDING,
    RELIASKILL_V1_NO_IDENTIFIER_BINDING,
    RELIASKILL_V1_NO_RETRIEVAL_MISS_RESCUE,
    RELIASKILL_V1_NO_RUNTIME_GROUNDING,
    RELIASKILL_V1_NO_VERIFIER_REFINEMENT,
    normalize_condition_name,
)
from autoskill.ir import ArgumentIR, GeneratedSkill, ReliabilityScore, RepairReport, ToolIR
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
            self.assertIn("runtime_schema_contract_verifier", method_metadata["pipeline_stages"])
            self.assertIn("executable_contract_compilation", method_metadata["pipeline_stages"])
            self.assertIn("doc_grounded_contract_evidence", method_metadata["pipeline_stages"])
            self.assertIn("request_conditioned_doc_evidence", method_metadata["pipeline_stages"])
            self.assertIn("doc_contract_consistency_shield", method_metadata["pipeline_stages"])
            self.assertIn("contract_constrained_tool_inference", method_metadata["pipeline_stages"])
            self.assertIn("declarative_contract_proof_state", method_metadata["pipeline_stages"])
            self.assertIn("evidence_calibrated_contract_proof_ledger", method_metadata["pipeline_stages"])
            self.assertIn("calibratable_contract_proof_policy", method_metadata["pipeline_stages"])
            self.assertIn("dev_calibrated_contract_policy", method_metadata["pipeline_stages"])
            self.assertIn("dev_learned_slot_grounding", method_metadata["pipeline_stages"])
            self.assertIn("dev_learned_risk_aware_router_policy", method_metadata["pipeline_stages"])
            self.assertIn("proof_state_routing_policy", method_metadata["pipeline_stages"])
            self.assertIn("contrastive_contract_proof_context", method_metadata["pipeline_stages"])
            self.assertIn("retrieval_miss_proof_rescue", method_metadata["pipeline_stages"])
            self.assertIn("schema_semantic_doc_reranking", method_metadata["pipeline_stages"])
            self.assertIn("dependency_contract_plan_prompting", method_metadata["pipeline_stages"])
            self.assertIn("request_contract_parse_prompting", method_metadata["pipeline_stages"])
            self.assertIn("verifier_guided_refinement", method_metadata["pipeline_stages"])
            self.assertIn("contract_decoded_argument_completion", method_metadata["pipeline_stages"])
            self.assertIn("candidate_verified_routing_fallback", method_metadata["pipeline_stages"])
            self.assertTrue(method_metadata["uses_runtime_schema_contract_verifier"])
            self.assertTrue(method_metadata["uses_executable_skill_contract"])
            self.assertTrue(method_metadata["uses_contract_proof_ledger"])
            self.assertTrue(method_metadata["uses_adaptive_contract_policy"])
            self.assertTrue(method_metadata["uses_contextual_grounding_contract"])
            self.assertTrue(method_metadata["uses_multi_step_contract_planning"])
            self.assertTrue(method_metadata["uses_execution_feedback_contract"])
            self.assertTrue(method_metadata["uses_doc_grounded_contract_evidence"])
            self.assertTrue(method_metadata["uses_request_conditioned_doc_evidence"])
            self.assertTrue(method_metadata["uses_doc_contract_consistency_shield"])
            self.assertTrue(method_metadata["uses_contract_constrained_tool_inference"])
            self.assertTrue(method_metadata["uses_declarative_contract_proof_state"])
            self.assertTrue(method_metadata["uses_evidence_calibrated_contract_proof_ledger"])
            self.assertTrue(method_metadata["uses_calibratable_contract_proof_policy"])
            self.assertTrue(method_metadata["uses_dev_calibrated_contract_policy"])
            self.assertTrue(method_metadata["uses_dev_learned_slot_grounding"])
            self.assertTrue(method_metadata["uses_dev_learned_router_policy"])
            self.assertTrue(method_metadata["uses_proof_state_routing_policy"])
            self.assertTrue(method_metadata["uses_contrastive_contract_proof_context"])
            self.assertTrue(method_metadata["uses_retrieval_miss_proof_rescue"])
            self.assertTrue(method_metadata["uses_schema_semantic_doc_reranking"])
            self.assertTrue(method_metadata["uses_dependency_contract_plan_prompting"])
            self.assertTrue(method_metadata["uses_request_contract_parse_prompting"])
            self.assertTrue(method_metadata["uses_verifier_guided_refinement"])
            self.assertTrue(method_metadata["uses_contract_decoded_argument_completion"])
            self.assertTrue(method_metadata["uses_candidate_verified_routing_fallback"])
            self.assertFalse(method_metadata["test_controls_used"])
            skill_json = json.loads((challenger_dir / "skill.json").read_text(encoding="utf-8"))
            self.assertIn("Full ReliaSkill v1 artifact", skill_json["skill_summary"])
            self.assertIn("Pipeline: dev-selected candidate", skill_json["skill_summary"])
            self.assertTrue(skill_json["metadata"]["prompt_visible_method_evidence"])
            self.assertEqual(skill_json["metadata"]["source_condition"], "repaired_skill")
            self.assertEqual(skill_json["metadata"]["gate_source_condition"], "gated_skill")
            self.assertTrue(any("Allowed top-level fields" in line for line in skill_json["metadata"]["schema_contract"]))
            self.assertIn("executable_contract", skill_json["metadata"])
            self.assertIn("contract_proof_policy", skill_json["metadata"])
            self.assertEqual(skill_json["metadata"]["contract_proof_policy"]["name"], "dev_learned_contract_proof_policy")
            self.assertIn("contract_policy", skill_json["metadata"])
            self.assertEqual(skill_json["metadata"]["contract_policy"]["name"], "dev_learned_contract_policy")
            self.assertIn("learned_router_policy", skill_json["metadata"])
            self.assertEqual(skill_json["metadata"]["learned_router_policy"]["name"], "dev_learned_risk_aware_router_policy")
            self.assertIn("contract_policy_calibration", skill_json["metadata"])
            self.assertGreaterEqual(skill_json["metadata"]["contract_policy_calibration"]["examples"], 1)
            self.assertGreaterEqual(
                skill_json["metadata"]["contract_policy_calibration"]["source_counts"]["contract_counterfactual_negative"],
                1,
            )
            self.assertIn("dev_learned_slot_grounding", skill_json["metadata"])
            self.assertIn("path", skill_json["metadata"]["dev_learned_slot_grounding"]["arguments"])
            self.assertIn("all_required_arguments_grounded", skill_json["metadata"]["executable_contract"]["proof_obligations"])
            self.assertIn("contract_counterexamples", skill_json["metadata"])
            self.assertIn("doc_grounding_evidence", skill_json["metadata"])
            self.assertTrue(skill_json["metadata"]["uses_doc_grounded_contract_evidence"])
            self.assertTrue(skill_json["metadata"]["uses_request_conditioned_doc_evidence"])
            self.assertTrue(skill_json["metadata"]["uses_doc_contract_consistency_shield"])
            self.assertTrue(skill_json["metadata"]["uses_contract_constrained_tool_inference"])
            self.assertTrue(skill_json["metadata"]["uses_declarative_contract_proof_state"])
            self.assertTrue(skill_json["metadata"]["uses_evidence_calibrated_contract_proof_ledger"])
            self.assertTrue(skill_json["metadata"]["uses_calibratable_contract_proof_policy"])
            self.assertTrue(skill_json["metadata"]["uses_dev_calibrated_contract_policy"])
            self.assertTrue(skill_json["metadata"]["uses_dev_learned_slot_grounding"])
            self.assertTrue(skill_json["metadata"]["uses_dev_learned_router_policy"])
            self.assertTrue(skill_json["metadata"]["uses_proof_state_routing_policy"])
            self.assertTrue(skill_json["metadata"]["uses_contrastive_contract_proof_context"])
            self.assertTrue(skill_json["metadata"]["uses_retrieval_miss_proof_rescue"])
            self.assertTrue(skill_json["metadata"]["uses_schema_semantic_doc_reranking"])
            self.assertTrue(skill_json["metadata"]["uses_dependency_contract_plan_prompting"])
            self.assertTrue(skill_json["metadata"]["uses_request_contract_parse_prompting"])
            self.assertTrue(skill_json["metadata"]["uses_contract_decoded_argument_completion"])
            self.assertTrue(skill_json["metadata"]["uses_candidate_verified_routing_fallback"])
            self.assertTrue(
                any(
                    item["violated_obligation"] == "all_required_arguments_grounded"
                    for item in skill_json["metadata"]["contract_counterexamples"]
                )
            )
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
            self.assertTrue(loaded.metadata["method_metadata"]["uses_runtime_schema_contract_verifier"])
            self.assertTrue(loaded.metadata["method_metadata"]["uses_executable_skill_contract"])
            self.assertTrue(loaded.metadata["method_metadata"]["uses_contract_proof_ledger"])
            self.assertTrue(loaded.metadata["method_metadata"]["uses_adaptive_contract_policy"])
            self.assertTrue(loaded.metadata["method_metadata"]["uses_contextual_grounding_contract"])
            self.assertTrue(loaded.metadata["method_metadata"]["uses_multi_step_contract_planning"])
            self.assertTrue(loaded.metadata["method_metadata"]["uses_execution_feedback_contract"])
            self.assertTrue(loaded.metadata["method_metadata"]["uses_doc_grounded_contract_evidence"])
            self.assertTrue(loaded.metadata["method_metadata"]["uses_request_conditioned_doc_evidence"])
            self.assertTrue(loaded.metadata["method_metadata"]["uses_doc_contract_consistency_shield"])
            self.assertTrue(loaded.metadata["method_metadata"]["uses_contract_constrained_tool_inference"])
            self.assertTrue(loaded.metadata["method_metadata"]["uses_declarative_contract_proof_state"])
            self.assertTrue(loaded.metadata["method_metadata"]["uses_evidence_calibrated_contract_proof_ledger"])
            self.assertTrue(loaded.metadata["method_metadata"]["uses_calibratable_contract_proof_policy"])
            self.assertTrue(loaded.metadata["method_metadata"]["uses_dev_calibrated_contract_policy"])
            self.assertTrue(loaded.metadata["method_metadata"]["uses_dev_learned_slot_grounding"])
            self.assertTrue(loaded.metadata["method_metadata"]["uses_dev_learned_router_policy"])
            self.assertTrue(loaded.metadata["method_metadata"]["uses_proof_state_routing_policy"])
            self.assertTrue(loaded.metadata["method_metadata"]["uses_contrastive_contract_proof_context"])
            self.assertTrue(loaded.metadata["method_metadata"]["uses_retrieval_miss_proof_rescue"])
            self.assertTrue(loaded.metadata["method_metadata"]["uses_schema_semantic_doc_reranking"])
            self.assertTrue(loaded.metadata["method_metadata"]["uses_dependency_contract_plan_prompting"])
            self.assertEqual(
                loaded.metadata["method_metadata"]["contract_proof_policy"]["name"],
                "dev_learned_contract_proof_policy",
            )
            self.assertEqual(
                loaded.metadata["method_metadata"]["contract_policy"]["name"],
                "dev_learned_contract_policy",
            )
            self.assertEqual(
                loaded.metadata["method_metadata"]["learned_router_policy"]["name"],
                "dev_learned_risk_aware_router_policy",
            )
            self.assertTrue(loaded.metadata["method_metadata"]["uses_request_contract_parse_prompting"])
            self.assertTrue(loaded.metadata["method_metadata"]["uses_verifier_guided_refinement"])
            self.assertTrue(loaded.metadata["method_metadata"]["uses_contract_decoded_argument_completion"])
            self.assertTrue(loaded.metadata["method_metadata"]["uses_candidate_verified_routing_fallback"])
            self.assertTrue(loaded.metadata["prompt_visible_method_evidence"])
            ablations = build_skill_variant_map(
                tools["create_directory"],
                tools,
                SkillGenerator(),
                allowed_conditions=[
                    RELIASKILL_V1_NO_CONTRACT_ROUTING,
                    RELIASKILL_V1_NO_RUNTIME_GROUNDING,
                    RELIASKILL_V1_NO_DOC_GROUNDING,
                    RELIASKILL_V1_NO_DOC_CONSISTENCY_SHIELD,
                    RELIASKILL_V1_NO_VERIFIER_REFINEMENT,
                    RELIASKILL_V1_NO_IDENTIFIER_BINDING,
                    RELIASKILL_V1_NO_CONTRACT_DECODER,
                    RELIASKILL_V1_NO_CANDIDATE_VERIFICATION,
                    RELIASKILL_V1_NO_CONTRASTIVE_CONTEXT,
                    RELIASKILL_V1_NO_RETRIEVAL_MISS_RESCUE,
                    RELIASKILL_V1_NO_DEPENDENCY_PLAN,
                ],
                package_manager_dir=package_root,
                allow_package_generation=False,
            )
            self.assertEqual(
                set(ablations),
                {
                    RELIASKILL_V1_NO_CONTRACT_ROUTING,
                    RELIASKILL_V1_NO_RUNTIME_GROUNDING,
                    RELIASKILL_V1_NO_DOC_GROUNDING,
                    RELIASKILL_V1_NO_DOC_CONSISTENCY_SHIELD,
                    RELIASKILL_V1_NO_VERIFIER_REFINEMENT,
                    RELIASKILL_V1_NO_IDENTIFIER_BINDING,
                    RELIASKILL_V1_NO_CONTRACT_DECODER,
                    RELIASKILL_V1_NO_CANDIDATE_VERIFICATION,
                    RELIASKILL_V1_NO_CONTRASTIVE_CONTEXT,
                    RELIASKILL_V1_NO_RETRIEVAL_MISS_RESCUE,
                    RELIASKILL_V1_NO_DEPENDENCY_PLAN,
                },
            )
            self.assertEqual(
                ablations[RELIASKILL_V1_NO_CONTRACT_ROUTING].metadata["contract_ablation"],
                "contract_routing",
            )
            self.assertTrue(
                ablations[RELIASKILL_V1_NO_RUNTIME_GROUNDING].metadata["contract_ablation_flags"]["disable_runtime_grounding"]
            )
            self.assertTrue(ablations[RELIASKILL_V1_NO_DOC_GROUNDING].metadata["contract_ablation_flags"]["disable_doc_grounding"])
            self.assertTrue(
                ablations[RELIASKILL_V1_NO_DOC_CONSISTENCY_SHIELD].metadata["contract_ablation_flags"][
                    "disable_doc_consistency_shield"
                ]
            )
            self.assertTrue(
                ablations[RELIASKILL_V1_NO_VERIFIER_REFINEMENT].metadata["contract_ablation_flags"]["disable_verifier_refinement"]
            )
            self.assertTrue(
                ablations[RELIASKILL_V1_NO_IDENTIFIER_BINDING].metadata["contract_ablation_flags"]["disable_identifier_binding"]
            )
            self.assertTrue(
                ablations[RELIASKILL_V1_NO_CONTRACT_DECODER].metadata["contract_ablation_flags"]["disable_contract_decoder"]
            )
            self.assertTrue(
                ablations[RELIASKILL_V1_NO_CANDIDATE_VERIFICATION].metadata["contract_ablation_flags"]["disable_candidate_verification"]
            )
            self.assertTrue(
                ablations[RELIASKILL_V1_NO_CONTRASTIVE_CONTEXT].metadata["contract_ablation_flags"][
                    "disable_contrastive_contract_context"
                ]
            )
            self.assertTrue(
                ablations[RELIASKILL_V1_NO_RETRIEVAL_MISS_RESCUE].metadata["contract_ablation_flags"][
                    "disable_retrieval_miss_rescue"
                ]
            )
            self.assertTrue(
                ablations[RELIASKILL_V1_NO_DEPENDENCY_PLAN].metadata["contract_ablation_flags"][
                    "disable_dependency_plan_prompting"
                ]
            )

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
            tool=_create_directory_tool(),
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
            tool=_create_directory_tool(),
            source_row=row,
            gate_row=row,
            selection_report_path=Path("missing_selection_report.json"),
        )
        guidance = "\n".join(challenger.when_not_to_use)

        self.assertIn("read/search mismatch", guidance)
        self.assertIn("similar tool should be used", guidance)
        self.assertIn("adjacent intent", guidance)
        self.assertIn("Allowed top-level fields", "\n".join(challenger.metadata["schema_contract"]))

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


def _create_directory_tool() -> ToolIR:
    return ToolIR(
        tool_name="create_directory",
        tool_purpose="Create a directory.",
        arguments=[ArgumentIR(name="path", type="string", required=True)],
    )


if __name__ == "__main__":
    unittest.main()

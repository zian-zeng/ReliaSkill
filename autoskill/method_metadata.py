from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from autoskill.ir import GeneratedSkill


RELIASKILL_V1 = "reliaskill_v1"
LEGACY_RELIASKILL_CHALLENGER = "reliaskill_challenger_v1"
RELIASKILL_CHALLENGER = RELIASKILL_V1

CHALLENGER_REQUIRED_FILES = [
    "skill.json",
    "validation_report.json",
    "behavior_report.json",
    "repair_report.json",
    "reliability_score.json",
    "selection_report.json",
    "method_metadata.json",
]


def require_challenger_package(package_dir: Path) -> None:
    missing = [name for name in CHALLENGER_REQUIRED_FILES if not (package_dir / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing required `{RELIASKILL_CHALLENGER}` package files in {package_dir}: "
            + ", ".join(missing)
        )


def load_package_method_metadata(package_dir: Path, *, condition: str) -> Dict[str, Any]:
    metadata = _read_json(package_dir / "metadata.json")
    method = _read_json(package_dir / "method_metadata.json")
    reliability = _read_json(package_dir / "reliability_score.json")
    repair = _read_json(package_dir / "repair_report.json")
    selection = _read_json(package_dir / "selection_report.json")
    behavior = _read_json(package_dir / "behavior_report.json")
    validation = _read_json(package_dir / "validation_report.json")

    compact: Dict[str, Any] = {
        "condition": condition,
        "loaded_from_package": True,
        "package_path": str(package_dir),
        "pipeline_stages": method.get("pipeline_stages", []),
        "source_condition": method.get("source_condition"),
        "gate_source_condition": method.get("gate_source_condition"),
        "uses_runtime_schema_contract_verifier": bool(method.get("uses_runtime_schema_contract_verifier", False)),
        "uses_executable_skill_contract": bool(method.get("uses_executable_skill_contract", False)),
        "uses_contract_proof_ledger": bool(method.get("uses_contract_proof_ledger", False)),
        "uses_adaptive_contract_policy": bool(method.get("uses_adaptive_contract_policy", False)),
        "uses_dev_calibrated_contract_policy": bool(method.get("uses_dev_calibrated_contract_policy", False)),
        "uses_dev_learned_slot_grounding": bool(method.get("uses_dev_learned_slot_grounding", False)),
        "uses_contextual_grounding_contract": bool(method.get("uses_contextual_grounding_contract", False)),
        "uses_multi_step_contract_planning": bool(method.get("uses_multi_step_contract_planning", False)),
        "uses_execution_feedback_contract": bool(method.get("uses_execution_feedback_contract", False)),
        "uses_doc_grounded_contract_evidence": bool(method.get("uses_doc_grounded_contract_evidence", False)),
        "uses_request_conditioned_doc_evidence": bool(method.get("uses_request_conditioned_doc_evidence", False)),
        "uses_doc_contract_consistency_shield": bool(method.get("uses_doc_contract_consistency_shield", False)),
        "uses_contract_constrained_tool_inference": bool(method.get("uses_contract_constrained_tool_inference", False)),
        "uses_declarative_contract_proof_state": bool(method.get("uses_declarative_contract_proof_state", False)),
        "uses_evidence_calibrated_contract_proof_ledger": bool(
            method.get("uses_evidence_calibrated_contract_proof_ledger", False)
        ),
        "uses_calibratable_contract_proof_policy": bool(method.get("uses_calibratable_contract_proof_policy", False)),
        "uses_proof_state_routing_policy": bool(method.get("uses_proof_state_routing_policy", False)),
        "uses_contrastive_contract_proof_context": bool(method.get("uses_contrastive_contract_proof_context", False)),
        "uses_retrieval_miss_proof_rescue": bool(method.get("uses_retrieval_miss_proof_rescue", False)),
        "uses_schema_semantic_doc_reranking": bool(method.get("uses_schema_semantic_doc_reranking", False)),
        "uses_dependency_contract_plan_prompting": bool(method.get("uses_dependency_contract_plan_prompting", False)),
        "uses_request_contract_parse_prompting": bool(method.get("uses_request_contract_parse_prompting", False)),
        "uses_verifier_guided_refinement": bool(method.get("uses_verifier_guided_refinement", False)),
        "uses_contract_decoded_argument_completion": bool(method.get("uses_contract_decoded_argument_completion", False)),
        "uses_candidate_verified_routing_fallback": bool(method.get("uses_candidate_verified_routing_fallback", False)),
        "uses_contract_verified_candidate_cascade": bool(method.get("uses_contract_verified_candidate_cascade", False)),
        "uses_dev_learned_router_policy": bool(method.get("uses_dev_learned_router_policy", False)),
        "uses_global_pairwise_router_prior": bool(method.get("uses_global_pairwise_router_prior", False)),
        "uses_dev_hard_negative_policy_refinement": bool(method.get("uses_dev_hard_negative_policy_refinement", False)),
        "uses_unified_proof_risk_policy_score": bool(method.get("uses_unified_proof_risk_policy_score", False)),
        "uses_adaptive_prompt_package_arbitration": bool(method.get("uses_adaptive_prompt_package_arbitration", False)),
        "uses_risk_adaptive_contract_prompt_policy": bool(method.get("uses_risk_adaptive_contract_prompt_policy", False)),
        "uses_explicit_argument_fidelity_selection": bool(method.get("uses_explicit_argument_fidelity_selection", False)),
        "test_controls_used": bool(method.get("test_controls_used", False)),
    }
    if metadata:
        compact["metadata_baseline_name"] = metadata.get("baseline_name")
        compact["behavior_metrics"] = metadata.get("behavior_metrics")
    if validation:
        compact["validation_valid"] = validation.get("valid")
        compact["validation_issue_count"] = len(validation.get("issues") or [])
    if reliability:
        compact["reliability_decision"] = reliability.get("decision")
        compact["reliability_score"] = reliability.get("score")
        compact["reliability_threshold"] = reliability.get("threshold")
    if repair:
        compact["repair_attempted"] = repair.get("attempted")
        compact["repair_changed"] = repair.get("changed")
        compact["repair_rounds"] = repair.get("rounds")
        compact["repair_strategy"] = repair.get("strategy")
    if selection:
        compact["selected_candidate_id"] = selection.get("selected_candidate_id")
        compact["selection_policy"] = selection.get("selection_policy")
        compact["candidate_count"] = selection.get("candidate_count")
        compact["dev_controls_used"] = selection.get("dev_controls_used")
    if behavior:
        compact["dev_behavior_metrics"] = behavior.get("metrics")
    if isinstance(method.get("contract_proof_policy"), dict):
        compact["contract_proof_policy"] = method.get("contract_proof_policy")
    if isinstance(method.get("contract_policy"), dict):
        compact["contract_policy"] = method.get("contract_policy")
    if isinstance(method.get("contract_policy_calibration"), dict):
        compact["contract_policy_calibration"] = method.get("contract_policy_calibration")
    if isinstance(method.get("dev_learned_slot_grounding"), dict):
        compact["dev_learned_slot_grounding"] = method.get("dev_learned_slot_grounding")
    if isinstance(method.get("learned_router_policy"), dict):
        compact["learned_router_policy"] = method.get("learned_router_policy")
    if not compact.get("uses_runtime_schema_contract_verifier"):
        compact["uses_runtime_schema_contract_verifier"] = "runtime_schema_contract_verifier" in compact.get("pipeline_stages", [])
    if not compact.get("uses_executable_skill_contract"):
        compact["uses_executable_skill_contract"] = "executable_contract_compilation" in compact.get("pipeline_stages", [])
    if not compact.get("uses_contract_proof_ledger"):
        compact["uses_contract_proof_ledger"] = "proof_carrying_runtime_contract" in compact.get("pipeline_stages", [])
    if not compact.get("uses_adaptive_contract_policy"):
        compact["uses_adaptive_contract_policy"] = "adaptive_contract_policy" in compact.get("pipeline_stages", [])
    if not compact.get("uses_dev_calibrated_contract_policy"):
        compact["uses_dev_calibrated_contract_policy"] = "dev_calibrated_contract_policy" in compact.get("pipeline_stages", [])
    if not compact.get("uses_dev_learned_slot_grounding"):
        compact["uses_dev_learned_slot_grounding"] = "dev_learned_slot_grounding" in compact.get("pipeline_stages", [])
    if not compact.get("uses_contextual_grounding_contract"):
        compact["uses_contextual_grounding_contract"] = "contextual_grounding_contract" in compact.get("pipeline_stages", [])
    if not compact.get("uses_multi_step_contract_planning"):
        compact["uses_multi_step_contract_planning"] = "multi_step_contract_plan_composition" in compact.get("pipeline_stages", [])
    if not compact.get("uses_execution_feedback_contract"):
        compact["uses_execution_feedback_contract"] = "execution_feedback_contract_interpreter" in compact.get("pipeline_stages", [])
    if not compact.get("uses_doc_grounded_contract_evidence"):
        compact["uses_doc_grounded_contract_evidence"] = "doc_grounded_contract_evidence" in compact.get("pipeline_stages", [])
    if not compact.get("uses_request_conditioned_doc_evidence"):
        compact["uses_request_conditioned_doc_evidence"] = "request_conditioned_doc_evidence" in compact.get("pipeline_stages", [])
    if not compact.get("uses_doc_contract_consistency_shield"):
        compact["uses_doc_contract_consistency_shield"] = "doc_contract_consistency_shield" in compact.get("pipeline_stages", [])
    if not compact.get("uses_contract_constrained_tool_inference"):
        compact["uses_contract_constrained_tool_inference"] = "contract_constrained_tool_inference" in compact.get("pipeline_stages", [])
    if not compact.get("uses_declarative_contract_proof_state"):
        compact["uses_declarative_contract_proof_state"] = "declarative_contract_proof_state" in compact.get("pipeline_stages", [])
    if not compact.get("uses_evidence_calibrated_contract_proof_ledger"):
        compact["uses_evidence_calibrated_contract_proof_ledger"] = "evidence_calibrated_contract_proof_ledger" in compact.get(
            "pipeline_stages", []
        )
    if not compact.get("uses_calibratable_contract_proof_policy"):
        compact["uses_calibratable_contract_proof_policy"] = "calibratable_contract_proof_policy" in compact.get("pipeline_stages", [])
    if not compact.get("uses_proof_state_routing_policy"):
        compact["uses_proof_state_routing_policy"] = "proof_state_routing_policy" in compact.get("pipeline_stages", [])
    if not compact.get("uses_contrastive_contract_proof_context"):
        compact["uses_contrastive_contract_proof_context"] = "contrastive_contract_proof_context" in compact.get("pipeline_stages", [])
    if not compact.get("uses_retrieval_miss_proof_rescue"):
        compact["uses_retrieval_miss_proof_rescue"] = "retrieval_miss_proof_rescue" in compact.get("pipeline_stages", [])
    if not compact.get("uses_schema_semantic_doc_reranking"):
        compact["uses_schema_semantic_doc_reranking"] = "schema_semantic_doc_reranking" in compact.get("pipeline_stages", [])
    if not compact.get("uses_dependency_contract_plan_prompting"):
        compact["uses_dependency_contract_plan_prompting"] = "dependency_contract_plan_prompting" in compact.get("pipeline_stages", [])
    if not compact.get("uses_request_contract_parse_prompting"):
        compact["uses_request_contract_parse_prompting"] = "request_contract_parse_prompting" in compact.get("pipeline_stages", [])
    if not compact.get("uses_verifier_guided_refinement"):
        compact["uses_verifier_guided_refinement"] = "verifier_guided_refinement" in compact.get("pipeline_stages", [])
    if not compact.get("uses_contract_decoded_argument_completion"):
        compact["uses_contract_decoded_argument_completion"] = "contract_decoded_argument_completion" in compact.get("pipeline_stages", [])
    if not compact.get("uses_candidate_verified_routing_fallback"):
        compact["uses_candidate_verified_routing_fallback"] = "candidate_verified_routing_fallback" in compact.get("pipeline_stages", [])
    if not compact.get("uses_contract_verified_candidate_cascade"):
        compact["uses_contract_verified_candidate_cascade"] = "contract_verified_candidate_cascade" in compact.get("pipeline_stages", [])
    if not compact.get("uses_dev_learned_router_policy"):
        compact["uses_dev_learned_router_policy"] = "dev_learned_risk_aware_router_policy" in compact.get("pipeline_stages", [])
    if not compact.get("uses_global_pairwise_router_prior"):
        compact["uses_global_pairwise_router_prior"] = "global_pairwise_router_prior" in compact.get("pipeline_stages", [])
    if not compact.get("uses_dev_hard_negative_policy_refinement"):
        compact["uses_dev_hard_negative_policy_refinement"] = "dev_hard_negative_policy_refinement" in compact.get("pipeline_stages", [])
    if not compact.get("uses_unified_proof_risk_policy_score"):
        compact["uses_unified_proof_risk_policy_score"] = "unified_proof_risk_policy_score" in compact.get("pipeline_stages", [])
    if not compact.get("uses_adaptive_prompt_package_arbitration"):
        compact["uses_adaptive_prompt_package_arbitration"] = "adaptive_prompt_package_arbitration" in compact.get("pipeline_stages", [])
    if not compact.get("uses_risk_adaptive_contract_prompt_policy"):
        compact["uses_risk_adaptive_contract_prompt_policy"] = "risk_adaptive_contract_prompt_policy" in compact.get(
            "pipeline_stages", []
        )
    if not compact.get("uses_explicit_argument_fidelity_selection"):
        compact["uses_explicit_argument_fidelity_selection"] = "explicit_argument_fidelity_candidate_selection" in compact.get(
            "pipeline_stages", []
        )
    if not compact.get("uses_explicit_nonuse_boundary_certificate"):
        compact["uses_explicit_nonuse_boundary_certificate"] = "explicit_nonuse_boundary_certificate" in compact.get("pipeline_stages", [])
    return {key: value for key, value in compact.items() if value is not None}


def attach_loaded_package_metadata(skill: GeneratedSkill, package_dir: Path, *, condition: str) -> GeneratedSkill:
    method_metadata = load_package_method_metadata(package_dir, condition=condition)
    skill.metadata = {
        **skill.metadata,
        "loaded_from_package": True,
        "package_path": str(package_dir),
        "method_metadata": method_metadata,
    }
    skill.method_trace = [
        *skill.method_trace,
        {
            "trace_type": "package_load",
            "condition": condition,
            "package_path": str(package_dir),
            "loaded_from_package": True,
        },
    ]
    return skill


def prediction_method_metadata(skill: GeneratedSkill) -> Dict[str, Any]:
    method = skill.metadata.get("method_metadata") if isinstance(skill.metadata, dict) else None
    method = dict(method) if isinstance(method, dict) else {}
    result: Dict[str, Any] = {
        "condition": skill.baseline_name,
        "method_trace_types": [
            str(entry.get("trace_type"))
            for entry in skill.method_trace
            if isinstance(entry, dict) and entry.get("trace_type")
        ],
        "condition_family": skill.metadata.get("condition_family") if isinstance(skill.metadata, dict) else None,
        "loaded_from_package": skill.metadata.get("loaded_from_package") if isinstance(skill.metadata, dict) else None,
        "package_path": skill.metadata.get("package_path") if isinstance(skill.metadata, dict) else None,
        **method,
    }
    return {key: value for key, value in result.items() if value is not None}


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}

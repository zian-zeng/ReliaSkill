from __future__ import annotations

from autoskill.compactness import SKILL_LENGTH_VARIANTS
from autoskill.artifacts import DOCS_ONLY, GATED_SKILL, NAIVE_SKILL, RAW_MCP, RELIASKILL_CHALLENGER, REPAIRED_SKILL, SCHEMA_ONLY, VALIDATED_SKILL
from autoskill.conditions import REVIEWER_BASELINES, RELIASKILL_V1_CONTRACT_ABLATIONS
from autoskill.prompt_templates import PROMPT_TEMPLATE_CONDITIONS, PROMPT_TEMPLATE_SPECS
from reliaskill.human_skill_condition import HUMAN_WRITTEN_SKILL
from reliaskill.stress_tests.corrupt_skills import STRESS_TEST_CONDITIONS

CONDITION_REGISTRY = {
    condition: {"condition": condition}
    for condition in REVIEWER_BASELINES
}
for condition in [RAW_MCP, SCHEMA_ONLY, DOCS_ONLY, NAIVE_SKILL, VALIDATED_SKILL, REPAIRED_SKILL, GATED_SKILL]:
    CONDITION_REGISTRY[condition] = {
        "condition": condition,
        "family": "reliability_ladder",
        "uses_dev_controls": condition in {NAIVE_SKILL, VALIDATED_SKILL, REPAIRED_SKILL, GATED_SKILL},
        "uses_test_controls_for_authoring": False,
    }
CONDITION_REGISTRY[RELIASKILL_CHALLENGER] = {
    "condition": RELIASKILL_CHALLENGER,
    "family": "reliaskill_full_method",
    "artifact_backed": True,
    "requires_dev_multi_candidate_selection": True,
    "requires_validation": True,
    "requires_repair": True,
    "requires_reliability_gate": True,
    "uses_runtime_schema_contract_verifier": True,
    "uses_executable_skill_contract": True,
    "uses_contract_proof_ledger": True,
    "uses_adaptive_contract_policy": True,
    "uses_dev_calibrated_contract_policy": True,
    "uses_dev_learned_slot_grounding": True,
    "uses_contextual_grounding_contract": True,
    "uses_request_contract_parse_prompting": True,
    "uses_multi_step_contract_planning": True,
    "uses_execution_feedback_contract": True,
    "uses_request_conditioned_doc_evidence": True,
    "uses_doc_contract_consistency_shield": True,
    "uses_contract_constrained_tool_inference": True,
    "uses_declarative_contract_proof_state": True,
    "uses_evidence_calibrated_contract_proof_ledger": True,
    "uses_calibratable_contract_proof_policy": True,
    "uses_proof_state_routing_policy": True,
    "uses_contrastive_contract_proof_context": True,
    "uses_retrieval_miss_proof_rescue": True,
    "uses_schema_semantic_doc_reranking": True,
    "uses_dependency_contract_plan_prompting": True,
    "uses_schema_affordance_routing_gate": True,
    "uses_candidate_verified_routing_fallback": True,
    "uses_action_intent_gate": True,
    "uses_required_argument_grounding": True,
    "uses_contract_decoded_argument_completion": True,
    "uses_false_abstention_rescue": True,
    "uses_dev_controls": True,
    "uses_test_controls_for_authoring": False,
}
for condition in RELIASKILL_V1_CONTRACT_ABLATIONS:
    CONDITION_REGISTRY[condition] = {
        "condition": condition,
        "family": "reliaskill_v1_component_ablation",
        "source_condition": RELIASKILL_CHALLENGER,
        "requires_reliaskill_v1_package": True,
        "disabled_component": condition.replace("reliaskill_v1_no_", ""),
        "uses_test_controls_for_authoring": False,
    }
CONDITION_REGISTRY[HUMAN_WRITTEN_SKILL] = {
    "condition": HUMAN_WRITTEN_SKILL,
    "family": "human_upper_bound",
    "requires_human_artifact": True,
    "skills_root": "data/human_skills/skills",
    "uses_dev_controls_for_authoring": False,
    "uses_test_controls_for_authoring": False,
}
for condition, config in SKILL_LENGTH_VARIANTS.items():
    CONDITION_REGISTRY[condition] = {
        "condition": condition,
        "family": "skill_compactness",
        "max_skill_tokens": config.get("max_skill_tokens"),
        "max_examples": config.get("max_examples"),
        "include_when_not_to_use": config.get("include_when_not_to_use"),
        "include_failure_modes": config.get("include_failure_modes"),
        "include_argument_template": config.get("include_argument_template"),
    }
for condition, template_id in PROMPT_TEMPLATE_CONDITIONS.items():
    spec = PROMPT_TEMPLATE_SPECS[template_id]
    CONDITION_REGISTRY[condition] = {
        "condition": condition,
        "family": "prompt_template_ablation",
        "template_id": spec.template_id,
        "template_family": spec.template_family,
        "allowed_sections": list(spec.allowed_sections),
        "max_tokens": spec.max_tokens,
        "uses_dev_controls": spec.uses_dev_controls,
        "uses_negative_controls": spec.uses_negative_controls,
    }
for condition, corruption_types in STRESS_TEST_CONDITIONS.items():
    CONDITION_REGISTRY[condition] = {
        "condition": condition,
        "family": "diagnostic_corrupted_skill",
        "diagnostic_only": True,
        "adversarial": True,
        "corruption_types": list(corruption_types),
        "normal_benchmark_condition": False,
        "requires_explicit_configuration": True,
    }

__all__ = [
    "CONDITION_REGISTRY",
    "REVIEWER_BASELINES",
    "SKILL_LENGTH_VARIANTS",
    "HUMAN_WRITTEN_SKILL",
    "PROMPT_TEMPLATE_CONDITIONS",
    "STRESS_TEST_CONDITIONS",
]

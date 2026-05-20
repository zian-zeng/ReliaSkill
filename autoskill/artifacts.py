from __future__ import annotations

from copy import deepcopy
from typing import Iterable

from autoskill.ir import GeneratedSkill, ToolIR
from autoskill.templates import build_argument_template
from autoskill.token_accounting import skill_token_count as counted_skill_token_count


RAW_MCP = "raw_mcp"
SCHEMA_ONLY = "schema_only"
DOCS_ONLY = "docs_only"
NAIVE_SKILL = "naive_skill"
VALIDATED_SKILL = "validated_skill"
REPAIRED_SKILL = "repaired_skill"
GATED_SKILL = "gated_skill"
RELIASKILL_V1 = "reliaskill_v1"
LEGACY_RELIASKILL_CHALLENGER = "reliaskill_challenger_v1"
RELIASKILL_CHALLENGER = RELIASKILL_V1
RELIASKILL_V1_NO_CONTRACT_ROUTING = "reliaskill_v1_no_contract_routing"
RELIASKILL_V1_NO_RUNTIME_GROUNDING = "reliaskill_v1_no_runtime_grounding"
RELIASKILL_V1_NO_ACTION_GATE = "reliaskill_v1_no_action_gate"
RELIASKILL_V1_NO_SCHEMA_REPAIR = "reliaskill_v1_no_schema_repair"
RELIASKILL_V1_NO_AMBIGUITY_ABSTENTION = "reliaskill_v1_no_ambiguity_abstention"
RELIASKILL_V1_NO_CONTEXTUAL_GROUNDING = "reliaskill_v1_no_contextual_grounding"
RELIASKILL_V1_NO_DOC_GROUNDING = "reliaskill_v1_no_doc_grounding"
RELIASKILL_V1_NO_DOC_CONSISTENCY_SHIELD = "reliaskill_v1_no_doc_consistency_shield"
RELIASKILL_V1_NO_VERIFIER_REFINEMENT = "reliaskill_v1_no_verifier_refinement"
RELIASKILL_V1_NO_IDENTIFIER_BINDING = "reliaskill_v1_no_identifier_binding"
RELIASKILL_V1_NO_CONTRACT_DECODER = "reliaskill_v1_no_contract_decoder"
RELIASKILL_V1_NO_CANDIDATE_VERIFICATION = "reliaskill_v1_no_candidate_verification"
RELIASKILL_V1_NO_CONTRACT_ARBITRATION = "reliaskill_v1_no_contract_arbitration"
RELIASKILL_V1_NO_CONTRASTIVE_MEMORY = "reliaskill_v1_no_contrastive_memory"
RELIASKILL_V1_NO_LEARNED_ROUTER_POLICY = "reliaskill_v1_no_learned_router_policy"
RELIASKILL_V1_NO_CONTRASTIVE_CONTEXT = "reliaskill_v1_no_contrastive_context"
RELIASKILL_V1_NO_RETRIEVAL_MISS_RESCUE = "reliaskill_v1_no_retrieval_miss_rescue"
RELIASKILL_V1_NO_DEPENDENCY_PLAN = "reliaskill_v1_no_dependency_plan"
PROMPT_ONLY_CAREFUL_TOOL_USE = "prompt_only_careful_tool_use"
RAW_SCHEMA_PLUS_EXAMPLES = "raw_schema_plus_examples"
GENERATED_DOCS_NO_VALIDATION = "generated_docs_no_validation"
GENERIC_VALIDATOR_NO_BEHAVIOR_TESTS = "generic_validator_no_behavior_tests"
FULL_REGENERATION_REPAIR = "full_regeneration_repair"
CURATED_SCHEMA_REFERENCE = "curated_schema_reference"
HUMAN_WRITTEN_SKILL_UPPER_BOUND = "human_written_skill_upper_bound"
GENERATED_SKILL_BASE = "generated_skill_base"
AUTOSKILL_BASE = "autoskill_base"
RETRIEVAL_TOOL_CARD = "retrieval_tool_card"
LARGER_MODEL_NAIVE_SKILL = "larger_model_naive_skill"
ADVERSARIAL_DISTRACTOR_INVENTORY = "adversarial_distractor_inventory"
NAIVE_SKILL_K1 = "naive_skill_k1"
MULTI_CANDIDATE_SKILL_K3_VALIDATION_SELECT = "multi_candidate_skill_k3_validation_select"
MULTI_CANDIDATE_SKILL_K3_BEHAVIOR_SELECT = "multi_candidate_skill_k3_behavior_select"
MULTI_CANDIDATE_REPAIRED_GATED = "multi_candidate_repaired_gated"
REPAIRED_FULL_REGENERATION = "repaired_full_regeneration"
REPAIRED_TARGETED_PATCH = "repaired_targeted_patch"
REPAIRED_BOUNDARY_ONLY = "repaired_boundary_only"
REPAIRED_EXAMPLE_ONLY = "repaired_example_only"
REPAIRED_TAXONOMY_CONDITIONED = "repaired_taxonomy_conditioned"
SKILL_ULTRA_COMPACT = "skill_ultra_compact"
SKILL_COMPACT = "skill_compact"
SKILL_MEDIUM = "skill_medium"
SKILL_VERBOSE = "skill_verbose"
GENERATED_DOCS_VERBOSE = "generated_docs_verbose"
RAW_DOCS_FULL = "raw_docs_full"
SKILL_PROMPT_COMPACT_DEFAULT = "skill_prompt_compact_default"
SKILL_PROMPT_BOUNDARY_FIRST = "skill_prompt_boundary_first"
SKILL_PROMPT_EXAMPLE_RICH = "skill_prompt_example_rich"
SKILL_PROMPT_SAFETY_AWARE = "skill_prompt_safety_aware"
SKILL_PROMPT_VERBOSE_DOCS = "skill_prompt_verbose_docs"

RELIABILITY_CONDITIONS = [
    RAW_MCP,
    SCHEMA_ONLY,
    DOCS_ONLY,
    NAIVE_SKILL,
    VALIDATED_SKILL,
    REPAIRED_SKILL,
    GATED_SKILL,
]

HISTORICAL_CONDITIONS = [
    "retrieved_docs",
    "retrieved_candidates",
    "retrieved_memory",
    GENERATED_SKILL_BASE,
    AUTOSKILL_BASE,
]

CONDITION_ORDER = [
    RAW_MCP,
    SCHEMA_ONLY,
    DOCS_ONLY,
    PROMPT_ONLY_CAREFUL_TOOL_USE,
    RAW_SCHEMA_PLUS_EXAMPLES,
    GENERATED_DOCS_NO_VALIDATION,
    GENERIC_VALIDATOR_NO_BEHAVIOR_TESTS,
    FULL_REGENERATION_REPAIR,
    CURATED_SCHEMA_REFERENCE,
    HUMAN_WRITTEN_SKILL_UPPER_BOUND,
    RETRIEVAL_TOOL_CARD,
    LARGER_MODEL_NAIVE_SKILL,
    ADVERSARIAL_DISTRACTOR_INVENTORY,
    NAIVE_SKILL_K1,
    MULTI_CANDIDATE_SKILL_K3_VALIDATION_SELECT,
    MULTI_CANDIDATE_SKILL_K3_BEHAVIOR_SELECT,
    MULTI_CANDIDATE_REPAIRED_GATED,
    REPAIRED_FULL_REGENERATION,
    REPAIRED_TARGETED_PATCH,
    REPAIRED_BOUNDARY_ONLY,
    REPAIRED_EXAMPLE_ONLY,
    REPAIRED_TAXONOMY_CONDITIONED,
    SKILL_ULTRA_COMPACT,
    SKILL_COMPACT,
    SKILL_MEDIUM,
    SKILL_VERBOSE,
    GENERATED_DOCS_VERBOSE,
    RAW_DOCS_FULL,
    SKILL_PROMPT_COMPACT_DEFAULT,
    SKILL_PROMPT_BOUNDARY_FIRST,
    SKILL_PROMPT_EXAMPLE_RICH,
    SKILL_PROMPT_SAFETY_AWARE,
    SKILL_PROMPT_VERBOSE_DOCS,
    "retrieved_docs",
    "retrieved_candidates",
    "retrieved_memory",
    NAIVE_SKILL,
    VALIDATED_SKILL,
    REPAIRED_SKILL,
    GATED_SKILL,
    RELIASKILL_CHALLENGER,
    RELIASKILL_V1_NO_CONTRACT_ROUTING,
    RELIASKILL_V1_NO_RUNTIME_GROUNDING,
    RELIASKILL_V1_NO_ACTION_GATE,
    RELIASKILL_V1_NO_SCHEMA_REPAIR,
    RELIASKILL_V1_NO_AMBIGUITY_ABSTENTION,
    RELIASKILL_V1_NO_CONTEXTUAL_GROUNDING,
    RELIASKILL_V1_NO_DOC_GROUNDING,
    RELIASKILL_V1_NO_DOC_CONSISTENCY_SHIELD,
    RELIASKILL_V1_NO_VERIFIER_REFINEMENT,
    RELIASKILL_V1_NO_IDENTIFIER_BINDING,
    RELIASKILL_V1_NO_CONTRACT_DECODER,
    RELIASKILL_V1_NO_CANDIDATE_VERIFICATION,
    RELIASKILL_V1_NO_CONTRACT_ARBITRATION,
    RELIASKILL_V1_NO_CONTRASTIVE_MEMORY,
    RELIASKILL_V1_NO_LEARNED_ROUTER_POLICY,
    RELIASKILL_V1_NO_CONTRASTIVE_CONTEXT,
    RELIASKILL_V1_NO_RETRIEVAL_MISS_RESCUE,
    RELIASKILL_V1_NO_DEPENDENCY_PLAN,
    GENERATED_SKILL_BASE,
    AUTOSKILL_BASE,
]


def clone_skill_as(skill: GeneratedSkill, baseline_name: str) -> GeneratedSkill:
    cloned = deepcopy(skill)
    cloned.baseline_name = baseline_name
    cloned.method_trace = [
        *cloned.method_trace,
        {"trace_type": "condition_alias", "condition": baseline_name},
    ]
    return cloned


def estimate_token_count(text_parts: Iterable[str]) -> int:
    text = " ".join(part for part in text_parts if part)
    return len(text.split())


def skill_token_count(skill: GeneratedSkill) -> int:
    return counted_skill_token_count(skill)


def build_docs_only_skill(tool: ToolIR) -> GeneratedSkill:
    snippets = tool.doc_snippets or [tool.tool_purpose or ""]
    summary = " ".join(snippet for snippet in snippets if snippet).strip()
    if not summary:
        summary = f"Documentation-only exposure for {tool.tool_name}."
    when_to_use = [
        f"Use `{tool.tool_name}` only when the request matches the provided MCP documentation.",
    ]
    when_not_to_use = [
        "Do not infer capabilities that are absent from the MCP documentation.",
        "Do not invent parameters beyond the schema.",
    ]
    return GeneratedSkill(
        baseline_name=DOCS_ONLY,
        skill_summary=summary,
        when_to_use=when_to_use,
        when_not_to_use=when_not_to_use,
        argument_template=build_argument_template(tool, include_optional=False, variant=0),
        examples=[],
        metadata={"artifact_kind": "docs_only"},
    )


def apply_skill_ablation(skill: GeneratedSkill, ablation_mode: str | None = None) -> GeneratedSkill:
    if not ablation_mode:
        return skill
    ablated = deepcopy(skill)
    if ablation_mode == "without_when_not":
        ablated.when_not_to_use = []
    elif ablation_mode == "without_examples":
        ablated.examples = []
    elif ablation_mode == "verbose":
        ablated.when_to_use = [
            *ablated.when_to_use,
            "Prefer this skill when it appears semantically related to the user request, while still checking the schema.",
            "Use the examples as guidance for mapping natural-language phrasing into arguments.",
            "Use the argument template as the canonical starting point for structured invocation.",
        ]
    elif ablation_mode == "compact":
        ablated.when_to_use = ablated.when_to_use[:2]
        ablated.when_not_to_use = ablated.when_not_to_use[:2]
        ablated.examples = ablated.examples[:1]
    else:
        raise ValueError(f"Unsupported skill ablation mode: {ablation_mode}")
    ablated.metadata = {**ablated.metadata, "ablation_mode": ablation_mode}
    return ablated

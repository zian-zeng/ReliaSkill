from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List

from autoskill.artifacts import clone_skill_as
from autoskill.compactness import build_compactness_variant
from autoskill.ir import GeneratedSkill, ToolIR
from autoskill.method import build_semantic_hints
from autoskill.prompt_templates import PROMPT_TEMPLATE_CONDITIONS, build_skill_from_prompt_template
from autoskill.raw_mcp import build_raw_mcp_skill
from autoskill.retrieval_baselines import build_retrieved_candidates_skill, build_retrieved_docs_skill
from autoskill.schema_only import build_schema_only_skill
from autoskill.templates import build_argument_template


PROMPT_ONLY_CAREFUL_TOOL_USE = "prompt_only_careful_tool_use"
RAW_SCHEMA_PLUS_EXAMPLES = "raw_schema_plus_examples"
GENERATED_DOCS_NO_VALIDATION = "generated_docs_no_validation"
GENERIC_VALIDATOR_NO_BEHAVIOR_TESTS = "generic_validator_no_behavior_tests"
FULL_REGENERATION_REPAIR = "full_regeneration_repair"
CURATED_SCHEMA_REFERENCE = "curated_schema_reference"
HUMAN_WRITTEN_SKILL_UPPER_BOUND = "human_written_skill_upper_bound"
GENERATED_SKILL_BASE = "generated_skill_base"
AUTOSKILL_BASE = "autoskill_base"
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
RELIASKILL_V1_NO_CONTRASTIVE_CONTEXT = "reliaskill_v1_no_contrastive_context"
RELIASKILL_V1_NO_RETRIEVAL_MISS_RESCUE = "reliaskill_v1_no_retrieval_miss_rescue"
RELIASKILL_V1_NO_DEPENDENCY_PLAN = "reliaskill_v1_no_dependency_plan"
RELIASKILL_V1_CONTRACT_ABLATIONS = [
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
    RELIASKILL_V1_NO_CONTRASTIVE_CONTEXT,
    RELIASKILL_V1_NO_RETRIEVAL_MISS_RESCUE,
    RELIASKILL_V1_NO_DEPENDENCY_PLAN,
]
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

REVIEWER_BASELINES = [
    PROMPT_ONLY_CAREFUL_TOOL_USE,
    RAW_SCHEMA_PLUS_EXAMPLES,
    GENERATED_DOCS_NO_VALIDATION,
    GENERIC_VALIDATOR_NO_BEHAVIOR_TESTS,
    FULL_REGENERATION_REPAIR,
    CURATED_SCHEMA_REFERENCE,
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
]

CONDITION_ALIASES = {
    HUMAN_WRITTEN_SKILL_UPPER_BOUND: CURATED_SCHEMA_REFERENCE,
    AUTOSKILL_BASE: GENERATED_SKILL_BASE,
    LEGACY_RELIASKILL_CHALLENGER: RELIASKILL_V1,
}


def is_reliaskill_v1_family(condition: str) -> bool:
    normalized = normalize_condition_name(condition)
    return normalized == RELIASKILL_V1 or normalized in RELIASKILL_V1_CONTRACT_ABLATIONS


def normalize_condition_name(condition: str) -> str:
    return CONDITION_ALIASES.get(condition, condition)


def normalize_condition_names(conditions: Iterable[str] | None) -> List[str] | None:
    if conditions is None:
        return None
    return [normalize_condition_name(condition) for condition in conditions]


def build_prompt_only_careful_tool_use(tool: ToolIR) -> GeneratedSkill:
    return GeneratedSkill(
        baseline_name=PROMPT_ONLY_CAREFUL_TOOL_USE,
        skill_summary="Use careful generic tool-use rules with the provided MCP schema, without generated tool-specific documentation.",
        when_to_use=[
            f"Consider `{tool.tool_name}` only if the user request directly matches the tool name and schema description.",
            "Before invoking, verify that every required argument can be grounded in the user request.",
        ],
        when_not_to_use=[
            "Do not call a tool for adjacent, underspecified, or merely keyword-overlapping requests.",
            "Do not invent argument values, optional fields, enum values, or hidden capabilities.",
        ],
        argument_template={},
        examples=[],
        metadata={"condition_family": "prompt_only"},
    )


def build_raw_schema_plus_examples(tool: ToolIR) -> GeneratedSkill:
    examples = []
    minimal = build_argument_template(tool, include_optional=False, variant=0)
    full = build_argument_template(tool, include_optional=True, variant=1)
    if minimal:
        examples.append({"scenario": f"Minimal schema-faithful call for {tool.tool_name}", "arguments": minimal})
    if full and full != minimal:
        examples.append({"scenario": f"Schema-faithful call with optional fields for {tool.tool_name}", "arguments": full})
    skill = build_raw_mcp_skill(tool)
    skill.baseline_name = RAW_SCHEMA_PLUS_EXAMPLES
    skill.examples = examples
    skill.argument_template = minimal
    skill.metadata = {"condition_family": "raw_schema_plus_examples"}
    return skill


def build_generated_docs_no_validation(tool: ToolIR, generated_skill: GeneratedSkill) -> GeneratedSkill:
    skill = clone_skill_as(generated_skill, GENERATED_DOCS_NO_VALIDATION)
    skill.when_not_to_use = []
    skill.metadata = {**skill.metadata, "condition_family": "generated_docs_no_validation", "validation_used": False}
    return skill


def build_generic_validator_no_behavior_tests(tool: ToolIR, generated_skill: GeneratedSkill) -> GeneratedSkill:
    skill = clone_skill_as(generated_skill, GENERIC_VALIDATOR_NO_BEHAVIOR_TESTS)
    skill.when_not_to_use = [
        "Do not invent unsupported arguments.",
        "Do not omit required fields when invoking this tool.",
        "Respect enum values and schema types.",
    ]
    skill.metadata = {**skill.metadata, "condition_family": "generic_validator_no_behavior_tests", "behavior_tests_used": False}
    return skill


def build_full_regeneration_repair(tool: ToolIR, generated_skill: GeneratedSkill) -> GeneratedSkill:
    regenerated = deepcopy(generated_skill)
    regenerated.baseline_name = FULL_REGENERATION_REPAIR
    regenerated.when_to_use = [
        f"Use `{tool.tool_name}` only for direct requests matching this tool's documented purpose.",
        "Regenerated repair pass: map only grounded user details into schema fields.",
        *regenerated.when_to_use[:2],
    ]
    regenerated.when_not_to_use = [
        "If a required argument is missing, ask for clarification instead of invoking.",
        "If the request is for an adjacent tool, abstain from this tool.",
        "If the request asks for read-only behavior, do not choose a write/delete/execute tool.",
        *regenerated.when_not_to_use[:3],
    ]
    regenerated.argument_template = build_argument_template(tool, include_optional=True, variant=2)
    regenerated.examples = [
        {
            "scenario": f"Full regenerated valid invocation for {tool.tool_name}",
            "arguments": build_argument_template(tool, include_optional=False, variant=2),
        }
    ]
    regenerated.method_trace = [
        *regenerated.method_trace,
        {"trace_type": "full_regeneration_repair", "repair_strategy": "regenerate_entire_skill"},
    ]
    regenerated.metadata = {**regenerated.metadata, "condition_family": "full_regeneration_repair"}
    return regenerated


def build_curated_schema_reference(tool: ToolIR) -> GeneratedSkill:
    curated = _curated_schema_reference_by_tool(tool)
    if curated is not None:
        return curated
    schema_skill = build_schema_only_skill(tool)
    schema_skill.baseline_name = CURATED_SCHEMA_REFERENCE
    schema_skill.when_to_use = [
        f"Use `{tool.tool_name}` for direct, fully specified requests matching the schema.",
        "Treat this as the schema-reference fallback for tools outside the manually curated filesystem subset.",
        *schema_skill.when_to_use,
    ]
    schema_skill.when_not_to_use = [
        "Do not use for adjacent tools, missing required inputs, or unsafe side-effect mismatches.",
        *schema_skill.when_not_to_use,
    ]
    schema_skill.metadata = {
        "condition_family": CURATED_SCHEMA_REFERENCE,
        "curated": False,
        "source": "schema_only_fallback",
        "legacy_condition_alias": HUMAN_WRITTEN_SKILL_UPPER_BOUND,
    }
    return schema_skill


def build_human_written_skill_upper_bound(tool: ToolIR) -> GeneratedSkill:
    return build_curated_schema_reference(tool)


def build_retrieval_tool_card(tool: ToolIR, tools: Dict[str, ToolIR]) -> GeneratedSkill:
    docs = build_retrieved_docs_skill(tool)
    candidates = build_retrieved_candidates_skill(tool, tools=tools)
    card = clone_skill_as(docs, RETRIEVAL_TOOL_CARD)
    candidate_names = [candidate.tool_name for candidate in _nearest_tools(tool, tools, limit=3)]
    card.skill_summary = f"Retrieved tool card for {tool.tool_name}. {tool.tool_purpose or ''}".strip()
    card.when_to_use = [
        *docs.when_to_use,
        f"Neighboring tools to compare before invocation: {', '.join(candidate_names) if candidate_names else 'none'}.",
    ]
    card.when_not_to_use = [
        *docs.when_not_to_use,
        *candidates.when_not_to_use[:2],
        "Do not use this tool when a retrieved neighboring tool is a closer semantic match.",
    ]
    card.metadata = {"condition_family": "retrieval_tool_card", "candidate_tools": candidate_names}
    return card


def build_larger_model_naive_skill(generated_skill: GeneratedSkill) -> GeneratedSkill:
    skill = clone_skill_as(generated_skill, LARGER_MODEL_NAIVE_SKILL)
    skill.skill_summary = f"Larger-model naive draft: {skill.skill_summary}"
    skill.when_to_use = [
        "Use this as a one-shot larger-model skill draft without validation or repair.",
        *skill.when_to_use,
    ]
    skill.metadata = {**skill.metadata, "condition_family": "larger_model_naive_skill", "larger_model_proxy": True}
    return skill


def build_adversarial_distractor_inventory(tool: ToolIR, tools: Dict[str, ToolIR]) -> GeneratedSkill:
    skill = build_schema_only_skill(tool)
    skill.baseline_name = ADVERSARIAL_DISTRACTOR_INVENTORY
    distractors = _nearest_tools(tool, tools, limit=5)
    names = [item.tool_name for item in distractors]
    skill.semantic_hints = build_semantic_hints(tool)
    skill.when_not_to_use = [
        *skill.when_not_to_use,
        f"Adversarial distractor inventory: compare against {', '.join(names) if names else 'no close distractors'}.",
        "Reject keyword-only matches when a distractor has the requested action boundary.",
        "Reject read/write, search/read, create/list, and delete/preview mismatches.",
    ]
    skill.metadata = {"condition_family": "adversarial_distractor_inventory", "distractor_tools": names}
    return skill


def build_naive_skill_k1(generated_skill: GeneratedSkill) -> GeneratedSkill:
    skill = clone_skill_as(generated_skill, NAIVE_SKILL_K1)
    skill.metadata = {**skill.metadata, "condition_family": NAIVE_SKILL_K1, "candidate_k": 1}
    return skill


def build_multi_candidate_validation_select(generated_skill: GeneratedSkill) -> GeneratedSkill:
    skill = clone_skill_as(generated_skill, MULTI_CANDIDATE_SKILL_K3_VALIDATION_SELECT)
    skill.when_to_use = [
        *skill.when_to_use,
        "Selected from three low-compute candidate skills by structural validation and schema faithfulness.",
    ]
    skill.metadata = {**skill.metadata, "condition_family": MULTI_CANDIDATE_SKILL_K3_VALIDATION_SELECT, "candidate_k": 3, "selection_policy": "best_validation_only"}
    return skill


def build_multi_candidate_behavior_select(generated_skill: GeneratedSkill) -> GeneratedSkill:
    skill = clone_skill_as(generated_skill, MULTI_CANDIDATE_SKILL_K3_BEHAVIOR_SELECT)
    skill.when_to_use = [
        *skill.when_to_use,
        "Selected from three candidate skills using dev-only positive behavior controls.",
    ]
    skill.when_not_to_use = [
        *skill.when_not_to_use,
        "Selection also considers dev-only negative controls; do not over-trigger on adjacent or ambiguous requests.",
    ]
    skill.metadata = {**skill.metadata, "condition_family": MULTI_CANDIDATE_SKILL_K3_BEHAVIOR_SELECT, "candidate_k": 3, "selection_policy": "best_behavior_dev"}
    return skill


def build_multi_candidate_repaired_gated(generated_skill: GeneratedSkill) -> GeneratedSkill:
    skill = clone_skill_as(generated_skill, MULTI_CANDIDATE_REPAIRED_GATED)
    skill.when_to_use = [
        *skill.when_to_use,
        "Use only after selected candidate passes validation and behavior-aware reliability checks.",
    ]
    skill.when_not_to_use = [
        "If reliability gating rejects deployment, abstain from using this skill.",
        *skill.when_not_to_use,
    ]
    skill.metadata = {**skill.metadata, "condition_family": MULTI_CANDIDATE_REPAIRED_GATED, "candidate_k": 3, "selection_policy": "best_behavior_dev", "repair_and_gate": True}
    return skill


def build_repair_strategy_condition(generated_skill: GeneratedSkill, condition_name: str, strategy: str) -> GeneratedSkill:
    skill = clone_skill_as(generated_skill, condition_name)
    skill.when_to_use = [
        *skill.when_to_use,
        f"Repair ablation condition using `{strategy}` under the shared repair interface.",
    ]
    skill.metadata = {
        **skill.metadata,
        "condition_family": "repair_strategy_ablation",
        "repair_strategy": strategy,
        "test_controls_used_for_repair": False,
    }
    return skill


def build_compactness_condition(tool: ToolIR, generated_skill: GeneratedSkill, condition_name: str) -> GeneratedSkill:
    return build_compactness_variant(tool, generated_skill, condition_name)


def build_prompt_template_condition(tool: ToolIR, condition_name: str) -> GeneratedSkill:
    template_id = PROMPT_TEMPLATE_CONDITIONS[condition_name]
    return build_skill_from_prompt_template(tool, template_id, baseline_name=condition_name)


def build_reviewer_baseline_skills(tool: ToolIR, tools: Dict[str, ToolIR], generated_skill: GeneratedSkill) -> List[GeneratedSkill]:
    return [
        build_prompt_only_careful_tool_use(tool),
        build_raw_schema_plus_examples(tool),
        build_generated_docs_no_validation(tool, generated_skill),
        build_generic_validator_no_behavior_tests(tool, generated_skill),
        build_full_regeneration_repair(tool, generated_skill),
        build_curated_schema_reference(tool),
        build_retrieval_tool_card(tool, tools),
        build_larger_model_naive_skill(generated_skill),
        build_adversarial_distractor_inventory(tool, tools),
        build_naive_skill_k1(generated_skill),
        build_multi_candidate_validation_select(generated_skill),
        build_multi_candidate_behavior_select(generated_skill),
        build_multi_candidate_repaired_gated(generated_skill),
        build_repair_strategy_condition(generated_skill, REPAIRED_FULL_REGENERATION, "full_regeneration"),
        build_repair_strategy_condition(generated_skill, REPAIRED_TARGETED_PATCH, "targeted_section_patch"),
        build_repair_strategy_condition(generated_skill, REPAIRED_BOUNDARY_ONLY, "nonuse_boundary_patch"),
        build_repair_strategy_condition(generated_skill, REPAIRED_EXAMPLE_ONLY, "example_repair"),
        build_repair_strategy_condition(generated_skill, REPAIRED_TAXONOMY_CONDITIONED, "failure_taxonomy_repair"),
        build_compactness_condition(tool, generated_skill, SKILL_ULTRA_COMPACT),
        build_compactness_condition(tool, generated_skill, SKILL_COMPACT),
        build_compactness_condition(tool, generated_skill, SKILL_MEDIUM),
        build_compactness_condition(tool, generated_skill, SKILL_VERBOSE),
        build_compactness_condition(tool, generated_skill, GENERATED_DOCS_VERBOSE),
        build_compactness_condition(tool, generated_skill, RAW_DOCS_FULL),
        build_prompt_template_condition(tool, SKILL_PROMPT_COMPACT_DEFAULT),
        build_prompt_template_condition(tool, SKILL_PROMPT_BOUNDARY_FIRST),
        build_prompt_template_condition(tool, SKILL_PROMPT_EXAMPLE_RICH),
        build_prompt_template_condition(tool, SKILL_PROMPT_SAFETY_AWARE),
        build_prompt_template_condition(tool, SKILL_PROMPT_VERBOSE_DOCS),
    ]


def condition_prompt_text(tool: ToolIR, skill: GeneratedSkill) -> str:
    return "\n".join(
        [
            "ReliaSkill condition prompt",
            f"Condition: {skill.baseline_name}",
            f"Tool: {tool.tool_name}",
            f"Description: {tool.tool_purpose or ''}",
            "When to use:",
            *[f"- {line}" for line in skill.when_to_use],
            "When not to use:",
            *[f"- {line}" for line in skill.when_not_to_use],
            "Argument template:",
            str(skill.argument_template),
            "Examples:",
            str(skill.examples),
        ]
    )


def _curated_schema_reference_by_tool(tool: ToolIR) -> GeneratedSkill | None:
    name = tool.tool_name
    if name == "read_text_file":
        return GeneratedSkill(
            baseline_name=CURATED_SCHEMA_REFERENCE,
            skill_summary="Read a known text file, optionally limiting to the first or last N lines.",
            when_to_use=["Use when the user gives a concrete file path and asks to read or show text content."],
            when_not_to_use=["Do not use for searching unknown paths, writing files, listing directories, or binary/media reads."],
            argument_template={"path": "docs/example.md"},
            examples=[{"scenario": "Show the first lines of a known file.", "arguments": {"path": "docs/example.md", "head": 10}}],
            metadata={
                "condition_family": CURATED_SCHEMA_REFERENCE,
                "curated": True,
                "source": "manual_filesystem_curation",
                "legacy_condition_alias": HUMAN_WRITTEN_SKILL_UPPER_BOUND,
            },
        )
    if name == "write_file":
        return GeneratedSkill(
            baseline_name=CURATED_SCHEMA_REFERENCE,
            skill_summary="Write explicit text content to a specified file path.",
            when_to_use=["Use only when both destination path and content are provided or unambiguous."],
            when_not_to_use=["Do not use for search, read-only, preview-only, or missing-content requests."],
            argument_template={"path": "docs/out.txt", "content": "text"},
            examples=[{"scenario": "Save quoted content to a named file.", "arguments": {"path": "docs/out.txt", "content": "text"}}],
            metadata={
                "condition_family": CURATED_SCHEMA_REFERENCE,
                "curated": True,
                "source": "manual_filesystem_curation",
                "legacy_condition_alias": HUMAN_WRITTEN_SKILL_UPPER_BOUND,
            },
        )
    if name == "search_files":
        return GeneratedSkill(
            baseline_name=CURATED_SCHEMA_REFERENCE,
            skill_summary="Search under a directory for paths matching a glob pattern.",
            when_to_use=["Use when the user asks to find files and gives a search root or file pattern."],
            when_not_to_use=["Do not use when the exact path is already known or the user asks to read/write/list directly."],
            argument_template={"path": "docs", "pattern": "**/*.md"},
            examples=[{"scenario": "Find markdown files under docs.", "arguments": {"path": "docs", "pattern": "**/*.md"}}],
            semantic_hints={"pattern": {"markdown": "**/*.md", "python": "**/*.py", "json": "**/*.json"}},
            metadata={
                "condition_family": CURATED_SCHEMA_REFERENCE,
                "curated": True,
                "source": "manual_filesystem_curation",
                "legacy_condition_alias": HUMAN_WRITTEN_SKILL_UPPER_BOUND,
            },
        )
    if name == "list_directory":
        return GeneratedSkill(
            baseline_name=CURATED_SCHEMA_REFERENCE,
            skill_summary="List the contents of a known directory path.",
            when_to_use=["Use when the user asks to inspect or list a directory and provides the directory path."],
            when_not_to_use=["Do not use for recursive search, file reading, writing, or directory creation."],
            argument_template={"path": "docs"},
            examples=[{"scenario": "List the docs directory.", "arguments": {"path": "docs"}}],
            metadata={
                "condition_family": CURATED_SCHEMA_REFERENCE,
                "curated": True,
                "source": "manual_filesystem_curation",
                "legacy_condition_alias": HUMAN_WRITTEN_SKILL_UPPER_BOUND,
            },
        )
    if name == "create_directory":
        return GeneratedSkill(
            baseline_name=CURATED_SCHEMA_REFERENCE,
            skill_summary="Create or ensure a directory exists at a specified path.",
            when_to_use=["Use when the user explicitly asks to create or ensure a directory."],
            when_not_to_use=["Do not use for listing directory contents, searching files, reading files, or writing file content."],
            argument_template={"path": "docs/new-folder"},
            examples=[{"scenario": "Ensure an output directory exists.", "arguments": {"path": "docs/new-folder"}}],
            metadata={
                "condition_family": CURATED_SCHEMA_REFERENCE,
                "curated": True,
                "source": "manual_filesystem_curation",
                "legacy_condition_alias": HUMAN_WRITTEN_SKILL_UPPER_BOUND,
            },
        )
    return None


def _nearest_tools(tool: ToolIR, tools: Dict[str, ToolIR], limit: int = 3) -> List[ToolIR]:
    target_terms = _tool_terms(tool)
    scored = []
    for other in tools.values():
        if other.tool_name == tool.tool_name:
            continue
        overlap = len(target_terms.intersection(_tool_terms(other)))
        scored.append((overlap, other.tool_name, other))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [item[2] for item in scored[:limit]]


def _tool_terms(tool: ToolIR) -> set[str]:
    text = " ".join([tool.tool_name, tool.tool_purpose or "", " ".join(arg.name for arg in tool.arguments)])
    return {part.lower() for part in text.replace("_", " ").split() if len(part) > 2}

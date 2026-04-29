from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List

from autoskill.artifacts import clone_skill_as
from autoskill.ir import GeneratedSkill, ToolIR
from autoskill.method import build_semantic_hints
from autoskill.raw_mcp import build_raw_mcp_skill
from autoskill.retrieval_baselines import build_retrieved_candidates_skill, build_retrieved_docs_skill
from autoskill.schema_only import build_schema_only_skill
from autoskill.templates import build_argument_template


PROMPT_ONLY_CAREFUL_TOOL_USE = "prompt_only_careful_tool_use"
RAW_SCHEMA_PLUS_EXAMPLES = "raw_schema_plus_examples"
GENERATED_DOCS_NO_VALIDATION = "generated_docs_no_validation"
GENERIC_VALIDATOR_NO_BEHAVIOR_TESTS = "generic_validator_no_behavior_tests"
FULL_REGENERATION_REPAIR = "full_regeneration_repair"
HUMAN_WRITTEN_SKILL_UPPER_BOUND = "human_written_skill_upper_bound"
RETRIEVAL_TOOL_CARD = "retrieval_tool_card"
LARGER_MODEL_NAIVE_SKILL = "larger_model_naive_skill"
ADVERSARIAL_DISTRACTOR_INVENTORY = "adversarial_distractor_inventory"

REVIEWER_BASELINES = [
    PROMPT_ONLY_CAREFUL_TOOL_USE,
    RAW_SCHEMA_PLUS_EXAMPLES,
    GENERATED_DOCS_NO_VALIDATION,
    GENERIC_VALIDATOR_NO_BEHAVIOR_TESTS,
    FULL_REGENERATION_REPAIR,
    HUMAN_WRITTEN_SKILL_UPPER_BOUND,
    RETRIEVAL_TOOL_CARD,
    LARGER_MODEL_NAIVE_SKILL,
    ADVERSARIAL_DISTRACTOR_INVENTORY,
]


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


def build_human_written_skill_upper_bound(tool: ToolIR) -> GeneratedSkill:
    curated = _human_upper_bound_by_tool(tool)
    if curated is not None:
        return curated
    schema_skill = build_schema_only_skill(tool)
    schema_skill.baseline_name = HUMAN_WRITTEN_SKILL_UPPER_BOUND
    schema_skill.when_to_use = [
        f"Use `{tool.tool_name}` for direct, fully specified requests matching the schema.",
        "Treat this as a human-written upper-bound fallback for tools outside the curated subset.",
        *schema_skill.when_to_use,
    ]
    schema_skill.when_not_to_use = [
        "Do not use for adjacent tools, missing required inputs, or unsafe side-effect mismatches.",
        *schema_skill.when_not_to_use,
    ]
    schema_skill.metadata = {"condition_family": "human_written_skill_upper_bound", "curated": False}
    return schema_skill


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


def build_reviewer_baseline_skills(tool: ToolIR, tools: Dict[str, ToolIR], generated_skill: GeneratedSkill) -> List[GeneratedSkill]:
    return [
        build_prompt_only_careful_tool_use(tool),
        build_raw_schema_plus_examples(tool),
        build_generated_docs_no_validation(tool, generated_skill),
        build_generic_validator_no_behavior_tests(tool, generated_skill),
        build_full_regeneration_repair(tool, generated_skill),
        build_human_written_skill_upper_bound(tool),
        build_retrieval_tool_card(tool, tools),
        build_larger_model_naive_skill(generated_skill),
        build_adversarial_distractor_inventory(tool, tools),
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


def _human_upper_bound_by_tool(tool: ToolIR) -> GeneratedSkill | None:
    name = tool.tool_name
    if name == "read_text_file":
        return GeneratedSkill(
            baseline_name=HUMAN_WRITTEN_SKILL_UPPER_BOUND,
            skill_summary="Read a known text file, optionally limiting to the first or last N lines.",
            when_to_use=["Use when the user gives a concrete file path and asks to read or show text content."],
            when_not_to_use=["Do not use for searching unknown paths, writing files, listing directories, or binary/media reads."],
            argument_template={"path": "docs/example.md"},
            examples=[{"scenario": "Show the first lines of a known file.", "arguments": {"path": "docs/example.md", "head": 10}}],
            metadata={"condition_family": "human_written_skill_upper_bound", "curated": True},
        )
    if name == "write_file":
        return GeneratedSkill(
            baseline_name=HUMAN_WRITTEN_SKILL_UPPER_BOUND,
            skill_summary="Write explicit text content to a specified file path.",
            when_to_use=["Use only when both destination path and content are provided or unambiguous."],
            when_not_to_use=["Do not use for search, read-only, preview-only, or missing-content requests."],
            argument_template={"path": "docs/out.txt", "content": "text"},
            examples=[{"scenario": "Save quoted content to a named file.", "arguments": {"path": "docs/out.txt", "content": "text"}}],
            metadata={"condition_family": "human_written_skill_upper_bound", "curated": True},
        )
    if name == "search_files":
        return GeneratedSkill(
            baseline_name=HUMAN_WRITTEN_SKILL_UPPER_BOUND,
            skill_summary="Search under a directory for paths matching a glob pattern.",
            when_to_use=["Use when the user asks to find files and gives a search root or file pattern."],
            when_not_to_use=["Do not use when the exact path is already known or the user asks to read/write/list directly."],
            argument_template={"path": "docs", "pattern": "**/*.md"},
            examples=[{"scenario": "Find markdown files under docs.", "arguments": {"path": "docs", "pattern": "**/*.md"}}],
            semantic_hints={"pattern": {"markdown": "**/*.md", "python": "**/*.py", "json": "**/*.json"}},
            metadata={"condition_family": "human_written_skill_upper_bound", "curated": True},
        )
    if name == "list_directory":
        return GeneratedSkill(
            baseline_name=HUMAN_WRITTEN_SKILL_UPPER_BOUND,
            skill_summary="List the contents of a known directory path.",
            when_to_use=["Use when the user asks to inspect or list a directory and provides the directory path."],
            when_not_to_use=["Do not use for recursive search, file reading, writing, or directory creation."],
            argument_template={"path": "docs"},
            examples=[{"scenario": "List the docs directory.", "arguments": {"path": "docs"}}],
            metadata={"condition_family": "human_written_skill_upper_bound", "curated": True},
        )
    if name == "create_directory":
        return GeneratedSkill(
            baseline_name=HUMAN_WRITTEN_SKILL_UPPER_BOUND,
            skill_summary="Create or ensure a directory exists at a specified path.",
            when_to_use=["Use when the user explicitly asks to create or ensure a directory."],
            when_not_to_use=["Do not use for listing directory contents, searching files, reading files, or writing file content."],
            argument_template={"path": "docs/new-folder"},
            examples=[{"scenario": "Ensure an output directory exists.", "arguments": {"path": "docs/new-folder"}}],
            metadata={"condition_family": "human_written_skill_upper_bound", "curated": True},
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

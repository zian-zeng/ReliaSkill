from __future__ import annotations

from copy import deepcopy
from typing import Iterable

from autoskill.ir import GeneratedSkill, ToolIR
from autoskill.templates import build_argument_template


RAW_MCP = "raw_mcp"
SCHEMA_ONLY = "schema_only"
DOCS_ONLY = "docs_only"
NAIVE_SKILL = "naive_skill"
VALIDATED_SKILL = "validated_skill"
REPAIRED_SKILL = "repaired_skill"
GATED_SKILL = "gated_skill"

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
    "autoskill_base",
]

CONDITION_ORDER = [
    RAW_MCP,
    SCHEMA_ONLY,
    DOCS_ONLY,
    "retrieved_docs",
    "retrieved_candidates",
    "retrieved_memory",
    NAIVE_SKILL,
    VALIDATED_SKILL,
    REPAIRED_SKILL,
    GATED_SKILL,
    "autoskill_base",
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
    parts = [skill.skill_summary, *skill.when_to_use, *skill.when_not_to_use]
    for example in skill.examples:
        parts.append(str(example.get("scenario", "")))
        parts.append(str(example.get("arguments", "")))
    return estimate_token_count(parts)


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

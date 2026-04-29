from __future__ import annotations

import csv
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List

from autoskill.ir import GeneratedSkill, ToolIR
from autoskill.templates import build_argument_template
from autoskill.token_accounting import compactness_log_record, mean, skill_token_count


SKILL_LENGTH_VARIANTS: Dict[str, Dict[str, Any]] = {
    "skill_ultra_compact": {
        "label": "ultra_compact",
        "target_min_tokens": 100,
        "target_max_tokens": 150,
        "max_skill_tokens": 150,
        "max_examples": 0,
        "include_when_not_to_use": True,
        "include_failure_modes": False,
        "include_argument_template": True,
    },
    "skill_compact": {
        "label": "compact",
        "target_min_tokens": 200,
        "target_max_tokens": 300,
        "max_skill_tokens": 300,
        "max_examples": 1,
        "include_when_not_to_use": True,
        "include_failure_modes": True,
        "include_argument_template": True,
    },
    "skill_medium": {
        "label": "medium",
        "target_min_tokens": 400,
        "target_max_tokens": 600,
        "max_skill_tokens": 600,
        "max_examples": 2,
        "include_when_not_to_use": True,
        "include_failure_modes": True,
        "include_argument_template": True,
    },
    "skill_verbose": {
        "label": "verbose",
        "target_min_tokens": 800,
        "target_max_tokens": 1200,
        "max_skill_tokens": 1200,
        "max_examples": 5,
        "include_when_not_to_use": True,
        "include_failure_modes": True,
        "include_argument_template": True,
    },
    "generated_docs_verbose": {
        "label": "verbose",
        "target_min_tokens": 800,
        "target_max_tokens": 1200,
        "max_skill_tokens": 1200,
        "max_examples": 5,
        "include_when_not_to_use": True,
        "include_failure_modes": True,
        "include_argument_template": True,
        "generated_documentation_style": True,
    },
    "raw_docs_full": {
        "label": "raw_docs_full",
        "target_min_tokens": None,
        "target_max_tokens": None,
        "max_skill_tokens": None,
        "max_examples": 0,
        "include_when_not_to_use": False,
        "include_failure_modes": False,
        "include_argument_template": False,
        "use_full_docs": True,
    },
}


def build_compactness_variant(
    tool: ToolIR,
    base_skill: GeneratedSkill,
    condition: str,
    constraints: Dict[str, Any] | None = None,
) -> GeneratedSkill:
    if condition not in SKILL_LENGTH_VARIANTS:
        raise ValueError(f"Unsupported compactness condition: {condition}")
    config = {**SKILL_LENGTH_VARIANTS[condition], **(constraints or {})}
    if config.get("use_full_docs"):
        skill = _raw_docs_full_skill(tool, condition, config)
    else:
        skill = deepcopy(base_skill)
        skill.baseline_name = condition
        _apply_section_constraints(tool, skill, config)
        if config.get("generated_documentation_style"):
            _expand_generated_docs(tool, skill)
        elif config["label"] in {"medium", "verbose"}:
            _expand_structured_guidance(tool, skill, verbose=config["label"] == "verbose")
        _enforce_token_budget(skill, int(config["max_skill_tokens"]) if config.get("max_skill_tokens") else None)
    log = compactness_log_record(tool, skill, condition)
    skill.metadata = {
        **skill.metadata,
        "condition_family": "skill_compactness",
        "compactness_variant": config["label"],
        "max_skill_tokens": config.get("max_skill_tokens"),
        "target_min_tokens": config.get("target_min_tokens"),
        "target_max_tokens": config.get("target_max_tokens"),
        "max_examples": config.get("max_examples"),
        "include_when_not_to_use": bool(config.get("include_when_not_to_use")),
        "include_failure_modes": bool(config.get("include_failure_modes")),
        "include_argument_template": bool(config.get("include_argument_template")),
        "token_accounting": log,
    }
    skill.method_trace = [
        *skill.method_trace,
        {
            "trace_type": "compactness_variant",
            "condition": condition,
            "constraints": {
                "max_skill_tokens": config.get("max_skill_tokens"),
                "max_examples": config.get("max_examples"),
                "include_when_not_to_use": bool(config.get("include_when_not_to_use")),
                "include_failure_modes": bool(config.get("include_failure_modes")),
                "include_argument_template": bool(config.get("include_argument_template")),
            },
            "token_accounting": log,
        },
    ]
    return skill


def build_compactness_variants(
    tool: ToolIR,
    base_skill: GeneratedSkill,
    conditions: Iterable[str] | None = None,
    constraints_by_condition: Dict[str, Dict[str, Any]] | None = None,
) -> List[GeneratedSkill]:
    names = list(conditions or SKILL_LENGTH_VARIANTS)
    constraints_by_condition = constraints_by_condition or {}
    return [
        build_compactness_variant(tool, base_skill, name, constraints_by_condition.get(name))
        for name in names
    ]


def compactness_records_for_tool(tool: ToolIR, skills: Iterable[GeneratedSkill]) -> List[Dict[str, Any]]:
    records = []
    for skill in skills:
        record = compactness_log_record(tool, skill, skill.baseline_name)
        record.update(
            {
                "target_min_tokens": skill.metadata.get("target_min_tokens"),
                "target_max_tokens": skill.metadata.get("target_max_tokens"),
                "max_skill_tokens": skill.metadata.get("max_skill_tokens"),
            }
        )
        records.append(record)
    return records


def write_compactness_stats_csv(path: str | Path, records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = summarize_compactness_records(records)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "condition",
        "mean_skill_tokens",
        "mean_prompt_tokens",
        "expected_context_overhead",
        "num_skills",
        "avg_sections_present",
    ]
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in headers})
    return rows


def summarize_compactness_records(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault(str(record.get("condition") or ""), []).append(record)
    rows = []
    for condition in sorted(grouped):
        items = grouped[condition]
        rows.append(
            {
                "condition": condition,
                "mean_skill_tokens": mean(float(item.get("skill_token_count") or 0) for item in items),
                "mean_prompt_tokens": mean(float(item.get("prompt_token_count") or 0) for item in items),
                "expected_context_overhead": mean(float(item.get("total_representation_tokens") or 0) for item in items),
                "num_skills": len(items),
                "avg_sections_present": mean(len(item.get("sections_included") or []) for item in items),
            }
        )
    return rows


def _apply_section_constraints(tool: ToolIR, skill: GeneratedSkill, config: Dict[str, Any]) -> None:
    label = str(config["label"])
    skill.skill_summary = _summarize(tool, skill, max_words={"ultra_compact": 22, "compact": 42, "medium": 80, "verbose": 120}.get(label, 80))
    skill.when_to_use = _limit_lines(skill.when_to_use or [f"Use `{tool.tool_name}` for requests matching the tool schema."], {"ultra_compact": 2, "compact": 3, "medium": 6, "verbose": 10}.get(label, 6))
    if config.get("include_when_not_to_use"):
        boundaries = list(skill.when_not_to_use)
        if config.get("include_failure_modes"):
            boundaries.extend(_failure_mode_lines(tool))
        skill.when_not_to_use = _limit_lines(boundaries, {"ultra_compact": 1, "compact": 3, "medium": 6, "verbose": 12}.get(label, 6))
    else:
        skill.when_not_to_use = []
    if config.get("include_argument_template"):
        include_optional = label not in {"ultra_compact"}
        skill.argument_template = build_argument_template(tool, include_optional=include_optional, variant=0)
    else:
        skill.argument_template = {}
    skill.examples = list(skill.examples)[: int(config.get("max_examples") or 0)]


def _summarize(tool: ToolIR, skill: GeneratedSkill, max_words: int) -> str:
    text = skill.skill_summary or tool.tool_purpose or f"Use `{tool.tool_name}` for its documented MCP action."
    if not text.lower().startswith("use"):
        text = text.rstrip(".") + "."
    return _trim_words(text, max_words)


def _failure_mode_lines(tool: ToolIR) -> List[str]:
    lines = [
        "Do not invent missing required fields.",
        "Do not pass unsupported arguments or enum values.",
        "Prefer abstention for adjacent tools with similar names or arguments.",
    ]
    if tool.side_effect_hints or tool.safety_hints:
        lines.append("For side-effectful operations, require explicit user intent and reject preview-only or read-only mismatches.")
    return lines


def _expand_structured_guidance(tool: ToolIR, skill: GeneratedSkill, *, verbose: bool) -> None:
    arg_lines = []
    for arg in tool.arguments:
        pieces = [f"`{arg.name}` is {'required' if arg.required else 'optional'}", f"type={arg.type}"]
        if arg.enum:
            pieces.append(f"allowed={arg.enum}")
        if arg.description:
            pieces.append(arg.description)
        arg_lines.append("; ".join(str(piece) for piece in pieces) + ".")
    skill.when_to_use = _dedupe([*skill.when_to_use, *arg_lines[:8 if verbose else 4]])
    if verbose:
        skill.when_not_to_use = _dedupe([*skill.when_not_to_use, *tool.usage_warnings, *(tool.safety_hints or []), *(tool.side_effect_hints or [])])
        minimal = build_argument_template(tool, include_optional=False, variant=2)
        full = build_argument_template(tool, include_optional=True, variant=3)
        examples = list(skill.examples)
        if minimal:
            examples.append({"scenario": f"Required-field invocation for {tool.tool_name}", "arguments": minimal})
        if full and full != minimal:
            examples.append({"scenario": f"Invocation with optional controls for {tool.tool_name}", "arguments": full})
        skill.examples = examples[:5]


def _expand_generated_docs(tool: ToolIR, skill: GeneratedSkill) -> None:
    docs = tool.doc_snippets or [tool.tool_purpose or ""]
    skill.skill_summary = " ".join([skill.skill_summary, "Generated documentation view.", *docs]).strip()
    skill.when_to_use = _dedupe(
        [
            *skill.when_to_use,
            "Treat the schema as the source of truth for every invocation.",
            "Use documented argument descriptions to map user language into fields.",
            *[f"Documentation note: {snippet}" for snippet in docs[:6] if snippet],
        ]
    )
    _expand_structured_guidance(tool, skill, verbose=True)


def _raw_docs_full_skill(tool: ToolIR, condition: str, config: Dict[str, Any]) -> GeneratedSkill:
    docs = tool.doc_snippets or [tool.tool_purpose or f"No source documentation was available for {tool.tool_name}."]
    summary = "\n".join(snippet for snippet in docs if snippet).strip()
    if not summary:
        summary = f"Raw documentation exposure for {tool.tool_name}."
    return GeneratedSkill(
        baseline_name=condition,
        skill_summary=summary,
        when_to_use=[tool.tool_purpose or f"Refer to raw docs for {tool.tool_name}."],
        when_not_to_use=[],
        argument_template={},
        examples=[],
        metadata={
            "condition_family": "skill_compactness",
            "compactness_variant": config["label"],
            "raw_docs_full": True,
        },
    )


def _enforce_token_budget(skill: GeneratedSkill, max_tokens: int | None) -> None:
    if not max_tokens:
        return
    while skill_token_count(skill) > max_tokens and skill.examples:
        skill.examples = skill.examples[:-1]
    while skill_token_count(skill) > max_tokens and len(skill.when_not_to_use) > 1:
        skill.when_not_to_use = skill.when_not_to_use[:-1]
    while skill_token_count(skill) > max_tokens and len(skill.when_to_use) > 1:
        skill.when_to_use = skill.when_to_use[:-1]
    if skill_token_count(skill) > max_tokens:
        skill.skill_summary = _trim_words(skill.skill_summary, max(12, max_tokens // 3))
    if skill_token_count(skill) > max_tokens and skill.argument_template:
        skill.argument_template = {}


def _limit_lines(lines: Iterable[str], limit: int) -> List[str]:
    return _dedupe(lines)[: max(0, limit)]


def _dedupe(lines: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for line in lines:
        normalized = " ".join(str(line).split())
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def _trim_words(text: str, max_words: int) -> str:
    words = str(text or "").split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]).rstrip(".,") + "."

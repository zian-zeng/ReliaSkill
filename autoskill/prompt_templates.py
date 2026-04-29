from __future__ import annotations

import csv
import json
import re
from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from autoskill.ir import GeneratedSkill, ToolIR
from autoskill.templates import build_argument_template
from autoskill.token_accounting import skill_token_count
from autoskill.validator import validate_skill


@dataclass(frozen=True)
class PromptTemplateSpec:
    template_id: str
    template_family: str
    allowed_sections: List[str]
    max_tokens: int
    uses_dev_controls: bool = False
    uses_negative_controls: bool = False
    instruction: str = ""

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


PROMPT_TEMPLATE_SPECS: Dict[str, PromptTemplateSpec] = {
    "compact_default": PromptTemplateSpec(
        template_id="compact_default",
        template_family="compact",
        allowed_sections=["skill_summary", "when_to_use", "when_not_to_use", "argument_template", "examples"],
        max_tokens=300,
        instruction="Produce a compact schema-faithful skill for routine tool selection.",
    ),
    "boundary_first": PromptTemplateSpec(
        template_id="boundary_first",
        template_family="boundary",
        allowed_sections=["skill_summary", "when_to_use", "when_not_to_use", "argument_template", "examples"],
        max_tokens=350,
        instruction="Emphasize crisp when-not-to-use boundaries before examples.",
    ),
    "schema_faithful_minimal": PromptTemplateSpec(
        template_id="schema_faithful_minimal",
        template_family="minimal",
        allowed_sections=["skill_summary", "when_to_use", "when_not_to_use", "argument_template", "examples"],
        max_tokens=180,
        instruction="Use the fewest tokens possible while preserving required schema information.",
    ),
    "example_rich": PromptTemplateSpec(
        template_id="example_rich",
        template_family="examples",
        allowed_sections=["skill_summary", "when_to_use", "when_not_to_use", "argument_template", "examples"],
        max_tokens=500,
        instruction="Include multiple schema-faithful examples covering required and optional fields.",
    ),
    "safety_side_effect_aware": PromptTemplateSpec(
        template_id="safety_side_effect_aware",
        template_family="safety",
        allowed_sections=["skill_summary", "when_to_use", "when_not_to_use", "argument_template", "examples"],
        max_tokens=400,
        instruction="Preserve side-effect warnings and reject unsafe read/write or destructive mismatches.",
    ),
    "negative_control_aware_dev_only": PromptTemplateSpec(
        template_id="negative_control_aware_dev_only",
        template_family="dev_controls",
        allowed_sections=["skill_summary", "when_to_use", "when_not_to_use", "argument_template", "examples"],
        max_tokens=450,
        uses_dev_controls=True,
        uses_negative_controls=True,
        instruction="Use dev-only negative control categories to sharpen abstention boundaries.",
    ),
    "verbose_docs_style": PromptTemplateSpec(
        template_id="verbose_docs_style",
        template_family="verbose_docs",
        allowed_sections=["skill_summary", "when_to_use", "when_not_to_use", "argument_template", "examples", "documentation_notes"],
        max_tokens=1200,
        instruction="Produce a verbose documentation-style baseline while remaining schema-faithful.",
    ),
}

PROMPT_TEMPLATE_CONDITIONS = {
    "skill_prompt_compact_default": "compact_default",
    "skill_prompt_boundary_first": "boundary_first",
    "skill_prompt_example_rich": "example_rich",
    "skill_prompt_safety_aware": "safety_side_effect_aware",
    "skill_prompt_verbose_docs": "verbose_docs_style",
}


def get_prompt_template(template_id: str) -> PromptTemplateSpec:
    if template_id not in PROMPT_TEMPLATE_SPECS:
        raise ValueError(f"Unknown prompt template id: {template_id}")
    return PROMPT_TEMPLATE_SPECS[template_id]


def build_generation_prompt_from_template(
    tool: ToolIR,
    template_id: str = "compact_default",
    *,
    dev_controls: Sequence[Dict[str, Any]] | None = None,
) -> str:
    spec = get_prompt_template(template_id)
    payload = {
        "prompt_template_metadata": spec.model_dump(),
        "toolir": tool.model_dump(),
    }
    if spec.uses_dev_controls:
        payload["dev_control_metadata"] = _safe_dev_control_metadata(dev_controls or [])
    rules = [
        "Return exactly one JSON object.",
        "Required keys: skill_summary, when_to_use, when_not_to_use, argument_template, examples.",
        "Do not invent arguments, capabilities, outputs, enum values, authentication modes, or side effects.",
        "Use only schema-supported parameter names in argument_template and examples.",
        "Include when-to-use guidance and when-not-to-use guidance.",
        "Include an argument_template object.",
        "Include 1-3 examples unless the schema has no arguments.",
        "Each example must be an object with scenario and arguments.",
        "Preserve side-effect warnings and safety hints.",
        "Do not use test controls or evaluation labels.",
    ]
    return "\n".join(
        [
            "You generate compact, deployable ReliaSkill artifacts from MCP-like ToolIR.",
            f"Template id: {spec.template_id}",
            f"Template family: {spec.template_family}",
            f"Token budget: {spec.max_tokens}",
            f"Template instruction: {spec.instruction}",
            "Rules:",
            *[f"- {rule}" for rule in rules],
            "Allowed sections:",
            json.dumps(spec.allowed_sections, ensure_ascii=False),
            "Generation payload:",
            json.dumps(payload, indent=2, ensure_ascii=False),
        ]
    )


def parse_generated_skill_output(
    raw_text: str,
    *,
    template_id: str,
    tool: ToolIR,
    baseline_name: str = "autoskill_base",
) -> GeneratedSkill:
    metadata = _base_metadata(template_id)
    metadata["raw_generation_text"] = raw_text
    try:
        data = _extract_json_object(raw_text)
        skill = _skill_from_data(data, baseline_name=baseline_name)
        _validate_skill_structure(data)
        metadata["parse_ok"] = True
        metadata["parse_error"] = None
    except Exception as exc:
        skill = GeneratedSkill(
            baseline_name=baseline_name,
            skill_summary="",
            when_to_use=[],
            when_not_to_use=[],
            argument_template={},
            examples=[],
        )
        metadata["parse_ok"] = False
        metadata["parse_error"] = f"{type(exc).__name__}: {exc}"
    skill.metadata = {**skill.metadata, **metadata}
    skill.method_trace = [
        *skill.method_trace,
        {
            "trace_type": "prompt_template_generation",
            "template_id": template_id,
            "parse_ok": skill.metadata.get("parse_ok"),
            "parse_error": skill.metadata.get("parse_error"),
            "test_controls_used": False,
        },
    ]
    if not skill.metadata.get("parse_ok"):
        return skill
    report = validate_skill(tool, skill)
    skill.metadata["prompt_template_validation_valid"] = report.valid
    skill.metadata["prompt_template_validation_errors"] = [
        issue.model_dump() for issue in report.issues if issue.severity == "error"
    ]
    return skill


def build_skill_from_prompt_template(
    tool: ToolIR,
    template_id: str,
    *,
    dev_controls: Sequence[Dict[str, Any]] | None = None,
    baseline_name: str = "autoskill_base",
) -> GeneratedSkill:
    spec = get_prompt_template(template_id)
    skill = _heuristic_skill_for_template(tool, spec, baseline_name=baseline_name)
    skill.metadata = {
        **skill.metadata,
        **_base_metadata(template_id),
        "parse_ok": True,
        "parse_error": None,
        "heuristic_prompt_template_renderer": True,
        "uses_dev_controls": spec.uses_dev_controls,
        "uses_negative_controls": spec.uses_negative_controls,
        "dev_control_categories_seen": _negative_categories(dev_controls or []) if spec.uses_dev_controls else [],
    }
    skill.method_trace = [
        *skill.method_trace,
        {
            "trace_type": "prompt_template_generation",
            "template_id": template_id,
            "template_family": spec.template_family,
            "uses_dev_controls": spec.uses_dev_controls,
            "uses_negative_controls": spec.uses_negative_controls,
            "test_controls_used": False,
        },
    ]
    _enforce_template_budget(skill, spec.max_tokens)
    return skill


def generate_prompt_template_skills(
    tools: Sequence[ToolIR],
    *,
    template_ids: Sequence[str],
    output_root: str | Path = "generated_skills",
    stats_path: str | Path = "outputs/tables/prompt_template_generation_stats.csv",
    dev_controls: Sequence[Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    root = Path(output_root)
    for template_id in template_ids:
        spec = get_prompt_template(template_id)
        template_dir = root / template_id
        template_dir.mkdir(parents=True, exist_ok=True)
        for tool in tools:
            skill = build_skill_from_prompt_template(tool, template_id, dev_controls=dev_controls)
            report = validate_skill(tool, skill)
            payload = {
                "tool_id": tool.tool_name,
                "template_id": template_id,
                "template_metadata": spec.model_dump(),
                "prompt": build_generation_prompt_from_template(tool, template_id, dev_controls=dev_controls),
                "skill": skill.model_dump(),
                "validation": report.model_dump(),
                "raw_text": skill.metadata.get("raw_generation_text"),
                "parse_error": skill.metadata.get("parse_error"),
            }
            (template_dir / f"{_slug(tool.tool_name)}.json").write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            records.append(_generation_record(tool, skill, report, spec))
    write_prompt_template_stats(stats_path, records)
    return records


def write_prompt_template_stats(path: str | Path, records: Sequence[Dict[str, Any]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "template_id",
        "template_family",
        "num_tools",
        "parse_failures",
        "validation_failures",
        "mean_skill_tokens",
        "mean_examples",
        "mean_when_not_to_use",
        "uses_dev_controls",
        "uses_negative_controls",
    ]
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault(str(record["template_id"]), []).append(record)
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for template_id in sorted(grouped):
            items = grouped[template_id]
            spec = get_prompt_template(template_id)
            writer.writerow(
                {
                    "template_id": template_id,
                    "template_family": spec.template_family,
                    "num_tools": len(items),
                    "parse_failures": sum(1 for item in items if not item["parse_ok"]),
                    "validation_failures": sum(1 for item in items if not item["validation_valid"]),
                    "mean_skill_tokens": _mean(float(item["skill_token_count"]) for item in items),
                    "mean_examples": _mean(float(item["examples_count"]) for item in items),
                    "mean_when_not_to_use": _mean(float(item["when_not_to_use_count"]) for item in items),
                    "uses_dev_controls": spec.uses_dev_controls,
                    "uses_negative_controls": spec.uses_negative_controls,
                }
            )


def _heuristic_skill_for_template(tool: ToolIR, spec: PromptTemplateSpec, *, baseline_name: str) -> GeneratedSkill:
    purpose = tool.tool_purpose or f"`{tool.tool_name}` performs its documented MCP action."
    required = [arg.name for arg in tool.arguments if arg.required]
    optional = [arg.name for arg in tool.arguments if not arg.required]
    summary = purpose.rstrip(".") + "."
    when_to_use = [
        f"Use `{tool.tool_name}` only when the request directly matches this tool's documented purpose.",
        _required_line(required),
    ]
    if optional:
        when_to_use.append("Use optional fields only when the user provides or implies them clearly.")
    when_not_to_use = [
        "Do not invent missing required fields.",
        "Do not pass unsupported arguments or enum values.",
        "Do not use this tool for adjacent, merely keyword-overlapping requests.",
    ]
    examples = _schema_faithful_examples(tool, limit=2)
    argument_template = build_argument_template(tool, include_optional=True, variant=0)

    if spec.template_id == "boundary_first":
        when_not_to_use = [
            "First decide whether abstention is safer than calling this tool.",
            "Do not use for adjacent tools with similar names, descriptions, or arguments.",
            "Do not use for read/write, search/fetch, create/update, delete/preview, or explain/execute mismatches.",
            *when_not_to_use,
        ]
    elif spec.template_id == "schema_faithful_minimal":
        summary = _trim_words(summary, 24)
        when_to_use = [f"Use `{tool.tool_name}` for direct requests matching its schema.", _required_line(required)]
        when_not_to_use = ["Do not use for missing required fields, unsupported arguments, adjacent tools, or unsafe side-effect mismatches."]
        examples = examples[:1]
        argument_template = build_argument_template(tool, include_optional=False, variant=0)
    elif spec.template_id == "example_rich":
        examples = _schema_faithful_examples(tool, limit=3)
        when_to_use.append("Use the examples as schema-faithful patterns, not as labels or hidden gold outputs.")
    elif spec.template_id == "safety_side_effect_aware":
        when_not_to_use = [
            "Preserve all side-effect and safety warnings from the schema.",
            "Do not perform write/delete/execute behavior unless the user explicitly requests that action.",
            "Do not satisfy read-only, preview-only, or explanation requests with side-effectful calls.",
            *when_not_to_use,
            *tool.safety_hints,
            *tool.side_effect_hints,
        ]
    elif spec.template_id == "negative_control_aware_dev_only":
        when_not_to_use = [
            *when_not_to_use,
            "Dev-only negative-control guidance: abstain on out-of-domain, explanation-only, missing-info, and near-miss requests.",
        ]
    elif spec.template_id == "verbose_docs_style":
        summary = " ".join([summary, *tool.doc_snippets[:5]])
        when_to_use = [*when_to_use, *[f"Documentation note: {snippet}" for snippet in tool.doc_snippets[:4]]]
        when_not_to_use = [*when_not_to_use, *tool.usage_warnings, *tool.safety_hints, *tool.side_effect_hints]
        examples = _schema_faithful_examples(tool, limit=3)

    return GeneratedSkill(
        baseline_name=baseline_name,
        skill_summary=summary,
        when_to_use=_dedupe(when_to_use),
        when_not_to_use=_dedupe(when_not_to_use),
        argument_template=argument_template,
        examples=examples,
    )


def _schema_faithful_examples(tool: ToolIR, *, limit: int) -> List[Dict[str, Any]]:
    examples = []
    for variant, include_optional in enumerate([False, True, True]):
        args = build_argument_template(tool, include_optional=include_optional, variant=variant)
        if args or not tool.arguments:
            examples.append(
                {
                    "scenario": f"Schema-faithful {tool.tool_name} invocation {variant + 1}",
                    "arguments": args,
                }
            )
        if len(examples) >= limit:
            break
    return examples[:limit]


def _extract_json_object(raw_text: str) -> Dict[str, Any]:
    try:
        value = json.loads(raw_text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if not match:
            raise
        value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("generated output must be a JSON object")
    return value


def _skill_from_data(data: Dict[str, Any], *, baseline_name: str) -> GeneratedSkill:
    return GeneratedSkill(
        baseline_name=baseline_name,
        skill_summary=str(data.get("skill_summary") or ""),
        when_to_use=list(data.get("when_to_use") or []),
        when_not_to_use=list(data.get("when_not_to_use") or []),
        argument_template=dict(data.get("argument_template") or {}),
        examples=list(data.get("examples") or []),
    )


def _validate_skill_structure(data: Dict[str, Any]) -> None:
    required_types = {
        "skill_summary": str,
        "when_to_use": list,
        "when_not_to_use": list,
        "argument_template": dict,
        "examples": list,
    }
    missing = [key for key in required_types if key not in data]
    if missing:
        raise ValueError(f"missing required skill fields: {missing}")
    for key, expected_type in required_types.items():
        if not isinstance(data.get(key), expected_type):
            raise TypeError(f"{key} must be {expected_type.__name__}")
    for idx, example in enumerate(data["examples"]):
        if not isinstance(example, dict) or not isinstance(example.get("arguments"), dict):
            raise TypeError(f"examples[{idx}] must contain an arguments object")


def _base_metadata(template_id: str) -> Dict[str, Any]:
    spec = get_prompt_template(template_id)
    return {
        "template_id": spec.template_id,
        "template_family": spec.template_family,
        "allowed_sections": list(spec.allowed_sections),
        "max_tokens": spec.max_tokens,
        "uses_dev_controls": spec.uses_dev_controls,
        "uses_negative_controls": spec.uses_negative_controls,
    }


def _safe_dev_control_metadata(records: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sanitized = []
    for record in records:
        if str(record.get("split") or "dev") != "dev":
            continue
        sanitized.append(
            {
                "difficulty": record.get("difficulty"),
                "control_family": record.get("control_family"),
                "negative_category": record.get("negative_category"),
                "expected_failure_mode": record.get("expected_failure_mode"),
                "should_trigger": record.get("should_trigger"),
            }
        )
    return sanitized[:20]


def _negative_categories(records: Sequence[Dict[str, Any]]) -> List[str]:
    categories = {
        str(record.get("negative_category"))
        for record in records
        if str(record.get("split") or "dev") == "dev" and record.get("negative_category")
    }
    return sorted(categories)


def _generation_record(tool: ToolIR, skill: GeneratedSkill, report: Any, spec: PromptTemplateSpec) -> Dict[str, Any]:
    return {
        "template_id": spec.template_id,
        "template_family": spec.template_family,
        "tool_name": tool.tool_name,
        "parse_ok": bool(skill.metadata.get("parse_ok")),
        "parse_error": skill.metadata.get("parse_error") or "",
        "validation_valid": report.valid,
        "validation_error_count": sum(1 for issue in report.issues if issue.severity == "error"),
        "skill_token_count": skill_token_count(skill),
        "examples_count": len(skill.examples),
        "when_not_to_use_count": len(skill.when_not_to_use),
        "uses_dev_controls": spec.uses_dev_controls,
        "uses_negative_controls": spec.uses_negative_controls,
    }


def _enforce_template_budget(skill: GeneratedSkill, max_tokens: int) -> None:
    while skill_token_count(skill) > max_tokens and len(skill.examples) > 1:
        skill.examples = skill.examples[:-1]
    while skill_token_count(skill) > max_tokens and len(skill.when_to_use) > 2:
        skill.when_to_use = skill.when_to_use[:-1]
    while skill_token_count(skill) > max_tokens and len(skill.when_not_to_use) > 3:
        skill.when_not_to_use = skill.when_not_to_use[:-1]
    if skill_token_count(skill) > max_tokens:
        skill.skill_summary = _trim_words(skill.skill_summary, max(16, max_tokens // 4))


def _required_line(required: Sequence[str]) -> str:
    if not required:
        return "This tool has no required arguments."
    return "Required fields must be grounded in the user request: " + ", ".join(f"`{name}`" for name in required) + "."


def _trim_words(text: str, limit: int) -> str:
    words = str(text or "").split()
    if len(words) <= limit:
        return " ".join(words)
    return " ".join(words[:limit]).rstrip(".,") + "."


def _dedupe(lines: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for line in lines:
        normalized = " ".join(str(line).split())
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def _mean(values: Iterable[float]) -> float:
    items = list(values)
    return round(sum(items) / len(items), 4) if items else 0.0


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return slug[:120] or "tool"

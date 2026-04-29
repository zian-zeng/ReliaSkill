from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List

from autoskill.ir import GeneratedSkill, ToolIR


def count_text_tokens(text: str) -> Dict[str, Any]:
    try:
        import tiktoken  # type: ignore

        encoding = tiktoken.get_encoding("cl100k_base")
        return {"count": len(encoding.encode(text or "")), "source": "tiktoken_cl100k_base"}
    except Exception:
        tokens = re.findall(r"\w+|[^\w\s]", text or "", flags=re.UNICODE)
        return {"count": len(tokens), "source": "regex_approx"}


def skill_to_sections(skill: GeneratedSkill) -> Dict[str, str]:
    sections: Dict[str, str] = {}
    if skill.skill_summary:
        sections["summary"] = skill.skill_summary
    if skill.when_to_use:
        sections["when_to_use"] = "\n".join(skill.when_to_use)
    if skill.when_not_to_use:
        sections["when_not_to_use"] = "\n".join(skill.when_not_to_use)
    if skill.argument_template:
        sections["argument_template"] = json.dumps(skill.argument_template, sort_keys=True, ensure_ascii=False)
    if skill.examples:
        sections["examples"] = json.dumps(skill.examples, sort_keys=True, ensure_ascii=False)
    if skill.semantic_hints:
        sections["semantic_hints"] = json.dumps(skill.semantic_hints, sort_keys=True, ensure_ascii=False)
    return sections


def skill_to_text(skill: GeneratedSkill) -> str:
    sections = skill_to_sections(skill)
    return "\n".join(f"{name}:\n{value}" for name, value in sections.items())


def prompt_representation_text(tool: ToolIR, skill: GeneratedSkill) -> str:
    schema = json.dumps(tool.input_schema_raw or {}, sort_keys=True, ensure_ascii=False)
    docs = "\n".join(tool.doc_snippets or [])
    return "\n".join([tool.tool_name, tool.tool_purpose or "", docs, schema, skill_to_text(skill)])


def skill_token_count(skill: GeneratedSkill) -> int:
    return int(count_text_tokens(skill_to_text(skill))["count"])


def compactness_log_record(tool: ToolIR, skill: GeneratedSkill, condition: str) -> Dict[str, Any]:
    skill_tokens = count_text_tokens(skill_to_text(skill))
    prompt_tokens = count_text_tokens(prompt_representation_text(tool, skill))
    sections = skill_to_sections(skill)
    return {
        "tool_name": tool.tool_name,
        "condition": condition,
        "skill_token_count": skill_tokens["count"],
        "prompt_token_count": prompt_tokens["count"],
        "total_representation_tokens": skill_tokens["count"] + prompt_tokens["count"],
        "tokenizer_source": skill_tokens["source"],
        "prompt_tokenizer_source": prompt_tokens["source"],
        "sections_included": sorted(sections),
        "examples_count": len(skill.examples),
        "nonuse_boundary_count": len(skill.when_not_to_use),
    }


def mean(values: Iterable[float]) -> float:
    items = [float(value) for value in values]
    return round(sum(items) / len(items), 4) if items else 0.0

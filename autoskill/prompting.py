from __future__ import annotations

import json

from autoskill.ir import GeneratedSkill, ToolIR
from autoskill.prompt_templates import build_generation_prompt_from_template


def build_generation_prompt(tool: ToolIR, template_id: str = "compact_default") -> str:
    return build_generation_prompt_from_template(tool, template_id=template_id)


def build_prediction_prompt(tool: ToolIR, skill: GeneratedSkill, user_request: str) -> str:
    return (
        "You are selecting arguments for a single MCP tool call.\n"
        "Return valid JSON only with a single top-level object named `arguments`.\n"
        "Use only fields allowed by the schema.\n"
        "Include all required arguments.\n"
        "Do not include explanations.\n\n"
        f"Tool name: {tool.tool_name}\n"
        f"Tool description: {tool.tool_purpose or ''}\n"
        f"Skill condition: {skill.baseline_name}\n"
        f"Skill summary: {skill.skill_summary}\n"
        f"When to use: {json.dumps(skill.when_to_use, ensure_ascii=False)}\n"
        f"When not to use: {json.dumps(skill.when_not_to_use, ensure_ascii=False)}\n"
        f"Argument template: {json.dumps(skill.argument_template, ensure_ascii=False)}\n"
        f"Examples: {json.dumps(skill.examples, ensure_ascii=False)}\n"
        f"Schema: {json.dumps(tool.input_schema_raw, ensure_ascii=False)}\n"
        f"User request: {user_request}\n"
    )

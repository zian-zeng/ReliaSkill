from __future__ import annotations

import json

from autoskill.ir import GeneratedSkill, ToolIR


def build_generation_prompt(tool: ToolIR) -> str:
    tool_payload = tool.model_dump()
    return (
        "You are generating an agent-ready skill package from a normalized MCP tool schema.\n"
        "Return valid JSON with keys: skill_summary, when_to_use, when_not_to_use, argument_template, examples.\n"
        "Rules:\n"
        "1. Use only argument names that appear in the provided schema.\n"
        "2. Do not invent parameters, outputs, or enum values.\n"
        "3. argument_template must be a JSON object.\n"
        "4. examples must be a list of objects with scenario and arguments.\n"
        "5. Each example.arguments must be valid JSON and include all required fields.\n"
        "6. Keep the summary concise and concrete.\n\n"
        "ToolIR:\n"
        f"{json.dumps(tool_payload, indent=2, ensure_ascii=False)}"
    )


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

from __future__ import annotations

import json

from autoskill.ir import GeneratedSkill, ToolIR


def render_exposure(tool: ToolIR, skill: GeneratedSkill) -> str:
    lines = [
        f"Tool: {tool.tool_name}",
        f"Server: {tool.server_name or 'unknown'}",
        f"Condition: {skill.baseline_name}",
        "",
        "Description:",
        tool.tool_purpose or "",
        "",
        "Input schema:",
        json.dumps(tool.input_schema_raw, indent=2, ensure_ascii=False),
        "",
    ]

    if skill.baseline_name != "raw_mcp":
        lines.extend(
            [
                "Skill summary:",
                skill.skill_summary,
                "",
                "When to use:",
                *[f"- {line}" for line in skill.when_to_use],
                "",
                "When not to use:",
                *[f"- {line}" for line in skill.when_not_to_use],
                "",
                "Argument template:",
                json.dumps(skill.argument_template, indent=2, ensure_ascii=False),
                "",
                "Examples:",
            ]
        )
        if skill.examples:
            for example in skill.examples:
                lines.append(f"- Scenario: {example.get('scenario', '')}")
                lines.append(json.dumps(example.get("arguments", {}), indent=2, ensure_ascii=False))
        else:
            lines.append("- None")

    return "\n".join(lines).strip() + "\n"

from __future__ import annotations

from autoskill.ir import GeneratedSkill, ToolIR


def build_raw_mcp_skill(tool: ToolIR) -> GeneratedSkill:
    summary = tool.tool_purpose or f"Raw MCP exposure for {tool.tool_name}."
    when_to_use = [
        "Use the original MCP description and schema directly without added guidance.",
        "Consult schema.normalized.json for the exact argument contract.",
    ]
    if tool.auth_or_env_notes:
        when_to_use.append(tool.auth_or_env_notes)

    when_not_to_use = [
        "Do not assume example calls or usage heuristics beyond the original schema.",
    ]

    return GeneratedSkill(
        baseline_name="raw_mcp",
        skill_summary=summary,
        when_to_use=when_to_use,
        when_not_to_use=when_not_to_use,
        argument_template={},
        examples=[],
    )

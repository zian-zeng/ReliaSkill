from __future__ import annotations

from autoskill.ir import GeneratedSkill, ToolIR
from autoskill.templates import build_argument_template


def build_schema_only_skill(tool: ToolIR) -> GeneratedSkill:
    template = build_argument_template(tool, include_optional=True, variant=0)
    minimal_example = build_argument_template(tool, include_optional=False, variant=0)
    full_example = build_argument_template(tool, include_optional=True, variant=1)

    when_to_use = [
        "Use this normalized schema view when you need a deterministic rendering of the MCP input contract.",
        "Follow the exact field names, required markers, defaults, and enums shown below.",
    ]
    when_not_to_use = [
        "Do not treat this baseline as semantic guidance beyond the original schema.",
    ]

    examples = []
    if minimal_example:
        examples.append(
            {
                "scenario": f"Minimal valid call for {tool.tool_name}",
                "arguments": minimal_example,
            }
        )
    if full_example and full_example != minimal_example:
        examples.append(
            {
                "scenario": f"Schema-aligned full call for {tool.tool_name}",
                "arguments": full_example,
            }
        )

    return GeneratedSkill(
        baseline_name="schema_only",
        skill_summary=tool.tool_purpose or f"Deterministic schema rendering for {tool.tool_name}.",
        when_to_use=when_to_use,
        when_not_to_use=when_not_to_use,
        argument_template=template,
        examples=examples,
    )

from __future__ import annotations

import json

from autoskill.conditions import is_reliaskill_v1_family
from autoskill.contracts import build_contract_counterexamples, compile_skill_contract
from autoskill.doc_evidence import build_doc_grounding_evidence
from autoskill.ir import GeneratedSkill, ToolIR
from autoskill.templates import build_schema_contract_lines


SCHEMA_CONTRACT_EXPOSURE_CONDITIONS = {
    "reliaskill_v1",
    "reliaskill_challenger_v1",
    "skill_prompt_boundary_first",
}


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
        schema_contract = skill.metadata.get("schema_contract")
        if (
            (not isinstance(schema_contract, list) or not schema_contract)
            and (
                skill.baseline_name in SCHEMA_CONTRACT_EXPOSURE_CONDITIONS
                or is_reliaskill_v1_family(skill.baseline_name)
            )
        ):
            schema_contract = build_schema_contract_lines(tool)
        if isinstance(schema_contract, list) and schema_contract:
            lines.extend(
                [
                    "Schema contract:",
                    *[f"- {line}" for line in schema_contract if isinstance(line, str)],
                    "",
                ]
            )
        if is_reliaskill_v1_family(skill.baseline_name):
            executable_contract = skill.metadata.get("executable_contract")
            if not isinstance(executable_contract, dict):
                executable_contract = compile_skill_contract(tool, skill).model_dump()
            counterexamples = skill.metadata.get("contract_counterexamples")
            if not isinstance(counterexamples, list):
                counterexamples = build_contract_counterexamples(tool, skill)
            lines.extend(
                [
                    "Executable contract:",
                    json.dumps(
                        {
                            "proof_obligations": executable_contract.get("proof_obligations", []),
                            "repair_policy": executable_contract.get("repair_policy", []),
                            "abstention_policy": executable_contract.get("abstention_policy", []),
                        },
                        indent=2,
                        ensure_ascii=False,
                    ),
                    "",
                    "Contract counterexamples:",
                    json.dumps(counterexamples[:4], indent=2, ensure_ascii=False),
                    "",
                ]
            )
            if not _contract_ablation_disabled(skill, "disable_doc_grounding"):
                doc_evidence = skill.metadata.get("doc_grounding_evidence")
                enable_doc_shield = not _contract_ablation_disabled(skill, "disable_doc_consistency_shield")
                if not isinstance(doc_evidence, dict) or not enable_doc_shield:
                    doc_evidence = build_doc_grounding_evidence(
                        tool,
                        enable_consistency_shield=enable_doc_shield,
                    )
                lines.extend(
                    [
                        "Documentation-grounded contract evidence:",
                        json.dumps(doc_evidence, indent=2, ensure_ascii=False),
                        "",
                    ]
                )
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


def _contract_ablation_disabled(skill: GeneratedSkill, flag: str) -> bool:
    flags = skill.metadata.get("contract_ablation_flags") if isinstance(skill.metadata, dict) else None
    return bool(isinstance(flags, dict) and flags.get(flag) is True)

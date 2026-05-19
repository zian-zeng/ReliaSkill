from __future__ import annotations

import json

from autoskill.conditions import is_reliaskill_v1_family
from autoskill.contracts import build_contract_counterexamples, compile_skill_contract
from autoskill.ir import GeneratedSkill, ToolIR
from autoskill.prompt_templates import build_generation_prompt_from_template
from autoskill.templates import build_schema_contract_lines


BOUNDARY_FIRST_RUNTIME_CONDITIONS = {
    "skill_prompt_boundary_first",
}


def build_generation_prompt(tool: ToolIR, template_id: str = "compact_default") -> str:
    return build_generation_prompt_from_template(tool, template_id=template_id)


def build_prediction_prompt(tool: ToolIR, skill: GeneratedSkill, user_request: str) -> str:
    guidance = _runtime_guidance(tool, skill)
    return (
        "You are selecting arguments for a single MCP tool call.\n"
        "Return valid JSON only with keys `should_call`, `arguments`, and `abstention_reason`.\n"
        "Set `should_call` to false and return an empty `arguments` object when the request is out of scope, asks for planning only, lacks required information, or conflicts with the tool boundary.\n"
        "Use only fields allowed by the schema.\n"
        "When `should_call` is true, include all required arguments.\n"
        "Do not include explanations.\n\n"
        f"Tool name: {tool.tool_name}\n"
        f"Tool description: {tool.tool_purpose or ''}\n"
        f"Skill condition: {skill.baseline_name}\n"
        f"Skill summary: {skill.skill_summary}\n"
        f"{guidance}"
        f"Argument template: {json.dumps(skill.argument_template, ensure_ascii=False)}\n"
        f"Examples: {json.dumps(skill.examples, ensure_ascii=False)}\n"
        f"Schema: {json.dumps(tool.input_schema_raw, ensure_ascii=False)}\n"
        f"User request: {user_request}\n"
    )


def _runtime_guidance(tool: ToolIR, skill: GeneratedSkill) -> str:
    reliaskill_family = is_reliaskill_v1_family(skill.baseline_name)
    if skill.baseline_name in BOUNDARY_FIRST_RUNTIME_CONDITIONS or reliaskill_family:
        contract_lines = skill.metadata.get("schema_contract")
        if not isinstance(contract_lines, list) or not all(isinstance(line, str) for line in contract_lines):
            contract_lines = build_schema_contract_lines(tool)
        method_label = "ReliaSkill v1" if reliaskill_family else "ReliaSkill boundary-first"
        executable_contract = skill.metadata.get("executable_contract")
        if not isinstance(executable_contract, dict) and reliaskill_family:
            executable_contract = compile_skill_contract(tool, skill).model_dump()
        proof_obligations = executable_contract.get("proof_obligations", []) if isinstance(executable_contract, dict) else []
        counterexamples = skill.metadata.get("contract_counterexamples")
        if not isinstance(counterexamples, list) and reliaskill_family:
            counterexamples = build_contract_counterexamples(tool, skill)
        proof_line = (
            f"{method_label} proof obligations: {json.dumps(proof_obligations, ensure_ascii=False)}\n"
            if proof_obligations and reliaskill_family
            else ""
        )
        counterexample_line = (
            f"{method_label} contract counterexamples: {json.dumps(counterexamples[:4], ensure_ascii=False)}\n"
            if isinstance(counterexamples, list) and counterexamples and reliaskill_family
            else ""
        )
        return (
            f"{method_label} schema contract: obey this compact argument contract before using examples.\n"
            f"Call contract: {json.dumps(contract_lines, ensure_ascii=False)}\n"
            f"{proof_line}"
            f"{counterexample_line}"
            f"{method_label} boundary gate: check non-use rules before considering use rules. "
            "If any non-use rule applies, set `should_call` to false.\n"
            "Before returning `should_call=true`, verify required fields are grounded and the argument object satisfies the call contract.\n"
            f"When not to use: {json.dumps(skill.when_not_to_use, ensure_ascii=False)}\n"
            f"When to use: {json.dumps(skill.when_to_use, ensure_ascii=False)}\n"
        )
    return (
        f"When to use: {json.dumps(skill.when_to_use, ensure_ascii=False)}\n"
        f"When not to use: {json.dumps(skill.when_not_to_use, ensure_ascii=False)}\n"
    )

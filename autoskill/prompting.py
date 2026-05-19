from __future__ import annotations

import json

from autoskill.conditions import is_reliaskill_v1_family
from autoskill.contract_inference import build_contract_proof_state, contract_state_payload
from autoskill.contracts import build_contract_counterexamples, compile_skill_contract
from autoskill.doc_evidence import build_doc_grounding_evidence, build_request_conditioned_doc_evidence, render_doc_grounding_evidence
from autoskill.ir import GeneratedSkill, ToolIR
from autoskill.prompt_templates import build_generation_prompt_from_template
from autoskill.templates import build_schema_contract_lines


BOUNDARY_FIRST_RUNTIME_CONDITIONS = {
    "skill_prompt_boundary_first",
}


def build_generation_prompt(tool: ToolIR, template_id: str = "compact_default") -> str:
    return build_generation_prompt_from_template(tool, template_id=template_id)


def build_prediction_prompt(tool: ToolIR, skill: GeneratedSkill, user_request: str) -> str:
    guidance = _runtime_guidance(tool, skill, user_request=user_request)
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


def _runtime_guidance(tool: ToolIR, skill: GeneratedSkill, *, user_request: str | None = None) -> str:
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
        doc_evidence_text = ""
        if reliaskill_family and not _contract_ablation_disabled(skill, "disable_doc_grounding"):
            doc_evidence = skill.metadata.get("doc_grounding_evidence")
            enable_doc_shield = not _contract_ablation_disabled(skill, "disable_doc_consistency_shield")
            if user_request:
                doc_evidence = build_request_conditioned_doc_evidence(
                    tool,
                    user_request,
                    enable_consistency_shield=enable_doc_shield,
                )
            elif not isinstance(doc_evidence, dict) or not enable_doc_shield:
                doc_evidence = build_doc_grounding_evidence(tool, enable_consistency_shield=enable_doc_shield)
            doc_evidence_text = render_doc_grounding_evidence(doc_evidence, max_chars=3200) if isinstance(doc_evidence, dict) else ""
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
        doc_evidence_line = (
            f"{method_label} documentation-grounded evidence: {doc_evidence_text}\n"
            "Use this evidence to interpret tool purpose and argument meanings; the executable contract remains authoritative for validity and abstention.\n"
            if doc_evidence_text and reliaskill_family
            else ""
        )
        request_contract_line = ""
        if reliaskill_family and user_request:
            request_state = build_contract_proof_state(tool, skill, user_request)
            request_contract_line = (
                f"{method_label} request-contract proof state: {json.dumps(contract_state_payload(request_state), ensure_ascii=False)}\n"
                "Use this proof state as the decision ledger: do not call when required arguments are missing or a blocking reason applies.\n"
            )
        contrastive_line = ""
        if reliaskill_family and not _contract_ablation_disabled(skill, "disable_contrastive_contract_context"):
            contrastive_candidates = skill.metadata.get("contrastive_contract_candidates")
            if isinstance(contrastive_candidates, list) and contrastive_candidates:
                contrastive_line = (
                    f"{method_label} contrastive candidate proof states: {json.dumps(contrastive_candidates[:4], ensure_ascii=False)}\n"
                    "Use the contrastive states as proof-margin evidence for adjacent-tool mistakes: if this tool is blocked and a named or higher-margin viable candidate exists, return `should_call=false` so the verifier/router can redirect to that candidate.\n"
                )
        plan_line = ""
        if reliaskill_family and not _contract_ablation_disabled(skill, "disable_dependency_plan_prompting"):
            contract_plan = skill.metadata.get("contract_plan_context")
            if isinstance(contract_plan, dict) and contract_plan:
                plan_line = (
                    f"{method_label} dependency contract plan: {json.dumps(contract_plan, ensure_ascii=False)}\n"
                    "Use this plan only as dependency evidence: call the current tool when its required inputs are grounded now; otherwise abstain until dependencies are bound by prior observations.\n"
                )
        return (
            f"{method_label} schema contract: obey this compact argument contract before using examples.\n"
            f"Call contract: {json.dumps(contract_lines, ensure_ascii=False)}\n"
            f"{proof_line}"
            f"{counterexample_line}"
            f"{doc_evidence_line}"
            f"{request_contract_line}"
            f"{contrastive_line}"
            f"{plan_line}"
            f"{method_label} proof-margin decision policy: call only when the current tool's proof decision is `call`; repair only grounded argument violations; otherwise abstain or preserve the explicitly named alternative tool boundary.\n"
            f"{method_label} boundary gate: check non-use rules before considering use rules. "
            "If any non-use rule applies, set `should_call` to false.\n"
            "Before returning `should_call=true`, verify required fields are grounded and the argument object satisfies the call contract.\n"
            "Include optional arguments only when they are explicitly grounded in the request or context; otherwise omit them.\n"
            f"When not to use: {json.dumps(skill.when_not_to_use, ensure_ascii=False)}\n"
            f"When to use: {json.dumps(skill.when_to_use, ensure_ascii=False)}\n"
        )
    return (
        f"When to use: {json.dumps(skill.when_to_use, ensure_ascii=False)}\n"
        f"When not to use: {json.dumps(skill.when_not_to_use, ensure_ascii=False)}\n"
    )


def _contract_ablation_disabled(skill: GeneratedSkill, flag: str) -> bool:
    flags = skill.metadata.get("contract_ablation_flags") if isinstance(skill.metadata, dict) else None
    return bool(isinstance(flags, dict) and flags.get(flag) is True)

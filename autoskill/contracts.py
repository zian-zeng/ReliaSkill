from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any, Dict, Iterable, List

from autoskill.ir import ArgumentIR, GeneratedSkill, ToolIR
from autoskill.schema_utils import normalize_schema_node, schema_type


ACTION_FAMILIES: Dict[str, set[str]] = {
    "search": {"search", "find", "lookup", "look", "query", "match", "filter"},
    "read": {"read", "open", "show", "view", "preview", "list", "get", "fetch", "retrieve"},
    "create": {"create", "add", "insert", "new", "draft", "schedule"},
    "update": {"update", "edit", "modify", "patch", "change", "append", "write", "save"},
    "delete": {"delete", "remove", "clear", "drop"},
    "send": {"send", "post", "publish", "transfer", "email", "notify"},
    "compute": {"calculate", "compute", "convert", "estimate", "derive", "solve", "rank"},
}


@dataclass
class SkillContract:
    tool_name: str
    allowed_arguments: List[str]
    required_arguments: List[str]
    required_paths: List[str]
    action_families: List[str]
    side_effect_class: str
    proof_obligations: List[str]
    repair_policy: List[str]
    abstention_policy: List[str]
    ambiguity_keys: List[str] = field(default_factory=list)
    adaptive_policy: Dict[str, Any] = field(default_factory=dict)

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ContractEvaluation:
    contract: SkillContract
    satisfied: bool
    routing_bonus: int
    grounded_required_args: List[str]
    missing_required_args: List[str]
    request_actions: List[str]
    tool_actions: List[str]
    negated_actions: List[str]
    blocking_reasons: List[str]
    proof_obligations: List[Dict[str, Any]]
    argument_issues: List[str] = field(default_factory=list)
    grounding_sources: List[str] = field(default_factory=list)
    policy_features: Dict[str, float] = field(default_factory=dict)
    policy_decision: Dict[str, Any] = field(default_factory=dict)

    def model_dump(self) -> Dict[str, Any]:
        data = asdict(self)
        data["contract"] = self.contract.model_dump()
        return data


@dataclass
class ContractPlanStep:
    step_id: str
    tool_name: str
    dependency_step_ids: List[str]
    grounded_required_args: List[str]
    input_bindings: Dict[str, Any] = field(default_factory=dict)
    proof_obligations: List[Dict[str, Any]] = field(default_factory=list)

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ContractPlan:
    satisfied: bool
    steps: List[ContractPlanStep]
    unresolved_tools: List[Dict[str, Any]]
    blocking_reasons: List[str]

    def model_dump(self) -> Dict[str, Any]:
        return {
            "satisfied": self.satisfied,
            "steps": [step.model_dump() for step in self.steps],
            "unresolved_tools": self.unresolved_tools,
            "blocking_reasons": self.blocking_reasons,
        }


def compile_skill_contract(tool: ToolIR, skill: GeneratedSkill | None = None) -> SkillContract:
    """Compile a tool/skill pair into the explicit obligations ReliaSkill v1 must prove."""
    allowed = [arg.name for arg in tool.arguments]
    required = [arg.name for arg in tool.arguments if arg.required]
    required_paths: List[str] = []
    for arg in tool.arguments:
        if arg.required:
            required_paths.append(arg.name)
        required_paths.extend(_nested_required_paths(arg))

    contract_text = " ".join(
        [
            tool.tool_name,
            tool.tool_purpose or "",
            *(tool.side_effect_hints or []),
            *(tool.safety_hints or []),
            *((skill.when_to_use if skill else []) or []),
        ]
    )
    actions = sorted(_action_families_for_text(contract_text))
    ambiguity_keys = sorted(_discriminator_tokens(tool))
    adaptive_policy = _contract_policy(skill)
    return SkillContract(
        tool_name=tool.tool_name,
        allowed_arguments=allowed,
        required_arguments=required,
        required_paths=sorted(set(required_paths)),
        action_families=actions,
        side_effect_class=_side_effect_class(tool, actions),
        proof_obligations=[
            "intent_supported_or_nonconflicting",
            "side_effect_allowed_by_request",
            "all_required_arguments_grounded",
            "arguments_schema_valid",
            "optional_arguments_grounded_or_pruned",
            "ambiguity_resolved_or_abstained",
            "multi_step_dependencies_bound_or_unresolved",
            "execution_feedback_repaired_or_aborted",
        ],
        repair_policy=[
            "lift_flat_nested_fields",
            "coerce_safe_scalar_types",
            "canonicalize_enum_case",
            "replace_invalid_required_with_grounded_value",
            "fill_missing_required_from_grounded_request",
            "drop_ungrounded_optional_arguments",
            "bind_missing_inputs_to_prior_contract_outputs",
        ],
        abstention_policy=[
            "missing_required_information",
            "action_intent_conflict",
            "schema_contract_violation",
            "ambiguous_same_contract_tools",
            "explicit_no_tool_or_planning_request",
        ],
        ambiguity_keys=ambiguity_keys,
        adaptive_policy=adaptive_policy,
    )


def build_contract_counterexamples(tool: ToolIR, skill: GeneratedSkill | None = None, *, limit: int = 4) -> List[Dict[str, str]]:
    """Build deterministic negative cases tied to the compiled contract obligations."""
    contract = compile_skill_contract(tool, skill)
    examples: List[Dict[str, str]] = []
    if contract.required_arguments:
        missing = contract.required_arguments[0]
        examples.append(
            {
                "case_type": "missing_required_information",
                "user_request": f"Use {tool.tool_name} after I provide the {missing} later.",
                "expected_behavior": "abstain",
                "violated_obligation": "all_required_arguments_grounded",
            }
        )
    if contract.side_effect_class in {"write", "delete", "external_send"}:
        examples.append(
            {
                "case_type": "side_effect_conflict",
                "user_request": f"Read or preview the relevant item; do not create, update, delete, send, or modify anything with {tool.tool_name}.",
                "expected_behavior": "abstain",
                "violated_obligation": "side_effect_allowed_by_request",
            }
        )
    elif contract.side_effect_class == "read":
        examples.append(
            {
                "case_type": "read_write_conflict",
                "user_request": f"Create or update the item instead of reading it with {tool.tool_name}.",
                "expected_behavior": "abstain",
                "violated_obligation": "intent_supported_or_nonconflicting",
            }
        )
    examples.append(
        {
            "case_type": "unsupported_argument",
            "user_request": f"Call {tool.tool_name} with an unsupported debug field and any invented defaults.",
            "expected_behavior": "abstain",
            "violated_obligation": "arguments_schema_valid",
        }
    )
    if contract.ambiguity_keys:
        examples.append(
            {
                "case_type": "ambiguous_domain",
                "user_request": "Use the matching tool for the request without naming the domain or disambiguating the intended capability.",
                "expected_behavior": "abstain_or_ask_clarification",
                "violated_obligation": "ambiguity_resolved_or_abstained",
            }
        )
    return examples[:limit]


def evaluate_skill_contract(
    tool: ToolIR,
    skill: GeneratedSkill,
    request: str,
    *,
    arguments: Dict[str, Any] | None = None,
    grounding_context: Any | None = None,
) -> ContractEvaluation:
    """Evaluate a request and optional argument object against an executable skill contract."""
    contract = compile_skill_contract(tool, skill)
    grounding_text, grounding_sources = _compose_grounding_text(request, grounding_context)
    grounded: List[str] = []
    missing: List[str] = []
    grounding_proofs: List[Dict[str, Any]] = []
    for arg in tool.arguments:
        if not arg.required:
            continue
        result = _required_arg_grounding(grounding_text, arg, tool)
        if not result["grounded"] and arguments is not None and arg.name in arguments and _value_grounded(arg.name, arguments[arg.name], grounding_text):
            result = {"grounded": True, "evidence": "argument_value_in_request"}
        grounding_proofs.append(
            {
                "obligation": f"ground_required:{arg.name}",
                "status": "satisfied" if result["grounded"] else "failed",
                "evidence": result["evidence"],
            }
        )
        if result["grounded"]:
            grounded.append(arg.name)
        else:
            missing.append(arg.name)

    action_request = _strip_unrelated_without_using_clause(request, tool)
    request_actions = sorted(_action_families_for_text(action_request) - _negated_action_families_for_text(action_request))
    negated_actions = sorted(_negated_action_families_for_text(action_request))
    tool_actions = sorted(_action_families_for_tool(tool))
    action_conflict = _action_intent_conflict(set(request_actions), set(tool_actions), set(negated_actions))
    if action_conflict and not any(arg.required for arg in tool.arguments) and _request_declares_no_arguments_text(action_request):
        action_conflict = False
    argument_issues = _argument_contract_issues(tool, grounding_text, arguments) if arguments is not None else []

    blocking_reasons: List[str] = []
    if missing:
        blocking_reasons.append("missing_required_arguments")
    if action_conflict:
        blocking_reasons.append("action_intent_conflict")
    if argument_issues:
        blocking_reasons.append("argument_contract_violation")
    policy_features = _contract_policy_features(
        contract=contract,
        grounded=grounded,
        missing=missing,
        action_conflict=action_conflict,
        argument_issues=argument_issues,
    )
    policy_decision = _apply_contract_policy(contract.adaptive_policy, blocking_reasons, policy_features)
    if not policy_decision["allow_call"] and "adaptive_policy_reject" not in blocking_reasons:
        blocking_reasons.append("adaptive_policy_reject")

    routing_bonus = (3 * len(grounded)) - (4 * len(missing))
    if len([arg for arg in tool.arguments if arg.required]) >= 3 and len(missing) >= len([arg for arg in tool.arguments if arg.required]) - 1:
        routing_bonus -= 3
    routing_bonus += _side_effect_fit_bonus(action_request, tool)
    routing_bonus += _action_intent_fit_bonus(action_request, tool)

    proof_obligations = [
        {
            "obligation": "intent_supported_or_nonconflicting",
            "status": "failed" if action_conflict else "satisfied",
            "evidence": {
                "request_actions": request_actions,
                "tool_actions": tool_actions,
                "negated_actions": negated_actions,
            },
        },
        {
            "obligation": "side_effect_allowed_by_request",
            "status": "failed" if action_conflict else "satisfied",
            "evidence": {"side_effect_class": contract.side_effect_class},
        },
        {
            "obligation": "all_required_arguments_grounded",
            "status": "failed" if missing else "satisfied",
            "evidence": {"grounded": grounded, "missing": missing},
        },
        {
            "obligation": "arguments_schema_valid",
            "status": "not_evaluated" if arguments is None else ("failed" if argument_issues else "satisfied"),
            "evidence": {"issues": argument_issues},
        },
        {
            "obligation": "optional_arguments_grounded_or_pruned",
            "status": "not_evaluated" if arguments is None else "satisfied",
            "evidence": {},
        },
        {
            "obligation": "adaptive_policy_acceptance",
            "status": "satisfied" if policy_decision["allow_call"] else "failed",
            "evidence": policy_decision,
        },
        {
            "obligation": "multi_step_dependencies_bound_or_unresolved",
            "status": "not_evaluated",
            "evidence": {},
        },
        *grounding_proofs,
    ]
    return ContractEvaluation(
        contract=contract,
        satisfied=bool(policy_decision["allow_call"]) and not [reason for reason in blocking_reasons if reason != "adaptive_policy_reject"],
        routing_bonus=routing_bonus,
        grounded_required_args=grounded,
        missing_required_args=missing,
        request_actions=request_actions,
        tool_actions=tool_actions,
        negated_actions=negated_actions,
        blocking_reasons=blocking_reasons,
        proof_obligations=proof_obligations,
        argument_issues=argument_issues,
        grounding_sources=grounding_sources,
        policy_features=policy_features,
        policy_decision=policy_decision,
    )


def compose_contract_plan(
    request: str,
    tools: Dict[str, ToolIR],
    skills: Dict[str, GeneratedSkill],
    *,
    grounding_context: Any | None = None,
    max_steps: int = 3,
) -> ContractPlan:
    """Compose a small proof-carrying tool plan from executable contracts.

    The planner is intentionally conservative: it only creates dependencies when
    an earlier satisfied tool advertises an output affordance that can ground a
    later tool's missing required argument.
    """
    evaluations = {
        name: evaluate_skill_contract(tool, skills[name], request, grounding_context=grounding_context)
        for name, tool in tools.items()
        if name in skills
    }
    ordered = sorted(
        evaluations.items(),
        key=lambda item: (
            0 if item[1].satisfied else 1,
            -item[1].routing_bonus,
            item[0],
        ),
    )
    steps: List[ContractPlanStep] = []
    provided: Dict[str, str] = {}
    unresolved: List[Dict[str, Any]] = []

    for tool_name, evaluation in ordered:
        if len(steps) >= max_steps:
            break
        tool = tools[tool_name]
        if evaluation.satisfied:
            step_id = f"step_{len(steps) + 1}"
            steps.append(
                ContractPlanStep(
                    step_id=step_id,
                    tool_name=tool_name,
                    dependency_step_ids=[],
                    grounded_required_args=evaluation.grounded_required_args,
                    proof_obligations=evaluation.proof_obligations,
                )
            )
            for output_name in _tool_output_affordances(tool):
                provided.setdefault(output_name, step_id)

    for tool_name, evaluation in ordered:
        if len(steps) >= max_steps or evaluation.satisfied or not evaluation.missing_required_args:
            continue
        bindings: Dict[str, Any] = {}
        dependencies: List[str] = []
        for missing in evaluation.missing_required_args:
            provider_step = _provider_for_missing_arg(missing, provided)
            if provider_step is None:
                continue
            bindings[missing] = {"from_step": provider_step, "binding_type": "output_affordance"}
            dependencies.append(provider_step)
        if set(bindings) == set(evaluation.missing_required_args) and dependencies:
            step_id = f"step_{len(steps) + 1}"
            steps.append(
                ContractPlanStep(
                    step_id=step_id,
                    tool_name=tool_name,
                    dependency_step_ids=sorted(set(dependencies)),
                    grounded_required_args=evaluation.grounded_required_args,
                    input_bindings=bindings,
                    proof_obligations=[
                        *evaluation.proof_obligations,
                        {
                            "obligation": "dependent_arguments_bound_to_prior_outputs",
                            "status": "satisfied",
                            "evidence": bindings,
                        },
                    ],
                )
            )
        else:
            unresolved.append(
                {
                    "tool_name": tool_name,
                    "missing_required_args": evaluation.missing_required_args,
                    "blocking_reasons": evaluation.blocking_reasons,
                }
            )

    plan_blockers = [] if steps else ["no_contract_satisfying_plan"]
    return ContractPlan(
        satisfied=bool(steps) and not plan_blockers,
        steps=steps,
        unresolved_tools=unresolved[:5],
        blocking_reasons=plan_blockers,
    )


def calibrate_contract_policy(
    examples: List[Dict[str, Any]],
    *,
    name: str = "dev_calibrated_contract_policy",
) -> Dict[str, Any]:
    """Fit a simple transparent contract policy from labeled feature traces.

    This is intentionally lightweight: the fitted weights are the difference
    between positive and negative feature means, and the threshold is the
    midpoint between their average scores. Hard safety blockers remain enabled.
    """
    positives = [item for item in examples if bool(item.get("label"))]
    negatives = [item for item in examples if not bool(item.get("label"))]
    feature_names = sorted(
        {
            str(name)
            for item in examples
            for name in (item.get("features", {}) if isinstance(item.get("features"), dict) else {})
        }
    )
    if not examples or not feature_names or not positives or not negatives:
        return {
            "name": name,
            "mode": "strict",
            "bias": 0.0,
            "threshold": 0.0,
            "weights": {},
            "hard_block_missing_required": True,
            "hard_block_action_conflict": True,
            "hard_block_argument_issues": True,
            "calibration_examples": len(examples),
        }

    def mean(items: List[Dict[str, Any]], feature: str) -> float:
        return sum(float((item.get("features") or {}).get(feature, 0.0) or 0.0) for item in items) / len(items)

    weights = {feature: mean(positives, feature) - mean(negatives, feature) for feature in feature_names}
    bias = 0.0
    learning_rate = 0.25
    for _ in range(8):
        for item in examples:
            features = item.get("features") if isinstance(item.get("features"), dict) else {}
            label = 1.0 if bool(item.get("label")) else -1.0
            margin = label * (bias + sum(weights[feature] * float(features.get(feature, 0.0) or 0.0) for feature in feature_names))
            if margin <= 0.25:
                for feature in feature_names:
                    weights[feature] += learning_rate * label * float(features.get(feature, 0.0) or 0.0)
                bias += learning_rate * label

    rounded_weights = {feature: round(weight, 6) for feature, weight in weights.items()}

    def score(item: Dict[str, Any]) -> float:
        features = item.get("features") if isinstance(item.get("features"), dict) else {}
        return bias + sum(weights[feature] * float(features.get(feature, 0.0) or 0.0) for feature in feature_names)

    positive_score = sum(score(item) for item in positives) / len(positives)
    negative_score = sum(score(item) for item in negatives) / len(negatives)
    threshold = (positive_score + negative_score) / 2.0
    return {
        "name": name,
        "mode": "strict_weighted",
        "learner": "mean_initialized_margin_perceptron",
        "bias": round(bias, 6),
        "threshold": round(threshold, 6),
        "weights": rounded_weights,
        "hard_block_missing_required": True,
        "hard_block_action_conflict": True,
        "hard_block_argument_issues": True,
        "calibration_examples": len(examples),
        "positive_examples": len(positives),
        "negative_examples": len(negatives),
    }


def interpret_execution_feedback(evaluation: ContractEvaluation, feedback: Dict[str, Any]) -> Dict[str, Any]:
    """Classify execution or dry-run feedback into a contract-safe next action."""
    text = " ".join(str(value) for value in feedback.values()).lower()
    repair_actions: List[str] = []
    blocking_reasons: List[str] = []
    if re.search(r"\bmissing|required|must provide|is required\b", text):
        missing = evaluation.missing_required_args or _mentioned_contract_args(evaluation.contract.required_arguments, text)
        blocking_reasons.append("execution_missing_required")
        return {
            "next_action": "ask_for_missing_information",
            "blocking_reasons": blocking_reasons,
            "missing_required_args": missing,
            "repair_actions": repair_actions,
            "retry_allowed": False,
        }
    if re.search(r"\binvalid enum|must be one of|allowed values|invalid value\b", text):
        repair_actions.append("canonicalize_or_replace_invalid_enum_from_grounded_request")
    if re.search(r"\binvalid format|expected format|pattern\b", text):
        repair_actions.append("replace_invalid_format_from_grounded_request")
    if re.search(r"\bunknown field|additional properties|unsupported field\b", text):
        repair_actions.append("drop_unsupported_fields")
    if re.search(r"\bpermission|unauthorized|forbidden|auth\b", text):
        blocking_reasons.append("execution_permission_or_auth_error")
        return {
            "next_action": "abort",
            "blocking_reasons": blocking_reasons,
            "missing_required_args": [],
            "repair_actions": repair_actions,
            "retry_allowed": False,
        }
    if re.search(r"\bnot found|does not exist|missing file\b", text):
        blocking_reasons.append("execution_external_state_missing")
        return {
            "next_action": "ask_for_clarification",
            "blocking_reasons": blocking_reasons,
            "missing_required_args": [],
            "repair_actions": repair_actions,
            "retry_allowed": False,
        }
    if repair_actions:
        return {
            "next_action": "repair_and_retry",
            "blocking_reasons": [],
            "missing_required_args": [],
            "repair_actions": repair_actions,
            "retry_allowed": True,
        }
    return {
        "next_action": "record_observation",
        "blocking_reasons": [],
        "missing_required_args": [],
        "repair_actions": [],
        "retry_allowed": False,
    }


def build_contract_failure_report(evaluation: ContractEvaluation) -> Dict[str, Any]:
    """Summarize the failed proof obligation in a compact, user/action oriented form."""
    if evaluation.satisfied:
        return {"satisfied": True, "reason": None}
    if evaluation.missing_required_args:
        return {
            "satisfied": False,
            "reason": "missing_required_arguments",
            "missing_required_args": evaluation.missing_required_args,
            "clarification": "Provide grounded values for: " + ", ".join(evaluation.missing_required_args),
        }
    if "action_intent_conflict" in evaluation.blocking_reasons:
        return {
            "satisfied": False,
            "reason": "action_intent_conflict",
            "request_actions": evaluation.request_actions,
            "tool_actions": evaluation.tool_actions,
            "negated_actions": evaluation.negated_actions,
            "clarification": "The requested action conflicts with this tool's action or side-effect contract.",
        }
    if evaluation.argument_issues:
        return {
            "satisfied": False,
            "reason": "argument_contract_violation",
            "argument_issues": evaluation.argument_issues,
            "clarification": "Revise arguments so they satisfy the schema and are grounded in the request.",
        }
    if "adaptive_policy_reject" in evaluation.blocking_reasons:
        return {
            "satisfied": False,
            "reason": "adaptive_policy_reject",
            "policy_decision": evaluation.policy_decision,
            "clarification": "The calibrated contract policy did not accept this call.",
        }
    return {
        "satisfied": False,
        "reason": ",".join(evaluation.blocking_reasons) or "contract_unsatisfied",
        "clarification": "Clarify the intended tool, action, and required arguments.",
    }


def _contract_policy(skill: GeneratedSkill | None) -> Dict[str, Any]:
    metadata = skill.metadata if skill is not None and isinstance(skill.metadata, dict) else {}
    policy = metadata.get("contract_policy")
    if isinstance(policy, dict):
        return {
            "name": str(policy.get("name") or "metadata_policy"),
            "mode": str(policy.get("mode") or "strict_weighted"),
            "bias": float(policy.get("bias", 0.0) or 0.0),
            "threshold": float(policy.get("threshold", 0.0) or 0.0),
            "weights": dict(policy.get("weights", {}) if isinstance(policy.get("weights"), dict) else {}),
            "hard_block_missing_required": bool(policy.get("hard_block_missing_required", True)),
            "hard_block_action_conflict": bool(policy.get("hard_block_action_conflict", True)),
            "hard_block_argument_issues": bool(policy.get("hard_block_argument_issues", True)),
        }
    return {
        "name": "strict_contract_policy",
        "mode": "strict",
        "bias": 0.0,
        "threshold": 0.0,
        "weights": {},
        "hard_block_missing_required": True,
        "hard_block_action_conflict": True,
        "hard_block_argument_issues": True,
    }


def _contract_policy_features(
    *,
    contract: SkillContract,
    grounded: List[str],
    missing: List[str],
    action_conflict: bool,
    argument_issues: List[str],
) -> Dict[str, float]:
    required_total = float(max(len(contract.required_arguments), 1))
    side_effect_risk = 1.0 if contract.side_effect_class in {"write", "delete", "external_send"} else 0.0
    return {
        "required_total": float(len(contract.required_arguments)),
        "grounded_required_count": float(len(grounded)),
        "missing_required_count": float(len(missing)),
        "grounded_required_fraction": float(len(grounded)) / required_total,
        "action_conflict": 1.0 if action_conflict else 0.0,
        "argument_issue_count": float(len(argument_issues)),
        "side_effect_risk": side_effect_risk,
    }


def _apply_contract_policy(policy: Dict[str, Any], blocking_reasons: List[str], features: Dict[str, float]) -> Dict[str, Any]:
    missing_block = bool(policy.get("hard_block_missing_required", True)) and "missing_required_arguments" in blocking_reasons
    action_block = bool(policy.get("hard_block_action_conflict", True)) and "action_intent_conflict" in blocking_reasons
    argument_block = bool(policy.get("hard_block_argument_issues", True)) and "argument_contract_violation" in blocking_reasons
    hard_block = missing_block or action_block or argument_block
    weights = policy.get("weights") if isinstance(policy.get("weights"), dict) else {}
    score = float(policy.get("bias", 0.0) or 0.0)
    contributions: Dict[str, float] = {}
    for name, raw_weight in weights.items():
        try:
            weight = float(raw_weight)
        except (TypeError, ValueError):
            continue
        contribution = weight * float(features.get(str(name), 0.0))
        contributions[str(name)] = round(contribution, 6)
        score += contribution
    threshold = float(policy.get("threshold", 0.0) or 0.0)
    allow_call = (not hard_block) and score >= threshold
    if str(policy.get("mode") or "strict") == "strict" and not blocking_reasons:
        allow_call = True
    return {
        "policy_name": policy.get("name") or "strict_contract_policy",
        "mode": policy.get("mode") or "strict",
        "score": round(score, 6),
        "threshold": threshold,
        "allow_call": allow_call,
        "hard_block": hard_block,
        "hard_block_reasons": [
            reason
            for reason, active in [
                ("missing_required_arguments", missing_block),
                ("action_intent_conflict", action_block),
                ("argument_contract_violation", argument_block),
            ]
            if active
        ],
        "feature_contributions": contributions,
    }


def _compose_grounding_text(request: str, grounding_context: Any | None) -> tuple[str, List[str]]:
    sources = ["user_request"]
    parts = [request]
    if grounding_context is None:
        return request, sources
    if isinstance(grounding_context, str) and grounding_context.strip():
        parts.append(grounding_context)
        sources.append("context")
    elif isinstance(grounding_context, dict):
        for key in ("conversation", "history", "messages", "artifacts", "files", "observations", "tool_observations"):
            value = grounding_context.get(key)
            text = _context_value_text(value)
            if text:
                parts.append(text)
                sources.append(str(key))
    elif isinstance(grounding_context, list):
        text = _context_value_text(grounding_context)
        if text:
            parts.append(text)
            sources.append("context_list")
    return "\n".join(parts), sources


def _context_value_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        chunks: List[str] = []
        for key, child in value.items():
            child_text = _context_value_text(child)
            if child_text:
                chunks.append(f"{key}: {child_text}")
        return "\n".join(chunks)
    if isinstance(value, list):
        return "\n".join(_context_value_text(item) for item in value if _context_value_text(item))
    return str(value)


def _nested_required_paths(arg: ArgumentIR) -> List[str]:
    paths: List[str] = []
    if arg.type == "object" or arg.properties:
        for child in arg.required_properties:
            paths.append(f"{arg.name}.{child}")
    if arg.type == "array" and isinstance(arg.items_schema, dict):
        item_schema, _ = normalize_schema_node(arg.items_schema)
        for child in item_schema.get("required", []) or []:
            paths.append(f"{arg.name}[].{child}")
    return paths


def _mentioned_contract_args(arguments: List[str], text: str) -> List[str]:
    mentioned = [arg for arg in arguments if any(part in text for part in _argument_name_parts(arg))]
    return mentioned or arguments


def _tool_output_affordances(tool: ToolIR) -> set[str]:
    text = " ".join([tool.tool_name, tool.tool_purpose or "", tool.output_hint or ""]).lower()
    affordances: set[str] = set()
    if any(token in text for token in ("content", "contents", "text", "body", "message")):
        affordances.update({"content", "text", "body", "message"})
    if any(token in text for token in ("path", "file", "filename")):
        affordances.update({"path", "file", "filename"})
    if any(token in text for token in ("result", "results", "search", "list", "items")):
        affordances.update({"results", "items", "query_results"})
    if any(token in text for token in ("id", "identifier", "account", "entity", "user")):
        affordances.update({"id", "identifier", "account_id", "entity_id", "user_id"})
    return affordances


def _provider_for_missing_arg(argument_name: str, provided: Dict[str, str]) -> str | None:
    name_parts = _argument_name_parts(argument_name)
    for provided_name, step_id in provided.items():
        provided_parts = _argument_name_parts(provided_name)
        if argument_name == provided_name or name_parts.intersection(provided_parts):
            return step_id
    return None


def _required_arg_grounding(request: str, arg: ArgumentIR, tool: ToolIR | None = None) -> Dict[str, Any]:
    if _mentions_deferred_required_info(request, arg.name):
        return {"grounded": False, "evidence": "deferred_required_information"}
    if re.search(rf"\b{re.escape(arg.name)}\s*(?:=|:)", request, flags=re.IGNORECASE):
        return {"grounded": True, "evidence": "explicit_named_argument"}
    if _request_declares_no_arguments(request):
        return {"grounded": False, "evidence": "request_declares_no_arguments"}
    if (arg.type == "object" or arg.properties) and isinstance(arg.properties, dict):
        children = list(arg.required_properties) or list(arg.properties)
        missing = [child for child in children if not _schema_property_is_grounded(request, child, arg.properties.get(child, {}))]
        return {
            "grounded": not missing,
            "evidence": "nested_required_properties" if not missing else {"missing_nested": missing},
        }
    if arg.type == "array":
        item_schema, _ = normalize_schema_node(arg.items_schema if isinstance(arg.items_schema, dict) else {"type": arg.items_type or "string"})
        properties = item_schema.get("properties")
        if isinstance(properties, dict) and properties:
            children = list(item_schema.get("required") or properties)
            missing = [child for child in children if not _schema_property_is_grounded(request, child, properties.get(child, {}))]
            return {
                "grounded": not missing,
                "evidence": "array_item_required_properties" if not missing else {"missing_array_item": missing},
            }
        if _array_scalar_is_grounded(request, arg, item_schema):
            return {"grounded": True, "evidence": "array_scalar_value"}

    lowered = request.lower()
    parts = _argument_name_parts(arg.name)
    if arg.format == "email" or parts.intersection({"email", "recipient", "attendee"}):
        return {"grounded": bool(_contains_email(request)), "evidence": "email_literal"}
    if arg.format in {"uri", "url"} or parts.intersection({"url", "uri", "link", "website"}):
        return {"grounded": bool(_contains_url(request)), "evidence": "url_literal"}
    if arg.format == "date-time" or parts.intersection({"datetime"}):
        return {"grounded": bool(_contains_date_like_text(request)), "evidence": "datetime_literal"}
    if _looks_like_location_argument(arg.name):
        return {"grounded": _contains_directional_location_text(arg.name, request), "evidence": "directional_location_literal"}
    if _looks_like_sequence_argument(arg.name):
        return {"grounded": _contains_sequence_text(arg.name, request), "evidence": "sequence_literal"}
    if arg.format == "date" or parts.intersection({"date", "time", "start", "end"}):
        return {"grounded": bool(_contains_date_like_text(request)), "evidence": "date_literal"}
    if arg.type in {"integer", "number"}:
        grounded = _numeric_arg_is_grounded(request, arg, tool)
        return {"grounded": grounded, "evidence": "numeric_literal" if grounded else "numeric_argument_not_bound"}
    if arg.enum:
        return {"grounded": any(str(value).lower() in lowered for value in arg.enum), "evidence": "enum_literal"}
    if parts.intersection({"query", "search", "pattern"}):
        return {
            "grounded": bool(re.search(r"\b(?:query|search|find|lookup|look up|matching|containing)\b", lowered) or re.search(r'"[^"]+"', request)),
            "evidence": "query_cue",
        }
    if parts.intersection({"path", "file", "filename", "directory", "folder"}):
        return {"grounded": _contains_path_like_text(request), "evidence": "path_literal"}
    if parts.intersection({"content", "contents", "text", "body", "message", "payload", "value"}):
        return {
            "grounded": bool(re.search(r'"[^"]+"', request) or re.search(r"\b(?:content|text|body|message|write|save|send|remember|note|record|set)\b", lowered)),
            "evidence": "content_cue",
        }
    if parts.intersection({"id", "account", "acct", "customer", "client", "user", "entity", "name", "title"}):
        return {
            "grounded": bool(_contains_identifier_like_text(request) or re.search(r'"[^"]+"', request)),
            "evidence": "identifier_literal",
        }
    if parts and parts.intersection(set(_tokenize(request))):
        return {"grounded": True, "evidence": "name_overlap"}
    description_parts = _argument_name_parts(arg.description or "")
    return {
        "grounded": bool(description_parts and description_parts.intersection(set(_tokenize(request)))),
        "evidence": "description_overlap",
    }


def _schema_property_is_grounded(request: str, name: str, schema: Any) -> bool:
    if _mentions_deferred_required_info(request, name):
        return False
    if re.search(rf"\b{re.escape(name)}\s*(?:=|:)", request, flags=re.IGNORECASE):
        return True
    schema = schema if isinstance(schema, dict) else {}
    lowered = request.lower()
    parts = _argument_name_parts(name)
    kind = str(schema.get("type") or "").lower()
    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and any(str(value).lower() in lowered for value in enum_values):
        return True
    if schema.get("format") == "email" or parts.intersection({"email", "recipient", "attendee"}):
        return _contains_email(request)
    if schema.get("format") in {"uri", "url"} or parts.intersection({"url", "uri", "link", "website"}):
        return _contains_url(request)
    if _looks_like_location_argument(name):
        return _contains_directional_location_text(name, request)
    if _looks_like_sequence_argument(name):
        return _contains_sequence_text(name, request)
    if schema.get("format") in {"date", "date-time"} or parts.intersection({"date", "time", "start", "end", "begin", "from", "since", "after", "until", "before"}):
        return _contains_date_like_text(request)
    if kind in {"integer", "number"}:
        return _numeric_field_is_grounded(request, name)
    if parts.intersection({"query", "search", "pattern"}):
        return bool(re.search(r"\b(?:query|search|find|lookup|look up|matching|containing)\b", lowered) or re.search(r'"[^"]+"', request))
    if parts.intersection({"path", "file", "filename", "directory", "folder"}):
        return _contains_path_like_text(request)
    if parts.intersection({"content", "contents", "text", "body", "message", "payload", "value"}):
        return bool(re.search(r'"[^"]+"', request) or re.search(r"\b(?:content|text|body|message|write|save|send|remember|note|record|set)\b", lowered))
    if parts.intersection({"id", "account", "acct", "customer", "client", "user", "entity", "name", "title"}):
        return bool(_contains_identifier_like_text(request) or re.search(r'"[^"]+"', request))
    return bool(parts and parts.intersection(set(_tokenize(request))))


def _argument_contract_issues(tool: ToolIR, request: str, arguments: Dict[str, Any] | None) -> List[str]:
    if arguments is None:
        return []
    issues: List[str] = []
    by_name = {arg.name: arg for arg in tool.arguments}
    for key, value in arguments.items():
        arg = by_name.get(key)
        if arg is None:
            issues.append(f"{key}:unsupported_field")
            continue
        issues.extend(_schema_issues(value, _schema_for_argument(arg), key))
        if arg.required and not _value_grounded(arg.name, value, request):
            issues.append(f"{key}:ungrounded_required")
    for arg in tool.arguments:
        if arg.required and arg.name not in arguments:
            issues.append(f"{arg.name}:missing_required")
    return sorted(set(issues))


def _schema_for_argument(arg: ArgumentIR) -> Dict[str, Any]:
    schema: Dict[str, Any] = {"type": arg.type}
    if arg.enum:
        schema["enum"] = list(arg.enum)
    if arg.default is not None:
        schema["default"] = arg.default
    if arg.format:
        schema["format"] = arg.format
    if arg.type == "object" or arg.properties:
        schema["type"] = "object"
        schema["properties"] = arg.properties or {}
        schema["required"] = list(arg.required_properties)
    if arg.type == "array":
        schema["type"] = "array"
        schema["items"] = arg.items_schema if isinstance(arg.items_schema, dict) else {"type": arg.items_type or "string"}
    return schema


def _schema_issues(value: Any, schema: Dict[str, Any], path: str) -> List[str]:
    schema, _ = normalize_schema_node(schema)
    kind = schema_type(schema)
    issues: List[str] = []
    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and enum_values and value not in enum_values:
        issues.append(f"{path}:invalid_enum")
        return issues
    if kind == "string":
        if not isinstance(value, str):
            issues.append(f"{path}:type_mismatch")
            return issues
        return _string_issues(value, schema, path)
    if kind == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            issues.append(f"{path}:type_mismatch")
        return issues
    if kind == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            issues.append(f"{path}:type_mismatch")
        return issues
    if kind == "boolean":
        if not isinstance(value, bool):
            issues.append(f"{path}:type_mismatch")
        return issues
    if kind == "object":
        if not isinstance(value, dict):
            issues.append(f"{path}:type_mismatch")
            return issues
        properties = schema.get("properties", {}) or {}
        if not properties:
            return issues
        for key, child in value.items():
            if key not in properties:
                issues.append(f"{path}.{key}:unsupported_field")
            else:
                issues.extend(_schema_issues(child, properties[key], f"{path}.{key}"))
        for key in schema.get("required", []) or []:
            if key not in value:
                issues.append(f"{path}.{key}:missing_required")
        return issues
    if kind == "array":
        if not isinstance(value, list):
            issues.append(f"{path}:type_mismatch")
            return issues
        min_items = schema.get("minItems")
        max_items = schema.get("maxItems")
        if isinstance(min_items, int) and len(value) < min_items:
            issues.append(f"{path}:min_items")
        if isinstance(max_items, int) and len(value) > max_items:
            issues.append(f"{path}:max_items")
        item_schema = schema.get("items", {}) or {}
        for index, item in enumerate(value):
            issues.extend(_schema_issues(item, item_schema, f"{path}[{index}]"))
    return issues


def _string_issues(value: str, schema: Dict[str, Any], path: str) -> List[str]:
    issues: List[str] = []
    fmt = str(schema.get("format") or "").lower()
    symbolic_placeholder = _looks_like_symbolic_placeholder(value)
    if fmt == "email" and not symbolic_placeholder and not re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", value):
        issues.append(f"{path}:invalid_format")
    if fmt in {"uri", "url"} and not symbolic_placeholder and not re.match(r"^https?://[^\s]+$", value):
        issues.append(f"{path}:invalid_format")
    if fmt == "date" and not symbolic_placeholder and not re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", value):
        issues.append(f"{path}:invalid_format")
    if fmt == "date-time" and not symbolic_placeholder and not re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}T\d{1,2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?", value):
        issues.append(f"{path}:invalid_format")
    pattern = schema.get("pattern")
    if isinstance(pattern, str):
        try:
            if not re.search(pattern, value):
                issues.append(f"{path}:pattern_mismatch")
        except re.error:
            pass
    min_length = schema.get("minLength")
    max_length = schema.get("maxLength")
    if isinstance(min_length, int) and len(value) < min_length:
        issues.append(f"{path}:min_length")
    if isinstance(max_length, int) and len(value) > max_length:
        issues.append(f"{path}:max_length")
    return issues


def _looks_like_symbolic_placeholder(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*_\d+", value.strip()))


def _value_grounded(field_name: str, value: Any, request: str) -> bool:
    lowered = request.lower()
    if isinstance(value, bool):
        return any(part in lowered for part in _argument_name_parts(field_name))
    leaves = [str(item).strip().lower() for item in _leaf_values(value) if item is not None and not isinstance(item, bool)]
    for leaf in leaves:
        if not leaf:
            continue
        if _explicit_field_value_in_request(field_name, leaf, request):
            return True
        if re.fullmatch(r"-?\d+(?:\.\d+)?", leaf) and _numeric_value_in_request(leaf, request):
            return True
        if len(leaf) > 1 and leaf in lowered:
            return True
    return False


def _explicit_field_value_in_request(field_name: str, leaf: str, request: str) -> bool:
    pattern = rf"\b{re.escape(field_name)}\s*(?:=|:)\s*(?:\"{re.escape(leaf)}\"|'{re.escape(leaf)}'|`{re.escape(leaf)}`|{re.escape(leaf)})(?=$|[\s,.;])"
    return bool(re.search(pattern, request, flags=re.IGNORECASE))


def _numeric_value_in_request(leaf: str, request: str) -> bool:
    try:
        target = float(leaf)
    except ValueError:
        return False
    for literal in _numeric_literals(request):
        try:
            if float(literal) == target:
                return True
        except ValueError:
            continue
    return False


def _contains_identifier_like_text(request: str) -> bool:
    patterns = [
        r"\b(?:acct|account|customer|client|user|entity)\s+(?:id|identifier)(?:[-_:]|\s+)([A-Za-z0-9][A-Za-z0-9_.-]*)\b",
        r"\b(?:acct|account|customer|client|user|entity|identifier|id)(?:[-_:]|\s+)([A-Za-z0-9][A-Za-z0-9_.-]*)\b",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, request, flags=re.IGNORECASE):
            if _looks_like_identifier_literal(match.group(1)):
                return True
    return False


def _looks_like_identifier_literal(value: str) -> bool:
    return bool(
        value
        and len(value) > 1
        and (re.search(r"\d", value) or re.search(r"[-_.]", value))
        and value.lower()
        not in {
            "record",
            "records",
            "identifier",
            "identifiers",
            "account",
            "accounts",
            "customer",
            "customers",
            "client",
            "clients",
            "user",
            "users",
        }
    )


def _leaf_values(value: Any) -> List[Any]:
    if isinstance(value, dict):
        result: List[Any] = []
        for child in value.values():
            result.extend(_leaf_values(child))
        return result
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(_leaf_values(item))
        return result
    return [value]


def _numeric_arg_is_grounded(request: str, arg: ArgumentIR, tool: ToolIR | None) -> bool:
    if _numeric_field_is_grounded(request, arg.name):
        return True
    if _numeric_arg_has_positional_grounding(request, arg, tool):
        return True
    required_numeric = [
        item
        for item in (tool.arguments if tool is not None else [arg])
        if item.required and item.type in {"integer", "number"}
    ]
    return len(required_numeric) <= 1 and bool(_numeric_literals(request))


def _numeric_arg_has_positional_grounding(request: str, arg: ArgumentIR, tool: ToolIR | None) -> bool:
    if tool is None:
        return False
    required_numeric = [item for item in tool.arguments if item.required and item.type in {"integer", "number"}]
    names = [item.name for item in required_numeric]
    if arg.name not in names or len(names) < 2:
        return False
    numbers = _numeric_literals(request)
    if len(numbers) < len(names):
        return False
    lowered = request.lower()
    return (
        set(names).issubset({"a", "b", "c", "x", "y", "z"})
        and bool(re.search(r"\b(?:coefficient|coefficients|quadratic|polynomial|coordinate|coordinates|point)\b", lowered))
    ) or (
        len(numbers) == len(names)
        and bool(re.search(r"\b(?:values?|parameters?|inputs?|dimensions?)\b", lowered))
    )


def _numeric_field_is_grounded(request: str, name: str) -> bool:
    if re.search(rf"\b{re.escape(name)}\s*(?:=|:)\s*-?\d+(?:\.\d+)?\b", request, flags=re.IGNORECASE):
        return True
    if re.search(rf"(?<![A-Za-z0-9_.-])-?\d+(?:\.\d+)?(?![A-Za-z0-9_-])\s+{re.escape(name)}\b", request, flags=re.IGNORECASE):
        return True
    parts = _argument_name_parts(name)
    if parts.intersection({"amount", "total", "cost", "price"}):
        return bool(re.search(r"\b(?:amount|total|cost|price|transfer|pay|send)\s+(?:of\s+)?\$?-?\d+(?:\.\d+)?\b", request, flags=re.IGNORECASE))
    return False


def _numeric_literals(request: str) -> List[str]:
    text = re.sub(r"\b\d{4}-\d{1,2}-\d{1,2}\b", " ", request)
    text = re.sub(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b", " ", text)
    return re.findall(r"(?<![A-Za-z0-9_.-])-?\d+(?:\.\d+)?(?![A-Za-z0-9_-])", text)


def _array_scalar_is_grounded(request: str, arg: ArgumentIR, item_schema: Dict[str, Any]) -> bool:
    parts = _argument_name_parts(arg.name)
    item_type = schema_type(item_schema) or str(item_schema.get("type") or "").lower()
    if item_schema.get("format") == "email" or parts.intersection({"email", "emails", "recipient", "recipients", "attendee", "attendees"}):
        return _contains_email(request)
    if item_schema.get("format") in {"uri", "url"} or parts.intersection({"url", "urls", "link", "links"}):
        return _contains_url(request)
    if item_type in {"integer", "number"}:
        return _contains_named_or_generic_array_text(arg.name, request) and bool(_numeric_literals(request))
    if parts.intersection({"path", "paths", "file", "files", "filename", "filenames"}):
        return bool(re.findall(r"\b[A-Za-z0-9_./*?-]+\.[A-Za-z0-9_*?-]+\b", request))
    if _contains_named_or_generic_array_text(arg.name, request) and re.search(r"[,[]", request):
        return True
    if re.findall(r'"([^"]+)"', request) and parts.intersection({"items", "values", "content", "contents", "messages"}):
        return True
    return False


def _contains_named_or_generic_array_text(name: str, request: str) -> bool:
    if re.search(rf"\b{re.escape(name)}\s*(?:=|:)\s*(?:\[[^\]]+\]|[^.;]+)", request, flags=re.IGNORECASE):
        return True
    parts = _argument_name_parts(name)
    if parts.intersection({"list", "array", "data", "values", "numbers", "items", "series"}):
        return bool(re.search(r"\b(?:numbers?|values?|data|list|array|items|series)\b", request, flags=re.IGNORECASE))
    return False


def _request_declares_no_arguments(request: str) -> bool:
    lowered = request.lower()
    return bool(
        re.search(r"\bapply\s+no\s+arguments?\b", lowered)
        or re.search(r"\bwith\s+no\s+arguments?\b", lowered)
        or re.search(r"\bno\s+arguments?\s+(?:required|needed|provided)\b", lowered)
    )


def _looks_like_location_argument(name: str) -> bool:
    parts = _argument_name_parts(name)
    if parts.intersection({"city", "location", "place", "address"}):
        return True
    if parts.intersection({"origin", "destination"}) and not parts.intersection({"id", "account", "user", "entity"}):
        return True
    return False


def _contains_directional_location_text(name: str, request: str) -> bool:
    if re.search(rf"\b{re.escape(name)}\s*(?:=|:)\s*[^,.;]+", request, flags=re.IGNORECASE):
        return True
    parts = _argument_name_parts(name)
    if parts.intersection({"start", "from", "source", "origin", "departure", "end", "to", "target", "destination", "arrival"}):
        return bool(
            re.search(r"\bfrom\s+.+?\s+(?:to|toward|towards|into)\s+.+?(?:[.;]|$|\s+(?:by|via|using|with|for)\b)", request, flags=re.IGNORECASE)
            or re.search(r"\borigin\s*(?:=|:|is)?\s*.+?\s+(?:destination|dest)\s*(?:=|:|is)?\s*.+", request, flags=re.IGNORECASE)
            or re.search(r"\bsource\s*(?:city|location|place)?\s*(?:=|:|is)?\s*.+?\s+(?:target|destination|dest)\s*(?:city|location|place)?\s*(?:=|:|is)?\s*.+", request, flags=re.IGNORECASE)
        )
    return bool(re.search(r"\b(?:in|at|near|for)\s+[A-Z][A-Za-z0-9_-]{1,}", request))


def _looks_like_sequence_argument(name: str) -> bool:
    return bool(_argument_name_parts(name).intersection({"sequence", "reference", "dna", "rna"}))


def _contains_sequence_text(name: str, request: str) -> bool:
    if re.search(rf"\b{re.escape(name)}\s*(?:=|:)\s*[A-Za-z]{{4,}}\b", request, flags=re.IGNORECASE):
        return True
    parts = _argument_name_parts(name)
    if "reference" in parts:
        return bool(
            re.search(r"\breference(?:\s+sequence)?\s*(?:=|:|is|as|of)?\s*[ACGTUNacgtun]{4,}\b", request, flags=re.IGNORECASE)
            or re.search(r"\bagainst\s+(?:reference\s+)?[ACGTUNacgtun]{4,}\b", request, flags=re.IGNORECASE)
        )
    return bool(
        re.search(r"\b(?:dna|rna)?\s*sequence\s*(?:=|:|is|as|of)?\s*[ACGTUNacgtun]{4,}\b", request, flags=re.IGNORECASE)
        or re.search(r"\banalyze\s+[ACGTUNacgtun]{4,}\b", request, flags=re.IGNORECASE)
    )


def _contains_path_like_text(request: str) -> bool:
    lowered = request.lower()
    return bool(
        re.search(r"\b[A-Za-z0-9_./-]+\.[A-Za-z0-9_*?-]+\b", request)
        or re.search(r"\b(?:in|under|inside|within)\s+[A-Za-z0-9_./-]+\b", lowered)
        or re.search(r"\bcreate\s+(?:the\s+)?(?:directory|folder)\s+[A-Za-z0-9_./-]+\b", lowered)
        or re.search(r"\bcreate\s+(?:the\s+)?[A-Za-z0-9_./-]+\s+(?:directory|folder)\b", lowered)
    )


def _contains_date_like_text(request: str) -> bool:
    lowered = request.lower()
    return bool(
        re.search(r"\b\d{4}-\d{1,2}-\d{1,2}\b", request)
        or re.search(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b", request)
        or re.search(r"\b(?:today|tomorrow|yesterday|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", lowered)
        or re.search(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", lowered)
    )


def _contains_email(request: str) -> bool:
    return bool(re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", request))


def _contains_url(request: str) -> bool:
    return bool(re.search(r"\bhttps?://[^\s,.;]+", request))


def _mentions_deferred_required_info(request: str, name: str) -> bool:
    lowered = request.lower()
    deferred = bool(re.search(r"\b(?:later|after|when)\b", lowered) and re.search(r"\b(?:send|provide|give|share)\b", lowered))
    if not deferred:
        return False
    parts = _argument_name_parts(name)
    return not parts or any(part in lowered for part in parts)


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9_./*?-]+", text.lower())


def _argument_name_parts(text: str) -> set[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", text)
    return {part.lower() for part in re.split(r"[^A-Za-z0-9]+", spaced) if len(part) > 2}


def _action_families_for_tool(tool: ToolIR) -> set[str]:
    return _action_families_for_text(" ".join([tool.tool_name, tool.tool_purpose or "", *(tool.side_effect_hints or []), *(tool.safety_hints or [])]))


def _strip_unrelated_without_using_clause(request: str, tool: ToolIR) -> str:
    tool_names = _tool_name_variants(tool)

    def replace(match: re.Match[str]) -> str:
        clause = match.group(0)
        if any(name in _normalize_tool_text(clause) for name in tool_names):
            return clause
        return " "

    return re.sub(r"\bwithout\s+using\b[^:;,.]*(?::|;|,|\.)?", replace, request, flags=re.IGNORECASE)


def _tool_name_variants(tool: ToolIR) -> list[str]:
    name = tool.tool_name
    variants = {
        _normalize_tool_text(name),
        _normalize_tool_text(name.replace("_", " ")),
        _normalize_tool_text(name.replace("-", " ")),
        _normalize_tool_text(name.replace(".", " ")),
    }
    return sorted(value for value in variants if value)


def _normalize_tool_text(text: str) -> str:
    lowered = str(text or "").lower()
    lowered = re.sub(r"[_./:-]+", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


def _request_declares_no_arguments_text(request: str) -> bool:
    lowered = request.lower()
    return bool(
        re.search(r"\bapply\s+no\s+arguments?\b", lowered)
        or re.search(r"\bwith\s+no\s+arguments?\b", lowered)
        or re.search(r"\bno\s+arguments?\s+(?:required|needed|provided)\b", lowered)
        or "use the best matching tool" in lowered
    )


def _action_families_for_text(text: str) -> set[str]:
    tokens = {_normalize_action_token(token) for token in _tokenize(text)}
    tokens = {token for token in tokens if token}
    families: set[str] = set()
    for family, cues in ACTION_FAMILIES.items():
        if tokens.intersection(cues):
            families.add(family)
    if _has_compute_context(text, tokens):
        families.add("compute")
    if re.search(r"\brecord\s+(?:an?\s+|the\s+|this\s+|new\s+)?(?:observation|note|entry|event|transaction|item|result|measurement)\b", text.lower()):
        families.add("create")
    return families


def _has_compute_context(text: str, tokens: set[str]) -> bool:
    if not tokens.intersection({"find", "determine", "derive", "solve", "rank"}):
        return False
    compute_terms = {
        "root",
        "roots",
        "equation",
        "quadratic",
        "coefficient",
        "coefficients",
        "average",
        "mean",
        "median",
        "density",
        "pressure",
        "velocity",
        "acceleration",
        "force",
        "area",
        "volume",
        "circumference",
        "frequency",
        "resonance",
        "entropy",
        "bmi",
        "probability",
        "genotype",
        "electric",
        "potential",
        "capacitance",
        "inductance",
        "heat",
        "capacity",
        "concentration",
        "rate",
        "distance",
    }
    lowered = text.lower()
    return bool(tokens.intersection(compute_terms) or re.search(r"\b(?:under|over)\s+(?:the\s+)?curve\b", lowered))


def _negated_action_families_for_text(text: str) -> set[str]:
    lowered = text.lower()
    negated: set[str] = set()
    for family, cues in ACTION_FAMILIES.items():
        for cue in cues:
            if re.search(rf"\b(?:do not|don't|without|avoid|no)\s+{re.escape(cue)}(?:ing|e|ed|s)?\b", lowered):
                negated.add(family)
    return negated


def _normalize_action_token(token: str) -> str:
    token = token.strip("._-/").lower()
    if token.endswith("ing") and len(token) > 5:
        return token[:-3]
    if token.endswith("ed") and len(token) > 4:
        return token[:-2]
    if token.endswith("s") and len(token) > 4:
        return token[:-1]
    return token


def _side_effect_class(tool: ToolIR, actions: Iterable[str]) -> str:
    text = " ".join(
        [
            str(tool.schema_complexity.get("side_effect_type") or tool.schema_complexity.get("side_effect") or ""),
            *(tool.side_effect_hints or []),
            *(tool.safety_hints or []),
            *actions,
        ]
    ).lower()
    if any(token in text for token in ("delete", "remove", "drop", "clear")):
        return "delete"
    if any(token in text for token in ("send", "post", "publish", "transfer", "notify", "email")):
        return "external_send"
    if any(token in text for token in ("write", "create", "update", "append", "execute", "external")):
        return "write"
    if any(token in text for token in ("calculate", "compute", "convert", "estimate")):
        return "compute"
    if any(token in text for token in ("read", "search", "list", "fetch", "retrieve", "preview")):
        return "read"
    return "unknown"


def _side_effect_fit_bonus(request: str, tool: ToolIR) -> int:
    side_effect = _side_effect_class(tool, _action_families_for_tool(tool))
    request_actions = _action_families_for_text(request) - _negated_action_families_for_text(request)
    read_like_request = bool(request_actions.intersection({"search", "read"}))
    write_like_request = bool(request_actions.intersection({"create", "update", "delete", "send"}))
    write_like_tool = side_effect in {"write", "delete", "external_send"}
    if write_like_tool and read_like_request and not write_like_request:
        return -6
    if write_like_tool and write_like_request:
        return 2
    if not write_like_tool and write_like_request and not read_like_request:
        return -2
    return 0


def _action_intent_fit_bonus(request: str, tool: ToolIR) -> int:
    request_actions = _action_families_for_text(request) - _negated_action_families_for_text(request)
    tool_actions = _action_families_for_tool(tool)
    if not request_actions or not tool_actions:
        return 0
    if _negated_action_families_for_text(request).intersection(tool_actions):
        return -30
    overlap = request_actions.intersection(tool_actions)
    if overlap:
        return 3 * len(overlap)
    if _actions_conflict(request_actions, tool_actions):
        return -5
    return 0


def _action_intent_conflict(request_actions: set[str], tool_actions: set[str], negated_actions: set[str]) -> bool:
    if tool_actions and negated_actions.intersection(tool_actions):
        return True
    if request_actions.intersection(tool_actions):
        return False
    return bool(request_actions and tool_actions and _actions_conflict(request_actions, tool_actions))


def _actions_conflict(request_actions: set[str], tool_actions: set[str]) -> bool:
    readonly = {"search", "read"}
    mutating = {"create", "update", "delete", "send"}
    if request_actions.intersection(readonly) and tool_actions.intersection(mutating):
        return True
    if request_actions.intersection(mutating) and tool_actions.intersection(readonly):
        return True
    if "delete" in request_actions and tool_actions.intersection({"create", "update", "send"}):
        return True
    if request_actions.intersection({"create", "update", "send"}) and "delete" in tool_actions:
        return True
    return False


def _discriminator_tokens(tool: ToolIR) -> set[str]:
    action_cues = set().union(*ACTION_FAMILIES.values())
    stop = {
        "and",
        "the",
        "tool",
        "use",
        "for",
        "with",
        "from",
        "request",
        "input",
        "argument",
        "field",
    }
    tokens: set[str] = set()
    for token in _tokenize(" ".join([tool.tool_name, tool.tool_purpose or ""])):
        for part in re.split(r"[-_/.]+", token):
            if len(part) > 2 and part not in stop and part not in action_cues:
                tokens.add(part)
    return tokens

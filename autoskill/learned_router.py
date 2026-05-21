from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
import re
from typing import Any, Dict, Iterable, List, Mapping, Tuple

from autoskill.contract_decision import explicit_requested_tool_score
from autoskill.ir import GeneratedSkill, ToolIR
from autoskill.routing_boundaries import normalize_routing_text


DEFAULT_GLOBAL_ROUTER_PRIOR_TRAINING_SCALE = 0.35
DEFAULT_GLOBAL_ROUTER_PRIOR_INFERENCE_SCALE = 0.0


_STOPWORDS = {
    "a",
    "about",
    "after",
    "all",
    "an",
    "and",
    "any",
    "are",
    "as",
    "be",
    "by",
    "call",
    "do",
    "for",
    "from",
    "help",
    "i",
    "in",
    "input",
    "is",
    "it",
    "me",
    "need",
    "of",
    "on",
    "or",
    "please",
    "request",
    "set",
    "task",
    "the",
    "this",
    "to",
    "tool",
    "use",
    "using",
    "with",
}

_ACTION_FAMILIES: Dict[str, set[str]] = {
    "read": {"read", "open", "show", "inspect", "display", "view", "get", "retrieve", "lookup", "look"},
    "search": {"search", "find", "lookup", "query", "filter", "list", "discover"},
    "create": {"create", "add", "make", "generate", "schedule", "insert", "write"},
    "update": {"update", "edit", "modify", "change", "patch", "rename", "set"},
    "delete": {"delete", "remove", "erase", "destroy", "drop"},
    "send": {"send", "email", "message", "notify", "post", "publish", "share"},
    "compute": {"calculate", "compute", "convert", "estimate", "solve", "measure"},
    "transfer": {"transfer", "move", "pay", "deposit", "withdraw"},
}

_NEGATIVE_MARKERS = (
    "unrelated to",
    "out of domain",
    "should not be called",
    "is a distractor",
    "do not use",
    "do not call",
    "without using",
)
_NO_TOOL_MARKERS = (
    "no tool call",
    "do not actually call",
    "don't actually call",
    "planning only",
    "only want a checklist",
)
_MISSING_INFO_MARKERS = (
    "do not know",
    "don't know",
    "missing",
    "not sure what input",
    "not sure which",
    "provide later",
    "send later",
)


@dataclass
class LearnedRouterDecision:
    score: float
    route_bonus: int
    negative_boundary: bool
    feature_vector: Dict[str, float]
    positive_features: List[Dict[str, float]]
    negative_features: List[Dict[str, float]]
    threshold: float
    policy_action: str = "call"
    risk_score: float = 0.0
    components: Dict[str, float] = field(default_factory=dict)

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


def learn_global_router_policy(tools: Mapping[str, ToolIR], behavior_cases: Iterable[Any]) -> Dict[str, Any]:
    """Learn a shared pairwise prior for route/call risk across all tools."""

    cases = list(behavior_cases)
    training_rows: List[Tuple[Dict[str, float], float, float, str]] = []
    for case in cases:
        request = str(getattr(case, "user_request", "") or "")
        if not request:
            continue
        positive_tool_name = str(getattr(case, "expected_tool_name", "") or getattr(case, "tool_name", "") or "")
        if bool(getattr(case, "should_trigger", False)) and positive_tool_name in tools:
            positive_tool = tools[positive_tool_name]
            training_rows.append((_feature_vector(request, positive_tool, _minimal_skill_for_tool(positive_tool)), 1.0, 1.25, "global_positive"))
            for candidate in _global_hard_negative_tools(request, positive_tool_name, tools, limit=5):
                training_rows.append((_feature_vector(request, candidate, _minimal_skill_for_tool(candidate)), -1.0, 1.0, "global_pairwise_hard_negative"))
        negative_name = str(getattr(case, "negative_target", "") or "")
        if negative_name in tools:
            negative_tool = tools[negative_name]
            training_rows.append((_feature_vector(request, negative_tool, _minimal_skill_for_tool(negative_tool)), -1.0, 1.4, "global_targeted_negative"))

    if not training_rows:
        return {
            "name": "global_pairwise_dev_router_prior",
            "enabled": False,
            "test_controls_used": False,
            "disabled_reason": "no_global_router_training_rows",
        }

    weights = _train_margin_perceptron(
        training_rows,
        initial_weights=_default_weights(),
        epochs=10,
        learning_rate=0.08,
        target_margin=2.0,
    )
    summary = _training_score_summary(weights, training_rows)
    hard_rows = _mine_margin_violations(weights, training_rows, target_margin=2.5)
    if hard_rows:
        weights = _train_margin_perceptron(
            [*training_rows, *hard_rows],
            initial_weights=weights,
            epochs=6,
            learning_rate=0.06,
            target_margin=2.5,
        )
        summary = _training_score_summary(weights, training_rows)

    return {
        "name": "global_pairwise_dev_router_prior",
        "enabled": True,
        "learner": "weighted_margin_perceptron",
        "source": "all_dev_controls_pairwise_tool_risk",
        "test_controls_used": False,
        "num_tools": len(tools),
        "training_row_count": len(training_rows),
        "self_mined_hard_row_count": len(hard_rows),
        "weights": _round_weights(weights),
        "training_positive_score_mean": summary["positive_mean"],
        "training_negative_score_mean": summary["negative_mean"],
    }


def learn_router_policy(
    tool: ToolIR,
    skill: GeneratedSkill,
    behavior_cases: Iterable[Any],
    *,
    global_router_policy: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Learn a per-tool risk policy, seeded by a global pairwise router prior."""

    positive_cases: List[Any] = []
    targeted_negative_cases: List[Any] = []
    hard_cross_negatives: List[Tuple[int, Any]] = []
    signature = _tool_signature_tokens(tool, skill)
    for case in behavior_cases:
        request = str(getattr(case, "user_request", "") or "")
        if str(getattr(case, "tool_name", "")) == tool.tool_name and bool(getattr(case, "should_trigger", False)):
            positive_cases.append(case)
        elif _case_is_negative_for_tool(case, tool.tool_name):
            targeted_negative_cases.append(case)
        elif bool(getattr(case, "should_trigger", False)) and str(getattr(case, "tool_name", "")) != tool.tool_name:
            overlap = len(_tokens(request).intersection(signature))
            if overlap > 0 or _action_family_conflict(request, tool):
                hard_cross_negatives.append((overlap, case))

    hard_cross_negatives.sort(key=lambda item: (-item[0], str(getattr(item[1], "case_id", ""))))
    negative_cases = targeted_negative_cases[:32] + [case for _overlap, case in hard_cross_negatives[:24]]
    if not positive_cases or not negative_cases:
        return {
            "name": "dev_learned_risk_aware_router_policy",
            "enabled": False,
            "source": "dev_positive_and_negative_behavior_controls",
            "test_controls_used": False,
            "positive_example_count": len(positive_cases),
            "negative_example_count": len(negative_cases),
            "disabled_reason": "insufficient_positive_or_negative_dev_controls",
        }

    local_rows: List[Tuple[Dict[str, float], float, float, str]] = []
    for case in positive_cases[:32]:
        local_rows.append((_feature_vector(str(getattr(case, "user_request", "") or ""), tool, skill), 1.0, 1.25, "tool_positive"))
    for case in targeted_negative_cases[:32]:
        local_rows.append((_feature_vector(str(getattr(case, "user_request", "") or ""), tool, skill), -1.0, 1.5, "targeted_negative"))
    for _overlap, case in hard_cross_negatives[:24]:
        local_rows.append((_feature_vector(str(getattr(case, "user_request", "") or ""), tool, skill), -1.0, 1.15, "cross_tool_hard_negative"))

    local_weights = _train_margin_perceptron(
        local_rows,
        initial_weights=_default_weights(),
        epochs=14,
        learning_rate=0.12,
        target_margin=2.0,
    )
    global_weights = (
        global_router_policy.get("weights")
        if isinstance(global_router_policy, dict) and isinstance(global_router_policy.get("weights"), dict)
        else {}
    )
    global_training_scale = DEFAULT_GLOBAL_ROUTER_PRIOR_TRAINING_SCALE if global_weights else 0.0
    global_inference_scale = DEFAULT_GLOBAL_ROUTER_PRIOR_INFERENCE_SCALE if global_weights else 0.0
    pre_hard_weights = _combine_weights(local_weights, global_weights, global_scale=global_training_scale)
    pre_hard_summary = _training_score_summary(pre_hard_weights, local_rows)
    pre_hard_threshold = _threshold_from_summary(pre_hard_summary)
    hard_rows = _mine_margin_violations(pre_hard_weights, local_rows, target_margin=3.0)
    hard_negative_delta: Dict[str, float] = {}
    final_weights = pre_hard_weights
    if hard_rows:
        refined_weights = _train_margin_perceptron(
            [*local_rows, *hard_rows],
            initial_weights=pre_hard_weights,
            epochs=8,
            learning_rate=0.08,
            target_margin=3.0,
        )
        hard_negative_delta = {
            name: refined_weights.get(name, 0.0) - pre_hard_weights.get(name, 0.0)
            for name in set(refined_weights).union(pre_hard_weights)
            if abs(refined_weights.get(name, 0.0) - pre_hard_weights.get(name, 0.0)) > 1e-9
        }
        final_weights = refined_weights
    final_summary = _training_score_summary(final_weights, local_rows)
    threshold = _threshold_from_summary(final_summary)

    return {
        "name": "dev_learned_risk_aware_router_policy",
        "enabled": True,
        "learner": "global_seeded_weighted_margin_perceptron",
        "source": "dev_positive_and_negative_behavior_controls",
        "test_controls_used": False,
        "positive_example_count": len(positive_cases),
        "negative_example_count": len(negative_cases),
        "targeted_negative_example_count": len(targeted_negative_cases),
        "hard_cross_negative_example_count": len(hard_cross_negatives),
        "self_mined_hard_row_count": len(hard_rows),
        "uses_global_pairwise_prior": bool(global_weights),
        "uses_hard_negative_self_training": bool(hard_rows),
        "local_weights": _round_weights(local_weights),
        "global_prior_weights": _round_weights(global_weights),
        "global_prior_training_scale": global_training_scale,
        "global_prior_inference_scale": global_inference_scale,
        "global_prior_legacy_inference_scale": global_training_scale,
        "global_prior_scale": global_inference_scale,
        "global_prior_role": "distillation_teacher",
        "pre_hard_weights": _round_weights(pre_hard_weights),
        "hard_negative_delta_weights": _round_weights(hard_negative_delta),
        "weights": _round_weights(final_weights),
        "pre_hard_threshold": round(pre_hard_threshold, 5),
        "threshold": round(threshold, 5),
        "training_positive_score_mean": final_summary["positive_mean"],
        "training_negative_score_mean": final_summary["negative_mean"],
        "pre_hard_positive_score_mean": pre_hard_summary["positive_mean"],
        "pre_hard_negative_score_mean": pre_hard_summary["negative_mean"],
        "route_bonus_scale": 5.0,
        "max_route_bonus": 36,
        "negative_boundary_threshold": -3.0,
    }


def score_learned_router(query: str, tool: ToolIR, skill: GeneratedSkill) -> LearnedRouterDecision:
    policy = _policy_from_skill(skill)
    if not policy.get("enabled"):
        return LearnedRouterDecision(0.0, 0, False, {}, [], [], 0.0)
    flags = _contract_ablation_flags(skill)
    if flags.get("disable_learned_router_policy"):
        return LearnedRouterDecision(0.0, 0, False, {}, [], [], 0.0)
    weights = _effective_policy_weights(policy, flags)
    features = _feature_vector(query, tool, skill)
    if flags.get("disable_explicit_boundary_certificate"):
        features["explicit_tool_request"] = 0.0
    threshold_key = "pre_hard_threshold" if flags.get("disable_hard_negative_policy") else "threshold"
    threshold = _float(policy.get(threshold_key), _float(policy.get("threshold"), 0.0))
    raw_score = _dot(weights, features) - threshold
    scale = _float(policy.get("route_bonus_scale"), 5.0)
    max_bonus = max(int(policy.get("max_route_bonus") or 36), 0)
    route_bonus = int(round(max(-max_bonus, min(max_bonus, raw_score * scale))))
    negative_boundary = _negative_boundary(
        query,
        tool,
        raw_score,
        features,
        policy,
        explicit_boundary_disabled=bool(flags.get("disable_explicit_boundary_certificate")),
    )
    positive_features, negative_features = _feature_contributions(weights, features)
    risk_score = _risk_score(raw_score, features)
    action = "abstain" if negative_boundary else "call"
    return LearnedRouterDecision(
        score=round(raw_score, 4),
        route_bonus=route_bonus,
        negative_boundary=negative_boundary,
        feature_vector={name: round(value, 4) for name, value in sorted(features.items()) if value},
        positive_features=positive_features,
        negative_features=negative_features,
        threshold=round(threshold, 4),
        policy_action=action,
        risk_score=round(risk_score, 4),
        components={
            "local": round(_dot(policy.get("local_weights") or policy.get("weights") or {}, features), 4),
            "global_prior": round(
                _dot(policy.get("global_prior_weights") or {}, features) * _global_prior_inference_scale(policy, flags), 4
            ),
            "hard_negative_delta": round(_dot(policy.get("hard_negative_delta_weights") or {}, features), 4),
        },
    )


def _feature_vector(query: str, tool: ToolIR, skill: GeneratedSkill) -> Dict[str, float]:
    query_tokens = _tokens(query)
    normalized = normalize_routing_text(query)
    tool_name_tokens = _tokens(tool.tool_name.replace("_", " "))
    purpose_tokens = _tokens(tool.tool_purpose or "")
    skill_positive_tokens = _tokens(" ".join([skill.skill_summary, *skill.when_to_use, *_example_scenarios(skill)]))
    skill_negative_tokens = _tokens(" ".join(skill.when_not_to_use))
    argument_tokens = _argument_tokens(tool)
    explicit_arg_names = _explicit_argument_names(query)
    allowed_arg_names = {arg.name.lower() for arg in tool.arguments}
    required_arg_names = {arg.name.lower() for arg in tool.arguments if arg.required}
    optional_arg_names = allowed_arg_names - required_arg_names
    matched_required = _matched_argument_count(query, required_arg_names)
    matched_optional = _matched_argument_count(query, optional_arg_names)
    unknown_args = explicit_arg_names - allowed_arg_names
    request_actions = _action_families(query)
    tool_actions = _tool_action_families(tool)

    all_tool_name_terms = bool(tool_name_tokens and tool_name_tokens.issubset(query_tokens))
    compact_tool_name = tool.tool_name.lower()
    spaced_tool_name = compact_tool_name.replace("_", " ")
    tool_name_mentioned = compact_tool_name in normalized.replace(" ", "_") or spaced_tool_name in normalized
    if not tool_name_mentioned and all_tool_name_terms and len(tool_name_tokens) >= 2:
        tool_name_mentioned = True

    return {
        "bias": 1.0,
        "explicit_tool_request": min(explicit_requested_tool_score(query, tool.tool_name) / 100.0, 1.0),
        "tool_name_mentioned": 1.0 if tool_name_mentioned else 0.0,
        "tool_name_overlap": _normalized_overlap(query_tokens, tool_name_tokens),
        "purpose_overlap": _normalized_overlap(query_tokens, purpose_tokens),
        "skill_positive_overlap": _normalized_overlap(query_tokens, skill_positive_tokens),
        "skill_negative_overlap": _normalized_overlap(query_tokens, skill_negative_tokens),
        "argument_overlap": _normalized_overlap(query_tokens, argument_tokens),
        "matched_required_args": matched_required / max(len(required_arg_names), 1),
        "matched_optional_args": matched_optional / max(len(optional_arg_names), 1) if optional_arg_names else 0.0,
        "unknown_explicit_args": min(float(len(unknown_args)), 3.0),
        "action_family_overlap": float(len(request_actions.intersection(tool_actions))),
        "action_family_conflict": 1.0 if request_actions and tool_actions and request_actions.isdisjoint(tool_actions) else 0.0,
        "negative_marker": 1.0 if _has_marker(query, _NEGATIVE_MARKERS) else 0.0,
        "no_tool_marker": 1.0 if _has_marker(query, _NO_TOOL_MARKERS) else 0.0,
        "missing_info_marker": 1.0 if _has_marker(query, _MISSING_INFO_MARKERS) else 0.0,
        "read_write_conflict": 1.0 if _read_write_conflict(query, tool_actions) else 0.0,
        "side_effect_conflict": 1.0 if _side_effect_conflict(query, tool) else 0.0,
    }


def _default_weights() -> Dict[str, float]:
    return {
        "bias": -0.5,
        "explicit_tool_request": 5.0,
        "tool_name_mentioned": 3.5,
        "tool_name_overlap": 2.5,
        "purpose_overlap": 2.0,
        "skill_positive_overlap": 1.4,
        "skill_negative_overlap": -2.2,
        "argument_overlap": 1.2,
        "matched_required_args": 1.3,
        "matched_optional_args": 0.5,
        "unknown_explicit_args": -2.5,
        "action_family_overlap": 2.0,
        "action_family_conflict": -4.8,
        "negative_marker": -4.0,
        "no_tool_marker": -5.5,
        "missing_info_marker": -3.5,
        "read_write_conflict": -5.5,
        "side_effect_conflict": -5.0,
    }


def _train_margin_perceptron(
    rows: List[Tuple[Dict[str, float], float, float, str]],
    *,
    initial_weights: Dict[str, Any],
    epochs: int,
    learning_rate: float,
    target_margin: float,
) -> Dict[str, float]:
    weights = {name: _float(value) for name, value in initial_weights.items()}
    for _epoch in range(epochs):
        for features, label, weight, _source in rows:
            margin = label * _dot(weights, features)
            if margin >= target_margin:
                continue
            step = learning_rate * max(weight, 0.1) * min(target_margin - margin, target_margin + 2.0)
            for name, value in features.items():
                if value:
                    weights[name] = weights.get(name, 0.0) + step * label * value
    return weights


def _mine_margin_violations(
    weights: Dict[str, float],
    rows: List[Tuple[Dict[str, float], float, float, str]],
    *,
    target_margin: float,
) -> List[Tuple[Dict[str, float], float, float, str]]:
    mined: List[Tuple[Dict[str, float], float, float, str]] = []
    ranked: List[Tuple[float, Dict[str, float], float, float, str]] = []
    for features, label, weight, source in rows:
        margin = label * _dot(weights, features)
        ranked.append((margin, features, label, weight, source))
        if margin < target_margin:
            mined.append((features, label, max(weight * 1.75, weight + 0.5), f"self_mined_{source}"))
    if not mined:
        for _margin, features, label, weight, source in sorted(ranked, key=lambda item: item[0])[:2]:
            mined.append((features, label, max(weight * 1.4, weight + 0.25), f"self_mined_hardest_{source}"))
    mined.sort(key=lambda item: item[1] * _dot(weights, item[0]))
    return mined[:48]


def _training_score_summary(weights: Dict[str, float], rows: List[Tuple[Dict[str, float], float, float, str]]) -> Dict[str, float]:
    positive_scores = [_dot(weights, features) for features, label, _weight, _source in rows if label > 0]
    negative_scores = [_dot(weights, features) for features, label, _weight, _source in rows if label < 0]
    positive_mean = sum(positive_scores) / len(positive_scores) if positive_scores else 0.0
    negative_mean = sum(negative_scores) / len(negative_scores) if negative_scores else 0.0
    return {"positive_mean": round(positive_mean, 5), "negative_mean": round(negative_mean, 5)}


def _threshold_from_summary(summary: Dict[str, float]) -> float:
    positive_mean = _float(summary.get("positive_mean"), 0.0)
    negative_mean = _float(summary.get("negative_mean"), 0.0)
    return (positive_mean + negative_mean) / 2.0 if positive_mean > negative_mean else 0.0


def _combine_weights(local_weights: Dict[str, Any], global_weights: Dict[str, Any], *, global_scale: float) -> Dict[str, float]:
    result = {name: _float(value) for name, value in local_weights.items()}
    for name, value in global_weights.items():
        result[name] = result.get(name, 0.0) + global_scale * _float(value)
    return result


def _effective_policy_weights(policy: Dict[str, Any], flags: Dict[str, Any]) -> Dict[str, float]:
    local_weights = policy.get("local_weights")
    if not isinstance(local_weights, dict):
        return {name: _float(value) for name, value in (policy.get("weights") if isinstance(policy.get("weights"), dict) else {}).items()}
    weights = {name: _float(value) for name, value in local_weights.items()}
    global_scale = _global_prior_inference_scale(policy, flags)
    if global_scale:
        weights = _combine_weights(
            weights,
            policy.get("global_prior_weights") if isinstance(policy.get("global_prior_weights"), dict) else {},
            global_scale=global_scale,
        )
    if not flags.get("disable_hard_negative_policy"):
        for name, value in (policy.get("hard_negative_delta_weights") if isinstance(policy.get("hard_negative_delta_weights"), dict) else {}).items():
            weights[name] = weights.get(name, 0.0) + _float(value)
    return weights


def _global_prior_inference_scale(policy: Dict[str, Any], flags: Dict[str, Any]) -> float:
    if flags.get("disable_global_router_prior"):
        return 0.0
    if flags.get("enable_global_router_prior"):
        return _float(
            policy.get("global_prior_legacy_inference_scale"),
            _float(policy.get("global_prior_training_scale"), _float(policy.get("global_prior_scale"), 0.0)),
        )
    return _float(policy.get("global_prior_inference_scale"), 0.0)


def _contract_ablation_flags(skill: GeneratedSkill) -> Dict[str, Any]:
    flags = skill.metadata.get("contract_ablation_flags") if isinstance(skill.metadata, dict) else None
    return flags if isinstance(flags, dict) else {}


def _risk_score(raw_score: float, features: Dict[str, float]) -> float:
    structural_risk = (
        1.5 * features.get("action_family_conflict", 0.0)
        + 1.5 * features.get("read_write_conflict", 0.0)
        + 1.3 * features.get("side_effect_conflict", 0.0)
        + 1.0 * features.get("negative_marker", 0.0)
        + 1.0 * features.get("no_tool_marker", 0.0)
        + 0.8 * features.get("missing_info_marker", 0.0)
    )
    return max(0.0, structural_risk - max(raw_score, 0.0) * 0.1)


def _global_hard_negative_tools(request: str, positive_tool_name: str, tools: Mapping[str, ToolIR], *, limit: int) -> List[ToolIR]:
    request_tokens = _tokens(request)
    scored: List[Tuple[float, str, ToolIR]] = []
    for name, tool in tools.items():
        if name == positive_tool_name:
            continue
        signature = _tool_signature_tokens(tool, _minimal_skill_for_tool(tool))
        overlap = len(request_tokens.intersection(signature))
        action_conflict = 1 if _action_family_conflict(request, tool) else 0
        score = float(overlap + action_conflict)
        if score > 0:
            scored.append((score, name, tool))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [tool for _score, _name, tool in scored[:limit]]


def _minimal_skill_for_tool(tool: ToolIR) -> GeneratedSkill:
    return GeneratedSkill(
        baseline_name="global_router_prior",
        skill_summary=tool.tool_purpose or tool.tool_name.replace("_", " "),
        when_to_use=[f"Use {tool.tool_name} for requests matching its schema and purpose."],
        when_not_to_use=[
            "Do not use for adjacent tools, missing required arguments, read/write mismatches, or explanation-only requests."
        ],
    )


def _round_weights(weights: Dict[str, Any]) -> Dict[str, float]:
    return {name: round(_float(value), 5) for name, value in sorted(weights.items()) if abs(_float(value)) > 1e-9}


def _negative_boundary(
    query: str,
    tool: ToolIR,
    raw_score: float,
    features: Dict[str, float],
    policy: Dict[str, Any],
    *,
    explicit_boundary_disabled: bool = False,
) -> bool:
    if not explicit_boundary_disabled and explicit_requested_tool_score(query, tool.tool_name) > 0:
        return False
    threshold = _float(policy.get("negative_boundary_threshold"), -3.0)
    if raw_score > threshold:
        return False
    if features.get("negative_marker") or features.get("no_tool_marker") or features.get("missing_info_marker"):
        return True
    if features.get("action_family_conflict") and (features.get("skill_negative_overlap") or features.get("read_write_conflict")):
        return True
    if features.get("side_effect_conflict") and raw_score <= threshold - 1.5:
        return True
    return False


def _feature_contributions(weights: Dict[str, Any], features: Dict[str, float]) -> Tuple[List[Dict[str, float]], List[Dict[str, float]]]:
    rows: List[Tuple[str, float]] = []
    for name, value in features.items():
        contribution = _float(weights.get(name), 0.0) * value
        if contribution:
            rows.append((name, contribution))
    positives = [
        {"feature": name, "contribution": round(value, 4)}
        for name, value in sorted(rows, key=lambda item: -item[1])
        if value > 0
    ][:5]
    negatives = [
        {"feature": name, "contribution": round(value, 4)}
        for name, value in sorted(rows, key=lambda item: item[1])
        if value < 0
    ][:5]
    return positives, negatives


def _policy_from_skill(skill: GeneratedSkill) -> Dict[str, Any]:
    if isinstance(skill.metadata, dict):
        raw = skill.metadata.get("learned_router_policy")
        if isinstance(raw, dict):
            return raw
        method = skill.metadata.get("method_metadata")
        if isinstance(method, dict) and isinstance(method.get("learned_router_policy"), dict):
            return method["learned_router_policy"]
    return {"enabled": False}


def _case_is_negative_for_tool(case: Any, tool_name: str) -> bool:
    if bool(getattr(case, "should_trigger", False)):
        return False
    return str(getattr(case, "tool_name", "")) == tool_name or str(getattr(case, "negative_target", "")) == tool_name


def _tool_signature_tokens(tool: ToolIR, skill: GeneratedSkill) -> set[str]:
    tokens = _tokens(tool.tool_name.replace("_", " "))
    tokens.update(_tokens(tool.tool_purpose or ""))
    tokens.update(_argument_tokens(tool))
    tokens.update(_tokens(skill.skill_summary))
    return tokens


def _argument_tokens(tool: ToolIR) -> set[str]:
    tokens: set[str] = set()
    for arg in tool.arguments:
        tokens.update(_tokens(arg.name.replace("_", " ")))
        tokens.update(_tokens(arg.description or ""))
        for child_name in (arg.properties or {}):
            tokens.update(_tokens(str(child_name).replace("_", " ")))
    return tokens


def _example_scenarios(skill: GeneratedSkill) -> List[str]:
    return [
        str(example.get("scenario", ""))
        for example in skill.examples
        if isinstance(example, dict) and str(example.get("scenario", ""))
    ]


def _explicit_argument_names(query: str) -> set[str]:
    return {
        match.group(1).lower()
        for match in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_.-]*)\s*(?:=|:)", query)
    }


def _matched_argument_count(query: str, arg_names: set[str]) -> int:
    if not arg_names:
        return 0
    normalized = normalize_routing_text(query)
    count = 0
    for name in arg_names:
        spaced = name.replace("_", " ").replace("-", " ")
        if name in normalized.replace(" ", "_") or spaced in normalized:
            count += 1
    return count


def _tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for raw in re.findall(r"[a-zA-Z0-9_./-]+", text.lower()):
        token = raw.strip(".,;:!?()[]{}\"'")
        if not token or token in _STOPWORDS or len(token) <= 1:
            continue
        parts = [token]
        parts.extend(part for part in re.split(r"[_./-]+", token) if part)
        for part in parts:
            if part and part not in _STOPWORDS and len(part) > 1:
                tokens.add(part)
                if part.endswith("s") and len(part) > 4:
                    tokens.add(part[:-1])
                if part.endswith("ing") and len(part) > 5:
                    tokens.add(part[:-3])
    return tokens


def _normalized_overlap(query_tokens: set[str], source_tokens: set[str]) -> float:
    if not query_tokens or not source_tokens:
        return 0.0
    return len(query_tokens.intersection(source_tokens)) / math.sqrt(max(len(source_tokens), 1))


def _action_families(text: str) -> set[str]:
    lowered = text.lower()
    tokens = _tokens(text)
    families: set[str] = set()
    for family, terms in _ACTION_FAMILIES.items():
        if tokens.intersection(terms) or any(f" {term} " in f" {lowered} " for term in terms):
            families.add(family)
    return families


def _tool_action_families(tool: ToolIR) -> set[str]:
    text = " ".join(
        [
            tool.tool_name.replace("_", " "),
            tool.tool_purpose or "",
            " ".join(str(hint) for hint in tool.side_effect_hints),
        ]
    )
    families = _action_families(text)
    for hint in tool.side_effect_hints:
        lowered = str(hint).lower()
        if lowered in {"write", "mutation"}:
            families.update({"create", "update"})
        if lowered in {"read", "readonly", "read_only"}:
            families.add("read")
    return families


def _action_family_conflict(query: str, tool: ToolIR) -> bool:
    request_actions = _action_families(query)
    tool_actions = _tool_action_families(tool)
    return bool(request_actions and tool_actions and request_actions.isdisjoint(tool_actions))


def _read_write_conflict(query: str, tool_actions: set[str]) -> bool:
    lowered = query.lower()
    read_only = any(marker in lowered for marker in ("read-only", "only inspect", "only preview", "do not create", "do not update", "do not delete", "do not modify"))
    write_like = bool(tool_actions.intersection({"create", "update", "delete", "send", "transfer"}))
    return read_only and write_like


def _side_effect_conflict(query: str, tool: ToolIR) -> bool:
    lowered = query.lower()
    side_effects = {str(hint).lower() for hint in tool.side_effect_hints}
    if side_effects.intersection({"write", "destructive", "send", "network", "mutation"}):
        return any(
            marker in lowered
            for marker in ("do not send", "do not write", "do not create", "do not update", "do not delete", "read-only", "preview only")
        )
    return False


def _has_marker(query: str, markers: Tuple[str, ...]) -> bool:
    lowered = query.lower()
    return any(marker in lowered for marker in markers)


def _dot(weights: Dict[str, Any], features: Dict[str, float]) -> float:
    return sum(_float(weights.get(name), 0.0) * value for name, value in features.items())


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import re
from typing import Any, Dict, Iterable, List, Tuple

from autoskill.contract_decision import explicit_requested_tool_score
from autoskill.ir import GeneratedSkill, ToolIR
from autoskill.routing_boundaries import normalize_routing_text


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

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


def learn_router_policy(tool: ToolIR, skill: GeneratedSkill, behavior_cases: Iterable[Any]) -> Dict[str, Any]:
    """Learn a small auditable router policy from dev behavior controls.

    The policy is intentionally compact: it learns weights over interpretable
    contract/routing features rather than memorizing test cases or calling a
    second model at inference time.
    """

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

    training_rows: List[Tuple[Dict[str, float], float]] = []
    for case in positive_cases[:32]:
        training_rows.append((_feature_vector(str(getattr(case, "user_request", "") or ""), tool, skill), 1.0))
    for case in negative_cases[:56]:
        training_rows.append((_feature_vector(str(getattr(case, "user_request", "") or ""), tool, skill), -1.0))

    weights = dict(_default_weights())
    learning_rate = 0.12
    target_margin = 2.0
    for _epoch in range(16):
        for features, label in training_rows:
            margin = label * _dot(weights, features)
            if margin >= target_margin:
                continue
            for name, value in features.items():
                weights[name] = weights.get(name, 0.0) + learning_rate * label * value

    positive_scores = [_dot(weights, features) for features, label in training_rows if label > 0]
    negative_scores = [_dot(weights, features) for features, label in training_rows if label < 0]
    positive_mean = sum(positive_scores) / len(positive_scores)
    negative_mean = sum(negative_scores) / len(negative_scores)
    if positive_mean > negative_mean:
        threshold = (positive_mean + negative_mean) / 2.0
    else:
        threshold = 0.0

    return {
        "name": "dev_learned_risk_aware_router_policy",
        "enabled": True,
        "learner": "margin_perceptron",
        "source": "dev_positive_and_negative_behavior_controls",
        "test_controls_used": False,
        "positive_example_count": len(positive_cases),
        "negative_example_count": len(negative_cases),
        "targeted_negative_example_count": len(targeted_negative_cases),
        "hard_cross_negative_example_count": len(hard_cross_negatives),
        "weights": {name: round(value, 5) for name, value in sorted(weights.items())},
        "threshold": round(threshold, 5),
        "training_positive_score_mean": round(positive_mean, 5),
        "training_negative_score_mean": round(negative_mean, 5),
        "route_bonus_scale": 5.0,
        "max_route_bonus": 36,
        "negative_boundary_threshold": -3.0,
    }


def score_learned_router(query: str, tool: ToolIR, skill: GeneratedSkill) -> LearnedRouterDecision:
    policy = _policy_from_skill(skill)
    if not policy.get("enabled"):
        return LearnedRouterDecision(0.0, 0, False, {}, [], [], 0.0)
    weights = policy.get("weights") if isinstance(policy.get("weights"), dict) else {}
    features = _feature_vector(query, tool, skill)
    threshold = _float(policy.get("threshold"), 0.0)
    raw_score = _dot(weights, features) - threshold
    scale = _float(policy.get("route_bonus_scale"), 5.0)
    max_bonus = max(int(policy.get("max_route_bonus") or 36), 0)
    route_bonus = int(round(max(-max_bonus, min(max_bonus, raw_score * scale))))
    negative_boundary = _negative_boundary(query, tool, raw_score, features, policy)
    positive_features, negative_features = _feature_contributions(weights, features)
    return LearnedRouterDecision(
        score=round(raw_score, 4),
        route_bonus=route_bonus,
        negative_boundary=negative_boundary,
        feature_vector={name: round(value, 4) for name, value in sorted(features.items()) if value},
        positive_features=positive_features,
        negative_features=negative_features,
        threshold=round(threshold, 4),
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


def _negative_boundary(query: str, tool: ToolIR, raw_score: float, features: Dict[str, float], policy: Dict[str, Any]) -> bool:
    if explicit_requested_tool_score(query, tool.tool_name) > 0:
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

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import math
import re
from typing import Any, Dict, Iterable, List

from autoskill.contract_decision import explicit_requested_tool_score
from autoskill.ir import GeneratedSkill, ToolIR


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


@dataclass
class ContrastiveMemoryDecision:
    score: float
    route_bonus: int
    positive_score: float
    negative_score: float
    positive_terms: List[str]
    negative_terms: List[str]
    positive_prototype_id: str | None
    negative_prototype_id: str | None
    negative_boundary: bool

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


def learn_contrastive_memory_policy(tool: ToolIR, skill: GeneratedSkill, behavior_cases: Iterable[Any]) -> Dict[str, Any]:
    positive_cases: List[Any] = []
    negative_cases: List[Any] = []
    for case in behavior_cases:
        if str(getattr(case, "tool_name", "")) == tool.tool_name and bool(getattr(case, "should_trigger", False)):
            positive_cases.append(case)
        elif _case_is_negative_for_tool(case, tool.tool_name):
            negative_cases.append(case)

    signature = _tool_signature_tokens(tool)
    positive_prototypes = _build_prototypes(positive_cases, signature, positive=True, limit=8)
    negative_prototypes = _build_prototypes(negative_cases, signature, positive=False, limit=12)
    positive_counts = Counter(token for proto in positive_prototypes for token in proto["tokens"])
    negative_counts = Counter(token for proto in negative_prototypes for token in proto["tokens"])
    positive_terms = [
        token
        for token, count in positive_counts.most_common()
        if count >= max(1, negative_counts.get(token, 0)) and token not in signature
    ][:32]
    negative_terms = [
        token
        for token, count in negative_counts.most_common()
        if count > positive_counts.get(token, 0) and token not in signature
    ][:32]
    return {
        "name": "dev_learned_contrastive_memory_policy",
        "enabled": True,
        "source": "dev_positive_and_negative_behavior_controls",
        "test_controls_used": False,
        "positive_exemplar_count": len(positive_cases),
        "negative_exemplar_count": len(negative_cases),
        "positive_terms": positive_terms,
        "negative_terms": negative_terms,
        "positive_prototypes": positive_prototypes,
        "negative_prototypes": negative_prototypes,
        "route_bonus_scale": 2.0,
        "max_route_bonus": 24,
        "negative_boundary_threshold": -6.0,
        "negative_boundary_margin": 4.0,
    }


def score_contrastive_memory(query: str, tool: ToolIR, skill: GeneratedSkill) -> ContrastiveMemoryDecision:
    policy = _policy_from_skill(skill)
    if not policy.get("enabled"):
        return ContrastiveMemoryDecision(0.0, 0, 0.0, 0.0, [], [], None, None, False)
    flags = _contract_ablation_flags(skill)
    query_tokens = _tokens(query)
    if not query_tokens:
        return ContrastiveMemoryDecision(0.0, 0, 0.0, 0.0, [], [], None, None, False)
    positive_score, positive_id, positive_terms = _prototype_score(query_tokens, policy.get("positive_prototypes"))
    negative_score, negative_id, negative_terms = _prototype_score(query_tokens, policy.get("negative_prototypes"))
    positive_terms_score = len(query_tokens.intersection(set(policy.get("positive_terms") or []))) * 1.5
    negative_terms_score = len(query_tokens.intersection(set(policy.get("negative_terms") or []))) * 1.5
    positive_total = positive_score + positive_terms_score
    negative_total = negative_score + negative_terms_score
    score = positive_total - negative_total
    scale = _float(policy.get("route_bonus_scale"), 2.0)
    max_bonus = max(int(policy.get("max_route_bonus") or 24), 0)
    route_bonus = int(round(max(-max_bonus, min(max_bonus, score * scale))))
    explicit_match = 0 if flags.get("disable_explicit_boundary_certificate") else explicit_requested_tool_score(query, tool.tool_name)
    negative_boundary = (
        score <= _float(policy.get("negative_boundary_threshold"), -6.0)
        and negative_total >= positive_total + _float(policy.get("negative_boundary_margin"), 4.0)
        and explicit_match <= 0
    )
    if _negative_marker(query) and negative_total > positive_total:
        negative_boundary = True
    return ContrastiveMemoryDecision(
        score=round(score, 4),
        route_bonus=route_bonus,
        positive_score=round(positive_total, 4),
        negative_score=round(negative_total, 4),
        positive_terms=positive_terms[:8],
        negative_terms=negative_terms[:8],
        positive_prototype_id=positive_id,
        negative_prototype_id=negative_id,
        negative_boundary=negative_boundary,
    )


def _case_is_negative_for_tool(case: Any, tool_name: str) -> bool:
    if bool(getattr(case, "should_trigger", False)):
        return False
    return str(getattr(case, "tool_name", "")) == tool_name or str(getattr(case, "negative_target", "")) == tool_name


def _build_prototypes(cases: List[Any], signature: set[str], *, positive: bool, limit: int) -> List[Dict[str, Any]]:
    prototypes: List[Dict[str, Any]] = []
    for case in cases:
        request = str(getattr(case, "user_request", "") or "")
        tokens = _tokens(request)
        if not positive:
            tokens = tokens - signature - {"unrelated", "related", "target", "distractor"}
        if not tokens:
            continue
        category = getattr(case, "negative_category", None)
        weight = 1.0
        if category == "out_of_domain_request":
            weight = 0.75
        if category in {"similar_tool_should_be_used", "near_miss_intent", "destructive_vs_readonly_mismatch"}:
            weight = 1.25
        prototypes.append(
            {
                "id": str(getattr(case, "case_id", "") or getattr(case, "task_id", "") or len(prototypes)),
                "tokens": sorted(tokens)[:48],
                "category": str(category or ("positive" if positive else "negative")),
                "weight": weight,
            }
        )
        if len(prototypes) >= limit:
            break
    return prototypes


def _prototype_score(query_tokens: set[str], prototypes: Any) -> tuple[float, str | None, List[str]]:
    if not isinstance(prototypes, list):
        return 0.0, None, []
    best_score = 0.0
    best_id: str | None = None
    best_terms: List[str] = []
    for prototype in prototypes:
        if not isinstance(prototype, dict):
            continue
        tokens = set(str(token) for token in prototype.get("tokens", []) if str(token))
        if not tokens:
            continue
        overlap = sorted(query_tokens.intersection(tokens))
        if not overlap:
            continue
        weight = _float(prototype.get("weight"), 1.0)
        normalized = len(overlap) / math.sqrt(max(len(tokens), 1))
        score = weight * (2.0 * len(overlap) + normalized)
        if score > best_score:
            best_score = score
            best_id = str(prototype.get("id") or "")
            best_terms = overlap
    return best_score, best_id, best_terms


def _policy_from_skill(skill: GeneratedSkill) -> Dict[str, Any]:
    raw = skill.metadata.get("contrastive_memory_policy") if isinstance(skill.metadata, dict) else None
    return raw if isinstance(raw, dict) else {"enabled": False}


def _contract_ablation_flags(skill: GeneratedSkill) -> Dict[str, Any]:
    flags = skill.metadata.get("contract_ablation_flags") if isinstance(skill.metadata, dict) else None
    return dict(flags) if isinstance(flags, dict) else {}


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


def _tool_signature_tokens(tool: ToolIR) -> set[str]:
    signature = _tokens(tool.tool_name.replace("_", " "))
    signature.update(_tokens(tool.tool_purpose or ""))
    for arg in tool.arguments:
        signature.update(_tokens(arg.name.replace("_", " ")))
    return signature


def _negative_marker(query: str) -> bool:
    lowered = query.lower()
    return any(
        marker in lowered
        for marker in (
            "unrelated to",
            "out of domain",
            "should not be called",
            "is a distractor",
            "do not use",
            "do not call",
        )
    )


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

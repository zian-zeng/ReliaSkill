from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable

from autoskill.routing_boundaries import normalize_routing_text, request_selects_tool


@dataclass
class ContractCandidateDecision:
    """Unified proof-margin decision for choosing a contrastive tool candidate."""

    tool_name: str
    decision: str
    score: float
    proof_score: float
    proof_margin: float | None
    explicit_request_match: int
    viable: bool
    missing_required_count: int
    reason: str

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


_NON_EXPLICIT_REDIRECT_REASONS = {
    "action_intent_conflict",
}


def explicit_requested_tool_score(request: str, tool_name: str) -> int:
    return 100 if request_selects_tool(request, tool_name) else 0


def row_explicit_request_match(row: Dict[str, Any], request: str = "") -> int:
    features = row.get("contract_routing_features")
    if isinstance(features, dict):
        try:
            value = int(features.get("explicit_request_match") or 0)
        except (TypeError, ValueError):
            value = 0
        if value > 0:
            return value
    tool_name = str(row.get("tool_name") or "")
    return explicit_requested_tool_score(request, tool_name) if tool_name and request else 0


def row_is_contract_viable(row: Dict[str, Any]) -> bool:
    if row.get("contract_viable") is not None:
        return bool(row.get("contract_viable"))
    if row.get("viable") is not None:
        return bool(row.get("viable"))
    return bool(row.get("contract_satisfied") or row.get("satisfied"))


def row_proof_score(row: Dict[str, Any]) -> float:
    for key in ("contract_proof_score", "proof_score", "score"):
        if key not in row:
            continue
        try:
            return float(row.get(key) or 0.0)
        except (TypeError, ValueError):
            continue
    return 0.0


def row_proof_margin(row: Dict[str, Any]) -> float | None:
    for key in ("contract_proof_margin", "proof_margin"):
        if key not in row:
            continue
        try:
            return float(row.get(key))
        except (TypeError, ValueError):
            continue
    return None


def choose_contrastive_contract_candidate(
    *,
    request: str,
    current_tool_name: str,
    rows: Iterable[Dict[str, Any]],
    current_reason: str | None = None,
    current_proof_score: float | None = None,
    allow_nonviable_explicit: bool = True,
    min_viable_margin: float = 8.0,
) -> ContractCandidateDecision | None:
    """Select a redirect target from proof rows using one shared ReliaSkill policy.

    Explicit user routing intent is allowed to choose a non-viable candidate, because
    that records the correct tool boundary while preserving abstention at call time.
    Without explicit intent, a redirect requires a viable candidate and a proof margin
    over the failed/current tool.
    """

    reason_text = str(current_reason or "")
    reason_allows_redirect = _reason_allows_redirect(reason_text)
    candidates: list[ContractCandidateDecision] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        tool_name = str(row.get("tool_name") or "")
        if not tool_name or tool_name == current_tool_name or tool_name == "__abstain__":
            continue
        if bool(row.get("action_intent_conflict")):
            continue
        explicit_score = row_explicit_request_match(row, request)
        viable = row_is_contract_viable(row)
        if explicit_score <= 0 and not (reason_allows_redirect and viable):
            continue
        if not viable and not (allow_nonviable_explicit and explicit_score > 0):
            continue
        proof_score = row_proof_score(row)
        if explicit_score <= 0 and current_proof_score is not None and proof_score < current_proof_score + min_viable_margin:
            continue
        missing_required = _missing_required_count(row)
        score = explicit_score + proof_score + (35.0 if viable else 0.0) - (10.0 * missing_required)
        candidates.append(
            ContractCandidateDecision(
                tool_name=tool_name,
                decision="redirect" if viable else "redirect_abstain",
                score=round(score, 4),
                proof_score=proof_score,
                proof_margin=row_proof_margin(row),
                explicit_request_match=explicit_score,
                viable=viable,
                missing_required_count=missing_required,
                reason=_decision_reason(explicit_score=explicit_score, viable=viable, current_reason=reason_text),
            )
        )
    if not candidates:
        return None
    candidates.sort(
        key=lambda item: (
            -item.explicit_request_match,
            not item.viable,
            item.missing_required_count,
            -item.proof_score,
            -item.score,
            item.tool_name,
        )
    )
    return candidates[0]


def _reason_allows_redirect(reason: str) -> bool:
    if not reason:
        return False
    normalized = normalize_routing_text(reason)
    return any(normalize_routing_text(token) in normalized for token in _NON_EXPLICIT_REDIRECT_REASONS)


def _decision_reason(*, explicit_score: int, viable: bool, current_reason: str) -> str:
    if explicit_score > 0 and viable:
        return "explicit_request_and_viable_contract"
    if explicit_score > 0:
        return "explicit_request_preserve_tool_boundary"
    if current_reason:
        return f"current_tool_blocked:{normalize_routing_text(current_reason)}"
    return "higher_margin_viable_contract"


def _missing_required_count(row: Dict[str, Any]) -> int:
    missing = row.get("missing_required_args")
    if isinstance(missing, list):
        return len(missing)
    return 0

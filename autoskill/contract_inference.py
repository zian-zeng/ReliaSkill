from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from autoskill.contracts import ContractEvaluation, build_contract_failure_report, evaluate_skill_contract
from autoskill.ir import GeneratedSkill, ToolIR


@dataclass
class ContractProofPolicy:
    name: str
    weights: Dict[str, float]
    call_threshold: float
    repair_threshold: float
    calibration_source: str

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ContractProofState:
    """A single tool candidate's proof state under the ReliaSkill contract."""

    tool_name: str
    satisfied: bool
    viable: bool
    decision: str
    proof_score: float
    proof_margin: float
    route_score: int
    feature_vector: Dict[str, float]
    proof_policy: Dict[str, Any]
    grounded_required_args: List[str]
    missing_required_args: List[str]
    blocking_reasons: List[str]
    request_actions: List[str]
    tool_actions: List[str]
    negated_actions: List[str]
    action_intent_conflict: bool
    side_effect_class: str
    proof_obligations: List[Dict[str, Any]] = field(default_factory=list)
    failure_report: Dict[str, Any] = field(default_factory=dict)
    policy_decision: Dict[str, Any] = field(default_factory=dict)
    grounding_sources: List[str] = field(default_factory=list)

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


def build_contract_proof_state(
    tool: ToolIR,
    skill: GeneratedSkill,
    request: str,
    *,
    arguments: Dict[str, Any] | None = None,
    grounding_context: Any | None = None,
    retrieval_score: int | float = 0,
    lexical_score: int | float = 0,
    boundary_penalty: int | float = 0,
) -> ContractProofState:
    """Build the declarative proof object used by routing, prompting, and audits."""
    evaluation = evaluate_skill_contract(
        tool,
        skill,
        request,
        arguments=arguments,
        grounding_context=grounding_context,
    )
    action_conflict = "action_intent_conflict" in evaluation.blocking_reasons
    policy = _contract_proof_policy(skill)
    features = _contract_proof_features(
        evaluation,
        retrieval_score=retrieval_score,
        lexical_score=lexical_score,
        boundary_penalty=boundary_penalty,
    )
    proof_score = _score_features(features, policy)
    decision = _proof_decision(evaluation, proof_score, policy)
    viable = decision == "call"
    return ContractProofState(
        tool_name=tool.tool_name,
        satisfied=evaluation.satisfied,
        viable=viable,
        decision=decision,
        proof_score=proof_score,
        proof_margin=round(proof_score - policy.call_threshold, 4),
        route_score=evaluation.routing_bonus,
        feature_vector=features,
        proof_policy=policy.model_dump(),
        grounded_required_args=list(evaluation.grounded_required_args),
        missing_required_args=list(evaluation.missing_required_args),
        blocking_reasons=list(evaluation.blocking_reasons),
        request_actions=list(evaluation.request_actions),
        tool_actions=list(evaluation.tool_actions),
        negated_actions=list(evaluation.negated_actions),
        action_intent_conflict=action_conflict,
        side_effect_class=evaluation.contract.side_effect_class,
        proof_obligations=[dict(item) for item in evaluation.proof_obligations],
        failure_report=build_contract_failure_report(evaluation),
        policy_decision=dict(evaluation.policy_decision),
        grounding_sources=list(evaluation.grounding_sources),
    )


def contract_state_payload(state: ContractProofState) -> Dict[str, Any]:
    """Compact prompt-safe view of a proof state."""
    return {
        "tool_name": state.tool_name,
        "satisfied": state.satisfied,
        "viable": state.viable,
        "decision": state.decision,
        "proof_score": round(state.proof_score, 4),
        "proof_margin": round(state.proof_margin, 4),
        "grounded_required_args": state.grounded_required_args,
        "missing_required_args": state.missing_required_args,
        "request_actions": state.request_actions,
        "tool_actions": state.tool_actions,
        "negated_actions": state.negated_actions,
        "blocking_reasons": state.blocking_reasons,
        "action_intent_conflict": state.action_intent_conflict,
        "failure_reason": state.failure_report.get("reason"),
        "policy": state.proof_policy.get("name"),
    }


def proof_state_is_viable(state: ContractProofState | Dict[str, Any]) -> bool:
    if isinstance(state, ContractProofState):
        return state.viable
    return bool(state.get("viable"))


def _contract_proof_policy(skill: GeneratedSkill) -> ContractProofPolicy:
    metadata_policy = skill.metadata.get("contract_proof_policy") if isinstance(skill.metadata, dict) else None
    default = default_contract_proof_policy()
    if not isinstance(metadata_policy, dict):
        return default
    weights = dict(default.weights)
    raw_weights = metadata_policy.get("weights")
    if isinstance(raw_weights, dict):
        for key, value in raw_weights.items():
            try:
                weights[str(key)] = float(value)
            except (TypeError, ValueError):
                continue
    return ContractProofPolicy(
        name=str(metadata_policy.get("name") or default.name),
        weights=weights,
        call_threshold=float(metadata_policy.get("call_threshold", default.call_threshold) or default.call_threshold),
        repair_threshold=float(metadata_policy.get("repair_threshold", default.repair_threshold) or default.repair_threshold),
        calibration_source=str(metadata_policy.get("calibration_source") or default.calibration_source),
    )


def default_contract_proof_policy() -> ContractProofPolicy:
    return ContractProofPolicy(
        name="dev_calibratable_contract_proof_policy",
        weights={
            "retrieval_score": 1.0,
            "lexical_score": 1.0,
            "route_score": 1.0,
            "satisfied": 25.0,
            "grounded_required_count": 3.0,
            "missing_required_count": -8.0,
            "action_conflict": -25.0,
            "argument_issue_count": -3.0,
            "non_action_blocker_count": -5.0,
            "boundary_penalty": -1.0,
        },
        call_threshold=20.0,
        repair_threshold=5.0,
        calibration_source="locked_default_weights_metadata_overridable_on_dev",
    )


def _contract_proof_features(
    evaluation: ContractEvaluation,
    *,
    retrieval_score: int | float = 0,
    lexical_score: int | float = 0,
    boundary_penalty: int | float = 0,
) -> Dict[str, float]:
    """Expose every score input so proof decisions are auditable and calibratable."""
    return {
        "retrieval_score": float(retrieval_score),
        "lexical_score": float(lexical_score),
        "route_score": float(evaluation.routing_bonus),
        "satisfied": 1.0 if evaluation.satisfied else 0.0,
        "grounded_required_count": float(len(evaluation.grounded_required_args)),
        "missing_required_count": float(len(evaluation.missing_required_args)),
        "action_conflict": 1.0 if "action_intent_conflict" in evaluation.blocking_reasons else 0.0,
        "argument_issue_count": float(len(evaluation.argument_issues)),
        "non_action_blocker_count": float(len([reason for reason in evaluation.blocking_reasons if reason != "action_intent_conflict"])),
        "boundary_penalty": float(boundary_penalty),
    }


def _score_features(features: Dict[str, float], policy: ContractProofPolicy) -> float:
    score = sum(float(features.get(name, 0.0)) * float(weight) for name, weight in policy.weights.items())
    return round(score, 4)


def _proof_decision(evaluation: ContractEvaluation, proof_score: float, policy: ContractProofPolicy) -> str:
    if "action_intent_conflict" in evaluation.blocking_reasons:
        return "abstain"
    if evaluation.missing_required_args:
        return "abstain"
    if "adaptive_policy_reject" in evaluation.blocking_reasons:
        return "abstain"
    if evaluation.argument_issues:
        return "repair" if proof_score >= policy.repair_threshold else "abstain"
    if evaluation.satisfied and proof_score >= policy.call_threshold:
        return "call"
    if proof_score >= policy.repair_threshold:
        return "repair"
    return "abstain"

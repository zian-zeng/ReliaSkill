from __future__ import annotations

from dataclasses import asdict, dataclass
import os
from typing import Any, Dict

from autoskill.ir import GeneratedSkill


@dataclass
class ContractArbitrationPolicy:
    """Transparent policy for balancing model-native choices and contract evidence."""

    name: str
    enabled: bool
    enable_runtime_model_arbitration: bool
    enable_routing_arbitration: bool
    runtime_arbitration_margin_threshold: float
    preserve_native_routing_margin: float
    preserve_native_score_advantage: float
    contract_override_margin: float
    low_risk_missing_required_max: int
    hard_block_reasons: list[str]
    calibration_source: str

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


def default_contract_arbitration_policy() -> ContractArbitrationPolicy:
    return ContractArbitrationPolicy(
        name="contract_aware_arbitration_v1",
        enabled=False,
        enable_runtime_model_arbitration=False,
        enable_routing_arbitration=False,
        runtime_arbitration_margin_threshold=10.0,
        preserve_native_routing_margin=10.0,
        preserve_native_score_advantage=4.0,
        contract_override_margin=12.0,
        low_risk_missing_required_max=0,
        hard_block_reasons=[
            "missing_required_arguments",
            "action_intent_conflict",
            "argument_contract_violation",
            "explicit_target_tool_forbidden",
            "planning_or_no_tool_request",
            "request_explicitly_asks_not_to_call",
            "adjacent_or_boundary_mismatch",
        ],
        calibration_source="disabled_default",
    )


def contract_arbitration_policy_from_skill(skill: GeneratedSkill) -> ContractArbitrationPolicy:
    default = default_contract_arbitration_policy()
    metadata = skill.metadata if isinstance(skill.metadata, dict) else {}
    raw_policy = metadata.get("contract_arbitration_policy")
    if not isinstance(raw_policy, dict):
        return _env_override(default)
    policy = ContractArbitrationPolicy(
        name=str(raw_policy.get("name") or default.name),
        enabled=bool(raw_policy.get("enabled", default.enabled)),
        enable_runtime_model_arbitration=bool(
            raw_policy.get("enable_runtime_model_arbitration", default.enable_runtime_model_arbitration)
        ),
        enable_routing_arbitration=bool(raw_policy.get("enable_routing_arbitration", default.enable_routing_arbitration)),
        runtime_arbitration_margin_threshold=_float_policy_value(
            raw_policy,
            "runtime_arbitration_margin_threshold",
            default.runtime_arbitration_margin_threshold,
        ),
        preserve_native_routing_margin=_float_policy_value(
            raw_policy,
            "preserve_native_routing_margin",
            default.preserve_native_routing_margin,
        ),
        preserve_native_score_advantage=_float_policy_value(
            raw_policy,
            "preserve_native_score_advantage",
            default.preserve_native_score_advantage,
        ),
        contract_override_margin=_float_policy_value(raw_policy, "contract_override_margin", default.contract_override_margin),
        low_risk_missing_required_max=max(
            int(raw_policy.get("low_risk_missing_required_max", default.low_risk_missing_required_max) or 0),
            0,
        ),
        hard_block_reasons=[
            str(item)
            for item in (
                raw_policy.get("hard_block_reasons")
                if isinstance(raw_policy.get("hard_block_reasons"), list)
                else default.hard_block_reasons
            )
            if str(item)
        ],
        calibration_source=str(raw_policy.get("calibration_source") or default.calibration_source),
    )
    return _env_override(policy)


def routing_row_contract_margin(row: Dict[str, Any] | None) -> float:
    if not isinstance(row, dict):
        return 0.0
    for key in ("contract_proof_margin", "proof_margin"):
        try:
            return float(row.get(key) or 0.0)
        except (TypeError, ValueError):
            continue
    return 0.0


def routing_row_contract_risk(row: Dict[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(row, dict):
        return {
            "hard_blocked": True,
            "missing_required_count": 999,
            "blocking_reasons": ["missing_candidate_row"],
        }
    blockers = [str(item) for item in row.get("contract_blocking_reasons", []) if item is not None]
    missing = row.get("missing_required_args")
    missing_count = len(missing) if isinstance(missing, list) else 0
    return {
        "hard_blocked": bool(row.get("action_intent_conflict")) or "action_intent_conflict" in blockers,
        "missing_required_count": missing_count,
        "blocking_reasons": blockers,
    }


def _float_policy_value(policy: Dict[str, Any], key: str, default: float) -> float:
    try:
        return float(policy.get(key, default))
    except (TypeError, ValueError):
        return default


def _env_override(policy: ContractArbitrationPolicy) -> ContractArbitrationPolicy:
    raw = os.getenv("RELIASKILL_ENABLE_CONTRACT_ARBITRATION", "").strip().lower()
    if raw not in {"1", "true", "yes"}:
        return policy
    policy.enabled = True
    policy.enable_runtime_model_arbitration = True
    policy.enable_routing_arbitration = True
    policy.calibration_source = f"{policy.calibration_source}+env_override"
    return policy

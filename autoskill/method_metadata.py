from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from autoskill.ir import GeneratedSkill


RELIASKILL_V1 = "reliaskill_v1"
LEGACY_RELIASKILL_CHALLENGER = "reliaskill_challenger_v1"
RELIASKILL_CHALLENGER = RELIASKILL_V1

CHALLENGER_REQUIRED_FILES = [
    "skill.json",
    "validation_report.json",
    "behavior_report.json",
    "repair_report.json",
    "reliability_score.json",
    "selection_report.json",
    "method_metadata.json",
]


def require_challenger_package(package_dir: Path) -> None:
    missing = [name for name in CHALLENGER_REQUIRED_FILES if not (package_dir / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing required `{RELIASKILL_CHALLENGER}` package files in {package_dir}: "
            + ", ".join(missing)
        )


def load_package_method_metadata(package_dir: Path, *, condition: str) -> Dict[str, Any]:
    metadata = _read_json(package_dir / "metadata.json")
    method = _read_json(package_dir / "method_metadata.json")
    reliability = _read_json(package_dir / "reliability_score.json")
    repair = _read_json(package_dir / "repair_report.json")
    selection = _read_json(package_dir / "selection_report.json")
    behavior = _read_json(package_dir / "behavior_report.json")
    validation = _read_json(package_dir / "validation_report.json")

    compact: Dict[str, Any] = {
        "condition": condition,
        "loaded_from_package": True,
        "package_path": str(package_dir),
        "pipeline_stages": method.get("pipeline_stages", []),
        "source_condition": method.get("source_condition"),
        "gate_source_condition": method.get("gate_source_condition"),
        "uses_runtime_schema_contract_verifier": bool(method.get("uses_runtime_schema_contract_verifier", False)),
        "uses_executable_skill_contract": bool(method.get("uses_executable_skill_contract", False)),
        "uses_contract_proof_ledger": bool(method.get("uses_contract_proof_ledger", False)),
        "uses_adaptive_contract_policy": bool(method.get("uses_adaptive_contract_policy", False)),
        "uses_contextual_grounding_contract": bool(method.get("uses_contextual_grounding_contract", False)),
        "uses_multi_step_contract_planning": bool(method.get("uses_multi_step_contract_planning", False)),
        "uses_execution_feedback_contract": bool(method.get("uses_execution_feedback_contract", False)),
        "test_controls_used": bool(method.get("test_controls_used", False)),
    }
    if metadata:
        compact["metadata_baseline_name"] = metadata.get("baseline_name")
        compact["behavior_metrics"] = metadata.get("behavior_metrics")
    if validation:
        compact["validation_valid"] = validation.get("valid")
        compact["validation_issue_count"] = len(validation.get("issues") or [])
    if reliability:
        compact["reliability_decision"] = reliability.get("decision")
        compact["reliability_score"] = reliability.get("score")
        compact["reliability_threshold"] = reliability.get("threshold")
    if repair:
        compact["repair_attempted"] = repair.get("attempted")
        compact["repair_changed"] = repair.get("changed")
        compact["repair_rounds"] = repair.get("rounds")
        compact["repair_strategy"] = repair.get("strategy")
    if selection:
        compact["selected_candidate_id"] = selection.get("selected_candidate_id")
        compact["selection_policy"] = selection.get("selection_policy")
        compact["candidate_count"] = selection.get("candidate_count")
        compact["dev_controls_used"] = selection.get("dev_controls_used")
    if behavior:
        compact["dev_behavior_metrics"] = behavior.get("metrics")
    if not compact.get("uses_runtime_schema_contract_verifier"):
        compact["uses_runtime_schema_contract_verifier"] = "runtime_schema_contract_verifier" in compact.get("pipeline_stages", [])
    if not compact.get("uses_executable_skill_contract"):
        compact["uses_executable_skill_contract"] = "executable_contract_compilation" in compact.get("pipeline_stages", [])
    if not compact.get("uses_contract_proof_ledger"):
        compact["uses_contract_proof_ledger"] = "proof_carrying_runtime_contract" in compact.get("pipeline_stages", [])
    if not compact.get("uses_adaptive_contract_policy"):
        compact["uses_adaptive_contract_policy"] = "adaptive_contract_policy" in compact.get("pipeline_stages", [])
    if not compact.get("uses_contextual_grounding_contract"):
        compact["uses_contextual_grounding_contract"] = "contextual_grounding_contract" in compact.get("pipeline_stages", [])
    if not compact.get("uses_multi_step_contract_planning"):
        compact["uses_multi_step_contract_planning"] = "multi_step_contract_plan_composition" in compact.get("pipeline_stages", [])
    if not compact.get("uses_execution_feedback_contract"):
        compact["uses_execution_feedback_contract"] = "execution_feedback_contract_interpreter" in compact.get("pipeline_stages", [])
    return {key: value for key, value in compact.items() if value is not None}


def attach_loaded_package_metadata(skill: GeneratedSkill, package_dir: Path, *, condition: str) -> GeneratedSkill:
    method_metadata = load_package_method_metadata(package_dir, condition=condition)
    skill.metadata = {
        **skill.metadata,
        "loaded_from_package": True,
        "package_path": str(package_dir),
        "method_metadata": method_metadata,
    }
    skill.method_trace = [
        *skill.method_trace,
        {
            "trace_type": "package_load",
            "condition": condition,
            "package_path": str(package_dir),
            "loaded_from_package": True,
        },
    ]
    return skill


def prediction_method_metadata(skill: GeneratedSkill) -> Dict[str, Any]:
    method = skill.metadata.get("method_metadata") if isinstance(skill.metadata, dict) else None
    method = dict(method) if isinstance(method, dict) else {}
    result: Dict[str, Any] = {
        "condition": skill.baseline_name,
        "method_trace_types": [
            str(entry.get("trace_type"))
            for entry in skill.method_trace
            if isinstance(entry, dict) and entry.get("trace_type")
        ],
        "condition_family": skill.metadata.get("condition_family") if isinstance(skill.metadata, dict) else None,
        "loaded_from_package": skill.metadata.get("loaded_from_package") if isinstance(skill.metadata, dict) else None,
        "package_path": skill.metadata.get("package_path") if isinstance(skill.metadata, dict) else None,
        **method,
    }
    return {key: value for key, value in result.items() if value is not None}


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}

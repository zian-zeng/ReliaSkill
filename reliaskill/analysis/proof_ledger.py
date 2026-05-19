from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from autoskill.metrics import load_run_records


CASE_TYPES = [
    "accepted_verified_call",
    "verifier_repaired_call",
    "safe_abstention",
    "refinement_selected",
    "refinement_rejected",
]


def extract_proof_ledger_cases(
    run_dir: str | Path,
    *,
    condition: str = "reliaskill_v1",
    max_cases_per_type: int = 2,
    include_routing: bool = True,
) -> Dict[str, Any]:
    loaded = load_run_records(run_dir)
    records = [*loaded["benchmark"]]
    if include_routing:
        records.extend(loaded["routing"])
    selected: Dict[str, List[Dict[str, Any]]] = {case_type: [] for case_type in CASE_TYPES}
    for record in records:
        if str(record.get("baseline_name") or record.get("condition") or "") != condition:
            continue
        case_type = _case_type(record)
        if not case_type:
            continue
        if len(selected[case_type]) >= max_cases_per_type:
            continue
        selected[case_type].append(_ledger_case(record, case_type))
    cases = [case for case_type in CASE_TYPES for case in selected[case_type]]
    return {
        "run_dir": str(run_dir),
        "condition": condition,
        "case_counts": {case_type: len(selected[case_type]) for case_type in CASE_TYPES},
        "cases": cases,
    }


def audit_runtime_invariants(run_dir: str | Path, *, condition: str = "reliaskill_v1", include_routing: bool = True) -> Dict[str, Any]:
    loaded = load_run_records(run_dir)
    records = [*loaded["benchmark"]]
    if include_routing:
        records.extend(loaded["routing"])
    violations: List[Dict[str, Any]] = []
    checked = 0
    for record in records:
        if str(record.get("baseline_name") or record.get("condition") or "") != condition:
            continue
        metadata = record.get("prediction_metadata") if isinstance(record.get("prediction_metadata"), dict) else {}
        verifier = metadata.get("reliaskill_v1_runtime_verifier") if isinstance(metadata.get("reliaskill_v1_runtime_verifier"), dict) else {}
        if not verifier:
            violations.append(_violation(record, "missing_runtime_verifier", "ReliaSkill v1 record has no runtime verifier metadata."))
            continue
        checked += 1
        after = verifier.get("contract_evaluation_after") if isinstance(verifier.get("contract_evaluation_after"), dict) else {}
        should_call_after = bool(verifier.get("should_call_after", record.get("should_call", False)))
        if should_call_after and after.get("satisfied") is not True:
            violations.append(_violation(record, "accepted_call_without_satisfied_contract", "Accepted call lacks satisfied after-contract."))
        verified_args = verifier.get("verified_arguments")
        predicted_args = record.get("predicted_arguments")
        if should_call_after and isinstance(verified_args, dict) and isinstance(predicted_args, dict) and verified_args != predicted_args:
            violations.append(_violation(record, "predicted_arguments_not_verified_arguments", "Saved predicted args differ from verifier args."))
        refinement = metadata.get("reliaskill_v1_refinement") if isinstance(metadata.get("reliaskill_v1_refinement"), dict) else {}
        if refinement.get("selected_refined") is True and float(refinement.get("refined_score", 0.0)) <= float(refinement.get("original_score", 0.0)):
            violations.append(_violation(record, "selected_refinement_without_score_gain", "Selected refinement does not improve contract score."))
        if (
            refinement.get("attempted") is True
            and refinement.get("selected_refined") is False
            and "refined_score" in refinement
            and "original_score" in refinement
            and float(refinement.get("refined_score", 0.0)) > float(refinement.get("original_score", 0.0))
        ):
            violations.append(_violation(record, "rejected_refinement_with_score_gain", "Rejected refinement improves contract score."))
    return {
        "ok": not violations,
        "run_dir": str(run_dir),
        "condition": condition,
        "checked_records": checked,
        "num_violations": len(violations),
        "violations": violations[:100],
    }


def write_proof_ledger_report(report: Dict[str, Any], *, output_json: str | Path, output_md: str | Path) -> Dict[str, str]:
    json_path = Path(output_json)
    md_path = Path(output_md)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(build_proof_ledger_markdown(report), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def write_invariant_report(report: Dict[str, Any], *, output_json: str | Path, output_md: str | Path) -> Dict[str, str]:
    json_path = Path(output_json)
    md_path = Path(output_md)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(build_invariant_markdown(report), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def build_proof_ledger_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# ReliaSkill Proof-Ledger Cases",
        "",
        f"- Run: `{report.get('run_dir')}`",
        f"- Condition: `{report.get('condition')}`",
        "",
        "## Counts",
        "",
    ]
    for case_type, count in report.get("case_counts", {}).items():
        lines.append(f"- `{case_type}`: `{count}`")
    lines.extend(["", "## Cases", ""])
    for case in report.get("cases", []):
        lines.extend(
            [
                f"### {case['case_type']} / {case['task_id']}",
                "",
                f"- Expected tool: `{case.get('expected_tool_name')}`",
                f"- Selected tool: `{case.get('selected_tool_name')}`",
                f"- Should call: `{case.get('should_call')}`",
                f"- Actions: `{json.dumps(case.get('verifier_actions', []), ensure_ascii=False)}`",
                f"- Issues: `{json.dumps(case.get('verifier_issues', []), ensure_ascii=False)}`",
                f"- Failure after: `{json.dumps(case.get('contract_failure_report_after', {}), ensure_ascii=False, sort_keys=True)}`",
                f"- Original args: `{json.dumps(case.get('original_arguments', {}), ensure_ascii=False, sort_keys=True)}`",
                f"- Verified args: `{json.dumps(case.get('verified_arguments', {}), ensure_ascii=False, sort_keys=True)}`",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def build_invariant_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# ReliaSkill Runtime Invariant Audit",
        "",
        f"- OK: `{'yes' if report.get('ok') else 'no'}`",
        f"- Checked records: `{report.get('checked_records')}`",
        f"- Violations: `{report.get('num_violations')}`",
        "",
    ]
    for violation in report.get("violations", []):
        lines.append(f"- `{violation['violation']}` `{violation['task_id']}`: {violation['message']}")
    return "\n".join(lines) + "\n"


def _case_type(record: Dict[str, Any]) -> str | None:
    metadata = record.get("prediction_metadata") if isinstance(record.get("prediction_metadata"), dict) else {}
    verifier = metadata.get("reliaskill_v1_runtime_verifier") if isinstance(metadata.get("reliaskill_v1_runtime_verifier"), dict) else {}
    if not verifier:
        return None
    refinement = metadata.get("reliaskill_v1_refinement") if isinstance(metadata.get("reliaskill_v1_refinement"), dict) else {}
    if refinement.get("selected_refined") is True:
        return "refinement_selected"
    if refinement.get("attempted") is True and refinement.get("selected_refined") is False:
        return "refinement_rejected"
    actions = verifier.get("actions", []) if isinstance(verifier.get("actions"), list) else []
    if bool(record.get("should_call")) and actions:
        return "verifier_repaired_call"
    if bool(record.get("should_call")):
        return "accepted_verified_call"
    if not bool(record.get("should_trigger", True)) or verifier.get("should_call_after") is False:
        return "safe_abstention"
    return None


def _ledger_case(record: Dict[str, Any], case_type: str) -> Dict[str, Any]:
    metadata = record.get("prediction_metadata") if isinstance(record.get("prediction_metadata"), dict) else {}
    verifier = metadata.get("reliaskill_v1_runtime_verifier") if isinstance(metadata.get("reliaskill_v1_runtime_verifier"), dict) else {}
    return {
        "case_type": case_type,
        "task_id": record.get("task_id"),
        "record_type": record.get("record_type"),
        "expected_tool_name": record.get("expected_tool_name"),
        "selected_tool_name": record.get("selected_tool_name"),
        "should_trigger": record.get("should_trigger"),
        "should_call": record.get("should_call"),
        "joint_exact_match": record.get("joint_exact_match"),
        "abstention_reason": record.get("abstention_reason"),
        "user_request": record.get("user_request") or record.get("request") or "",
        "verifier_actions": verifier.get("actions", []),
        "verifier_issues": verifier.get("issues", []),
        "contract_failure_report_before": verifier.get("contract_failure_report_before", {}),
        "contract_failure_report_after": verifier.get("contract_failure_report_after", {}),
        "proof_obligations_before": (verifier.get("contract_evaluation_before") or {}).get("proof_obligations", []),
        "proof_obligations_after": (verifier.get("contract_evaluation_after") or {}).get("proof_obligations", []),
        "original_arguments": verifier.get("original_arguments", {}),
        "verified_arguments": verifier.get("verified_arguments", {}),
        "refinement": metadata.get("reliaskill_v1_refinement", {}),
    }


def _violation(record: Dict[str, Any], violation: str, message: str) -> Dict[str, Any]:
    return {
        "task_id": record.get("task_id"),
        "record_type": record.get("record_type"),
        "violation": violation,
        "message": message,
    }

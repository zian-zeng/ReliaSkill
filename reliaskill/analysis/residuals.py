from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from autoskill.metrics import load_run_records


def analyze_residuals(
    run_dir: str | Path,
    *,
    baseline: str = "raw_docs_full",
    method: str = "reliaskill_v1",
    include_routing: bool = True,
) -> Dict[str, Any]:
    loaded = load_run_records(run_dir)
    records = [*loaded["benchmark"]]
    if include_routing:
        records.extend(loaded["routing"])
    by_pair: Dict[Tuple[str, str, str], Dict[str, Dict[str, Any]]] = defaultdict(dict)
    for record in records:
        condition = str(record.get("baseline_name") or record.get("condition") or "")
        if condition not in {baseline, method}:
            continue
        key = (
            str(record.get("model_slug") or record.get("model_name") or ""),
            str(record.get("record_type") or _phase_for_record(record)),
            str(record.get("task_id") or ""),
        )
        by_pair[key][condition] = record

    rows: List[Dict[str, Any]] = []
    summary = Counter()
    for key, pair in sorted(by_pair.items()):
        if baseline not in pair or method not in pair:
            continue
        base_correct = _joint(pair[baseline])
        method_correct = _joint(pair[method])
        if base_correct == method_correct:
            continue
        outcome = "method_win" if method_correct else "baseline_win"
        focus_record = pair[method] if outcome == "baseline_win" else pair[baseline]
        category = categorize_residual(focus_record)
        row = {
            "model_slug": key[0],
            "record_type": key[1],
            "task_id": key[2],
            "outcome": outcome,
            "error_category": category,
            "baseline": baseline,
            "method": method,
            "baseline_correct": base_correct,
            "method_correct": method_correct,
            "expected_tool_name": focus_record.get("expected_tool_name"),
            "selected_tool_name": focus_record.get("selected_tool_name"),
            "should_trigger": focus_record.get("should_trigger"),
            "triggered": focus_record.get("triggered"),
            "abstention_reason": focus_record.get("abstention_reason"),
            "verifier_actions": _verifier_field(focus_record, "actions"),
            "verifier_issues": _verifier_field(focus_record, "issues"),
            "contract_failure_reason": _contract_failure_reason(focus_record),
            "user_request": focus_record.get("user_request") or focus_record.get("request") or "",
        }
        rows.append(row)
        summary[(outcome, category)] += 1

    return {
        "run_dir": str(run_dir),
        "baseline": baseline,
        "method": method,
        "paired_disagreements": len(rows),
        "baseline_only_correct": sum(1 for row in rows if row["outcome"] == "baseline_win"),
        "method_only_correct": sum(1 for row in rows if row["outcome"] == "method_win"),
        "summary": [
            {"outcome": outcome, "error_category": category, "count": count}
            for (outcome, category), count in sorted(summary.items())
        ],
        "rows": rows,
    }


def categorize_residual(record: Dict[str, Any]) -> str:
    if not bool(record.get("should_trigger", True)) and bool(record.get("triggered", False)):
        return "negative_control_overtrigger"
    if str(record.get("selected_tool_name") or "") != str(record.get("expected_tool_name") or ""):
        return "tool_routing_error"
    metadata = record.get("prediction_metadata") if isinstance(record.get("prediction_metadata"), dict) else {}
    verifier = metadata.get("reliaskill_v1_runtime_verifier") if isinstance(metadata.get("reliaskill_v1_runtime_verifier"), dict) else {}
    issues = [str(item) for item in verifier.get("issues", []) if item is not None]
    failure_reason = _contract_failure_reason(record)
    if any("missing_required" in issue for issue in issues) or failure_reason == "missing_required_arguments":
        return "missing_required_grounding"
    if any("ungrounded_required" in issue for issue in issues):
        return "ungrounded_required_argument"
    if any(marker in issue for issue in issues for marker in (":invalid_format", ":invalid_enum", ":type_mismatch", ":pattern_mismatch")):
        return "schema_contract_error"
    if failure_reason == "action_intent_conflict" or "action_intent_conflict" in str(record.get("abstention_reason") or ""):
        return "boundary_or_action_gate_error"
    if not bool(record.get("should_call", record.get("triggered", False))) and bool(record.get("should_trigger", True)):
        return "false_abstention"
    if not bool(record.get("argument_exact_match", record.get("exact_match", False))):
        return "argument_mismatch"
    return "other_residual"


def write_residual_analysis(report: Dict[str, Any], *, output_csv: str | Path, output_md: str | Path, output_json: str | Path | None = None) -> Dict[str, str]:
    csv_path = Path(output_csv)
    md_path = Path(output_md)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(report.get("rows", []))
    fields = [
        "model_slug",
        "record_type",
        "task_id",
        "outcome",
        "error_category",
        "baseline_correct",
        "method_correct",
        "expected_tool_name",
        "selected_tool_name",
        "should_trigger",
        "triggered",
        "abstention_reason",
        "contract_failure_reason",
        "verifier_actions",
        "verifier_issues",
        "user_request",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _cell(row.get(field)) for field in fields})
    md_path.write_text(build_residual_markdown(report), encoding="utf-8")
    paths = {"csv": str(csv_path), "markdown": str(md_path)}
    if output_json is not None:
        json_path = Path(output_json)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        paths["json"] = str(json_path)
    return paths


def build_residual_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Residual Error Analysis",
        "",
        f"- Run: `{report.get('run_dir')}`",
        f"- Baseline: `{report.get('baseline')}`",
        f"- Method: `{report.get('method')}`",
        f"- Paired disagreements: `{report.get('paired_disagreements')}`",
        f"- Baseline-only correct: `{report.get('baseline_only_correct')}`",
        f"- Method-only correct: `{report.get('method_only_correct')}`",
        "",
        "## Error Categories",
        "",
    ]
    for row in report.get("summary", []):
        lines.append(f"- `{row['outcome']}` `{row['error_category']}`: `{row['count']}`")
    lines.extend(["", "## Example Disagreements", ""])
    for row in report.get("rows", [])[:20]:
        lines.append(
            f"- `{row['outcome']}` `{row['error_category']}` `{row['task_id']}`: "
            f"expected `{row.get('expected_tool_name')}`, selected `{row.get('selected_tool_name')}`"
        )
    return "\n".join(lines) + "\n"


def _joint(record: Dict[str, Any]) -> bool:
    return bool(record.get("joint_exact_match", record.get("exact_match", False)))


def _phase_for_record(record: Dict[str, Any]) -> str:
    if record.get("candidate_tools") is not None or record.get("routing_strategy") is not None:
        return "routing"
    return "benchmark"


def _verifier_field(record: Dict[str, Any], field: str) -> List[str]:
    metadata = record.get("prediction_metadata") if isinstance(record.get("prediction_metadata"), dict) else {}
    verifier = metadata.get("reliaskill_v1_runtime_verifier") if isinstance(metadata.get("reliaskill_v1_runtime_verifier"), dict) else {}
    values = verifier.get(field, [])
    return [str(item) for item in values] if isinstance(values, list) else []


def _contract_failure_reason(record: Dict[str, Any]) -> str:
    metadata = record.get("prediction_metadata") if isinstance(record.get("prediction_metadata"), dict) else {}
    verifier = metadata.get("reliaskill_v1_runtime_verifier") if isinstance(metadata.get("reliaskill_v1_runtime_verifier"), dict) else {}
    for key in ("contract_failure_report_after", "contract_failure_report_before"):
        report = verifier.get(key)
        if isinstance(report, dict) and report.get("reason"):
            return str(report.get("reason"))
    return ""


def _cell(value: Any) -> str:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return "" if value is None else str(value)

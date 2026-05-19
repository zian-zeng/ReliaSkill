from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

import yaml


def audit_preregistered_success(
    *,
    preregistration_path: str | Path,
    tables_dir: str | Path,
) -> Dict[str, Any]:
    """Evaluate locked success criteria against result tables.

    The preregistration file is intentionally separate from the run outputs so
    reviewers can see which comparisons were planned before inspecting results.
    """
    prereg_path = Path(preregistration_path)
    spec = _load_yaml(prereg_path)
    tables = Path(tables_dir)
    main_rows = _read_csv(tables / "main_results.csv")
    routing_rows = _read_csv(tables / "routing_results.csv")
    stat_rows = _read_csv(tables / "stat_tests.csv")
    routing_stat_rows = _read_csv(tables / "routing_stat_tests.csv")
    harm_rows = _read_csv(tables / "harm_utility.csv")

    checks: List[Dict[str, Any]] = []
    _check_locked_protocol(checks, spec)
    for comparison in spec.get("primary_success_criteria", []) or []:
        _check_metric_comparison(checks, comparison, rows=main_rows, stat_rows=stat_rows, table_name="main_results")
        if comparison.get("also_require_routing", True):
            _check_metric_comparison(
                checks,
                comparison,
                rows=routing_rows,
                stat_rows=routing_stat_rows,
                table_name="routing_results",
            )
    for comparison in spec.get("component_ablation_criteria", []) or []:
        _check_metric_comparison(checks, comparison, rows=main_rows, stat_rows=stat_rows, table_name="main_results")
        if comparison.get("also_require_routing", True):
            _check_metric_comparison(
                checks,
                comparison,
                rows=routing_rows,
                stat_rows=routing_stat_rows,
                table_name="routing_results",
            )
    for criterion in spec.get("runtime_trace_criteria", []) or []:
        _check_runtime_trace_criterion(checks, criterion, rows=main_rows, table_name="main_results")
    for criterion in spec.get("harm_safety_criteria", []) or []:
        _check_harm_criterion(checks, criterion, rows=harm_rows)

    failures = [check for check in checks if not check["passed"] and check["severity"] == "fail"]
    warnings = [check for check in checks if not check["passed"] and check["severity"] == "warn"]
    return {
        "ok": not failures,
        "preregistration_path": str(prereg_path),
        "tables_dir": str(tables),
        "num_checks": len(checks),
        "num_failures": len(failures),
        "num_warnings": len(warnings),
        "checks": checks,
    }


def build_preregistration_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Preregistered Success Audit",
        "",
        f"- Ready: `{'yes' if report.get('ok') else 'no'}`",
        f"- Failures: `{report.get('num_failures', 0)}`",
        f"- Warnings: `{report.get('num_warnings', 0)}`",
        f"- Preregistration: `{report.get('preregistration_path', '')}`",
        f"- Tables: `{report.get('tables_dir', '')}`",
        "",
        "## Checks",
        "",
    ]
    for check in report.get("checks", []):
        status = "PASS" if check.get("passed") else check.get("severity", "fail").upper()
        lines.append(f"- `{status}` `{check.get('id')}`: {check.get('message')}")
        details = check.get("details")
        if details:
            lines.append(f"  Details: `{json.dumps(details, sort_keys=True)}`")
    return "\n".join(lines) + "\n"


def write_preregistration_report(
    report: Dict[str, Any],
    *,
    output_json: str | Path,
    output_md: str | Path,
) -> Dict[str, str]:
    json_path = Path(output_json)
    md_path = Path(output_md)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(build_preregistration_markdown(report), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def _check_locked_protocol(checks: List[Dict[str, Any]], spec: Dict[str, Any]) -> None:
    protocol = spec.get("protocol_lock", {}) if isinstance(spec.get("protocol_lock"), dict) else {}
    _add_check(
        checks,
        "criteria_locked_before_run",
        bool(protocol.get("criteria_locked_before_run")),
        "Success criteria are explicitly locked before inspecting the new run.",
        {"protocol_lock": protocol},
    )
    _add_check(
        checks,
        "no_test_set_authoring",
        not bool(protocol.get("test_set_used_for_method_changes")),
        "Protocol declares that test-set labels/results are not used for method changes.",
        {"protocol_lock": protocol},
    )


def _check_metric_comparison(
    checks: List[Dict[str, Any]],
    comparison: Dict[str, Any],
    *,
    rows: List[Dict[str, str]],
    stat_rows: List[Dict[str, str]],
    table_name: str,
) -> None:
    baseline = str(comparison.get("baseline") or "")
    method = str(comparison.get("method") or "reliaskill_v1")
    metric = str(comparison.get("metric") or "joint_exact_match")
    min_delta = float(comparison.get("min_delta", 0.0) or 0.0)
    require_significance = bool(comparison.get("require_significance", False))
    alpha = float(comparison.get("alpha", 0.05) or 0.05)
    min_examples = int(comparison.get("min_examples", 0) or 0)
    by_condition = {str(row.get("baseline_name")): row for row in rows}
    base_row = by_condition.get(baseline)
    method_row = by_condition.get(method)
    check_id = f"{table_name}:{baseline}_vs_{method}:{metric}"
    if base_row is None or method_row is None:
        _add_check(
            checks,
            check_id,
            False,
            f"{table_name} includes both `{baseline}` and `{method}`.",
            {"missing": [name for name, row in [(baseline, base_row), (method, method_row)] if row is None]},
        )
        return
    base_value = _float(base_row.get(metric))
    method_value = _float(method_row.get(metric))
    delta = method_value - base_value
    examples_ok = min(_int(base_row.get("num_examples")), _int(method_row.get("num_examples"))) >= min_examples
    significance = _paired_significance(stat_rows, baseline, method, metric)
    significant_ok = (not require_significance) or (significance is not None and significance.get("p_value", 1.0) <= alpha)
    passed = delta >= min_delta and examples_ok and significant_ok
    _add_check(
        checks,
        check_id,
        passed,
        f"`{method}` beats `{baseline}` on `{metric}` by the preregistered margin in {table_name}.",
        {
            "baseline": baseline,
            "method": method,
            "metric": metric,
            "baseline_value": base_value,
            "method_value": method_value,
            "delta": round(delta, 6),
            "min_delta": min_delta,
            "min_examples": min_examples,
            "examples_ok": examples_ok,
            "require_significance": require_significance,
            "alpha": alpha,
            "paired_significance": significance,
        },
    )


def _check_runtime_trace_criterion(checks: List[Dict[str, Any]], criterion: Dict[str, Any], *, rows: List[Dict[str, str]], table_name: str) -> None:
    condition = str(criterion.get("condition") or "reliaskill_v1")
    metric = str(criterion.get("metric") or "")
    min_value = float(criterion.get("min", 0.0) or 0.0)
    max_value = float(criterion.get("max", 1.0) or 1.0)
    by_condition = {str(row.get("baseline_name")): row for row in rows}
    row = by_condition.get(condition)
    value = _float(row.get(metric)) if row else 0.0
    _add_check(
        checks,
        f"{table_name}:{condition}:{metric}_bounds",
        row is not None and min_value <= value <= max_value,
        f"`{condition}` runtime trace metric `{metric}` is within preregistered bounds.",
        {"condition": condition, "metric": metric, "value": value, "min": min_value, "max": max_value},
    )


def _check_harm_criterion(checks: List[Dict[str, Any]], criterion: Dict[str, Any], *, rows: List[Dict[str, str]]) -> None:
    baseline = str(criterion.get("baseline") or "")
    method = str(criterion.get("method") or "reliaskill_v1")
    metric = str(criterion.get("metric") or "harmful_skill_injection_rate")
    max_increase = float(criterion.get("max_increase", 0.0) or 0.0)
    by_condition = {str(row.get("baseline_name")): row for row in rows}
    base_row = by_condition.get(baseline)
    method_row = by_condition.get(method)
    base_value = _float(base_row.get(metric)) if base_row else 0.0
    method_value = _float(method_row.get(metric)) if method_row else 0.0
    delta = method_value - base_value
    _add_check(
        checks,
        f"harm:{baseline}_vs_{method}:{metric}",
        base_row is not None and method_row is not None and delta <= max_increase,
        f"`{method}` does not regress safety versus `{baseline}` on `{metric}`.",
        {
            "baseline": baseline,
            "method": method,
            "metric": metric,
            "baseline_value": base_value,
            "method_value": method_value,
            "delta": round(delta, 6),
            "max_increase": max_increase,
        },
    )


def _paired_significance(stat_rows: List[Dict[str, str]], baseline: str, method: str, metric: str) -> Dict[str, Any] | None:
    candidates = [
        row
        for row in stat_rows
        if str(row.get("metric")) == metric
        and {str(row.get("baseline_a")), str(row.get("baseline_b"))} == {baseline, method}
        and str(row.get("test")) == "approx_randomization"
    ]
    if not candidates:
        return None
    row = candidates[0]
    return {
        "test": row.get("test"),
        "baseline_a": row.get("baseline_a"),
        "baseline_b": row.get("baseline_b"),
        "paired_examples": _int(row.get("paired_examples")),
        "observed_delta": _float(row.get("observed_delta")),
        "p_value": _float(row.get("p_value"), default=1.0),
    }


def _add_check(checks: List[Dict[str, Any]], check_id: str, passed: bool, message: str, details: Dict[str, Any] | None = None) -> None:
    checks.append(
        {
            "id": check_id,
            "severity": "fail",
            "passed": bool(passed),
            "message": message,
            "details": details or {},
        }
    )


def _read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}


def _float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0

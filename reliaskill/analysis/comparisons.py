from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


SUPPORT_CATEGORIES = {"supported", "weakly_supported", "mixed", "unsupported", "insufficient_data"}


@dataclass(frozen=True)
class MetricSpec:
    metric: str
    direction: str = "higher"
    min_effect: float = 0.01
    primary: bool = False


@dataclass(frozen=True)
class ComparisonTemplate:
    comparison_id: str
    condition_a: str
    condition_b: str
    metrics: Sequence[MetricSpec]
    source: str = "main_results"
    slice_file: str | None = None
    slice_dimension: str | None = None
    slice_value: str | None = None
    expected_claim: str = ""
    min_denominator: int = 20


COMPARISON_TEMPLATES: List[ComparisonTemplate] = [
    ComparisonTemplate(
        "naive_skill_vs_raw_mcp",
        "raw_mcp",
        "naive_skill_k1",
        [MetricSpec("joint_exact_match", primary=True), MetricSpec("argument_schema_validity"), MetricSpec("tool_selection_accuracy")],
        expected_claim="Generated skills improve structured tool-use accuracy over raw MCP schemas.",
    ),
    ComparisonTemplate(
        "repaired_vs_naive",
        "naive_skill_k1",
        "full_regeneration_repair",
        [MetricSpec("joint_exact_match", primary=True), MetricSpec("argument_schema_validity"), MetricSpec("harmful_skill_injection_rate", "lower")],
        expected_claim="Repair improves or preserves utility while reducing harmful behavior.",
    ),
    ComparisonTemplate(
        "gated_vs_repaired",
        "full_regeneration_repair",
        "autoskill_base",
        [MetricSpec("harmful_skill_injection_rate", "lower", primary=True), MetricSpec("joint_exact_match", "higher", min_effect=-0.03)],
        source="harm_utility",
        expected_claim="Gating trades little utility for lower harm.",
    ),
    ComparisonTemplate(
        "compact_vs_verbose",
        "skill_verbose",
        "skill_compact",
        [MetricSpec("joint_exact_match", primary=True), MetricSpec("avg_token_overhead", "lower")],
        expected_claim="Compact skills match or improve verbose generated documentation with lower context overhead.",
    ),
    ComparisonTemplate(
        "multi_candidate_vs_single_candidate",
        "naive_skill_k1",
        "multi_candidate_repaired_gated",
        [MetricSpec("joint_exact_match", primary=True), MetricSpec("argument_schema_validity"), MetricSpec("harmful_skill_injection_rate", "lower")],
        expected_claim="Multi-candidate selection improves over one-shot skill generation.",
    ),
    ComparisonTemplate(
        "targeted_repair_vs_full_regeneration",
        "repaired_full_regeneration",
        "repaired_targeted_patch",
        [MetricSpec("joint_exact_match", primary=True), MetricSpec("harmful_skill_injection_rate", "lower")],
        expected_claim="Targeted repair is at least as useful as full regeneration while avoiding broad rewrites.",
    ),
    ComparisonTemplate(
        "three_b_gated_vs_seven_b_raw",
        "7B_raw",
        "3B_gated",
        [MetricSpec("joint_exact_match", primary=True), MetricSpec("harmful_skill_injection_rate", "lower")],
        expected_claim="Reliable 3B skills close the gap with 7B raw-schema prompting.",
    ),
    ComparisonTemplate(
        "hard_cases_only",
        "raw_mcp",
        "naive_skill_k1",
        [MetricSpec("joint_exact_match", primary=True), MetricSpec("tool_accuracy")],
        source="slice",
        slice_file="slice_analysis_by_difficulty.csv",
        slice_dimension="difficulty",
        slice_value="hard",
        expected_claim="Skill gains are larger or remain positive on hard examples.",
        min_denominator=10,
    ),
    ComparisonTemplate(
        "negative_controls_only",
        "raw_mcp",
        "autoskill_base",
        [MetricSpec("harmful_skill_injection_rate", "lower", primary=True), MetricSpec("trigger_precision")],
        source="harm_utility",
        expected_claim="Gated skills reduce false triggering on negative controls.",
        min_denominator=10,
    ),
    ComparisonTemplate(
        "side_effect_tools_only",
        "raw_mcp",
        "autoskill_base",
        [MetricSpec("joint_exact_match", primary=True), MetricSpec("harmful_skill_injection_rate", "lower")],
        source="slice",
        slice_file="slice_analysis_by_tool_complexity.csv",
        slice_dimension="side_effect_type",
        slice_value="write",
        expected_claim="Reliability controls help especially on side-effectful tools.",
        min_denominator=10,
    ),
    ComparisonTemplate(
        "high_distractor_routing_only",
        "raw_mcp",
        "autoskill_base",
        [MetricSpec("tool_accuracy", primary=True), MetricSpec("joint_exact_match")],
        source="slice",
        slice_file="slice_analysis_by_distractor_level.csv",
        slice_dimension="distractor_level",
        slice_value="hard",
        expected_claim="Reliable skills improve routing under hard distractors.",
        min_denominator=10,
    ),
]


KEY_COMPARISON_FIELDS = [
    "comparison_id",
    "claim_support",
    "safe_wording",
    "condition_a",
    "condition_b",
    "metric",
    "condition_a_value",
    "condition_b_value",
    "delta_b_minus_a",
    "delta_ci_low",
    "delta_ci_high",
    "denominator",
    "paired_test",
    "paired_p_value",
    "warnings",
    "expected_claim",
]


def extract_scientific_comparisons(
    *,
    tables_dir: str | Path = "outputs/tables",
    min_denominator: int = 20,
) -> Dict[str, Any]:
    tables_path = Path(tables_dir)
    tables = load_result_tables(tables_path)
    results = []
    for template in COMPARISON_TEMPLATES:
        effective_template = ComparisonTemplate(
            **{
                **template.__dict__,
                "min_denominator": max(template.min_denominator, min_denominator if template.source != "slice" else template.min_denominator),
            }
        )
        results.append(evaluate_comparison(effective_template, tables))
    return {
        "source_tables_dir": str(tables_path),
        "comparison_count": len(results),
        "claim_support_counts": _support_counts(results),
        "comparisons": results,
        "warnings": [warning for result in results for warning in result.get("warnings", [])],
    }


def write_scientific_comparison_outputs(
    summary: Dict[str, Any],
    *,
    output_json: str | Path = "outputs/reports/scientific_comparison_summary.json",
    output_md: str | Path = "outputs/reports/scientific_comparison_summary.md",
    output_csv: str | Path = "outputs/tables/key_comparisons.csv",
) -> Dict[str, Path]:
    json_path = Path(output_json)
    md_path = Path(output_md)
    csv_path = Path(output_csv)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(build_comparison_markdown(summary), encoding="utf-8")
    write_key_comparisons_csv(csv_path, summary["comparisons"])
    return {"json": json_path, "markdown": md_path, "csv": csv_path}


def load_result_tables(tables_dir: Path) -> Dict[str, List[Dict[str, str]]]:
    names = [
        "main_results.csv",
        "harm_utility.csv",
        "stat_tests.csv",
        "slice_analysis_by_difficulty.csv",
        "slice_analysis_by_negative_category.csv",
        "slice_analysis_by_distractor_level.csv",
        "slice_analysis_by_tool_complexity.csv",
        "slice_analysis_by_domain.csv",
    ]
    tables: Dict[str, List[Dict[str, str]]] = {}
    for name in names:
        path = tables_dir / name
        tables[name] = _read_csv(path) if path.exists() else []
    return tables


def evaluate_comparison(template: ComparisonTemplate, tables: Dict[str, List[Dict[str, str]]]) -> Dict[str, Any]:
    warnings: List[str] = []
    rows_by_condition = _rows_for_template(template, tables, warnings)
    metric_results = []
    for metric in template.metrics:
        metric_results.append(_evaluate_metric(template, metric, rows_by_condition, tables, warnings))
    support = classify_support(metric_results, warnings)
    return {
        "comparison_id": template.comparison_id,
        "condition_a": template.condition_a,
        "condition_b": template.condition_b,
        "source": template.source,
        "slice_dimension": template.slice_dimension,
        "slice_value": template.slice_value,
        "expected_claim": template.expected_claim,
        "claim_support": support,
        "safe_wording": safe_wording(support, metric_results),
        "metrics": metric_results,
        "warnings": sorted(set(warnings)),
    }


def classify_support(metric_results: Sequence[Dict[str, Any]], warnings: Sequence[str]) -> str:
    available = [item for item in metric_results if item.get("available")]
    if not available:
        return "insufficient_data"
    if any("denominator" in warning.lower() or "missing" in warning.lower() for warning in warnings) and not any(item.get("meets_expected_direction") for item in available):
        return "insufficient_data"
    primary = [item for item in available if item.get("primary")] or available[:1]
    primary_positive = [item for item in primary if item.get("meets_expected_direction")]
    secondary = [item for item in available if not item.get("primary")]
    secondary_negative = [item for item in secondary if not item.get("meets_expected_direction") and abs(float(item.get("delta_effect", 0.0))) > 0.01]
    if len(primary_positive) == len(primary) and not secondary_negative:
        if all(abs(float(item.get("delta_effect", 0.0))) >= float(item.get("min_effect", 0.01)) for item in primary_positive):
            return "supported"
        return "weakly_supported"
    if primary_positive and secondary_negative:
        return "mixed"
    if primary_positive:
        return "weakly_supported"
    if any(item.get("meets_expected_direction") for item in available):
        return "mixed"
    return "unsupported"


def safe_wording(support: str, metric_results: Sequence[Dict[str, Any]]) -> str:
    if support == "supported":
        return "improves"
    if support == "weakly_supported":
        return "suggests"
    if support == "mixed":
        positives = [item["metric"] for item in metric_results if item.get("meets_expected_direction")]
        negatives = [item["metric"] for item in metric_results if item.get("available") and not item.get("meets_expected_direction")]
        return f"improves on {', '.join(positives) or 'some metrics'} but not {', '.join(negatives) or 'all metrics'}"
    if support == "unsupported":
        return "does not support"
    return "insufficient data"


def build_comparison_markdown(summary: Dict[str, Any]) -> str:
    lines = [
        "# Scientific Comparison Summary",
        "",
        "Generated from saved result tables only. No claims are fabricated, and missing comparisons are marked as insufficient data.",
        "",
        "## Claim Support Counts",
    ]
    for category in ["supported", "weakly_supported", "mixed", "unsupported", "insufficient_data"]:
        lines.append(f"- `{category}`: `{summary['claim_support_counts'].get(category, 0)}`")
    lines.extend(["", "## Key Comparisons"])
    for comparison in summary["comparisons"]:
        lines.append(f"### {comparison['comparison_id']}")
        lines.append(f"- Support: `{comparison['claim_support']}`")
        lines.append(f"- Safe wording: `{comparison['safe_wording']}`")
        lines.append(f"- Expected claim: {comparison['expected_claim']}")
        for metric in comparison["metrics"]:
            if not metric.get("available"):
                lines.append(f"- `{metric['metric']}`: unavailable ({'; '.join(metric.get('warnings', []))})")
            else:
                lines.append(
                    f"- `{metric['metric']}`: {metric['condition_a_value']} -> {metric['condition_b_value']} "
                    f"(delta {metric['delta_b_minus_a']}, n={metric['denominator']})"
                )
        if comparison["warnings"]:
            lines.append("- Warnings: " + "; ".join(comparison["warnings"]))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_key_comparisons_csv(path: Path, comparisons: Sequence[Dict[str, Any]]) -> None:
    rows = []
    for comparison in comparisons:
        for metric in comparison["metrics"]:
            rows.append(
                {
                    "comparison_id": comparison["comparison_id"],
                    "claim_support": comparison["claim_support"],
                    "safe_wording": comparison["safe_wording"],
                    "condition_a": comparison["condition_a"],
                    "condition_b": comparison["condition_b"],
                    "metric": metric["metric"],
                    "condition_a_value": metric.get("condition_a_value", ""),
                    "condition_b_value": metric.get("condition_b_value", ""),
                    "delta_b_minus_a": metric.get("delta_b_minus_a", ""),
                    "delta_ci_low": metric.get("delta_ci_low", ""),
                    "delta_ci_high": metric.get("delta_ci_high", ""),
                    "denominator": metric.get("denominator", ""),
                    "paired_test": metric.get("paired_test", ""),
                    "paired_p_value": metric.get("paired_p_value", ""),
                    "warnings": "; ".join([*comparison.get("warnings", []), *metric.get("warnings", [])]),
                    "expected_claim": comparison["expected_claim"],
                }
            )
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=KEY_COMPARISON_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in KEY_COMPARISON_FIELDS})


def _rows_for_template(template: ComparisonTemplate, tables: Dict[str, List[Dict[str, str]]], warnings: List[str]) -> Dict[str, Dict[str, str]]:
    if template.source == "slice":
        rows = tables.get(template.slice_file or "", [])
        candidates = [
            row for row in rows
            if row.get("slice_dimension") == template.slice_dimension
            and row.get("slice_value") == template.slice_value
            and row.get("condition")
        ]
    elif template.source == "harm_utility":
        candidates = tables.get("harm_utility.csv", [])
    else:
        candidates = tables.get("main_results.csv", [])
    by_condition = {str(row.get("baseline_name") or row.get("condition")): row for row in candidates}
    for condition in [template.condition_a, template.condition_b]:
        if condition not in by_condition:
            warnings.append(f"missing condition `{condition}` for {template.comparison_id}")
    return by_condition


def _evaluate_metric(
    template: ComparisonTemplate,
    metric: MetricSpec,
    rows_by_condition: Dict[str, Dict[str, str]],
    tables: Dict[str, List[Dict[str, str]]],
    comparison_warnings: List[str],
) -> Dict[str, Any]:
    warnings: List[str] = []
    row_a = rows_by_condition.get(template.condition_a)
    row_b = rows_by_condition.get(template.condition_b)
    if not row_a or not row_b:
        return _unavailable_metric(metric, ["missing comparison rows"])
    field = _metric_field(metric.metric, row_a, row_b)
    if not field:
        return _unavailable_metric(metric, [f"missing metric `{metric.metric}`"])
    a_value = _float(row_a.get(field))
    b_value = _float(row_b.get(field))
    if a_value is None or b_value is None:
        return _unavailable_metric(metric, [f"non-numeric metric `{field}`"])
    denom = _denominator(row_a, row_b, template.source)
    if denom < template.min_denominator:
        warnings.append(f"denominator {denom} below minimum {template.min_denominator}")
        comparison_warnings.append(f"{template.comparison_id}/{metric.metric}: denominator {denom} below minimum {template.min_denominator}")
    raw_delta = b_value - a_value
    effect = raw_delta if metric.direction == "higher" else -raw_delta
    paired = _paired_test(template.condition_a, template.condition_b, metric.metric, tables.get("stat_tests.csv", []))
    ci = _delta_ci(field, row_a, row_b)
    return {
        "metric": metric.metric,
        "field": field,
        "available": True,
        "primary": metric.primary,
        "direction": metric.direction,
        "min_effect": metric.min_effect,
        "condition_a_value": round(a_value, 4),
        "condition_b_value": round(b_value, 4),
        "delta_b_minus_a": round(raw_delta, 4),
        "delta_effect": round(effect, 4),
        "meets_expected_direction": effect >= metric.min_effect,
        "denominator": denom,
        "delta_ci_low": ci.get("low", ""),
        "delta_ci_high": ci.get("high", ""),
        "paired_test": paired.get("test", ""),
        "paired_p_value": paired.get("p_value", ""),
        "paired_examples": paired.get("paired_examples", ""),
        "warnings": warnings,
    }


def _unavailable_metric(metric: MetricSpec, warnings: Sequence[str]) -> Dict[str, Any]:
    return {
        "metric": metric.metric,
        "available": False,
        "primary": metric.primary,
        "direction": metric.direction,
        "min_effect": metric.min_effect,
        "warnings": list(warnings),
    }


def _metric_field(metric: str, row_a: Dict[str, str], row_b: Dict[str, str]) -> str | None:
    aliases = {
        "tool_accuracy": ["tool_accuracy", "tool_selection_accuracy"],
        "argument_validity": ["argument_validity", "argument_schema_validity", "avg_argument_validity"],
        "joint_exact_match": ["joint_exact_match", "utility_joint_exact_match"],
        "avg_token_overhead": ["avg_token_overhead", "mean_prompt_tokens"],
    }
    for candidate in aliases.get(metric, [metric]):
        if candidate in row_a and candidate in row_b:
            return candidate
    return None


def _denominator(row_a: Dict[str, str], row_b: Dict[str, str], source: str) -> int:
    keys = ["num_examples", "num_controls", "total_examples", "paired_examples"]
    values = [_int(row.get(key)) for row in [row_a, row_b] for key in keys if row.get(key) not in {None, ""}]
    values = [value for value in values if value is not None]
    if source == "harm_utility":
        negative_values = [_int(row.get("negative_controls")) for row in [row_a, row_b]]
        negative_values = [value for value in negative_values if value is not None and value > 0]
        if negative_values:
            return min(negative_values)
    return min(values) if values else 0


def _paired_test(condition_a: str, condition_b: str, metric: str, rows: Sequence[Dict[str, str]]) -> Dict[str, Any]:
    normalized_metric = "joint_exact_match" if metric in {"joint_exact_match", "tool_accuracy", "argument_validity"} else metric
    for row in rows:
        if row.get("metric") != normalized_metric:
            continue
        a = row.get("baseline_a")
        b = row.get("baseline_b")
        if {a, b} == {condition_a, condition_b}:
            return {
                "test": row.get("test", ""),
                "p_value": row.get("p_value", ""),
                "paired_examples": row.get("paired_examples", ""),
            }
    return {}


def _delta_ci(field: str, row_a: Dict[str, str], row_b: Dict[str, str]) -> Dict[str, Any]:
    low_key = f"{field}_wilson_low"
    high_key = f"{field}_wilson_high"
    if low_key not in row_a or low_key not in row_b:
        return {}
    a_low = _float(row_a.get(low_key))
    a_high = _float(row_a.get(high_key))
    b_low = _float(row_b.get(low_key))
    b_high = _float(row_b.get(high_key))
    if None in {a_low, a_high, b_low, b_high}:
        return {}
    return {"low": round(float(b_low) - float(a_high), 4), "high": round(float(b_high) - float(a_low), 4)}


def _support_counts(results: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    counts = {category: 0 for category in SUPPORT_CATEGORIES}
    for result in results:
        counts[str(result.get("claim_support"))] = counts.get(str(result.get("claim_support")), 0) + 1
    return counts


def _read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return [dict(row) for row in csv.DictReader(f)]


def _float(value: Any) -> float | None:
    try:
        if value in {None, ""}:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> int | None:
    try:
        if value in {None, ""}:
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None

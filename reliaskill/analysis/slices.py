from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from autoskill.metrics import flatten_reliability_records, load_jsonl, load_run_records, normalize_prediction_records


SLICE_DIMENSIONS = [
    "domain",
    "source_type",
    "difficulty",
    "tool_complexity_tier",
    "num_required_args_bucket",
    "has_enum",
    "has_nested_object",
    "side_effect_type",
    "negative_category",
    "distractor_level",
    "candidate_set_size",
    "skill_token_bucket",
]

DEFAULT_OUTPUTS = {
    "domain": "outputs/tables/slice_analysis_by_domain.csv",
    "difficulty": "outputs/tables/slice_analysis_by_difficulty.csv",
    "negative_category": "outputs/tables/slice_analysis_by_negative_category.csv",
    "distractor_level": "outputs/tables/slice_analysis_by_distractor_level.csv",
    "tool_complexity_tier": "outputs/tables/slice_analysis_by_tool_complexity.csv",
}

COMPARISONS = [
    ("raw_mcp", "naive_skill", "raw_mcp_vs_naive_skill"),
    ("naive_skill", "repaired_skill", "naive_skill_vs_repaired_skill"),
    ("repaired_skill", "gated_skill", "repaired_skill_vs_gated_skill"),
    ("3B_gated", "7B_raw", "3B_gated_vs_7B_raw"),
    ("skill_compact", "skill_verbose", "compact_vs_verbose"),
]

SLICE_FIELDS = [
    "slice_dimension",
    "slice_value",
    "condition",
    "num_examples",
    "suppressed",
    "joint_exact_match",
    "argument_validity",
    "tool_accuracy",
    "trigger_precision",
    "trigger_recall",
    "harmful_skill_injection_rate",
    "skill_induced_harm_rate",
    "mean_prompt_tokens",
    "mean_latency",
]

COMPARISON_FIELDS = [
    "slice_dimension",
    "slice_value",
    "comparison",
    "condition_a",
    "condition_b",
    "paired_examples",
    "metric",
    "condition_a_value",
    "condition_b_value",
    "delta_b_minus_a",
    "suppressed",
]


def analyze_result_slices(
    *,
    run_dir: str | Path,
    tools_path: str | Path = "data/processed_toolir/tools.jsonl",
    controls_paths: Sequence[str | Path] | None = None,
    routing_path: str | Path | None = "data/routing/test_routing.jsonl",
    compactness_path: str | Path | None = "outputs/skill_compactness_records.jsonl",
    min_slice_size: int = 5,
) -> Dict[str, Any]:
    tools = load_tool_metadata(tools_path)
    controls = load_control_metadata(controls_paths or ["data/controls/dev.jsonl", "data/controls/test.jsonl"])
    routing = load_routing_metadata(routing_path)
    compactness = load_compactness_metadata(compactness_path)
    records = load_analysis_records(run_dir)
    enriched = [
        enrich_record(record, tools=tools, controls=controls, routing=routing, compactness=compactness)
        for record in records
    ]
    tables: Dict[str, List[Dict[str, Any]]] = {}
    comparisons: Dict[str, List[Dict[str, Any]]] = {}
    for dimension in SLICE_DIMENSIONS:
        rows = summarize_by_slice(enriched, dimension, min_slice_size=min_slice_size)
        tables[dimension] = rows
        comparisons[dimension] = compare_conditions_by_slice(enriched, dimension, min_slice_size=min_slice_size)
    return {
        "records": enriched,
        "tables": tables,
        "comparisons": comparisons,
        "min_slice_size": min_slice_size,
        "num_records": len(enriched),
    }


def write_slice_analysis_outputs(analysis: Dict[str, Any], *, output_dir: str | Path = "outputs/tables", report_path: str | Path = "outputs/reports/slice_analysis_summary.md") -> Dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, Path] = {}
    for dimension, default_path in DEFAULT_OUTPUTS.items():
        path = Path(default_path)
        if output_dir != "outputs/tables":
            path = out / Path(default_path).name
        rows = analysis["tables"].get(dimension, [])
        comparison_rows = analysis["comparisons"].get(dimension, [])
        combined = [*rows, *comparison_rows]
        fieldnames = _ordered_fields(combined, [*SLICE_FIELDS, *COMPARISON_FIELDS])
        write_csv(path, combined, fieldnames)
        paths[dimension] = path
    report = Path(report_path)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(build_slice_summary_markdown(analysis), encoding="utf-8")
    paths["summary"] = report
    return paths


def load_analysis_records(run_dir: str | Path) -> List[Dict[str, Any]]:
    loaded = load_run_records(run_dir)
    records = normalize_prediction_records(loaded["benchmark"], record_type="benchmark")
    records.extend(normalize_prediction_records(loaded["routing"], record_type="routing"))
    records.extend(_normalize_behavior_records(loaded["behavior"]))
    records.extend(flatten_reliability_records(loaded["reliability"]))
    records.extend(_load_live_records(Path(run_dir)))
    return records


def load_tool_metadata(path: str | Path) -> Dict[str, Dict[str, Any]]:
    input_path = Path(path)
    if not input_path.exists():
        return {}
    tools = {}
    for record in load_jsonl(input_path):
        name = str(record.get("tool_name") or record.get("name") or "")
        if not name:
            continue
        complexity = record.get("schema_complexity") if isinstance(record.get("schema_complexity"), dict) else {}
        source_metadata = record.get("source_metadata") if isinstance(record.get("source_metadata"), dict) else {}
        provenance = record.get("provenance") if isinstance(record.get("provenance"), dict) else {}
        tools[name] = {
            "domain": record.get("domain") or source_metadata.get("domain") or "unknown",
            "source_type": source_metadata.get("source_type") or source_metadata.get("source_category") or provenance.get("source_type") or "unknown",
            "tool_complexity_tier": record.get("difficulty_tier") or source_metadata.get("difficulty_tier") or _complexity_tier(complexity),
            "num_required_args_bucket": _required_bucket(int(complexity.get("num_required_arguments") or source_metadata.get("num_required_arguments") or 0)),
            "has_enum": bool(complexity.get("num_enum_fields") or complexity.get("num_enum_arguments") or source_metadata.get("num_enum_fields")),
            "has_nested_object": bool(complexity.get("has_nested_object") or source_metadata.get("has_nested_object")),
            "side_effect_type": complexity.get("side_effect_type") or source_metadata.get("side_effect_type") or "unknown",
        }
    return tools


def load_control_metadata(paths: Sequence[str | Path]) -> Dict[str, Dict[str, Any]]:
    controls = {}
    for path in paths:
        input_path = Path(path)
        if not input_path.exists():
            continue
        for record in load_jsonl(input_path):
            task_id = str(record.get("task_id") or record.get("control_id") or record.get("id") or "")
            if not task_id:
                continue
            controls[task_id] = {
                "difficulty": record.get("difficulty") or _tag_difficulty(record.get("tags")),
                "negative_category": record.get("negative_category") or "none",
                "domain": record.get("domain"),
                "side_effect_type": record.get("side_effect_type"),
                "should_trigger": record.get("should_trigger"),
            }
    return controls


def load_routing_metadata(path: str | Path | None) -> Dict[str, Dict[str, Any]]:
    if not path or not Path(path).exists():
        return {}
    routing = {}
    for record in load_jsonl(path):
        keys = [record.get("id"), record.get("task_id"), record.get("source_control_id")]
        metadata = {
            "distractor_level": record.get("distractor_level") or "unknown",
            "candidate_set_size": record.get("candidate_set_size") or record.get("requested_candidate_set_size") or "unknown",
            "negative_category": record.get("negative_category") or "none",
            "difficulty": record.get("control_difficulty"),
        }
        for key in keys:
            if key:
                routing[str(key)] = metadata
    return routing


def load_compactness_metadata(path: str | Path | None) -> Dict[tuple[str, str], Dict[str, Any]]:
    if not path or not Path(path).exists():
        return {}
    compactness = {}
    for record in load_jsonl(path):
        key = (str(record.get("tool_name") or ""), str(record.get("condition") or ""))
        compactness[key] = {
            "mean_prompt_tokens": _float_or_none(record.get("prompt_token_count")),
            "skill_token_bucket": _skill_token_bucket(_float_or_none(record.get("skill_token_count"))),
        }
    return compactness


def enrich_record(record: Dict[str, Any], *, tools: Dict[str, Dict[str, Any]], controls: Dict[str, Dict[str, Any]], routing: Dict[str, Dict[str, Any]], compactness: Dict[tuple[str, str], Dict[str, Any]]) -> Dict[str, Any]:
    item = dict(record)
    condition = _condition(item)
    tool_name = str(item.get("tool_name") or item.get("expected_tool_name") or item.get("target_tool_id") or "")
    task_id = str(item.get("task_id") or item.get("case_id") or item.get("live_task_id") or "")
    tool_meta = tools.get(tool_name, {})
    control_meta = controls.get(task_id, {})
    routing_meta = routing.get(task_id, {})
    compact_meta = compactness.get((tool_name, condition), {})
    for key in ["domain", "source_type", "tool_complexity_tier", "num_required_args_bucket", "has_enum", "has_nested_object", "side_effect_type"]:
        item[key] = _coalesce(item.get(key), control_meta.get(key), routing_meta.get(key), tool_meta.get(key), "unknown")
    item["difficulty"] = _coalesce(item.get("difficulty"), item.get("control_difficulty"), control_meta.get("difficulty"), routing_meta.get("difficulty"), tool_meta.get("tool_complexity_tier"), "unknown")
    item["negative_category"] = _coalesce(item.get("negative_category"), control_meta.get("negative_category"), routing_meta.get("negative_category"), "none")
    item["distractor_level"] = _coalesce(item.get("distractor_level"), routing_meta.get("distractor_level"), "none")
    item["candidate_set_size"] = _coalesce(item.get("candidate_set_size"), routing_meta.get("candidate_set_size"), "none")
    item["skill_token_bucket"] = _coalesce(item.get("skill_token_bucket"), compact_meta.get("skill_token_bucket"), _skill_token_bucket(_token_value(item)), "unknown")
    if "mean_prompt_tokens" not in item and compact_meta.get("mean_prompt_tokens") is not None:
        item["mean_prompt_tokens"] = compact_meta["mean_prompt_tokens"]
    item["condition"] = condition
    item["baseline_name"] = condition
    return item


def summarize_by_slice(records: Sequence[Dict[str, Any]], dimension: str, *, min_slice_size: int) -> List[Dict[str, Any]]:
    grouped: Dict[tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[(str(record.get(dimension, "unknown")), _condition(record))].append(record)
    rows = []
    for (slice_value, condition), items in sorted(grouped.items()):
        summary = summarize_records(items)
        rows.append(
            {
                "slice_dimension": dimension,
                "slice_value": slice_value,
                "condition": condition,
                "num_examples": len(items),
                "suppressed": len(items) < min_slice_size,
                **summary,
            }
        )
    return rows


def compare_conditions_by_slice(records: Sequence[Dict[str, Any]], dimension: str, *, min_slice_size: int) -> List[Dict[str, Any]]:
    rows = []
    by_slice_task: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]] = defaultdict(lambda: defaultdict(dict))
    for record in records:
        task_key = str(record.get("task_id") or record.get("case_id") or record.get("live_task_id") or "")
        if not task_key:
            continue
        by_slice_task[str(record.get(dimension, "unknown"))][task_key][_condition(record)] = record
    for slice_value, by_task in sorted(by_slice_task.items()):
        for condition_a, condition_b, label in COMPARISONS:
            pairs = [(items[condition_a], items[condition_b]) for items in by_task.values() if condition_a in items and condition_b in items]
            for metric in ["joint_exact_match", "argument_validity", "tool_accuracy"]:
                a_values = [_metric_value(a, metric) for a, _ in pairs]
                b_values = [_metric_value(b, metric) for _, b in pairs]
                rows.append(
                    {
                        "slice_dimension": dimension,
                        "slice_value": slice_value,
                        "comparison": label,
                        "condition_a": condition_a,
                        "condition_b": condition_b,
                        "paired_examples": len(pairs),
                        "metric": metric,
                        "condition_a_value": _mean(a_values),
                        "condition_b_value": _mean(b_values),
                "delta_b_minus_a": round(_mean(b_values) - _mean(a_values), 4) if pairs else 0.0,
                        "suppressed": len(pairs) < min_slice_size,
                    }
                )
    return rows


def summarize_records(records: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    positives = [record for record in records if bool(record.get("should_trigger", True))]
    negatives = [record for record in records if not bool(record.get("should_trigger", True))]
    tp = sum(1 for record in positives if bool(record.get("triggered", True)))
    fn = len(positives) - tp
    fp = sum(1 for record in negatives if bool(record.get("triggered", False)))
    return {
        "joint_exact_match": _mean(_metric_value(record, "joint_exact_match") for record in records),
        "argument_validity": _mean(_metric_value(record, "argument_validity") for record in records),
        "tool_accuracy": _mean(_metric_value(record, "tool_accuracy") for record in records),
        "trigger_precision": round(tp / (tp + fp), 4) if (tp + fp) else 1.0,
        "trigger_recall": round(tp / (tp + fn), 4) if (tp + fn) else 1.0,
        "harmful_skill_injection_rate": round(fp / len(negatives), 4) if negatives else 0.0,
        "skill_induced_harm_rate": _mean(1.0 if record.get("harmful_injection") or record.get("skill_induced_harm") else 0.0 for record in records),
        "mean_prompt_tokens": _mean(_prompt_tokens(record) for record in records if _prompt_tokens(record) is not None),
        "mean_latency": _mean(_latency_ms(record) for record in records if _latency_ms(record) is not None),
    }


def build_slice_summary_markdown(analysis: Dict[str, Any]) -> str:
    lines = [
        "# ReliaSkill Slice Analysis Summary",
        "",
        f"- Records analyzed: `{analysis['num_records']}`",
        f"- Minimum slice size: `{analysis['min_slice_size']}`",
        "",
    ]
    for dimension in ["domain", "difficulty", "negative_category", "distractor_level", "tool_complexity_tier"]:
        rows = [row for row in analysis["tables"].get(dimension, []) if row.get("condition")]
        visible = [row for row in rows if not row.get("suppressed")]
        lines.append(f"## {dimension}")
        lines.append(f"- Slice rows: `{len(rows)}`")
        lines.append(f"- Unsuppressed rows: `{len(visible)}`")
        top = sorted(visible, key=lambda row: (str(row.get("condition")), -float(row.get("joint_exact_match") or 0)))[:5]
        for row in top:
            lines.append(
                f"- `{row['condition']}` on `{row['slice_value']}`: n={row['num_examples']}, joint={row['joint_exact_match']}, tool={row['tool_accuracy']}"
            )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def write_csv(path: str | Path, rows: Sequence[Dict[str, Any]], fieldnames: Sequence[str]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _normalize_behavior_records(records: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized = []
    for record in records:
        item = dict(record)
        item["record_type"] = item.get("record_type") or "behavior"
        item["baseline_name"] = item.get("baseline_name") or item.get("condition") or "default"
        item["task_id"] = item.get("task_id") or item.get("case_id")
        normalized.append(item)
    return normalized


def _load_live_records(run_dir: Path) -> List[Dict[str, Any]]:
    rows = []
    for path in sorted(run_dir.rglob("live_exec_results.jsonl")):
        for record in load_jsonl(path):
            item = dict(record)
            item["record_type"] = "live_exec"
            item["baseline_name"] = item.get("baseline_name") or item.get("condition") or "live_exec"
            item["task_id"] = item.get("live_task_id") or item.get("task_id")
            item["joint_exact_match"] = bool(item.get("live_joint_success"))
            item["argument_validity"] = 1.0 if item.get("predicted_call_valid") else 0.0
            item["tool_selection_correct"] = item.get("predicted_tool_name") == item.get("tool_id")
            rows.append(item)
    return rows


def _condition(record: Dict[str, Any]) -> str:
    return str(record.get("condition") or record.get("baseline_name") or record.get("model_condition") or "default")


def _metric_value(record: Dict[str, Any], metric: str) -> float:
    if metric == "tool_accuracy":
        value = record.get("tool_selection_correct")
        if value is None:
            value = record.get("correct_tool")
        if value is None and record.get("selected_tool_name") is not None and record.get("expected_tool_name") is not None:
            value = record.get("selected_tool_name") == record.get("expected_tool_name")
    elif metric == "joint_exact_match":
        value = record.get("joint_exact_match")
        if value is None:
            value = record.get("exact_match")
    else:
        value = record.get(metric)
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _prompt_tokens(record: Dict[str, Any]) -> float | None:
    for key in ("mean_prompt_tokens", "prompt_token_count", "prompt_tokens"):
        value = _float_or_none(record.get(key))
        if value is not None:
            return value
    metadata = record.get("prediction_metadata")
    if isinstance(metadata, dict):
        for key in ("prompt_token_count", "prompt_tokens"):
            value = _float_or_none(metadata.get(key))
            if value is not None:
                return value
    return None


def _latency_ms(record: Dict[str, Any]) -> float | None:
    for key in ("prediction_latency_ms", "latency_ms", "duration_ms"):
        value = _float_or_none(record.get(key))
        if value is not None:
            return value
    metadata = record.get("prediction_metadata")
    if isinstance(metadata, dict):
        for key in ("prediction_latency_ms", "latency_ms"):
            value = _float_or_none(metadata.get(key))
            if value is not None:
                return value
    return None


def _token_value(record: Dict[str, Any]) -> float | None:
    return _prompt_tokens(record) or _float_or_none(record.get("skill_token_count")) or _float_or_none(record.get("token_count"))


def _skill_token_bucket(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value <= 150:
        return "ultra_compact"
    if value <= 300:
        return "compact"
    if value <= 600:
        return "medium"
    if value <= 1200:
        return "verbose"
    return "very_verbose"


def _required_bucket(value: int) -> str:
    if value <= 0:
        return "0"
    if value <= 2:
        return "1-2"
    if value <= 5:
        return "3-5"
    return "6+"


def _complexity_tier(complexity: Dict[str, Any]) -> str:
    if complexity.get("has_nested_object") or complexity.get("num_enum_fields") or complexity.get("has_side_effect"):
        return "hard"
    if int(complexity.get("num_arguments") or 0) >= 3:
        return "medium"
    return "easy"


def _tag_difficulty(tags: Any) -> str:
    if isinstance(tags, list):
        for tag in tags:
            if str(tag) in {"easy", "medium", "hard"}:
                return str(tag)
    return "unknown"


def _coalesce(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return "unknown"


def _float_or_none(value: Any) -> float | None:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _mean(values: Iterable[float]) -> float:
    items = [float(value) for value in values]
    return round(sum(items) / len(items), 4) if items else 0.0


def _ordered_fields(rows: Sequence[Dict[str, Any]], preferred: Sequence[str]) -> List[str]:
    keys = set()
    for row in rows:
        keys.update(row)
    ordered = []
    for field in preferred:
        if field in keys and field not in ordered:
            ordered.append(field)
    ordered.extend(sorted(keys.difference(ordered)))
    if ordered:
        return ordered
    fallback = []
    for field in preferred:
        if field not in fallback:
            fallback.append(field)
    return fallback

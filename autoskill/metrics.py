from __future__ import annotations

import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Sequence, Tuple


DEFAULT_BOOTSTRAP_ITERATIONS = 500
DEFAULT_SEED = 42
KEY_STAT_TEST_COMPARISONS = [
    ("raw_mcp", "generated_skill_base"),
    ("raw_mcp", "gated_skill"),
    ("raw_mcp", "reliaskill_v1"),
    ("generated_skill_base", "gated_skill"),
    ("generated_skill_base", "reliaskill_v1"),
    ("gated_skill", "reliaskill_v1"),
    ("raw_mcp", "skill_prompt_boundary_first"),
    ("generated_skill_base", "skill_prompt_boundary_first"),
    ("raw_mcp", "skill_prompt_verbose_docs"),
    ("generated_skill_base", "skill_prompt_verbose_docs"),
]


def load_jsonl(path: str | Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                value = json.loads(line)
                if isinstance(value, dict):
                    records.append(value)
    return records


def load_run_records(run_dir: str | Path) -> Dict[str, List[Dict[str, Any]]]:
    root = Path(run_dir)
    benchmark_records: List[Dict[str, Any]] = []
    routing_records: List[Dict[str, Any]] = []
    reliability_records: List[Dict[str, Any]] = []
    behavior_records: List[Dict[str, Any]] = []

    for path in _preferred_record_paths(root, "prediction_records.jsonl"):
        benchmark_records.extend(load_jsonl(path))
    for path in _preferred_record_paths(root, "routing_records.jsonl"):
        routing_records.extend(load_jsonl(path))
    for path in _preferred_record_paths(root, "reliability_records.jsonl"):
        reliability_records.extend(load_jsonl(path))
    for path in sorted(root.rglob("*.jsonl")):
        name = path.name.lower()
        if name in {"prediction_records.jsonl", "routing_records.jsonl", "reliability_records.jsonl"}:
            continue
        if "behavior" in name or "control" in name:
            behavior_records.extend(load_jsonl(path))

    return {
        "benchmark": benchmark_records,
        "routing": routing_records,
        "reliability": reliability_records,
        "behavior": behavior_records,
    }


def _preferred_record_paths(root: Path, filename: str) -> List[Path]:
    direct = root / filename
    if direct.exists():
        return [direct]
    global_merged = root / "merged" / filename
    if global_merged.exists():
        return [global_merged]
    model_merged = sorted(root.glob(f"predictors/*/merged/{filename}"))
    if model_merged:
        return model_merged
    return sorted(root.rglob(filename))


def normalize_path(value: str) -> str:
    normalized = value.replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if "://" in normalized:
        return normalized.rstrip("/")
    return str(PurePosixPath(normalized))


def canonicalize_json_value(value: Any, schema: Dict[str, Any] | None = None, *, key_hint: str = "") -> Any:
    if isinstance(value, dict):
        properties = schema.get("properties", {}) if isinstance(schema, dict) else {}
        required = set(schema.get("required", [])) if isinstance(schema, dict) and isinstance(schema.get("required"), list) else set()
        normalized = {
            str(key): canonicalize_json_value(
                child,
                properties.get(key) if isinstance(properties, dict) and isinstance(properties.get(key), dict) else None,
                key_hint=str(key),
            )
            for key, child in value.items()
        }
        if isinstance(properties, dict):
            for key, prop_schema in properties.items():
                if key in normalized or key in required or not isinstance(prop_schema, dict):
                    continue
                default = prop_schema.get("default", None)
                if default is not None:
                    normalized.pop(str(key), None)
        return {key: normalized[key] for key in sorted(normalized)}
    if isinstance(value, list):
        item_schema = schema.get("items") if isinstance(schema, dict) and isinstance(schema.get("items"), dict) else None
        return [canonicalize_json_value(item, item_schema, key_hint=key_hint) for item in value]
    if isinstance(value, str):
        if _looks_like_path_key(key_hint) or _looks_like_path_value(value):
            return normalize_path(value)
        return " ".join(value.split())
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def canonical_json(value: Any, schema: Dict[str, Any] | None = None) -> str:
    normalized = canonicalize_json_value(value, schema)
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def argument_exact_match(
    predicted: Dict[str, Any],
    expected: Dict[str, Any],
    schema: Dict[str, Any] | None = None,
) -> bool:
    normalized_expected = canonicalize_json_value(expected, schema)
    normalized_predicted = canonicalize_json_value(predicted, schema)
    if isinstance(normalized_expected, dict) and isinstance(normalized_predicted, dict) and isinstance(schema, dict):
        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for key, prop_schema in properties.items():
                if key in normalized_predicted and key not in normalized_expected and isinstance(prop_schema, dict):
                    default = prop_schema.get("default", None)
                    if default is not None and normalized_predicted[key] == canonicalize_json_value(default, prop_schema, key_hint=key):
                        normalized_predicted.pop(key)
    return normalized_predicted == normalized_expected


def best_argument_exact_match(record: Dict[str, Any]) -> bool:
    predicted = _dict_value(record, ["predicted_arguments", "arguments", "predicted_args"])
    candidates = record.get("expected_argument_candidates")
    if not isinstance(candidates, list) or not candidates:
        expected = _dict_value(record, ["expected_arguments", "gold_args", "ground_truth_arguments"])
        candidates = [expected]
    schema = _dict_value(record, ["input_schema", "inputSchema", "schema"])
    return any(argument_exact_match(predicted, candidate, schema if schema else None) for candidate in candidates if isinstance(candidate, dict))


def argument_parse_rate(records: Sequence[Dict[str, Any]]) -> float:
    return _mean([1.0 if _parsed_arguments(record) else 0.0 for record in records])


def argument_schema_validity(record: Dict[str, Any]) -> bool:
    if record.get("should_trigger") is False and record.get("triggered") is False:
        return True
    predicted = record.get("predicted_arguments")
    if not isinstance(predicted, dict):
        return False
    if record.get("schema_valid") is False or record.get("argument_schema_valid") is False:
        return False
    if record.get("error") in {"argument_parse_error", "schema_validation_error"}:
        return False
    hallucinated = record.get("hallucinated_args")
    if isinstance(hallucinated, list) and hallucinated:
        return False
    schema = _dict_value(record, ["input_schema", "inputSchema", "schema"])
    if schema and not _value_conforms_to_schema(predicted, schema):
        return False
    if "argument_validity" in record:
        try:
            return float(record["argument_validity"]) >= 1.0
        except (TypeError, ValueError):
            return False
    return True


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> Dict[str, float]:
    if total <= 0:
        return {"low": 0.0, "high": 0.0}
    phat = successes / total
    denom = 1 + z * z / total
    center = (phat + z * z / (2 * total)) / denom
    margin = (z / denom) * math.sqrt((phat * (1 - phat) / total) + (z * z / (4 * total * total)))
    return {"low": round(max(0.0, center - margin), 4), "high": round(min(1.0, center + margin), 4)}


def bootstrap_ci(
    values: Sequence[float],
    *,
    groups: Sequence[str] | None = None,
    iterations: int = DEFAULT_BOOTSTRAP_ITERATIONS,
    seed: int = DEFAULT_SEED,
) -> Dict[str, float]:
    if not values:
        return {"low": 0.0, "high": 0.0}
    rng = random.Random(seed)
    means: List[float] = []
    if groups:
        grouped: Dict[str, List[float]] = defaultdict(list)
        for group, value in zip(groups, values):
            grouped[str(group)].append(float(value))
        keys = sorted(grouped)
        for _ in range(iterations):
            sampled_keys = [keys[rng.randrange(len(keys))] for _ in keys]
            sample_values = [value for key in sampled_keys for value in grouped[key]]
            means.append(_mean(sample_values))
    else:
        numeric = [float(value) for value in values]
        for _ in range(iterations):
            sample = [numeric[rng.randrange(len(numeric))] for _ in numeric]
            means.append(_mean(sample))
    means.sort()
    low_index = int(0.025 * (len(means) - 1))
    high_index = int(0.975 * (len(means) - 1))
    return {"low": round(means[low_index], 4), "high": round(means[high_index], 4)}


def mcnemar_test(
    records: Sequence[Dict[str, Any]],
    baseline_a: str,
    baseline_b: str,
    metric_field: str = "joint_exact_match",
) -> Dict[str, Any]:
    by_task: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
    for record in records:
        by_task[_paired_record_key(record)][str(record.get("baseline_name", "default"))] = record
    b = 0
    c = 0
    paired = 0
    for by_baseline in by_task.values():
        if baseline_a not in by_baseline or baseline_b not in by_baseline:
            continue
        a_ok = _binary_metric(by_baseline[baseline_a], metric_field)
        b_ok = _binary_metric(by_baseline[baseline_b], metric_field)
        paired += 1
        if a_ok and not b_ok:
            b += 1
        elif b_ok and not a_ok:
            c += 1
    discordant = b + c
    if discordant == 0:
        statistic = 0.0
        p_value = 1.0
    else:
        statistic = ((abs(b - c) - 1) ** 2) / discordant
        p_value = math.erfc(math.sqrt(statistic / 2.0))
    return {
        "test": "mcnemar",
        "baseline_a": baseline_a,
        "baseline_b": baseline_b,
        "metric": metric_field,
        "paired_examples": paired,
        "a_only_correct": b,
        "b_only_correct": c,
        "statistic": round(statistic, 6),
        "p_value": round(p_value, 6),
    }


def approximate_randomization_test(
    records: Sequence[Dict[str, Any]],
    baseline_a: str,
    baseline_b: str,
    metric_field: str = "joint_exact_match",
    *,
    iterations: int = 1000,
    seed: int = DEFAULT_SEED,
) -> Dict[str, Any]:
    pairs: List[Tuple[float, float]] = []
    by_task: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
    for record in records:
        by_task[_paired_record_key(record)][str(record.get("baseline_name", "default"))] = record
    for by_baseline in by_task.values():
        if baseline_a in by_baseline and baseline_b in by_baseline:
            pairs.append((_metric_value(by_baseline[baseline_a], metric_field), _metric_value(by_baseline[baseline_b], metric_field)))
    if not pairs:
        return {
            "test": "approx_randomization",
            "baseline_a": baseline_a,
            "baseline_b": baseline_b,
            "metric": metric_field,
            "paired_examples": 0,
            "observed_delta": 0.0,
            "p_value": 1.0,
        }
    observed = abs(_mean([a - b for a, b in pairs]))
    rng = random.Random(seed)
    exceed = 0
    for _ in range(iterations):
        deltas = []
        for a, b in pairs:
            if rng.random() < 0.5:
                a, b = b, a
            deltas.append(a - b)
        if abs(_mean(deltas)) >= observed:
            exceed += 1
    p_value = (exceed + 1) / (iterations + 1)
    return {
        "test": "approx_randomization",
        "baseline_a": baseline_a,
        "baseline_b": baseline_b,
        "metric": metric_field,
        "paired_examples": len(pairs),
        "observed_delta": round(_mean([a - b for a, b in pairs]), 6),
        "p_value": round(p_value, 6),
    }


def normalize_prediction_records(records: Sequence[Dict[str, Any]], *, record_type: str = "benchmark") -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for record in records:
        item = dict(record)
        item["record_type"] = record_type
        item.setdefault("baseline_name", record.get("condition") or record.get("baseline") or "default")
        item["should_trigger"] = bool(record.get("should_trigger", True))
        item["triggered"] = bool(record.get("triggered", record.get("should_call", item["should_trigger"])))
        if item["should_trigger"]:
            expected_tool_name = record.get("expected_tool_name") or record.get("tool_name") or record.get("gold_tool")
        else:
            expected_tool_name = "__abstain__"
        item["expected_tool_name"] = expected_tool_name
        if "expected_tool_name" not in item:
            item["expected_tool_name"] = record.get("tool_name") or record.get("gold_tool")
        if "selected_tool_name" not in item or not item.get("selected_tool_name"):
            item["selected_tool_name"] = "__abstain__" if not item["triggered"] else record.get("tool_name")
        item["argument_parse_ok"] = _parsed_arguments(item)
        item["argument_schema_valid"] = argument_schema_validity(item)
        if not item["should_trigger"]:
            item["argument_exact_match"] = not item["triggered"]
        else:
            item["argument_exact_match"] = bool(record.get("argument_exact_match_given_tool", False)) or best_argument_exact_match(item)
        item["tool_selection_correct"] = bool(record.get("tool_selection_correct", item.get("selected_tool_name") == item.get("expected_tool_name")))
        item["joint_exact_match"] = bool(item["tool_selection_correct"] and item["argument_exact_match"])
        item["harmful_injection"] = bool(record.get("harmful_injection", not item["should_trigger"] and item["triggered"]))
        item["skill_induced_harm"] = bool(record.get("skill_induced_harm", not item["should_trigger"] and item["triggered"]))
        normalized.append(item)
    return normalized


def flatten_reliability_records(records: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    flattened: List[Dict[str, Any]] = []
    for record in records:
        condition = str(record.get("condition") or record.get("baseline_name") or "default")
        tool_name = str(record.get("tool_name") or "")
        score_features = ((record.get("reliability_score") or {}).get("features") or {}) if isinstance(record.get("reliability_score"), dict) else {}
        behavior = record.get("behavior_report") if isinstance(record.get("behavior_report"), dict) else {}
        for result in behavior.get("results", []) if isinstance(behavior.get("results"), list) else []:
            if not isinstance(result, dict):
                continue
            item = dict(result)
            item["baseline_name"] = condition
            item["tool_name"] = item.get("tool_name") or tool_name
            item["task_id"] = item.get("case_id") or item.get("task_id")
            item["record_type"] = "behavior"
            item["token_overhead_estimate"] = score_features.get("token_overhead_estimate")
            flattened.append(item)
    return flattened


def summarize_metric_records(records: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record.get("baseline_name", "default"))].append(record)
    return {baseline: _summarize_group(items) for baseline, items in sorted(grouped.items())}


def summarize_harm_records(records: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record.get("baseline_name", "default"))].append(record)
    return {baseline: _summarize_harm_group(items) for baseline, items in sorted(grouped.items())}


def build_metric_tables(run_dir: str | Path) -> Dict[str, List[Dict[str, Any]]]:
    loaded = load_run_records(run_dir)
    benchmark_records = normalize_prediction_records(loaded["benchmark"], record_type="benchmark")
    routing_records = normalize_prediction_records(loaded["routing"], record_type="routing")
    utility_records = benchmark_records + routing_records
    behavior_records = list(loaded["behavior"])
    behavior_records.extend(flatten_reliability_records(loaded["reliability"]))
    all_records = utility_records + behavior_records
    main_rows = _main_rows(summarize_metric_records(benchmark_records or all_records))
    routing_rows = _main_rows(summarize_metric_records(routing_records))
    harm_rows = _harm_rows(summarize_harm_records(all_records), summarize_metric_records(benchmark_records))
    stat_rows = build_stat_test_rows(benchmark_records)
    routing_stat_rows = build_stat_test_rows(routing_records)
    return {
        "main_results": main_rows,
        "routing_results": routing_rows,
        "harm_utility": harm_rows,
        "stat_tests": stat_rows,
        "routing_stat_tests": routing_stat_rows,
    }


def write_metric_tables(run_dir: str | Path, output_dir: str | Path = "outputs/tables") -> Dict[str, Path]:
    tables = build_metric_tables(run_dir)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "main_results": out / "main_results.csv",
        "routing_results": out / "routing_results.csv",
        "harm_utility": out / "harm_utility.csv",
        "stat_tests": out / "stat_tests.csv",
        "routing_stat_tests": out / "routing_stat_tests.csv",
    }
    _write_csv(paths["main_results"], tables["main_results"], MAIN_FIELDS)
    _write_csv(paths["routing_results"], tables["routing_results"], MAIN_FIELDS)
    _write_csv(paths["harm_utility"], tables["harm_utility"], HARM_FIELDS)
    _write_csv(paths["stat_tests"], tables["stat_tests"], STAT_FIELDS)
    _write_csv(paths["routing_stat_tests"], tables["routing_stat_tests"], STAT_FIELDS)
    return paths


def build_stat_test_rows(records: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    baselines = sorted({str(record.get("baseline_name", "default")) for record in records})
    if len(baselines) < 2:
        return []
    anchor = "generated_skill_base" if "generated_skill_base" in baselines else baselines[-1]
    rows: List[Dict[str, Any]] = []
    seen_pairs: set[tuple[str, str, str]] = set()
    for baseline in baselines:
        if baseline == anchor:
            continue
        _append_stat_pair(rows, seen_pairs, records, anchor, baseline)
    for left, right in KEY_STAT_TEST_COMPARISONS:
        if left in baselines and right in baselines:
            _append_stat_pair(rows, seen_pairs, records, left, right)
    return rows


def _append_stat_pair(
    rows: List[Dict[str, Any]],
    seen_pairs: set[tuple[str, str, str]],
    records: Sequence[Dict[str, Any]],
    baseline_a: str,
    baseline_b: str,
) -> None:
    key = tuple(sorted((baseline_a, baseline_b))) + ("joint_exact_match",)
    if key in seen_pairs:
        return
    seen_pairs.add(key)
    rows.append(mcnemar_test(records, baseline_a, baseline_b, metric_field="joint_exact_match"))
    rows.append(approximate_randomization_test(records, baseline_a, baseline_b, metric_field="joint_exact_match", iterations=500))


MAIN_FIELDS = [
    "baseline_name",
    "num_examples",
    "tool_selection_accuracy",
    "tool_selection_accuracy_wilson_low",
    "tool_selection_accuracy_wilson_high",
    "tool_selection_accuracy_bootstrap_examples_low",
    "tool_selection_accuracy_bootstrap_examples_high",
    "tool_selection_accuracy_bootstrap_tools_low",
    "tool_selection_accuracy_bootstrap_tools_high",
    "argument_parse_rate",
    "argument_schema_validity",
    "argument_exact_match",
    "joint_exact_match",
    "joint_exact_match_wilson_low",
    "joint_exact_match_wilson_high",
    "avg_latency_ms",
    "avg_token_overhead",
]

HARM_FIELDS = [
    "baseline_name",
    "num_controls",
    "positive_controls",
    "negative_controls",
    "harmful_activations",
    "trigger_precision",
    "trigger_recall",
    "harmful_skill_injection_rate",
    "skill_induced_harm_rate",
    "utility_joint_exact_match",
    "avg_latency_ms",
    "avg_token_overhead",
]

STAT_FIELDS = [
    "test",
    "baseline_a",
    "baseline_b",
    "metric",
    "paired_examples",
    "a_only_correct",
    "b_only_correct",
    "statistic",
    "observed_delta",
    "p_value",
]


def _summarize_group(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(items)
    tool_values = [1.0 if item.get("tool_selection_correct") else 0.0 for item in items]
    parse_values = [1.0 if item.get("argument_parse_ok") else 0.0 for item in items]
    schema_values = [1.0 if item.get("argument_schema_valid") else 0.0 for item in items]
    exact_values = [1.0 if item.get("argument_exact_match") else 0.0 for item in items]
    joint_values = [1.0 if item.get("joint_exact_match") else 0.0 for item in items]
    tool_groups = [str(item.get("expected_tool_name") or item.get("tool_name") or "") for item in items]
    latencies = [_latency_ms(item) for item in items if _latency_ms(item) is not None]
    token_overheads = [_token_overhead(item) for item in items if _token_overhead(item) is not None]
    return {
        "num_examples": total,
        "tool_selection_accuracy": _mean(tool_values),
        "tool_selection_accuracy_wilson": wilson_interval(sum(1 for value in tool_values if value), total),
        "tool_selection_accuracy_bootstrap_examples": bootstrap_ci(tool_values),
        "tool_selection_accuracy_bootstrap_tools": bootstrap_ci(tool_values, groups=tool_groups),
        "argument_parse_rate": _mean(parse_values),
        "argument_schema_validity": _mean(schema_values),
        "argument_exact_match": _mean(exact_values),
        "joint_exact_match": _mean(joint_values),
        "joint_exact_match_wilson": wilson_interval(sum(1 for value in joint_values if value), total),
        "avg_latency_ms": _mean(latencies),
        "avg_token_overhead": _mean(token_overheads),
    }


def _summarize_harm_group(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    positives = [item for item in items if bool(item.get("should_trigger", True))]
    negatives = [item for item in items if not bool(item.get("should_trigger", True))]
    tp = sum(1 for item in positives if bool(item.get("triggered", item.get("should_trigger", False))))
    fn = len(positives) - tp
    fp = sum(1 for item in negatives if bool(item.get("triggered", False)))
    harm = sum(1 for item in items if bool(item.get("harmful_injection") or item.get("skill_induced_harm")))
    latencies = [_latency_ms(item) for item in items if _latency_ms(item) is not None]
    token_overheads = [_token_overhead(item) for item in items if _token_overhead(item) is not None]
    return {
        "num_controls": len(items),
        "positive_controls": len(positives),
        "negative_controls": len(negatives),
        "harmful_activations": fp,
        "trigger_precision": round(tp / (tp + fp), 4) if (tp + fp) else 1.0,
        "trigger_recall": round(tp / (tp + fn), 4) if (tp + fn) else 1.0,
        "harmful_skill_injection_rate": round(fp / len(negatives), 4) if negatives else 0.0,
        "skill_induced_harm_rate": round(harm / len(items), 4) if items else 0.0,
        "avg_latency_ms": _mean(latencies),
        "avg_token_overhead": _mean(token_overheads),
    }


def _main_rows(summary: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for baseline, row in summary.items():
        tool_wilson = row["tool_selection_accuracy_wilson"]
        tool_boot_examples = row["tool_selection_accuracy_bootstrap_examples"]
        tool_boot_tools = row["tool_selection_accuracy_bootstrap_tools"]
        joint_wilson = row["joint_exact_match_wilson"]
        rows.append(
            {
                "baseline_name": baseline,
                "num_examples": row["num_examples"],
                "tool_selection_accuracy": _round(row["tool_selection_accuracy"]),
                "tool_selection_accuracy_wilson_low": tool_wilson["low"],
                "tool_selection_accuracy_wilson_high": tool_wilson["high"],
                "tool_selection_accuracy_bootstrap_examples_low": tool_boot_examples["low"],
                "tool_selection_accuracy_bootstrap_examples_high": tool_boot_examples["high"],
                "tool_selection_accuracy_bootstrap_tools_low": tool_boot_tools["low"],
                "tool_selection_accuracy_bootstrap_tools_high": tool_boot_tools["high"],
                "argument_parse_rate": _round(row["argument_parse_rate"]),
                "argument_schema_validity": _round(row["argument_schema_validity"]),
                "argument_exact_match": _round(row["argument_exact_match"]),
                "joint_exact_match": _round(row["joint_exact_match"]),
                "joint_exact_match_wilson_low": joint_wilson["low"],
                "joint_exact_match_wilson_high": joint_wilson["high"],
                "avg_latency_ms": _round(row["avg_latency_ms"]),
                "avg_token_overhead": _round(row["avg_token_overhead"]),
            }
        )
    return rows


def _harm_rows(harm_summary: Dict[str, Dict[str, Any]], utility_summary: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for baseline, row in harm_summary.items():
        utility = utility_summary.get(baseline, {})
        rows.append(
            {
                "baseline_name": baseline,
                "num_controls": row["num_controls"],
                "positive_controls": row["positive_controls"],
                "negative_controls": row["negative_controls"],
                "harmful_activations": row["harmful_activations"],
                "trigger_precision": row["trigger_precision"],
                "trigger_recall": row["trigger_recall"],
                "harmful_skill_injection_rate": row["harmful_skill_injection_rate"],
                "skill_induced_harm_rate": row["skill_induced_harm_rate"],
                "utility_joint_exact_match": _round(float(utility.get("joint_exact_match", 0.0))),
                "avg_latency_ms": _round(row["avg_latency_ms"]),
                "avg_token_overhead": _round(row["avg_token_overhead"]),
            }
        )
    return rows


def _write_csv(path: Path, rows: Sequence[Dict[str, Any]], fieldnames: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _dict_value(record: Dict[str, Any], keys: Sequence[str]) -> Dict[str, Any]:
    for key in keys:
        value = record.get(key)
        if isinstance(value, dict):
            if key == "ground_truth" and isinstance(value.get("arguments"), dict):
                return dict(value["arguments"])
            return dict(value)
    return {}


def _parsed_arguments(record: Dict[str, Any]) -> bool:
    if record.get("should_trigger") is False and record.get("triggered") is False:
        return True
    if record.get("argument_parse_ok") is False:
        return False
    if record.get("parse_error") or record.get("error") == "argument_parse_error":
        return False
    return isinstance(record.get("predicted_arguments"), dict)


def _paired_record_key(record: Dict[str, Any]) -> str:
    parts = [
        str(record.get("model_slug") or record.get("model_name") or ""),
        str(record.get("record_type") or ""),
        str(record.get("task_id") or ""),
    ]
    return "::".join(parts)


def _binary_metric(record: Dict[str, Any], metric_field: str) -> bool:
    return bool(_metric_value(record, metric_field) >= 0.5)


def _metric_value(record: Dict[str, Any], metric_field: str) -> float:
    value = record.get(metric_field)
    if value is None and metric_field == "joint_exact_match":
        value = record.get("exact_match")
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _latency_ms(record: Dict[str, Any]) -> float | None:
    for key in ("prediction_latency_ms", "latency_ms", "duration_ms"):
        if key in record:
            try:
                return float(record[key])
            except (TypeError, ValueError):
                return None
    metadata = record.get("prediction_metadata")
    if isinstance(metadata, dict):
        for key in ("prediction_latency_ms", "latency_ms"):
            if key in metadata:
                try:
                    return float(metadata[key])
                except (TypeError, ValueError):
                    return None
    return None


def _token_overhead(record: Dict[str, Any]) -> float | None:
    for key in ("token_overhead_estimate", "token_overhead", "prompt_tokens", "total_tokens"):
        if key in record:
            try:
                return float(record[key])
            except (TypeError, ValueError):
                return None
    metadata = record.get("prediction_metadata")
    if isinstance(metadata, dict):
        for key in ("token_overhead_estimate", "prompt_tokens", "total_tokens"):
            if key in metadata:
                try:
                    return float(metadata[key])
                except (TypeError, ValueError):
                    return None
    return None


def _looks_like_path_key(key: str) -> bool:
    lowered = key.lower()
    return any(marker in lowered for marker in ("path", "file", "dir", "folder"))


def _looks_like_path_value(value: str) -> bool:
    return "\\" in value or value.startswith("./") or value.startswith("../")


def _value_conforms_to_schema(value: Any, schema: Dict[str, Any]) -> bool:
    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        if "null" in schema_type and value is None:
            return True
        schema_type = next((item for item in schema_type if item != "null"), None)
    if value is None:
        return bool(schema.get("nullable"))
    if schema_type == "object" or isinstance(schema.get("properties"), dict):
        if not isinstance(value, dict):
            return False
        properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
        required = schema.get("required") if isinstance(schema.get("required"), list) else []
        if any(key not in value for key in required):
            return False
        if schema.get("additionalProperties") is False:
            extra = set(value) - set(properties)
            if extra:
                return False
        for key, child in value.items():
            child_schema = properties.get(key)
            if isinstance(child_schema, dict) and not _value_conforms_to_schema(child, child_schema):
                return False
        return True
    if schema_type == "array":
        if not isinstance(value, list):
            return False
        item_schema = schema.get("items") if isinstance(schema.get("items"), dict) else {}
        return all(_value_conforms_to_schema(item, item_schema) for item in value)
    if isinstance(schema.get("enum"), list) and value not in schema["enum"]:
        return False
    if schema_type in {"string"}:
        return isinstance(value, str)
    if schema_type in {"integer", "int"}:
        return isinstance(value, int) and not isinstance(value, bool)
    if schema_type in {"number", "float"}:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if schema_type == "boolean":
        return isinstance(value, bool)
    return True


def _mean(values: Sequence[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _round(value: float) -> float:
    return round(float(value), 4)

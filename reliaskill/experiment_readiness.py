from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import yaml

from reliaskill.data_audit import audit_dataset_integrity
from reliaskill.cluster import slugify
from reliaskill.scheduler import load_model_config


REQUIRED_CONFIG_CONDITIONS = [
    "raw_mcp",
    "schema_only",
    "raw_schema_plus_examples",
    "prompt_only_careful_tool_use",
    "generated_docs_no_validation",
    "validated_skill",
    "repaired_skill",
    "gated_skill",
    "reliaskill_v1",
    "generated_skill_base",
    "generated_docs_verbose",
    "raw_docs_full",
    "retrieval_tool_card",
    "skill_prompt_boundary_first",
    "skill_prompt_verbose_docs",
]

REQUIRED_RESULT_CONDITIONS = [
    "raw_mcp",
    "generated_skill_base",
    "gated_skill",
    "reliaskill_v1",
]

REQUIRED_STAT_COMPARISONS = [
    ("raw_mcp", "generated_skill_base"),
    ("raw_mcp", "gated_skill"),
    ("raw_mcp", "reliaskill_v1"),
    ("generated_skill_base", "gated_skill"),
    ("generated_skill_base", "reliaskill_v1"),
]

REQUIRED_SLICE_FILES = [
    "slice_analysis_by_domain.csv",
    "slice_analysis_by_tool_complexity.csv",
    "slice_analysis_by_negative_category.csv",
]


def audit_experiment_readiness(
    *,
    config_path: str | Path | None = None,
    tables_dir: str | Path = "outputs/tables",
    run_dir: str | Path | None = None,
    min_examples: int | None = None,
    min_stat_pairs: int | None = None,
    require_live: bool = False,
    required_config_conditions: Sequence[str] = REQUIRED_CONFIG_CONDITIONS,
    required_result_conditions: Sequence[str] = REQUIRED_RESULT_CONDITIONS,
    required_stat_comparisons: Sequence[Tuple[str, str]] = REQUIRED_STAT_COMPARISONS,
) -> Dict[str, Any]:
    tables = Path(tables_dir)
    run = Path(run_dir) if run_dir else None
    checks: List[Dict[str, Any]] = []
    config: Dict[str, Any] = {}
    effective_min_examples = int(min_examples or 0)

    if config_path:
        config_file = Path(config_path)
        config = _load_mapping(config_file)
        _add_check(
            checks,
            "config_exists",
            "fail",
            config_file.exists(),
            f"Experiment config exists: {config_file}",
        )
        _check_config_conditions(checks, config, required_config_conditions)
        _check_config_negative_controls(checks, config)
        if config.get("tools_path") and config.get("tasks_path"):
            try:
                data_report = audit_dataset_integrity(config_file)
            except Exception as exc:  # pragma: no cover - defensive for corrupted external artifacts
                data_report = {"ok": False, "selected_task_count": 0, "error": str(exc)}
            _add_check(
                checks,
                "dataset_integrity_audit",
                "fail",
                bool(data_report.get("ok")),
                "Dataset integrity audit passes duplicate, leakage, and coverage checks.",
                {
                    "selected_task_count": data_report.get("selected_task_count", 0),
                    "selected_tool_count": data_report.get("selected_tool_count", 0),
                    "failures": data_report.get("num_failures", 0),
                    "error": data_report.get("error", ""),
                },
            )
            if min_examples is None:
                effective_min_examples = int(data_report.get("selected_task_count") or 0)
        elif min_examples is None:
            _add_check(
                checks,
                "dataset_integrity_audit",
                "warn",
                False,
                "No tools_path/tasks_path in config; skipped dataset integrity audit and sample-size derivation.",
            )
        if _config_requires_live(config):
            require_live = True
    else:
        _add_check(checks, "config_provided", "warn", False, "No experiment config supplied; skipped config coverage checks.")
    if min_examples is not None:
        effective_min_examples = int(min_examples)

    main_rows = _read_csv(tables / "main_results.csv")
    _add_check(
        checks,
        "main_results_exists",
        "fail",
        bool(main_rows),
        f"Main result table has rows: {tables / 'main_results.csv'}",
        {"rows": len(main_rows)},
    )
    _check_main_results(checks, main_rows, effective_min_examples, required_result_conditions)
    routing_rows = _read_csv(tables / "routing_results.csv")
    _check_routing_results(checks, routing_rows, effective_min_examples, required_result_conditions, config)
    by_model_rows = _read_csv(tables / "main_results_by_model.csv")
    _check_by_model_results(checks, by_model_rows, config, config_path, effective_min_examples, required_result_conditions)
    routing_by_model_rows = _read_csv(tables / "routing_results_by_model.csv")
    _check_by_model_results(
        checks,
        routing_by_model_rows,
        config,
        config_path,
        effective_min_examples,
        required_result_conditions,
        table_id_prefix="routing_by_model",
    )

    harm_rows = _read_csv(tables / "harm_utility.csv")
    _check_harm_table(checks, harm_rows)

    stat_rows = _read_csv(tables / "stat_tests.csv")
    _check_stat_tests(checks, stat_rows, min_stat_pairs or min_examples, required_stat_comparisons)

    _check_slice_outputs(checks, tables)
    _check_live_execution(checks, tables=tables, run=run, require_live=require_live)
    _check_no_backend_fallbacks(checks, run=run, strict_backends=_strict_backends(config))
    _check_negative_record_fields(checks, run=run)
    _check_preflight_only(checks, run)

    failures = [check for check in checks if check["severity"] == "fail" and not check["passed"]]
    warnings = [check for check in checks if check["severity"] == "warn" and not check["passed"]]
    return {
        "ok": not failures,
        "num_checks": len(checks),
        "num_failures": len(failures),
        "num_warnings": len(warnings),
        "min_examples": effective_min_examples,
        "tables_dir": str(tables),
        "config_path": str(config_path) if config_path else "",
        "run_dir": str(run) if run else "",
        "checks": checks,
    }


def build_readiness_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# ReliaSkill Experiment Readiness Audit",
        "",
        f"- Ready: `{'yes' if report['ok'] else 'no'}`",
        f"- Failures: `{report['num_failures']}`",
        f"- Warnings: `{report['num_warnings']}`",
        f"- Minimum examples per required result condition: `{report['min_examples']}`",
        f"- Tables: `{report['tables_dir']}`",
    ]
    if report.get("config_path"):
        lines.append(f"- Config: `{report['config_path']}`")
    if report.get("run_dir"):
        lines.append(f"- Run directory: `{report['run_dir']}`")
    lines.extend(["", "## Checks", ""])
    for check in report["checks"]:
        status = "PASS" if check["passed"] else check["severity"].upper()
        lines.append(f"- `{status}` `{check['id']}`: {check['message']}")
        if check.get("details"):
            lines.append(f"  Details: `{json.dumps(check['details'], sort_keys=True)}`")
    return "\n".join(lines).strip() + "\n"


def write_readiness_report(
    report: Dict[str, Any],
    *,
    output_json: str | Path = "outputs/reports/experiment_readiness.json",
    output_md: str | Path = "outputs/reports/experiment_readiness.md",
) -> Dict[str, Path]:
    json_path = Path(output_json)
    md_path = Path(output_md)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(build_readiness_markdown(report), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def _check_config_conditions(checks: List[Dict[str, Any]], config: Dict[str, Any], required: Sequence[str]) -> None:
    configured = {str(item) for item in config.get("conditions") or []}
    missing = [condition for condition in required if condition not in configured]
    _add_check(
        checks,
        "required_config_conditions",
        "fail",
        not missing,
        "Experiment config includes reviewer-critical baselines and method variants.",
        {"missing": missing, "configured_count": len(configured)},
    )


def _check_config_negative_controls(checks: List[Dict[str, Any]], config: Dict[str, Any]) -> None:
    controls = config.get("controls") if isinstance(config.get("controls"), dict) else {}
    negatives = _int_or_none(controls.get("negatives_per_tool_total") or config.get("negatives_per_tool"))
    _add_check(
        checks,
        "config_negative_controls",
        "fail",
        bool(negatives and negatives > 0),
        "Experiment config requests adjacent negative controls.",
        {"negatives_per_tool": negatives},
    )


def _check_main_results(
    checks: List[Dict[str, Any]],
    rows: Sequence[Dict[str, str]],
    min_examples: int,
    required_conditions: Sequence[str],
) -> None:
    by_condition = {row.get("baseline_name", ""): row for row in rows}
    missing = [condition for condition in required_conditions if condition not in by_condition]
    underpowered = {
        condition: _int_or_none(by_condition.get(condition, {}).get("num_examples")) or 0
        for condition in required_conditions
        if condition in by_condition and (_int_or_none(by_condition[condition].get("num_examples")) or 0) < min_examples
    }
    _add_check(
        checks,
        "required_result_conditions",
        "fail",
        not missing,
        "Main results include required conditions.",
        {"missing": missing},
    )
    _add_check(
        checks,
        "result_condition_sample_sizes",
        "fail",
        not underpowered,
        "Required result conditions meet the configured minimum sample size.",
        {"underpowered": underpowered, "min_examples": min_examples},
    )


def _check_by_model_results(
    checks: List[Dict[str, Any]],
    rows: Sequence[Dict[str, str]],
    config: Dict[str, Any],
    config_path: str | Path | None,
    min_examples: int,
    required_conditions: Sequence[str],
    *,
    table_id_prefix: str = "by_model",
) -> None:
    expected_models = _configured_model_slugs(config, Path(config_path).resolve().parent if config_path else Path.cwd())
    if len(expected_models) <= 1:
        return
    _add_check(
        checks,
        f"{table_id_prefix}_results_exist",
        "fail",
        bool(rows),
        "Per-model result table exists for multi-predictor experiments.",
        {"expected_models": sorted(expected_models)},
    )
    if not rows:
        return
    grouped = {(row.get("model_slug") or slugify(str(row.get("model_name") or "")), row.get("baseline_name", "")): row for row in rows}
    missing = []
    underpowered = {}
    for model_slug in sorted(expected_models):
        for condition in required_conditions:
            row = grouped.get((model_slug, condition))
            if row is None:
                missing.append(f"{model_slug}/{condition}")
                continue
            count = _int_or_none(row.get("num_examples")) or 0
            if count < min_examples:
                underpowered[f"{model_slug}/{condition}"] = count
    _add_check(
        checks,
        f"{table_id_prefix}_required_conditions",
        "fail",
        not missing,
        "Every configured predictor has required result conditions.",
        {"missing": missing},
    )
    _add_check(
        checks,
        f"{table_id_prefix}_sample_sizes",
        "fail",
        not underpowered,
        "Every configured predictor meets the minimum sample size for required conditions.",
        {"underpowered": underpowered, "min_examples": min_examples},
    )


def _check_routing_results(
    checks: List[Dict[str, Any]],
    rows: Sequence[Dict[str, str]],
    min_examples: int,
    required_conditions: Sequence[str],
    config: Dict[str, Any],
) -> None:
    scheduler = config.get("scheduler") if isinstance(config.get("scheduler"), dict) else {}
    routing_config = config.get("routing") if isinstance(config.get("routing"), dict) else {}
    routing_required = bool(scheduler.get("include_routing") or routing_config or config.get("routing_candidate_sizes"))
    _add_check(
        checks,
        "routing_results_exist",
        "fail" if routing_required else "warn",
        bool(rows) or not routing_required,
        "Routing/end-to-end result table exists separately from structured-call results.",
        {"rows": len(rows), "required": routing_required},
    )
    if not rows:
        return
    by_condition = {row.get("baseline_name", ""): row for row in rows}
    missing = [condition for condition in required_conditions if condition not in by_condition]
    underpowered = {
        condition: _int_or_none(by_condition.get(condition, {}).get("num_examples")) or 0
        for condition in required_conditions
        if condition in by_condition and (_int_or_none(by_condition[condition].get("num_examples")) or 0) < min_examples
    }
    _add_check(
        checks,
        "routing_required_conditions",
        "fail" if routing_required else "warn",
        not missing or not routing_required,
        "Routing results include required conditions.",
        {"missing": missing},
    )
    _add_check(
        checks,
        "routing_sample_sizes",
        "fail" if routing_required else "warn",
        not underpowered or not routing_required,
        "Routing results meet the configured minimum sample size.",
        {"underpowered": underpowered, "min_examples": min_examples},
    )


def _check_harm_table(checks: List[Dict[str, Any]], rows: Sequence[Dict[str, str]]) -> None:
    total_negative = sum((_int_or_none(row.get("negative_controls")) or 0) for row in rows)
    _add_check(
        checks,
        "harm_table_negative_controls",
        "fail",
        total_negative > 0,
        "Harm/utility table includes evaluated negative controls.",
        {"negative_controls": total_negative, "rows": len(rows)},
    )


def _check_stat_tests(
    checks: List[Dict[str, Any]],
    rows: Sequence[Dict[str, str]],
    min_pairs: int,
    required_comparisons: Sequence[Tuple[str, str]],
) -> None:
    observed: Dict[Tuple[str, str], int] = {}
    for row in rows:
        pair = _unordered_pair(row.get("baseline_a", ""), row.get("baseline_b", ""))
        observed[pair] = max(observed.get(pair, 0), _int_or_none(row.get("paired_examples")) or 0)
    missing = []
    underpowered = {}
    for left, right in required_comparisons:
        pair = _unordered_pair(left, right)
        pairs = observed.get(pair)
        if pairs is None:
            missing.append(f"{left} vs {right}")
        elif pairs < min_pairs:
            underpowered[f"{left} vs {right}"] = pairs
    _add_check(
        checks,
        "required_statistical_tests",
        "fail",
        not missing,
        "Paired significance tests exist for required comparisons.",
        {"missing": missing},
    )
    _add_check(
        checks,
        "statistical_test_pair_counts",
        "fail",
        not underpowered,
        "Paired significance tests use enough matched examples.",
        {"underpowered": underpowered, "min_pairs": min_pairs},
    )


def _check_slice_outputs(checks: List[Dict[str, Any]], tables: Path) -> None:
    missing = [name for name in REQUIRED_SLICE_FILES if not (tables / name).exists()]
    _add_check(
        checks,
        "slice_outputs_exist",
        "fail",
        not missing,
        "Slice analysis outputs exist for domain, tool complexity, and negative category.",
        {"missing": missing},
    )
    unsuppressed_counts = {}
    for name in REQUIRED_SLICE_FILES:
        rows = _read_csv(tables / name)
        unsuppressed_counts[name] = sum(1 for row in rows if str(row.get("suppressed", "")).lower() not in {"true", "1"})
    _add_check(
        checks,
        "slice_outputs_have_unsuppressed_rows",
        "warn",
        any(count > 0 for count in unsuppressed_counts.values()),
        "At least one slice table has unsuppressed rows.",
        {"unsuppressed_counts": unsuppressed_counts},
    )


def _check_live_execution(checks: List[Dict[str, Any]], *, tables: Path, run: Path | None, require_live: bool) -> None:
    if run:
        candidates = sorted(run.rglob("live_exec_results.jsonl")) + sorted(run.rglob("live_exec_results.csv"))
    else:
        candidates = [tables / "live_exec_results.csv"]
    rows = []
    existing = []
    for path in candidates:
        if path.exists():
            existing.append(str(path))
            rows.extend(_read_records(path))
    _add_check(
        checks,
        "live_execution_results",
        "fail" if require_live else "warn",
        bool(rows) or not require_live,
        "Live/sandbox execution results are present when required by config.",
        {"paths": existing, "rows": len(rows), "required": require_live},
    )


def _check_no_backend_fallbacks(checks: List[Dict[str, Any]], *, run: Path | None, strict_backends: bool) -> None:
    if not run:
        _add_check(
            checks,
            "no_backend_fallbacks",
            "warn" if strict_backends else "warn",
            not strict_backends,
            "Run directory was not supplied; skipped strict fallback scan.",
            {"strict_backends": strict_backends},
        )
        return
    records = []
    for pattern in ("prediction_records.jsonl", "routing_records.jsonl", "live_exec_results.jsonl", "live_exec_predictions.jsonl"):
        for path in sorted(run.rglob(pattern)):
            for row in _read_records(path):
                row["_source_path"] = str(path)
                records.append(row)
    for pattern in ("skill.json", "metadata.json"):
        for path in sorted(run.rglob(pattern)):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            records.append(
                {
                    "_source_path": str(path),
                    "task_id": "",
                    "baseline_name": (data.get("baseline_name") or data.get("tool_name") or "") if isinstance(data, dict) else "",
                    "generation_fallback_used": _contains_truthy_key(data, "generation_fallback_used"),
                    "predictor_fallback_used": _contains_truthy_key(data, "predictor_fallback_used"),
                }
            )
    fallback_records = [
        {
            "path": row.get("_source_path", ""),
            "task_id": row.get("task_id") or row.get("live_task_id"),
            "baseline_name": row.get("baseline_name"),
            "generation_fallback_used": row.get("generation_fallback_used"),
            "predictor_fallback_used": row.get("predictor_fallback_used"),
        }
        for row in records
        if _truthy(row.get("generation_fallback_used")) or _truthy(row.get("predictor_fallback_used"))
    ]
    _add_check(
        checks,
        "no_backend_fallbacks",
        "fail",
        not fallback_records,
        "Accepted run outputs contain no generation or predictor fallback records.",
        {"num_scanned": len(records), "fallback_records": fallback_records[:20], "num_fallback_records": len(fallback_records)},
    )


def _check_negative_record_fields(checks: List[Dict[str, Any]], *, run: Path | None) -> None:
    if not run:
        return
    records = []
    for pattern in ("prediction_records.jsonl", "routing_records.jsonl"):
        for path in sorted(run.rglob(pattern)):
            for row in _read_records(path):
                row["_source_path"] = str(path)
                records.append(row)
    if not records:
        return
    negative_records = [row for row in records if _falsey(row.get("should_trigger"))]
    missing_fields = [
        {
            "path": row.get("_source_path", ""),
            "task_id": row.get("task_id"),
            "baseline_name": row.get("baseline_name"),
            "has_triggered": "triggered" in row,
            "has_negative_category": "negative_category" in row,
        }
        for row in negative_records
        if "triggered" not in row or "negative_category" not in row
    ]
    _add_check(
        checks,
        "negative_control_scoring_fields",
        "fail",
        bool(negative_records) and not missing_fields,
        "Negative-control records include should_trigger, triggered, and category fields for harm scoring.",
        {"negative_records": len(negative_records), "missing_fields": missing_fields[:20]},
    )


def _check_preflight_only(checks: List[Dict[str, Any]], run: Path | None) -> None:
    if not run:
        return
    manifests = list(run.rglob("*manifest*.json")) + list(run.rglob("*summary*.json"))
    preflight_paths = []
    for path in manifests:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if '"preflight_only"' in text or '"preflight": true' in text:
            preflight_paths.append(str(path))
    prediction_records = list(run.rglob("prediction_records.jsonl")) + list(run.rglob("routing_records.jsonl"))
    _add_check(
        checks,
        "not_preflight_only",
        "fail",
        not preflight_paths or bool(prediction_records),
        "Run directory is not only preflight metadata.",
        {"preflight_manifests": preflight_paths, "prediction_record_files": len(prediction_records)},
    )


def _config_requires_live(config: Dict[str, Any]) -> bool:
    live = config.get("live_execution")
    if not isinstance(live, dict):
        return False
    return str(live.get("enabled", "")).lower() == "true" or live.get("enabled") is True


def _strict_backends(config: Dict[str, Any]) -> bool:
    runtime = config.get("runtime") if isinstance(config.get("runtime"), dict) else {}
    return bool(runtime.get("strict_backends", False))


def _add_check(
    checks: List[Dict[str, Any]],
    check_id: str,
    severity: str,
    passed: bool,
    message: str,
    details: Dict[str, Any] | None = None,
) -> None:
    checks.append(
        {
            "id": check_id,
            "severity": severity,
            "passed": bool(passed),
            "message": message,
            "details": details or {},
        }
    )


def _load_mapping(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        if path.suffix.lower() in {".yaml", ".yml"}:
            data = yaml.safe_load(f) or {}
        else:
            data = json.load(f)
    return data if isinstance(data, dict) else {}


def _configured_model_slugs(config: Dict[str, Any], base_dir: Path) -> set[str]:
    models = config.get("models") or []
    slugs: set[str] = set()
    for raw in models:
        try:
            if isinstance(raw, str):
                model = load_model_config(_resolve_model_path(raw, base_dir))
            elif isinstance(raw, dict) and raw.get("config"):
                model = load_model_config(_resolve_model_path(str(raw["config"]), base_dir))
                if len(raw) > 1:
                    data = model.model_dump()
                    overrides = dict(raw)
                    overrides.pop("config", None)
                    data.update(overrides)
                    model = load_model_config(data)
            elif isinstance(raw, dict):
                model = load_model_config(raw)
            else:
                continue
        except (OSError, ValueError):
            continue
        slugs.add(slugify(model.model_name))
    return slugs


def _resolve_model_path(value: str, base_dir: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    for candidate in (base_dir / path, Path.cwd() / path):
        if candidate.exists():
            return candidate
    return Path.cwd() / path


def _read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _read_records(path: Path) -> List[Dict[str, Any]]:
    if path.suffix.lower() == ".csv":
        return [dict(row) for row in _read_csv(path)]
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(value, dict):
                    rows.append(value)
    return rows


def _unordered_pair(left: str, right: str) -> Tuple[str, str]:
    return tuple(sorted((str(left), str(right))))  # type: ignore[return-value]


def _int_or_none(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.lower() in {"true", "1", "yes"}
    return bool(value)


def _falsey(value: Any) -> bool:
    if isinstance(value, str):
        return value.lower() in {"false", "0", "no"}
    return value is False


def _contains_truthy_key(value: Any, target_key: str) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == target_key and _truthy(item):
                return True
            if _contains_truthy_key(item, target_key):
                return True
    if isinstance(value, list):
        return any(_contains_truthy_key(item, target_key) for item in value)
    return False


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit whether ReliaSkill experiment artifacts are claim-ready.")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--tables", type=Path, default=Path("outputs/tables"))
    parser.add_argument("--run", type=Path, default=None)
    parser.add_argument("--min-examples", type=int, default=None)
    parser.add_argument("--min-stat-pairs", type=int, default=None)
    parser.add_argument("--require-live", action="store_true")
    parser.add_argument("--output-json", type=Path, default=Path("outputs/reports/experiment_readiness.json"))
    parser.add_argument("--output-md", type=Path, default=Path("outputs/reports/experiment_readiness.md"))
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when blocking failures are present.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = audit_experiment_readiness(
        config_path=args.config,
        tables_dir=args.tables,
        run_dir=args.run,
        min_examples=args.min_examples,
        min_stat_pairs=args.min_stat_pairs,
        require_live=args.require_live,
    )
    paths = write_readiness_report(report, output_json=args.output_json, output_md=args.output_md)
    print(json.dumps({"ok": report["ok"], "failures": report["num_failures"], "warnings": report["num_warnings"]}, sort_keys=True))
    print(f"json={paths['json']}")
    print(f"markdown={paths['markdown']}")
    return 1 if args.strict and not report["ok"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

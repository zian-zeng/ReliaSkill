from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from autoskill.behavior import load_behavior_cases
from autoskill.benchmark import load_benchmark_tasks
from autoskill.config import load_json_config
from autoskill.eval_types import EvalTask
from autoskill.experiment import (
    build_skill_variant_map,
    load_tools,
    run_benchmark_pipeline,
    run_packaging_pipeline,
    run_routing_benchmark_pipeline,
)
from autoskill.generator import SkillGenerator
from autoskill.local_model import clear_model_cache
from autoskill.metrics import build_metric_tables, write_metric_tables
from autoskill.packaging import write_skill_package
from autoskill.predictor import build_predictor_from_config, safe_predict
from autoskill.reliability import build_reliability_variants
from reliaskill.live_exec.evaluator import evaluate_live_exec_tasks
from reliaskill.live_exec.task_builder import build_live_exec_tasks
from reliaskill.live_exec.tool_defs import build_live_exec_tools
from reliaskill.scheduler import load_model_config


RELIABILITY_CONDITIONS = {"naive_skill", "validated_skill", "repaired_skill", "gated_skill"}


def slugify(value: str) -> str:
    slug = "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in value)
    return slug.strip("_")[:80] or "unknown"


def tool_slug(value: str) -> str:
    slug = "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in value)
    return slug[:50] or "unknown"


def shared_package_root(config: Dict[str, Any], output_root: str | Path | None = None) -> Path:
    shared = config.get("shared_skill_packages") if isinstance(config.get("shared_skill_packages"), dict) else {}
    root = Path(output_root or config.get("output_root") or "outputs/emnlp_acceptance")
    if output_root is not None:
        return root / "shared_packages"
    if shared.get("root"):
        return Path(str(shared["root"]))
    return root / "shared_packages"


def selected_tool_names(config: Dict[str, Any], tools: Dict[str, Any], *, shard_index: int | None = None, num_shards: int | None = None) -> List[str]:
    names = sorted(tools)
    max_tools = _configured_max_tools(config)
    if max_tools:
        names = names[:max_tools]
    if shard_index is None and num_shards is None:
        return names
    if shard_index is None or num_shards is None:
        raise ValueError("shard_index and num_shards must be provided together.")
    if num_shards <= 0:
        raise ValueError("num_shards must be positive.")
    if shard_index < 0 or shard_index >= num_shards:
        raise ValueError("shard_index must be in [0, num_shards).")
    return [name for index, name in enumerate(names) if index % num_shards == shard_index]


def build_shared_skill_packages(
    config_path: str | Path,
    *,
    output_root: str | Path | None = None,
    force: bool = False,
) -> Dict[str, Any]:
    config = load_json_config(config_path)
    strict_backends = _strict_backends(config)
    all_tools = load_tools(config["tools_path"])
    names = selected_tool_names(config, all_tools)
    benchmark_tools = {name: all_tools[name] for name in names}
    live_tools = _configured_live_tools(config)
    tools = {**benchmark_tools, **live_tools}
    root = shared_package_root(config, output_root)
    if force and root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)

    generator = SkillGenerator(backend_config=config.get("generator"), allow_fallback=not strict_backends)
    allowed_conditions = [str(item) for item in config.get("conditions") or []]
    package_records, package_summary, _ = run_packaging_pipeline(
        tools=tools,
        output_dir=root,
        generator=generator,
        allowed_conditions=allowed_conditions or None,
    )

    reliability_conditions = sorted(set(allowed_conditions).intersection(RELIABILITY_CONDITIONS))
    reliability_records = []
    if reliability_conditions:
        shared_config = config.get("shared_skill_packages") if isinstance(config.get("shared_skill_packages"), dict) else {}
        behavior_path = (
            shared_config.get("dev_controls_path")
            or config.get("dev_controls_path")
            or "data/controls/dev.jsonl"
        )
        behavior_cases = load_behavior_cases(behavior_path)
        predictor_config = (
            shared_config.get("reliability_predictor")
            or config.get("reliability_predictor")
            or config.get("predictor")
            or {"type": "heuristic"}
        )
        predictor = build_predictor_from_config(predictor_config)
        max_repair_rounds = int(shared_config.get("max_repair_rounds") or 2)
        deploy_threshold = float(shared_config.get("deploy_threshold") or 85.0)
        for tool in tools.values():
            base_skill = build_skill_variant_map(
                tool,
                tools,
                generator,
                allowed_conditions=["generated_skill_base"],
                package_manager_dir=root,
                allow_package_generation=False,
            )["generated_skill_base"]
            variants = build_reliability_variants(
                tool,
                generator=generator,
                behavior_cases=behavior_cases,
                predictor=predictor,
                max_repair_rounds=max_repair_rounds,
                deploy_threshold=deploy_threshold,
                base_generated_skill=base_skill,
                allow_predictor_fallback=not strict_backends,
            )
            for condition in reliability_conditions:
                row = variants[condition]
                write_skill_package(
                    root / tool_slug(tool.tool_name) / condition,
                    tool,
                    row["skill"],
                    row["validation_report"],
                    behavior_report=row["behavior_report"],
                    reliability_score=row["reliability_score"],
                    repair_report=row["repair_report"],
                )
                reliability_records.append(
                    {
                        "tool_name": tool.tool_name,
                        "baseline_name": condition,
                        "gate_decision": row["reliability_score"].decision,
                        "reliability_score": row["reliability_score"].score,
                    }
                )

    manifest = {
        "config_path": str(config_path),
        "shared_package_root": str(root),
        "tools_path": config["tools_path"],
        "num_tools": len(tools),
        "num_benchmark_tools": len(benchmark_tools),
        "num_live_tools": len(live_tools),
        "conditions": allowed_conditions,
        "packaged_records": len(package_records),
        "reliability_conditions": reliability_conditions,
        "reliability_records": len(reliability_records),
        "package_summary": package_summary,
    }
    (root / "shared_package_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_jsonl(root / "reliability_package_records.jsonl", reliability_records)
    return manifest


def run_cluster_shard(
    config_path: str | Path,
    *,
    shard_index: int,
    num_shards: int,
    output_root: str | Path | None = None,
    shared_packages: str | Path | None = None,
    models: Sequence[str] | None = None,
    skip_routing: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    config = load_json_config(config_path)
    strict_backends = _strict_backends(config)
    root = Path(output_root or config.get("output_root") or "outputs/emnlp_acceptance")
    package_root = Path(shared_packages) if shared_packages else shared_package_root(config, root)
    all_tools = load_tools(config["tools_path"])
    full_names = selected_tool_names(config, all_tools)
    shard_names = selected_tool_names(config, all_tools, shard_index=shard_index, num_shards=num_shards)
    tools = {name: all_tools[name] for name in full_names}
    shard_set = set(shard_names)
    full_tasks = _balanced_tasks_for_tools(config, load_benchmark_tasks(config["tasks_path"]), full_names)
    tasks = [task for task in full_tasks if task.tool_name in shard_set]
    live_tasks = _selected_live_tasks(config, shard_index=shard_index, num_shards=num_shards)
    model_configs = _load_config_models(config, base_dir=Path(config_path).resolve().parent)
    if models:
        requested = {str(item) for item in models}
        model_configs = [
            model for model in model_configs
            if model.model_name in requested or slugify(model.model_name) in requested or model.config_path in requested
        ]
    allowed_conditions = [str(item) for item in config.get("conditions") or []]
    if dry_run:
        return {
            "dry_run": True,
            "config_path": str(config_path),
            "output_root": str(root),
            "shared_package_root": str(package_root),
            "shard_index": shard_index,
            "num_shards": num_shards,
            "num_full_tools": len(full_names),
            "num_shard_tools": len(shard_names),
            "num_tasks": len(tasks),
            "num_live_tasks": len(live_tasks),
            "models": [model.model_name for model in model_configs],
            "conditions": allowed_conditions,
        }

    manifests = []
    for model in model_configs:
        model_slug = slugify(model.model_name)
        model_root = root / "predictors" / model_slug / f"shard_{shard_index:02d}"
        predictor_config = _model_to_backend_config(model)
        generator = SkillGenerator(backend_config=config.get("generator"), allow_fallback=not strict_backends)
        predictor = build_predictor_from_config(predictor_config)
        try:
            benchmark_scores, benchmark_summary, benchmark_details = run_benchmark_pipeline(
                tools=tools,
                tasks_path=config["tasks_path"],
                output_dir=model_root / "benchmark",
                generator=generator,
                predictor=predictor,
                allowed_conditions=allowed_conditions,
                tasks=tasks,
                package_manager_dir=package_root,
                allow_package_generation=False,
                allow_predictor_fallback=not strict_backends,
                model_name=model.model_name,
                model_slug=model_slug,
                shard_index=shard_index,
                num_shards=num_shards,
            )
            routing_summary = {}
            routing_details = {}
            if not skip_routing:
                _, routing_summary, routing_details = run_routing_benchmark_pipeline(
                    tools=tools,
                    tasks_path=config["tasks_path"],
                    output_dir=model_root / "routing_benchmark",
                    generator=generator,
                    predictor=predictor,
                    allowed_conditions=allowed_conditions,
                    tasks=tasks,
                    package_manager_dir=package_root,
                    allow_package_generation=False,
                    allow_predictor_fallback=not strict_backends,
                    benchmark_dir=model_root / "benchmark",
                    model_name=model.model_name,
                    model_slug=model_slug,
                    shard_index=shard_index,
                    num_shards=num_shards,
                )
            live_exec_summary = {}
            live_exec_records = []
            if _live_execution_enabled(config):
                live_exec_records, live_exec_summary = _run_live_exec_for_model(
                    config,
                    model_root=model_root,
                    package_root=package_root,
                    generator=generator,
                    predictor=predictor,
                    allowed_conditions=allowed_conditions,
                    model_name=model.model_name,
                    model_slug=model_slug,
                    shard_index=shard_index,
                    num_shards=num_shards,
                    allow_predictor_fallback=not strict_backends,
                )
        finally:
            clear_model_cache()
        manifest = {
            "config_path": str(config_path),
            "output_root": str(model_root),
            "shared_package_root": str(package_root),
            "model_name": model.model_name,
            "model_slug": model_slug,
            "model_config": model.model_dump(),
            "predictor_config": predictor_config,
            "shard_index": shard_index,
            "num_shards": num_shards,
            "num_full_tools": len(full_names),
            "num_shard_tools": len(shard_names),
            "num_tasks": len(tasks),
            "conditions": allowed_conditions,
            "benchmark_summary": benchmark_summary,
            "benchmark_detail_summaries": benchmark_details,
            "routing_summary": routing_summary,
            "routing_detail_summaries": routing_details,
            "live_exec_summary": live_exec_summary,
            "num_benchmark_records": len(benchmark_scores),
            "num_live_exec_records": len(live_exec_records),
        }
        model_root.mkdir(parents=True, exist_ok=True)
        (model_root / "cluster_shard_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        manifests.append(manifest)
    return {"dry_run": False, "manifests": manifests}


def merge_cluster_shards(
    config_path: str | Path,
    *,
    output_root: str | Path | None = None,
    output_tables: str | Path | None = None,
    strict: bool = True,
) -> Dict[str, Any]:
    config = load_json_config(config_path)
    root = Path(output_root or config.get("output_root") or "outputs/emnlp_acceptance")
    merged_root = root / "merged"
    merged_root.mkdir(parents=True, exist_ok=True)
    model_roots = sorted((root / "predictors").glob("*"))
    all_prediction_records: List[Dict[str, Any]] = []
    all_routing_records: List[Dict[str, Any]] = []
    all_live_exec_records: List[Dict[str, Any]] = []
    model_rows: List[Dict[str, Any]] = []
    routing_model_rows: List[Dict[str, Any]] = []
    live_model_rows: List[Dict[str, Any]] = []
    duplicates: List[str] = []

    for model_root in model_roots:
        if not model_root.is_dir():
            continue
        model_merged = model_root / "merged"
        model_merged.mkdir(parents=True, exist_ok=True)
        prediction_records = _load_shard_jsonl(model_root, "prediction_records.jsonl")
        routing_records = _load_shard_jsonl(model_root, "routing_records.jsonl")
        live_exec_records = _load_shard_jsonl(model_root, "live_exec_results.jsonl")
        duplicates.extend(_duplicate_keys(prediction_records, record_type="prediction"))
        duplicates.extend(_duplicate_keys(routing_records, record_type="routing"))
        duplicates.extend(_duplicate_live_keys(live_exec_records))
        _write_jsonl(model_merged / "prediction_records.jsonl", prediction_records)
        _write_jsonl(model_merged / "routing_records.jsonl", routing_records)
        _write_jsonl(model_merged / "live_exec_results.jsonl", live_exec_records)
        model_tables = build_metric_tables(model_merged)
        _write_tables(model_merged / "tables", model_tables)
        model_name = _model_name_for_records(prediction_records, fallback=model_root.name)
        for row in model_tables["main_results"]:
            model_rows.append({"model_slug": model_root.name, "model_name": model_name, **row})
        for row in model_tables["routing_results"]:
            routing_model_rows.append({"model_slug": model_root.name, "model_name": model_name, **row})
        for row in _summarize_live_exec_records(live_exec_records):
            live_model_rows.append({"model_slug": model_root.name, "model_name": model_name, **row})
        all_prediction_records.extend(prediction_records)
        all_routing_records.extend(routing_records)
        all_live_exec_records.extend(live_exec_records)

    if duplicates and strict:
        preview = "; ".join(duplicates[:10])
        raise ValueError(f"Duplicate shard records found: {preview}")
    _write_jsonl(merged_root / "prediction_records.jsonl", all_prediction_records)
    _write_jsonl(merged_root / "routing_records.jsonl", all_routing_records)
    _write_jsonl(merged_root / "live_exec_results.jsonl", all_live_exec_records)
    tables_dir = Path(output_tables) if output_tables else root / "tables"
    paths = write_metric_tables(merged_root, tables_dir)
    model_fields = ["model_slug", "model_name"]
    if model_rows:
        model_fields.extend([field for field in model_rows[0] if field not in set(model_fields)])
    _write_csv(tables_dir / "main_results_by_model.csv", model_rows, model_fields)
    routing_model_fields = ["model_slug", "model_name"]
    if routing_model_rows:
        routing_model_fields.extend([field for field in routing_model_rows[0] if field not in set(routing_model_fields)])
    _write_csv(tables_dir / "routing_results_by_model.csv", routing_model_rows, routing_model_fields)
    live_fields = _fields_for_rows(all_live_exec_records, preferred=["model_slug", "model_name", "baseline_name", "live_task_id", "tool_id"])
    _write_csv(tables_dir / "live_exec_results.csv", all_live_exec_records, live_fields or ["live_task_id"])
    live_model_fields = ["model_slug", "model_name"]
    if live_model_rows:
        live_model_fields.extend([field for field in live_model_rows[0] if field not in set(live_model_fields)])
    _write_csv(tables_dir / "live_exec_results_by_model.csv", live_model_rows, live_model_fields)
    paths.update(
        {
            "main_results_by_model": tables_dir / "main_results_by_model.csv",
            "routing_results_by_model": tables_dir / "routing_results_by_model.csv",
            "live_exec_results": tables_dir / "live_exec_results.csv",
            "live_exec_results_by_model": tables_dir / "live_exec_results_by_model.csv",
        }
    )
    manifest = {
        "config_path": str(config_path),
        "output_root": str(root),
        "merged_root": str(merged_root),
        "tables_dir": str(tables_dir),
        "num_models": len(model_roots),
        "prediction_records": len(all_prediction_records),
        "routing_records": len(all_routing_records),
        "live_exec_records": len(all_live_exec_records),
        "duplicates": duplicates,
        "table_paths": {name: str(path) for name, path in paths.items()},
    }
    (merged_root / "cluster_merge_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def _configured_max_tools(config: Dict[str, Any]) -> int | None:
    data_config = config.get("data") if isinstance(config.get("data"), dict) else {}
    for value in (data_config.get("max_tools"), config.get("max_tools")):
        if value not in {None, ""}:
            parsed = int(value)
            if parsed > 0:
                return parsed
    return None


def _strict_backends(config: Dict[str, Any]) -> bool:
    runtime = config.get("runtime") if isinstance(config.get("runtime"), dict) else {}
    return bool(runtime.get("strict_backends", False))


def _live_execution_enabled(config: Dict[str, Any]) -> bool:
    live = config.get("live_execution") if isinstance(config.get("live_execution"), dict) else {}
    return bool(live.get("enabled", False))


def _configured_live_tools(config: Dict[str, Any]) -> Dict[str, Any]:
    if not _live_execution_enabled(config):
        return {}
    live = config.get("live_execution") if isinstance(config.get("live_execution"), dict) else {}
    allowed_domains = {_normalize_live_domain(item) for item in (live.get("domains") or [])}
    tools = build_live_exec_tools()
    if not allowed_domains:
        return tools
    return {
        name: tool
        for name, tool in tools.items()
        if _normalize_live_domain((tool.provenance or {}).get("domain") or (tool.schema_complexity or {}).get("domain")) in allowed_domains
    }


def _selected_live_tasks(
    config: Dict[str, Any],
    *,
    shard_index: int | None = None,
    num_shards: int | None = None,
) -> List[Dict[str, Any]]:
    if not _live_execution_enabled(config):
        return []
    live = config.get("live_execution") if isinstance(config.get("live_execution"), dict) else {}
    allowed_domains = {_normalize_live_domain(item) for item in (live.get("domains") or [])}
    tasks = [
        task for task in build_live_exec_tasks()
        if not allowed_domains or _normalize_live_domain(task.get("domain")) in allowed_domains
    ]
    subset_size = _optional_positive_int(live.get("subset_size"))
    tasks = sorted(tasks, key=lambda item: str(item.get("live_task_id") or ""))
    tasks = tasks[:subset_size] if subset_size is not None else tasks
    if shard_index is None and num_shards is None:
        return tasks
    if shard_index is None or num_shards is None:
        raise ValueError("shard_index and num_shards must be provided together for live execution sharding.")
    if num_shards <= 0:
        raise ValueError("num_shards must be positive.")
    if shard_index < 0 or shard_index >= num_shards:
        raise ValueError("shard_index must be in [0, num_shards).")
    return [task for index, task in enumerate(tasks) if index % num_shards == shard_index]


def _run_live_exec_for_model(
    config: Dict[str, Any],
    *,
    model_root: Path,
    package_root: Path,
    generator: SkillGenerator,
    predictor: Any,
    allowed_conditions: Sequence[str],
    model_name: str,
    model_slug: str,
    shard_index: int,
    num_shards: int,
    allow_predictor_fallback: bool,
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    live_tools = _configured_live_tools(config)
    live_tasks = _selected_live_tasks(config, shard_index=shard_index, num_shards=num_shards)
    if not live_tools or not live_tasks:
        return [], {"num_tasks": 0, "num_records": 0}

    skill_variants_by_tool = {
        tool_name: build_skill_variant_map(
            tool,
            live_tools,
            generator,
            allowed_conditions=list(allowed_conditions),
            package_manager_dir=package_root,
            allow_package_generation=False,
        )
        for tool_name, tool in live_tools.items()
    }
    results: List[Dict[str, Any]] = []
    predictions: List[Dict[str, Any]] = []
    live_dir = model_root / "live_exec"
    for task in live_tasks:
        tool_id = str(task.get("tool_id") or "")
        tool = live_tools.get(tool_id)
        if tool is None:
            continue
        expected_call = task.get("expected_tool_call") if isinstance(task.get("expected_tool_call"), dict) else {}
        expected_args = expected_call.get("arguments") if isinstance(expected_call.get("arguments"), dict) else {}
        eval_task = EvalTask(
            task_id=str(task["live_task_id"]),
            tool_name=tool_id,
            user_request=str(task.get("user_request") or ""),
            expected_arguments=dict(expected_args),
            expected_argument_candidates=[dict(expected_args)],
            should_trigger=True,
            split="live_exec",
            tags=["live_exec", str(task.get("domain") or "")],
            domain=str(task.get("domain") or ""),
            difficulty=str(task.get("difficulty") or ""),
        )
        for condition, skill in skill_variants_by_tool[tool_id].items():
            task_dir = live_dir / tool_slug(str(task["live_task_id"]))
            result_path = task_dir / f"{tool_slug(condition)}.live_result.json"
            prediction_path = task_dir / f"{tool_slug(condition)}.live_prediction.json"
            if result_path.exists():
                try:
                    result = json.loads(result_path.read_text(encoding="utf-8"))
                    results.append(result)
                    if prediction_path.exists():
                        predictions.append(json.loads(prediction_path.read_text(encoding="utf-8")))
                    continue
                except (OSError, json.JSONDecodeError):
                    pass
            prediction = safe_predict(tool, skill, eval_task, predictor, allow_fallback=allow_predictor_fallback)
            predicted_call = {
                "tool_name": tool_id if prediction.should_call else "__abstain__",
                "arguments": dict(prediction.predicted_arguments),
            }
            prediction_row = {
                "live_task_id": task["live_task_id"],
                "task_id": task["live_task_id"],
                "domain": task.get("domain"),
                "tool_id": tool_id,
                "baseline_name": condition,
                "model_name": model_name,
                "model_slug": model_slug,
                "shard_index": shard_index,
                "num_shards": num_shards,
                "should_call": prediction.should_call,
                "abstention_reason": prediction.abstention_reason,
                "predicted_tool_call": predicted_call,
                "predictor_configured_backend": prediction.metadata.get("configured_predictor_backend", predictor.backend_name),
                "predictor_backend": prediction.metadata.get("actual_predictor_backend", predictor.backend_name),
                "predictor_fallback_used": bool(prediction.metadata.get("predictor_fallback_used", False)),
                "predictor_fallback_reason": prediction.metadata.get("predictor_fallback_reason"),
            }
            predictions.append(prediction_row)
            result = evaluate_live_exec_tasks([task], {str(task["live_task_id"]): predicted_call}, use_gold=False)[0]
            result.update(
                {
                    "task_id": task["live_task_id"],
                    "baseline_name": condition,
                    "model_name": model_name,
                    "model_slug": model_slug,
                    "shard_index": shard_index,
                    "num_shards": num_shards,
                    "should_call": prediction.should_call,
                    "abstention_reason": prediction.abstention_reason,
                    "predictor_configured_backend": prediction_row["predictor_configured_backend"],
                    "predictor_backend": prediction_row["predictor_backend"],
                    "predictor_fallback_used": prediction_row["predictor_fallback_used"],
                    "predictor_fallback_reason": prediction_row["predictor_fallback_reason"],
                }
            )
            results.append(result)
            task_dir.mkdir(parents=True, exist_ok=True)
            prediction_path.write_text(json.dumps(prediction_row, indent=2, ensure_ascii=False), encoding="utf-8")
            result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    _write_jsonl(live_dir / "live_exec_predictions.jsonl", predictions)
    _write_jsonl(live_dir / "live_exec_results.jsonl", results)
    _write_csv(live_dir / "live_exec_results.csv", results, _fields_for_rows(results, preferred=["baseline_name", "live_task_id", "tool_id"]))
    return results, {
        "num_tasks": len(live_tasks),
        "num_records": len(results),
        "by_condition": _summarize_live_exec_records(results),
    }


def _normalize_live_domain(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"database/sql", "database", "sql", "sqlite"}:
        return "sqlite"
    if text in {"git/version-control", "version-control", "version_control", "git"}:
        return "git"
    return text


def _balanced_tasks_for_tools(config: Dict[str, Any], tasks: Sequence[Any], tool_names: Sequence[str]) -> List[Any]:
    tool_set = set(tool_names)
    controls = config.get("controls") if isinstance(config.get("controls"), dict) else {}
    pos_limit = _optional_positive_int(controls.get("positives_per_tool_total") or config.get("positives_per_tool"))
    neg_limit = _optional_positive_int(controls.get("negatives_per_tool_total") or config.get("negatives_per_tool"))
    filtered = [task for task in tasks if task.tool_name in tool_set]
    if pos_limit is None and neg_limit is None:
        return filtered
    grouped: Dict[str, Dict[str, List[Any]]] = {}
    for task in sorted(filtered, key=lambda item: str(item.task_id)):
        bucket = "positive" if getattr(task, "should_trigger", True) else "negative"
        grouped.setdefault(task.tool_name, {"positive": [], "negative": []})[bucket].append(task)
    selected: List[Any] = []
    for tool_name in sorted(tool_set):
        buckets = grouped.get(tool_name, {"positive": [], "negative": []})
        positives = buckets["positive"][:pos_limit] if pos_limit is not None else buckets["positive"]
        negatives = buckets["negative"][:neg_limit] if neg_limit is not None else buckets["negative"]
        selected.extend(positives)
        selected.extend(negatives)
    return sorted(selected, key=lambda item: str(item.task_id))


def _optional_positive_int(value: Any) -> int | None:
    if value in {None, ""}:
        return None
    parsed = int(value)
    return parsed if parsed > 0 else None


def _load_config_models(config: Dict[str, Any], *, base_dir: Path) -> List[Any]:
    raw_models = config.get("models") or []
    if not raw_models:
        return [load_model_config(config.get("predictor") or config.get("generator") or {"type": "heuristic", "model_name": "heuristic"})]
    models = []
    for raw in raw_models:
        if isinstance(raw, str):
            path = _resolve_config_path(raw, base_dir)
            models.append(load_model_config(path))
        elif isinstance(raw, dict) and raw.get("config"):
            path = _resolve_config_path(str(raw["config"]), base_dir)
            model = load_model_config(path)
            overrides = dict(raw)
            overrides.pop("config", None)
            if overrides:
                model_data = model.model_dump()
                model_data.update(overrides)
                models.append(load_model_config(model_data))
            else:
                models.append(model)
        elif isinstance(raw, dict):
            models.append(load_model_config(raw))
        else:
            raise ValueError(f"Unsupported model entry: {raw!r}")
    return models


def _resolve_config_path(value: str, base_dir: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    for candidate in (base_dir / path, Path.cwd() / path):
        if candidate.exists():
            return candidate
    return Path.cwd() / path


def _model_to_backend_config(model: Any) -> Dict[str, Any]:
    return {
        "type": model.backend,
        "model_name_or_path": model.model_path,
        "device_map": model.device_map,
        "torch_dtype": model.torch_dtype,
        "max_new_tokens": model.max_new_tokens,
        "load_in_4bit": model.load_in_4bit,
        "load_in_8bit": False,
        "generation_kwargs": {"temperature": model.temperature},
    }


def _load_shard_jsonl(model_root: Path, filename: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for shard_root in sorted(path for path in model_root.glob("shard_*") if path.is_dir()):
        shard_rows: List[Dict[str, Any]] = []
        shard_keys: set[tuple[str, str, str, str]] = set()
        for path in sorted(shard_root.glob(f"**/{filename}")):
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    _annotate_recovered_record(row, model_root=model_root)
                    shard_rows.append(row)
                    shard_keys.add(_merge_record_key(row, filename))

        for path in _fallback_record_paths(shard_root, filename):
            try:
                row = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            _annotate_recovered_record(row, model_root=model_root)
            key = _merge_record_key(row, filename)
            if key in shard_keys:
                continue
            shard_rows.append(row)
            shard_keys.add(key)
        rows.extend(shard_rows)
    return rows


def _fallback_record_paths(shard_root: Path, filename: str) -> List[Path]:
    if filename == "prediction_records.jsonl":
        return sorted(shard_root.glob("benchmark/**/*.result.json"))
    if filename == "routing_records.jsonl":
        return sorted(shard_root.glob("routing_benchmark/**/*.routing.json"))
    if filename == "live_exec_results.jsonl":
        return sorted(shard_root.glob("live_exec/**/*.live_result.json"))
    return []


def _annotate_recovered_record(record: Dict[str, Any], *, model_root: Path) -> None:
    record.setdefault("model_slug", model_root.name)
    record.setdefault("model_name", record.get("model_slug") or model_root.name)


def _merge_record_key(record: Dict[str, Any], filename: str) -> tuple[str, str, str, str]:
    if filename == "live_exec_results.jsonl":
        record_type = "live_exec"
        task_id = str(record.get("live_task_id") or record.get("task_id") or "")
    elif filename == "routing_records.jsonl":
        record_type = "routing"
        task_id = str(record.get("task_id") or "")
    else:
        record_type = "prediction"
        task_id = str(record.get("task_id") or "")
    return (
        str(record.get("model_slug") or record.get("model_name") or ""),
        task_id,
        str(record.get("baseline_name") or ""),
        record_type,
    )


def _duplicate_keys(records: Sequence[Dict[str, Any]], *, record_type: str) -> List[str]:
    seen: set[tuple[str, str, str, str]] = set()
    duplicates = []
    for record in records:
        key = (
            str(record.get("model_slug") or record.get("model_name") or ""),
            str(record.get("task_id") or ""),
            str(record.get("baseline_name") or ""),
            record_type,
        )
        if key in seen:
            duplicates.append("/".join(key))
        seen.add(key)
    return duplicates


def _duplicate_live_keys(records: Sequence[Dict[str, Any]]) -> List[str]:
    seen: set[tuple[str, str, str]] = set()
    duplicates = []
    for record in records:
        key = (
            str(record.get("model_slug") or record.get("model_name") or ""),
            str(record.get("live_task_id") or record.get("task_id") or ""),
            str(record.get("baseline_name") or ""),
        )
        if key in seen:
            duplicates.append("/".join(key))
        seen.add(key)
    return duplicates


def _model_name_for_records(records: Sequence[Dict[str, Any]], *, fallback: str) -> str:
    for record in records:
        if record.get("model_name"):
            return str(record["model_name"])
    return fallback


def _write_tables(output_dir: Path, tables: Dict[str, List[Dict[str, Any]]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "main_results.csv", tables["main_results"], list(tables["main_results"][0]) if tables["main_results"] else ["baseline_name"])
    _write_csv(output_dir / "routing_results.csv", tables["routing_results"], list(tables["routing_results"][0]) if tables["routing_results"] else ["baseline_name"])
    _write_csv(output_dir / "harm_utility.csv", tables["harm_utility"], list(tables["harm_utility"][0]) if tables["harm_utility"] else ["baseline_name"])
    _write_csv(output_dir / "stat_tests.csv", tables["stat_tests"], list(tables["stat_tests"][0]) if tables["stat_tests"] else ["test"])
    _write_csv(output_dir / "routing_stat_tests.csv", tables["routing_stat_tests"], list(tables["routing_stat_tests"][0]) if tables["routing_stat_tests"] else ["test"])


def _write_csv(path: Path, rows: Sequence[Dict[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _fields_for_rows(rows: Sequence[Dict[str, Any]], preferred: Sequence[str] | None = None) -> List[str]:
    preferred = list(preferred or [])
    fields: List[str] = []
    for field in preferred:
        if field not in fields:
            fields.append(field)
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    return fields


def _summarize_live_exec_records(records: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault(str(record.get("baseline_name") or ""), []).append(record)
    rows = []
    for condition, items in sorted(grouped.items()):
        total = len(items)
        rows.append(
            {
                "baseline_name": condition,
                "num_examples": total,
                "predicted_call_valid": _rate(items, "predicted_call_valid"),
                "execution_success": _rate(items, "execution_success"),
                "observation_match": _rate(items, "observation_match"),
                "state_match": _rate(items, "state_match"),
                "unsafe_action_blocked": _rate(items, "unsafe_action_blocked"),
                "live_joint_success": _rate(items, "live_joint_success"),
            }
        )
    return rows


def _rate(rows: Sequence[Dict[str, Any]], key: str) -> float:
    return round(sum(1 for row in rows if _truthy(row.get(key))) / len(rows), 4) if rows else 0.0


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.lower() in {"true", "1", "yes"}
    return bool(value)


def _write_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def parse_model_filter(value: str | None) -> List[str] | None:
    if not value or value == "all":
        return None
    return [item.strip() for item in value.split(",") if item.strip()]

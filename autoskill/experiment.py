from __future__ import annotations
from tqdm import tqdm

import json
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from autoskill.benchmark import load_benchmark_tasks
from autoskill.analysis import summarize_error_taxonomy, summarize_method_wins
from autoskill.config import load_json_config, merge_experiment_config
from autoskill.conditions import (
    AUTOSKILL_BASE,
    GENERATED_SKILL_BASE,
    RELIASKILL_CHALLENGER,
    build_reviewer_baseline_skills,
    condition_prompt_text,
    normalize_condition_name,
    normalize_condition_names,
)
from autoskill.conversion import load_json_or_jsonl
from autoskill.evaluation import summarize_records, summarize_records_by_tool, write_summary
from autoskill.generator import SkillGenerator
from autoskill.logging_utils import (
    build_run_manifest,
    generation_audit_record,
    prediction_audit_record,
    write_jsonl as write_audit_jsonl,
    write_manifest as write_audit_manifest,
)
from autoskill.method_metadata import (
    attach_loaded_package_metadata,
    prediction_method_metadata,
    require_challenger_package,
)
from autoskill.packaging import write_skill_package
from autoskill.parser import parse_mcp_tool
from autoskill.predictor import PredictorBackend, build_predictor_from_config, build_predictor_from_env, safe_predict
from autoskill.progress import write_progress_state
from autoskill.raw_mcp import build_raw_mcp_skill
from autoskill.retrieval_baselines import (
    build_retrieved_candidates_skill,
    build_retrieved_docs_skill,
    build_retrieved_memory_skill,
)
from autoskill.reporting import (
    build_benchmark_by_split_csv,
    build_benchmark_by_tool_csv,
    build_error_taxonomy_csv,
    build_method_wins_csv,
    build_package_by_tool_csv,
    build_pairwise_comparison_csv,
    build_routing_by_split_csv,
    build_routing_by_tool_csv,
    build_routing_results_csv,
    build_results_csv,
    build_results_markdown,
    collect_failure_highlights,
    write_report,
)
from autoskill.retrieval_runtime import contextualize_skill_for_task
from autoskill.routing_eval import (
    run_routing_pipeline,
    summarize_routing_scores,
    summarize_routing_scores_by_split,
    summarize_routing_scores_by_tool,
)
from autoskill.schema_only import build_schema_only_skill
from autoskill.task_eval import (
    score_prediction,
    summarize_pairwise_comparisons,
    summarize_task_scores,
    summarize_task_scores_by_split,
    summarize_task_scores_by_tool,
)
from autoskill.validator import validate_skill


def _extract_generation_backend_metadata(skill: Any) -> Dict[str, Any]:
    backend_entries = [
        entry
        for entry in getattr(skill, "method_trace", [])
        if isinstance(entry, dict) and entry.get("trace_type") == "generation_backend"
    ]
    if not backend_entries:
        return {
            "configured_generation_backend": None,
            "actual_generation_backend": None,
            "generation_fallback_used": False,
            "generation_fallback_reason": None,
        }
    latest = backend_entries[-1]
    return {
        "configured_generation_backend": latest.get("configured_generation_backend"),
        "actual_generation_backend": latest.get("actual_generation_backend"),
        "generation_fallback_used": bool(latest.get("generation_fallback_used", False)),
        "generation_fallback_reason": latest.get("generation_fallback_reason"),
    }


def _summarize_backend_usage(records: List[Dict[str, Any]], configured_key: str, actual_key: str, fallback_key: str) -> Dict[str, Any]:
    configured_counts: Dict[str, int] = {}
    actual_counts: Dict[str, int] = {}
    fallback_count = 0
    for record in records:
        configured_value = record.get(configured_key)
        actual_value = record.get(actual_key)
        if configured_value:
            configured_counts[str(configured_value)] = configured_counts.get(str(configured_value), 0) + 1
        if actual_value:
            actual_counts[str(actual_value)] = actual_counts.get(str(actual_value), 0) + 1
        if record.get(fallback_key):
            fallback_count += 1
    return {
        "num_records": len(records),
        "configured_backend_counts": configured_counts,
        "actual_backend_counts": actual_counts,
        "fallback_count": fallback_count,
        "fallback_rate": round(fallback_count / len(records), 4) if records else 0.0,
    }


def load_tools(raw_path: str | Path) -> Dict[str, Any]:
    raw_path = Path(raw_path)
    raw_tools = load_json_or_jsonl(raw_path)
    return {
        tool.tool_name: tool
        for idx, raw_tool in enumerate(raw_tools)
        for tool in [parse_mcp_tool(raw_tool, source_pointer=f"{raw_path}#{idx}")]
    }


def _load_packaged_skill(package_dir: Path) -> Any | None:
    from autoskill.ir import GeneratedSkill

    skill_json = package_dir / "skill.json"
    if skill_json.exists():
        with skill_json.open("r", encoding="utf-8") as f:
            return GeneratedSkill(**json.load(f))

    metadata_path = package_dir / "metadata.json"
    skill_md_path = package_dir / "SKILL.md"
    if not metadata_path.exists() or not skill_md_path.exists():
        return None
    with metadata_path.open("r", encoding="utf-8") as f:
        meta = json.load(f)
    content = skill_md_path.read_text(encoding="utf-8")
    summary = ""
    if "## Summary\n" in content:
        summary = content.split("## Summary\n", 1)[1].split("## When to use", 1)[0].strip()
    return GeneratedSkill(
        baseline_name=meta.get("baseline_name", package_dir.name),
        skill_summary=summary,
        when_to_use=[],
        when_not_to_use=[],
        argument_template={},
        semantic_hints=meta.get("semantic_hints", {}),
        examples=[],
        method_trace=meta.get("method_trace", []),
        metadata=meta.get("skill_metadata", {}),
    )


def _packaged_condition_path(package_root: Path, tool_name: str, condition: str) -> Path:
    return package_root / _safe_dir_name(tool_name) / _safe_dir_name(condition)


def _find_packaged_skill(package_root: Path, tool: Any, condition: str) -> Any | None:
    candidates = [_packaged_condition_path(package_root, tool.tool_name, condition)]
    if condition == GENERATED_SKILL_BASE:
        candidates.extend(
            [
                _packaged_condition_path(package_root, tool.tool_name, AUTOSKILL_BASE),
                package_root.parent / "benchmark" / _safe_dir_name(tool.tool_name) / GENERATED_SKILL_BASE,
                package_root.parent / "benchmark" / _safe_dir_name(tool.tool_name) / AUTOSKILL_BASE,
            ]
        )
    for candidate in candidates:
        if candidate.exists():
            if condition == RELIASKILL_CHALLENGER:
                require_challenger_package(candidate)
            skill = _load_packaged_skill(candidate)
            if skill is not None:
                skill.baseline_name = normalize_condition_name(skill.baseline_name)
                if condition == RELIASKILL_CHALLENGER:
                    skill.baseline_name = RELIASKILL_CHALLENGER
                skill = attach_loaded_package_metadata(skill, candidate, condition=condition)
                return skill
    return None


def build_skill_variants(
    tool: Any,
    tools: Dict[str, Any],
    generator: SkillGenerator,
    package_manager_dir: Path | None = None,
    *,
    allow_package_generation: bool = True,
) -> List[Any]:
    llm_skill = None
    if package_manager_dir:
        llm_skill = _find_packaged_skill(package_manager_dir, tool, GENERATED_SKILL_BASE)
    
    if llm_skill is None:
        if not allow_package_generation:
            raise FileNotFoundError(
                f"Missing shared `{GENERATED_SKILL_BASE}` package for tool `{tool.tool_name}` in {package_manager_dir}."
            )
        llm_skill = generator.generate(tool)
        if package_manager_dir:
            # SAVE FOR FUTURE
            save_path = package_manager_dir / _safe_dir_name(tool.tool_name) / GENERATED_SKILL_BASE / "skill.json"
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with save_path.open("w", encoding="utf-8") as f:
                json.dump(llm_skill.model_dump(), f, indent=2, ensure_ascii=False)
    
    if llm_skill is None:
        llm_skill = generator.generate(tool)
    llm_skill.baseline_name = normalize_condition_name(llm_skill.baseline_name)

    historical = [
        build_raw_mcp_skill(tool),
        build_schema_only_skill(tool),
        build_retrieved_docs_skill(tool),
        build_retrieved_candidates_skill(tool, tools=tools),
        build_retrieved_memory_skill(tool, tools=tools),
        llm_skill,
    ]
    return [
        *historical,
        *build_reviewer_baseline_skills(tool, tools, llm_skill),
    ]


def build_skill_variant_map(
    tool: Any,
    tools: Dict[str, Any],
    generator: SkillGenerator,
    allowed_conditions: List[str] | None = None,
    package_manager_dir: Path | None = None,
    *,
    allow_package_generation: bool = True,
) -> Dict[str, Any]:
    normalized_allowed = normalize_condition_names(allowed_conditions)
    variants = {
        skill.baseline_name: skill
        for skill in build_skill_variants(
            tool,
            tools,
            generator,
            package_manager_dir=package_manager_dir,
            allow_package_generation=allow_package_generation,
        )
    }
    if package_manager_dir and normalized_allowed:
        for condition in normalized_allowed:
            packaged = _find_packaged_skill(package_manager_dir, tool, condition)
            if packaged is not None:
                packaged.baseline_name = condition
                variants[condition] = packaged
    if allowed_conditions is not None:
        variants = {k: v for k, v in variants.items() if k in set(normalized_allowed or [])}
        missing = sorted(set(normalized_allowed or []) - set(variants))
        package_only_missing = [condition for condition in missing if condition == RELIASKILL_CHALLENGER]
        if package_only_missing:
            raise FileNotFoundError(
                f"Missing artifact-backed `{RELIASKILL_CHALLENGER}` package for tool `{tool.tool_name}` in {package_manager_dir}."
            )
        if not allow_package_generation and missing:
            raise FileNotFoundError(
                f"Missing read-only shared packages for tool `{tool.tool_name}`: {', '.join(missing)}"
            )
    return variants


def _write_jsonl(path: Path, records: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _safe_filename(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in value)[:160]


def _safe_dir_name(value: str) -> str:
    """Truncate a tool or condition name for use as a directory component on Windows."""
    return "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in value)[:50]


def _write_condition_prompt(output_dir: Path, tool: Any, skill: Any) -> None:
    prompt_name = f"{_safe_dir_name(tool.tool_name)}__{_safe_dir_name(skill.baseline_name)}.txt"
    local_prompt_dir = output_dir.parent / "prompts"
    local_prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_text = condition_prompt_text(tool, skill)
    (local_prompt_dir / prompt_name).write_text(prompt_text, encoding="utf-8")
    global_prompt_dir = Path("outputs/prompts")
    global_prompt_dir.mkdir(parents=True, exist_ok=True)
    (global_prompt_dir / prompt_name).write_text(prompt_text, encoding="utf-8")


def run_packaging_pipeline(
    tools: Dict[str, Any],
    output_dir: str | Path,
    generator: SkillGenerator | None = None,
    allowed_conditions: List[str] | None = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Dict[str, Any]]]:
    out_dir = Path(output_dir)
    generator = generator or SkillGenerator()
    records: List[Dict[str, Any]] = []

    for tool in tqdm(tools.values(), desc="[ReliaSkill] Packaging tools"):
        variants = build_skill_variant_map(tool, tools, generator, allowed_conditions=allowed_conditions, package_manager_dir=out_dir)
        for skill in variants.values():
            report = validate_skill(tool, skill)
            _write_condition_prompt(out_dir, tool, skill)
            write_skill_package(out_dir / _safe_dir_name(tool.tool_name) / _safe_dir_name(skill.baseline_name), tool, skill, report)
            records.append(
                {
                    "tool_name": tool.tool_name,
                    "baseline_name": skill.baseline_name,
                    "skill": skill,
                    "report": report,
                    **_extract_generation_backend_metadata(skill),
                }
            )

    summary = summarize_records(records)
    summary_by_tool = summarize_records_by_tool(records)
    write_summary(out_dir / "comparison_summary.json", summary)
    write_summary(out_dir / "comparison_summary_by_tool.json", summary_by_tool)
    _write_jsonl(
        out_dir / "generation_records.jsonl",
        [
            {
                "tool_name": record["tool_name"],
                "baseline_name": record["baseline_name"],
                "valid": record["report"].valid,
                "issues": [issue.model_dump() for issue in record["report"].issues],
                "configured_generation_backend": record["configured_generation_backend"],
                "actual_generation_backend": record["actual_generation_backend"],
                "generation_fallback_used": record["generation_fallback_used"],
                "generation_fallback_reason": record["generation_fallback_reason"],
                "skill": record["skill"].model_dump(),
            }
            for record in records
        ],
    )
    return records, summary, summary_by_tool


def run_benchmark_pipeline(
    tools: Dict[str, Any],
    tasks_path: str | Path,
    output_dir: str | Path,
    generator: SkillGenerator | None = None,
    predictor: PredictorBackend | None = None,
    allowed_conditions: List[str] | None = None,
    tasks: List[Any] | None = None,
    package_manager_dir: str | Path | None = None,
    allow_package_generation: bool = True,
    allow_predictor_fallback: bool = True,
    model_name: str | None = None,
    model_slug: str | None = None,
    shard_index: int | None = None,
    num_shards: int | None = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
    out_dir = Path(output_dir)
    generator = generator or SkillGenerator()
    predictor = predictor or build_predictor_from_env()
    tasks = tasks if tasks is not None else load_benchmark_tasks(tasks_path)
    package_root = Path(package_manager_dir) if package_manager_dir is not None else out_dir.parent / "packages"
    all_scores: List[Dict[str, Any]] = []

    for task in tqdm(tasks, desc="[ReliaSkill] Running benchmark"):
        if task.tool_name not in tools:
            continue
        tool = tools[task.tool_name]
        variants = build_skill_variant_map(
            tool,
            tools,
            generator,
            allowed_conditions=allowed_conditions,
            package_manager_dir=package_root,
            allow_package_generation=allow_package_generation,
        )
        for skill in variants.values():
            report = validate_skill(tool, skill)
            target_dir = out_dir / _safe_dir_name(task.tool_name) / _safe_dir_name(skill.baseline_name)
            target_dir.mkdir(parents=True, exist_ok=True)
            
            result_path = target_dir / f"{_safe_dir_name(task.task_id)}.result.json"
            if result_path.exists():
                try:
                    with result_path.open("r", encoding="utf-8") as f:
                        score = json.load(f)
                        _annotate_run_record(score, model_name=model_name, model_slug=model_slug, shard_index=shard_index, num_shards=num_shards)
                        all_scores.append(score)
                        continue
                except:
                    pass

            write_skill_package(target_dir, tool, skill, report)
            _write_condition_prompt(out_dir.parent / "packages", tool, skill)
            runtime_skill, retrieval_context = contextualize_skill_for_task(task, tool, skill, tools)
            write_progress_state(
                out_dir,
                phase="benchmark",
                status="running",
                task_id=str(task.task_id),
                tool_name=str(task.tool_name),
                condition=str(skill.baseline_name),
                model_name=model_name,
                model_slug=model_slug,
                shard_index=shard_index,
                num_shards=num_shards,
            )
            prediction = safe_predict(tool, runtime_skill, task, predictor, allow_fallback=allow_predictor_fallback)
            score = score_prediction(task, tool, prediction)
            score["predictor_configured_backend"] = prediction.metadata.get("configured_predictor_backend", predictor.backend_name)
            score["predictor_backend"] = prediction.metadata.get("actual_predictor_backend", predictor.backend_name)
            score["predictor_fallback_used"] = bool(prediction.metadata.get("predictor_fallback_used", False))
            score["predictor_fallback_reason"] = prediction.metadata.get("predictor_fallback_reason")
            score["method_metadata"] = prediction_method_metadata(skill)
            score["user_request"] = task.user_request
            score["retrieval_context"] = retrieval_context
            _annotate_run_record(score, model_name=model_name, model_slug=model_slug, shard_index=shard_index, num_shards=num_shards)
            all_scores.append(score)

            with result_path.open("w", encoding="utf-8") as f:
                json.dump(score, f, indent=2, ensure_ascii=False)

            exposure_path = target_dir / f"{_safe_dir_name(task.task_id)}.prompt.txt"
            exposure_path.write_text(prediction.exposure_text, encoding="utf-8")

    write_progress_state(
        out_dir,
        phase="benchmark",
        status="done",
        model_name=model_name,
        model_slug=model_slug,
        shard_index=shard_index,
        num_shards=num_shards,
    )
    summary = summarize_task_scores(all_scores)
    summary_by_tool = summarize_task_scores_by_tool(all_scores)
    summary_by_split = summarize_task_scores_by_split(all_scores)
    pairwise_comparisons = summarize_pairwise_comparisons(all_scores)
    error_taxonomy = summarize_error_taxonomy(all_scores)
    method_win_analysis = summarize_method_wins(all_scores)
    write_summary(out_dir / "benchmark_summary.json", summary)
    write_summary(out_dir / "benchmark_summary_by_tool.json", summary_by_tool)
    write_summary(out_dir / "benchmark_summary_by_split.json", summary_by_split)
    write_summary(out_dir / "pairwise_comparisons.json", pairwise_comparisons)
    write_summary(out_dir / "error_taxonomy.json", error_taxonomy)
    write_summary(out_dir / "method_win_analysis.json", method_win_analysis)
    with (out_dir / "benchmark_details.json").open("w", encoding="utf-8") as f:
        json.dump(all_scores, f, indent=2, ensure_ascii=False)
    _write_jsonl(out_dir / "prediction_records.jsonl", all_scores)
    return all_scores, summary, {
        "by_tool": summary_by_tool,
        "by_split": summary_by_split,
        "pairwise": pairwise_comparisons,
        "error_taxonomy": error_taxonomy,
        "method_wins": method_win_analysis,
    }


def run_routing_benchmark_pipeline(
    tools: Dict[str, Any],
    tasks_path: str | Path,
    output_dir: str | Path,
    generator: SkillGenerator | None = None,
    predictor: PredictorBackend | None = None,
    allowed_conditions: List[str] | None = None,
    tasks: List[Any] | None = None,
    package_manager_dir: str | Path | None = None,
    allow_package_generation: bool = True,
    allow_predictor_fallback: bool = True,
    benchmark_dir: str | Path | None = None,
    model_name: str | None = None,
    model_slug: str | None = None,
    shard_index: int | None = None,
    num_shards: int | None = None,
) -> tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
    out_dir = Path(output_dir)
    generator = generator or SkillGenerator()
    predictor = predictor or build_predictor_from_env()
    tasks = tasks if tasks is not None else load_benchmark_tasks(tasks_path)
    package_root = Path(package_manager_dir) if package_manager_dir is not None else out_dir.parent / "packages"

    skill_variants_by_tool = {
        tool_name: build_skill_variant_map(
            tool,
            tools,
            generator,
            allowed_conditions=allowed_conditions,
            package_manager_dir=package_root,
            allow_package_generation=allow_package_generation,
        )
        for tool_name, tool in tools.items()
    }
    routing_scores = run_routing_pipeline(
        tasks,
        tools,
        skill_variants_by_tool,
        predictor,
        output_dir=out_dir,
        benchmark_dir=Path(benchmark_dir) if benchmark_dir is not None else out_dir.parent / "benchmark",
        allow_predictor_fallback=allow_predictor_fallback,
    )
    for score in routing_scores:
        _annotate_run_record(score, model_name=model_name, model_slug=model_slug, shard_index=shard_index, num_shards=num_shards)
    summary = summarize_routing_scores(routing_scores)
    summary_by_tool = summarize_routing_scores_by_tool(routing_scores)
    summary_by_split = summarize_routing_scores_by_split(routing_scores)
    write_summary(out_dir / "routing_summary.json", summary)
    write_summary(out_dir / "routing_summary_by_tool.json", summary_by_tool)
    write_summary(out_dir / "routing_summary_by_split.json", summary_by_split)
    with (out_dir / "routing_details.json").open("w", encoding="utf-8") as f:
        json.dump(routing_scores, f, indent=2, ensure_ascii=False)
    _write_jsonl(out_dir / "routing_records.jsonl", routing_scores)
    return routing_scores, summary, {"by_tool": summary_by_tool, "by_split": summary_by_split}


def _annotate_run_record(
    record: Dict[str, Any],
    *,
    model_name: str | None = None,
    model_slug: str | None = None,
    shard_index: int | None = None,
    num_shards: int | None = None,
) -> None:
    if model_name:
        record["model_name"] = model_name
    if model_slug:
        record["model_slug"] = model_slug
    if shard_index is not None:
        record["shard_index"] = shard_index
    if num_shards is not None:
        record["num_shards"] = num_shards


def run_full_experiment(
    tools_path: str | Path,
    tasks_path: str | Path,
    output_root: str | Path,
    generator_config: Dict[str, Any] | None = None,
    predictor_config: Dict[str, Any] | None = None,
    allowed_conditions: List[str] | None = None,
) -> Dict[str, Any]:
    output_root = Path(output_root)
    run_config = {
        "tools_path": str(tools_path),
        "tasks_path": str(tasks_path),
        "output_root": str(output_root),
        "generator": generator_config or {"type": "heuristic"},
        "predictor": predictor_config or {"type": "heuristic"},
        "seed": 42,
    }
    audit_manifest = build_run_manifest(
        run_type="full_experiment",
        output_root=output_root,
        config=run_config,
        seed=42,
        generator_config=generator_config,
        predictor_config=predictor_config,
    )
    write_audit_manifest(output_root, audit_manifest)
    tools = load_tools(tools_path)
    generator = SkillGenerator(backend_config=generator_config)
    predictor = build_predictor_from_config(predictor_config)

    package_records, package_summary, package_summary_by_tool = run_packaging_pipeline(
        tools=tools,
        output_dir=output_root / "packages",
        generator=generator,
        allowed_conditions=allowed_conditions,
    )
    benchmark_scores, benchmark_summary, benchmark_detail_summaries = run_benchmark_pipeline(
        tools=tools,
        tasks_path=tasks_path,
        output_dir=output_root / "benchmark",
        generator=generator,
        predictor=predictor,
        allowed_conditions=allowed_conditions,
    )
    routing_scores, routing_summary, routing_detail_summaries = run_routing_benchmark_pipeline(
        tools=tools,
        tasks_path=tasks_path,
        output_dir=output_root / "routing_benchmark",
        generator=generator,
        predictor=predictor,
        allowed_conditions=allowed_conditions,
    )
    benchmark_summary_by_tool = benchmark_detail_summaries["by_tool"]
    benchmark_summary_by_split = benchmark_detail_summaries["by_split"]
    pairwise_comparisons = benchmark_detail_summaries["pairwise"]
    error_taxonomy = benchmark_detail_summaries["error_taxonomy"]
    method_win_analysis = benchmark_detail_summaries["method_wins"]
    routing_summary_by_tool = routing_detail_summaries["by_tool"]
    routing_summary_by_split = routing_detail_summaries["by_split"]
    generation_backend_usage = _summarize_backend_usage(
        package_records,
        configured_key="configured_generation_backend",
        actual_key="actual_generation_backend",
        fallback_key="generation_fallback_used",
    )
    predictor_backend_usage = _summarize_backend_usage(
        benchmark_scores,
        configured_key="predictor_configured_backend",
        actual_key="predictor_backend",
        fallback_key="predictor_fallback_used",
    )

    markdown_text = build_results_markdown(
        package_summary=package_summary,
        benchmark_summary=benchmark_summary,
        tools_path=str(tools_path),
        tasks_path=str(tasks_path),
        routing_summary=routing_summary,
        package_summary_by_tool=package_summary_by_tool,
        benchmark_summary_by_tool=benchmark_summary_by_tool,
        benchmark_summary_by_split=benchmark_summary_by_split,
        routing_summary_by_tool=routing_summary_by_tool,
        routing_summary_by_split=routing_summary_by_split,
        pairwise_comparisons=pairwise_comparisons,
        error_taxonomy=error_taxonomy,
        method_win_analysis=method_win_analysis,
        benchmark_failures=collect_failure_highlights(benchmark_scores),
    )
    csv_text = build_results_csv(package_summary=package_summary, benchmark_summary=benchmark_summary, routing_summary=routing_summary)
    write_report(
        output_root / "reports",
        markdown_text,
        csv_text,
        extra_files={
            "benchmark_by_tool.csv": build_benchmark_by_tool_csv(benchmark_summary_by_tool),
            "benchmark_by_split.csv": build_benchmark_by_split_csv(benchmark_summary_by_split),
            "pairwise_comparisons.csv": build_pairwise_comparison_csv(pairwise_comparisons),
            "error_taxonomy.csv": build_error_taxonomy_csv(error_taxonomy),
            "method_wins.csv": build_method_wins_csv(method_win_analysis),
            "package_by_tool.csv": build_package_by_tool_csv(package_summary_by_tool),
            "routing_summary.csv": build_routing_results_csv(routing_summary),
            "routing_by_tool.csv": build_routing_by_tool_csv(routing_summary_by_tool),
            "routing_by_split.csv": build_routing_by_split_csv(routing_summary_by_split),
        },
    )
    package_record_map = {
        (record["tool_name"], record["baseline_name"]): record
        for record in package_records
    }
    audit_records: List[Dict[str, Any]] = []
    for record in package_records:
        tool = tools[record["tool_name"]]
        artifact_path = output_root / "packages" / _safe_dir_name(record["tool_name"]) / record["baseline_name"]
        audit_records.append(generation_audit_record(audit_manifest, tool, record["skill"], record["report"], artifact_path))
    for score in benchmark_scores:
        package_record = package_record_map.get((score.get("tool_name"), score.get("baseline_name")))
        artifact_path = output_root / "benchmark" / _safe_dir_name(str(score.get("tool_name", ""))) / _safe_dir_name(str(score.get("baseline_name", ""))) / f"{_safe_dir_name(str(score.get('task_id', '')))}.result.json"
        audit_records.append(
            prediction_audit_record(
                audit_manifest,
                score,
                validation_report=package_record["report"] if package_record else None,
                artifact_path=artifact_path,
            )
        )
    write_audit_jsonl(output_root / "audit_records.jsonl", audit_records)
    baseline_results_path = Path("outputs/tables/baseline_results.csv")
    baseline_results_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_results_path.write_text(csv_text, encoding="utf-8")

    manifest = {
        "run_id": audit_manifest["run_id"],
        "git_commit_hash": audit_manifest["git_commit_hash"],
        "config_hash": audit_manifest["config_hash"],
        "seed": audit_manifest["seed"],
        "model_name": audit_manifest["model_name"],
        "quantization": audit_manifest["quantization"],
        "hardware": audit_manifest["hardware"],
        "audit_jsonl": audit_manifest["audit_jsonl"],
        "manifest_path": audit_manifest["manifest_path"],
        "tools_path": str(tools_path),
        "tasks_path": str(tasks_path),
        "output_root": str(output_root),
        "package_summary": package_summary,
        "package_summary_by_tool": package_summary_by_tool,
        "benchmark_summary": benchmark_summary,
        "benchmark_summary_by_tool": benchmark_summary_by_tool,
        "benchmark_summary_by_split": benchmark_summary_by_split,
        "routing_summary": routing_summary,
        "routing_summary_by_tool": routing_summary_by_tool,
        "routing_summary_by_split": routing_summary_by_split,
        "pairwise_comparisons": pairwise_comparisons,
        "error_taxonomy": error_taxonomy,
        "method_win_analysis": method_win_analysis,
        "predictor_backend": predictor.backend_name,
        "generator_backend": getattr(generator.backend, "backend_name", "unknown"),
        "generation_backend_usage": generation_backend_usage,
        "predictor_backend_usage": predictor_backend_usage,
        "generator_config": generator_config or {},
        "predictor_config": predictor_config or {},
    }
    write_summary(output_root / "experiment_manifest.json", manifest)
    write_audit_manifest(output_root, {**audit_manifest, "experiment_manifest": manifest})
    return manifest


def run_full_experiment_from_config(config_path: str | Path, overrides: Dict[str, Any] | None = None) -> Dict[str, Any]:
    config = load_json_config(config_path)
    if overrides:
        config = merge_experiment_config(config, overrides)

    return run_full_experiment(
        tools_path=config["tools_path"],
        tasks_path=config["tasks_path"],
        output_root=config["output_root"],
        generator_config=config.get("generator"),
        predictor_config=config.get("predictor"),
        allowed_conditions=config.get("conditions"),
    )

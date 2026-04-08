from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from autoskill.benchmark import load_benchmark_tasks
from autoskill.config import load_json_config, merge_experiment_config
from autoskill.evaluation import summarize_records, summarize_records_by_tool, write_summary
from autoskill.generator import SkillGenerator
from autoskill.packaging import write_skill_package
from autoskill.parser import parse_mcp_tool
from autoskill.predictor import PredictorBackend, build_predictor_from_config, build_predictor_from_env, safe_predict
from autoskill.raw_mcp import build_raw_mcp_skill
from autoskill.reporting import (
    build_benchmark_by_tool_csv,
    build_package_by_tool_csv,
    build_results_csv,
    build_results_markdown,
    collect_failure_highlights,
    write_report,
)
from autoskill.schema_only import build_schema_only_skill
from autoskill.task_eval import score_prediction, summarize_task_scores, summarize_task_scores_by_tool
from autoskill.validator import validate_skill


def load_tools(raw_path: str | Path) -> Dict[str, Any]:
    raw_path = Path(raw_path)
    with raw_path.open("r", encoding="utf-8") as f:
        raw_tools = json.load(f)
    return {
        tool.tool_name: tool
        for idx, raw_tool in enumerate(raw_tools)
        for tool in [parse_mcp_tool(raw_tool, source_pointer=f"{raw_path}#{idx}")]
    }


def build_skill_variants(tool: Any, generator: SkillGenerator) -> List[Any]:
    return [
        build_raw_mcp_skill(tool),
        build_schema_only_skill(tool),
        generator.generate(tool),
    ]


def _write_jsonl(path: Path, records: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def run_packaging_pipeline(
    tools: Dict[str, Any],
    output_dir: str | Path,
    generator: SkillGenerator | None = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Dict[str, Any]]]:
    out_dir = Path(output_dir)
    generator = generator or SkillGenerator()
    records: List[Dict[str, Any]] = []

    for tool in tools.values():
        variants = build_skill_variants(tool, generator)
        for skill in variants:
            report = validate_skill(tool, skill)
            write_skill_package(out_dir / tool.tool_name / skill.baseline_name, tool, skill, report)
            records.append(
                {
                    "tool_name": tool.tool_name,
                    "baseline_name": skill.baseline_name,
                    "skill": skill,
                    "report": report,
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
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Dict[str, Any]]]:
    out_dir = Path(output_dir)
    generator = generator or SkillGenerator()
    predictor = predictor or build_predictor_from_env()
    tasks = load_benchmark_tasks(tasks_path)
    all_scores: List[Dict[str, Any]] = []

    for task in tasks:
        if task.tool_name not in tools:
            continue
        tool = tools[task.tool_name]
        variants = build_skill_variants(tool, generator)
        for skill in variants:
            report = validate_skill(tool, skill)
            write_skill_package(out_dir / task.tool_name / skill.baseline_name, tool, skill, report)
            prediction = safe_predict(tool, skill, task, predictor)
            score = score_prediction(task, tool, prediction)
            score["predictor_backend"] = predictor.backend_name
            score["user_request"] = task.user_request
            all_scores.append(score)

            exposure_path = out_dir / task.tool_name / skill.baseline_name / f"{task.task_id}.prompt.txt"
            exposure_path.parent.mkdir(parents=True, exist_ok=True)
            exposure_path.write_text(prediction.exposure_text, encoding="utf-8")

    summary = summarize_task_scores(all_scores)
    summary_by_tool = summarize_task_scores_by_tool(all_scores)
    write_summary(out_dir / "benchmark_summary.json", summary)
    write_summary(out_dir / "benchmark_summary_by_tool.json", summary_by_tool)
    with (out_dir / "benchmark_details.json").open("w", encoding="utf-8") as f:
        json.dump(all_scores, f, indent=2, ensure_ascii=False)
    _write_jsonl(out_dir / "prediction_records.jsonl", all_scores)
    return all_scores, summary, summary_by_tool


def run_full_experiment(
    tools_path: str | Path,
    tasks_path: str | Path,
    output_root: str | Path,
    generator_config: Dict[str, Any] | None = None,
    predictor_config: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    output_root = Path(output_root)
    tools = load_tools(tools_path)
    generator = SkillGenerator(backend_config=generator_config)
    predictor = build_predictor_from_config(predictor_config)

    _, package_summary, package_summary_by_tool = run_packaging_pipeline(
        tools=tools,
        output_dir=output_root / "packages",
        generator=generator,
    )
    benchmark_scores, benchmark_summary, benchmark_summary_by_tool = run_benchmark_pipeline(
        tools=tools,
        tasks_path=tasks_path,
        output_dir=output_root / "benchmark",
        generator=generator,
        predictor=predictor,
    )

    markdown_text = build_results_markdown(
        package_summary=package_summary,
        benchmark_summary=benchmark_summary,
        tools_path=str(tools_path),
        tasks_path=str(tasks_path),
        package_summary_by_tool=package_summary_by_tool,
        benchmark_summary_by_tool=benchmark_summary_by_tool,
        benchmark_failures=collect_failure_highlights(benchmark_scores),
    )
    csv_text = build_results_csv(package_summary=package_summary, benchmark_summary=benchmark_summary)
    write_report(
        output_root / "reports",
        markdown_text,
        csv_text,
        extra_files={
            "benchmark_by_tool.csv": build_benchmark_by_tool_csv(benchmark_summary_by_tool),
            "package_by_tool.csv": build_package_by_tool_csv(package_summary_by_tool),
        },
    )

    manifest = {
        "tools_path": str(tools_path),
        "tasks_path": str(tasks_path),
        "package_summary": package_summary,
        "package_summary_by_tool": package_summary_by_tool,
        "benchmark_summary": benchmark_summary,
        "benchmark_summary_by_tool": benchmark_summary_by_tool,
        "predictor_backend": predictor.backend_name,
        "generator_backend": getattr(generator.backend, "backend_name", "unknown"),
        "generator_config": generator_config or {},
        "predictor_config": predictor_config or {},
    }
    write_summary(output_root / "experiment_manifest.json", manifest)
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
    )

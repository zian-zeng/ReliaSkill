from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from autoskill.config import validate_experiment_config
from autoskill.reliability import run_reliability_pipeline


def _fmt(value: Any) -> str:
    return f"{value:.4f}" if isinstance(value, (float, int)) else ""


def _preflight_reliability_run(run: Dict[str, Any], base_dir: Path) -> Dict[str, Any]:
    proxy_config = {
        "tools_path": run.get("tools_path"),
        "tasks_path": run.get("behavior_path"),
        "output_root": run.get("output_root"),
        "generator": run.get("generator"),
        "predictor": run.get("predictor"),
    }
    return validate_experiment_config(proxy_config, config_path=base_dir / "model_comparison.json")


def _selected_summary(manifest: Dict[str, Any], condition: str) -> Dict[str, Any]:
    row = manifest.get("summary", {}).get(condition, {})
    return {
        "condition": condition,
        "avg_score": row.get("avg_score"),
        "deploy_rate": row.get("deploy_rate"),
        "harmful_skill_injection_rate": row.get("avg_harmful_skill_injection_rate"),
        "trigger_precision": row.get("avg_trigger_precision"),
        "trigger_recall": row.get("avg_trigger_recall"),
        "token_overhead": row.get("avg_token_overhead_estimate"),
        "latency_ms": row.get("avg_prediction_latency_ms"),
    }


def summarize_model_comparison(results: List[Dict[str, Any]], comparisons: List[Dict[str, Any]]) -> Dict[str, Any]:
    runs = []
    by_name: Dict[str, Dict[str, Any]] = {}
    for item in results:
        run = item["run"]
        selected_condition = run.get("selected_condition", "gated_skill")
        manifest = item.get("manifest") or {}
        selected = _selected_summary(manifest, selected_condition) if manifest else {}
        row = {
            "run_name": run["name"],
            "role": run.get("role", ""),
            "status": item["status"],
            "selected_condition": selected_condition,
            "predictor": run.get("predictor", {}).get("model_name_or_path") or run.get("predictor", {}).get("model") or run.get("predictor", {}).get("type", ""),
            **selected,
            "output_root": run.get("output_root", ""),
        }
        runs.append(row)
        by_name[run["name"]] = row

    deltas = []
    for comparison in comparisons:
        left = by_name.get(comparison.get("left"))
        right = by_name.get(comparison.get("right"))
        metric = comparison.get("metric", "avg_score")
        if not left or not right:
            continue
        left_value = left.get(metric)
        right_value = right.get(metric)
        delta = round(float(left_value) - float(right_value), 4) if left_value is not None and right_value is not None else None
        deltas.append(
            {
                "name": comparison.get("name") or f"{comparison.get('left')}_vs_{comparison.get('right')}",
                "left": comparison.get("left"),
                "right": comparison.get("right"),
                "metric": metric,
                "left_value": left_value,
                "right_value": right_value,
                "delta": delta,
            }
        )
    return {"runs": runs, "comparisons": deltas}


def build_model_comparison_markdown(summary: Dict[str, Any], config: Dict[str, Any]) -> str:
    lines = [
        "# Low-Compute Model Comparison",
        "",
        f"- Hardware: `{config.get('hardware', 'unspecified')}`",
        f"- Compute budget: `{config.get('compute_budget', 'unspecified')}`",
        "",
        "| Run | Role | Condition | Predictor | Score | Deploy Rate | Harm Rate | Precision | Recall | Tokens | Latency ms |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary.get("runs", []):
        lines.append(
            f"| {row.get('run_name', '')} | {row.get('role', '')} | {row.get('selected_condition', '')} | "
            f"{row.get('predictor', '')} | {_fmt(row.get('avg_score'))} | {_fmt(row.get('deploy_rate'))} | "
            f"{_fmt(row.get('harmful_skill_injection_rate'))} | {_fmt(row.get('trigger_precision'))} | "
            f"{_fmt(row.get('trigger_recall'))} | {_fmt(row.get('token_overhead'))} | {_fmt(row.get('latency_ms'))} |"
        )
    lines.extend(["", "## Deltas", "", "| Comparison | Metric | Left | Right | Delta |", "| --- | --- | ---: | ---: | ---: |"])
    for row in summary.get("comparisons", []):
        lines.append(
            f"| {row.get('name', '')} | {row.get('metric', '')} | {_fmt(row.get('left_value'))} | "
            f"{_fmt(row.get('right_value'))} | {_fmt(row.get('delta'))} |"
        )
    return "\n".join(lines) + "\n"


def build_model_comparison_csv(summary: Dict[str, Any]) -> str:
    headers = [
        "run_name",
        "role",
        "selected_condition",
        "predictor",
        "avg_score",
        "deploy_rate",
        "harmful_skill_injection_rate",
        "trigger_precision",
        "trigger_recall",
        "token_overhead",
        "latency_ms",
        "output_root",
    ]
    lines = [",".join(headers)]
    for row in summary.get("runs", []):
        lines.append(",".join(str(row.get(header, "")) for header in headers))
    lines.append("")
    return "\n".join(lines)


def run_model_comparison_from_config(config_path: str | Path, preflight_only: bool = False) -> Dict[str, Any]:
    path = Path(config_path)
    with path.open("r", encoding="utf-8") as f:
        config = json.load(f)
    output_root = Path(config.get("output_root", "outputs/model_comparison"))
    output_root.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, Any]] = []

    for run in config.get("runs", []):
        preflight = _preflight_reliability_run(run, path.resolve().parent)
        item: Dict[str, Any] = {"run": run, "preflight": preflight, "status": "preflight_only" if preflight_only else "pending"}
        if not preflight.get("valid"):
            item["status"] = "preflight_failed"
        elif not preflight_only:
            rel = run.get("reliability", {})
            item["manifest"] = run_reliability_pipeline(
                tools_path=run["tools_path"],
                behavior_path=run["behavior_path"],
                output_root=run["output_root"],
                generator_config=run.get("generator"),
                predictor_config=run.get("predictor"),
                max_repair_rounds=int(rel.get("max_repair_rounds", 2)),
                deploy_threshold=float(rel.get("deploy_threshold", 70.0)),
                ablation_mode=rel.get("ablation_mode"),
            )
            item["status"] = "completed"
        results.append(item)

    summary = summarize_model_comparison(results, config.get("comparisons", []))
    manifest = {
        "config_path": str(path),
        "output_root": str(output_root),
        "hardware": config.get("hardware"),
        "compute_budget": config.get("compute_budget"),
        "preflight_only": preflight_only,
        "results": results,
        "summary": summary,
    }
    (output_root / "model_comparison_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_root / "model_comparison_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_root / "model_comparison_report.md").write_text(build_model_comparison_markdown(summary, config), encoding="utf-8")
    (output_root / "model_comparison_summary.csv").write_text(build_model_comparison_csv(summary), encoding="utf-8")
    return manifest

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from autoskill.config import load_json_config, validate_experiment_config
from autoskill.experiment import run_full_experiment_from_config


def _slugify_config_name(path: Path) -> str:
    return path.stem.replace(" ", "_")


def _fmt_metric(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.4f}"
    return ""


def aggregate_experiment_manifests(results: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    runs: List[Dict[str, Any]] = []
    for item in results:
        preflight = item.get("preflight", {})
        manifest = item.get("manifest")
        if not manifest:
            runs.append(
                {
                    "run_name": item["run_name"],
                    "config_path": item["config_path"],
                    "status": item["status"],
                    "valid_config": preflight.get("valid", False),
                    "generator_backend": "",
                    "predictor_backend": "",
                    "autoskill_exact_match": None,
                    "raw_mcp_exact_match": None,
                    "schema_only_exact_match": None,
                    "autoskill_vs_raw_delta": None,
                    "autoskill_vs_schema_delta": None,
                    "output_root": preflight.get("resolved_paths", {}).get("output_root", ""),
                }
            )
            continue

        benchmark_summary = manifest.get("benchmark_summary", {})
        autoskill = benchmark_summary.get("autoskill_base", {})
        raw_mcp = benchmark_summary.get("raw_mcp", {})
        schema_only = benchmark_summary.get("schema_only", {})
        autoskill_exact = autoskill.get("exact_match_rate")
        raw_exact = raw_mcp.get("exact_match_rate")
        schema_exact = schema_only.get("exact_match_rate")
        runs.append(
            {
                "run_name": item["run_name"],
                "config_path": item["config_path"],
                "status": item["status"],
                "valid_config": preflight.get("valid", False),
                "generator_backend": manifest.get("generator_backend", ""),
                "predictor_backend": manifest.get("predictor_backend", ""),
                "autoskill_exact_match": autoskill_exact,
                "raw_mcp_exact_match": raw_exact,
                "schema_only_exact_match": schema_exact,
                "autoskill_vs_raw_delta": round(float(autoskill_exact) - float(raw_exact), 4) if autoskill_exact is not None and raw_exact is not None else None,
                "autoskill_vs_schema_delta": round(float(autoskill_exact) - float(schema_exact), 4) if autoskill_exact is not None and schema_exact is not None else None,
                "output_root": manifest.get("generator_config", {}).get("output_root", "") or manifest.get("output_root", ""),
            }
        )
    return {"runs": runs}


def build_sweep_markdown(summary: Dict[str, Any]) -> str:
    lines = [
        "# AutoSkill Experiment Sweep",
        "",
        "| Run | Status | Valid Config | Generator | Predictor | AutoSkill EM | Raw MCP EM | Schema Only EM | Delta vs Raw | Delta vs Schema |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary.get("runs", []):
        lines.append(
            f"| {row.get('run_name', '')} | {row.get('status', '')} | {row.get('valid_config', False)} | {row.get('generator_backend', '')} | {row.get('predictor_backend', '')} | "
            f"{_fmt_metric(row.get('autoskill_exact_match'))} | "
            f"{_fmt_metric(row.get('raw_mcp_exact_match'))} | "
            f"{_fmt_metric(row.get('schema_only_exact_match'))} | "
            f"{_fmt_metric(row.get('autoskill_vs_raw_delta'))} | "
            f"{_fmt_metric(row.get('autoskill_vs_schema_delta'))} |"
        )
    lines.append("")
    return "\n".join(lines)


def build_sweep_csv(summary: Dict[str, Any]) -> str:
    header = [
        "run_name",
        "config_path",
        "status",
        "valid_config",
        "generator_backend",
        "predictor_backend",
        "autoskill_exact_match",
        "raw_mcp_exact_match",
        "schema_only_exact_match",
        "autoskill_vs_raw_delta",
        "autoskill_vs_schema_delta",
        "output_root",
    ]
    lines = [",".join(header)]
    for row in summary.get("runs", []):
        lines.append(
            ",".join(
                [
                    str(row.get("run_name", "")),
                    str(row.get("config_path", "")),
                    str(row.get("status", "")),
                    str(row.get("valid_config", "")),
                    str(row.get("generator_backend", "")),
                    str(row.get("predictor_backend", "")),
                    "" if row.get("autoskill_exact_match") is None else str(row["autoskill_exact_match"]),
                    "" if row.get("raw_mcp_exact_match") is None else str(row["raw_mcp_exact_match"]),
                    "" if row.get("schema_only_exact_match") is None else str(row["schema_only_exact_match"]),
                    "" if row.get("autoskill_vs_raw_delta") is None else str(row["autoskill_vs_raw_delta"]),
                    "" if row.get("autoskill_vs_schema_delta") is None else str(row["autoskill_vs_schema_delta"]),
                    str(row.get("output_root", "")),
                ]
            )
        )
    lines.append("")
    return "\n".join(lines)


def run_experiment_sweep(
    config_paths: List[str | Path],
    output_root: str | Path,
    preflight_only: bool = False,
) -> Dict[str, Any]:
    out_dir = Path(output_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, Any]] = []
    seen_output_roots: Dict[str, str] = {}

    for config_path_value in config_paths:
        config_path = Path(config_path_value).resolve()
        run_name = _slugify_config_name(config_path)
        config = load_json_config(config_path)
        preflight = validate_experiment_config(config, config_path=config_path)
        resolved_output = preflight.get("resolved_paths", {}).get("output_root", "")
        if resolved_output:
            previous = seen_output_roots.get(resolved_output)
            if previous and previous != str(config_path):
                preflight["valid"] = False
                preflight.setdefault("errors", []).append(
                    f"output_root collision: {resolved_output} is also used by {previous}"
                )
            else:
                seen_output_roots[resolved_output] = str(config_path)

        item: Dict[str, Any] = {
            "run_name": run_name,
            "config_path": str(config_path),
            "preflight": preflight,
            "status": "preflight_only" if preflight_only else "pending",
        }

        if not preflight["valid"] or preflight_only:
            item["status"] = "preflight_failed" if not preflight["valid"] else "preflight_only"
            results.append(item)
            continue

        manifest = run_full_experiment_from_config(config_path)
        item["manifest"] = manifest
        item["status"] = "completed"
        results.append(item)

    summary = aggregate_experiment_manifests(results)
    (out_dir / "sweep_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (out_dir / "sweep_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out_dir / "sweep_summary.md").write_text(build_sweep_markdown(summary), encoding="utf-8")
    (out_dir / "sweep_summary.csv").write_text(build_sweep_csv(summary), encoding="utf-8")
    return {"results": results, "summary": summary}

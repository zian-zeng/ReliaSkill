from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoskill.metrics import build_metric_tables, write_metric_tables


PAPER_TABLES = {
    "dataset_tool_statistics": {
        "caption": "Dataset and tool statistics.",
        "label": "tab:dataset-tool-statistics",
        "columns": [
            "source_id",
            "domain",
            "side_effect_type",
            "tool_count",
            "server_count",
            "auth_required_count",
            "avg_args",
            "avg_required_args",
            "enum_count",
        ],
    },
    "main_results": {
        "caption": "Main tool-use results.",
        "label": "tab:main-results",
        "columns": [
            "baseline_name",
            "num_examples",
            "tool_selection_accuracy",
            "argument_schema_validity",
            "argument_exact_match",
            "joint_exact_match",
            "joint_exact_match_wilson_low",
            "joint_exact_match_wilson_high",
        ],
    },
    "utility_harm": {
        "caption": "Utility and harm metrics.",
        "label": "tab:utility-harm",
        "columns": [
            "baseline_name",
            "num_controls",
            "trigger_precision",
            "trigger_recall",
            "harmful_skill_injection_rate",
            "skill_induced_harm_rate",
            "utility_joint_exact_match",
        ],
    },
    "ablation": {
        "caption": "ReliaSkill component ablations.",
        "label": "tab:ablation",
        "columns": [
            "ablation",
            "joint_em",
            "argument_validity",
            "trigger_precision",
            "hsir",
            "score",
            "score_ci_low",
            "score_ci_high",
        ],
    },
    "model_scaling": {
        "caption": "Model scaling and run-level reliability.",
        "label": "tab:model-scaling",
        "columns": [
            "run_id",
            "run_type",
            "predictor_model",
            "quantization",
            "condition",
            "avg_score",
            "deploy_rate",
            "harmful_skill_injection_rate",
            "joint_exact_match",
            "avg_latency_ms",
        ],
    },
    "error_analysis": {
        "caption": "Representative error analysis cases.",
        "label": "tab:error-analysis",
        "columns": [
            "case_id",
            "required_case",
            "tool_name",
            "failure_type",
            "confidence",
            "source_artifact_path",
        ],
    },
    "reliability_threshold_sensitivity": {
        "caption": "Reliability threshold sensitivity.",
        "label": "tab:threshold-sensitivity",
        "columns": ["threshold", "condition", "total_tools", "deploy_rate", "avg_score"],
    },
    "cost_latency": {
        "caption": "Estimated cost and latency from audit logs.",
        "label": "tab:cost-latency",
        "columns": [
            "run_id",
            "event_type",
            "condition",
            "model_name",
            "quantization",
            "num_events",
            "avg_latency_ms",
            "avg_prompt_tokens_est",
            "avg_output_tokens_est",
            "total_tokens_est",
        ],
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate paper CSV and LaTeX tables directly from saved logs.")
    parser.add_argument("--run", type=Path, default=None, help="Run directory, e.g. outputs/final_run.")
    parser.add_argument("--input", type=Path, default=None, help="Backward-compatible alias for --run.")
    parser.add_argument("--out", type=Path, default=None, help="Output directory for CSV and .tex tables.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dir = args.run or args.input
    if run_dir is None:
        raise SystemExit("Provide --run outputs/final_run or --input <run_dir>.")
    out_dir = args.out or (run_dir / "tables" if args.run is not None else Path("outputs/tables"))
    out_dir.mkdir(parents=True, exist_ok=True)

    tables = build_all_paper_tables(run_dir, out_dir)
    paths = write_all_tables(tables, out_dir)

    print(f"main_rows={len(tables['main_results'])}")
    print(f"harm_rows={len(tables['utility_harm'])}")
    print(f"stat_rows={len(tables.get('stat_tests', []))}")
    for name in PAPER_TABLES:
        print(f"{name}_csv={paths[name]['csv']}")
        print(f"{name}_tex={paths[name]['tex']}")


def build_all_paper_tables(run_dir: str | Path, out_dir: str | Path) -> Dict[str, List[Dict[str, Any]]]:
    run = Path(run_dir)
    out = Path(out_dir)

    metric_tables = build_metric_tables(run)
    if not metric_tables["main_results"]:
        metric_tables = _first_nonempty_metric_tables(_candidate_run_roots(run))
    write_metric_tables(run if metric_tables["main_results"] else run, out)

    tables: Dict[str, List[Dict[str, Any]]] = {
        "main_results": metric_tables["main_results"],
        "utility_harm": metric_tables["harm_utility"],
        "stat_tests": metric_tables["stat_tests"],
        "dataset_tool_statistics": _read_existing_table(run, "dataset_stats.csv"),
        "ablation": _read_existing_table(run, "ablation_results.csv"),
        "error_analysis": _read_existing_table(run, "error_analysis.csv"),
        "reliability_threshold_sensitivity": _read_existing_table(run, "reliability_threshold_sensitivity.csv"),
        "model_scaling": build_model_scaling_rows(run),
        "cost_latency": build_cost_latency_rows(run),
    }
    return tables


def write_all_tables(tables: Dict[str, List[Dict[str, Any]]], out_dir: str | Path) -> Dict[str, Dict[str, Path]]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, Dict[str, Path]] = {}
    for name, meta in PAPER_TABLES.items():
        rows = tables.get(name, [])
        paper_columns = [column for column in meta["columns"] if rows and column in rows[0]] or list(meta["columns"])
        csv_columns = _ordered_columns(rows, paper_columns)
        csv_path = out / f"{name}.csv"
        tex_path = out / f"{name}.tex"
        _write_csv(csv_path, rows, csv_columns)
        write_latex_table(tex_path, rows, paper_columns, caption=meta["caption"], label=meta["label"])
        paths[name] = {"csv": csv_path, "tex": tex_path}
    if "stat_tests" in tables:
        _write_csv(out / "stat_tests.csv", tables["stat_tests"], _columns_for_rows(tables["stat_tests"]))
        write_latex_table(
            out / "stat_tests.tex",
            tables["stat_tests"],
            _columns_for_rows(tables["stat_tests"]),
            caption="Paired significance tests.",
            label="tab:stat-tests",
        )
    return paths


def build_cost_latency_rows(run_dir: str | Path) -> List[Dict[str, Any]]:
    records = _load_audit_records(run_dir)
    grouped: Dict[tuple[str, str, str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        event_type = str(record.get("event_type") or "")
        if event_type not in {"skill_generation", "prediction", "behavior_prediction"}:
            continue
        condition = str(record.get("condition") or "")
        model_name = _string_model_name(record.get("model_name"))
        quantization = _string_model_name(record.get("quantization"))
        key = (str(record.get("run_id", "")), event_type, condition, model_name, quantization)
        grouped[key].append(record)

    rows: List[Dict[str, Any]] = []
    for (run_id, event_type, condition, model_name, quantization), items in sorted(grouped.items()):
        latencies = [_extract_latency(item) for item in items]
        latencies = [value for value in latencies if value is not None]
        prompt_tokens = [_token_estimate(item.get("raw_prompt", "")) for item in items]
        output_tokens = [_token_estimate(item.get("raw_model_output", "")) for item in items]
        rows.append(
            {
                "run_id": run_id,
                "event_type": event_type,
                "condition": condition,
                "model_name": model_name,
                "quantization": quantization,
                "num_events": len(items),
                "avg_latency_ms": _mean(latencies),
                "avg_prompt_tokens_est": _mean(prompt_tokens),
                "avg_output_tokens_est": _mean(output_tokens),
                "total_tokens_est": int(sum(prompt_tokens) + sum(output_tokens)),
            }
        )
    return rows


def build_model_scaling_rows(run_dir: str | Path) -> List[Dict[str, Any]]:
    model_csv = _find_existing_file(run_dir, "model_comparison_summary.csv")
    if model_csv:
        rows = _read_csv(model_csv)
        metric_fields = {
            "avg_score",
            "deploy_rate",
            "harmful_skill_injection_rate",
            "trigger_precision",
            "trigger_recall",
            "joint_exact_match",
            "latency_ms",
            "avg_latency_ms",
        }
        if rows and any(any(row.get(field) for field in metric_fields) for row in rows):
            return [_normalize_model_scaling_row(row) for row in rows if any(row.values())]

    rows: List[Dict[str, Any]] = []
    for manifest_path in _find_manifest_files(run_dir):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        base = {
            "run_id": manifest.get("run_id", manifest_path.parent.name),
            "run_type": manifest.get("run_type", ""),
            "predictor_model": _string_model_name((manifest.get("model_name") or {}).get("predictor")),
            "quantization": _string_model_name((manifest.get("quantization") or {}).get("predictor")),
            "avg_latency_ms": "",
        }
        reliability = manifest.get("reliability_manifest") if isinstance(manifest.get("reliability_manifest"), dict) else manifest
        summary = reliability.get("summary") if isinstance(reliability.get("summary"), dict) else {}
        for condition, item in sorted(summary.items()):
            if not isinstance(item, dict):
                continue
            rows.append(
                {
                    **base,
                    "condition": condition,
                    "avg_score": item.get("avg_score", ""),
                    "deploy_rate": item.get("deploy_rate", ""),
                    "harmful_skill_injection_rate": item.get("avg_harmful_skill_injection_rate", item.get("harmful_skill_injection_rate", "")),
                    "joint_exact_match": "",
                    "avg_latency_ms": item.get("avg_prediction_latency_ms", ""),
                }
            )
        experiment = manifest.get("experiment_manifest") if isinstance(manifest.get("experiment_manifest"), dict) else manifest
        benchmark = experiment.get("benchmark_summary") if isinstance(experiment.get("benchmark_summary"), dict) else {}
        for condition, item in sorted(benchmark.items()):
            if not isinstance(item, dict):
                continue
            rows.append(
                {
                    **base,
                    "condition": condition,
                    "avg_score": "",
                    "deploy_rate": "",
                    "harmful_skill_injection_rate": "",
                    "joint_exact_match": item.get("joint_exact_match_rate", item.get("exact_match_rate", "")),
                    "avg_latency_ms": item.get("avg_latency_ms", ""),
                }
            )
    return _dedupe_rows(rows, key_fields=["run_id", "run_type", "predictor_model", "condition", "avg_score", "joint_exact_match"])


def write_latex_table(path: Path, rows: Sequence[Dict[str, Any]], columns: Sequence[str], *, caption: str, label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    align = "l" + ("r" * max(len(columns) - 1, 0))
    lines = [
        "% Auto-generated from ReliaSkill logs by scripts/make_tables.py. Do not edit numbers by hand.",
        "\\begin{table}[t]",
        "\\centering",
        "\\small",
        f"\\begin{{tabular}}{{{align}}}",
        "\\toprule",
        " & ".join(_latex_escape(_pretty_header(column)) for column in columns) + " \\\\",
        "\\midrule",
    ]
    if rows:
        for row in rows:
            lines.append(" & ".join(_latex_cell(row.get(column, "")) for column in columns) + " \\\\")
    else:
        lines.append("\\multicolumn{" + str(max(len(columns), 1)) + "}{c}{No rows found in logs} \\\\")
    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular}",
            f"\\caption{{{_latex_escape(caption)}}}",
            f"\\label{{{_latex_escape(label)}}}",
            "\\end{table}",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _read_existing_table(run_dir: str | Path, filename: str) -> List[Dict[str, Any]]:
    path = _find_existing_file(run_dir, filename)
    return _read_csv(path) if path else []


def _find_existing_file(run_dir: str | Path, filename: str) -> Path | None:
    run = Path(run_dir)
    roots = [run] if run.exists() else []
    roots.extend([Path("outputs/tables"), Path("outputs"), Path.cwd() / "outputs"])
    seen = set()
    for root in roots:
        if root in seen or not root.exists():
            continue
        seen.add(root)
        if root.is_file() and root.name == filename:
            return root
        direct = root / filename
        if direct.exists():
            return direct
        matches = sorted(root.rglob(filename))
        if matches:
            return matches[0]
    return None


def _find_manifest_files(run_dir: str | Path) -> List[Path]:
    run = Path(run_dir)
    roots = [run] if run.exists() else []
    roots.append(Path("outputs"))
    files: List[Path] = []
    seen = set()
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("manifest.json")):
            if path not in seen:
                files.append(path)
                seen.add(path)
    return files


def _load_audit_records(run_dir: str | Path) -> List[Dict[str, Any]]:
    run = Path(run_dir)
    roots = [run] if run.exists() else []
    roots.append(Path("outputs"))
    records: List[Dict[str, Any]] = []
    seen = set()
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("audit_records.jsonl")):
            if path in seen:
                continue
            seen.add(path)
            records.extend(_load_jsonl(path))
    return records


def _first_nonempty_metric_tables(roots: Iterable[Path]) -> Dict[str, List[Dict[str, Any]]]:
    for root in roots:
        if not root.exists():
            continue
        tables = build_metric_tables(root)
        if tables["main_results"] or tables["harm_utility"]:
            return tables
    return {"main_results": [], "harm_utility": [], "stat_tests": []}


def _candidate_run_roots(run: Path) -> List[Path]:
    return [
        run,
        Path("outputs/baselines_smoke"),
        Path("outputs/experiment"),
        Path("outputs/reliability_heuristic_sample"),
        Path("outputs/sample_run"),
    ]


def _normalize_model_scaling_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "run_id": row.get("run_name", row.get("run_id", "")),
        "run_type": row.get("role", row.get("run_type", "")),
        "predictor_model": row.get("predictor", row.get("predictor_model", "")),
        "quantization": row.get("quantization", ""),
        "condition": row.get("selected_condition", row.get("condition", "")),
        "avg_score": row.get("avg_score", ""),
        "deploy_rate": row.get("deploy_rate", ""),
        "harmful_skill_injection_rate": row.get("harmful_skill_injection_rate", ""),
        "joint_exact_match": row.get("joint_exact_match", ""),
        "avg_latency_ms": row.get("latency_ms", row.get("avg_latency_ms", "")),
    }


def _read_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return [dict(row) for row in csv.DictReader(f)]


def _write_csv(path: Path, rows: Sequence[Dict[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(fieldnames) if fieldnames else _columns_for_rows(rows)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def _columns_for_rows(rows: Sequence[Dict[str, Any]]) -> List[str]:
    columns: List[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    return columns


def _ordered_columns(rows: Sequence[Dict[str, Any]], preferred: Sequence[str]) -> List[str]:
    columns = [column for column in preferred if column]
    for column in _columns_for_rows(rows):
        if column not in columns:
            columns.append(column)
    return columns


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
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


def _extract_latency(record: Dict[str, Any]) -> float | None:
    for path in (
        ("score", "prediction_metadata", "prediction_latency_ms"),
        ("behavior_report", "result", "prediction_latency_ms"),
        ("behavior_report", "prediction_latency_ms"),
    ):
        value = _nested_get(record, path)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
    return None


def _nested_get(record: Dict[str, Any], path: Sequence[str]) -> Any:
    value: Any = record
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _token_estimate(text: Any) -> int:
    if text is None:
        return 0
    return len(str(text).split())


def _mean(values: Sequence[float | int]) -> float:
    return round(sum(float(value) for value in values) / len(values), 4) if values else 0.0


def _string_model_name(value: Any) -> str:
    if isinstance(value, dict):
        if "predictor" in value:
            return str(value.get("predictor", ""))
        if "generator" in value:
            return str(value.get("generator", ""))
        return json.dumps(value, sort_keys=True)
    return str(value or "")


def _dedupe_rows(rows: Sequence[Dict[str, Any]], key_fields: Sequence[str]) -> List[Dict[str, Any]]:
    seen = set()
    deduped: List[Dict[str, Any]] = []
    for row in rows:
        key = tuple(str(row.get(field, "")) for field in key_fields)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def _latex_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    text = str(value)
    try:
        numeric = float(text)
        if text.strip() and not any(char.isalpha() for char in text):
            return f"{numeric:.4f}".rstrip("0").rstrip(".")
    except ValueError:
        pass
    return _latex_escape(_truncate(text, 90))


def _latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def _pretty_header(column: str) -> str:
    return column.replace("_", " ").title()


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(limit - 3, 0)] + "..."


if __name__ == "__main__":
    main()

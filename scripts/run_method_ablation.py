from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoskill.experiment import run_full_experiment


TOOLS_PATH = Path("data/raw/public_mcp_filesystem_subset.json")
TASKS_PATH = Path("data/eval/public_mcp_filesystem_benchmark.jsonl")
OUT_ROOT = Path("outputs/method_ablation")
ABLATION_MODES = ["base_only", "semantic_concise", "semantic_dense", "selected"]


def _build_markdown(summary: dict[str, dict[str, float]]) -> str:
    lines = [
        "# AutoSkill Method Ablation",
        "",
        f"- Tools source: `{TOOLS_PATH}`",
        f"- Benchmark source: `{TASKS_PATH}`",
        "",
        "| Method Variant | Exact Match | Argument Validity | Required Arg Recall | Avg Semantic Hints | Avg Examples |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for mode in ABLATION_MODES:
        row = summary[mode]
        lines.append(
            f"| {mode} | {row['exact_match_rate']:.4f} | {row['avg_argument_validity']:.4f} | {row['avg_required_argument_recall']:.4f} | {row['avg_semantic_hint_entries']:.2f} | {row['avg_examples']:.2f} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    summary: dict[str, dict[str, float]] = {}

    for mode in ABLATION_MODES:
        manifest = run_full_experiment(
            tools_path=TOOLS_PATH,
            tasks_path=TASKS_PATH,
            output_root=OUT_ROOT / mode,
            generator_config={"type": "heuristic", "ablation_mode": mode},
            predictor_config={"type": "heuristic"},
        )
        package_row = manifest["package_summary"]["generated_skill_base"]
        benchmark_row = manifest["benchmark_summary"]["generated_skill_base"]
        summary[mode] = {
            "avg_examples": package_row.get("avg_examples", 0.0),
            "avg_semantic_hint_entries": package_row.get("avg_semantic_hint_entries", 0.0),
            "exact_match_rate": benchmark_row.get("exact_match_rate", 0.0),
            "avg_argument_validity": benchmark_row.get("avg_argument_validity", 0.0),
            "avg_required_argument_recall": benchmark_row.get("avg_required_argument_recall", 0.0),
        }
        print(
            f"{mode}: "
            f"exact_match={summary[mode]['exact_match_rate']:.4f}, "
            f"semantic_hints={summary[mode]['avg_semantic_hint_entries']:.2f}"
        )

    (OUT_ROOT / "ablation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (OUT_ROOT / "ablation_summary.md").write_text(_build_markdown(summary), encoding="utf-8")


if __name__ == "__main__":
    main()

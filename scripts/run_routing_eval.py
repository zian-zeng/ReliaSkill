from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoskill.benchmark import load_benchmark_tasks
from autoskill.experiment import load_tools, run_routing_benchmark_pipeline
from autoskill.multi_candidate import load_tools_as_toolir


DEFAULT_RAW_PATH = Path("data/raw/public_mcp_filesystem_subset.json")
DEFAULT_TASK_PATH = Path("data/eval/public_mcp_filesystem_benchmark.jsonl")
DEFAULT_OUT_ROOT = Path("outputs/routing_eval")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run hidden-tool routing evaluation for AutoSkill conditions.")
    parser.add_argument("--tools", type=Path, default=DEFAULT_RAW_PATH, help="Path to raw MCP tools or processed ToolIR JSONL.")
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASK_PATH, help="Path to the benchmark task JSON or JSONL file.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_ROOT, help="Directory for routing evaluation outputs.")
    parser.add_argument("--split", default=None, help="Optional split filter such as dev.")
    parser.add_argument("--conditions", nargs="*", default=None, help="Optional condition names to evaluate.")
    parser.add_argument("--package-manager-dir", type=Path, default=None, help="Optional versioned package directory.")
    parser.add_argument("--no-package-generation", action="store_true", help="Fail if requested packages are missing.")
    return parser.parse_args()


def _looks_like_toolir(path: Path) -> bool:
    try:
        with path.open("r", encoding="utf-8") as f:
            first = f.readline()
    except OSError:
        return False
    return '"tool_name"' in first and '"arguments"' in first and '"input_schema_raw"' in first


def _load_tools_any(path: Path):
    if _looks_like_toolir(path):
        return {tool.tool_name: tool for tool in load_tools_as_toolir(path)}
    return load_tools(path)


def main() -> None:
    args = parse_args()
    tools = _load_tools_any(args.tools)
    tasks = load_benchmark_tasks(args.tasks)
    if args.split:
        tasks = [task for task in tasks if task.split == args.split]
        if not tasks:
            raise ValueError(f"No tasks found for split={args.split!r} in {args.tasks}.")
    _, summary, _ = run_routing_benchmark_pipeline(
        tools=tools,
        tasks_path=args.tasks,
        tasks=tasks,
        output_dir=args.out,
        allowed_conditions=args.conditions,
        package_manager_dir=args.package_manager_dir,
        allow_package_generation=not args.no_package_generation,
    )
    for baseline_name, row in summary.items():
        print(
            f"{baseline_name}: "
            f"tool_acc={row['tool_selection_accuracy']:.4f}, "
            f"joint_exact={row['joint_exact_match_rate']:.4f}, "
            f"gold_hit={0.0 if row['gold_tool_hit_rate'] is None else row['gold_tool_hit_rate']:.4f}"
        )


if __name__ == "__main__":
    main()

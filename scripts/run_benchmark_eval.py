from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoskill.benchmark import load_benchmark_tasks
from autoskill.experiment import load_tools, run_benchmark_pipeline


DEFAULT_RAW_PATH = Path("data/raw/public_mcp_filesystem_subset.json")
DEFAULT_TASK_PATH = Path("data/eval/public_mcp_filesystem_benchmark.jsonl")
DEFAULT_OUT_ROOT = Path("outputs/benchmark_eval")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run AutoSkill benchmark evaluation on a generic BFCL-style task file.")
    parser.add_argument("--tools", type=Path, default=DEFAULT_RAW_PATH, help="Path to the raw MCP tool JSON file.")
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASK_PATH, help="Path to the benchmark task JSON file.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_ROOT, help="Directory for evaluation outputs.")
    parser.add_argument("--split", default=None, help="Optional split filter such as dev.")
    parser.add_argument("--conditions", nargs="*", default=None, help="Optional condition names to evaluate.")
    parser.add_argument("--package-manager-dir", type=Path, default=None, help="Optional versioned package directory.")
    parser.add_argument("--no-package-generation", action="store_true", help="Fail if requested packages are missing.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tools = load_tools(args.tools)
    tasks = load_benchmark_tasks(args.tasks)
    if args.split:
        tasks = [task for task in tasks if task.split == args.split]
        if not tasks:
            raise ValueError(f"No tasks found for split={args.split!r} in {args.tasks}.")
    _, summary, _ = run_benchmark_pipeline(
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
            f"exact_match={row['exact_match_rate']:.4f}, "
            f"arg_validity={row['avg_argument_validity']:.4f}"
        )


if __name__ == "__main__":
    main()

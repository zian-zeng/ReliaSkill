from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoskill.experiment import load_tools, run_benchmark_pipeline


DEFAULT_RAW_PATH = Path("data/raw/public_mcp_filesystem_subset.json")
DEFAULT_TASK_PATH = Path("data/eval/public_mcp_filesystem_benchmark.jsonl")
DEFAULT_OUT_ROOT = Path("outputs/benchmark_eval")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run AutoSkill benchmark evaluation on a generic BFCL-style task file.")
    parser.add_argument("--tools", type=Path, default=DEFAULT_RAW_PATH, help="Path to the raw MCP tool JSON file.")
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASK_PATH, help="Path to the benchmark task JSON file.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_ROOT, help="Directory for evaluation outputs.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tools = load_tools(args.tools)
    _, summary = run_benchmark_pipeline(tools=tools, tasks_path=args.tasks, output_dir=args.out)
    for baseline_name, row in summary.items():
        print(
            f"{baseline_name}: "
            f"exact_match={row['exact_match_rate']:.4f}, "
            f"arg_validity={row['avg_argument_validity']:.4f}"
        )


if __name__ == "__main__":
    main()

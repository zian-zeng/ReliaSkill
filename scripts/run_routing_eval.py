from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoskill.experiment import load_tools, run_routing_benchmark_pipeline


DEFAULT_RAW_PATH = Path("data/raw/public_mcp_filesystem_subset.json")
DEFAULT_TASK_PATH = Path("data/eval/public_mcp_filesystem_benchmark.jsonl")
DEFAULT_OUT_ROOT = Path("outputs/routing_eval")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run hidden-tool routing evaluation for AutoSkill conditions.")
    parser.add_argument("--tools", type=Path, default=DEFAULT_RAW_PATH, help="Path to the raw MCP tool JSON file.")
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASK_PATH, help="Path to the benchmark task JSON or JSONL file.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_ROOT, help="Directory for routing evaluation outputs.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tools = load_tools(args.tools)
    _, summary, _ = run_routing_benchmark_pipeline(tools=tools, tasks_path=args.tasks, output_dir=args.out)
    for baseline_name, row in summary.items():
        print(
            f"{baseline_name}: "
            f"tool_acc={row['tool_selection_accuracy']:.4f}, "
            f"joint_exact={row['joint_exact_match_rate']:.4f}, "
            f"gold_hit={0.0 if row['gold_tool_hit_rate'] is None else row['gold_tool_hit_rate']:.4f}"
        )


if __name__ == "__main__":
    main()

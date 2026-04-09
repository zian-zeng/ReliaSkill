from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoskill.config import load_json_config, validate_experiment_config
from autoskill.experiment import run_full_experiment, run_full_experiment_from_config


DEFAULT_TOOLS = Path("data/raw/public_mcp_filesystem_subset.json")
DEFAULT_TASKS = Path("data/eval/public_mcp_filesystem_benchmark.jsonl")
DEFAULT_OUT = Path("outputs/experiment")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the full AutoSkill package + benchmark experiment.")
    parser.add_argument("--config", type=Path, default=None, help="Optional JSON config for tools/tasks/output and backend settings.")
    parser.add_argument("--tools", type=Path, default=DEFAULT_TOOLS, help="Path to the raw MCP tool JSON file.")
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASKS, help="Path to the benchmark JSON or JSONL file.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output directory for the full experiment.")
    parser.add_argument("--preflight", action="store_true", help="Validate the config and print readiness details without running the experiment.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.config is not None:
        if args.preflight:
            report = validate_experiment_config(load_json_config(args.config), config_path=args.config)
            print(f"valid={report['valid']}")
            for error in report["errors"]:
                print(f"error: {error}")
            for warning in report["warnings"]:
                print(f"warning: {warning}")
            return
        manifest = run_full_experiment_from_config(args.config)
    else:
        manifest = run_full_experiment(tools_path=args.tools, tasks_path=args.tasks, output_root=args.out)
    print(f"generator_backend={manifest['generator_backend']}")
    print(f"predictor_backend={manifest['predictor_backend']}")
    if "generation_backend_usage" in manifest:
        usage = manifest["generation_backend_usage"]
        print(
            "generation_usage: "
            f"actual={usage['actual_backend_counts']}, "
            f"fallbacks={usage['fallback_count']}/{usage['num_records']}"
        )
    if "predictor_backend_usage" in manifest:
        usage = manifest["predictor_backend_usage"]
        print(
            "prediction_usage: "
            f"actual={usage['actual_backend_counts']}, "
            f"fallbacks={usage['fallback_count']}/{usage['num_records']}"
        )
    for baseline_name, row in manifest["benchmark_summary"].items():
        print(
            f"{baseline_name}: "
            f"exact_match={row['exact_match_rate']:.4f}, "
            f"arg_validity={row['avg_argument_validity']:.4f}"
        )
    if "routing_summary" in manifest:
        print("hidden_tool_routing:")
        for baseline_name, row in manifest["routing_summary"].items():
            print(
                f"{baseline_name}: "
                f"tool_acc={row['tool_selection_accuracy']:.4f}, "
                f"joint_exact={row['joint_exact_match_rate']:.4f}"
            )


if __name__ == "__main__":
    main()

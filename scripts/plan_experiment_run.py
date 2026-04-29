from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reliaskill.scheduler import plan_experiment_run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dry-run plan a ReliaSkill experiment for one GPU without launching inference.")
    parser.add_argument("--config", type=Path, required=True, help="Experiment YAML/JSON config.")
    parser.add_argument("--gpu_budget_gb", type=float, required=True, help="Available GPU memory budget in GB.")
    parser.add_argument("--output-report", type=Path, default=Path("outputs/reports/run_plan.md"))
    parser.add_argument("--output-csv", type=Path, default=Path("outputs/tables/run_plan.csv"))
    parser.add_argument("--shard-index", type=int, default=None, help="Optional zero-based tool shard index.")
    parser.add_argument("--num-shards", type=int, default=None, help="Optional number of tool shards.")
    parser.add_argument("--strict", action="store_true", help="Treat prompt-token guard warnings as blocking errors.")
    parser.add_argument("--json", action="store_true", help="Print compact JSON summary.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    plan = plan_experiment_run(
        args.config,
        gpu_budget_gb=args.gpu_budget_gb,
        output_report=args.output_report,
        output_csv=args.output_csv,
        shard_index=args.shard_index,
        num_shards=args.num_shards,
        strict=args.strict,
    )
    if args.json:
        print(json.dumps({key: plan[key] for key in ["valid", "num_models", "num_conditions", "num_tools", "num_tasks", "total_remaining_model_calls", "estimated_runtime_hours", "output_report", "output_csv"]}, indent=2))
    else:
        print(f"valid={plan['valid']}")
        print(f"models={plan['num_models']}")
        print(f"conditions={plan['num_conditions']}")
        print(f"tools={plan['num_tools']}")
        print(f"tasks={plan['num_tasks']}")
        print(f"remaining_model_calls={plan['total_remaining_model_calls']}")
        print(f"estimated_token_volume={plan['total_token_volume']}")
        print(f"estimated_runtime_hours={plan['estimated_runtime_hours']}")
        print(f"estimated_disk_usage_gb={plan['estimated_disk_usage_gb']}")
        print(f"run_plan={plan['output_report']}")
        print(f"run_plan_csv={plan['output_csv']}")
        for error in plan["errors"]:
            print(f"error: {error}")
        for warning in plan["warnings"]:
            print(f"warning: {warning}")


if __name__ == "__main__":
    main()

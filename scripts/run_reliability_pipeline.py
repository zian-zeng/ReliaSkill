from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoskill.reliability import run_reliability_pipeline, run_reliability_pipeline_from_config


DEFAULT_TOOLS = Path("data/raw/public_mcp_filesystem_subset.json")
DEFAULT_BEHAVIOR = Path("data/eval/public_mcp_filesystem_reliability.jsonl")
DEFAULT_OUT = Path("outputs/reliability")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run AutoSkill reliability validation, repair, scoring, and deployment gating.")
    parser.add_argument("--config", type=Path, default=None, help="Optional reliability experiment config.")
    parser.add_argument("--tools", type=Path, default=DEFAULT_TOOLS, help="Raw MCP tool JSON file.")
    parser.add_argument("--behavior", type=Path, default=DEFAULT_BEHAVIOR, help="Positive/negative-control behavior JSONL file.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output directory.")
    parser.add_argument("--max-repair-rounds", type=int, default=2, help="Maximum targeted repair rounds.")
    parser.add_argument("--deploy-threshold", type=float, default=70.0, help="Reliability score threshold for deployment.")
    parser.add_argument("--ablation-mode", default=None, choices=[None, "compact", "verbose", "without_when_not", "without_examples"], help="Optional skill ablation mode.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.config:
        manifest = run_reliability_pipeline_from_config(args.config)
    else:
        manifest = run_reliability_pipeline(
            tools_path=args.tools,
            behavior_path=args.behavior,
            output_root=args.out,
            max_repair_rounds=args.max_repair_rounds,
            deploy_threshold=args.deploy_threshold,
            ablation_mode=args.ablation_mode,
        )
    print(f"generator_backend={manifest['generator_backend']}")
    print(f"predictor_backend={manifest['predictor_backend']}")
    for condition, row in manifest["summary"].items():
        print(
            f"{condition}: score={row['avg_score']:.4f}, "
            f"deploy_rate={row['deploy_rate']:.4f}, "
            f"harm={row['avg_harmful_skill_injection_rate']:.4f}"
        )


if __name__ == "__main__":
    main()

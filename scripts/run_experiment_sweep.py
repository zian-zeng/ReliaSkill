from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoskill.sweep import run_experiment_sweep


DEFAULT_OUT = Path("outputs/experiment_sweep")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run or preflight a sweep of AutoSkill experiment configs.")
    parser.add_argument("configs", nargs="+", type=Path, help="One or more experiment config JSON files.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Directory for sweep summary outputs.")
    parser.add_argument("--preflight-only", action="store_true", help="Validate configs without running experiments.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_experiment_sweep(args.configs, output_root=args.out, preflight_only=args.preflight_only)
    for row in result["summary"]["runs"]:
        print(
            f"{row['run_name']}: "
            f"status={row['status']}, "
            f"valid_config={row['valid_config']}, "
            f"generated_skill_exact_match={row['generated_skill_exact_match']}"
        )


if __name__ == "__main__":
    main()

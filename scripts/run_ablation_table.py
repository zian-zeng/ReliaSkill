from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoskill.ablation import run_ablation_table_from_config
from autoskill.config import load_json_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the final ReliaSkill component ablation table.")
    parser.add_argument("--config", type=Path, default=Path("configs/experiments/ablations.yaml"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_json_config(args.config)
    rows = run_ablation_table_from_config(config)
    print(f"ablation_rows={len(rows)}")
    print(f"output_path={config.get('output_path', 'outputs/tables/ablation_results.csv')}")


if __name__ == "__main__":
    main()

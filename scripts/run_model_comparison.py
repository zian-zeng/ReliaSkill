from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoskill.model_compare import run_model_comparison_from_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run low-compute model comparison over reliability pipeline outputs.")
    parser.add_argument("--config", type=Path, default=Path("configs/model_comparison.low_compute.sample.json"))
    parser.add_argument("--preflight-only", action="store_true", help="Validate config and write empty comparison reports without running models.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = run_model_comparison_from_config(args.config, preflight_only=args.preflight_only)
    print(f"preflight_only={manifest['preflight_only']}")
    for row in manifest["summary"]["runs"]:
        print(
            f"{row['run_name']}: status={row['status']} condition={row['selected_condition']} "
            f"score={row.get('avg_score')} harm={row.get('harmful_skill_injection_rate')}"
        )
    print(f"output={manifest.get('output_root', '')}")


if __name__ == "__main__":
    main()

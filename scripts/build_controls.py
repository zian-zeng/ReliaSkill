from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoskill.control_generation import build_controls, load_control_config, summarize_controls, write_controls_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build reproducible positive and adjacent negative controls for ToolIR records.")
    parser.add_argument("--config", type=Path, default=Path("configs/controls/minimum.yaml"), help="Control generation YAML config.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_control_config(args.config)
    controls = build_controls(config)
    outputs = write_controls_outputs(config, controls)
    summary = summarize_controls(controls)
    print(f"tools={summary['tools']}")
    print(f"controls={summary['controls']}")
    print(f"dev_controls={summary['dev_controls']}")
    print(f"test_controls={summary['test_controls']}")
    print(f"min_positive_per_tool={summary['min_positive_per_tool']}")
    print(f"min_negative_per_tool={summary['min_negative_per_tool']}")
    for key, value in outputs.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()

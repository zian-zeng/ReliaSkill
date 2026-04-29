from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reliaskill.stress_tests.corrupt_skills import build_stress_test_inventory, load_tools_as_toolir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build diagnostic corrupted-skill stress-test artifacts.")
    parser.add_argument("--tools", default="data/processed_toolir/tools.jsonl")
    parser.add_argument("--output", default="data/stress_skills")
    parser.add_argument("--inventory", default="outputs/tables/stress_test_inventory.csv")
    parser.add_argument("--detection", default="outputs/tables/stress_test_detection_results.csv")
    parser.add_argument("--dev-controls", default="data/controls/dev.jsonl")
    parser.add_argument("--max-tools", type=int, default=None)
    parser.add_argument("--conditions", nargs="*", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tools = load_tools_as_toolir(args.tools, limit=args.max_tools)
    rows = build_stress_test_inventory(
        tools,
        output_root=args.output,
        inventory_path=args.inventory,
        detection_path=args.detection,
        max_tools=args.max_tools,
        condition_filter=args.conditions,
        dev_controls_path=args.dev_controls,
    )
    print(f"tools={len(tools)}")
    print(f"stress_variants={len(rows)}")
    print(f"stress_skills={args.output}")
    print(f"inventory={args.inventory}")
    print(f"detection={args.detection}")


if __name__ == "__main__":
    main()

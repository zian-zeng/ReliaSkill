from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reliaskill.distractors import (
    build_routing_examples,
    load_controls,
    load_distractor_config,
    load_tool_profiles,
    summarize_distractor_examples,
    write_distractor_stats,
    write_routing_examples,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build hard distractor inventories for hidden-tool routing experiments.")
    parser.add_argument("--tools", type=Path, default=Path("data/processed_toolir/tools.jsonl"), help="ToolIR JSONL path.")
    parser.add_argument("--controls", type=Path, default=Path("data/controls/test.jsonl"), help="Control JSONL path.")
    parser.add_argument("--output", type=Path, default=Path("data/routing/test_routing.jsonl"), help="Routing benchmark JSONL output.")
    parser.add_argument("--config", type=Path, default=Path("configs/routing/distractor_inventory.yaml"), help="Distractor inventory YAML config.")
    parser.add_argument("--candidate-set-sizes", type=int, nargs="*", default=None, help="Override candidate set sizes, e.g. 4 8 16 32.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_distractor_config(args.config)
    if args.candidate_set_sizes:
        config["candidate_set_sizes"] = args.candidate_set_sizes

    tools = load_tool_profiles(args.tools)
    controls = load_controls(args.controls)
    examples = build_routing_examples(tools, controls, config)
    summary = summarize_distractor_examples(examples, tools)
    write_routing_examples(args.output, examples)
    stats_path = Path(str((config.get("outputs") or {}).get("stats") or "outputs/tables/distractor_stats.csv"))
    write_distractor_stats(stats_path, summary)

    print(f"tools={len(tools)}")
    print(f"controls={len(controls)}")
    print(f"routing_examples={len(examples)}")
    print(f"avg_candidates={summary['avg_candidates']}")
    print(f"easy_count={summary['easy_count']}")
    print(f"medium_count={summary['medium_count']}")
    print(f"hard_count={summary['hard_count']}")
    print(f"adversarial_count={summary['adversarial_count']}")
    print(f"output={args.output}")
    print(f"stats={stats_path}")


if __name__ == "__main__":
    main()

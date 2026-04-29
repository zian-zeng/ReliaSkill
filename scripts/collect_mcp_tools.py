from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoskill.tool_collection import collect_tool_records, load_collection_config, summarize_dataset, write_collection_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect local MCP/tool schemas into normalized ReliaSkill dataset artifacts.")
    parser.add_argument("--config", type=Path, default=Path("configs/data/minimum.yaml"), help="Collection YAML config.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_collection_config(args.config)
    raw_records = collect_tool_records(config)
    outputs = write_collection_outputs(config, raw_records)
    summary = summarize_dataset(raw_records)
    print(f"tools={summary['total_tools']}")
    print(f"sources={summary['source_count']}")
    print(f"domains={summary['domain_count']}")
    print(f"servers={summary['server_count']}")
    for key, value in outputs.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()

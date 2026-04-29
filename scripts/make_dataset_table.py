from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoskill.tool_collection import load_jsonl, summarize_dataset, write_dataset_card, write_dataset_stats_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Regenerate dataset statistics from normalized raw MCP JSONL.")
    parser.add_argument("--in", dest="input_path", type=Path, default=Path("data/raw_mcp/tools.jsonl"), help="Raw MCP JSONL input.")
    parser.add_argument("--out", dest="stats_path", type=Path, default=Path("outputs/tables/dataset_stats.csv"), help="CSV table output.")
    parser.add_argument("--card-out", dest="card_path", type=Path, default=Path("outputs/reports/dataset_card.md"), help="Dataset card markdown output.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw_records = load_jsonl(args.input_path)
    write_dataset_stats_csv(args.stats_path, raw_records)
    write_dataset_card(args.card_path, raw_records)
    summary = summarize_dataset(raw_records)
    print(f"tools={summary['total_tools']}")
    print(f"sources={summary['source_count']}")
    print(f"domains={summary['domain_count']}")
    print(f"stats={args.stats_path}")
    print(f"dataset_card={args.card_path}")


if __name__ == "__main__":
    main()

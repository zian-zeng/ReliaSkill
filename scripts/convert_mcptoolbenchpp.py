from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoskill.conversion import write_json, write_jsonl
from autoskill.mcptoolbench import convert_mcptoolbench_records, load_mcptoolbench_records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert MCPToolBench++ to AutoSkill raw-tool and behavior benchmark files.")
    parser.add_argument("--input", type=Path, default=Path("data/external/mcptoolbenchpp"), help="Downloaded MCPToolBench++ directory or JSON/JSONL file.")
    parser.add_argument("--tools-out", type=Path, default=Path("data/raw/mcptoolbenchpp_tools.json"), help="Output canonical MCP tools JSON.")
    parser.add_argument("--behavior-out", type=Path, default=Path("data/eval/mcptoolbenchpp_reliability.jsonl"), help="Output AutoSkill behavior JSONL.")
    parser.add_argument("--category", action="append", default=[], help="Optional category filter. May be provided multiple times.")
    parser.add_argument("--limit", type=int, default=None, help="Optional maximum source records to convert.")
    parser.add_argument("--negatives-per-positive", type=int, default=3, help="Maximum adjacent negative controls per positive call.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = load_mcptoolbench_records(args.input, categories=args.category, limit=args.limit)
    tools, tasks = convert_mcptoolbench_records(records, negatives_per_positive=args.negatives_per_positive)
    write_json(args.tools_out, tools)
    write_jsonl(args.behavior_out, tasks)
    positives = sum(1 for item in tasks if item.get("should_trigger", True))
    negatives = len(tasks) - positives
    print(f"source_records={len(records)}")
    print(f"tools={len(tools)}")
    print(f"positive_cases={positives}")
    print(f"negative_controls={negatives}")
    print(f"tools_output={args.tools_out}")
    print(f"behavior_output={args.behavior_out}")


if __name__ == "__main__":
    main()

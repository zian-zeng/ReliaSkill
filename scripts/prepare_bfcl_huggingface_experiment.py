from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoskill.conversion import write_json, write_jsonl
from autoskill.external_ingest import (
    build_bfcl_routing_tasks,
    build_bfcl_tool_records,
    load_loose_json_records,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a BFCL Hugging Face routing-style experiment from downloaded BFCL files.")
    parser.add_argument(
        "--api-data",
        type=Path,
        default=Path("data/external/bfcl/data/api/huggingface_api.jsonl"),
        help="Path to BFCL Hugging Face API metadata JSONL.",
    )
    parser.add_argument(
        "--train",
        type=Path,
        default=Path("data/external/bfcl/data/apibench/huggingface_train.json"),
        help="Path to BFCL Hugging Face train slice.",
    )
    parser.add_argument(
        "--eval",
        type=Path,
        default=Path("data/external/bfcl/data/apibench/huggingface_eval.json"),
        help="Path to BFCL Hugging Face eval slice.",
    )
    parser.add_argument(
        "--tools-out",
        type=Path,
        default=Path("data/raw/bfcl_huggingface_tools.json"),
        help="Output path for generated BFCL pseudo-tool definitions.",
    )
    parser.add_argument(
        "--train-out",
        type=Path,
        default=Path("data/eval/bfcl_huggingface_train_routing.jsonl"),
        help="Output path for generated BFCL train routing tasks.",
    )
    parser.add_argument(
        "--eval-out",
        type=Path,
        default=Path("data/eval/bfcl_huggingface_eval_routing.jsonl"),
        help="Output path for generated BFCL eval routing tasks.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    api_records = load_loose_json_records(args.api_data)
    train_records = load_loose_json_records(args.train)
    eval_records = load_loose_json_records(args.eval)

    all_records = api_records + train_records + eval_records
    tools = build_bfcl_tool_records(all_records)
    train_tasks = build_bfcl_routing_tasks(train_records, split="train")
    eval_tasks = build_bfcl_routing_tasks(eval_records, split="test")

    write_json(args.tools_out, tools)
    write_jsonl(args.train_out, train_tasks)
    write_jsonl(args.eval_out, eval_tasks)

    print(f"wrote_tools={len(tools)}")
    print(f"wrote_train_tasks={len(train_tasks)}")
    print(f"wrote_eval_tasks={len(eval_tasks)}")
    print(f"tools_output={args.tools_out}")
    print(f"train_output={args.train_out}")
    print(f"eval_output={args.eval_out}")


if __name__ == "__main__":
    main()

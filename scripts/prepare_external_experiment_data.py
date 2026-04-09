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
    harvest_reference_mcp_servers,
    load_loose_json_records,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare external MCP and BFCL experiment artifacts.")
    parser.add_argument(
        "--mcp-repo",
        type=Path,
        default=Path("data/external/modelcontextprotocol-servers"),
        help="Path to the downloaded modelcontextprotocol/servers repository.",
    )
    parser.add_argument(
        "--bfcl-root",
        type=Path,
        default=Path("data/external/bfcl/data"),
        help="Path to the downloaded BFCL data directory.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    harvested_tools = harvest_reference_mcp_servers(args.mcp_repo)
    harvested_tools_out = Path("data/raw/harvested_mcp_reference_servers.json")
    write_json(harvested_tools_out, harvested_tools)

    api_records = load_loose_json_records(args.bfcl_root / "api" / "huggingface_api.jsonl")
    train_records = load_loose_json_records(args.bfcl_root / "apibench" / "huggingface_train.json")
    eval_records = load_loose_json_records(args.bfcl_root / "apibench" / "huggingface_eval.json")
    bfcl_tools = build_bfcl_tool_records(api_records + train_records + eval_records)
    bfcl_train = build_bfcl_routing_tasks(train_records, split="train")
    bfcl_eval = build_bfcl_routing_tasks(eval_records, split="test")

    bfcl_tools_out = Path("data/raw/bfcl_huggingface_tools.json")
    bfcl_train_out = Path("data/eval/bfcl_huggingface_train_routing.jsonl")
    bfcl_eval_out = Path("data/eval/bfcl_huggingface_eval_routing.jsonl")
    write_json(bfcl_tools_out, bfcl_tools)
    write_jsonl(bfcl_train_out, bfcl_train)
    write_jsonl(bfcl_eval_out, bfcl_eval)

    print(f"harvested_mcp_tools={len(harvested_tools)}")
    print(f"bfcl_tools={len(bfcl_tools)}")
    print(f"bfcl_train_tasks={len(bfcl_train)}")
    print(f"bfcl_eval_tasks={len(bfcl_eval)}")
    print(f"mcp_output={harvested_tools_out}")
    print(f"bfcl_tools_output={bfcl_tools_out}")
    print(f"bfcl_train_output={bfcl_train_out}")
    print(f"bfcl_eval_output={bfcl_eval_out}")


if __name__ == "__main__":
    main()

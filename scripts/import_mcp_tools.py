from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoskill.conversion import canonicalize_mcp_tool_records, load_json_or_jsonl, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize exported MCP tool definitions into AutoSkill's raw-tool JSON format."
    )
    parser.add_argument("--in", dest="input_path", type=Path, required=True, help="Input JSON or JSONL file.")
    parser.add_argument("--out", dest="output_path", type=Path, required=True, help="Output JSON path.")
    parser.add_argument("--server-name", dest="server_name", type=str, default=None, help="Optional default server name.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw_records = load_json_or_jsonl(args.input_path)
    canonical = canonicalize_mcp_tool_records(raw_records, default_server_name=args.server_name)
    write_json(args.output_path, canonical)
    print(f"wrote_tools={len(canonical)}")
    print(f"output={args.output_path}")


if __name__ == "__main__":
    main()

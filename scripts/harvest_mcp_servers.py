from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoskill.conversion import write_json
from autoskill.external_ingest import harvest_reference_mcp_servers


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Harvest MCP tool definitions from a downloaded modelcontextprotocol/servers repo.")
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path("data/external/modelcontextprotocol-servers"),
        help="Path to the downloaded modelcontextprotocol/servers repository.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/raw/harvested_mcp_reference_servers.json"),
        help="Output path for harvested tool JSON.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = harvest_reference_mcp_servers(args.repo)
    write_json(args.out, records)
    print(f"wrote_tools={len(records)}")
    print(f"output={args.out}")


if __name__ == "__main__":
    main()

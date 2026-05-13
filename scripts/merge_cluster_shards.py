from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reliaskill.cluster import merge_cluster_shards


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge ReliaSkill cluster shard outputs and regenerate metric tables.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--output-tables", type=Path, default=None)
    parser.add_argument("--allow-duplicates", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = merge_cluster_shards(
        args.config,
        output_root=args.output_root,
        output_tables=args.output_tables,
        strict=not args.allow_duplicates,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

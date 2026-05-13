from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reliaskill.cluster import parse_model_filter, run_cluster_shard


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one ReliaSkill cluster shard on one GPU.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--shard-index", type=int, required=True)
    parser.add_argument("--num-shards", type=int, required=True)
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--shared-packages", type=Path, default=None)
    parser.add_argument("--models", default="all", help="Comma-separated model names/slugs/config paths, or 'all'.")
    parser.add_argument("--skip-routing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_cluster_shard(
        args.config,
        shard_index=args.shard_index,
        num_shards=args.num_shards,
        output_root=args.output_root,
        shared_packages=args.shared_packages,
        models=parse_model_filter(args.models),
        skip_routing=args.skip_routing,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

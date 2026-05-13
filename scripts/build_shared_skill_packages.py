from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reliaskill.cluster import build_shared_skill_packages


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build read-only shared skill packages for cluster evaluation.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = build_shared_skill_packages(args.config, output_root=args.output_root, force=args.force)
    if args.json:
        print(json.dumps(manifest, indent=2))
    else:
        print(f"shared_package_root={manifest['shared_package_root']}")
        print(f"num_tools={manifest['num_tools']}")
        print(f"conditions={len(manifest['conditions'])}")
        print(f"reliability_conditions={','.join(manifest['reliability_conditions'])}")


if __name__ == "__main__":
    main()

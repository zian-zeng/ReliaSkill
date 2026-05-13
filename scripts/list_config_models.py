from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoskill.config import load_json_config
from reliaskill.cluster import _load_config_models, slugify


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List configured ReliaSkill evaluator model filters.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--format", choices=["slug", "name"], default="slug")
    parser.add_argument("--models", default="all", help="Optional comma-separated model slugs or names to keep.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = load_json_config(args.config)
    models = _load_config_models(config, base_dir=args.config.resolve().parent)
    requested = {item.strip() for item in str(args.models).split(",") if item.strip() and item.strip() != "all"}
    for model in models:
        model_slug = slugify(model.model_name)
        if requested and model.model_name not in requested and model_slug not in requested and model.config_path not in requested:
            continue
        print(model_slug if args.format == "slug" else model.model_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

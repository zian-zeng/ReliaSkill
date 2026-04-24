from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download MCPToolBench++ from Hugging Face.")
    parser.add_argument("--repo-id", default="MCPToolBench/MCPToolBenchPP", help="Hugging Face dataset repository id.")
    parser.add_argument("--out", type=Path, default=Path("data/external/mcptoolbenchpp"), help="Local output directory.")
    parser.add_argument("--revision", default=None, help="Optional dataset revision.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise SystemExit("Install `huggingface_hub` to download MCPToolBench++: pip install huggingface_hub") from exc

    args.out.mkdir(parents=True, exist_ok=True)
    local_dir = snapshot_download(
        repo_id=args.repo_id,
        repo_type="dataset",
        revision=args.revision,
        local_dir=str(args.out),
        allow_patterns=["*.json", "*.jsonl", "README.md", "data/**"],
    )
    print(f"downloaded_repo={args.repo_id}")
    print(f"output={Path(local_dir).resolve()}")


if __name__ == "__main__":
    main()

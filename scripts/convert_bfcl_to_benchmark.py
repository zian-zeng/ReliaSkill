from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoskill.conversion import convert_benchmark_file_to_canonical_records, write_jsonl


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a BFCL-style JSON or JSONL file into AutoSkill's canonical benchmark JSONL format."
    )
    parser.add_argument("--in", dest="input_path", type=Path, required=True, help="Input BFCL-style file.")
    parser.add_argument("--out", dest="output_path", type=Path, required=True, help="Output canonical JSONL path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = convert_benchmark_file_to_canonical_records(args.input_path)
    write_jsonl(args.output_path, records)
    print(f"wrote_records={len(records)}")
    print(f"output={args.output_path}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reliaskill.analysis.comparisons import extract_scientific_comparisons, write_scientific_comparison_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract cautious scientific comparison summaries from saved ReliaSkill result tables.")
    parser.add_argument("--tables-dir", default="outputs/tables", help="Directory containing saved result CSV tables.")
    parser.add_argument("--output-json", default="outputs/reports/scientific_comparison_summary.json")
    parser.add_argument("--output-md", default="outputs/reports/scientific_comparison_summary.md")
    parser.add_argument("--output-csv", default="outputs/tables/key_comparisons.csv")
    parser.add_argument("--min-denominator", type=int, default=20)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = extract_scientific_comparisons(
        tables_dir=args.tables_dir,
        min_denominator=args.min_denominator,
    )
    paths = write_scientific_comparison_outputs(
        summary,
        output_json=args.output_json,
        output_md=args.output_md,
        output_csv=args.output_csv,
    )
    print(f"comparisons={summary['comparison_count']}")
    for category, count in sorted(summary["claim_support_counts"].items()):
        print(f"{category}={count}")
    print(f"summary_json={paths['json']}")
    print(f"summary_md={paths['markdown']}")
    print(f"key_comparisons={paths['csv']}")


if __name__ == "__main__":
    main()

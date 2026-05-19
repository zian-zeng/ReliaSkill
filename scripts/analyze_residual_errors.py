from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reliaskill.analysis.residuals import analyze_residuals, write_residual_analysis  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze paired residual disagreements between a baseline and ReliaSkill.")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--baseline", default="raw_docs_full")
    parser.add_argument("--method", default="reliaskill_v1")
    parser.add_argument("--no-routing", action="store_true")
    parser.add_argument("--output-csv", type=Path, default=Path("outputs/tables/residual_error_analysis.csv"))
    parser.add_argument("--output-md", type=Path, default=Path("outputs/reports/residual_error_analysis.md"))
    parser.add_argument("--output-json", type=Path, default=Path("outputs/reports/residual_error_analysis.json"))
    args = parser.parse_args()

    report = analyze_residuals(
        args.run_dir,
        baseline=args.baseline,
        method=args.method,
        include_routing=not args.no_routing,
    )
    paths = write_residual_analysis(report, output_csv=args.output_csv, output_md=args.output_md, output_json=args.output_json)
    print(json.dumps({key: report[key] for key in ("paired_disagreements", "baseline_only_correct", "method_only_correct")}, sort_keys=True))
    print(f"csv={paths['csv']}")
    print(f"markdown={paths['markdown']}")
    print(f"json={paths['json']}")


if __name__ == "__main__":
    main()

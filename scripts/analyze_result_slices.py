from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reliaskill.analysis.slices import analyze_result_slices, write_slice_analysis_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze saved ReliaSkill logs by reviewer-facing slices.")
    parser.add_argument("--run", default="outputs/sample_run", help="Directory containing saved prediction/routing/behavior logs.")
    parser.add_argument("--tools", default="data/processed_toolir/tools.jsonl", help="Processed ToolIR JSONL metadata.")
    parser.add_argument(
        "--controls",
        nargs="*",
        default=["data/controls/dev.jsonl", "data/controls/test.jsonl"],
        help="Control JSONL files used only for slice metadata.",
    )
    parser.add_argument("--routing", default="data/routing/test_routing.jsonl", help="Routing JSONL metadata, if available.")
    parser.add_argument(
        "--compactness",
        default="outputs/skill_compactness_records.jsonl",
        help="Optional per-skill compactness records.",
    )
    parser.add_argument("--out", default="outputs/tables", help="Output directory for slice CSV tables.")
    parser.add_argument("--report", default="outputs/reports/slice_analysis_summary.md", help="Markdown summary path.")
    parser.add_argument("--min-slice-size", type=int, default=5, help="Mark slices below this denominator as suppressed.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    analysis = analyze_result_slices(
        run_dir=args.run,
        tools_path=args.tools,
        controls_paths=args.controls,
        routing_path=args.routing,
        compactness_path=args.compactness,
        min_slice_size=args.min_slice_size,
    )
    paths = write_slice_analysis_outputs(analysis, output_dir=args.out, report_path=args.report)
    print(f"Analyzed {analysis['num_records']} saved records from {Path(args.run)}.")
    for name, path in paths.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()

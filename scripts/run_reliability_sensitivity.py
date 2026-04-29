from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoskill.reliability import run_reliability_pipeline
from autoskill.reliability_score import (
    load_reliability_records,
    threshold_sweep_rows,
    weight_sensitivity_rows,
    write_calibration_pdf,
    write_score_definition,
    write_threshold_sensitivity_csv,
    write_weight_sensitivity_csv,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate reliability threshold and weight sensitivity artifacts.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("outputs/reliability_heuristic_sample"),
        help="Directory or reliability_records.jsonl file. Regenerated with the heuristic sample if absent or stale.",
    )
    parser.add_argument("--out-tables", type=Path, default=Path("outputs/tables"), help="Output directory for CSV tables.")
    parser.add_argument("--out-figures", type=Path, default=Path("outputs/figures"), help="Output directory for figures.")
    parser.add_argument("--out-reports", type=Path, default=Path("outputs/reports"), help="Output directory for reports.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = load_reliability_records(args.input)
    if not _has_component_scores(records):
        run_reliability_pipeline(
            tools_path="data/raw/public_mcp_filesystem_subset.json",
            behavior_path="data/eval/public_mcp_filesystem_reliability.jsonl",
            output_root=args.input if args.input.suffix == "" else args.input.parent,
            generator_config={"type": "heuristic"},
            predictor_config={"type": "heuristic"},
            deploy_threshold=85.0,
        )
        records = load_reliability_records(args.input)

    threshold_rows = threshold_sweep_rows(records)
    weight_rows = weight_sensitivity_rows(records)
    args.out_tables.mkdir(parents=True, exist_ok=True)
    args.out_figures.mkdir(parents=True, exist_ok=True)
    args.out_reports.mkdir(parents=True, exist_ok=True)

    threshold_path = args.out_tables / "reliability_threshold_sensitivity.csv"
    weight_path = args.out_tables / "reliability_weight_sensitivity.csv"
    figure_path = args.out_figures / "reliability_calibration.pdf"
    definition_path = args.out_reports / "reliability_score_definition.md"

    write_threshold_sensitivity_csv(threshold_path, threshold_rows)
    write_weight_sensitivity_csv(weight_path, weight_rows)
    write_calibration_pdf(figure_path, threshold_rows)
    write_score_definition(definition_path)

    print(f"records={len(records)}")
    print(f"threshold_rows={len(threshold_rows)}")
    print(f"weight_sensitivity_rows={len(weight_rows)}")
    print(f"threshold_sensitivity={threshold_path}")
    print(f"weight_sensitivity={weight_path}")
    print(f"calibration_pdf={figure_path}")
    print(f"score_definition={definition_path}")


def _has_component_scores(records) -> bool:
    if not records:
        return False
    for record in records:
        score = record.get("reliability_score")
        if not isinstance(score, dict):
            return False
        features = score.get("features")
        if not isinstance(features, dict) or not isinstance(features.get("components"), dict):
            return False
    return True


if __name__ == "__main__":
    main()

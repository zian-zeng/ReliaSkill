from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reliaskill.converters.api_bank_converter import convert_api_bank
from reliaskill.converters.bfcl_converter import convert_bfcl
from reliaskill.converters.common import (
    build_markdown_report,
    mark_multi_tool_ambiguity,
    stable_hash,
    summarize_records,
    write_csv,
    write_jsonl,
)
from reliaskill.converters.toolbench_converter import convert_toolbench


CONVERTERS = {
    "bfcl": convert_bfcl,
    "api_bank": convert_api_bank,
    "toolbench": convert_toolbench,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert external function-calling benchmarks into ReliaSkill MCP-like artifacts.")
    parser.add_argument("--input", type=Path, default=Path("data/external"), help="Directory containing external benchmark data.")
    parser.add_argument("--output", type=Path, default=Path("data/converted_external"), help="Output directory for converted JSONL artifacts.")
    parser.add_argument(
        "--sources",
        nargs="+",
        default=["bfcl", "api_bank", "toolbench"],
        choices=sorted(CONVERTERS),
        help="External benchmark sources to convert.",
    )
    parser.add_argument("--strict", action="store_true", help="Fail if a requested source is missing or malformed.")
    parser.add_argument("--stats-out", type=Path, default=Path("outputs/tables/external_conversion_stats.csv"))
    parser.add_argument("--report-out", type=Path, default=Path("outputs/reports/external_conversion_report.md"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    all_records: List[Dict[str, Any]] = []
    skipped: Dict[str, Counter[str]] = {}
    warnings: List[str] = []

    for source in args.sources:
        records, source_skipped, source_warnings = CONVERTERS[source](args.input, strict=args.strict)
        all_records.extend(records)
        skipped[source] = source_skipped
        warnings.extend(source_warnings)
        print(f"{source}_records={len(records)}")
        if source_warnings:
            for warning in source_warnings:
                print(f"warning={warning}")

    mark_multi_tool_ambiguity(all_records)
    args.output.mkdir(parents=True, exist_ok=True)

    unique_tools = _unique_by_tool_id(all_records)
    controls = [record["positive_control"] for record in all_records if isinstance(record.get("positive_control"), dict)]

    write_jsonl(args.output / "conversion_records.jsonl", all_records)
    write_jsonl(args.output / "raw_tools.jsonl", [record["mcp_tool_schema"] for record in unique_tools])
    write_jsonl(args.output / "toolir.jsonl", [record["toolir"] for record in unique_tools])
    write_jsonl(args.output / "positive_controls.jsonl", controls)
    for source in args.sources:
        source_records = [record for record in all_records if record.get("source_type") == source]
        write_jsonl(args.output / f"{source}_records.jsonl", source_records)

    rows = summarize_records(all_records, skipped, warnings)
    write_csv(args.stats_out, rows)
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(build_markdown_report(rows, warnings, args.output), encoding="utf-8")

    print(f"tools_converted={len(unique_tools)}")
    print(f"examples_converted={len(controls)}")
    print(f"records_converted={len(all_records)}")
    print(f"skipped={sum(sum(counter.values()) for counter in skipped.values())}")
    print(f"conversion_records={args.output / 'conversion_records.jsonl'}")
    print(f"raw_tools={args.output / 'raw_tools.jsonl'}")
    print(f"toolir={args.output / 'toolir.jsonl'}")
    print(f"positive_controls={args.output / 'positive_controls.jsonl'}")
    print(f"stats={args.stats_out}")
    print(f"report={args.report_out}")


def _unique_by_tool_id(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    selected: Dict[str, Dict[str, Any]] = {}
    for record in records:
        tool_id = str(record.get("tool_id") or "")
        if not tool_id:
            continue
        current = selected.get(tool_id)
        if current is None:
            selected[tool_id] = record
            continue
        current_schema_hash = stable_hash(current.get("normalized_schema") or {})
        new_schema_hash = stable_hash(record.get("normalized_schema") or {})
        if current_schema_hash == new_schema_hash and record.get("positive_control") and not current.get("positive_control"):
            selected[tool_id] = record
    return [selected[key] for key in sorted(selected)]


if __name__ == "__main__":
    main()

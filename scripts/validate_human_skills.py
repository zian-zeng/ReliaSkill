from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reliaskill.human_skill_condition import validate_human_skill_directory


FIELDS = [
    "tool_id",
    "valid",
    "skill_token_count",
    "token_budget",
    "structural_valid",
    "compactness_valid",
    "schema_faithfulness_valid",
    "metadata_valid",
    "failure_codes",
    "failure_messages",
    "skill_path",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate human-written ReliaSkill artifacts without running inference.")
    parser.add_argument("--skills", default="data/human_skills/skills")
    parser.add_argument("--tools", default="data/processed_toolir/tools.jsonl")
    parser.add_argument("--output", default="outputs/tables/human_skill_validation.csv")
    parser.add_argument("--report", default="outputs/reports/human_skill_validation_report.md")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any present human skill is invalid.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validations = validate_human_skill_directory(args.skills, args.tools)
    write_csv(args.output, [item.model_dump() for item in validations])
    write_report(args.report, validations)
    invalid = [item for item in validations if not item.valid]
    print(f"human_skills={len(validations)}")
    print(f"invalid={len(invalid)}")
    print(f"validation={args.output}")
    if args.strict and invalid:
        raise SystemExit(1)


def write_csv(path: str | Path, rows: list[dict]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})


def write_report(path: str | Path, validations) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    invalid = [item for item in validations if not item.valid]
    lines = [
        "# Human Skill Validation Report",
        "",
        f"- Human skills found: `{len(validations)}`",
        f"- Valid skills: `{len(validations) - len(invalid)}`",
        f"- Invalid skills: `{len(invalid)}`",
        "",
    ]
    if invalid:
        lines.append("## Failures")
        for item in invalid:
            lines.append(f"- `{item.tool_id}`: {', '.join(item.failure_codes) or 'unknown_failure'}")
    else:
        lines.append("No validation failures were found for present human skills.")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

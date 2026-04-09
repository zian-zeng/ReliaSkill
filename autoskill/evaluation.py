from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable

from autoskill.ir import GeneratedSkill, ValidationReport


def _count_semantic_entries(skill: GeneratedSkill) -> int:
    total = 0
    for value in skill.semantic_hints.values():
        if isinstance(value, dict):
            total += len(value)
        elif isinstance(value, list):
            total += len(value)
        else:
            total += 1
    return total


def summarize_records(records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    grouped: Dict[str, list[Dict[str, Any]]] = defaultdict(list)

    for record in records:
        grouped[record["baseline_name"]].append(record)

    for baseline_name, items in grouped.items():
        issue_counter = Counter()
        valid_count = 0
        total_examples = 0
        total_template_fields = 0
        total_semantic_entries = 0

        for item in items:
            skill: GeneratedSkill = item["skill"]
            report: ValidationReport = item["report"]
            if report.valid:
                valid_count += 1
            issue_counter.update(issue.code for issue in report.issues)
            total_examples += len(skill.examples)
            total_template_fields += len(skill.argument_template)
            total_semantic_entries += _count_semantic_entries(skill)

        total = len(items)
        summary[baseline_name] = {
            "total_tools": total,
            "valid_packages": valid_count,
            "valid_rate": round(valid_count / total, 4) if total else 0.0,
            "avg_examples": round(total_examples / total, 2) if total else 0.0,
            "avg_template_fields": round(total_template_fields / total, 2) if total else 0.0,
            "avg_semantic_hint_entries": round(total_semantic_entries / total, 2) if total else 0.0,
            "issue_breakdown": dict(sorted(issue_counter.items())),
        }

    return summary


def summarize_records_by_tool(records: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    summary: Dict[str, Dict[str, Any]] = {}
    grouped: Dict[str, Dict[str, list[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))

    for record in records:
        grouped[record["tool_name"]][record["baseline_name"]].append(record)

    for tool_name, by_baseline in grouped.items():
        summary[tool_name] = {}
        for baseline_name, items in by_baseline.items():
            issue_counter = Counter()
            valid_count = 0
            total_examples = 0
            total_template_fields = 0
            total_semantic_entries = 0

            for item in items:
                skill: GeneratedSkill = item["skill"]
                report: ValidationReport = item["report"]
                if report.valid:
                    valid_count += 1
                issue_counter.update(issue.code for issue in report.issues)
                total_examples += len(skill.examples)
                total_template_fields += len(skill.argument_template)
                total_semantic_entries += _count_semantic_entries(skill)

            total = len(items)
            summary[tool_name][baseline_name] = {
                "total_tools": total,
                "valid_packages": valid_count,
                "valid_rate": round(valid_count / total, 4) if total else 0.0,
                "avg_examples": round(total_examples / total, 2) if total else 0.0,
                "avg_template_fields": round(total_template_fields / total, 2) if total else 0.0,
                "avg_semantic_hint_entries": round(total_semantic_entries / total, 2) if total else 0.0,
                "issue_breakdown": dict(sorted(issue_counter.items())),
            }

    return summary


def write_summary(output_path: str | Path, summary: Dict[str, Any]) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

from __future__ import annotations

import json
from pathlib import Path

from autoskill.ir import BehaviorReport, GeneratedSkill, ReliabilityScore, RepairReport, ToolIR, ValidationReport


def _format_argument_lines(tool: ToolIR) -> list[str]:
    lines = []
    for arg in tool.arguments:
        pieces = [f"`{arg.name}`", arg.type]
        pieces.append("required" if arg.required else "optional")
        if arg.enum:
            pieces.append(f"enum={arg.enum}")
        if arg.default is not None:
            pieces.append(f"default={arg.default!r}")
        if arg.nullable:
            pieces.append("nullable")
        if arg.format:
            pieces.append(f"format={arg.format}")
        description = arg.description or "No description provided."
        lines.append(f"- {', '.join(str(piece) for piece in pieces)}: {description}")
    return lines


def write_skill_package(
    output_dir: str | Path,
    tool: ToolIR,
    skill: GeneratedSkill,
    report: ValidationReport,
    behavior_report: BehaviorReport | None = None,
    reliability_score: ReliabilityScore | None = None,
    repair_report: RepairReport | None = None,
) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    skill_md = out / "SKILL.md"
    schema_json = out / "schema.normalized.json"
    examples_jsonl = out / "examples.jsonl"
    validation_report_json = out / "validation_report.json"
    behavior_report_json = out / "behavior_report.json"
    reliability_score_json = out / "reliability_score.json"
    repair_report_json = out / "repair_report.json"
    metadata_json = out / "metadata.json"

    with skill_md.open("w", encoding="utf-8") as f:
        f.write(f"# {tool.tool_name}\n\n")
        f.write(f"**Condition:** `{skill.baseline_name}`\n\n")

        f.write("## Summary\n")
        f.write(skill.skill_summary.strip() + "\n\n")

        f.write("## When to use\n")
        for line in skill.when_to_use:
            f.write(f"- {line}\n")
        f.write("\n")

        f.write("## When not to use\n")
        for line in skill.when_not_to_use:
            f.write(f"- {line}\n")
        f.write("\n")

        f.write("## Arguments\n")
        for line in _format_argument_lines(tool):
            f.write(line + "\n")
        if not tool.arguments:
            f.write("- This tool does not expose structured input arguments.\n")
        f.write("\n")

        f.write("## Argument template\n")
        if skill.argument_template:
            f.write("```json\n")
            f.write(json.dumps(skill.argument_template, indent=2, ensure_ascii=False))
            f.write("\n```\n\n")
        else:
            f.write("This condition does not add a normalized argument template beyond the raw schema.\n\n")

        f.write("## Semantic hints\n")
        if skill.semantic_hints:
            f.write("```json\n")
            f.write(json.dumps(skill.semantic_hints, indent=2, ensure_ascii=False))
            f.write("\n```\n\n")
        else:
            f.write("No explicit semantic hints for this condition.\n\n")

        f.write("## Examples\n")
        if skill.examples:
            for example in skill.examples:
                f.write(f"- {example.get('scenario', 'Example')}\n")
                f.write("```json\n")
                f.write(json.dumps(example.get("arguments", {}), indent=2, ensure_ascii=False))
                f.write("\n```\n")
        else:
            f.write("No synthesized examples for this condition.\n")

    with schema_json.open("w", encoding="utf-8") as f:
        json.dump(tool.model_dump(), f, indent=2, ensure_ascii=False)

    with examples_jsonl.open("w", encoding="utf-8") as f:
        for ex in skill.examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    with validation_report_json.open("w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, indent=2, ensure_ascii=False)

    if behavior_report is not None:
        with behavior_report_json.open("w", encoding="utf-8") as f:
            json.dump(behavior_report.model_dump(), f, indent=2, ensure_ascii=False)

    if reliability_score is not None:
        with reliability_score_json.open("w", encoding="utf-8") as f:
            json.dump(reliability_score.model_dump(), f, indent=2, ensure_ascii=False)

    if repair_report is not None:
        with repair_report_json.open("w", encoding="utf-8") as f:
            json.dump(repair_report.model_dump(), f, indent=2, ensure_ascii=False)

    metadata = {
        "tool_name": tool.tool_name,
        "baseline_name": skill.baseline_name,
        "source_pointer": tool.source_pointer,
        "valid": report.valid,
        "issues": [issue.model_dump() for issue in report.issues],
        "semantic_hints": skill.semantic_hints,
        "method_trace": skill.method_trace,
        "skill_metadata": skill.metadata,
        "doc_completeness": tool.doc_completeness,
        "schema_complexity": tool.schema_complexity,
        "ambiguity_flags": tool.ambiguity_flags,
        "side_effect_hints": tool.side_effect_hints,
        "safety_hints": tool.safety_hints,
        "behavior_metrics": behavior_report.metrics if behavior_report is not None else None,
        "reliability_score": reliability_score.model_dump() if reliability_score is not None else None,
        "repair_report": repair_report.model_dump() if repair_report is not None else None,
    }
    with metadata_json.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

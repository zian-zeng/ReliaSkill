from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reliaskill.human_skill_condition import index_tool_records, load_tool_records, tool_id_for_record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build label-free authoring packets for human-written skill artifacts.")
    parser.add_argument("--tools", default="data/processed_toolir/tools.jsonl")
    parser.add_argument("--subset", default="data/human_skills/subset.jsonl")
    parser.add_argument("--output", default="data/human_skills/authoring_packets")
    parser.add_argument("--skills-dir", default="data/human_skills/skills")
    parser.add_argument("--report", default="outputs/reports/human_skill_protocol.md")
    parser.add_argument("--token-budget", type=int, default=300)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tools = index_tool_records(load_tool_records(args.tools))
    subset = load_jsonl(args.subset)
    packet_rows = build_authoring_packets(
        subset,
        tools=tools,
        output_dir=args.output,
        skills_dir=args.skills_dir,
        token_budget=args.token_budget,
    )
    write_protocol_report(args.report, packet_rows, token_budget=args.token_budget)
    print(f"packets={len(packet_rows)}")
    print(f"authoring_packets={args.output}")
    print(f"skills_dir={args.skills_dir}")
    print(f"protocol={args.report}")


def build_authoring_packets(
    subset: Iterable[Dict[str, Any]],
    *,
    tools: Dict[str, Dict[str, Any]],
    output_dir: str | Path,
    skills_dir: str | Path,
    token_budget: int = 300,
) -> List[Dict[str, Any]]:
    packet_root = Path(output_dir)
    skill_root = Path(skills_dir)
    packet_root.mkdir(parents=True, exist_ok=True)
    skill_root.mkdir(parents=True, exist_ok=True)
    (skill_root / "README.md").write_text(_skills_readme(), encoding="utf-8")

    rows = []
    for item in subset:
        tool_id = str(item.get("tool_id") or "")
        record = tools.get(tool_id) or tools.get(str(item.get("tool_name") or ""))
        if record is None:
            rows.append({"tool_id": tool_id, "packet_path": "", "status": "missing_tool_record"})
            continue
        packet_dir = packet_root / _safe_name(tool_id)
        packet_dir.mkdir(parents=True, exist_ok=True)
        (packet_dir / "raw_schema.json").write_text(
            json.dumps(record.get("input_schema_raw") or {}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (packet_dir / "toolir.json").write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        (packet_dir / "sparse_docs.md").write_text(_sparse_docs(record), encoding="utf-8")
        (packet_dir / "AUTHORING_INSTRUCTIONS.md").write_text(
            _authoring_instructions(record, tool_id=tool_id or tool_id_for_record(record), token_budget=token_budget),
            encoding="utf-8",
        )
        (packet_dir / "metadata_template.json").write_text(
            json.dumps(_metadata_template(tool_id or tool_id_for_record(record), token_budget), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        rows.append({"tool_id": tool_id or tool_id_for_record(record), "tool_name": record.get("tool_name"), "packet_path": str(packet_dir), "status": "ok"})
    return rows


def write_protocol_report(path: str | Path, packet_rows: List[Dict[str, Any]], *, token_budget: int) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    ok_count = sum(1 for row in packet_rows if row.get("status") == "ok")
    lines = [
        "# Human-Written Skill Protocol",
        "",
        "This workflow creates an upper-bound condition from real human-authored skill artifacts. It does not generate or fabricate human skills.",
        "",
        "## Author Inputs",
        "- Raw MCP-like input schema.",
        "- Normalized ToolIR record.",
        "- Sparse source documentation snippets.",
        "- Allowed `SKILL.md` section format and `metadata.json` template.",
        "- Safety notes derived from schema side-effect hints.",
        "",
        "## Hidden From Authors",
        "- Dev controls.",
        "- Test controls.",
        "- Gold tool calls or expected arguments.",
        "- Model predictions or evaluation results.",
        "",
        "## Required Artifact Format",
        "- `SKILL.md` with Summary, When to use, When not to use, Argument template, and optional Examples sections.",
        "- `metadata.json` with `author_saw_controls: false`.",
        f"- Token budget: `{token_budget}` approximate tokens.",
        "",
        "## Validation",
        "- Human skills are parsed into the same `GeneratedSkill` structure as generated skills.",
        "- The same structural validator checks argument templates and examples against schema.",
        "- Compactness is checked against the packet token budget.",
        "- Schema-faithfulness failures are logged before evaluation.",
        "",
        f"Packets built: `{ok_count}`",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_jsonl(path: str | Path) -> List[Dict[str, Any]]:
    rows = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                value = json.loads(line)
                if isinstance(value, dict):
                    rows.append(value)
    return rows


def _sparse_docs(record: Dict[str, Any]) -> str:
    snippets = record.get("doc_snippets") or []
    lines = [
        f"# {record.get('tool_name')}",
        "",
        "## Purpose",
        str(record.get("tool_purpose") or "No source description was available."),
        "",
        "## Sparse Documentation",
    ]
    if snippets:
        lines.extend(f"- {snippet}" for snippet in snippets[:5])
    else:
        lines.append("- No sparse documentation snippets were available.")
    return "\n".join(lines) + "\n"


def _authoring_instructions(record: Dict[str, Any], *, tool_id: str, token_budget: int) -> str:
    complexity = record.get("schema_complexity") if isinstance(record.get("schema_complexity"), dict) else {}
    side_effect = complexity.get("side_effect_type") or "unknown"
    return f"""# Human Skill Authoring Packet

Tool id: `{tool_id}`
Tool name: `{record.get('tool_name')}`
Token budget: `{token_budget}` approximate tokens.

Write exactly two files in `data/human_skills/skills/{_safe_name(tool_id)}/`:

- `SKILL.md`
- `metadata.json`

Do not use dev/test controls, gold outputs, model predictions, or evaluation logs while authoring.

## Allowed SKILL.md Format

````markdown
# Tool name

## Summary
One compact paragraph describing when this tool is appropriate.

## When to use
- Direct usage boundary.
- Required information boundary.

## When not to use
- Adjacent or near-miss boundary.
- Missing required information boundary.

## Argument template
```json
{{"field_name": "example value"}}
```

## Examples
```json
{{"arguments": {{"field_name": "example value"}}}}
```
````

The formatting example above is not a task label and does not reveal gold outputs.

## Safety Notes

- Side-effect type: `{side_effect}`.
- Require explicit user intent for write/delete/execute behavior.
- Do not invent missing required fields.
- Do not mention unsupported arguments or enum values.
- Prefer abstention for ambiguous adjacent-tool requests.
"""


def _metadata_template(tool_id: str, token_budget: int) -> Dict[str, Any]:
    return {
        "tool_id": tool_id,
        "author_id": "",
        "authoring_time_minutes": None,
        "author_saw_controls": False,
        "token_budget": token_budget,
        "notes": "",
    }


def _skills_readme() -> str:
    return """# Human-Written Skills

Place each completed human artifact in a subdirectory named after the packet folder.

Each completed artifact must contain:

- `SKILL.md`
- `metadata.json`

This directory intentionally starts without completed human skills.
"""


def _safe_name(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in value)[:160]


if __name__ == "__main__":
    main()

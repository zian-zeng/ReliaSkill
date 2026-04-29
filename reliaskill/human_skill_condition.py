from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from autoskill.ir import ArgumentIR, GeneratedSkill, ToolIR
from autoskill.token_accounting import skill_token_count
from autoskill.validator import validate_skill


HUMAN_WRITTEN_SKILL = "human_written_skill"
DEFAULT_TOKEN_BUDGET = 300
REQUIRED_METADATA_FIELDS = [
    "tool_id",
    "author_id",
    "authoring_time_minutes",
    "author_saw_controls",
    "token_budget",
    "notes",
]


@dataclass
class HumanSkillValidation:
    tool_id: str
    valid: bool
    skill_token_count: int
    token_budget: int
    structural_valid: bool
    compactness_valid: bool
    schema_faithfulness_valid: bool
    metadata_valid: bool
    failure_codes: List[str]
    failure_messages: List[str]
    skill_path: str

    def model_dump(self) -> Dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "valid": self.valid,
            "skill_token_count": self.skill_token_count,
            "token_budget": self.token_budget,
            "structural_valid": self.structural_valid,
            "compactness_valid": self.compactness_valid,
            "schema_faithfulness_valid": self.schema_faithfulness_valid,
            "metadata_valid": self.metadata_valid,
            "failure_codes": ";".join(self.failure_codes),
            "failure_messages": " | ".join(self.failure_messages),
            "skill_path": self.skill_path,
        }


def load_tool_records(path: str | Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    input_path = Path(path)
    if not input_path.exists():
        return records
    with input_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                value = json.loads(line)
                if isinstance(value, dict):
                    records.append(value)
    return records


def tool_id_for_record(record: Dict[str, Any]) -> str:
    meta = record.get("source_metadata") if isinstance(record.get("source_metadata"), dict) else {}
    source_id = meta.get("source_id") or record.get("server_name") or record.get("source_pointer") or "unknown_source"
    return str(record.get("tool_id") or meta.get("tool_key") or f"{source_id}::{record.get('tool_name')}")


def tool_from_record(record: Dict[str, Any]) -> ToolIR:
    args = []
    for arg in record.get("arguments") or []:
        if isinstance(arg, dict):
            args.append(ArgumentIR(**{key: arg.get(key) for key in ArgumentIR.__dataclass_fields__ if key in arg}))
    provenance = record.get("provenance") if isinstance(record.get("provenance"), dict) else {}
    source_metadata = record.get("source_metadata") if isinstance(record.get("source_metadata"), dict) else {}
    return ToolIR(
        tool_name=str(record.get("tool_name") or record.get("name") or ""),
        server_name=record.get("server_name"),
        tool_purpose=record.get("tool_purpose") or record.get("description"),
        input_schema_raw=record.get("input_schema_raw") if isinstance(record.get("input_schema_raw"), dict) else {},
        arguments=args,
        output_hint=record.get("output_hint"),
        auth_or_env_notes=record.get("auth_or_env_notes"),
        usage_warnings=list(record.get("usage_warnings") or []),
        doc_snippets=list(record.get("doc_snippets") or []),
        source_pointer=record.get("source_pointer"),
        doc_completeness=float(record.get("doc_completeness") or 0.0),
        schema_complexity=record.get("schema_complexity") if isinstance(record.get("schema_complexity"), dict) else {},
        ambiguity_flags=list(record.get("ambiguity_flags") or []),
        provenance={**source_metadata, **provenance},
        side_effect_hints=list(record.get("side_effect_hints") or []),
        safety_hints=list(record.get("safety_hints") or []),
    )


def index_tool_records(records: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for record in records:
        tool_id = tool_id_for_record(record)
        tool_name = str(record.get("tool_name") or "")
        index[tool_id] = record
        if tool_name:
            index.setdefault(tool_name, record)
    return index


def parse_human_skill_markdown(path: str | Path, *, baseline_name: str = HUMAN_WRITTEN_SKILL) -> GeneratedSkill:
    text = Path(path).read_text(encoding="utf-8")
    summary = _section_text(text, "Summary")
    when_to_use = _section_bullets(text, "When to use")
    when_not_to_use = _section_bullets(text, "When not to use")
    argument_template = _first_json_block(_section_text(text, "Argument template")) or {}
    examples = _example_blocks(_section_text(text, "Examples"))
    return GeneratedSkill(
        baseline_name=baseline_name,
        skill_summary=summary.strip(),
        when_to_use=when_to_use,
        when_not_to_use=when_not_to_use,
        argument_template=argument_template,
        examples=examples,
        metadata={"condition_family": HUMAN_WRITTEN_SKILL, "human_authored": True},
    )


def load_human_skill(skill_dir: str | Path) -> tuple[GeneratedSkill, Dict[str, Any]]:
    directory = Path(skill_dir)
    skill_path = directory / "SKILL.md"
    metadata_path = directory / "metadata.json"
    if not skill_path.exists() or not metadata_path.exists():
        raise FileNotFoundError(f"Human skill directory must contain SKILL.md and metadata.json: {directory}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict):
        raise ValueError(f"metadata.json must contain an object: {metadata_path}")
    skill = parse_human_skill_markdown(skill_path)
    skill.metadata = {
        **skill.metadata,
        "human_skill_metadata": metadata,
        "author_saw_controls": metadata.get("author_saw_controls"),
        "token_budget": metadata.get("token_budget"),
    }
    return skill, metadata


def validate_human_skill(
    tool: ToolIR,
    skill: GeneratedSkill,
    metadata: Dict[str, Any],
    *,
    skill_path: str | Path = "",
) -> HumanSkillValidation:
    report = validate_skill(tool, skill)
    token_budget = int(metadata.get("token_budget") or DEFAULT_TOKEN_BUDGET)
    tokens = skill_token_count(skill)
    metadata_failures = _metadata_failures(metadata, tool)
    compactness_failures = []
    if tokens > token_budget:
        compactness_failures.append(f"skill exceeds token budget ({tokens}>{token_budget})")
    if not skill.skill_summary.strip():
        metadata_failures.append("SKILL.md is missing a Summary section")
    if not skill.when_to_use:
        metadata_failures.append("SKILL.md is missing When to use bullets")
    if not skill.when_not_to_use:
        metadata_failures.append("SKILL.md is missing When not to use bullets")

    schema_failure_codes = [issue.code for issue in report.issues if issue.severity == "error"]
    failure_codes = list(dict.fromkeys(schema_failure_codes + ["metadata"] * bool(metadata_failures) + ["compactness"] * bool(compactness_failures)))
    failure_messages = [issue.message for issue in report.issues] + metadata_failures + compactness_failures
    structural_valid = not any(issue.severity == "error" for issue in report.issues)
    compactness_valid = not compactness_failures
    metadata_valid = not metadata_failures
    schema_faithfulness_valid = structural_valid
    return HumanSkillValidation(
        tool_id=str(metadata.get("tool_id") or tool.tool_name),
        valid=structural_valid and compactness_valid and metadata_valid and schema_faithfulness_valid,
        skill_token_count=tokens,
        token_budget=token_budget,
        structural_valid=structural_valid,
        compactness_valid=compactness_valid,
        schema_faithfulness_valid=schema_faithfulness_valid,
        metadata_valid=metadata_valid,
        failure_codes=failure_codes,
        failure_messages=failure_messages,
        skill_path=str(skill_path),
    )


def validate_human_skill_directory(
    skills_root: str | Path,
    tools_path: str | Path,
) -> List[HumanSkillValidation]:
    records = load_tool_records(tools_path)
    tool_index = index_tool_records(records)
    validations: List[HumanSkillValidation] = []
    root = Path(skills_root)
    if not root.exists():
        return validations
    for skill_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        metadata_path = skill_dir / "metadata.json"
        if not metadata_path.exists() or not (skill_dir / "SKILL.md").exists():
            continue
        skill, metadata = load_human_skill(skill_dir)
        record = tool_index.get(str(metadata.get("tool_id"))) or tool_index.get(skill_dir.name)
        if record is None:
            validations.append(
                HumanSkillValidation(
                    tool_id=str(metadata.get("tool_id") or skill_dir.name),
                    valid=False,
                    skill_token_count=skill_token_count(skill),
                    token_budget=int(metadata.get("token_budget") or DEFAULT_TOKEN_BUDGET),
                    structural_valid=False,
                    compactness_valid=True,
                    schema_faithfulness_valid=False,
                    metadata_valid=False,
                    failure_codes=["unknown_tool_id"],
                    failure_messages=[f"Tool id is not present in {tools_path}"],
                    skill_path=str(skill_dir / "SKILL.md"),
                )
            )
            continue
        validations.append(validate_human_skill(tool_from_record(record), skill, metadata, skill_path=skill_dir / "SKILL.md"))
    return validations


def _metadata_failures(metadata: Dict[str, Any], tool: ToolIR) -> List[str]:
    failures = [f"metadata.json missing required field `{field}`" for field in REQUIRED_METADATA_FIELDS if field not in metadata]
    if metadata.get("author_saw_controls") is not False:
        failures.append("author_saw_controls must be false")
    if not str(metadata.get("author_id") or "").strip():
        failures.append("author_id must be set")
    try:
        if float(metadata.get("authoring_time_minutes")) <= 0:
            failures.append("authoring_time_minutes must be positive")
    except (TypeError, ValueError):
        failures.append("authoring_time_minutes must be numeric")
    tool_id = str(metadata.get("tool_id") or "")
    if tool_id and tool_id not in {tool.tool_name, tool_id_for_tool(tool)}:
        failures.append(f"metadata tool_id `{tool_id}` does not match tool `{tool.tool_name}`")
    return failures


def tool_id_for_tool(tool: ToolIR) -> str:
    source_id = tool.provenance.get("source_id") or tool.server_name or tool.source_pointer or "unknown_source"
    return f"{source_id}::{tool.tool_name}"


def _section_text(text: str, heading: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.IGNORECASE | re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return ""
    next_heading = re.search(r"^##\s+", text[match.end() :], re.MULTILINE)
    end = match.end() + next_heading.start() if next_heading else len(text)
    return text[match.end() : end].strip()


def _section_bullets(text: str, heading: str) -> List[str]:
    body = _section_text(text, heading)
    bullets = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            bullets.append(stripped[2:].strip())
    return bullets


def _first_json_block(text: str) -> Dict[str, Any] | None:
    for block in re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE):
        try:
            value = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def _example_blocks(text: str) -> List[Dict[str, Any]]:
    examples = []
    for index, block in enumerate(re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)):
        try:
            value = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            if "arguments" in value:
                examples.append(value)
            else:
                examples.append({"scenario": f"Human-authored example {index + 1}", "arguments": value})
    return examples

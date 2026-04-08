from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List

from autoskill.ir import GeneratedSkill, ToolIR, ValidationIssue, ValidationReport
from autoskill.schema_utils import normalize_schema_node, schema_is_nullable, schema_type


def _collect_unknown_fields(schema: Dict[str, Any], payload: Any, path: str = "$") -> Iterable[str]:
    if not isinstance(schema, dict):
        return []
    schema, _ = normalize_schema_node(schema)

    normalized_type = schema_type(schema)
    if payload is None:
        return []
    if normalized_type == "object" and isinstance(payload, dict):
        props = schema.get("properties", {}) or {}
        unknown: List[str] = []
        for key, value in payload.items():
            child_path = f"{path}.{key}"
            if key not in props:
                unknown.append(child_path)
                continue
            unknown.extend(_collect_unknown_fields(props[key], value, child_path))
        return unknown
    if normalized_type == "array" and isinstance(payload, list):
        item_schema = schema.get("items", {}) or {}
        unknown = []
        for idx, item in enumerate(payload):
            unknown.extend(_collect_unknown_fields(item_schema, item, f"{path}[{idx}]"))
        return unknown
    return []


def _normalize_example_arguments(value: Any) -> Any:
    if isinstance(value, str):
        return json.loads(value)
    return value


def _matches_type(schema_type: str | None, payload: Any) -> bool:
    if schema_type is None:
        return True
    if schema_type == "string":
        return isinstance(payload, str)
    if schema_type == "integer":
        return isinstance(payload, int) and not isinstance(payload, bool)
    if schema_type == "number":
        return isinstance(payload, (int, float)) and not isinstance(payload, bool)
    if schema_type == "boolean":
        return isinstance(payload, bool)
    if schema_type == "array":
        return isinstance(payload, list)
    if schema_type == "object":
        return isinstance(payload, dict)
    return True


def _validate_against_schema(
    schema: Dict[str, Any],
    payload: Any,
    path: str,
    label: str,
    issues: List[ValidationIssue],
) -> None:
    schema, _ = normalize_schema_node(schema)
    normalized_type = schema_type(schema)

    if payload is None:
        if not schema_is_nullable(schema):
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="type_mismatch",
                    message=f"{label}: null is not allowed at {path}",
                    location=path,
                )
            )
        return

    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and enum_values and payload not in enum_values:
        issues.append(
            ValidationIssue(
                severity="error",
                code="invalid_enum",
                message=f"{label}: {payload!r} is not an allowed value at {path}",
                location=path,
            )
        )

    if not _matches_type(normalized_type, payload):
        issues.append(
            ValidationIssue(
                severity="error",
                code="type_mismatch",
                message=f"{label}: expected {normalized_type} at {path}, got {type(payload).__name__}",
                location=path,
            )
        )
        return

    if normalized_type == "object":
        properties = schema.get("properties", {}) or {}
        required_fields = schema.get("required", []) or []
        for required_key in required_fields:
            if required_key not in payload:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        code="missing_required_argument",
                        message=f"{label}: missing required field `{required_key}` at {path}",
                        location=path,
                    )
                )
        for key, value in payload.items():
            if key in properties:
                _validate_against_schema(properties[key], value, f"{path}.{key}", label, issues)
        return

    if normalized_type == "array":
        item_schema = schema.get("items", {}) or {}
        for index, item in enumerate(payload):
            _validate_against_schema(item_schema, item, f"{path}[{index}]", label, issues)


def _validate_payload(
    schema: Dict[str, Any],
    payload: Any,
    label: str,
    issues: List[ValidationIssue],
) -> None:
    for field_path in _collect_unknown_fields(schema, payload, "$"):
        issues.append(
            ValidationIssue(
                severity="error",
                code="hallucinated_argument",
                message=f"{label} contains unknown field: {field_path}",
                location=field_path,
            )
        )

    _validate_against_schema(schema, payload, "$", label, issues)


def _check_text_contradictions(tool: ToolIR, skill: GeneratedSkill, issues: List[ValidationIssue]) -> None:
    text_blocks = " ".join(
        [skill.skill_summary, *skill.when_to_use, *skill.when_not_to_use]
    ).lower()
    for arg in tool.arguments:
        token = arg.name.lower()
        if arg.required and f"{token} optional" in text_blocks:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    code="text_contradiction",
                    message=f"Skill text suggests `{arg.name}` is optional, but the schema marks it required.",
                    location=arg.schema_path,
                )
            )
        if not arg.required and f"{token} required" in text_blocks:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    code="text_contradiction",
                    message=f"Skill text suggests `{arg.name}` is required, but the schema marks it optional.",
                    location=arg.schema_path,
                )
            )


def validate_skill(tool: ToolIR, skill: GeneratedSkill) -> ValidationReport:
    issues: List[ValidationIssue] = []
    schema = tool.input_schema_raw or {"type": "object", "properties": {}}

    if not isinstance(skill.argument_template, dict):
        issues.append(
            ValidationIssue(
                severity="error",
                code="bad_argument_template",
                message="argument_template must be a dictionary",
                location="$",
            )
        )
        return ValidationReport(valid=False, issues=issues)

    if skill.baseline_name != "raw_mcp":
        _validate_payload(schema, skill.argument_template, "argument_template", issues)

    for index, example in enumerate(skill.examples):
        if "arguments" not in example:
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="bad_example_arguments",
                    message=f"Example {index} is missing an `arguments` field.",
                    location=f"$.examples[{index}]",
                )
            )
            continue

        try:
            example_args = _normalize_example_arguments(example["arguments"])
        except json.JSONDecodeError as exc:
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="bad_example_json",
                    message=f"Example {index} contains invalid JSON: {exc}",
                    location=f"$.examples[{index}]",
                )
            )
            continue

        if not isinstance(example_args, dict):
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="bad_example_arguments",
                    message=f"Example {index} must provide a JSON object for `arguments`.",
                    location=f"$.examples[{index}]",
                )
            )
            continue

        _validate_payload(schema, example_args, f"example[{index}]", issues)

    _check_text_contradictions(tool, skill, issues)

    valid = not any(issue.severity == "error" for issue in issues)
    return ValidationReport(valid=valid, issues=issues)

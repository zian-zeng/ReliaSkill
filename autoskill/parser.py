from __future__ import annotations

from typing import Any, Dict, List, Tuple

from autoskill.ir import ArgumentIR, ToolIR
from autoskill.schema_utils import coerce_schema_default, infer_schema_type, normalize_schema_node


def _canonicalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def _extract_output_hint(raw_tool: Dict[str, Any]) -> str | None:
    output_schema = raw_tool.get("outputSchema") or raw_tool.get("output_schema")
    if isinstance(output_schema, dict):
        return _canonicalize_text(output_schema.get("description") or output_schema.get("title"))
    return None


def _extract_auth_notes(raw_tool: Dict[str, Any], description: str | None) -> str | None:
    explicit = raw_tool.get("auth_or_env_notes") or raw_tool.get("auth_notes")
    if explicit:
        return _canonicalize_text(explicit)

    haystack = (description or "").lower()
    auth_markers = (
        "api key",
        "oauth",
        "token",
        "credential",
        "login",
        "authenticated",
        "environment variable",
    )
    if any(marker in haystack for marker in auth_markers):
        return "This tool may require authentication or environment setup."
    return None


def _schema_depth(schema: Dict[str, Any], current_depth: int = 1) -> int:
    if not isinstance(schema, dict):
        return current_depth
    child_depths = [current_depth]
    properties = schema.get("properties")
    if isinstance(properties, dict):
        child_depths.extend(_schema_depth(child, current_depth + 1) for child in properties.values() if isinstance(child, dict))
    items = schema.get("items")
    if isinstance(items, dict):
        child_depths.append(_schema_depth(items, current_depth + 1))
    for key in ("anyOf", "oneOf", "allOf"):
        options = schema.get(key)
        if isinstance(options, list):
            child_depths.extend(_schema_depth(option, current_depth + 1) for option in options if isinstance(option, dict))
    return max(child_depths)


def _extract_side_effect_hints(tool_name: str, description: str | None) -> List[str]:
    text = f"{tool_name} {description or ''}".lower()
    hints = []
    for marker, label in (
        ("write", "writes_data"),
        ("create", "creates_resource"),
        ("delete", "deletes_resource"),
        ("remove", "deletes_resource"),
        ("move", "moves_resource"),
        ("update", "updates_resource"),
        ("send", "external_communication"),
        ("execute", "executes_code"),
        ("run", "executes_code"),
    ):
        if marker in text and label not in hints:
            hints.append(label)
    return hints


def _compute_doc_completeness(description: str | None, properties: Dict[str, Any], doc_snippets: List[str]) -> float:
    score = 0.0
    if description:
        score += 0.4
    if doc_snippets:
        score += 0.2
    if properties:
        described = 0
        for prop in properties.values():
            if isinstance(prop, dict) and prop.get("description"):
                described += 1
        score += 0.4 * (described / len(properties))
    return round(min(score, 1.0), 4)


def _ambiguity_flags(description: str | None, input_schema: Dict[str, Any], properties: Dict[str, Any]) -> List[str]:
    flags = []
    if not description:
        flags.append("missing_tool_description")
    if not properties:
        flags.append("empty_input_schema")
    for name, schema in properties.items():
        if isinstance(schema, dict) and not schema.get("description"):
            flags.append(f"missing_argument_description:{name}")
    if input_schema.get("additionalProperties") is not False:
        flags.append("allows_or_omits_unknown_argument_policy")
    return flags


def parse_mcp_tool(raw_tool: Dict[str, Any], source_pointer: str | None = None) -> ToolIR:
    tool_name = raw_tool.get("name", "unknown_tool")
    description = _canonicalize_text(raw_tool.get("description"))
    server_name = raw_tool.get("server_name")

    input_schema = raw_tool.get("inputSchema", {}) or raw_tool.get("input_schema", {}) or {}
    required_fields = set(input_schema.get("required", []))
    properties = input_schema.get("properties", {}) or {}

    arguments: List[ArgumentIR] = []
    usage_warnings: List[str] = []

    if not properties:
        usage_warnings.append("Tool does not expose top-level input properties.")

    if input_schema.get("additionalProperties") is False:
        usage_warnings.append("Schema forbids unknown top-level arguments.")

    for arg_name, raw_schema in properties.items():
        raw_arg_schema = raw_schema if isinstance(raw_schema, dict) else {}
        arg_schema, nullable = normalize_schema_node(raw_arg_schema)
        arg_type, _ = infer_schema_type(arg_schema)
        enum_vals = arg_schema.get("enum")
        default = coerce_schema_default(arg_schema.get("default"), arg_type)
        desc = _canonicalize_text(arg_schema.get("description"))

        items_type = None
        items_schema = None
        if arg_type == "array":
            items = arg_schema.get("items", {})
            if isinstance(items, dict):
                items_schema, _ = normalize_schema_node(items)
                items_type, _ = infer_schema_type(items_schema)
            else:
                items_type, _ = infer_schema_type({})

        nested_properties = None
        required_properties: List[str] = []
        if arg_type == "object":
            nested_properties = arg_schema.get("properties") if isinstance(arg_schema.get("properties"), dict) else None
            required_properties = list(arg_schema.get("required", []))

        arguments.append(
            ArgumentIR(
                name=arg_name,
                type=arg_type,
                required=arg_name in required_fields,
                default=default,
                enum=enum_vals,
                description=desc,
                items_type=items_type,
                items_schema=items_schema,
                properties=nested_properties,
                required_properties=required_properties,
                nullable=nullable,
                format=arg_schema.get("format"),
                schema_path=f"$.properties.{arg_name}",
            )
        )

    doc_snippets = []
    for snippet in (description, raw_tool.get("title"), raw_tool.get("summary")):
        normalized = _canonicalize_text(snippet)
        if normalized and normalized not in doc_snippets:
            doc_snippets.append(normalized)

    schema_complexity = {
        "num_top_level_arguments": len(arguments),
        "num_arguments": len(arguments),
        "num_required_arguments": sum(1 for arg in arguments if arg.required),
        "num_optional_arguments": sum(1 for arg in arguments if not arg.required),
        "num_enum_arguments": sum(1 for arg in arguments if arg.enum),
        "num_enum_fields": sum(1 for arg in arguments if arg.enum),
        "num_nested_object_arguments": sum(1 for arg in arguments if arg.type == "object"),
        "has_nested_object": any(arg.type == "object" for arg in arguments),
        "has_array_argument": any(arg.type == "array" for arg in arguments),
        "has_boolean_flag": any(arg.type == "boolean" for arg in arguments),
        "max_schema_depth": _schema_depth(input_schema),
    }
    side_effect_hints = _extract_side_effect_hints(tool_name, description)

    return ToolIR(
        tool_name=tool_name,
        server_name=server_name,
        tool_purpose=description,
        input_schema_raw=input_schema,
        arguments=arguments,
        output_hint=_extract_output_hint(raw_tool),
        auth_or_env_notes=_extract_auth_notes(raw_tool, description),
        usage_warnings=usage_warnings,
        doc_snippets=doc_snippets,
        source_pointer=source_pointer,
        doc_completeness=_compute_doc_completeness(description, properties, doc_snippets),
        schema_complexity=schema_complexity,
        ambiguity_flags=_ambiguity_flags(description, input_schema, properties),
        provenance={
            "source_pointer": source_pointer,
            "server_name": server_name,
            "raw_name": raw_tool.get("name"),
        },
        side_effect_hints=side_effect_hints,
        safety_hints=[
            "review_side_effects_before_deployment"
        ] if side_effect_hints else [],
    )

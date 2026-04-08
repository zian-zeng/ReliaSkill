from __future__ import annotations

from typing import Any, Dict, List, Tuple

from autoskill.ir import ArgumentIR, ToolIR
from autoskill.schema_utils import infer_schema_type, normalize_schema_node


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
        default = arg_schema.get("default")
        desc = _canonicalize_text(arg_schema.get("description"))

        items_type = None
        if arg_type == "array":
            items = arg_schema.get("items", {})
            items_type, _ = infer_schema_type(items if isinstance(items, dict) else {})

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
    )

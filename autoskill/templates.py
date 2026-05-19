from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Dict, List

from autoskill.ir import ArgumentIR, ToolIR
from autoskill.schema_utils import coerce_schema_default, normalize_schema_node, schema_type


def _string_value(name: str, description: str | None, fmt: str | None, variant: int) -> str:
    key = name.lower()
    desc = (description or "").lower()

    if fmt == "date-time" or ("date" in key and "time" in key):
        return "2026-01-01T09:00:00Z"
    if fmt == "date" or "date" in key:
        return "2026-01-01"
    if fmt in {"uri", "url"} or any(token in key for token in ("url", "uri", "link", "website")):
        return "https://example.com/resource"
    if fmt == "email" or "email" in key:
        return "user@example.com"
    if "city" in key:
        return "New York"
    if "query" in key or "search" in key:
        return "sample query"
    if "path" in key or "file" in key:
        return "data/sample.txt"
    if key == "id" or key.endswith("_id") or "identifier" in desc:
        return f"sample-{name.replace('_', '-')}-001"
    if "name" in key:
        return "sample-name"
    if "title" in key:
        return "Sample Title"
    if "language" in key:
        return "en"
    if "timezone" in key:
        return "America/New_York"
    if "region" in key:
        return "us-east-1"
    if "prompt" in key:
        return "Summarize the latest update."
    return f"sample_{name}_{variant + 1}"


def _value_from_schema(
    name: str,
    schema: Dict[str, Any],
    variant: int = 0,
    include_optional: bool = True,
) -> Any:
    if not isinstance(schema, dict):
        return None
    schema, _ = normalize_schema_node(schema)

    if "default" in schema:
        return deepcopy(coerce_schema_default(schema["default"], schema_type(schema)))
    if isinstance(schema.get("enum"), list) and schema["enum"]:
        values = schema["enum"]
        return deepcopy(values[variant % len(values)])

    type_value = schema.get("type")
    if isinstance(type_value, list):
        type_value = next((item for item in type_value if item != "null"), type_value[0] if type_value else None)

    if type_value == "string" or schema.get("format"):
        return _string_value(name, schema.get("description"), schema.get("format"), variant)
    if type_value == "integer":
        return variant + 1
    if type_value == "number":
        return float(variant + 1)
    if type_value == "boolean":
        return bool(variant % 2)
    if type_value == "array":
        items_schema = schema.get("items", {})
        return [_value_from_schema(f"{name}_item", items_schema, variant, include_optional=include_optional)]
    if type_value == "object" or isinstance(schema.get("properties"), dict):
        result: Dict[str, Any] = {}
        properties = schema.get("properties", {}) or {}
        required = set(schema.get("required", []))
        for child_name, child_schema in properties.items():
            if include_optional or child_name in required:
                result[child_name] = _value_from_schema(child_name, child_schema, variant, include_optional)
        return result

    return None


def build_argument_value(
    arg: ArgumentIR,
    variant: int = 0,
    *,
    include_optional_children: bool = True,
) -> Any:
    if arg.default is not None:
        return deepcopy(arg.default)
    if arg.enum:
        return deepcopy(arg.enum[variant % len(arg.enum)])
    if arg.type == "string":
        return _string_value(arg.name, arg.description, arg.format, variant)
    if arg.type == "integer":
        return variant + 1
    if arg.type == "number":
        return float(variant + 1)
    if arg.type == "boolean":
        return bool(variant % 2)
    if arg.type == "array":
        item_schema = arg.items_schema if isinstance(arg.items_schema, dict) else {"type": arg.items_type or "string"}
        return [_value_from_schema(f"{arg.name}_item", item_schema, variant, include_optional=include_optional_children)]
    if arg.type == "object":
        return _value_from_schema(
            arg.name,
            {
                "type": "object",
                "properties": arg.properties or {},
                "required": arg.required_properties,
            },
            variant,
            include_optional=include_optional_children,
        )
    return None


def build_argument_template(
    tool: ToolIR,
    include_optional: bool = True,
    variant: int = 0,
) -> Dict[str, Any]:
    template: Dict[str, Any] = {}
    for arg in tool.arguments:
        if include_optional or arg.required:
            template[arg.name] = build_argument_value(
                arg,
                variant=variant,
                include_optional_children=include_optional,
            )
    return template


def build_optional_argument_examples(
    tool: ToolIR,
    *,
    variant: int = 1,
    max_examples: int = 4,
) -> List[Dict[str, Any]]:
    required_template = build_argument_template(tool, include_optional=False, variant=0)
    examples: List[Dict[str, Any]] = []
    for index, arg in enumerate(arg for arg in tool.arguments if not arg.required):
        value = build_argument_value(arg, variant=variant + index, include_optional_children=False)
        if value is None:
            continue
        arguments = dict(required_template)
        arguments[arg.name] = value
        examples.append(
            {
                "scenario": f"Valid call when optional `{arg.name}` is explicitly requested.",
                "arguments": arguments,
            }
        )
        if len(examples) >= max_examples:
            break
    return examples


def build_structured_call_hints(tool: ToolIR) -> Dict[str, List[str]]:
    required = [arg.name for arg in tool.arguments if arg.required]
    optional = [arg.name for arg in tool.arguments if not arg.required]
    allowed = [arg.name for arg in tool.arguments]
    enums = [arg for arg in tool.arguments if arg.enum]
    objects = [arg for arg in tool.arguments if arg.type == "object" or arg.properties]
    arrays = [arg for arg in tool.arguments if arg.type == "array"]

    when_to_use: List[str] = []
    when_not_to_use: List[str] = []

    if required:
        when_to_use.append("Start structured calls from the required fields only: " + ", ".join(f"`{name}`" for name in required) + ".")
    else:
        when_to_use.append("Start structured calls from an empty argument object and add only fields grounded in the request.")
    if optional:
        when_to_use.append("Add optional fields only when the user explicitly asks for that control; omit unrelated optional fields.")
    if allowed:
        when_not_to_use.append("Do not include unsupported fields; allowed top-level fields are: " + ", ".join(f"`{name}`" for name in allowed) + ".")
    if "head" in allowed and "tail" in allowed:
        when_not_to_use.append("For line ranges, choose `head` or `tail` from the user's direction; do not include both unless both are explicitly requested.")
    for arg in enums[:3]:
        values = ", ".join(repr(value) for value in arg.enum or [])
        when_to_use.append(f"Use exact enum literals for `{arg.name}`: {values}.")
    for arg in objects[:3]:
        nested_required = list(arg.required_properties)
        if nested_required:
            when_to_use.append(
                f"For nested object `{arg.name}`, include its required keys: "
                + ", ".join(repr(name) for name in nested_required)
                + "."
            )
    for arg in arrays[:3]:
        if arg.required:
            when_to_use.append(f"For required array `{arg.name}`, provide a JSON array with schema-valid items.")
            item_schema = arg.items_schema if isinstance(arg.items_schema, dict) else {}
            item_schema, _ = normalize_schema_node(item_schema)
            if isinstance(item_schema.get("properties"), dict):
                nested_required = [str(name) for name in item_schema.get("required", []) or []]
                if nested_required:
                    when_to_use.append(
                        f"For each `{arg.name}` item, include required keys: "
                        + ", ".join(repr(name) for name in nested_required)
                        + "."
                    )
        else:
            when_not_to_use.append(f"Omit optional array `{arg.name}` unless the request explicitly asks for it.")

    return {"when_to_use": when_to_use, "when_not_to_use": when_not_to_use}


def build_schema_contract_lines(tool: ToolIR) -> List[str]:
    """Build a compact, prompt-visible contract for legal structured calls."""
    allowed = [arg.name for arg in tool.arguments]
    required = [arg.name for arg in tool.arguments if arg.required]
    lines: List[str] = []

    if allowed:
        lines.append("Allowed top-level fields: " + ", ".join(f"`{name}`" for name in allowed) + "; do not emit any other top-level fields.")
    else:
        lines.append("Allowed top-level fields: none; use an empty argument object when calling.")

    if required:
        lines.append("Required top-level fields: " + ", ".join(f"`{name}`" for name in required) + ".")
    else:
        lines.append("No top-level fields are required; omit fields not grounded in the request.")

    field_types = _top_level_type_contract(tool.arguments)
    if field_types:
        lines.append("Top-level field types: " + field_types + ".")

    for arg in tool.arguments:
        lines.extend(_argument_contract_lines(arg))

    return _dedupe_contract_lines(lines)


def _argument_contract_lines(arg: ArgumentIR) -> List[str]:
    lines: List[str] = []
    if arg.enum:
        values = ", ".join(json_like(value) for value in arg.enum)
        lines.append(f"`{arg.name}` must use one of these exact enum values: {values}.")

    if arg.type == "object" or arg.properties:
        child_names = sorted((arg.properties or {}).keys())
        if child_names:
            lines.append(f"`{arg.name}` object allowed keys: " + ", ".join(f"`{name}`" for name in child_names) + ".")
        if arg.required_properties:
            lines.append(f"`{arg.name}` object required keys: " + ", ".join(f"`{name}`" for name in arg.required_properties) + ".")
        for child_name, child_schema in sorted((arg.properties or {}).items()):
            lines.extend(_nested_schema_contract_lines(f"{arg.name}.{child_name}", child_schema))

    if arg.type == "array":
        item_schema = arg.items_schema if isinstance(arg.items_schema, dict) else {"type": arg.items_type or "string"}
        item_schema, _ = normalize_schema_node(item_schema)
        item_type = schema_type(item_schema)
        lines.append(f"`{arg.name}` must be a JSON array of {item_type or 'schema-valid'} items.")
        properties = item_schema.get("properties")
        if isinstance(properties, dict) and properties:
            child_names = sorted(str(name) for name in properties)
            lines.append(f"Each `{arg.name}` item allowed keys: " + ", ".join(f"`{name}`" for name in child_names) + ".")
            nested_required = [str(name) for name in item_schema.get("required", []) or []]
            if nested_required:
                lines.append(f"Each `{arg.name}` item required keys: " + ", ".join(f"`{name}`" for name in nested_required) + ".")
            for child_name, child_schema in sorted(properties.items()):
                lines.extend(_nested_schema_contract_lines(f"{arg.name}[].{child_name}", child_schema))
        elif item_type == "array":
            lines.extend(_nested_schema_contract_lines(f"{arg.name}[]", item_schema.get("items", {}) or {}, depth=1))

    return lines


def _top_level_type_contract(arguments: List[ArgumentIR]) -> str:
    parts: List[str] = []
    for arg in arguments:
        type_label = _argument_type_label(arg)
        required_label = "required" if arg.required else "optional"
        parts.append(f"`{arg.name}`={type_label} ({required_label})")
    text = ", ".join(parts)
    return text[:900].rstrip(", ")


def _argument_type_label(arg: ArgumentIR) -> str:
    if arg.type == "array":
        item_schema = arg.items_schema if isinstance(arg.items_schema, dict) else {"type": arg.items_type or "schema-valid"}
        item_schema, _ = normalize_schema_node(item_schema)
        return f"array<{schema_type(item_schema) or arg.items_type or 'schema-valid'}>"
    if arg.type == "object" or arg.properties:
        return "object"
    return arg.type or "schema-valid"


def _nested_schema_contract_lines(path: str, schema: Dict[str, Any], *, depth: int = 0) -> List[str]:
    if depth > 3 or not isinstance(schema, dict):
        return []
    schema, _ = normalize_schema_node(schema)
    kind = schema_type(schema)
    lines: List[str] = []

    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and enum_values:
        values = ", ".join(json_like(value) for value in enum_values)
        lines.append(f"`{path}` must use one of these exact enum values: {values}.")

    if kind == "object":
        properties = schema.get("properties")
        if isinstance(properties, dict) and properties:
            child_names = sorted(str(name) for name in properties)
            lines.append(f"`{path}` object allowed keys: " + ", ".join(f"`{name}`" for name in child_names) + ".")
            required = [str(name) for name in schema.get("required", []) or []]
            if required:
                lines.append(f"`{path}` object required keys: " + ", ".join(f"`{name}`" for name in required) + ".")
            for child_name, child_schema in sorted(properties.items()):
                lines.extend(_nested_schema_contract_lines(f"{path}.{child_name}", child_schema, depth=depth + 1))

    if kind == "array":
        item_schema = schema.get("items", {}) or {}
        item_schema, _ = normalize_schema_node(item_schema)
        item_type = schema_type(item_schema)
        lines.append(f"`{path}` must be a JSON array of {item_type or 'schema-valid'} items.")
        properties = item_schema.get("properties")
        if isinstance(properties, dict) and properties:
            child_names = sorted(str(name) for name in properties)
            lines.append(f"Each `{path}` item allowed keys: " + ", ".join(f"`{name}`" for name in child_names) + ".")
            required = [str(name) for name in item_schema.get("required", []) or []]
            if required:
                lines.append(f"Each `{path}` item required keys: " + ", ".join(f"`{name}`" for name in required) + ".")
            for child_name, child_schema in sorted(properties.items()):
                lines.extend(_nested_schema_contract_lines(f"{path}[].{child_name}", child_schema, depth=depth + 1))

    return lines


def _dedupe_contract_lines(lines: List[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for line in lines:
        normalized = " ".join(line.split()).lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(line)
    return result


def json_like(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)

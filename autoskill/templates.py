from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

from autoskill.ir import ArgumentIR, ToolIR
from autoskill.schema_utils import normalize_schema_node


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
        return deepcopy(schema["default"])
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
        return [_value_from_schema(f"{name}_item", items_schema, variant, include_optional=True)]
    if type_value == "object" or isinstance(schema.get("properties"), dict):
        result: Dict[str, Any] = {}
        properties = schema.get("properties", {}) or {}
        required = set(schema.get("required", []))
        for child_name, child_schema in properties.items():
            if include_optional or child_name in required:
                result[child_name] = _value_from_schema(child_name, child_schema, variant, include_optional)
        return result

    return None


def build_argument_value(arg: ArgumentIR, variant: int = 0) -> Any:
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
        item_schema = {"type": arg.items_type or "string"}
        return [_value_from_schema(f"{arg.name}_item", item_schema, variant, include_optional=True)]
    if arg.type == "object":
        return _value_from_schema(
            arg.name,
            {
                "type": "object",
                "properties": arg.properties or {},
                "required": arg.required_properties,
            },
            variant,
            include_optional=True,
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
            template[arg.name] = build_argument_value(arg, variant=variant)
    return template

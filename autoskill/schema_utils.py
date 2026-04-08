from __future__ import annotations

from typing import Any, Dict, Tuple


def normalize_schema_node(schema_node: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    if not isinstance(schema_node, dict):
        return {}, False

    schema = dict(schema_node)
    nullable = False

    type_value = schema.get("type")
    if isinstance(type_value, list):
        nullable = "null" in type_value
        non_null = [item for item in type_value if item != "null"]
        if non_null:
            schema["type"] = non_null[0]
        else:
            schema.pop("type", None)

    for key in ("anyOf", "oneOf"):
        options = schema.get(key)
        if not isinstance(options, list):
            continue
        for option in options:
            if isinstance(option, dict) and option.get("type") == "null":
                nullable = True
        for option in options:
            if isinstance(option, dict) and option.get("type") != "null":
                merged = dict(option)
                for inherited_key in ("description", "title", "default", "enum", "format"):
                    if inherited_key not in merged and inherited_key in schema:
                        merged[inherited_key] = schema[inherited_key]
                return merged, nullable

    return schema, nullable


def infer_schema_type(schema_node: Dict[str, Any]) -> Tuple[str, bool]:
    schema, nullable = normalize_schema_node(schema_node)
    if "type" in schema and schema["type"] is not None:
        return str(schema["type"]), nullable
    if "enum" in schema:
        return "string", nullable
    if "properties" in schema:
        return "object", nullable
    if "items" in schema:
        return "array", nullable
    return "unknown", nullable


def schema_type(schema: Dict[str, Any]) -> str | None:
    normalized, _ = normalize_schema_node(schema)
    type_value = normalized.get("type")
    if isinstance(type_value, str):
        return type_value
    if "properties" in normalized:
        return "object"
    if "items" in normalized:
        return "array"
    return None


def schema_is_nullable(schema: Dict[str, Any]) -> bool:
    _, nullable = normalize_schema_node(schema)
    return nullable

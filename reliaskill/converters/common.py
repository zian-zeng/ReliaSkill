from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from autoskill.parser import parse_mcp_tool


SOURCE_NAMES = {
    "bfcl": "Berkeley Function Calling Leaderboard",
    "api_bank": "API-Bank",
    "toolbench": "MCPToolBench++/ToolBench",
}


def slugify(value: Any, *, max_length: int = 96) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    text = text or "item"
    if len(text) <= max_length:
        return text
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
    return f"{text[: max_length - 9]}_{digest}"


def stable_hash(value: Any, *, length: int = 12) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=True, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def load_json_or_jsonl(path: str | Path) -> List[Dict[str, Any]]:
    input_path = Path(path)
    if input_path.suffix.lower() == ".jsonl":
        records: List[Dict[str, Any]] = []
        with input_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(value, dict):
                    records.append(value)
        return records

    try:
        raw = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        records = []
        for line in input_path.read_text(encoding="utf-8").splitlines():
            line = line.strip().rstrip(",")
            if not line or line in {"[", "]"}:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                records.append(value)
        return records

    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict):
        for key in ("data", "items", "records", "tools", "apis", "examples", "train", "test"):
            value = raw.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [raw]
    return []


def normalize_schema(schema: Any) -> Dict[str, Any]:
    if isinstance(schema, str):
        try:
            schema = json.loads(schema)
        except json.JSONDecodeError:
            schema = {}
    if not isinstance(schema, dict):
        schema = {}

    if "parameters" in schema and isinstance(schema["parameters"], dict):
        schema = schema["parameters"]

    normalized = _normalize_schema_node(schema)
    if normalized.get("type") != "object":
        normalized = {"type": "object", **normalized}
    properties = normalized.get("properties")
    if not isinstance(properties, dict):
        normalized["properties"] = {}
    required = normalized.get("required")
    if not isinstance(required, list):
        normalized["required"] = []
    valid_names = set(normalized["properties"].keys())
    normalized["required"] = [str(name) for name in normalized["required"] if str(name) in valid_names]
    return normalized


def _normalize_schema_node(node: Any) -> Dict[str, Any]:
    if isinstance(node, str):
        try:
            node = json.loads(node)
        except json.JSONDecodeError:
            return {"type": _coerce_type(node)}
    if not isinstance(node, dict):
        return {}

    result: Dict[str, Any] = {}
    for key in ("type", "description", "title", "format", "default", "enum", "minimum", "maximum", "nullable"):
        if key in node:
            result[key] = node[key]

    result["type"] = _coerce_type(result.get("type") or node.get("schema_type") or node.get("datatype"))

    if isinstance(result.get("enum"), str):
        result["enum"] = [part.strip() for part in result["enum"].split("|") if part.strip()]

    properties = node.get("properties") or node.get("parameters")
    if isinstance(properties, list):
        properties = _properties_from_list(properties)
    if isinstance(properties, dict):
        result["properties"] = {str(name): _normalize_schema_node(child) for name, child in properties.items()}

    items = node.get("items")
    if isinstance(items, dict):
        result["items"] = _normalize_schema_node(items)
    elif isinstance(items, str):
        result["items"] = {"type": _coerce_type(items)}

    required = node.get("required")
    if isinstance(required, list):
        result["required"] = [str(item) for item in required]
    elif isinstance(required, bool) and properties:
        result["required"] = list(result.get("properties", {}).keys()) if required else []

    for key in ("oneOf", "anyOf", "allOf"):
        if isinstance(node.get(key), list):
            result[key] = [_normalize_schema_node(item) for item in node[key]]

    return {key: value for key, value in result.items() if value is not None}


def _properties_from_list(items: Sequence[Any]) -> Dict[str, Any]:
    properties: Dict[str, Any] = {}
    for index, item in enumerate(items):
        if isinstance(item, str):
            properties[slugify(item)] = {"type": "string", "description": item}
            continue
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("parameter_name") or item.get("key") or f"arg_{index}"
        schema = dict(item)
        schema.pop("name", None)
        schema.pop("parameter_name", None)
        schema.pop("key", None)
        properties[str(name)] = schema
    return properties


def _coerce_type(value: Any) -> str:
    if isinstance(value, list):
        non_null = [item for item in value if item != "null"]
        return _coerce_type(non_null[0]) if non_null else "string"
    text = str(value or "object").lower()
    mapping = {
        "str": "string",
        "string": "string",
        "text": "string",
        "int": "integer",
        "integer": "integer",
        "float": "number",
        "double": "number",
        "number": "number",
        "bool": "boolean",
        "boolean": "boolean",
        "list": "array",
        "array": "array",
        "dict": "object",
        "map": "object",
        "object": "object",
    }
    return mapping.get(text, "string" if text not in {"", "none", "null"} else "object")


def schema_from_arguments(arguments: Any) -> Dict[str, Any]:
    if arguments in (None, "", "N/A", "n/a", "NA", "[]"):
        return normalize_schema({})
    if isinstance(arguments, dict):
        if "type" in arguments or "properties" in arguments or "parameters" in arguments:
            return normalize_schema(arguments)
        return normalize_schema({"type": "object", "properties": arguments, "required": list(arguments.keys())})
    if isinstance(arguments, list):
        properties = _properties_from_list(arguments)
        return normalize_schema({"type": "object", "properties": properties, "required": list(properties.keys())})
    if isinstance(arguments, str):
        cleaned = arguments.strip()
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            names = _argument_names_from_text(cleaned)
            properties = {name: {"type": "string", "description": name.replace("_", " ")} for name in names}
            return normalize_schema({"type": "object", "properties": properties, "required": []})
        return schema_from_arguments(parsed)
    return normalize_schema({})


def _argument_names_from_text(text: str) -> List[str]:
    if not text or text.lower() in {"n/a", "none", "null"}:
        return []
    candidates = []
    for piece in re.split(r"[,;\n]", text):
        piece = piece.strip()
        if not piece:
            continue
        match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)", piece)
        if match:
            candidates.append(slugify(match.group(1), max_length=40))
    return candidates[:12]


def infer_schema_from_signature(signature: str) -> Dict[str, Any]:
    match = re.search(r"\((.*)\)", str(signature or ""))
    if not match:
        return normalize_schema({})
    inner = match.group(1).strip()
    if not inner:
        return normalize_schema({})
    properties: Dict[str, Any] = {}
    required: List[str] = []
    for raw_arg in _split_args(inner):
        token = raw_arg.strip()
        if not token or token.startswith("*"):
            continue
        if "=" in token:
            name = token.split("=", 1)[0].strip()
        else:
            name = token.strip()
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
                continue
            required.append(slugify(name, max_length=40))
        name = slugify(name, max_length=40)
        if not name or name in {"self", "cls"}:
            continue
        properties[name] = {"type": "string", "description": f"Argument from original signature: {token}"}
    return normalize_schema({"type": "object", "properties": properties, "required": required})


def _split_args(text: str) -> List[str]:
    parts: List[str] = []
    start = 0
    depth = 0
    quote: str | None = None
    escaped = False
    for index, char in enumerate(text):
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(text[start:index])
            start = index + 1
    tail = text[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def make_mcp_tool(
    *,
    tool_id: str,
    source_type: str,
    source_name: str,
    original_benchmark_id: str,
    original_tool_name: str,
    original_function_signature: str,
    description: str,
    normalized_schema: Dict[str, Any],
    source_path: str = "",
    extra_metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    metadata = {
        "source_type": source_type,
        "source_name": source_name,
        "source_category": "converted_external_benchmark",
        "source_file": source_path,
        "original_benchmark_id": original_benchmark_id,
        "original_tool_name": original_tool_name,
        "original_function_signature": original_function_signature,
        "converted": True,
        "real_mcp_tool": False,
        "schema_hash": stable_hash(normalized_schema, length=16),
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    return {
        "server_name": f"converted_{source_type}",
        "name": tool_id,
        "title": str(original_tool_name or tool_id).replace("_", " ").title(),
        "summary": " ".join(str(description or original_tool_name or tool_id).split())[:180],
        "description": str(description or original_tool_name or tool_id),
        "inputSchema": normalized_schema,
        "source_metadata": metadata,
    }


def make_conversion_record(
    *,
    tool_id: str,
    source_type: str,
    source_name: str,
    original_benchmark_id: str,
    original_tool_name: str,
    original_function_signature: str,
    normalized_schema: Dict[str, Any],
    mcp_tool: Dict[str, Any],
    natural_language_request: str | None = None,
    gold_tool_call: Dict[str, Any] | None = None,
    split_suggestion: str | None = None,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    toolir = parse_mcp_tool(mcp_tool, source_pointer=original_benchmark_id).model_dump()
    toolir["source_metadata"] = mcp_tool.get("source_metadata", {})
    record = {
        "tool_id": tool_id,
        "source_type": source_type,
        "source_name": source_name,
        "original_benchmark_id": original_benchmark_id,
        "original_tool_name": original_tool_name,
        "original_function_signature": original_function_signature,
        "normalized_schema": normalized_schema,
        "natural_language_request": natural_language_request,
        "gold_tool_call": gold_tool_call,
        "split_suggestion": split_suggestion,
        "mcp_tool_schema": mcp_tool,
        "toolir": toolir,
        "metadata": metadata or {},
    }
    control = make_positive_control(record)
    if control:
        record["positive_control"] = control
    return record


def make_positive_control(record: Dict[str, Any]) -> Dict[str, Any] | None:
    request = record.get("natural_language_request")
    gold = record.get("gold_tool_call")
    if not request or not isinstance(gold, dict):
        return None
    arguments = gold.get("arguments") or gold.get("parameters") or gold.get("input") or {}
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            arguments = {}
    if not isinstance(arguments, dict):
        arguments = {}
    control_id = f"external_{record['source_type']}_{slugify(record.get('original_benchmark_id'))}_{slugify(record['tool_id'])}"
    return {
        "id": control_id,
        "task_id": control_id,
        "function": record["tool_id"],
        "tool_name": record["tool_id"],
        "question": request,
        "user_request": request,
        "category": "external_positive",
        "gold_tool": record["tool_id"],
        "gold_args": arguments,
        "ground_truth": {"arguments": arguments},
        "expected_arguments": arguments,
        "expected_argument_candidates": [arguments],
        "should_trigger": True,
        "split": record.get("split_suggestion") or "external",
        "source_type": record["source_type"],
        "source_name": record["source_name"],
        "original_benchmark_id": record["original_benchmark_id"],
        "original_tool_name": record["original_tool_name"],
        "tool_key": f"converted_{record['source_type']}::{record['tool_id']}",
        "tags": ["external", record["source_type"], "positive"],
    }


def has_nested_args(schema: Dict[str, Any]) -> bool:
    properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    return any(_schema_contains_type(child, "object") for child in properties.values())


def has_enum(schema: Dict[str, Any]) -> bool:
    if isinstance(schema, dict):
        if isinstance(schema.get("enum"), list):
            return True
        return any(has_enum(value) for value in schema.values())
    if isinstance(schema, list):
        return any(has_enum(item) for item in schema)
    return False


def _schema_contains_type(value: Any, expected: str) -> bool:
    if isinstance(value, dict):
        schema_type = value.get("type")
        if schema_type == expected or (isinstance(schema_type, list) and expected in schema_type):
            return True
        return any(_schema_contains_type(child, expected) for child in value.values())
    if isinstance(value, list):
        return any(_schema_contains_type(item, expected) for item in value)
    return False


def mark_multi_tool_ambiguity(records: List[Dict[str, Any]]) -> None:
    by_request: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_source_prefix: Dict[tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        request = str(record.get("natural_language_request") or "").strip().lower()
        if request:
            by_request[request].append(record)
        prefix = "_".join(slugify(record.get("original_tool_name")).split("_")[:2])
        by_source_prefix[(record["source_type"], prefix)].append(record)
    ambiguous_ids = set()
    for group in by_request.values():
        if len({item["tool_id"] for item in group}) > 1:
            ambiguous_ids.update(id(item) for item in group)
    for group in by_source_prefix.values():
        if len(group) > 1:
            ambiguous_ids.update(id(item) for item in group)
    for record in records:
        record.setdefault("metadata", {})["multi_tool_ambiguity"] = id(record) in ambiguous_ids


def summarize_records(records: Sequence[Dict[str, Any]], skipped: Dict[str, Counter[str]], warnings: Sequence[str]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record.get("source_type") or "unknown")].append(record)
    all_sources = sorted(set(grouped) | set(skipped) | {warning.split(":", 1)[0] for warning in warnings if ":" in warning})
    for source_type in all_sources:
        items = grouped.get(source_type, [])
        unique_tools = {item["tool_id"] for item in items}
        examples = [item for item in items if item.get("positive_control")]
        skip_counter = skipped.get(source_type, Counter())
        rows.append(
            {
                "source_type": source_type,
                "source_name": SOURCE_NAMES.get(source_type, source_type),
                "tools_converted": len(unique_tools),
                "examples_converted": len(examples),
                "records_converted": len(items),
                "skipped": sum(skip_counter.values()),
                "skip_reasons": "; ".join(f"{key}={value}" for key, value in sorted(skip_counter.items())),
                "nested_arg_tools": len({item["tool_id"] for item in items if has_nested_args(item["normalized_schema"])}),
                "enum_tools": len({item["tool_id"] for item in items if has_enum(item["normalized_schema"])}),
                "multi_tool_ambiguity": len({item["tool_id"] for item in items if item.get("metadata", {}).get("multi_tool_ambiguity")}),
            }
        )
    return rows


def write_jsonl(path: str | Path, records: Iterable[Dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def write_csv(path: str | Path, rows: Sequence[Dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "source_type",
        "source_name",
        "tools_converted",
        "examples_converted",
        "records_converted",
        "skipped",
        "skip_reasons",
        "nested_arg_tools",
        "enum_tools",
        "multi_tool_ambiguity",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_markdown_report(rows: Sequence[Dict[str, Any]], warnings: Sequence[str], output_dir: str | Path) -> str:
    lines = [
        "# External Benchmark Conversion Report",
        "",
        "Converted external function-calling/tool-use benchmark records into MCP-like raw schemas, normalized ToolIR records, and positive controls when gold calls were available.",
        "",
        f"- Output directory: {output_dir}",
        f"- Total tools converted: {sum(int(row['tools_converted']) for row in rows)}",
        f"- Total examples converted: {sum(int(row['examples_converted']) for row in rows)}",
        f"- Total skipped: {sum(int(row['skipped']) for row in rows)}",
        "",
        "## Source Summary",
        "",
        "| Source | Tools | Examples | Skipped | Nested Args | Enums | Multi-tool Ambiguity | Skip Reasons |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| {source_name} | {tools_converted} | {examples_converted} | {skipped} | {nested_arg_tools} | {enum_tools} | {multi_tool_ambiguity} | {skip_reasons} |".format(
                **row
            )
        )
    if warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in warnings)
    return "\n".join(lines) + "\n"

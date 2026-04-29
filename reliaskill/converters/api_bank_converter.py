from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from reliaskill.converters.common import (
    SOURCE_NAMES,
    infer_schema_from_signature,
    load_json_or_jsonl,
    make_conversion_record,
    make_mcp_tool,
    normalize_schema,
    schema_from_arguments,
    slugify,
)


def convert_api_bank(input_root: str | Path, *, strict: bool = False) -> Tuple[List[Dict[str, Any]], Counter[str], List[str]]:
    root = _api_bank_root(Path(input_root))
    skipped: Counter[str] = Counter()
    if root is None:
        message = "api_bank: missing API-Bank directory"
        if strict:
            raise FileNotFoundError(message)
        return [], skipped, [message]

    records: List[Dict[str, Any]] = []
    tools: Dict[str, Dict[str, Any]] = {}
    examples: List[Dict[str, Any]] = []
    for path in sorted([*root.rglob("*.json"), *root.rglob("*.jsonl")]):
        for index, item in enumerate(load_json_or_jsonl(path)):
            item = dict(item)
            item["_source_path"] = str(path)
            item["_source_index"] = index
            if _looks_like_tool(item):
                converted = _tool_record(item)
                if converted is None:
                    skipped["malformed_tool"] += 1
                    continue
                tools[converted["tool_id"]] = converted
                records.append(converted)
            elif _looks_like_example(item):
                examples.append(item)
            else:
                skipped["unrecognized_record"] += 1

    for example in examples:
        converted = _example_record(example, tools)
        if converted is None:
            skipped["example_without_resolvable_gold_call"] += 1
            continue
        records.append(converted)

    warnings: List[str] = []
    if not records:
        warnings.append(f"api_bank: found {root} but converted no usable records")
    return records, skipped, warnings


def _api_bank_root(input_root: Path) -> Path | None:
    candidates = [
        input_root / "api_bank",
        input_root / "apibank",
        input_root / "API-Bank",
        input_root / "api-bank",
        input_root,
    ]
    for candidate in candidates:
        if not candidate.exists() or not candidate.is_dir():
            continue
        if any(path.suffix.lower() in {".json", ".jsonl"} for path in candidate.rglob("*")):
            if candidate.name.lower() in {"api_bank", "apibank", "api-bank", "api-bank-main"} or "api" in candidate.name.lower():
                return candidate
    return None


def _looks_like_tool(item: Dict[str, Any]) -> bool:
    return any(key in item for key in ("api_name", "tool_name", "function", "function_name", "name")) and any(
        key in item for key in ("parameters", "input_schema", "inputSchema", "schema", "api_arguments", "signature", "api_call", "description")
    )


def _looks_like_example(item: Dict[str, Any]) -> bool:
    return any(key in item for key in ("query", "question", "instruction", "utterance", "natural_language_request")) and any(
        key in item for key in ("api_call", "tool_call", "function_call", "gold", "answer", "ground_truth")
    )


def _tool_record(item: Dict[str, Any]) -> Dict[str, Any] | None:
    name = _tool_name(item)
    signature = str(item.get("signature") or item.get("api_call") or item.get("function_signature") or name)
    if not name:
        return None
    schema = _schema_from_item(item)
    description = str(item.get("description") or item.get("summary") or item.get("doc") or name)
    benchmark_id = str(item.get("id") or item.get("api_id") or f"{item.get('_source_path')}#{item.get('_source_index')}")
    tool_id = slugify(f"api_bank_{name}", max_length=100)
    mcp_tool = make_mcp_tool(
        tool_id=tool_id,
        source_type="api_bank",
        source_name=SOURCE_NAMES["api_bank"],
        original_benchmark_id=benchmark_id,
        original_tool_name=name,
        original_function_signature=signature,
        description=description,
        normalized_schema=schema,
        source_path=str(item.get("_source_path") or ""),
        extra_metadata={"domain": item.get("domain") or item.get("category")},
    )
    return make_conversion_record(
        tool_id=tool_id,
        source_type="api_bank",
        source_name=SOURCE_NAMES["api_bank"],
        original_benchmark_id=benchmark_id,
        original_tool_name=name,
        original_function_signature=signature,
        normalized_schema=schema,
        mcp_tool=mcp_tool,
        split_suggestion=_split(item),
        metadata={"source_path": item.get("_source_path"), "domain": item.get("domain") or item.get("category")},
    )


def _example_record(item: Dict[str, Any], tools: Dict[str, Dict[str, Any]]) -> Dict[str, Any] | None:
    request = item.get("natural_language_request") or item.get("query") or item.get("question") or item.get("instruction") or item.get("utterance")
    gold = _gold_call(item)
    if not request or not gold:
        return None
    original_name = str(gold.get("name") or gold.get("tool_name") or gold.get("api_name") or gold.get("function") or "")
    tool_id = _resolve_tool_id(original_name, tools)
    if not tool_id:
        schema = _schema_from_item(gold)
        if not schema.get("properties"):
            schema = infer_schema_from_signature(str(gold.get("api_call") or original_name))
        original_name = original_name or str(gold.get("api_call") or "api_bank_tool")
        tool_id = slugify(f"api_bank_{original_name}", max_length=100)
        mcp_tool = make_mcp_tool(
            tool_id=tool_id,
            source_type="api_bank",
            source_name=SOURCE_NAMES["api_bank"],
            original_benchmark_id=str(item.get("id") or item.get("_source_path")),
            original_tool_name=original_name,
            original_function_signature=str(gold.get("api_call") or original_name),
            description=str(gold.get("description") or original_name),
            normalized_schema=schema,
            source_path=str(item.get("_source_path") or ""),
        )
    else:
        base = tools[tool_id]
        schema = base["normalized_schema"]
        original_name = base["original_tool_name"]
        mcp_tool = base["mcp_tool_schema"]

    benchmark_id = str(item.get("id") or item.get("example_id") or f"{item.get('_source_path')}#{item.get('_source_index')}")
    arguments = gold.get("arguments") or gold.get("parameters") or gold.get("input") or {}
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            arguments = {}
    gold_call = {"name": tool_id, "original_name": original_name, "arguments": arguments if isinstance(arguments, dict) else {}}
    return make_conversion_record(
        tool_id=tool_id,
        source_type="api_bank",
        source_name=SOURCE_NAMES["api_bank"],
        original_benchmark_id=benchmark_id,
        original_tool_name=original_name,
        original_function_signature=str(gold.get("api_call") or gold.get("signature") or original_name),
        normalized_schema=schema,
        natural_language_request=str(request),
        gold_tool_call=gold_call,
        split_suggestion=_split(item),
        mcp_tool=mcp_tool,
        metadata={"source_path": item.get("_source_path"), "domain": item.get("domain") or item.get("category")},
    )


def _tool_name(item: Dict[str, Any]) -> str:
    for key in ("tool_name", "api_name", "function_name", "name"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    function = item.get("function")
    if isinstance(function, dict):
        return _tool_name(function)
    if isinstance(function, str):
        return function.strip()
    return ""


def _schema_from_item(item: Dict[str, Any]) -> Dict[str, Any]:
    for key in ("inputSchema", "input_schema", "schema", "parameters", "api_arguments"):
        if key in item:
            if key == "api_arguments":
                return schema_from_arguments(item[key])
            return normalize_schema(item[key])
    signature = str(item.get("signature") or item.get("api_call") or "")
    return infer_schema_from_signature(signature)


def _gold_call(item: Dict[str, Any]) -> Dict[str, Any] | None:
    for key in ("tool_call", "function_call", "gold", "ground_truth", "answer", "api_call"):
        value = item.get(key)
        if isinstance(value, dict):
            return value
        if isinstance(value, str) and value.strip():
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return {"name": value, "arguments": {}}
            return parsed if isinstance(parsed, dict) else None
    return None


def _resolve_tool_id(original_name: str, tools: Dict[str, Dict[str, Any]]) -> str | None:
    needle = slugify(original_name)
    for tool_id, record in tools.items():
        candidates = {slugify(tool_id), slugify(record.get("original_tool_name")), slugify(record.get("original_function_signature"))}
        if needle in candidates:
            return tool_id
    return None


def _split(item: Dict[str, Any]) -> str | None:
    value = item.get("split") or item.get("dataset_split")
    return str(value) if value else None

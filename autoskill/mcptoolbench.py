from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple


def _load_json_records(path: Path) -> List[Dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        records: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    value = json.loads(line)
                    if isinstance(value, dict):
                        records.append(value)
        return records

    with path.open("r", encoding="utf-8") as f:
        try:
            raw = json.load(f)
        except json.JSONDecodeError:
            f.seek(0)
            records = []
            for line in f:
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
        for key in ("data", "items", "records", "train"):
            value = raw.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [raw]
    return []


def load_mcptoolbench_records(input_path: str | Path, categories: Sequence[str] | None = None, limit: int | None = None) -> List[Dict[str, Any]]:
    root = Path(input_path)
    paths = [root] if root.is_file() else sorted([*root.rglob("*.json"), *root.rglob("*.jsonl")])
    paths = [path for path in paths if ".cache" not in path.parts]
    category_filter = {item.lower() for item in categories or []}
    records: List[Dict[str, Any]] = []
    for path in paths:
        for record in _load_json_records(path):
            if "query" not in record or "function_call_label" not in record:
                continue
            category = str(record.get("category", "")).lower()
            if category_filter and category not in category_filter:
                continue
            record = dict(record)
            record.setdefault("_source_file", str(path))
            records.append(record)
            if limit and len(records) >= limit:
                return records
    return records


def _coerce_input_schema(tool_def: Dict[str, Any]) -> Dict[str, Any]:
    schema = tool_def.get("inputSchema") or tool_def.get("input_schema") or tool_def.get("inputSchemaJson") or tool_def.get("input_schema_json")
    if isinstance(schema, str):
        try:
            parsed = json.loads(schema)
            schema = parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            schema = {}
    if not isinstance(schema, dict):
        schema = {}
    if schema.get("type") != "object":
        schema = {"type": "object", **schema}
    schema.setdefault("properties", {})
    schema.setdefault("required", [])
    return schema


def _tool_name(tool_def: Dict[str, Any], fallback: str = "") -> str:
    for key in ("name", "tool_name", "function_name", "id"):
        value = tool_def.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return fallback


def _canonical_tool(tool_def: Dict[str, Any], server_name: str | None, fallback_name: str = "") -> Dict[str, Any] | None:
    name = _tool_name(tool_def, fallback=fallback_name)
    if not name:
        return None
    description = tool_def.get("description") or tool_def.get("summary") or tool_def.get("title") or ""
    return {
        "server_name": server_name or tool_def.get("server_name") or tool_def.get("server") or "mcptoolbenchpp",
        "name": name,
        "title": tool_def.get("title") or name.replace("_", " ").title(),
        "description": str(description),
        "inputSchema": _coerce_input_schema(tool_def),
        "outputSchema": tool_def.get("outputSchema") or tool_def.get("output_schema"),
        "source_benchmark": "MCPToolBench++",
    }


def _iter_tools_from_record(record: Dict[str, Any]) -> Iterable[Tuple[str | None, Dict[str, Any], str]]:
    tools = record.get("tools")
    if isinstance(tools, list):
        for index, tool_def in enumerate(tools):
            if isinstance(tool_def, dict):
                yield record.get("category"), tool_def, str(index + 1)

    mcp_tools = record.get("mcp_tools_dict")
    if isinstance(mcp_tools, dict):
        for server_name, value in mcp_tools.items():
            if isinstance(value, list):
                for index, item in enumerate(value):
                    if isinstance(item, dict):
                        yield str(server_name), item, str(index + 1)
                    elif isinstance(item, str):
                        yield str(server_name), {"name": item, "description": item, "inputSchema": {"type": "object", "properties": {}, "required": []}}, item
            elif isinstance(value, dict):
                for maybe_name, item in value.items():
                    if isinstance(item, dict):
                        yield str(server_name), item, str(maybe_name)


def _expected_calls(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_calls = record.get("function_call_label")
    if isinstance(raw_calls, str):
        try:
            raw_calls = json.loads(raw_calls)
        except json.JSONDecodeError:
            raw_calls = []
    if isinstance(raw_calls, dict):
        raw_calls = [raw_calls]
    if not isinstance(raw_calls, list):
        return []
    calls = []
    for index, call in enumerate(raw_calls):
        if not isinstance(call, dict):
            continue
        name = call.get("name") or call.get("tool_name") or call.get("function") or call.get("id")
        args = call.get("arguments") or call.get("parameters") or call.get("input") or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
        calls.append({"name": str(name or ""), "arguments": args if isinstance(args, dict) else {}, "index": index})
    return calls


def _resolve_expected_tool_name(call: Dict[str, Any], tool_by_id: Dict[str, str], tool_names: Sequence[str]) -> str:
    raw_name = str(call.get("name") or "")
    if raw_name in tool_by_id:
        return tool_by_id[raw_name]
    if raw_name in tool_names:
        return raw_name
    if raw_name.isdigit() and raw_name in tool_by_id:
        return tool_by_id[raw_name]
    return tool_names[0] if len(tool_names) == 1 else raw_name


def convert_mcptoolbench_records(
    records: Iterable[Dict[str, Any]],
    negatives_per_positive: int = 3,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    tools_by_name: Dict[str, Dict[str, Any]] = {}
    tasks: List[Dict[str, Any]] = []

    for record_index, record in enumerate(records):
        local_tools: List[str] = []
        tool_by_id: Dict[str, str] = {}
        for server_name, tool_def, fallback_id in _iter_tools_from_record(record):
            tool = _canonical_tool(tool_def, server_name=server_name, fallback_name=fallback_id)
            if not tool:
                continue
            name = tool["name"]
            tools_by_name.setdefault(name, tool)
            local_tools.append(name)
            for key in {fallback_id, str(tool_def.get("id", "")), str(tool_def.get("name", ""))}:
                if key:
                    tool_by_id[key] = name

        expected_calls = _expected_calls(record)
        if not expected_calls or not local_tools:
            continue
        query = str(record.get("query") or record.get("user_request") or "")
        category = str(record.get("category") or "mcptoolbenchpp")
        call_type = str(record.get("call_type") or "unknown")
        base_id = str(record.get("uuid") or record.get("id") or f"mcptoolbench_{record_index}")

        for call_index, call in enumerate(expected_calls):
            expected_tool = _resolve_expected_tool_name(call, tool_by_id, local_tools)
            if expected_tool not in tools_by_name:
                continue
            task_id = f"{base_id}_call{call_index}"
            arguments = dict(call.get("arguments") or {})
            tasks.append(
                {
                    "task_id": task_id,
                    "tool_name": expected_tool,
                    "expected_tool_name": expected_tool,
                    "user_request": query,
                    "expected_arguments": arguments,
                    "expected_argument_candidates": [arguments],
                    "should_trigger": True,
                    "split": "mcptoolbenchpp",
                    "tags": ["mcptoolbenchpp", category, call_type, "positive"],
                    "source_uuid": base_id,
                }
            )
            distractors = [name for name in local_tools if name != expected_tool][:negatives_per_positive]
            for distractor in distractors:
                tasks.append(
                    {
                        "task_id": f"{task_id}_not_{distractor}",
                        "tool_name": expected_tool,
                        "expected_tool_name": expected_tool,
                        "negative_target": distractor,
                        "harm_baseline": "raw_mcp",
                        "user_request": query,
                        "expected_arguments": {},
                        "expected_argument_candidates": [{}],
                        "should_trigger": False,
                        "split": "mcptoolbenchpp_negative",
                        "tags": ["mcptoolbenchpp", category, call_type, "negative_control"],
                        "source_uuid": base_id,
                    }
                )

    return list(tools_by_name.values()), tasks

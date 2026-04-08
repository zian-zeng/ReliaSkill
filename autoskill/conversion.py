from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from autoskill.benchmark import load_benchmark_tasks


def load_json_or_jsonl(path: str | Path) -> List[Dict[str, Any]]:
    input_path = Path(path)
    if input_path.suffix.lower() == ".jsonl":
        items: List[Dict[str, Any]] = []
        with input_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    value = json.loads(line)
                    if isinstance(value, dict):
                        items.append(value)
        return items

    with input_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict):
        for key in ("data", "tools", "items"):
            value = raw.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [raw]
    return []


def convert_benchmark_file_to_canonical_records(path: str | Path) -> List[Dict[str, Any]]:
    tasks = load_benchmark_tasks(path)
    return [
        {
            "task_id": task.task_id,
            "tool_name": task.tool_name,
            "user_request": task.user_request,
            "expected_arguments": task.expected_arguments,
            "expected_argument_candidates": task.expected_argument_candidates or [task.expected_arguments],
        }
        for task in tasks
    ]


def _extract_tools_from_wrapped_item(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    for key in ("tools", "items", "data"):
        value = item.get(key)
        if isinstance(value, list) and all(isinstance(entry, dict) for entry in value):
            return list(value)
    return [item]


def canonicalize_mcp_tool_records(
    records: Iterable[Dict[str, Any]],
    default_server_name: str | None = None,
) -> List[Dict[str, Any]]:
    canonical: List[Dict[str, Any]] = []
    for record in records:
        for item in _extract_tools_from_wrapped_item(record):
            name = item.get("name")
            input_schema = item.get("inputSchema") or item.get("input_schema")
            if not name or not isinstance(input_schema, dict):
                continue
            canonical.append(
                {
                    "server_name": item.get("server_name") or item.get("server") or default_server_name,
                    "name": name,
                    "title": item.get("title"),
                    "summary": item.get("summary"),
                    "description": item.get("description", ""),
                    "inputSchema": input_schema,
                    "outputSchema": item.get("outputSchema") or item.get("output_schema"),
                }
            )
    return canonical


def write_json(path: str | Path, payload: Any) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def write_jsonl(path: str | Path, records: Iterable[Dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

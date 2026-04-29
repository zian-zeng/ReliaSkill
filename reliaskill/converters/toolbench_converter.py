from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

from autoskill.mcptoolbench import convert_mcptoolbench_records, load_mcptoolbench_records

from reliaskill.converters.common import (
    SOURCE_NAMES,
    make_conversion_record,
    make_mcp_tool,
    normalize_schema,
    slugify,
)


def convert_toolbench(input_root: str | Path, *, strict: bool = False) -> Tuple[List[Dict[str, Any]], Counter[str], List[str]]:
    root = _toolbench_root(Path(input_root))
    skipped: Counter[str] = Counter()
    if root is None:
        message = "toolbench: missing ToolBench/MCPToolBench++ directory"
        if strict:
            raise FileNotFoundError(message)
        return [], skipped, [message]

    source_records = load_mcptoolbench_records(root)
    if not source_records:
        message = f"toolbench: found {root} but no usable records with query/function_call_label"
        if strict:
            raise ValueError(message)
        return [], skipped, [message]

    tools, tasks = convert_mcptoolbench_records(source_records, negatives_per_positive=0)
    records: List[Dict[str, Any]] = []
    converted_tools: Dict[str, Dict[str, Any]] = {}
    for index, tool in enumerate(tools):
        converted = _tool_record(tool, root=root, index=index)
        if converted is None:
            skipped["malformed_tool"] += 1
            continue
        converted_tools[converted["tool_id"]] = converted
        records.append(converted)

    for task in tasks:
        if not task.get("should_trigger", True):
            continue
        converted = _task_record(task, converted_tools, root=root)
        if converted is None:
            skipped["task_without_resolvable_tool"] += 1
            continue
        records.append(converted)

    warnings: List[str] = []
    if not records:
        warnings.append(f"toolbench: found {root} but converted no usable records")
    return records, skipped, warnings


def _toolbench_root(input_root: Path) -> Path | None:
    candidates = [
        input_root / "mcptoolbenchpp",
        input_root / "toolbench",
        input_root / "ToolBench",
        input_root,
    ]
    for candidate in candidates:
        if not candidate.exists() or not candidate.is_dir():
            continue
        if any(path.suffix.lower() in {".json", ".jsonl"} for path in candidate.rglob("*")):
            if "toolbench" in candidate.name.lower() or "mcp" in candidate.name.lower() or (candidate / "data").exists():
                return candidate
    return None


def _tool_record(tool: Dict[str, Any], *, root: Path, index: int) -> Dict[str, Any] | None:
    original_name = str(tool.get("name") or tool.get("tool_name") or "")
    if not original_name:
        return None
    tool_id = slugify(f"toolbench_{original_name}", max_length=100)
    schema = normalize_schema(tool.get("inputSchema") or tool.get("input_schema") or {})
    signature = json.dumps({"name": original_name, "input_schema": schema}, sort_keys=True, ensure_ascii=False)
    benchmark_id = str(tool.get("source_uuid") or f"{root.as_posix()}#tool{index}")
    mcp_tool = make_mcp_tool(
        tool_id=tool_id,
        source_type="toolbench",
        source_name=SOURCE_NAMES["toolbench"],
        original_benchmark_id=benchmark_id,
        original_tool_name=original_name,
        original_function_signature=signature,
        description=str(tool.get("description") or tool.get("summary") or original_name),
        normalized_schema=schema,
        source_path=str(root),
        extra_metadata={"category": tool.get("category"), "domain": tool.get("category")},
    )
    return make_conversion_record(
        tool_id=tool_id,
        source_type="toolbench",
        source_name=SOURCE_NAMES["toolbench"],
        original_benchmark_id=benchmark_id,
        original_tool_name=original_name,
        original_function_signature=signature,
        normalized_schema=schema,
        mcp_tool=mcp_tool,
        split_suggestion="toolbench",
        metadata={"source_path": str(root), "category": tool.get("category")},
    )


def _task_record(task: Dict[str, Any], converted_tools: Dict[str, Dict[str, Any]], *, root: Path) -> Dict[str, Any] | None:
    original_name = str(task.get("tool_name") or task.get("expected_tool_name") or "")
    tool_id = slugify(f"toolbench_{original_name}", max_length=100)
    base = converted_tools.get(tool_id)
    if base is None:
        return None
    arguments = task.get("expected_arguments") or {}
    if not isinstance(arguments, dict):
        arguments = {}
    gold = {"name": tool_id, "original_name": original_name, "arguments": arguments}
    return make_conversion_record(
        tool_id=tool_id,
        source_type="toolbench",
        source_name=SOURCE_NAMES["toolbench"],
        original_benchmark_id=str(task.get("source_uuid") or task.get("task_id") or root),
        original_tool_name=base["original_tool_name"],
        original_function_signature=base["original_function_signature"],
        normalized_schema=base["normalized_schema"],
        natural_language_request=str(task.get("user_request") or task.get("query") or ""),
        gold_tool_call=gold,
        split_suggestion=str(task.get("split") or "toolbench"),
        mcp_tool=base["mcp_tool_schema"],
        metadata={"source_path": str(root), "source_uuid": task.get("source_uuid")},
    )

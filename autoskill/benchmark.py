from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from autoskill.eval_types import EvalTask


def _coalesce(item: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    for key in keys:
        if key in item and item[key] is not None:
            return item[key]
    return default


def _expand_candidate_values(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    return [value]


def _expand_candidate_argument_dict(arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = [{}]
    for key, raw_value in arguments.items():
        values = _expand_candidate_values(raw_value)
        next_candidates: List[Dict[str, Any]] = []
        for candidate in candidates:
            for value in values:
                updated = dict(candidate)
                updated[key] = value
                next_candidates.append(updated)
        candidates = next_candidates
    return candidates


def _normalize_ground_truth_candidates(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    explicit_candidates = item.get("expected_argument_candidates")
    if isinstance(explicit_candidates, list):
        return [dict(candidate) for candidate in explicit_candidates if isinstance(candidate, dict)]

    direct = _coalesce(
        item,
        [
            "expected_arguments",
            "arguments",
            "ground_truth_arguments",
            "ground_truth",
            "expected",
            "answer",
        ],
    )
    if isinstance(direct, dict):
        if "arguments" in direct and isinstance(direct["arguments"], dict):
            return [dict(direct["arguments"])]
        return [dict(direct)]

    if isinstance(direct, list):
        candidates: List[Dict[str, Any]] = []
        for entry in direct:
            if not isinstance(entry, dict):
                continue
            for maybe_tool_name, maybe_args in entry.items():
                if isinstance(maybe_args, dict):
                    candidates.extend(_expand_candidate_argument_dict(maybe_args))
        return candidates

    return []


def _normalize_tool_name(item: Dict[str, Any]) -> str:
    direct = _coalesce(item, ["tool_name", "name", "function_name", "function", "api_name"])
    if isinstance(direct, str):
        return direct
    if isinstance(direct, dict):
        return str(_coalesce(direct, ["name", "function_name", "tool_name"], ""))
    return ""


def _normalize_user_request(item: Dict[str, Any]) -> str:
    direct = _coalesce(item, ["user_request", "question", "prompt", "instruction", "query"], "")
    if isinstance(direct, str):
        return direct
    if isinstance(direct, list):
        text_parts = []
        for part in direct:
            if isinstance(part, dict):
                content = part.get("content")
                if isinstance(content, str):
                    text_parts.append(content)
            elif isinstance(part, str):
                text_parts.append(part)
        return "\n".join(text_parts)
    return str(direct)


def load_benchmark_tasks(path: str | Path) -> List[EvalTask]:
    task_path = Path(path)
    if task_path.suffix.lower() == ".jsonl":
        raw_items = []
        with task_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    raw_items.append(json.loads(line))
    else:
        with task_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        raw_items = raw["data"] if isinstance(raw, dict) and "data" in raw else raw

    tasks: List[EvalTask] = []

    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            continue
        task_id = str(_coalesce(item, ["task_id", "id", "uid"], f"task_{index}"))
        tool_name = _normalize_tool_name(item)
        user_request = _normalize_user_request(item)
        expected_candidates = _normalize_ground_truth_candidates(item)
        if not tool_name or not user_request:
            continue
        raw_tags = _coalesce(item, ["tags", "labels"], [])
        tags = [str(tag) for tag in raw_tags] if isinstance(raw_tags, list) else []
        tasks.append(
            EvalTask(
                task_id=task_id,
                tool_name=tool_name,
                user_request=user_request,
                expected_arguments=expected_candidates[0] if expected_candidates else {},
                expected_argument_candidates=expected_candidates,
                split=str(_coalesce(item, ["split", "partition"], "default")),
                tags=tags,
            )
        )
    return tasks

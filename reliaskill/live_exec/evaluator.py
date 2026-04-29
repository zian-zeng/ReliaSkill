from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List

from reliaskill.live_exec.filesystem_sandbox import FilesystemSandbox
from reliaskill.live_exec.git_sandbox import GitSandbox
from reliaskill.live_exec.sqlite_sandbox import SQLiteSandbox


LIVE_RESULT_FIELDS = [
    "live_task_id",
    "domain",
    "tool_id",
    "difficulty",
    "predicted_call_valid",
    "execution_success",
    "observation_match",
    "state_match",
    "unsafe_action_blocked",
    "live_joint_success",
]


class LiveExecEvaluator:
    def evaluate_task(self, task: Dict[str, Any], predicted_call: Dict[str, Any] | None = None) -> Dict[str, Any]:
        call = predicted_call or task.get("expected_tool_call") or {}
        with tempfile.TemporaryDirectory(prefix="reliaskill_live_") as tmpdir:
            root = Path(tmpdir)
            sandbox = self._build_sandbox(task, root)
            before = sandbox.snapshot()
            predicted_call_valid = _call_valid(call)
            observation: Dict[str, Any]
            if predicted_call_valid:
                observation = sandbox.call(str(call.get("tool_name")), dict(call.get("arguments") or {}))
            else:
                observation = {"ok": False, "error": "invalid_predicted_call"}
            after = sandbox.snapshot()
            if hasattr(sandbox, "close"):
                sandbox.close()

        expected_observation = task.get("expected_observation") or {}
        expected_state_change = task.get("expected_state_change") or {}
        unsafe_action_blocked = bool(observation.get("unsafe_action_blocked")) or _forbidden_action_blocked(task, call, observation)
        execution_success = bool(observation.get("ok")) or unsafe_action_blocked
        observation_match = _matches_expected(observation, expected_observation)
        state_match = _state_matches(before, after, expected_state_change)
        live_joint_success = bool(predicted_call_valid and execution_success and observation_match and state_match and _forbidden_actions_respected(task, call, unsafe_action_blocked))
        return {
            "live_task_id": task["live_task_id"],
            "domain": task["domain"],
            "tool_id": task["tool_id"],
            "difficulty": task.get("difficulty", ""),
            "predicted_call_valid": predicted_call_valid,
            "execution_success": execution_success,
            "observation_match": observation_match,
            "state_match": state_match,
            "unsafe_action_blocked": unsafe_action_blocked,
            "live_joint_success": live_joint_success,
            "predicted_tool_name": call.get("tool_name") if isinstance(call, dict) else None,
            "predicted_arguments": call.get("arguments") if isinstance(call, dict) else None,
            "observation": observation,
            "expected_observation": expected_observation,
            "before_state": before,
            "after_state": after,
        }

    def _build_sandbox(self, task: Dict[str, Any], root: Path) -> Any:
        domain = task.get("domain")
        setup = task.get("initial_state_setup") or {}
        if domain == "filesystem":
            sandbox = FilesystemSandbox(root / "fs")
        elif domain == "sqlite":
            sandbox = SQLiteSandbox(root / "task.db")
        elif domain == "git":
            sandbox = GitSandbox(root / "repo")
        else:
            raise ValueError(f"Unsupported live execution domain: {domain}")
        sandbox.setup(setup)
        return sandbox


def load_live_tasks(path: str | Path) -> List[Dict[str, Any]]:
    tasks = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return tasks


def load_prediction_calls(path: str | Path | None) -> Dict[str, Dict[str, Any]]:
    if not path:
        return {}
    predictions = {}
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            task_id = item.get("live_task_id") or item.get("task_id")
            call = item.get("predicted_tool_call") or item.get("tool_call") or item.get("expected_tool_call")
            if task_id and isinstance(call, dict):
                predictions[str(task_id)] = call
    return predictions


def evaluate_live_exec_tasks(
    tasks: Iterable[Dict[str, Any]],
    predictions: Dict[str, Dict[str, Any]] | None = None,
    *,
    use_gold: bool = False,
) -> List[Dict[str, Any]]:
    evaluator = LiveExecEvaluator()
    predictions = predictions or {}
    results = []
    for task in tasks:
        predicted = task.get("expected_tool_call") if use_gold else predictions.get(task["live_task_id"])
        results.append(evaluator.evaluate_task(task, predicted))
    return results


def summarize_live_results(results: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows = list(results)
    total = len(rows)
    return {
        "num_tasks": total,
        "predicted_call_valid": _rate(rows, "predicted_call_valid"),
        "execution_success": _rate(rows, "execution_success"),
        "observation_match": _rate(rows, "observation_match"),
        "state_match": _rate(rows, "state_match"),
        "unsafe_action_blocked": _rate(rows, "unsafe_action_blocked"),
        "live_joint_success": _rate(rows, "live_joint_success"),
    }


def write_live_results_csv(path: str | Path, results: Iterable[Dict[str, Any]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LIVE_RESULT_FIELDS)
        writer.writeheader()
        for row in results:
            writer.writerow({field: row.get(field, "") for field in LIVE_RESULT_FIELDS})


def write_jsonl(path: str | Path, rows: Iterable[Dict[str, Any]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _call_valid(call: Any) -> bool:
    return isinstance(call, dict) and isinstance(call.get("tool_name"), str) and isinstance(call.get("arguments"), dict)


def _matches_expected(observation: Dict[str, Any], expected: Dict[str, Any]) -> bool:
    for key, expected_value in expected.items():
        actual = observation.get(key)
        if isinstance(expected_value, list):
            if actual != expected_value:
                return False
        elif isinstance(expected_value, dict):
            if not isinstance(actual, dict) or not _matches_expected(actual, expected_value):
                return False
        elif actual != expected_value:
            return False
    return True


def _state_matches(before: Dict[str, Any], after: Dict[str, Any], expected_change: Dict[str, Any]) -> bool:
    if not expected_change:
        return before == after
    mode = expected_change.get("type")
    if mode == "no_change":
        return before == after
    if mode == "filesystem_file_written":
        path = expected_change.get("path")
        content = expected_change.get("content")
        return after.get("files", {}).get(path) == content
    if mode == "sqlite_rows_changed":
        table = expected_change.get("table")
        min_delta = int(expected_change.get("min_delta", 1))
        before_rows = len(before.get("tables", {}).get(table, []))
        after_rows = len(after.get("tables", {}).get(table, []))
        return after_rows - before_rows >= min_delta
    if mode == "sqlite_value_updated":
        table = expected_change.get("table")
        key = expected_change.get("key")
        value = expected_change.get("value")
        return any(row.get(key) == value for row in after.get("tables", {}).get(table, []))
    if mode == "git_no_change":
        return before == after
    return False


def _forbidden_action_blocked(task: Dict[str, Any], call: Dict[str, Any], observation: Dict[str, Any]) -> bool:
    forbidden = set(task.get("forbidden_actions") or [])
    tool_name = str(call.get("tool_name", ""))
    if tool_name in forbidden and not observation.get("ok"):
        return True
    if "path_traversal" in forbidden and observation.get("error") == "path_traversal_blocked":
        return True
    if "network" in forbidden and observation.get("error") == "network_operation_blocked":
        return True
    return False


def _forbidden_actions_respected(task: Dict[str, Any], call: Dict[str, Any], unsafe_action_blocked: bool) -> bool:
    forbidden = set(task.get("forbidden_actions") or [])
    if not forbidden:
        return True
    if str(call.get("tool_name", "")) in forbidden:
        return unsafe_action_blocked
    if {"path_traversal", "network"}.intersection(forbidden):
        return unsafe_action_blocked
    return True


def _rate(rows: List[Dict[str, Any]], key: str) -> float:
    return round(sum(1 for row in rows if row.get(key)) / len(rows), 4) if rows else 0.0

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from autoskill.eval_types import EvalPrediction, EvalTask
from autoskill.ir import GeneratedSkill, ToolIR
from autoskill.predictor import HeuristicPredictorBackend


def load_eval_tasks(path: str | Path) -> List[EvalTask]:
    task_path = Path(path)
    with task_path.open("r", encoding="utf-8") as f:
        raw_tasks = json.load(f)
    return [
        EvalTask(
            task_id=item["task_id"],
            tool_name=item["tool_name"],
            user_request=item["user_request"],
            expected_arguments=item["expected_arguments"],
            expected_argument_candidates=[dict(item["expected_arguments"])],
        )
        for item in raw_tasks
    ]


def demo_predict_call(tool: ToolIR, skill: GeneratedSkill, task: EvalTask) -> EvalPrediction:
    return HeuristicPredictorBackend().predict(tool, skill, task)


def _required_argument_recall(expected: Dict[str, Any], predicted: Dict[str, Any], tool: ToolIR) -> float:
    required = [arg.name for arg in tool.arguments if arg.required]
    if not required:
        return 1.0
    hits = sum(1 for name in required if predicted.get(name) == expected.get(name))
    return hits / len(required)


def _normalize_predicted_arguments(tool: ToolIR, expected: Dict[str, Any], predicted: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(predicted)
    for arg in tool.arguments:
        if arg.name in normalized and arg.name not in expected and arg.default is not None:
            if normalized[arg.name] == arg.default:
                normalized.pop(arg.name)
    return normalized


def _score_against_expected(tool: ToolIR, expected: Dict[str, Any], predicted: Dict[str, Any]) -> Dict[str, Any]:
    normalized_predicted = _normalize_predicted_arguments(tool, expected, predicted)
    exact_match = normalized_predicted == expected

    expected_keys = set(expected.keys())
    predicted_keys = set(normalized_predicted.keys())
    correct_pairs = sum(1 for key in expected_keys if normalized_predicted.get(key) == expected.get(key))
    arg_validity = correct_pairs / len(expected_keys) if expected_keys else 1.0
    hallucinated_args = sorted(predicted_keys - expected_keys)
    required_recall = _required_argument_recall(expected, normalized_predicted, tool)

    return {
        "exact_match": exact_match,
        "argument_validity": round(arg_validity, 4),
        "required_argument_recall": round(required_recall, 4),
        "hallucinated_args": hallucinated_args,
        "predicted_arguments": normalized_predicted,
        "expected_arguments": expected,
    }


def score_prediction(task: EvalTask, tool: ToolIR, prediction: EvalPrediction) -> Dict[str, Any]:
    candidates = task.expected_argument_candidates or [task.expected_arguments]
    candidate_scores = [
        _score_against_expected(tool, expected_candidate, prediction.predicted_arguments)
        for expected_candidate in candidates
    ]
    best = max(
        candidate_scores,
        key=lambda item: (
            1 if item["exact_match"] else 0,
            item["argument_validity"],
            item["required_argument_recall"],
            -len(item["hallucinated_args"]),
        ),
    )

    return {
        "task_id": task.task_id,
        "tool_name": task.tool_name,
        "baseline_name": prediction.baseline_name,
        "exact_match": best["exact_match"],
        "argument_validity": best["argument_validity"],
        "required_argument_recall": best["required_argument_recall"],
        "hallucinated_args": best["hallucinated_args"],
        "predicted_arguments": best["predicted_arguments"],
        "expected_arguments": best["expected_arguments"],
        "num_gold_candidates": len(candidates),
    }


def summarize_task_scores(scores: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for score in scores:
        grouped.setdefault(score["baseline_name"], []).append(score)

    summary: Dict[str, Any] = {}
    for baseline_name, items in grouped.items():
        total = len(items)
        summary[baseline_name] = {
            "num_tasks": total,
            "exact_match_rate": round(sum(1 for item in items if item["exact_match"]) / total, 4) if total else 0.0,
            "avg_argument_validity": round(sum(item["argument_validity"] for item in items) / total, 4) if total else 0.0,
            "avg_required_argument_recall": round(sum(item["required_argument_recall"] for item in items) / total, 4) if total else 0.0,
            "hallucinated_argument_count": sum(len(item["hallucinated_args"]) for item in items),
        }
    return summary


def summarize_task_scores_by_tool(scores: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    grouped: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for score in scores:
        grouped.setdefault(score["tool_name"], {}).setdefault(score["baseline_name"], []).append(score)

    summary: Dict[str, Dict[str, Any]] = {}
    for tool_name, by_baseline in grouped.items():
        summary[tool_name] = {}
        for baseline_name, items in by_baseline.items():
            total = len(items)
            summary[tool_name][baseline_name] = {
                "num_tasks": total,
                "exact_match_rate": round(sum(1 for item in items if item["exact_match"]) / total, 4) if total else 0.0,
                "avg_argument_validity": round(sum(item["argument_validity"] for item in items) / total, 4) if total else 0.0,
                "avg_required_argument_recall": round(sum(item["required_argument_recall"] for item in items) / total, 4) if total else 0.0,
                "hallucinated_argument_count": sum(len(item["hallucinated_args"]) for item in items),
            }
    return summary

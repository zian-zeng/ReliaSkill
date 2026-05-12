from __future__ import annotations

import json
import random
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
            split=str(item.get("split", "default")),
            tags=[str(tag) for tag in item.get("tags", [])] if isinstance(item.get("tags", []), list) else [],
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

    retrieval_rank = prediction.metadata.get("retrieval_target_rank")
    selected_tool_name = prediction.metadata.get("selected_tool_name")
    retrieved_tool_candidates = list(prediction.metadata.get("retrieved_tool_candidates", []))
    retrieval_hit = None
    if isinstance(retrieval_rank, int):
        retrieval_hit = retrieval_rank <= max(len(retrieved_tool_candidates), 1)

    return {
        "task_id": task.task_id,
        "tool_name": task.tool_name,
        "baseline_name": prediction.baseline_name,
        "split": task.split,
        "tags": list(task.tags),
        "exact_match": best["exact_match"],
        "argument_validity": best["argument_validity"],
        "required_argument_recall": best["required_argument_recall"],
        "hallucinated_args": best["hallucinated_args"],
        "predicted_arguments": best["predicted_arguments"],
        "expected_arguments": best["expected_arguments"],
        "num_gold_candidates": len(candidates),
        "selected_tool_name": selected_tool_name,
        "retrieved_tool_candidates": retrieved_tool_candidates,
        "retrieval_target_rank": retrieval_rank,
        "retrieval_hit_at_k": retrieval_hit,
        "prediction_metadata": dict(prediction.metadata),
    }


def _bootstrap_confidence_interval(values: List[float], iterations: int = 500, seed: int = 13) -> Dict[str, float]:
    if not values:
        return {"low": 0.0, "high": 0.0}
    rng = random.Random(seed)
    means: List[float] = []
    for _ in range(iterations):
        sample = [values[rng.randrange(len(values))] for _ in range(len(values))]
        means.append(sum(sample) / len(sample))
    means.sort()
    low_index = int(0.025 * (len(means) - 1))
    high_index = int(0.975 * (len(means) - 1))
    return {
        "low": round(means[low_index], 4),
        "high": round(means[high_index], 4),
    }


def _summarize_item_group(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(items)
    exact_match_values = [1.0 if item["exact_match"] else 0.0 for item in items]
    exact_match_rate = round(sum(exact_match_values) / total, 4) if total else 0.0
    retrieval_hits = [1.0 if item.get("retrieval_hit_at_k") else 0.0 for item in items if item.get("retrieval_hit_at_k") is not None]
    retrieval_ranks = [float(item["retrieval_target_rank"]) for item in items if isinstance(item.get("retrieval_target_rank"), int)]
    return {
        "num_tasks": total,
        "exact_match_rate": exact_match_rate,
        "exact_match_ci": _bootstrap_confidence_interval(exact_match_values) if total else {"low": 0.0, "high": 0.0},
        "avg_argument_validity": round(sum(item["argument_validity"] for item in items) / total, 4) if total else 0.0,
        "avg_required_argument_recall": round(sum(item["required_argument_recall"] for item in items) / total, 4) if total else 0.0,
        "hallucinated_argument_count": sum(len(item["hallucinated_args"]) for item in items),
        "tool_retrieval_hit_rate": round(sum(retrieval_hits) / len(retrieval_hits), 4) if retrieval_hits else None,
        "avg_target_tool_rank": round(sum(retrieval_ranks) / len(retrieval_ranks), 4) if retrieval_ranks else None,
    }


def summarize_task_scores(scores: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for score in scores:
        grouped.setdefault(score["baseline_name"], []).append(score)

    summary: Dict[str, Any] = {}
    for baseline_name, items in grouped.items():
        summary[baseline_name] = _summarize_item_group(items)
    return summary


def summarize_task_scores_by_tool(scores: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    grouped: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for score in scores:
        grouped.setdefault(score["tool_name"], {}).setdefault(score["baseline_name"], []).append(score)

    summary: Dict[str, Dict[str, Any]] = {}
    for tool_name, by_baseline in grouped.items():
        summary[tool_name] = {}
        for baseline_name, items in by_baseline.items():
            summary[tool_name][baseline_name] = _summarize_item_group(items)
    return summary


def summarize_task_scores_by_split(scores: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    grouped: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for score in scores:
        grouped.setdefault(score.get("split", "default"), {}).setdefault(score["baseline_name"], []).append(score)

    summary: Dict[str, Dict[str, Any]] = {}
    for split_name, by_baseline in grouped.items():
        summary[split_name] = {}
        for baseline_name, items in by_baseline.items():
            summary[split_name][baseline_name] = _summarize_item_group(items)
    return summary


def summarize_pairwise_comparisons(
    scores: Iterable[Dict[str, Any]],
    anchor_baseline: str = "generated_skill_base",
    comparison_baselines: List[str] | None = None,
) -> Dict[str, Any]:
    comparison_baselines = comparison_baselines or ["raw_mcp", "schema_only", "retrieved_docs", "retrieved_candidates", "retrieved_memory"]
    by_task_and_baseline: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for score in scores:
        by_task_and_baseline.setdefault(score["task_id"], {})[score["baseline_name"]] = score

    summary: Dict[str, Any] = {}
    for baseline_name in comparison_baselines:
        paired_items: List[Dict[str, Any]] = []
        deltas: List[float] = []
        wins = 0
        ties = 0
        losses = 0
        for task_id, by_baseline in by_task_and_baseline.items():
            if anchor_baseline not in by_baseline or baseline_name not in by_baseline:
                continue
            anchor = by_baseline[anchor_baseline]
            other = by_baseline[baseline_name]
            exact_delta = (1.0 if anchor["exact_match"] else 0.0) - (1.0 if other["exact_match"] else 0.0)
            deltas.append(exact_delta)
            if exact_delta > 0:
                wins += 1
            elif exact_delta < 0:
                losses += 1
            else:
                ties += 1
            paired_items.append(
                {
                    "task_id": task_id,
                    "tool_name": anchor["tool_name"],
                    "split": anchor.get("split", "default"),
                    "anchor_exact_match": anchor["exact_match"],
                    "baseline_exact_match": other["exact_match"],
                    "anchor_argument_validity": anchor["argument_validity"],
                    "baseline_argument_validity": other["argument_validity"],
                }
            )

        total = len(paired_items)
        summary[baseline_name] = {
            "anchor_baseline": anchor_baseline,
            "comparison_baseline": baseline_name,
            "num_paired_tasks": total,
            "win_count": wins,
            "tie_count": ties,
            "loss_count": losses,
            "win_rate": round(wins / total, 4) if total else 0.0,
            "exact_match_delta": round(sum(deltas) / total, 4) if total else 0.0,
            "exact_match_delta_ci": _bootstrap_confidence_interval(deltas) if total else {"low": 0.0, "high": 0.0},
            "avg_argument_validity_delta": round(
                sum(item["anchor_argument_validity"] - item["baseline_argument_validity"] for item in paired_items) / total,
                4,
            ) if total else 0.0,
        }
    return summary

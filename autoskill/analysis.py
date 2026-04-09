from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List


def classify_score_error(score: Dict[str, Any]) -> str:
    if score.get("exact_match"):
        return "success"
    if score.get("hallucinated_args"):
        return "hallucinated_argument"
    if score.get("required_argument_recall", 1.0) < 1.0:
        if "semantic" in score.get("tags", []):
            return "semantic_missing_required_argument"
        return "missing_required_argument"
    tags = set(score.get("tags", []))
    if "semantic" in tags:
        return "semantic_mapping_failure"
    if "exclude" in tags:
        return "exclude_pattern_failure"
    if "head" in tags or "tail" in tags:
        return "range_direction_failure"
    if "write" in tags:
        return "content_extraction_failure"
    return "wrong_argument_value"


def summarize_error_taxonomy(scores: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for score in scores:
        grouped[str(score["baseline_name"])].append(score)

    summary: Dict[str, Any] = {}
    for baseline_name, items in grouped.items():
        failure_items = [item for item in items if not item.get("exact_match")]
        counter = Counter(classify_score_error(item) for item in failure_items)
        total_failures = len(failure_items)
        summary[baseline_name] = {
            "num_failures": total_failures,
            "error_type_counts": dict(sorted(counter.items())),
            "error_type_rates": {
                key: round(value / total_failures, 4) if total_failures else 0.0
                for key, value in sorted(counter.items())
            },
        }
    return summary


def summarize_method_wins(
    scores: Iterable[Dict[str, Any]],
    anchor_baseline: str = "autoskill_base",
    comparison_baselines: List[str] | None = None,
    max_examples: int = 5,
) -> Dict[str, Any]:
    comparison_baselines = comparison_baselines or ["raw_mcp", "schema_only", "retrieved_docs", "retrieved_candidates", "retrieved_memory"]
    by_task_and_baseline: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for score in scores:
        by_task_and_baseline.setdefault(str(score["task_id"]), {})[str(score["baseline_name"])] = score

    summary: Dict[str, Any] = {}
    for baseline_name in comparison_baselines:
        wins: List[Dict[str, Any]] = []
        by_tool = Counter()
        by_split = Counter()
        by_tag = Counter()
        by_error_type = Counter()

        for task_id, rows in by_task_and_baseline.items():
            anchor = rows.get(anchor_baseline)
            other = rows.get(baseline_name)
            if not anchor or not other:
                continue
            if not anchor.get("exact_match") or other.get("exact_match"):
                continue

            error_type = classify_score_error(other)
            tags = list(other.get("tags", []))
            by_tool.update([str(other.get("tool_name", "unknown"))])
            by_split.update([str(other.get("split", "default"))])
            by_error_type.update([error_type])
            for tag in tags:
                by_tag.update([str(tag)])

            wins.append(
                {
                    "task_id": task_id,
                    "tool_name": other.get("tool_name", "unknown"),
                    "split": other.get("split", "default"),
                    "tags": tags,
                    "baseline_error_type": error_type,
                    "baseline_predicted_arguments": other.get("predicted_arguments", {}),
                    "expected_arguments": other.get("expected_arguments", {}),
                    "user_request": other.get("user_request", ""),
                }
            )

        summary[baseline_name] = {
            "anchor_baseline": anchor_baseline,
            "comparison_baseline": baseline_name,
            "num_anchor_wins": len(wins),
            "wins_by_tool": dict(by_tool.most_common()),
            "wins_by_split": dict(by_split.most_common()),
            "wins_by_tag": dict(by_tag.most_common()),
            "wins_by_error_type": dict(by_error_type.most_common()),
            "example_wins": wins[:max_examples],
        }

    return summary

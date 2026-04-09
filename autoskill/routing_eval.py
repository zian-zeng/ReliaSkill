from __future__ import annotations

import random
import re
from typing import Any, Dict, Iterable, List, Tuple

from autoskill.eval_types import EvalTask
from autoskill.ir import GeneratedSkill, ToolIR
from autoskill.predictor import PredictorBackend, safe_predict
from autoskill.retrieval_runtime import (
    contextualize_skill_for_task,
    retrieve_candidate_tools,
    retrieve_doc_tool_rankings,
    retrieve_memory_tool_rankings,
)
from autoskill.task_eval import score_prediction


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9_./*?-]+", text.lower())


def _skill_router_text(tool: ToolIR, skill: GeneratedSkill) -> str:
    parts = [tool.tool_name, tool.tool_purpose or "", skill.skill_summary]
    parts.extend(skill.when_to_use)
    parts.extend(skill.when_not_to_use)
    for argument in tool.arguments:
        parts.append(argument.name)
        if argument.description:
            parts.append(argument.description)
    for example in skill.examples:
        parts.append(str(example.get("scenario", "")))
    for arg_name, spec in skill.semantic_hints.items():
        parts.append(arg_name)
        if isinstance(spec, dict):
            parts.extend(str(key) for key in spec.keys())
            parts.extend(str(value) for value in spec.values() if isinstance(value, (str, int, float)))
    return " ".join(part for part in parts if part)


def _router_overlap_score(query: str, text: str) -> int:
    query_tokens = _tokenize(query)
    text_tokens = set(_tokenize(text))
    overlap = set(query_tokens).intersection(text_tokens)
    score = 2 * len(overlap)
    if query.lower() in text.lower():
        score += 5
    return score


def _autoskill_routing_bonus(query: str, tool: ToolIR, skill: GeneratedSkill) -> int:
    lowered = query.lower()
    bonus = 0
    for arg_name, spec in skill.semantic_hints.items():
        if not isinstance(spec, dict):
            continue
        for cue in spec.keys():
            if cue in lowered:
                bonus += 4
        if arg_name in {"pattern", "excludePatterns"} and tool.tool_name == "search_files":
            bonus += 3
        if arg_name in {"head", "tail"} and tool.tool_name == "read_text_file":
            bonus += 3
        if arg_name == "content" and tool.tool_name == "write_file":
            bonus += 3
    return bonus


def select_tool_for_task(
    task: EvalTask,
    baseline_name: str,
    tools: Dict[str, ToolIR],
    skill_bank: Dict[str, GeneratedSkill],
    top_k: int = 3,
) -> Dict[str, Any]:
    if baseline_name == "retrieved_docs":
        candidates = retrieve_doc_tool_rankings(task.user_request, tools, top_k=top_k)["candidates"]
        return {
            "routing_strategy": "docs_retrieval",
            "selected_tool_name": candidates[0]["tool_name"] if candidates else task.tool_name,
            "candidate_tools": [item["tool_name"] for item in candidates],
            "candidate_rows": candidates,
        }

    if baseline_name == "retrieved_candidates":
        candidates = retrieve_candidate_tools(task.user_request, tools, top_k=top_k)["candidates"]
        return {
            "routing_strategy": "candidate_tool_retrieval",
            "selected_tool_name": candidates[0]["tool_name"] if candidates else task.tool_name,
            "candidate_tools": [item["tool_name"] for item in candidates],
            "candidate_rows": candidates,
        }

    if baseline_name == "retrieved_memory":
        candidates = retrieve_memory_tool_rankings(task.user_request, tools, top_k=top_k)["candidates"]
        return {
            "routing_strategy": "memory_retrieval",
            "selected_tool_name": candidates[0]["tool_name"] if candidates else task.tool_name,
            "candidate_tools": [item["tool_name"] for item in candidates],
            "candidate_rows": candidates,
        }

    if baseline_name == "autoskill_base":
        retrieval_rows = retrieve_candidate_tools(task.user_request, tools, top_k=max(len(tools), top_k))["candidates"]
        reranked: List[Dict[str, Any]] = []
        for row in retrieval_rows:
            tool_name = str(row["tool_name"])
            tool = tools[tool_name]
            skill = skill_bank[tool_name]
            rerank_score = (2 * int(row.get("score", 0))) + _router_overlap_score(task.user_request, _skill_router_text(tool, skill))
            rerank_score += _autoskill_routing_bonus(task.user_request, tool, skill)
            reranked.append(
                {
                    "tool_name": tool_name,
                    "score": rerank_score,
                    "retrieval_score": row.get("score", 0),
                    "overlap_terms": row.get("overlap_terms", []),
                }
            )
        reranked.sort(key=lambda item: (-int(item["score"]), item["tool_name"]))
        top_rows = reranked[: max(top_k, 1)]
        return {
            "routing_strategy": "retrieve_then_semantic_rerank",
            "selected_tool_name": top_rows[0]["tool_name"] if top_rows else task.tool_name,
            "candidate_tools": [item["tool_name"] for item in top_rows],
            "candidate_rows": top_rows,
        }

    ranked: List[Tuple[str, int]] = []
    for tool_name, tool in tools.items():
        skill = skill_bank[tool_name]
        score = _router_overlap_score(task.user_request, _skill_router_text(tool, skill))
        if baseline_name == "autoskill_base":
            score += _autoskill_routing_bonus(task.user_request, tool, skill)
        ranked.append((tool_name, score))
    ranked.sort(key=lambda item: (-item[1], item[0]))
    top_rows = [{"tool_name": tool_name, "score": score} for tool_name, score in ranked[: max(top_k, 1)]]
    return {
        "routing_strategy": "skill_text_overlap",
        "selected_tool_name": top_rows[0]["tool_name"] if top_rows else task.tool_name,
        "candidate_tools": [item["tool_name"] for item in top_rows],
        "candidate_rows": top_rows,
    }


def score_routed_prediction(
    gold_task: EvalTask,
    selected_tool_name: str,
    candidate_tools: List[str],
    predictor_record: Dict[str, Any],
) -> Dict[str, Any]:
    tool_correct = selected_tool_name == gold_task.tool_name
    argument_score = predictor_record["argument_score"]
    gold_rank = next((index + 1 for index, name in enumerate(candidate_tools) if name == gold_task.tool_name), None)
    return {
        "task_id": gold_task.task_id,
        "expected_tool_name": gold_task.tool_name,
        "selected_tool_name": selected_tool_name,
        "baseline_name": predictor_record["baseline_name"],
        "split": gold_task.split,
        "tags": list(gold_task.tags),
        "tool_selection_correct": tool_correct,
        "joint_exact_match": bool(tool_correct and argument_score["exact_match"]),
        "argument_exact_match_given_tool": bool(argument_score["exact_match"]),
        "argument_validity": round(argument_score["argument_validity"] if tool_correct else 0.0, 4),
        "required_argument_recall": round(argument_score["required_argument_recall"] if tool_correct else 0.0, 4),
        "hallucinated_args": argument_score["hallucinated_args"] if tool_correct else sorted(predictor_record["predicted_arguments"].keys()),
        "predicted_arguments": predictor_record["predicted_arguments"],
        "expected_arguments": gold_task.expected_arguments,
        "candidate_tools": list(candidate_tools),
        "gold_tool_rank": gold_rank,
        "gold_tool_hit_at_k": gold_rank is not None,
        "routing_strategy": predictor_record["routing_strategy"],
        "prediction_metadata": predictor_record["prediction_metadata"],
    }


def run_routing_pipeline(
    tasks: List[EvalTask],
    tools: Dict[str, ToolIR],
    skill_variants_by_tool: Dict[str, Dict[str, GeneratedSkill]],
    predictor: PredictorBackend,
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for task in tasks:
        for baseline_name in next(iter(skill_variants_by_tool.values())).keys():
            skill_bank = {tool_name: variants[baseline_name] for tool_name, variants in skill_variants_by_tool.items()}
            routing = select_tool_for_task(task, baseline_name, tools, skill_bank)
            selected_tool_name = str(routing["selected_tool_name"])
            selected_tool = tools[selected_tool_name]
            selected_skill = skill_bank[selected_tool_name]
            routed_task = EvalTask(
                task_id=task.task_id,
                tool_name=selected_tool_name,
                user_request=task.user_request,
                expected_arguments=task.expected_arguments,
                expected_argument_candidates=task.expected_argument_candidates,
                split=task.split,
                tags=list(task.tags),
            )
            runtime_skill, retrieval_context = contextualize_skill_for_task(routed_task, selected_tool, selected_skill, tools)
            prediction = safe_predict(selected_tool, runtime_skill, routed_task, predictor)
            prediction.tool_name = selected_tool_name
            argument_score = score_prediction(routed_task, selected_tool, prediction)
            records.append(
                score_routed_prediction(
                    task,
                    selected_tool_name=selected_tool_name,
                    candidate_tools=list(routing["candidate_tools"]),
                    predictor_record={
                        "baseline_name": baseline_name,
                        "predicted_arguments": dict(prediction.predicted_arguments),
                        "argument_score": argument_score,
                        "routing_strategy": routing["routing_strategy"],
                        "prediction_metadata": {
                            **prediction.metadata,
                            "routing_candidate_rows": routing["candidate_rows"],
                            "retrieval_context": retrieval_context,
                        },
                    },
                )
            )
    return records


def _bootstrap_confidence_interval(values: List[float], iterations: int = 500, seed: int = 17) -> Dict[str, float]:
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
    return {"low": round(means[low_index], 4), "high": round(means[high_index], 4)}


def _summarize_routing_group(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(items)
    tool_selection = [1.0 if item["tool_selection_correct"] else 0.0 for item in items]
    joint = [1.0 if item["joint_exact_match"] else 0.0 for item in items]
    hit_values = [1.0 if item["gold_tool_hit_at_k"] else 0.0 for item in items if item.get("gold_tool_hit_at_k") is not None]
    gold_ranks = [float(item["gold_tool_rank"]) for item in items if isinstance(item.get("gold_tool_rank"), int)]
    return {
        "num_tasks": total,
        "tool_selection_accuracy": round(sum(tool_selection) / total, 4) if total else 0.0,
        "tool_selection_accuracy_ci": _bootstrap_confidence_interval(tool_selection) if total else {"low": 0.0, "high": 0.0},
        "joint_exact_match_rate": round(sum(joint) / total, 4) if total else 0.0,
        "joint_exact_match_ci": _bootstrap_confidence_interval(joint) if total else {"low": 0.0, "high": 0.0},
        "avg_argument_validity": round(sum(item["argument_validity"] for item in items) / total, 4) if total else 0.0,
        "avg_required_argument_recall": round(sum(item["required_argument_recall"] for item in items) / total, 4) if total else 0.0,
        "gold_tool_hit_rate": round(sum(hit_values) / len(hit_values), 4) if hit_values else None,
        "avg_gold_tool_rank": round(sum(gold_ranks) / len(gold_ranks), 4) if gold_ranks else None,
    }


def summarize_routing_scores(scores: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for score in scores:
        grouped.setdefault(str(score["baseline_name"]), []).append(score)
    return {baseline_name: _summarize_routing_group(items) for baseline_name, items in grouped.items()}


def summarize_routing_scores_by_tool(scores: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    grouped: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for score in scores:
        grouped.setdefault(str(score["expected_tool_name"]), {}).setdefault(str(score["baseline_name"]), []).append(score)
    return {
        tool_name: {baseline_name: _summarize_routing_group(items) for baseline_name, items in by_baseline.items()}
        for tool_name, by_baseline in grouped.items()
    }


def summarize_routing_scores_by_split(scores: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    grouped: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for score in scores:
        grouped.setdefault(str(score["split"]), {}).setdefault(str(score["baseline_name"]), []).append(score)
    return {
        split_name: {baseline_name: _summarize_routing_group(items) for baseline_name, items in by_baseline.items()}
        for split_name, by_baseline in grouped.items()
    }

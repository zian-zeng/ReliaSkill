from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List

from autoskill.benchmark import load_benchmark_tasks
from autoskill.eval_types import EvalPrediction, EvalTask
from autoskill.ir import BehaviorCase, BehaviorReport, BehaviorResult, GeneratedSkill, ToolIR
from autoskill.predictor import HeuristicPredictorBackend, PredictorBackend, safe_predict
from autoskill.task_eval import score_prediction


STOPWORDS = {
    "a", "an", "and", "are", "as", "for", "from", "in", "into", "is", "it",
    "of", "on", "or", "the", "this", "to", "tool", "use", "when", "with",
}


def _tokens(text: str) -> set[str]:
    tokens = set()
    for token in re.findall(r"[a-z0-9_./*?-]+", text.lower()):
        normalized = token.strip(".,;:!?")
        if normalized and normalized not in STOPWORDS and len(normalized) > 1:
            tokens.add(normalized)
    return tokens


def _skill_trigger_text(tool: ToolIR, skill: GeneratedSkill) -> str:
    parts = [
        tool.tool_name.replace("_", " "),
        tool.tool_purpose or "",
        skill.skill_summary,
        *skill.when_to_use,
    ]
    for arg in tool.arguments:
        parts.append(arg.name.replace("_", " "))
        if arg.description:
            parts.append(arg.description)
    for example in skill.examples:
        parts.append(str(example.get("scenario", "")))
    return " ".join(parts)


def _negative_boundary_suppresses(skill: GeneratedSkill, request_tokens: set[str], user_request: str) -> bool:
    request_lower = user_request.lower().strip()
    for line in skill.when_not_to_use:
        line_lower = line.lower()
        if _category_boundary_suppresses(line_lower, request_lower):
            return True
        if "requests like:" in line_lower:
            exemplar = line_lower.split("requests like:", 1)[1].strip().strip(".")
            if exemplar and (exemplar in request_lower or request_lower in exemplar):
                return True
            boundary_overlap = request_tokens.intersection(_tokens(exemplar))
            if len(boundary_overlap) >= 2:
                return True
        elif "adjacent" in line_lower or "do not use" in line_lower:
            boundary_overlap = request_tokens.intersection(_tokens(line))
            if len(boundary_overlap) >= 4:
                return True
    return False


def _has_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _category_boundary_suppresses(line_lower: str, request_lower: str) -> bool:
    if "out-of-domain" in line_lower and _has_any(request_lower, ("unrelated to", "out of domain")):
        return True
    if _has_any(line_lower, ("explanation", "planning-only", "no-tool-call", "checklist")) and _has_any(
        request_lower,
        ("explain", "checklist", "planning only", "no tool call", "no tool yet", "do not actually call", "do not call", "don't call"),
    ):
        return True
    if _has_any(line_lower, ("missing required information", "required inputs are missing")) and _has_any(
        request_lower,
        ("do not know", "don't know", "missing", "not sure what input", "lacks required"),
    ):
        return True
    if "ambiguous" in line_lower and _has_any(request_lower, ("maybe do something", "not sure", "ambiguous", "what input or action")):
        return True
    if _has_any(line_lower, ("destructive/read-only", "read/write", "read-only/destructive")) and _has_any(
        request_lower,
        ("only inspect", "not a read-only lookup", "do not create", "do not update", "do not delete", "do not send", "do not execute", "do not mutate"),
    ):
        return True
    if _has_any(line_lower, ("known path", "no search or discovery")) and _has_any(
        request_lower,
        ("already know the exact path", "no search or discovery is needed"),
    ):
        return True
    if "read/search mismatch" in line_lower and _has_any(request_lower, ("do not search", "do not search, retrieve", "read the exact item")):
        return True
    if _has_any(line_lower, ("similar tool", "distractor")) and _has_any(request_lower, ("distractor", "should not be called")):
        return True
    if "adjacent intent" in line_lower and _has_any(request_lower, ("adjacent to", "intended capability is")):
        return True
    return False


def skill_should_trigger(tool: ToolIR, skill: GeneratedSkill, user_request: str) -> bool:
    if skill.metadata.get("gate_decision") and skill.metadata.get("gate_decision") != "deploy":
        return False
    request_tokens = _tokens(user_request)
    if not request_tokens:
        return False
    if _negative_boundary_suppresses(skill, request_tokens, user_request):
        return False
    trigger_tokens = _tokens(_skill_trigger_text(tool, skill))
    overlap = request_tokens.intersection(trigger_tokens)
    if tool.tool_name.lower() in user_request.lower():
        return True
    for arg_name, spec in skill.semantic_hints.items():
        if isinstance(spec, dict) and any(str(cue).lower() in user_request.lower() for cue in spec):
            return True
        if arg_name.lower() in user_request.lower():
            return True
    return len(overlap) >= 2


def behavior_cases_from_tasks(tasks: Iterable[EvalTask]) -> List[BehaviorCase]:
    cases: List[BehaviorCase] = []
    for task in tasks:
        cases.append(
            BehaviorCase(
                case_id=task.task_id,
                tool_name=task.tool_name,
                user_request=task.user_request,
                should_trigger=task.should_trigger,
                expected_arguments=dict(task.expected_arguments),
                expected_argument_candidates=[dict(item) for item in task.expected_argument_candidates],
                expected_tool_name=task.expected_tool_name,
                negative_target=task.negative_target,
                negative_category=task.negative_category,
                difficulty=task.difficulty,
                domain=task.domain,
                harm_baseline=task.harm_baseline,
                split=task.split,
                tags=list(task.tags),
            )
        )
    return cases


def load_behavior_cases(path: str | Path) -> List[BehaviorCase]:
    return behavior_cases_from_tasks(load_benchmark_tasks(path))


def run_behavior_tests(
    tool: ToolIR,
    skill: GeneratedSkill,
    cases: Iterable[BehaviorCase],
    predictor: PredictorBackend | None = None,
    *,
    allow_predictor_fallback: bool = True,
) -> BehaviorReport:
    predictor = predictor or HeuristicPredictorBackend()
    results: List[BehaviorResult] = []

    for case in cases:
        applies_to_tool = case.tool_name == tool.tool_name or case.negative_target == tool.tool_name
        if not applies_to_tool:
            continue
        triggered = skill_should_trigger(tool, skill, case.user_request)

        if case.should_trigger:
            task = EvalTask(
                task_id=case.case_id,
                tool_name=tool.tool_name,
                user_request=case.user_request,
                expected_arguments=case.expected_arguments,
                expected_argument_candidates=case.expected_argument_candidates or [case.expected_arguments],
                should_trigger=True,
                split=case.split,
                tags=list(case.tags),
                negative_category=case.negative_category,
                difficulty=case.difficulty,
                domain=case.domain,
                conversation_history=[],
                artifact_context={},
                tool_observation_context=[],
            )
            start = time.perf_counter()
            prediction = safe_predict(tool, skill, task, predictor, allow_fallback=allow_predictor_fallback)
            latency_ms = (time.perf_counter() - start) * 1000.0
            score = score_prediction(task, tool, prediction)
            results.append(
                BehaviorResult(
                    case_id=case.case_id,
                    tool_name=tool.tool_name,
                    should_trigger=True,
                    negative_category=case.negative_category,
                    triggered=triggered,
                    user_request=case.user_request,
                    exact_match=bool(score["exact_match"]),
                    argument_validity=float(score["argument_validity"]),
                    harmful_injection=False,
                    predicted_arguments=dict(score["predicted_arguments"]),
                    expected_arguments=dict(score["expected_arguments"]),
                    prediction_latency_ms=round(latency_ms, 4),
                    notes=[] if triggered else ["positive_control_not_triggered"],
                    prediction_metadata=dict(prediction.metadata),
                )
            )
        else:
            predicted_arguments: Dict[str, Any] = {}
            if triggered:
                task = EvalTask(
                    task_id=case.case_id,
                    tool_name=tool.tool_name,
                    user_request=case.user_request,
                    expected_arguments={},
                    expected_argument_candidates=[{}],
                    should_trigger=False,
                    negative_category=case.negative_category,
                    difficulty=case.difficulty,
                    domain=case.domain,
                    split=case.split,
                    tags=list(case.tags),
                    conversation_history=[],
                    artifact_context={},
                    tool_observation_context=[],
                )
                start = time.perf_counter()
                prediction: EvalPrediction = safe_predict(tool, skill, task, predictor, allow_fallback=allow_predictor_fallback)
                latency_ms = (time.perf_counter() - start) * 1000.0
                predicted_arguments = dict(prediction.predicted_arguments)
            else:
                latency_ms = 0.0
            results.append(
                BehaviorResult(
                    case_id=case.case_id,
                    tool_name=tool.tool_name,
                    should_trigger=False,
                    negative_category=case.negative_category,
                    triggered=triggered,
                    user_request=case.user_request,
                    exact_match=not triggered,
                    argument_validity=1.0 if not triggered else 0.0,
                    harmful_injection=triggered,
                    predicted_arguments=predicted_arguments,
                    expected_arguments={},
                    prediction_latency_ms=round(latency_ms, 4),
                    notes=["negative_control_triggered"] if triggered else [],
                    prediction_metadata=dict(prediction.metadata) if triggered else {},
                )
            )

    positive = [item for item in results if item.should_trigger]
    negative = [item for item in results if not item.should_trigger]
    tp = sum(1 for item in positive if item.triggered)
    fn = sum(1 for item in positive if not item.triggered)
    fp = sum(1 for item in negative if item.triggered)
    tn = sum(1 for item in negative if not item.triggered)
    exact_values = [1.0 if item.exact_match else 0.0 for item in positive]
    arg_values = [item.argument_validity for item in positive]
    latency_values = [item.prediction_latency_ms for item in results]

    metrics = {
        "num_cases": len(results),
        "positive_cases": len(positive),
        "negative_cases": len(negative),
        "trigger_true_positive": tp,
        "trigger_false_negative": fn,
        "trigger_false_positive": fp,
        "trigger_true_negative": tn,
        "trigger_precision": round(tp / (tp + fp), 4) if (tp + fp) else 1.0,
        "trigger_recall": round(tp / (tp + fn), 4) if (tp + fn) else 1.0,
        "harmful_skill_injection_rate": round(fp / len(negative), 4) if negative else 0.0,
        "exact_match_rate": round(sum(exact_values) / len(exact_values), 4) if exact_values else 0.0,
        "avg_argument_validity": round(sum(arg_values) / len(arg_values), 4) if arg_values else 0.0,
        "avg_prediction_latency_ms": round(sum(latency_values) / len(latency_values), 4) if latency_values else 0.0,
    }
    valid = metrics["harmful_skill_injection_rate"] == 0.0 and metrics["trigger_recall"] >= 0.5
    return BehaviorReport(valid=valid, results=results, metrics=metrics)

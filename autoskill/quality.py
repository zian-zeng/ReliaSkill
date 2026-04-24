from __future__ import annotations

from typing import Any, Dict, Iterable

from autoskill.artifacts import skill_token_count
from autoskill.ir import BehaviorReport, GeneratedSkill, ReliabilityScore, ToolIR, ValidationReport


def _argument_coverage(tool: ToolIR, skill: GeneratedSkill) -> float:
    arg_names = {arg.name for arg in tool.arguments}
    if not arg_names:
        return 1.0
    covered = set(skill.argument_template).intersection(arg_names)
    for example in skill.examples:
        args = example.get("arguments", {})
        if isinstance(args, dict):
            covered.update(set(args).intersection(arg_names))
    return round(len(covered) / len(arg_names), 4)


def _required_coverage(tool: ToolIR, skill: GeneratedSkill) -> float:
    required = {arg.name for arg in tool.arguments if arg.required}
    if not required:
        return 1.0
    covered = set(skill.argument_template).intersection(required)
    for example in skill.examples:
        args = example.get("arguments", {})
        if isinstance(args, dict):
            covered.update(set(args).intersection(required))
    return round(len(covered) / len(required), 4)


def _enum_coverage(tool: ToolIR, skill: GeneratedSkill) -> float:
    enum_args = [arg for arg in tool.arguments if arg.enum]
    if not enum_args:
        return 1.0
    covered = 0
    for arg in enum_args:
        values = []
        if arg.name in skill.argument_template:
            values.append(skill.argument_template[arg.name])
        for example in skill.examples:
            args = example.get("arguments", {})
            if isinstance(args, dict) and arg.name in args:
                values.append(args[arg.name])
        if any(value in (arg.enum or []) for value in values):
            covered += 1
    return round(covered / len(enum_args), 4)


def score_reliability(
    tool: ToolIR,
    skill: GeneratedSkill,
    validation_report: ValidationReport,
    behavior_report: BehaviorReport | None = None,
    repair_rounds: int = 0,
    deploy_threshold: float = 70.0,
    max_repair_rounds: int = 2,
) -> ReliabilityScore:
    error_count = sum(1 for issue in validation_report.issues if issue.severity == "error")
    warning_count = sum(1 for issue in validation_report.issues if issue.severity == "warning")
    repairable_count = sum(1 for issue in validation_report.issues if issue.repairable)
    token_count = skill_token_count(skill)
    argument_coverage = _argument_coverage(tool, skill)
    required_coverage = _required_coverage(tool, skill)
    enum_coverage = _enum_coverage(tool, skill)
    compactness = 1.0 if token_count <= 250 else max(0.0, 1.0 - ((token_count - 250) / 500))

    behavior_metrics = behavior_report.metrics if behavior_report else {}
    trigger_precision = float(behavior_metrics.get("trigger_precision", 1.0))
    trigger_recall = float(behavior_metrics.get("trigger_recall", 1.0))
    harmful_rate = float(behavior_metrics.get("harmful_skill_injection_rate", 0.0))
    behavior_exact = float(behavior_metrics.get("exact_match_rate", 0.0 if behavior_report else 1.0))
    avg_latency_ms = float(behavior_metrics.get("avg_prediction_latency_ms", 0.0))

    score = 50.0
    score -= 25.0 * error_count
    score -= 6.0 * warning_count
    score -= 7.0 * repair_rounds
    score -= 35.0 * harmful_rate
    score += 8.0 * argument_coverage
    score += 8.0 * required_coverage
    score += 5.0 * enum_coverage
    score += 5.0 * compactness
    score += 10.0 * trigger_precision
    score += 10.0 * trigger_recall
    score += 8.0 * behavior_exact
    score = round(max(0.0, min(score, 100.0)), 4)

    rationale = []
    if error_count:
        rationale.append(f"{error_count} structural validation error(s)")
    if warning_count:
        rationale.append(f"{warning_count} validation warning(s)")
    if harmful_rate > 0:
        rationale.append(f"harmful injection rate {harmful_rate:.4f}")
    if repair_rounds:
        rationale.append(f"{repair_rounds} repair round(s)")
    if not rationale:
        rationale.append("structurally valid and behavior-safe under available controls")

    behavior_safe = behavior_report.valid if behavior_report is not None else True
    if validation_report.valid and behavior_safe and harmful_rate == 0.0 and score >= deploy_threshold:
        decision = "deploy"
    elif repairable_count and repair_rounds < max_repair_rounds:
        decision = "repair"
    else:
        decision = "reject"

    features: Dict[str, Any] = {
        "validation_error_count": error_count,
        "validation_warning_count": warning_count,
        "repairable_issue_count": repairable_count,
        "schema_argument_coverage": argument_coverage,
        "required_argument_coverage": required_coverage,
        "enum_argument_coverage": enum_coverage,
        "compactness": round(compactness, 4),
        "token_overhead_estimate": token_count,
        "repair_rounds": repair_rounds,
        "trigger_precision": trigger_precision,
        "trigger_recall": trigger_recall,
        "harmful_skill_injection_rate": harmful_rate,
        "behavior_exact_match_rate": behavior_exact,
        "avg_prediction_latency_ms": avg_latency_ms,
    }
    return ReliabilityScore(score=score, decision=decision, features=features, rationale=rationale, threshold=deploy_threshold)

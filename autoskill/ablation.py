from __future__ import annotations

import csv
import json
import random
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List

from autoskill.artifacts import apply_skill_ablation, clone_skill_as
from autoskill.behavior import load_behavior_cases, run_behavior_tests
from autoskill.conditions import build_full_regeneration_repair
from autoskill.experiment import load_tools
from autoskill.generator import SkillGenerator
from autoskill.ir import BehaviorCase, BehaviorReport, GeneratedSkill, ReliabilityScore, ToolIR
from autoskill.metrics import bootstrap_ci, wilson_interval
from autoskill.predictor import build_predictor_from_config
from autoskill.quality import score_reliability
from autoskill.reliability_score import compute_reliability_score_value
from autoskill.repair import repair_behavior_failures, repair_skill
from autoskill.validator import validate_skill


DEFAULT_ABLATION_CONDITIONS: List[Dict[str, Any]] = [
    {"id": "full_reliaskill", "label": "full ReliaSkill"},
    {"id": "without_validation", "label": "w/o validation", "validation": False, "targeted_repair": False},
    {"id": "without_behavior_tests", "label": "w/o behavior tests", "behavior_tests": False, "behavior_repair": False},
    {"id": "without_positive_controls", "label": "w/o positive controls", "positive_controls": False},
    {"id": "without_negative_controls", "label": "w/o negative controls", "negative_controls": False},
    {"id": "without_repair", "label": "w/o repair", "targeted_repair": False, "behavior_repair": False},
    {
        "id": "full_regeneration_repair",
        "label": "full regeneration instead of targeted repair",
        "full_regeneration_repair": True,
        "targeted_repair": False,
    },
    {"id": "without_gating", "label": "w/o gating", "gating": False},
    {"id": "without_non_use_boundaries", "label": "w/o non-use boundaries", "non_use_boundaries": False},
    {"id": "without_examples", "label": "w/o examples", "examples": False},
    {"id": "without_compactness_constraint", "label": "w/o compactness constraint", "compactness_constraint": False},
    {"id": "dev_test_leakage_check", "label": "dev/test leakage check", "leakage_check": True},
]

DEFAULTS: Dict[str, Any] = {
    "validation": True,
    "behavior_tests": True,
    "positive_controls": True,
    "negative_controls": True,
    "targeted_repair": True,
    "behavior_repair": True,
    "full_regeneration_repair": False,
    "gating": True,
    "non_use_boundaries": True,
    "examples": True,
    "compactness_constraint": True,
    "leakage_check": False,
}

ABLATED_RESULT_FIELDS = [
    "ablation",
    "condition_id",
    "num_tools",
    "num_test_cases",
    "positive_test_cases",
    "negative_test_cases",
    "joint_em",
    "joint_em_ci_low",
    "joint_em_ci_high",
    "argument_validity",
    "argument_validity_ci_low",
    "argument_validity_ci_high",
    "trigger_precision",
    "trigger_precision_ci_low",
    "trigger_precision_ci_high",
    "hsir",
    "hsir_ci_low",
    "hsir_ci_high",
    "score",
    "score_ci_low",
    "score_ci_high",
    "avg_repair_rounds",
    "dev_test_leakage_count",
    "dev_test_leakage_rate",
]


def run_ablation_table_from_config(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    tools = load_tools(config["tools_path"])
    selected_tools = _select_tools(tools, config)
    dev_cases = load_behavior_cases(config["dev_controls_path"])
    test_cases = load_behavior_cases(config["test_controls_path"])
    generator = SkillGenerator(backend_config=config.get("generator"))
    predictor = build_predictor_from_config(config.get("predictor"))
    seed = int(config.get("seed", 42))

    rows: List[Dict[str, Any]] = []
    detail_records: List[Dict[str, Any]] = []
    for raw_condition in _configured_conditions(config):
        condition = {**DEFAULTS, **raw_condition}
        per_tool: List[Dict[str, Any]] = []
        for tool in selected_tools:
            record = _run_tool_condition(tool, selected_tools, condition, dev_cases, test_cases, generator, predictor, seed)
            per_tool.append(record)
            detail_records.append(_compact_detail_record(record))
        row = _aggregate_condition(condition, per_tool, seed=seed)
        if condition["leakage_check"]:
            row.update(_leakage_check_stats(selected_tools, dev_cases, test_cases))
        rows.append(row)

    output_path = Path(config.get("output_path", "outputs/tables/ablation_results.csv"))
    write_ablation_results_csv(output_path, rows)
    details_path = Path(config.get("details_path", "outputs/ablations/ablation_details.jsonl"))
    _write_jsonl(details_path, detail_records)
    return rows


def write_ablation_results_csv(path: str | Path, rows: Iterable[Dict[str, Any]]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ABLATED_RESULT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in ABLATED_RESULT_FIELDS})


def _configured_conditions(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    conditions = config.get("conditions") or DEFAULT_ABLATION_CONDITIONS
    return [dict(item) for item in conditions]


def _select_tools(tools: Dict[str, ToolIR], config: Dict[str, Any]) -> List[ToolIR]:
    names = config.get("tool_names")
    if names:
        selected_names = [str(name) for name in names if str(name) in tools]
    else:
        selected_names = sorted(tools)
    max_tools = config.get("max_tools")
    if max_tools:
        selected_names = selected_names[: int(max_tools)]
    return [tools[name] for name in selected_names]


def _run_tool_condition(
    tool: ToolIR,
    tools: List[ToolIR],
    condition: Dict[str, Any],
    dev_cases: List[BehaviorCase],
    test_cases: List[BehaviorCase],
    generator: SkillGenerator,
    predictor: Any,
    seed: int,
) -> Dict[str, Any]:
    skill = generator.generate(tool)
    skill = _condition_skill(tool, {item.tool_name: item for item in tools}, skill, condition)

    repair_rounds = 0
    if condition["validation"] and condition["targeted_repair"] and not condition["full_regeneration_repair"]:
        skill, repair_report, validation_report = repair_skill(tool, skill)
        repair_rounds += repair_report.rounds
    else:
        validation_report = validate_skill(tool, skill)

    behavior_for_score: BehaviorReport | None = None
    if condition["behavior_tests"]:
        training_cases = _filter_cases_for_condition(dev_cases, condition)
        behavior_for_score = run_behavior_tests(tool, skill, training_cases, predictor=predictor)
        if condition["behavior_repair"] and condition["targeted_repair"] and not behavior_for_score.valid:
            skill, behavior_repair_report, validation_report = repair_behavior_failures(tool, skill, behavior_for_score)
            repair_rounds += behavior_repair_report.rounds
            behavior_for_score = run_behavior_tests(tool, skill, training_cases, predictor=predictor)

    score = score_reliability(tool, skill, validation_report, behavior_for_score, repair_rounds=repair_rounds)
    if not condition["compactness_constraint"]:
        score = _neutralize_compactness(score, repair_rounds)

    measurement_skill = _apply_gating_if_enabled(skill, score, condition)
    test_report = run_behavior_tests(tool, measurement_skill, test_cases, predictor=predictor)
    return {
        "condition_id": condition["id"],
        "ablation": condition.get("label", condition["id"]),
        "tool_name": tool.tool_name,
        "skill": measurement_skill,
        "validation_report": validation_report,
        "score": score,
        "test_report": test_report,
        "repair_rounds": repair_rounds,
        "seed": seed,
    }


def _condition_skill(tool: ToolIR, tools: Dict[str, ToolIR], base_skill: GeneratedSkill, condition: Dict[str, Any]) -> GeneratedSkill:
    if condition["full_regeneration_repair"]:
        skill = build_full_regeneration_repair(tool, base_skill)
    else:
        skill = clone_skill_as(base_skill, condition["id"])
    if not condition["non_use_boundaries"]:
        skill.when_not_to_use = []
    if not condition["examples"]:
        skill.examples = []
    if not condition["compactness_constraint"]:
        skill = apply_skill_ablation(skill, "verbose")
    skill.baseline_name = condition["id"]
    skill.metadata = {
        **skill.metadata,
        "ablation_condition": condition["id"],
        "ablation_flags": {key: condition[key] for key in DEFAULTS if key in condition},
    }
    return skill


def _filter_cases_for_condition(cases: Iterable[BehaviorCase], condition: Dict[str, Any]) -> List[BehaviorCase]:
    filtered: List[BehaviorCase] = []
    for case in cases:
        if case.should_trigger and not condition["positive_controls"]:
            continue
        if not case.should_trigger and not condition["negative_controls"]:
            continue
        filtered.append(case)
    return filtered


def _apply_gating_if_enabled(skill: GeneratedSkill, score: ReliabilityScore, condition: Dict[str, Any]) -> GeneratedSkill:
    gated = deepcopy(skill)
    if condition["gating"]:
        gated.baseline_name = "gated_skill"
        gated.metadata = {**gated.metadata, "gate_decision": score.decision, "gate_score": score.score}
    else:
        gated.baseline_name = condition["id"]
        gated.metadata = {**gated.metadata, "gate_decision": "disabled", "gate_score": score.score}
    return gated


def _neutralize_compactness(score: ReliabilityScore, repair_rounds: int) -> ReliabilityScore:
    updated = deepcopy(score)
    components = dict(updated.features.get("components", {}))
    components["C"] = 1.0
    updated.score = compute_reliability_score_value(components, repair_rounds=repair_rounds)
    updated.features = {
        **updated.features,
        "components": components,
        "compactness_constraint_applied": False,
        "ablation_note": "compactness component is neutralized for this condition",
    }
    return updated


def _aggregate_condition(condition: Dict[str, Any], records: List[Dict[str, Any]], seed: int) -> Dict[str, Any]:
    results = [result for record in records for result in record["test_report"].results]
    positives = [item for item in results if item.should_trigger]
    negatives = [item for item in results if not item.should_trigger]
    joint_values = [1.0 if item.triggered and item.exact_match else 0.0 for item in positives]
    argument_values = [float(item.argument_validity) for item in positives]
    precision_values = _precision_indicator_values(positives, negatives)
    hsir_values = [1.0 if item.harmful_injection else 0.0 for item in negatives]
    score_values = [float(record["score"].score) for record in records]
    repair_values = [float(record["repair_rounds"]) for record in records]

    joint_successes = sum(1 for value in joint_values if value)
    joint_ci = wilson_interval(joint_successes, len(joint_values))
    argument_ci = bootstrap_ci(argument_values, iterations=250, seed=seed)
    precision_ci = bootstrap_ci(precision_values, iterations=250, seed=seed) if precision_values else {"low": 1.0, "high": 1.0}
    hsir_ci = wilson_interval(sum(1 for value in hsir_values if value), len(hsir_values))
    score_ci = bootstrap_ci(score_values, iterations=250, seed=seed)

    return {
        "ablation": condition.get("label", condition["id"]),
        "condition_id": condition["id"],
        "num_tools": len(records),
        "num_test_cases": len(results),
        "positive_test_cases": len(positives),
        "negative_test_cases": len(negatives),
        "joint_em": _mean(joint_values),
        "joint_em_ci_low": joint_ci["low"],
        "joint_em_ci_high": joint_ci["high"],
        "argument_validity": _mean(argument_values),
        "argument_validity_ci_low": argument_ci["low"],
        "argument_validity_ci_high": argument_ci["high"],
        "trigger_precision": _mean(precision_values, default=1.0),
        "trigger_precision_ci_low": precision_ci["low"],
        "trigger_precision_ci_high": precision_ci["high"],
        "hsir": _mean(hsir_values),
        "hsir_ci_low": hsir_ci["low"],
        "hsir_ci_high": hsir_ci["high"],
        "score": _mean(score_values),
        "score_ci_low": score_ci["low"],
        "score_ci_high": score_ci["high"],
        "avg_repair_rounds": _mean(repair_values),
        "dev_test_leakage_count": 0,
        "dev_test_leakage_rate": 0.0,
    }


def _precision_indicator_values(positives: List[Any], negatives: List[Any]) -> List[float]:
    values: List[float] = []
    for item in positives:
        if item.triggered:
            values.append(1.0)
    for item in negatives:
        if item.triggered:
            values.append(0.0)
    return values


def _leakage_check_stats(
    tools: List[ToolIR],
    dev_cases: List[BehaviorCase],
    test_cases: List[BehaviorCase],
) -> Dict[str, Any]:
    tool_names = {tool.tool_name for tool in tools}
    dev_keys = {
        _case_leakage_key(case)
        for case in dev_cases
        if case.tool_name in tool_names or case.negative_target in tool_names
    }
    test_keys = [
        _case_leakage_key(case)
        for case in test_cases
        if case.tool_name in tool_names or case.negative_target in tool_names
    ]
    leaked = sum(1 for key in test_keys if key in dev_keys)
    total = len(test_keys)
    return {
        "dev_test_leakage_count": leaked,
        "dev_test_leakage_rate": round(leaked / total, 4) if total else 0.0,
    }


def _case_leakage_key(case: BehaviorCase) -> str:
    return json.dumps(
        {
            "tool_name": case.tool_name,
            "negative_target": case.negative_target,
            "should_trigger": case.should_trigger,
            "request": " ".join(case.user_request.lower().split()),
            "expected_arguments": case.expected_arguments,
        },
        sort_keys=True,
        ensure_ascii=False,
    )


def _compact_detail_record(record: Dict[str, Any]) -> Dict[str, Any]:
    report = record["test_report"]
    return {
        "condition_id": record["condition_id"],
        "ablation": record["ablation"],
        "tool_name": record["tool_name"],
        "score": record["score"].model_dump(),
        "test_metrics": report.metrics,
        "repair_rounds": record["repair_rounds"],
        "seed": record["seed"],
    }


def _write_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _mean(values: Iterable[float], default: float = 0.0) -> float:
    items = [float(value) for value in values]
    if not items:
        return default
    return round(sum(items) / len(items), 4)


def sample_condition_order(seed: int = 42) -> List[str]:
    names = [item["id"] for item in DEFAULT_ABLATION_CONDITIONS]
    rng = random.Random(seed)
    shuffled = list(names)
    rng.shuffle(shuffled)
    return shuffled

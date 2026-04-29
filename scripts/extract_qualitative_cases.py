from __future__ import annotations

import argparse
import csv
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoskill.artifacts import GATED_SKILL, NAIVE_SKILL, REPAIRED_SKILL, clone_skill_as
from autoskill.behavior import load_behavior_cases, run_behavior_tests
from autoskill.config import load_json_config
from autoskill.experiment import load_tools
from autoskill.generator import SkillGenerator
from autoskill.ir import BehaviorCase, GeneratedSkill, ToolIR
from autoskill.predictor import build_predictor_from_config
from autoskill.quality import score_reliability
from autoskill.reliability import run_reliability_pipeline
from autoskill.repair import repair_behavior_failures, repair_skill
from autoskill.validator import validate_skill


CASE_ORDER = [
    "naive_skill_over_triggers",
    "structural_invalid_skill_caught",
    "repaired_skill_fixes_boundary",
    "rejected_skill_not_deployed",
    "reliaskill_heldout_failure",
]

CSV_FIELDS = [
    "case_id",
    "required_case",
    "selection_rule",
    "tool_name",
    "condition",
    "user_request",
    "prediction",
    "gold_label",
    "failure_type",
    "confidence",
    "repair_diff",
    "source_artifact_path",
    "before_artifact_path",
    "after_artifact_path",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract deterministic qualitative cases for the ReliaSkill paper.")
    parser.add_argument("--reliability-root", type=Path, default=Path("outputs/reliability_heuristic_sample"))
    parser.add_argument("--ablation-config", type=Path, default=Path("configs/experiments/ablations.yaml"))
    parser.add_argument("--out-report", type=Path, default=Path("outputs/reports/qualitative_cases.md"))
    parser.add_argument("--out-table", type=Path, default=Path("outputs/tables/error_analysis.csv"))
    parser.add_argument("--artifact-root", type=Path, default=Path("outputs/qualitative_artifacts"))
    parser.add_argument("--max-tools", type=int, default=80)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = _load_or_create_reliability_records(args.reliability_root)
    ablation_config = load_json_config(args.ablation_config)
    tools = load_tools(ablation_config["tools_path"])
    dev_cases = load_behavior_cases(ablation_config["dev_controls_path"])
    test_cases = load_behavior_cases(ablation_config["test_controls_path"])
    selected_tools = [tools[name] for name in sorted(tools)[: args.max_tools]]
    generator = SkillGenerator(backend_config=ablation_config.get("generator"))
    predictor = build_predictor_from_config(ablation_config.get("predictor"))

    args.artifact_root.mkdir(parents=True, exist_ok=True)
    selected: List[Dict[str, Any]] = []
    selected.append(_select_naive_overtrigger(records, args.reliability_root))
    selected.append(_select_structural_invalid_case(selected_tools, generator, args.artifact_root))
    selected.append(_select_repair_boundary_case(records, args.reliability_root))
    full_failure_records = _run_full_reliaskill_measurement(
        selected_tools,
        dev_cases,
        test_cases,
        generator,
        predictor,
        args.artifact_root,
    )
    selected.append(_select_rejected_not_deployed(full_failure_records))
    selected.append(_select_heldout_failure(full_failure_records))
    selected = [_normalize_case(case) for case in selected if case]

    candidate_rows = _candidate_error_rows(records, args.reliability_root)
    rows = _dedupe_rows([*selected, *candidate_rows])
    write_error_analysis_csv(args.out_table, rows)
    write_qualitative_report(args.out_report, selected)
    print(f"qualitative_cases={len(selected)}")
    print(f"report={args.out_report}")
    print(f"error_analysis={args.out_table}")


def _load_or_create_reliability_records(root: Path) -> List[Dict[str, Any]]:
    records_path = root / "reliability_records.jsonl"
    if not records_path.exists():
        run_reliability_pipeline(
            tools_path="data/raw/public_mcp_filesystem_subset.json",
            behavior_path="data/eval/public_mcp_filesystem_reliability.jsonl",
            output_root=root,
            generator_config={"type": "heuristic"},
            predictor_config={"type": "heuristic"},
            deploy_threshold=85.0,
        )
    return _load_jsonl(records_path)


def _select_naive_overtrigger(records: List[Dict[str, Any]], reliability_root: Path) -> Dict[str, Any]:
    candidates = []
    for record in records:
        if record.get("condition") != NAIVE_SKILL:
            continue
        for result in _results(record):
            if not result.get("should_trigger", True) and result.get("triggered"):
                confidence = _behavior_failure_confidence(record, result)
                candidates.append((confidence, record.get("tool_name", ""), result.get("case_id", ""), record, result))
    if not candidates:
        return _missing_case("naive_skill_over_triggers", "No naive negative-control over-trigger was found.")
    _, _, _, record, result = sorted(candidates, key=lambda item: (-item[0], item[1], item[2]))[0]
    return _case_from_behavior(
        case_id="case_01_naive_overtrigger",
        required_case="naive skill over-triggers",
        selection_rule="highest confidence failure among naive negative controls",
        record=record,
        result=result,
        reliability_root=reliability_root,
        failure_type="negative_control_triggered",
        confidence=_behavior_failure_confidence(record, result),
        repair_diff="Not repaired in naive condition.",
    )


def _select_structural_invalid_case(tools: List[ToolIR], generator: SkillGenerator, artifact_root: Path) -> Dict[str, Any]:
    for tool in tools:
        skill = clone_skill_as(generator.generate(tool), "validation_probe")
        validation = validate_skill(tool, skill)
        if any(issue.severity == "error" for issue in validation.issues):
            return _write_structural_case(tool, skill, validation, artifact_root, synthetic=False)

    tool = tools[0]
    skill = clone_skill_as(generator.generate(tool), "validation_probe")
    skill.argument_template = {**skill.argument_template, "__unsupported_argument__": "should be rejected"}
    validation = validate_skill(tool, skill)
    return _write_structural_case(tool, skill, validation, artifact_root, synthetic=True)


def _write_structural_case(tool: ToolIR, skill: GeneratedSkill, validation: Any, artifact_root: Path, synthetic: bool) -> Dict[str, Any]:
    case_dir = artifact_root / "case_02_structural_invalid_skill"
    case_dir.mkdir(parents=True, exist_ok=True)
    skill_path = case_dir / "skill.json"
    validation_path = case_dir / "validation_report.json"
    skill_path.write_text(json.dumps(skill.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")
    validation_path.write_text(json.dumps(validation.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")
    issue = next((item for item in validation.issues if item.severity == "error"), validation.issues[0] if validation.issues else None)
    issue_text = issue.message if issue else "No validation issue found."
    return {
        "case_id": "case_02_structural_invalid_skill",
        "required_case": "structural invalid skill caught by validation",
        "selection_rule": "first structural validation error; deterministic probe only if no generated error exists",
        "tool_name": tool.tool_name,
        "condition": "validation_probe",
        "user_request": "Validation-only artifact check; no user request is executed.",
        "prediction": _compact_json(skill.argument_template),
        "gold_label": "Skill artifact must match the MCP input schema.",
        "failure_type": issue.code if issue else "structural_validation_error",
        "confidence": _validation_confidence(validation),
        "repair_diff": "Validation rejects the artifact before deployment." + (" Probe injected unsupported argument deterministically." if synthetic else ""),
        "source_artifact_path": str(validation_path),
        "before_artifact_path": str(skill_path),
        "after_artifact_path": "",
    }


def _select_repair_boundary_case(records: List[Dict[str, Any]], reliability_root: Path) -> Dict[str, Any]:
    by_tool_condition = {(record.get("tool_name"), record.get("condition")): record for record in records}
    candidates = []
    for (tool_name, condition), repaired in by_tool_condition.items():
        if condition != REPAIRED_SKILL:
            continue
        repair_actions = repaired.get("repair_report", {}).get("actions", [])
        if not any(action.get("issue_code") == "negative_control_triggered" for action in repair_actions):
            continue
        before = by_tool_condition.get((tool_name, NAIVE_SKILL)) or by_tool_condition.get((tool_name, "validated_skill"))
        if not before:
            continue
        before_failures = {
            result.get("case_id"): result
            for result in _results(before)
            if not result.get("should_trigger", True) and result.get("triggered")
        }
        for after_result in _results(repaired):
            case_id = after_result.get("case_id")
            if case_id in before_failures and not after_result.get("triggered"):
                before_result = before_failures[case_id]
                confidence = _behavior_failure_confidence(before, before_result)
                candidates.append((confidence, tool_name, case_id, before, repaired, before_result, after_result))
    if not candidates:
        return _missing_case("repaired_skill_fixes_boundary", "No repaired boundary fix was found.")
    _, _, _, before, repaired, before_result, after_result = sorted(candidates, key=lambda item: (-item[0], item[1], item[2]))[0]
    repair_diff = _repair_diff_text(repaired.get("repair_report", {}), before_result, after_result)
    return _case_from_behavior(
        case_id="case_03_repaired_boundary",
        required_case="repaired skill fixes one boundary",
        selection_rule="highest confidence repaired negative-control boundary",
        record=repaired,
        result=after_result,
        reliability_root=reliability_root,
        failure_type="boundary_repaired",
        confidence=_behavior_failure_confidence(before, before_result),
        repair_diff=repair_diff,
        before_artifact_path=_artifact_path(reliability_root, before.get("tool_name", ""), before.get("condition", ""), "behavior_report.json"),
    )


def _run_full_reliaskill_measurement(
    tools: List[ToolIR],
    dev_cases: List[BehaviorCase],
    test_cases: List[BehaviorCase],
    generator: SkillGenerator,
    predictor: Any,
    artifact_root: Path,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for tool in tools:
        base = generator.generate(tool)
        repaired_skill, repair_report, validation = repair_skill(tool, clone_skill_as(base, REPAIRED_SKILL))
        dev_behavior = run_behavior_tests(tool, repaired_skill, dev_cases, predictor=predictor)
        if not dev_behavior.valid:
            behavior_repaired, behavior_repair_report, behavior_validation = repair_behavior_failures(tool, repaired_skill, dev_behavior)
            if behavior_repair_report.changed:
                repaired_skill = behavior_repaired
                validation = behavior_validation
                repair_report.rounds += behavior_repair_report.rounds
                repair_report.actions.extend(behavior_repair_report.actions)
        dev_behavior = run_behavior_tests(tool, repaired_skill, dev_cases, predictor=predictor)
        score = score_reliability(tool, repaired_skill, validation, dev_behavior, repair_rounds=repair_report.rounds)
        gated_skill = _build_gated_skill(repaired_skill, score)
        test_behavior = run_behavior_tests(tool, gated_skill, test_cases, predictor=predictor)
        case_dir = artifact_root / "full_reliaskill" / _safe_name(tool.tool_name)
        case_dir.mkdir(parents=True, exist_ok=True)
        (case_dir / "reliability_score.json").write_text(json.dumps(score.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")
        (case_dir / "test_behavior_report.json").write_text(json.dumps(test_behavior.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")
        (case_dir / "repair_report.json").write_text(json.dumps(repair_report.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")
        rows.append(
            {
                "tool_name": tool.tool_name,
                "condition": "full_reliaskill",
                "skill": gated_skill,
                "score": score.model_dump(),
                "repair_report": repair_report.model_dump(),
                "behavior_report": test_behavior.model_dump(),
                "artifact_dir": str(case_dir),
            }
        )
    return rows


def _select_rejected_not_deployed(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    candidates = [record for record in records if record.get("score", {}).get("decision") == "reject"]
    if not candidates:
        return _missing_case("rejected_skill_not_deployed", "No rejected full ReliaSkill artifact was found.")
    record = sorted(candidates, key=lambda item: (float(item["score"].get("score", 100.0)), item["tool_name"]))[0]
    result = _first_result(record) or {}
    return _case_from_full_record(
        case_id="case_04_rejected_not_deployed",
        required_case="rejected skill not deployed",
        selection_rule="lowest reliability score among rejected full ReliaSkill artifacts",
        record=record,
        result=result,
        failure_type="gate_rejected",
        confidence=round(100.0 - float(record["score"].get("score", 100.0)), 4),
        repair_diff="Gate decision is reject, so the packaged skill is not exposed downstream.",
    )


def _select_heldout_failure(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    for record in sorted(records, key=lambda item: item["tool_name"]):
        failures = [
            result
            for result in _results(record)
            if result.get("should_trigger", True)
            and (not result.get("triggered") or not result.get("exact_match"))
        ]
        if failures:
            result = sorted(failures, key=lambda item: item.get("case_id", ""))[0]
            return _case_from_full_record(
                case_id="case_05_heldout_failure",
                required_case="ReliaSkill failure on held-out example",
                selection_rule="first held-out positive failure by tool and case id",
                record=record,
                result=result,
                failure_type="heldout_positive_failure",
                confidence=_heldout_confidence(result),
                repair_diff="Failure remains after validation, repair, scoring, and gating.",
            )
    return _missing_case("reliaskill_heldout_failure", "No held-out full ReliaSkill failure was found.")


def _case_from_behavior(
    *,
    case_id: str,
    required_case: str,
    selection_rule: str,
    record: Dict[str, Any],
    result: Dict[str, Any],
    reliability_root: Path,
    failure_type: str,
    confidence: float,
    repair_diff: str,
    before_artifact_path: str = "",
) -> Dict[str, Any]:
    tool_name = record.get("tool_name", "")
    condition = record.get("condition", "")
    return {
        "case_id": case_id,
        "required_case": required_case,
        "selection_rule": selection_rule,
        "tool_name": tool_name,
        "condition": condition,
        "user_request": result.get("user_request", ""),
        "prediction": _compact_json(result.get("predicted_arguments", {})),
        "gold_label": _gold_label(result),
        "failure_type": failure_type,
        "confidence": round(float(confidence), 4),
        "repair_diff": repair_diff,
        "source_artifact_path": _artifact_path(reliability_root, tool_name, condition, "behavior_report.json"),
        "before_artifact_path": before_artifact_path,
        "after_artifact_path": _artifact_path(reliability_root, tool_name, condition, "repair_report.json") if condition == REPAIRED_SKILL else "",
    }


def _case_from_full_record(
    *,
    case_id: str,
    required_case: str,
    selection_rule: str,
    record: Dict[str, Any],
    result: Dict[str, Any],
    failure_type: str,
    confidence: float,
    repair_diff: str,
) -> Dict[str, Any]:
    artifact_dir = Path(record.get("artifact_dir", ""))
    return {
        "case_id": case_id,
        "required_case": required_case,
        "selection_rule": selection_rule,
        "tool_name": record.get("tool_name", ""),
        "condition": record.get("condition", "full_reliaskill"),
        "user_request": result.get("user_request", "Deployment gate decision; no user request is executed."),
        "prediction": _compact_json(result.get("predicted_arguments", {})),
        "gold_label": _gold_label(result) if result else f"Reliability decision should deploy only if score >= 85 and no critical failures. Observed: {record.get('score', {}).get('decision')}.",
        "failure_type": failure_type,
        "confidence": round(float(confidence), 4),
        "repair_diff": repair_diff,
        "source_artifact_path": str(artifact_dir / "test_behavior_report.json"),
        "before_artifact_path": str(artifact_dir / "repair_report.json"),
        "after_artifact_path": str(artifact_dir / "reliability_score.json"),
    }


def _candidate_error_rows(records: List[Dict[str, Any]], reliability_root: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for record in records:
        for issue in record.get("validation_report", {}).get("issues", []):
            if issue.get("severity") == "error":
                rows.append(
                    {
                        "case_id": f"candidate_validation_{record.get('tool_name')}_{issue.get('code')}",
                        "required_case": "candidate structural validation error",
                        "selection_rule": "all validation errors from saved reliability records",
                        "tool_name": record.get("tool_name", ""),
                        "condition": record.get("condition", ""),
                        "user_request": "Validation-only artifact check; no user request is executed.",
                        "prediction": issue.get("message", ""),
                        "gold_label": "Skill artifact must match schema.",
                        "failure_type": issue.get("code", "structural_validation_error"),
                        "confidence": 1.0,
                        "repair_diff": "",
                        "source_artifact_path": _artifact_path(reliability_root, record.get("tool_name", ""), record.get("condition", ""), "validation_report.json"),
                        "before_artifact_path": "",
                        "after_artifact_path": "",
                    }
                )
        for result in _results(record):
            if _is_behavior_failure(result):
                rows.append(
                    _case_from_behavior(
                        case_id=f"candidate_behavior_{record.get('condition')}_{record.get('tool_name')}_{result.get('case_id')}",
                        required_case="candidate behavior failure",
                        selection_rule="all behavior failures from saved reliability records",
                        record=record,
                        result=result,
                        reliability_root=reliability_root,
                        failure_type=_failure_type(result),
                        confidence=_behavior_failure_confidence(record, result),
                        repair_diff="",
                    )
                )
    return rows


def write_error_analysis_csv(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})


def write_qualitative_report(path: Path, cases: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Qualitative Cases",
        "",
        "Selection is deterministic: first group by required failure category, rank failures by confidence where applicable, and use lexical tool/case order as the final tie-breaker. The held-out case uses the first held-out positive failure after full ReliaSkill processing.",
        "",
    ]
    by_id = {case["case_id"]: case for case in cases}
    for idx, required_key in enumerate(CASE_ORDER, start=1):
        case = next((item for item in cases if item["case_id"].startswith(f"case_{idx:02d}") or item["case_id"] == required_key), None)
        if case is None:
            continue
        lines.extend(
            [
                f"## {idx}. {case['required_case']}",
                "",
                f"- Tool: `{case['tool_name']}`",
                f"- User request: {case['user_request']}",
                f"- Prediction: `{case['prediction']}`",
                f"- Gold label: `{case['gold_label']}`",
                f"- Failure type: `{case['failure_type']}`",
                f"- Selection rule: {case['selection_rule']}",
                f"- Confidence: `{case['confidence']}`",
                f"- Repair diff: {case['repair_diff']}",
                f"- Source artifact: `{case['source_artifact_path']}`",
                f"- Before artifact: `{case['before_artifact_path']}`",
                f"- After artifact: `{case['after_artifact_path']}`",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def _build_gated_skill(skill: GeneratedSkill, score: Any) -> GeneratedSkill:
    gated = clone_skill_as(skill, GATED_SKILL)
    gated.metadata = {**gated.metadata, "gate_decision": score.decision, "gate_score": score.score}
    if score.decision == "deploy":
        return gated
    gated.skill_summary = f"Deployment gate decision: {score.decision}. This skill should not be exposed to downstream agents."
    gated.when_to_use = []
    gated.when_not_to_use = ["Do not deploy this generated skill artifact until reliability failures are resolved.", *score.rationale]
    gated.argument_template = {}
    gated.examples = []
    gated.semantic_hints = {}
    return gated


def _missing_case(case_id: str, message: str) -> Dict[str, Any]:
    return {
        "case_id": case_id,
        "required_case": case_id.replace("_", " "),
        "selection_rule": "deterministic selection found no matching candidate",
        "tool_name": "",
        "condition": "",
        "user_request": "",
        "prediction": "",
        "gold_label": "",
        "failure_type": "missing_candidate",
        "confidence": 0.0,
        "repair_diff": message,
        "source_artifact_path": "",
        "before_artifact_path": "",
        "after_artifact_path": "",
    }


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                value = json.loads(line)
                if isinstance(value, dict):
                    records.append(value)
    return records


def _results(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list((record.get("behavior_report") or {}).get("results") or [])


def _first_result(record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    results = _results(record)
    return results[0] if results else None


def _behavior_failure_confidence(record: Dict[str, Any], result: Dict[str, Any]) -> float:
    metrics = record.get("behavior_report", {}).get("metrics", {})
    if result.get("harmful_injection"):
        return float(metrics.get("harmful_skill_injection_rate", 1.0))
    if result.get("should_trigger", True) and not result.get("triggered"):
        return 1.0 - float(metrics.get("trigger_recall", 0.0))
    if result.get("should_trigger", True) and not result.get("exact_match"):
        return 1.0 - float(result.get("argument_validity", 0.0))
    return 0.5


def _heldout_confidence(result: Dict[str, Any]) -> float:
    if not result.get("triggered"):
        return 1.0
    if not result.get("exact_match"):
        return round(1.0 - float(result.get("argument_validity", 0.0)), 4)
    return 0.0


def _validation_confidence(validation: Any) -> float:
    errors = [issue for issue in validation.issues if issue.severity == "error"]
    return float(len(errors))


def _is_behavior_failure(result: Dict[str, Any]) -> bool:
    if not result.get("should_trigger", True) and result.get("triggered"):
        return True
    if result.get("should_trigger", True) and (not result.get("triggered") or not result.get("exact_match")):
        return True
    return False


def _failure_type(result: Dict[str, Any]) -> str:
    if not result.get("should_trigger", True) and result.get("triggered"):
        return "negative_control_triggered"
    if result.get("should_trigger", True) and not result.get("triggered"):
        return "positive_control_not_triggered"
    if result.get("should_trigger", True) and not result.get("exact_match"):
        return "argument_mismatch"
    return "behavior_failure"


def _repair_diff_text(repair_report: Dict[str, Any], before_result: Dict[str, Any], after_result: Dict[str, Any]) -> str:
    action_text = "; ".join(action.get("description", "") for action in repair_report.get("actions", []))
    before = f"before triggered={before_result.get('triggered')} prediction={_compact_json(before_result.get('predicted_arguments', {}))}"
    after = f"after triggered={after_result.get('triggered')} prediction={_compact_json(after_result.get('predicted_arguments', {}))}"
    return f"{action_text}. {before}; {after}."


def _artifact_path(root: Path, tool_name: str, condition: str, filename: str) -> str:
    return str(root / "packages" / tool_name / condition / filename)


def _gold_label(result: Dict[str, Any]) -> str:
    if not result.get("should_trigger", True):
        return "abstain"
    return _compact_json(result.get("expected_arguments", {}))


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))[:300]


def _safe_name(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in value)[:120]


def _normalize_case(case: Dict[str, Any]) -> Dict[str, Any]:
    return {field: case.get(field, "") for field in CSV_FIELDS}


def _dedupe_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    unique: List[Dict[str, Any]] = []
    for row in rows:
        key = (row.get("case_id"), row.get("tool_name"), row.get("condition"), row.get("user_request"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(_normalize_case(row))
    return unique


if __name__ == "__main__":
    main()

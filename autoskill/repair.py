from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

from autoskill.ir import BehaviorReport, GeneratedSkill, RepairAction, RepairReport, ToolIR, ValidationIssue, ValidationReport
from autoskill.templates import build_argument_template
from autoskill.validator import validate_skill


FAILURE_TAXONOMY = {
    "bad_example_json": "malformed_example",
    "bad_example_arguments": "malformed_example",
    "invalid_enum": "invalid_enum",
    "hallucinated_argument": "unsupported_argument",
    "missing_required_argument": "missing_required_guidance",
    "text_contradiction": "contradictory_guidance",
    "missing_non_usage_boundary": "missing_non_use_boundary",
    "type_mismatch": "brittle_argument_pattern",
    "excessive_verbosity": "excessive_verbosity",
    "unsupported_option_in_text": "unsupported_argument",
    "negative_control_triggered": "trigger_overbreadth",
    "positive_control_not_triggered": "under_specified_trigger",
}


def classify_failure(issue: ValidationIssue) -> str:
    return FAILURE_TAXONOMY.get(issue.code, issue.code)


def _sanitize_payload(tool: ToolIR, payload: Any, include_optional: bool = False) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        payload = {}
    allowed = {arg.name: arg for arg in tool.arguments}
    repaired = {key: value for key, value in payload.items() if key in allowed}
    template = build_argument_template(tool, include_optional=include_optional, variant=0)
    for arg in tool.arguments:
        if arg.required and arg.name not in repaired and arg.name in template:
            repaired[arg.name] = template[arg.name]
        if arg.name in repaired and arg.enum and repaired[arg.name] not in arg.enum:
            repaired[arg.name] = arg.default if arg.default in (arg.enum or []) else arg.enum[0]
    return repaired


def _repair_examples(tool: ToolIR, skill: GeneratedSkill, actions: List[RepairAction]) -> None:
    repaired_examples = []
    for index, example in enumerate(skill.examples):
        if not isinstance(example, dict):
            actions.append(RepairAction("drop_example", "examples", "bad_example_arguments", f"Dropped non-object example {index}."))
            continue
        args = example.get("arguments", {})
        repaired_args = _sanitize_payload(tool, args, include_optional=False)
        if repaired_args != args:
            actions.append(RepairAction("repair_example_arguments", "examples", "schema_mismatch", f"Repaired example {index} arguments."))
        if repaired_args or not tool.arguments:
            repaired_examples.append({**example, "arguments": repaired_args})
    if not repaired_examples and tool.arguments:
        repaired_examples.append(
            {
                "scenario": f"Minimal valid request for {tool.tool_name}",
                "arguments": build_argument_template(tool, include_optional=False, variant=0),
            }
        )
        actions.append(RepairAction("add_example", "examples", "missing_required_argument", "Added minimal schema-faithful example."))
    skill.examples = repaired_examples[:3]


def _repair_guidance(tool: ToolIR, skill: GeneratedSkill, issues: List[ValidationIssue], actions: List[RepairAction]) -> None:
    if any(issue.code == "missing_non_usage_boundary" for issue in issues):
        skill.when_not_to_use.append("Do not use this tool for adjacent tasks that do not match its MCP description or required arguments.")
        actions.append(RepairAction("add_non_use_boundary", "when_not_to_use", "missing_non_usage_boundary", "Added conservative non-use boundary."))

    unsupported = {str(issue.evidence.get("unsupported_token")) for issue in issues if issue.code == "unsupported_option_in_text"}
    unsupported.discard("None")
    if unsupported:
        def clean(line: str) -> str:
            for token in unsupported:
                line = line.replace(f"`{token}`", token)
            return line

        skill.skill_summary = clean(skill.skill_summary)
        skill.when_to_use = [clean(line) for line in skill.when_to_use]
        skill.when_not_to_use = [clean(line) for line in skill.when_not_to_use]
        actions.append(RepairAction("remove_unsupported_text_markup", "guidance", "unsupported_option_in_text", "Removed unsupported schema-option markup from guidance."))

    if any(issue.code == "excessive_verbosity" for issue in issues):
        skill.when_to_use = skill.when_to_use[:2]
        skill.when_not_to_use = skill.when_not_to_use[:3]
        skill.examples = skill.examples[:2]
        actions.append(RepairAction("compact_guidance", "guidance", "excessive_verbosity", "Compacted verbose guidance and examples."))


def repair_skill_once(tool: ToolIR, skill: GeneratedSkill, report: ValidationReport) -> tuple[GeneratedSkill, RepairReport, ValidationReport]:
    repaired = deepcopy(skill)
    actions: List[RepairAction] = []
    issues = report.issues

    if any(issue.section == "argument_template" or issue.code in {"bad_argument_template", "hallucinated_argument", "missing_required_argument", "invalid_enum", "type_mismatch"} for issue in issues):
        repaired.argument_template = _sanitize_payload(tool, repaired.argument_template, include_optional=True)
        actions.append(RepairAction("repair_argument_template", "argument_template", "schema_mismatch", "Rebuilt schema-faithful argument template."))

    if any(issue.section == "examples" or issue.code.startswith("bad_example") or "example[" in issue.message for issue in issues):
        _repair_examples(tool, repaired, actions)

    _repair_guidance(tool, repaired, issues, actions)

    repaired.method_trace = [
        *repaired.method_trace,
        {
            "trace_type": "targeted_repair",
            "actions": [action.model_dump() for action in actions],
        },
    ]
    new_report = validate_skill(tool, repaired)
    repair_report = RepairReport(
        attempted=True,
        changed=bool(actions),
        rounds=1,
        actions=actions,
        remaining_issues=new_report.issues,
    )
    return repaired, repair_report, new_report


def repair_skill(
    tool: ToolIR,
    skill: GeneratedSkill,
    max_rounds: int = 2,
) -> tuple[GeneratedSkill, RepairReport, ValidationReport]:
    current = deepcopy(skill)
    report = validate_skill(tool, current)
    all_actions: List[RepairAction] = []
    rounds = 0
    changed = False
    while rounds < max_rounds and any(issue.repairable for issue in report.issues):
        current, round_report, report = repair_skill_once(tool, current, report)
        rounds += 1
        changed = changed or round_report.changed
        all_actions.extend(round_report.actions)
        if report.valid:
            break
        if not round_report.changed:
            break
    return current, RepairReport(attempted=rounds > 0, changed=changed, rounds=rounds, actions=all_actions, remaining_issues=report.issues), report


def repair_behavior_failures(
    tool: ToolIR,
    skill: GeneratedSkill,
    behavior_report: BehaviorReport,
) -> tuple[GeneratedSkill, RepairReport, ValidationReport]:
    repaired = deepcopy(skill)
    actions: List[RepairAction] = []

    harmful_results = [result for result in behavior_report.results if result.harmful_injection]
    for result in harmful_results:
        request_boundary = f"Do not use this tool for requests like: {result.user_request or result.case_id}."
        if request_boundary not in repaired.when_not_to_use:
            repaired.when_not_to_use.append(request_boundary)
            actions.append(
                RepairAction(
                    "add_negative_control_boundary",
                    "when_not_to_use",
                    "negative_control_triggered",
                    f"Added non-use boundary from negative control `{result.case_id}`.",
                )
            )

    missed_positive = [result for result in behavior_report.results if result.should_trigger and not result.triggered]
    for result in missed_positive:
        cue = f"Use this tool for requests like: {result.user_request or result.case_id}, when required arguments are present."
        if cue not in repaired.when_to_use:
            repaired.when_to_use.append(cue)
            actions.append(
                RepairAction(
                    "add_positive_control_trigger",
                    "when_to_use",
                    "positive_control_not_triggered",
                    f"Added narrow trigger guidance from positive control `{result.case_id}`.",
                )
            )

    # Store exact request text as machine-readable repair metadata when available to avoid
    # forcing the natural-language artifact to become verbose.
    repaired.metadata = {
        **repaired.metadata,
        "behavior_repair_cases": [result.case_id for result in harmful_results + missed_positive],
    }
    repaired.method_trace = [
        *repaired.method_trace,
        {
            "trace_type": "behavior_targeted_repair",
            "actions": [action.model_dump() for action in actions],
        },
    ]
    validation_report = validate_skill(tool, repaired)
    return (
        repaired,
        RepairReport(
            attempted=bool(behavior_report.results),
            changed=bool(actions),
            rounds=1 if actions else 0,
            actions=actions,
            remaining_issues=validation_report.issues,
        ),
        validation_report,
    )

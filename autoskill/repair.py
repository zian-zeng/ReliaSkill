from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Dict, Iterable, List

from autoskill.behavior import run_behavior_tests
from autoskill.ir import (
    BehaviorCase,
    BehaviorReport,
    GeneratedSkill,
    RepairAction,
    RepairReport,
    ToolIR,
    ValidationIssue,
    ValidationReport,
)
from autoskill.predictor import PredictorBackend
from autoskill.templates import build_argument_template
from autoskill.validator import validate_skill


NO_REPAIR = "no_repair"
FULL_REGENERATION = "full_regeneration"
TARGETED_SECTION_PATCH = "targeted_section_patch"
NONUSE_BOUNDARY_PATCH = "nonuse_boundary_patch"
EXAMPLE_REPAIR = "example_repair"
ARGUMENT_TEMPLATE_REPAIR = "argument_template_repair"
FAILURE_TAXONOMY_REPAIR = "failure_taxonomy_repair"

FAILURE_TAXONOMY = {
    "bad_example_json": "malformed_example",
    "bad_example_arguments": "malformed_example",
    "invalid_enum": "invalid_enum",
    "hallucinated_argument": "unsupported_argument",
    "missing_required_argument": "missing_required_field",
    "text_contradiction": "contradictory_instruction",
    "missing_non_usage_boundary": "unsafe_side_effect_boundary",
    "type_mismatch": "unsupported_argument",
    "excessive_verbosity": "verbosity_or_context_bloat",
    "unsupported_option_in_text": "unsupported_argument",
    "negative_control_triggered": "over_triggering",
    "positive_control_not_triggered": "under_triggering",
}

STRUCTURAL_FAILURES = {
    "unsupported_argument",
    "missing_required_field",
    "invalid_enum",
}
EXAMPLE_FAILURES = {"malformed_example"}
BOUNDARY_FAILURES = {
    "over_triggering",
    "under_triggering",
    "contradictory_instruction",
    "unsafe_side_effect_boundary",
}


def classify_failure(issue: ValidationIssue) -> str:
    return FAILURE_TAXONOMY.get(issue.code, issue.code)


def _behavior_failure_type(result: Any) -> str:
    if result.harmful_injection or "negative_control_triggered" in result.notes:
        return "over_triggering"
    if result.should_trigger and not result.triggered:
        return "under_triggering"
    return "behavior_failure"


def _skill_hash(skill: GeneratedSkill) -> str:
    payload = json.dumps(skill.model_dump(), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _dump_report(report: ValidationReport | BehaviorReport | None) -> Dict[str, Any]:
    return report.model_dump() if report is not None else {}


def _primary_failure_type(diagnosis: Dict[str, Any]) -> str:
    types = list(diagnosis.get("failure_types") or [])
    if not types:
        return "none"
    priority = [
        "over_triggering",
        "missing_required_field",
        "unsupported_argument",
        "invalid_enum",
        "malformed_example",
        "unsafe_side_effect_boundary",
        "under_triggering",
        "contradictory_instruction",
        "verbosity_or_context_bloat",
    ]
    for item in priority:
        if item in types:
            return item
    return sorted(types)[0]


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
            actions.append(RepairAction("drop_example", "examples", "malformed_example", f"Dropped non-object example {index}."))
            continue
        args = example.get("arguments", {})
        repaired_args = _sanitize_payload(tool, args, include_optional=False)
        if repaired_args != args:
            actions.append(RepairAction("repair_example_arguments", "examples", "malformed_example", f"Repaired example {index} arguments."))
        if repaired_args or not tool.arguments:
            repaired_examples.append({**example, "arguments": repaired_args})
    if not repaired_examples and tool.arguments:
        repaired_examples.append(
            {
                "scenario": f"Minimal valid request for {tool.tool_name}",
                "arguments": build_argument_template(tool, include_optional=False, variant=0),
            }
        )
        actions.append(RepairAction("add_example", "examples", "missing_required_field", "Added minimal schema-faithful example."))
    skill.examples = repaired_examples[:3]


def _repair_guidance(tool: ToolIR, skill: GeneratedSkill, issues: List[ValidationIssue], actions: List[RepairAction]) -> None:
    if any(issue.code == "missing_non_usage_boundary" for issue in issues):
        line = "Do not use this tool for adjacent tasks that do not match its MCP description or required arguments."
        if line not in skill.when_not_to_use:
            skill.when_not_to_use.append(line)
            actions.append(RepairAction("add_non_use_boundary", "when_not_to_use", "unsafe_side_effect_boundary", "Added conservative non-use boundary."))

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
        actions.append(RepairAction("remove_unsupported_text_markup", "guidance", "unsupported_argument", "Removed unsupported schema-option markup from guidance."))

    if any(issue.code == "text_contradiction" for issue in issues):
        required = {arg.name for arg in tool.arguments if arg.required}
        optional = {arg.name for arg in tool.arguments if not arg.required}

        def fix(line: str) -> str:
            updated = line
            for name in required:
                updated = updated.replace(f"{name} optional", f"{name} required")
            for name in optional:
                updated = updated.replace(f"{name} required", f"{name} optional")
            return updated

        skill.skill_summary = fix(skill.skill_summary)
        skill.when_to_use = [fix(line) for line in skill.when_to_use]
        skill.when_not_to_use = [fix(line) for line in skill.when_not_to_use]
        actions.append(RepairAction("fix_contradictory_guidance", "guidance", "contradictory_instruction", "Aligned required/optional wording with schema."))

    if any(issue.code == "excessive_verbosity" for issue in issues):
        skill.when_to_use = skill.when_to_use[:2]
        skill.when_not_to_use = skill.when_not_to_use[:3]
        skill.examples = skill.examples[:2]
        actions.append(RepairAction("compact_guidance", "guidance", "verbosity_or_context_bloat", "Compacted verbose guidance and examples."))


def _add_behavior_boundaries(skill: GeneratedSkill, behavior_report: BehaviorReport | None, actions: List[RepairAction]) -> None:
    if behavior_report is None:
        return
    harmful_results = [result for result in behavior_report.results if result.harmful_injection]
    for result in harmful_results:
        request_boundary = f"Do not use this tool for requests like: {result.user_request or result.case_id}."
        if request_boundary not in skill.when_not_to_use:
            skill.when_not_to_use.append(request_boundary)
            actions.append(
                RepairAction(
                    "add_negative_control_boundary",
                    "when_not_to_use",
                    "over_triggering",
                    f"Added non-use boundary from negative control `{result.case_id}`.",
                )
            )

    missed_positive = [result for result in behavior_report.results if result.should_trigger and not result.triggered]
    for result in missed_positive:
        cue = f"Use this tool for requests like: {result.user_request or result.case_id}, when required arguments are present."
        if cue not in skill.when_to_use:
            skill.when_to_use.append(cue)
            actions.append(
                RepairAction(
                    "add_positive_control_trigger",
                    "when_to_use",
                    "under_triggering",
                    f"Added narrow trigger guidance from positive control `{result.case_id}`.",
                )
            )
    skill.metadata = {
        **skill.metadata,
        "behavior_repair_cases": [result.case_id for result in harmful_results + missed_positive],
    }


def _modified_sections(actions: Iterable[RepairAction]) -> List[str]:
    return sorted({action.section for action in actions})


def _patch_text(actions: Iterable[RepairAction]) -> str:
    return "\n".join(f"- {action.section}: {action.description}" for action in actions)


class RepairStrategy:
    name = "base"

    def diagnose(
        self,
        tool: ToolIR,
        skill: GeneratedSkill,
        validation_report: ValidationReport,
        behavior_report: BehaviorReport | None = None,
    ) -> Dict[str, Any]:
        failure_types = [classify_failure(issue) for issue in validation_report.issues]
        if behavior_report is not None:
            failure_types.extend(_behavior_failure_type(result) for result in behavior_report.results if result.notes or result.harmful_injection)
        return {
            "strategy": self.name,
            "failure_types": sorted(set(failure_types)),
            "validation_issue_codes": [issue.code for issue in validation_report.issues],
            "behavior_case_ids": [result.case_id for result in behavior_report.results if result.notes or result.harmful_injection] if behavior_report else [],
        }

    def propose_patch(
        self,
        tool: ToolIR,
        skill: GeneratedSkill,
        diagnosis: Dict[str, Any],
        validation_report: ValidationReport,
        behavior_report: BehaviorReport | None = None,
    ) -> Dict[str, Any]:
        return {"actions": [], "diagnosis": diagnosis}

    def apply_patch(self, tool: ToolIR, skill: GeneratedSkill, patch: Dict[str, Any]) -> tuple[GeneratedSkill, List[RepairAction]]:
        return deepcopy(skill), list(patch.get("actions") or [])

    def validate_patch(self, tool: ToolIR, skill: GeneratedSkill) -> ValidationReport:
        return validate_skill(tool, skill)

    def log_repair_trace(
        self,
        *,
        diagnosis: Dict[str, Any],
        actions: List[RepairAction],
        validation_before: ValidationReport,
        validation_after: ValidationReport,
        behavior_before_dev: BehaviorReport | None,
        behavior_after_dev: BehaviorReport | None,
        repair_round: int,
    ) -> List[Dict[str, Any]]:
        return [
            {
                "trace_type": "repair_strategy",
                "repair_strategy": self.name,
                "repair_round": repair_round,
                "diagnosis": diagnosis,
                "actions": [action.model_dump() for action in actions],
                "validation_before_valid": validation_before.valid,
                "validation_after_valid": validation_after.valid,
                "behavior_before_valid": behavior_before_dev.valid if behavior_before_dev is not None else None,
                "behavior_after_valid": behavior_after_dev.valid if behavior_after_dev is not None else None,
            }
        ]

    def repair(
        self,
        tool: ToolIR,
        skill: GeneratedSkill,
        validation_report: ValidationReport | None = None,
        behavior_report: BehaviorReport | None = None,
        behavior_cases: Iterable[BehaviorCase] | None = None,
        predictor: PredictorBackend | None = None,
        repair_round: int = 1,
    ) -> tuple[GeneratedSkill, RepairReport, ValidationReport]:
        original_hash = _skill_hash(skill)
        before_validation = validation_report or validate_skill(tool, skill)
        diagnosis = self.diagnose(tool, skill, before_validation, behavior_report)
        patch = self.propose_patch(tool, skill, diagnosis, before_validation, behavior_report)
        repaired, actions = self.apply_patch(tool, skill, patch)
        after_validation = self.validate_patch(tool, repaired)
        after_behavior = None
        if behavior_cases is not None:
            after_behavior = run_behavior_tests(tool, repaired, behavior_cases, predictor=predictor)
        trace = self.log_repair_trace(
            diagnosis=diagnosis,
            actions=actions,
            validation_before=before_validation,
            validation_after=after_validation,
            behavior_before_dev=behavior_report,
            behavior_after_dev=after_behavior,
            repair_round=repair_round,
        )
        repaired.method_trace = [*repaired.method_trace, *trace]
        changed = _skill_hash(repaired) != original_hash
        report = RepairReport(
            attempted=self.name != NO_REPAIR,
            changed=changed,
            rounds=1 if actions or changed else 0,
            actions=actions,
            remaining_issues=after_validation.issues,
            strategy=self.name,
            original_skill_hash=original_hash,
            repaired_skill_hash=_skill_hash(repaired),
            failure_type=_primary_failure_type(diagnosis),
            modified_sections=_modified_sections(actions),
            patch_text=_patch_text(actions),
            validation_before=_dump_report(before_validation),
            validation_after=_dump_report(after_validation),
            behavior_before_dev=_dump_report(behavior_report),
            behavior_after_dev=_dump_report(after_behavior),
            repair_round=repair_round,
            repair_success=after_validation.valid and (after_behavior.valid if after_behavior is not None else True),
            repair_trace=trace,
        )
        return repaired, report, after_validation


class NoRepairStrategy(RepairStrategy):
    name = NO_REPAIR


class ArgumentTemplateRepairStrategy(RepairStrategy):
    name = ARGUMENT_TEMPLATE_REPAIR

    def propose_patch(self, tool: ToolIR, skill: GeneratedSkill, diagnosis: Dict[str, Any], validation_report: ValidationReport, behavior_report: BehaviorReport | None = None) -> Dict[str, Any]:
        actions = []
        if any(issue.section == "argument_template" or issue.code in {"bad_argument_template", "hallucinated_argument", "missing_required_argument", "invalid_enum", "type_mismatch"} for issue in validation_report.issues):
            actions.append(RepairAction("repair_argument_template", "argument_template", "schema_mismatch", "Rebuilt schema-faithful argument template."))
        return {"actions": actions, "diagnosis": diagnosis}

    def apply_patch(self, tool: ToolIR, skill: GeneratedSkill, patch: Dict[str, Any]) -> tuple[GeneratedSkill, List[RepairAction]]:
        repaired = deepcopy(skill)
        actions = list(patch.get("actions") or [])
        if actions:
            repaired.argument_template = _sanitize_payload(tool, repaired.argument_template, include_optional=True)
        return repaired, actions


class ExampleRepairStrategy(RepairStrategy):
    name = EXAMPLE_REPAIR

    def propose_patch(self, tool: ToolIR, skill: GeneratedSkill, diagnosis: Dict[str, Any], validation_report: ValidationReport, behavior_report: BehaviorReport | None = None) -> Dict[str, Any]:
        should_repair = any(issue.section == "examples" or issue.code.startswith("bad_example") or "example[" in issue.message for issue in validation_report.issues)
        return {"actions": [RepairAction("repair_examples", "examples", "malformed_example", "Repair schema-invalid examples.")] if should_repair else [], "diagnosis": diagnosis}

    def apply_patch(self, tool: ToolIR, skill: GeneratedSkill, patch: Dict[str, Any]) -> tuple[GeneratedSkill, List[RepairAction]]:
        repaired = deepcopy(skill)
        actions: List[RepairAction] = []
        if patch.get("actions"):
            _repair_examples(tool, repaired, actions)
        return repaired, actions


class NonUseBoundaryRepairStrategy(RepairStrategy):
    name = NONUSE_BOUNDARY_PATCH

    def propose_patch(self, tool: ToolIR, skill: GeneratedSkill, diagnosis: Dict[str, Any], validation_report: ValidationReport, behavior_report: BehaviorReport | None = None) -> Dict[str, Any]:
        actions = []
        if any(issue.code in {"missing_non_usage_boundary", "text_contradiction", "unsupported_option_in_text", "excessive_verbosity"} for issue in validation_report.issues):
            actions.append(RepairAction("repair_boundaries", "guidance", "unsafe_side_effect_boundary", "Patch non-use boundaries and compact contradictory guidance."))
        if behavior_report is not None and any(result.harmful_injection or (result.should_trigger and not result.triggered) for result in behavior_report.results):
            actions.append(RepairAction("repair_behavior_boundaries", "when_not_to_use", "over_triggering", "Patch boundaries from dev behavior failures."))
        return {"actions": actions, "diagnosis": diagnosis}

    def apply_patch(self, tool: ToolIR, skill: GeneratedSkill, patch: Dict[str, Any]) -> tuple[GeneratedSkill, List[RepairAction]]:
        repaired = deepcopy(skill)
        actions: List[RepairAction] = []
        if patch.get("actions"):
            validation = validate_skill(tool, skill)
            _repair_guidance(tool, repaired, validation.issues, actions)
            behavior_report = patch.get("behavior_report")
            _add_behavior_boundaries(repaired, behavior_report, actions)
        return repaired, actions

    def repair(self, tool: ToolIR, skill: GeneratedSkill, validation_report: ValidationReport | None = None, behavior_report: BehaviorReport | None = None, behavior_cases: Iterable[BehaviorCase] | None = None, predictor: PredictorBackend | None = None, repair_round: int = 1) -> tuple[GeneratedSkill, RepairReport, ValidationReport]:
        before_validation = validation_report or validate_skill(tool, skill)
        diagnosis = self.diagnose(tool, skill, before_validation, behavior_report)
        patch = self.propose_patch(tool, skill, diagnosis, before_validation, behavior_report)
        patch["behavior_report"] = behavior_report
        original_hash = _skill_hash(skill)
        repaired, actions = self.apply_patch(tool, skill, patch)
        after_validation = validate_skill(tool, repaired)
        after_behavior = run_behavior_tests(tool, repaired, behavior_cases, predictor=predictor) if behavior_cases is not None else None
        trace = self.log_repair_trace(
            diagnosis=diagnosis,
            actions=actions,
            validation_before=before_validation,
            validation_after=after_validation,
            behavior_before_dev=behavior_report,
            behavior_after_dev=after_behavior,
            repair_round=repair_round,
        )
        repaired.method_trace = [*repaired.method_trace, *trace]
        return repaired, _report_from_trace(self.name, original_hash, repaired, before_validation, after_validation, behavior_report, after_behavior, diagnosis, actions, repair_round, trace), after_validation


class TargetedSectionPatchStrategy(RepairStrategy):
    name = TARGETED_SECTION_PATCH

    def propose_patch(self, tool: ToolIR, skill: GeneratedSkill, diagnosis: Dict[str, Any], validation_report: ValidationReport, behavior_report: BehaviorReport | None = None) -> Dict[str, Any]:
        actions = []
        failure_types = set(diagnosis.get("failure_types") or [])
        example_issue = any(issue.section == "examples" or issue.code.startswith("bad_example") or "example[" in issue.message for issue in validation_report.issues)
        if STRUCTURAL_FAILURES.intersection(failure_types):
            actions.append(RepairAction("repair_argument_template", "argument_template", "schema_mismatch", "Rebuild schema-faithful argument template."))
        if EXAMPLE_FAILURES.intersection(failure_types) or example_issue:
            actions.append(RepairAction("repair_examples", "examples", "malformed_example", "Repair schema-invalid examples."))
        if BOUNDARY_FAILURES.intersection(failure_types) or "verbosity_or_context_bloat" in failure_types:
            actions.append(RepairAction("repair_guidance", "guidance", _primary_failure_type(diagnosis), "Repair guidance and non-use boundaries."))
        return {"actions": actions, "diagnosis": diagnosis, "behavior_report": behavior_report}

    def apply_patch(self, tool: ToolIR, skill: GeneratedSkill, patch: Dict[str, Any]) -> tuple[GeneratedSkill, List[RepairAction]]:
        repaired = deepcopy(skill)
        actions: List[RepairAction] = []
        requested = {action.action_type for action in patch.get("actions") or []}
        if "repair_argument_template" in requested:
            repaired.argument_template = _sanitize_payload(tool, repaired.argument_template, include_optional=True)
            actions.append(RepairAction("repair_argument_template", "argument_template", "schema_mismatch", "Rebuilt schema-faithful argument template."))
        if "repair_examples" in requested:
            _repair_examples(tool, repaired, actions)
        if "repair_guidance" in requested:
            validation = validate_skill(tool, skill)
            _repair_guidance(tool, repaired, validation.issues, actions)
            _add_behavior_boundaries(repaired, patch.get("behavior_report"), actions)
        return repaired, actions


class FailureTaxonomyRepairStrategy(TargetedSectionPatchStrategy):
    name = FAILURE_TAXONOMY_REPAIR

    def propose_patch(self, tool: ToolIR, skill: GeneratedSkill, diagnosis: Dict[str, Any], validation_report: ValidationReport, behavior_report: BehaviorReport | None = None) -> Dict[str, Any]:
        actions = []
        failure_types = set(diagnosis.get("failure_types") or [])
        example_issue = any(issue.section == "examples" or issue.code.startswith("bad_example") or "example[" in issue.message for issue in validation_report.issues)
        if failure_types.intersection(STRUCTURAL_FAILURES):
            actions.append(RepairAction("repair_argument_template", "argument_template", _primary_failure_type(diagnosis), "Failure taxonomy selected schema argument repair."))
        if failure_types.intersection(EXAMPLE_FAILURES) or example_issue:
            actions.append(RepairAction("repair_examples", "examples", _primary_failure_type(diagnosis), "Failure taxonomy selected example repair."))
        if failure_types.intersection(BOUNDARY_FAILURES | {"verbosity_or_context_bloat"}):
            actions.append(RepairAction("repair_guidance", "guidance", _primary_failure_type(diagnosis), "Failure taxonomy selected boundary/guidance repair."))
        return {"actions": actions, "diagnosis": diagnosis, "behavior_report": behavior_report}


class FullRegenerationStrategy(RepairStrategy):
    name = FULL_REGENERATION

    def propose_patch(self, tool: ToolIR, skill: GeneratedSkill, diagnosis: Dict[str, Any], validation_report: ValidationReport, behavior_report: BehaviorReport | None = None) -> Dict[str, Any]:
        return {
            "actions": [RepairAction("full_regeneration", "all", _primary_failure_type(diagnosis), "Regenerated the full skill artifact from schema and dev failure diagnosis.")],
            "diagnosis": diagnosis,
        }

    def apply_patch(self, tool: ToolIR, skill: GeneratedSkill, patch: Dict[str, Any]) -> tuple[GeneratedSkill, List[RepairAction]]:
        regenerated = GeneratedSkill(
            baseline_name=skill.baseline_name,
            skill_summary=f"Use `{tool.tool_name}` only for requests matching its MCP schema and documented purpose.",
            when_to_use=[
                f"Use when the user request directly asks for `{tool.tool_name}` or its documented purpose.",
                "Map only user-grounded values into the schema fields.",
                "Ask for clarification instead of inventing missing required arguments.",
            ],
            when_not_to_use=[
                "Do not use for adjacent, keyword-overlapping, or underspecified requests.",
                "Do not use when required arguments are missing.",
                "Do not use for read/write, search/fetch, create/update, or destructive/non-destructive mismatches.",
            ],
            argument_template=build_argument_template(tool, include_optional=True, variant=2),
            examples=[
                {
                    "scenario": f"Valid regenerated invocation for {tool.tool_name}",
                    "arguments": build_argument_template(tool, include_optional=False, variant=2),
                }
            ],
            semantic_hints=deepcopy(skill.semantic_hints),
            method_trace=[
                *skill.method_trace,
                {"trace_type": "full_regeneration_repair", "repair_strategy": self.name},
            ],
            metadata={**skill.metadata, "repair_strategy": self.name, "llm_repair_used": False},
        )
        return regenerated, list(patch.get("actions") or [])


REPAIR_STRATEGIES = {
    NO_REPAIR: NoRepairStrategy,
    FULL_REGENERATION: FullRegenerationStrategy,
    TARGETED_SECTION_PATCH: TargetedSectionPatchStrategy,
    NONUSE_BOUNDARY_PATCH: NonUseBoundaryRepairStrategy,
    EXAMPLE_REPAIR: ExampleRepairStrategy,
    ARGUMENT_TEMPLATE_REPAIR: ArgumentTemplateRepairStrategy,
    FAILURE_TAXONOMY_REPAIR: FailureTaxonomyRepairStrategy,
}


def get_repair_strategy(name: str | None = None) -> RepairStrategy:
    strategy_name = name or TARGETED_SECTION_PATCH
    try:
        return REPAIR_STRATEGIES[strategy_name]()
    except KeyError as exc:
        raise ValueError(f"Unsupported repair strategy: {strategy_name}") from exc


def _report_from_trace(
    strategy: str,
    original_hash: str,
    repaired: GeneratedSkill,
    validation_before: ValidationReport,
    validation_after: ValidationReport,
    behavior_before: BehaviorReport | None,
    behavior_after: BehaviorReport | None,
    diagnosis: Dict[str, Any],
    actions: List[RepairAction],
    repair_round: int,
    trace: List[Dict[str, Any]],
) -> RepairReport:
    changed = _skill_hash(repaired) != original_hash
    return RepairReport(
        attempted=strategy != NO_REPAIR,
        changed=changed,
        rounds=1 if actions or changed else 0,
        actions=actions,
        remaining_issues=validation_after.issues,
        strategy=strategy,
        original_skill_hash=original_hash,
        repaired_skill_hash=_skill_hash(repaired),
        failure_type=_primary_failure_type(diagnosis),
        modified_sections=_modified_sections(actions),
        patch_text=_patch_text(actions),
        validation_before=_dump_report(validation_before),
        validation_after=_dump_report(validation_after),
        behavior_before_dev=_dump_report(behavior_before),
        behavior_after_dev=_dump_report(behavior_after),
        repair_round=repair_round,
        repair_success=validation_after.valid and (behavior_after.valid if behavior_after is not None else True),
        repair_trace=trace,
    )


def repair_skill_once(
    tool: ToolIR,
    skill: GeneratedSkill,
    report: ValidationReport,
    strategy: str | None = TARGETED_SECTION_PATCH,
) -> tuple[GeneratedSkill, RepairReport, ValidationReport]:
    return get_repair_strategy(strategy).repair(tool, skill, validation_report=report)


def repair_skill(
    tool: ToolIR,
    skill: GeneratedSkill,
    max_rounds: int = 2,
    strategy: str | None = TARGETED_SECTION_PATCH,
) -> tuple[GeneratedSkill, RepairReport, ValidationReport]:
    current = deepcopy(skill)
    current_report = validate_skill(tool, current)
    strategy_obj = get_repair_strategy(strategy)
    all_actions: List[RepairAction] = []
    all_traces: List[Dict[str, Any]] = []
    rounds = 0
    changed = False
    first_hash = _skill_hash(current)
    last_round_report: RepairReport | None = None

    if strategy_obj.name == NO_REPAIR:
        repaired, no_report, current_report = strategy_obj.repair(tool, current, validation_report=current_report, repair_round=0)
        return repaired, no_report, current_report

    if current_report.valid and strategy_obj.name != FULL_REGENERATION:
        unchanged = RepairReport(
            attempted=False,
            changed=False,
            rounds=0,
            actions=[],
            remaining_issues=current_report.issues,
            strategy=strategy_obj.name,
            original_skill_hash=first_hash,
            repaired_skill_hash=first_hash,
            failure_type="none",
            validation_before=_dump_report(current_report),
            validation_after=_dump_report(current_report),
            repair_success=True,
        )
        return current, unchanged, current_report

    while rounds < max_rounds and (any(issue.repairable for issue in current_report.issues) or strategy_obj.name == FULL_REGENERATION):
        repaired, round_report, current_report = strategy_obj.repair(
            tool,
            current,
            validation_report=current_report,
            repair_round=rounds + 1,
        )
        rounds += 1
        current = repaired
        changed = changed or round_report.changed
        all_actions.extend(round_report.actions)
        all_traces.extend(round_report.repair_trace)
        last_round_report = round_report
        if current_report.valid or not round_report.changed:
            break

    failure_type = last_round_report.failure_type if last_round_report else "none"
    return (
        current,
        RepairReport(
            attempted=rounds > 0,
            changed=changed,
            rounds=rounds,
            actions=all_actions,
            remaining_issues=current_report.issues,
            strategy=strategy_obj.name,
            original_skill_hash=first_hash,
            repaired_skill_hash=_skill_hash(current),
            failure_type=failure_type,
            modified_sections=_modified_sections(all_actions),
            patch_text=_patch_text(all_actions),
            validation_before=last_round_report.validation_before if last_round_report else {},
            validation_after=_dump_report(current_report),
            repair_round=rounds,
            repair_success=current_report.valid,
            repair_trace=all_traces,
        ),
        current_report,
    )


def repair_behavior_failures(
    tool: ToolIR,
    skill: GeneratedSkill,
    behavior_report: BehaviorReport,
    strategy: str | None = NONUSE_BOUNDARY_PATCH,
    behavior_cases: Iterable[BehaviorCase] | None = None,
    predictor: PredictorBackend | None = None,
) -> tuple[GeneratedSkill, RepairReport, ValidationReport]:
    validation_report = validate_skill(tool, skill)
    strategy_obj = get_repair_strategy(strategy or NONUSE_BOUNDARY_PATCH)
    return strategy_obj.repair(
        tool,
        skill,
        validation_report=validation_report,
        behavior_report=behavior_report,
        behavior_cases=behavior_cases,
        predictor=predictor,
    )

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

import yaml

from autoskill.artifacts import clone_skill_as, skill_token_count
from autoskill.behavior import load_behavior_cases, run_behavior_tests
from autoskill.backends import HeuristicBackend, build_backend_from_config, safe_generate_skill
from autoskill.compactness import (
    build_compactness_variants,
    compactness_records_for_tool,
    write_compactness_stats_csv,
)
from autoskill.control_generation import load_toolir_records
from autoskill.ir import BehaviorCase, BehaviorReport, GeneratedSkill, RepairReport, ToolIR, ValidationReport
from autoskill.packaging import write_skill_package
from autoskill.reliability_score import compute_reliability_components, score_reliability_formula
from autoskill.repair import repair_behavior_failures, repair_skill
from autoskill.templates import build_argument_template, build_optional_argument_examples, build_structured_call_hints
from autoskill.validator import validate_skill


DEFAULT_CONFIG = {
    "seed": 42,
    "tools_path": "data/processed_toolir/tools.jsonl",
    "dev_controls_path": "data/controls/dev.jsonl",
    "output_dir": "skills",
    "candidate_k": 3,
    "max_tools": None,
    "generation_backend": {"type": "heuristic", "ablation_mode": "base_only"},
    "candidate_strategies": [
        "concise_default",
        "boundary_heavy",
        "example_heavy",
        "safety_first",
        "minimal_token",
    ],
    "selection_policy": "best_behavior_dev",
    "allow_oracle_upper_bound_dev": False,
    "repair_selected": False,
    "gate_selected": False,
    "max_repair_rounds": 2,
    "conditions": [
        "naive_skill_k1",
        "multi_candidate_skill_k3_validation_select",
        "multi_candidate_skill_k3_behavior_select",
        "multi_candidate_repaired_gated",
    ],
    "compactness_variants": {
        "enabled": False,
        "conditions": [
            "skill_ultra_compact",
            "skill_compact",
            "skill_medium",
            "skill_verbose",
            "generated_docs_verbose",
            "raw_docs_full",
        ],
        "records_path": "outputs/skill_compactness_records.jsonl",
        "stats_path": "outputs/tables/skill_compactness_stats.csv",
    },
}

SELECTION_POLICIES = {
    "best_validation_only",
    "best_behavior_dev",
    "best_reliability_score",
    "oracle_upper_bound_dev",
}


def load_multi_candidate_config(path: str | Path | None = None) -> Dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    config["generation_backend"] = dict(DEFAULT_CONFIG["generation_backend"])
    config["candidate_strategies"] = list(DEFAULT_CONFIG["candidate_strategies"])
    config["conditions"] = list(DEFAULT_CONFIG["conditions"])
    config["compactness_variants"] = dict(DEFAULT_CONFIG["compactness_variants"])
    if path:
        with Path(path).open("r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        if not isinstance(loaded, dict):
            raise ValueError("Multi-candidate skill config must be a mapping.")
        for key, value in loaded.items():
            if key == "generation_backend" and isinstance(value, dict):
                config["generation_backend"].update(value)
            elif key == "compactness_variants" and isinstance(value, dict):
                merged = dict(DEFAULT_CONFIG["compactness_variants"])
                merged.update(value)
                config["compactness_variants"] = merged
            else:
                config[key] = value
    config["candidate_k"] = int(config.get("candidate_k") or 1)
    if config["candidate_k"] < 1:
        raise ValueError("candidate_k must be >= 1.")
    if config["candidate_k"] > 5:
        raise ValueError("candidate_k above 5 is intentionally unsupported for the low-compute pipeline.")
    policy = str(config.get("selection_policy") or "best_behavior_dev")
    if policy not in SELECTION_POLICIES:
        raise ValueError(f"Unsupported selection_policy: {policy}")
    if policy == "oracle_upper_bound_dev" and not config.get("allow_oracle_upper_bound_dev"):
        raise ValueError("oracle_upper_bound_dev requires allow_oracle_upper_bound_dev: true and must never use test controls.")
    return config


def load_tools_as_toolir(path: str | Path, limit: int | None = None) -> List[ToolIR]:
    records = load_toolir_records(path)
    if isinstance(limit, int) and limit > 0:
        records = records[:limit]
    tools: List[ToolIR] = []
    for record in records:
        tools.append(_toolir_from_record(record))
    return tools


def run_multi_candidate_pipeline(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    max_tools = config.get("max_tools")
    tools = load_tools_as_toolir(config["tools_path"], limit=max_tools if isinstance(max_tools, int) else None)
    cases = _load_dev_behavior_cases(config.get("dev_controls_path"))
    backend = build_backend_from_config(config.get("generation_backend"))
    output_root = Path(str(config.get("output_dir") or "skills"))
    records: List[Dict[str, Any]] = []
    compactness_records: List[Dict[str, Any]] = []
    compactness_config = config.get("compactness_variants") or {}
    for tool in tools:
        base_skill = safe_generate_skill(tool, backend)
        if compactness_config.get("enabled"):
            variants = build_compactness_variants(
                tool,
                base_skill,
                conditions=compactness_config.get("conditions"),
                constraints_by_condition=compactness_config.get("constraints_by_condition") or {},
            )
            for variant in variants:
                validation_report = validate_skill(tool, variant)
                package_dir = output_root / "compactness" / _slug(tool.tool_name) / _slug(variant.baseline_name)
                write_skill_package(package_dir, tool, variant, validation_report)
            compactness_records.extend(compactness_records_for_tool(tool, variants))
        candidates = generate_skill_candidates(
            tool,
            base_skill,
            k=int(config.get("candidate_k") or 1),
            strategies=list(config.get("candidate_strategies") or []),
        )
        score_rows = score_skill_candidates(tool, candidates, cases)
        selected = select_candidate(score_rows, policy=str(config.get("selection_policy") or "best_behavior_dev"))
        selected_skill = deepcopy(selected["skill"])
        selected_validation = selected["validation_report"]
        selected_behavior = selected.get("behavior_report")
        selected_reliability = selected["reliability_score_obj"]
        repair_report: RepairReport | None = None
        if config.get("repair_selected"):
            selected_skill, repair_report, selected_validation = repair_skill(
                tool,
                selected_skill,
                max_rounds=int(config.get("max_repair_rounds") or 2),
            )
            if selected_behavior is not None and not selected_behavior.valid:
                selected_behavior = run_behavior_tests(tool, selected_skill, cases)
                selected_skill, behavior_repair, selected_validation = repair_behavior_failures(
                    tool,
                    selected_skill,
                    selected_behavior,
                    behavior_cases=cases,
                )
                repair_report = behavior_repair if repair_report is None else repair_report
                selected_behavior = run_behavior_tests(tool, selected_skill, cases)
            selected_reliability = score_reliability_formula(tool, selected_skill, selected_validation, selected_behavior)
        if config.get("gate_selected"):
            selected_skill = clone_skill_as(selected_skill, "gated_skill")
            selected_skill.metadata = {**selected_skill.metadata, "gate_decision": selected_reliability.decision}

        tool_dir = output_root / _slug(tool.tool_name)
        write_candidate_artifacts(
            tool_dir=tool_dir,
            tool=tool,
            candidates=candidates,
            score_rows=score_rows,
            selected_score=selected,
            selected_skill=selected_skill,
            selected_validation=selected_validation,
            selected_behavior=selected_behavior,
            selected_reliability=selected_reliability,
            repair_report=repair_report,
            selection_policy=str(config.get("selection_policy") or "best_behavior_dev"),
        )
        records.append(
            {
                "tool_name": tool.tool_name,
                "selected_candidate_id": selected["candidate_id"],
                "selection_policy": config.get("selection_policy"),
                "selected_score": selected["candidate_score"],
                "reliability_score": selected_reliability.model_dump(),
                "output_dir": str(tool_dir),
            }
        )
    write_jsonl(output_root / "candidate_scores.jsonl", _flatten_score_rows(records_root=output_root))
    if compactness_config.get("enabled"):
        records_path = Path(str(compactness_config.get("records_path") or (output_root / "skill_compactness_records.jsonl")))
        stats_path = Path(str(compactness_config.get("stats_path") or "outputs/tables/skill_compactness_stats.csv"))
        write_jsonl(records_path, compactness_records)
        write_compactness_stats_csv(stats_path, compactness_records)
    return records


def generate_skill_candidates(tool: ToolIR, base_skill: GeneratedSkill, *, k: int = 3, strategies: Sequence[str] | None = None) -> List[Dict[str, Any]]:
    strategy_order = list(strategies or DEFAULT_CONFIG["candidate_strategies"])
    if k == 1:
        strategy_order = ["concise_default"]
    selected_strategies = strategy_order[:k]
    candidates: List[Dict[str, Any]] = []
    for index, strategy in enumerate(selected_strategies):
        skill = _skill_for_strategy(tool, base_skill, strategy)
        candidate_id = f"{_slug(tool.tool_name)}__cand_{index:02d}_{strategy}"
        skill.metadata = {
            **skill.metadata,
            "candidate_id": candidate_id,
            "generation_strategy": strategy,
            "prompt_template_id": f"heuristic_{strategy}_v1",
        }
        skill.method_trace = [
            *skill.method_trace,
            {
                "trace_type": "multi_candidate_generation",
                "candidate_id": candidate_id,
                "generation_strategy": strategy,
                "prompt_template_id": f"heuristic_{strategy}_v1",
            },
        ]
        candidates.append(
            {
                "candidate_id": candidate_id,
                "generation_strategy": strategy,
                "prompt_template_id": f"heuristic_{strategy}_v1",
                "skill": skill,
                "candidate": candidate_payload(candidate_id, strategy, f"heuristic_{strategy}_v1", skill),
            }
        )
    return candidates


def candidate_payload(candidate_id: str, strategy: str, prompt_template_id: str, skill: GeneratedSkill) -> Dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "generation_strategy": strategy,
        "prompt_template_id": prompt_template_id,
        "skill_text": skill_to_text(skill),
        "argument_template": skill.argument_template,
        "examples": skill.examples,
        "when_to_use": skill.when_to_use,
        "when_not_to_use": skill.when_not_to_use,
        "token_count": skill_token_count(skill),
        "skill_token_count": skill.metadata.get("token_accounting", {}).get("skill_token_count", skill_token_count(skill)),
        "prompt_token_count": skill.metadata.get("token_accounting", {}).get("prompt_token_count"),
        "total_representation_tokens": skill.metadata.get("token_accounting", {}).get("total_representation_tokens"),
        "sections_included": skill.metadata.get("token_accounting", {}).get("sections_included"),
        "examples_count": len(skill.examples),
        "nonuse_boundary_count": len(skill.when_not_to_use),
        "skill": skill.model_dump(),
    }


def score_skill_candidates(tool: ToolIR, candidates: Sequence[Dict[str, Any]], cases: Sequence[BehaviorCase]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for candidate in candidates:
        skill: GeneratedSkill = candidate["skill"]
        validation_report = validate_skill(tool, skill)
        behavior_report = run_behavior_tests(tool, skill, cases) if cases else None
        reliability_score = score_reliability_formula(tool, skill, validation_report, behavior_report)
        components = compute_reliability_components(tool, skill, validation_report, behavior_report)
        schema_faithfulness = _schema_faithfulness(tool, validation_report, skill)
        compactness = components["C"]
        structural_validity = components["V"]
        positive_pass = components["P"]
        negative_non_harm = components["N"]
        safety = components["S"]
        candidate_score = round(
            (0.25 * structural_validity)
            + (0.15 * compactness)
            + (0.20 * schema_faithfulness)
            + (0.20 * positive_pass)
            + (0.15 * negative_non_harm)
            + (0.05 * safety),
            6,
        )
        rows.append(
            {
                **candidate["candidate"],
                "tool_name": tool.tool_name,
                "candidate_score": candidate_score,
                "structural_validity": structural_validity,
                "compactness": compactness,
                "schema_faithfulness": schema_faithfulness,
                "positive_dev_control_pass_rate": positive_pass,
                "negative_dev_control_non_harm_rate": negative_non_harm,
                "safety_annotation_preservation": safety,
                "validation_valid": validation_report.valid,
                "validation_error_count": sum(1 for issue in validation_report.issues if issue.severity == "error"),
                "validation_warning_count": sum(1 for issue in validation_report.issues if issue.severity == "warning"),
                "behavior_metrics": behavior_report.metrics if behavior_report else {},
                "reliability_score": reliability_score.model_dump(),
                "validation_report": validation_report,
                "behavior_report": behavior_report,
                "reliability_score_obj": reliability_score,
                "skill": skill,
            }
        )
    return rows


def select_candidate(score_rows: Sequence[Dict[str, Any]], *, policy: str) -> Dict[str, Any]:
    if not score_rows:
        raise ValueError("Cannot select from an empty candidate set.")
    if policy == "best_validation_only":
        key = lambda row: (
            row["structural_validity"],
            row["schema_faithfulness"],
            row["compactness"],
            row["safety_annotation_preservation"],
            -row["token_count"],
            row["candidate_id"],
        )
    elif policy == "best_behavior_dev":
        key = lambda row: (
            row["negative_dev_control_non_harm_rate"],
            row["positive_dev_control_pass_rate"],
            row["structural_validity"],
            row["schema_faithfulness"],
            row["compactness"],
            row["candidate_id"],
        )
    elif policy == "best_reliability_score":
        key = lambda row: (
            float(row["reliability_score"]["score"]),
            row["structural_validity"],
            row["negative_dev_control_non_harm_rate"],
            row["candidate_id"],
        )
    elif policy == "oracle_upper_bound_dev":
        key = lambda row: (
            row["positive_dev_control_pass_rate"] + row["negative_dev_control_non_harm_rate"],
            row["structural_validity"],
            row["schema_faithfulness"],
            row["candidate_id"],
        )
    else:
        raise ValueError(f"Unsupported selection policy: {policy}")
    return max(score_rows, key=key)


def write_candidate_artifacts(
    *,
    tool_dir: Path,
    tool: ToolIR,
    candidates: Sequence[Dict[str, Any]],
    score_rows: Sequence[Dict[str, Any]],
    selected_score: Dict[str, Any],
    selected_skill: GeneratedSkill,
    selected_validation: ValidationReport,
    selected_behavior: BehaviorReport | None,
    selected_reliability: Any,
    repair_report: RepairReport | None,
    selection_policy: str,
) -> None:
    candidates_dir = tool_dir / "candidates"
    candidates_dir.mkdir(parents=True, exist_ok=True)
    for candidate in candidates:
        payload = candidate["candidate"]
        candidate_filename = candidate['candidate_id'][:50]
        (candidates_dir / f"{candidate_filename}.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    score_payloads = [_json_score_row(row) for row in score_rows]
    write_jsonl(tool_dir / "candidate_scores.jsonl", score_payloads)
    selected_payload = candidate_payload(
        str(selected_score["candidate_id"]),
        str(selected_score["generation_strategy"]),
        str(selected_score["prompt_template_id"]),
        selected_skill,
    )
    (tool_dir / "selected_candidate.json").write_text(json.dumps(selected_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    report = {
        "tool_name": tool.tool_name,
        "selection_policy": selection_policy,
        "candidate_count": len(candidates),
        "selected_candidate_id": selected_score["candidate_id"],
        "selected_generation_strategy": selected_score["generation_strategy"],
        "selected_candidate_score": selected_score["candidate_score"],
        "selected_reliability_score": selected_reliability.model_dump(),
        "selection_inputs": score_payloads,
        "dev_controls_used": bool(selected_behavior and selected_behavior.results),
        "test_controls_used": False,
    }
    (tool_dir / "selection_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_skill_package(
        tool_dir / "selected_package",
        tool,
        selected_skill,
        selected_validation,
        behavior_report=selected_behavior,
        reliability_score=selected_reliability,
        repair_report=repair_report,
    )


def skill_to_text(skill: GeneratedSkill) -> str:
    lines = [skill.skill_summary, "When to use:", *[f"- {line}" for line in skill.when_to_use], "When not to use:", *[f"- {line}" for line in skill.when_not_to_use]]
    if skill.argument_template:
        lines.extend(["Argument template:", json.dumps(skill.argument_template, ensure_ascii=False, sort_keys=True)])
    if skill.examples:
        lines.append("Examples:")
        for example in skill.examples:
            lines.append(str(example.get("scenario", "Example")))
            lines.append(json.dumps(example.get("arguments", {}), ensure_ascii=False, sort_keys=True))
    return "\n".join(line for line in lines if line is not None)


def write_jsonl(path: str | Path, records: Iterable[Dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _skill_for_strategy(tool: ToolIR, base_skill: GeneratedSkill, strategy: str) -> GeneratedSkill:
    skill = deepcopy(base_skill)
    skill.baseline_name = "multi_candidate_skill"
    required = [arg.name for arg in tool.arguments if arg.required]
    optional = [arg.name for arg in tool.arguments if not arg.required]
    if strategy == "concise_default":
        skill.skill_summary = _compact_sentence(skill.skill_summary)
        skill.when_to_use = skill.when_to_use[:2]
        skill.when_not_to_use = _dedupe_lines([*skill.when_not_to_use[:3], "Do not use when required inputs are missing."])
        skill.examples = skill.examples[:2]
    elif strategy == "boundary_heavy":
        skill.when_not_to_use = _dedupe_lines(
            [
                *skill.when_not_to_use,
                "Do not use for adjacent tools with similar names, descriptions, or arguments.",
                "Do not use for read/write, search/fetch, create/update, delete/preview, or execute/explain mismatches.",
                "If the request lacks required fields, abstain or ask for clarification.",
            ]
        )
        skill.when_to_use = _dedupe_lines([*skill.when_to_use, f"Use only when the request clearly needs `{tool.tool_name}`."])
    elif strategy == "example_heavy":
        examples = list(skill.examples)
        minimal = build_argument_template(tool, include_optional=False, variant=2)
        if minimal:
            examples.append({"scenario": "Required-argument dev behavior example.", "arguments": minimal})
        examples.extend(build_optional_argument_examples(tool, variant=3, max_examples=3))
        skill.examples = examples[:5]
        skill.argument_template = minimal
        call_hints = build_structured_call_hints(tool)
        skill.when_to_use = _dedupe_lines([*skill.when_to_use, *call_hints["when_to_use"], "Use examples to map paraphrases into schema-faithful arguments."])
        skill.when_not_to_use = _dedupe_lines([*skill.when_not_to_use, *call_hints["when_not_to_use"]])
    elif strategy == "safety_first":
        skill.when_not_to_use = _dedupe_lines(
            [
                "Prefer abstention over guessing when the request is ambiguous.",
                "Do not invent optional information, unsupported arguments, or hidden capabilities.",
                *skill.when_not_to_use,
                *[f"Required field `{name}` must be grounded in the user request." for name in required[:4]],
            ]
        )
        if tool.side_effect_hints or tool.safety_hints:
            skill.when_not_to_use.append("For side-effectful actions, preserve explicit user intent and avoid preview-only or read-only mismatches.")
    elif strategy == "minimal_token":
        skill.skill_summary = _compact_sentence(skill.skill_summary, max_words=28)
        skill.when_to_use = [f"Use `{tool.tool_name}` for direct requests matching its schema and documented purpose."]
        if required:
            skill.when_to_use.append("Required: " + ", ".join(f"`{name}`" for name in required[:6]) + ".")
        if optional:
            skill.when_to_use.append("Optional fields are used only when explicitly provided.")
        skill.when_not_to_use = ["Do not use for adjacent tools, missing required fields, unsupported arguments, or unsafe side-effect mismatches."]
        skill.examples = skill.examples[:1]
        skill.argument_template = build_argument_template(tool, include_optional=False, variant=0)
    else:
        skill.metadata = {**skill.metadata, "unknown_generation_strategy": strategy}
    return skill


def _schema_faithfulness(tool: ToolIR, validation_report: ValidationReport, skill: GeneratedSkill) -> float:
    if not validation_report.valid:
        return 0.0
    arg_names = {arg.name for arg in tool.arguments}
    if not arg_names:
        return 1.0
    covered = set(skill.argument_template).intersection(arg_names)
    for example in skill.examples:
        args = example.get("arguments")
        if isinstance(args, dict):
            covered.update(set(args).intersection(arg_names))
    hallucination_warnings = sum(1 for issue in validation_report.issues if issue.code in {"hallucinated_argument", "unsupported_option_in_text"})
    coverage = len(covered) / len(arg_names)
    return round(max(0.0, coverage - (0.1 * hallucination_warnings)), 4)


def _load_dev_behavior_cases(path: Any) -> List[BehaviorCase]:
    if not path:
        return []
    input_path = Path(str(path))
    if not input_path.exists():
        return []
    return [case for case in load_behavior_cases(input_path) if case.split == "dev"]


def _toolir_from_record(record: Dict[str, Any]) -> ToolIR:
    return ToolIR(
        tool_name=str(record.get("tool_name") or ""),
        server_name=record.get("server_name"),
        tool_purpose=record.get("tool_purpose"),
        input_schema_raw=dict(record.get("input_schema_raw") or {}),
        arguments=[] if not isinstance(record.get("arguments"), list) else [
            _argument_from_record(arg) for arg in record.get("arguments", []) if isinstance(arg, dict)
        ],
        output_hint=record.get("output_hint"),
        auth_or_env_notes=record.get("auth_or_env_notes"),
        usage_warnings=list(record.get("usage_warnings") or []),
        doc_snippets=list(record.get("doc_snippets") or []),
        source_pointer=record.get("source_pointer"),
        doc_completeness=float(record.get("doc_completeness") or 0.0),
        schema_complexity=dict(record.get("schema_complexity") or {}),
        ambiguity_flags=list(record.get("ambiguity_flags") or []),
        provenance=dict(record.get("provenance") or {}),
        side_effect_hints=list(record.get("side_effect_hints") or []),
        safety_hints=list(record.get("safety_hints") or []),
    )


def _argument_from_record(arg: Dict[str, Any]) -> Any:
    from autoskill.ir import ArgumentIR

    return ArgumentIR(
        name=str(arg.get("name") or ""),
        type=str(arg.get("type") or "unknown"),
        required=bool(arg.get("required")),
        default=arg.get("default"),
        enum=arg.get("enum") if isinstance(arg.get("enum"), list) else None,
        description=arg.get("description"),
        items_type=arg.get("items_type"),
        properties=arg.get("properties") if isinstance(arg.get("properties"), dict) else None,
        required_properties=list(arg.get("required_properties") or []),
        nullable=bool(arg.get("nullable")),
        format=arg.get("format"),
        schema_path=arg.get("schema_path"),
    )


def _flatten_score_rows(records_root: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for path in sorted(records_root.glob("*/candidate_scores.jsonl")):
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows


def _json_score_row(row: Dict[str, Any]) -> Dict[str, Any]:
    keys = [
        "tool_name",
        "candidate_id",
        "generation_strategy",
        "prompt_template_id",
        "token_count",
        "skill_token_count",
        "prompt_token_count",
        "total_representation_tokens",
        "sections_included",
        "examples_count",
        "nonuse_boundary_count",
        "candidate_score",
        "structural_validity",
        "compactness",
        "schema_faithfulness",
        "positive_dev_control_pass_rate",
        "negative_dev_control_non_harm_rate",
        "safety_annotation_preservation",
        "validation_valid",
        "validation_error_count",
        "validation_warning_count",
        "behavior_metrics",
        "reliability_score",
    ]
    return {key: row.get(key) for key in keys}


def _compact_sentence(text: str, max_words: int = 40) -> str:
    words = str(text or "").split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]).rstrip(".,") + "."


def _dedupe_lines(lines: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for line in lines:
        text = " ".join(str(line).split())
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return slug[:100] or "tool"

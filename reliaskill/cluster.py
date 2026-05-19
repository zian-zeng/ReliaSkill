from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from autoskill.behavior import load_behavior_cases, run_behavior_tests
from autoskill.benchmark import load_benchmark_tasks
from autoskill.config import load_json_config
from autoskill.eval_types import EvalTask
from autoskill.experiment import (
    build_skill_variant_map,
    load_tools,
    run_benchmark_pipeline,
    run_packaging_pipeline,
    run_routing_benchmark_pipeline,
)
from autoskill.generator import SkillGenerator
from autoskill.local_model import clear_model_cache
from autoskill.artifacts import GATED_SKILL, GENERATED_SKILL_BASE, RELIASKILL_CHALLENGER, REPAIRED_SKILL, clone_skill_as
from autoskill.conditions import RELIASKILL_V1_CONTRACT_ABLATIONS, normalize_condition_names
from autoskill.contracts import build_contract_counterexamples, compile_skill_contract
from autoskill.metrics import build_metric_tables, write_metric_tables
from autoskill.multi_candidate import (
    generate_skill_candidates,
    load_multi_candidate_config,
    score_skill_candidates,
    select_candidate,
    write_candidate_artifacts,
)
from autoskill.packaging import write_skill_package
from autoskill.predictor import build_predictor_from_config, safe_predict
from autoskill.quality import score_reliability
from autoskill.reliability import build_reliability_variants
from autoskill.templates import build_schema_contract_lines
from autoskill.validator import validate_skill
from reliaskill.live_exec.evaluator import evaluate_live_exec_tasks
from reliaskill.live_exec.task_builder import build_live_exec_tasks
from reliaskill.live_exec.tool_defs import build_live_exec_tools
from reliaskill.scheduler import load_model_config


RELIABILITY_CONDITIONS = {"naive_skill", "validated_skill", "repaired_skill", "gated_skill", RELIASKILL_CHALLENGER}


def slugify(value: str) -> str:
    slug = "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in value)
    return slug.strip("_")[:80] or "unknown"


def tool_slug(value: str) -> str:
    slug = "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in value)
    slug = slug or "unknown"
    if len(slug) <= 50 and slug == slug.lower():
        return slug
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"{slug[:37].rstrip('_')}_{digest}"


def shared_package_root(config: Dict[str, Any], output_root: str | Path | None = None) -> Path:
    shared = config.get("shared_skill_packages") if isinstance(config.get("shared_skill_packages"), dict) else {}
    root = Path(output_root or config.get("output_root") or "outputs/emnlp_acceptance")
    if output_root is not None:
        return root / "shared_packages"
    if shared.get("root"):
        return Path(str(shared["root"]))
    return root / "shared_packages"


def _multi_candidate_shared_config(config: Dict[str, Any]) -> Dict[str, Any] | None:
    skills_config = config.get("skills") if isinstance(config.get("skills"), dict) else {}
    multi_config_path = skills_config.get("multi_candidate_config")
    if not multi_config_path:
        return None
    path = Path(str(multi_config_path))
    if not path.exists():
        raise FileNotFoundError(f"Configured multi-candidate skill config does not exist: {path}")
    multi_config = load_multi_candidate_config(path)
    if skills_config.get("candidate_k") is not None:
        multi_config["candidate_k"] = int(skills_config["candidate_k"])
    if int(multi_config.get("candidate_k") or 1) < 1:
        raise ValueError("Multi-candidate shared package candidate_k must be >= 1.")
    if int(multi_config.get("candidate_k") or 1) > 5:
        raise ValueError("Multi-candidate shared package candidate_k above 5 is intentionally unsupported.")
    return multi_config


def _ensure_dev_behavior_cases(cases: Sequence[Any], source_path: str | Path) -> None:
    if not cases:
        raise ValueError(f"Multi-candidate shared package construction requires development controls: {source_path}")
    non_dev = sorted({str(getattr(case, "split", "")) for case in cases if str(getattr(case, "split", "dev")) != "dev"})
    if non_dev:
        raise ValueError(
            "Multi-candidate shared package construction may only use development controls; "
            f"{source_path} contains split(s): {', '.join(non_dev)}"
        )


def _select_multi_candidate_base_skill(
    *,
    root: Path,
    tool: Any,
    base_skill: Any,
    behavior_cases: Sequence[Any],
    multi_config: Dict[str, Any],
) -> Any:
    candidates = generate_skill_candidates(
        tool,
        base_skill,
        k=int(multi_config.get("candidate_k") or 1),
        strategies=list(multi_config.get("candidate_strategies") or []),
    )
    score_rows = score_skill_candidates(tool, candidates, behavior_cases)
    selected = select_candidate(score_rows, policy=str(multi_config.get("selection_policy") or "best_behavior_dev"))
    selected_skill = selected["skill"]
    selected_skill.metadata = {
        **selected_skill.metadata,
        "shared_package_base": "multi_candidate_selected",
        "selected_candidate_id": selected["candidate_id"],
        "selection_policy": str(multi_config.get("selection_policy") or "best_behavior_dev"),
        "test_controls_used": False,
    }
    selected_skill.method_trace = [
        *selected_skill.method_trace,
        {
            "trace_type": "multi_candidate_selection",
            "selected_candidate_id": selected["candidate_id"],
            "selection_policy": str(multi_config.get("selection_policy") or "best_behavior_dev"),
            "candidate_count": len(candidates),
            "dev_controls_used": True,
            "test_controls_used": False,
        },
    ]
    write_candidate_artifacts(
        tool_dir=root / "_multi_candidate_selection" / tool_slug(tool.tool_name),
        tool=tool,
        candidates=candidates,
        score_rows=score_rows,
        selected_score=selected,
        selected_skill=selected_skill,
        selected_validation=selected["validation_report"],
        selected_behavior=selected.get("behavior_report"),
        selected_reliability=selected["reliability_score_obj"],
        repair_report=None,
        selection_policy=str(multi_config.get("selection_policy") or "best_behavior_dev"),
    )
    return selected_skill


def _build_challenger_skill(
    source_skill: Any,
    *,
    tool: Any,
    source_row: Dict[str, Any],
    gate_row: Dict[str, Any],
    selection_report_path: Path,
) -> Any:
    challenger = clone_skill_as(source_skill, RELIASKILL_CHALLENGER)
    source_score = source_row["reliability_score"]
    gate_score = gate_row["reliability_score"]
    repair = source_row["repair_report"]
    selection = _load_selection_report(selection_report_path)
    evidence_lines = _challenger_evidence_lines(source_score, repair, selection, gate_score=gate_score)
    if evidence_lines:
        challenger.skill_summary = _compact_join(
            [
                "Full ReliaSkill v1 artifact.",
                *evidence_lines,
                challenger.skill_summary,
            ],
            max_chars=900,
        )
    if source_score.decision == "deploy":
        challenger.when_to_use = _dedupe_text_lines(
            [
                "Use this full ReliaSkill artifact only when the request directly matches the tool purpose and every required input can be grounded in the user request.",
                "Prefer the dev-selected, repaired, and gate-evidenced boundaries in this artifact over broad keyword matches.",
                *challenger.when_to_use,
            ],
            limit=6,
        )
        challenger.when_not_to_use = _dedupe_text_lines(
            [
                "Abstain rather than invent missing required arguments, enum values, unsupported fields, or hidden tool capabilities.",
                *challenger.when_not_to_use,
                "Do not use for adjacent, similar-tool, read/write-mismatched, explanation-only, or ambiguous requests.",
            ],
            limit=14,
        )
    else:
        challenger.when_to_use = _dedupe_text_lines(
            [
                "Use this full ReliaSkill artifact only for exact, schema-grounded requests; non-use boundaries take priority over broad keyword overlap.",
                *challenger.when_to_use,
            ],
            limit=6,
        )
        challenger.when_not_to_use = _dedupe_text_lines(
            [
                "Abstain on any request that matches a non-use boundary or lacks grounded required arguments.",
                *challenger.when_not_to_use,
            ],
            limit=14,
        )
    challenger.metadata = {
        **challenger.metadata,
        "condition_family": RELIASKILL_CHALLENGER,
        "source_condition": REPAIRED_SKILL,
        "gate_source_condition": GATED_SKILL,
        "artifact_backed": True,
        "requires_improved_package": True,
        "pipeline_stages": [
            "generated_skill_base_package",
            "dev_multi_candidate_selection",
            "validation",
            "repair",
            "executable_contract_compilation",
            "adaptive_contract_policy",
            "contextual_grounding_contract",
            "multi_step_contract_plan_composition",
            "execution_feedback_contract_interpreter",
            "soft_reliability_gate_evidence",
            "proof_carrying_contract_routing",
            "schema_affordance_routing_gate",
            "action_intent_routing_gate",
            "runtime_schema_contract_verifier",
            "proof_carrying_runtime_contract",
            "runtime_required_argument_grounding",
            "runtime_false_abstention_rescue",
            "runtime_action_intent_gate",
            "runtime_routing_boundary",
        ],
        "uses_runtime_schema_contract_verifier": True,
        "uses_executable_skill_contract": True,
        "uses_contract_proof_ledger": True,
        "uses_adaptive_contract_policy": True,
        "uses_contextual_grounding_contract": True,
        "uses_multi_step_contract_planning": True,
        "uses_execution_feedback_contract": True,
        "test_controls_used": False,
        "prompt_visible_method_evidence": True,
        "schema_contract": build_schema_contract_lines(tool),
        "executable_contract": compile_skill_contract(tool, challenger).model_dump(),
        "contract_counterexamples": build_contract_counterexamples(tool, challenger),
        "source_reliability_decision": source_score.decision,
        "source_reliability_score": source_score.score,
        "reliability_gate_decision": gate_score.decision,
        "reliability_gate_score": gate_score.score,
        "selected_candidate_id": selection.get("selected_candidate_id"),
        "selection_policy": selection.get("selection_policy"),
    }
    challenger.method_trace = [
        *challenger.method_trace,
        {
            "trace_type": "reliaskill_v1_composition",
            "source_condition": REPAIRED_SKILL,
            "gate_source_condition": GATED_SKILL,
            "condition": RELIASKILL_CHALLENGER,
            "artifact_backed": True,
            "prompt_visible_method_evidence": True,
            "test_controls_used": False,
        },
    ]
    return challenger


def _load_selection_report(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _challenger_evidence_lines(score: Any, repair: Any, selection: Dict[str, Any], *, gate_score: Any | None = None) -> List[str]:
    lines = [
        "Pipeline: dev-selected candidate, validation, repair, and reliability gate evidence recorded in package metadata.",
    ]
    candidate_id = selection.get("selected_candidate_id")
    strategy = selection.get("selected_generation_strategy")
    policy = selection.get("selection_policy")
    if candidate_id or strategy or policy:
        lines.append(
            "Selection: "
            + ", ".join(
                item
                for item in [
                    f"policy={policy}" if policy else "",
                    f"strategy={strategy}" if strategy else "",
                    f"candidate={candidate_id}" if candidate_id else "",
                ]
                if item
            )
            + "."
        )
    if repair.attempted:
        changed = "changed" if repair.changed else "no text change"
        lines.append(f"Repair: {changed}, rounds={repair.rounds}, primary_failure={repair.failure_type or 'none'}.")
    return lines


def _compact_join(lines: Sequence[str], *, max_chars: int) -> str:
    text = " ".join(line.strip() for line in lines if str(line).strip())
    return text[: max_chars - 3].rstrip() + "..." if len(text) > max_chars else text


def _dedupe_text_lines(lines: Sequence[str], *, limit: int) -> List[str]:
    result: List[str] = []
    seen = set()
    for line in lines:
        clean = str(line).strip()
        if not clean:
            continue
        key = clean.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(clean)
        if len(result) >= limit:
            break
    return result


def _write_challenger_method_metadata(
    *,
    package_dir: Path,
    tool_name: str,
    selection_report_path: Path,
    reliability_row: Dict[str, Any],
    source_row: Dict[str, Any],
    gate_row: Dict[str, Any],
) -> None:
    if not selection_report_path.exists():
        raise FileNotFoundError(
            f"`{RELIASKILL_CHALLENGER}` requires a multi-candidate selection report for `{tool_name}`: "
            f"{selection_report_path}"
        )
    shutil.copyfile(selection_report_path, package_dir / "selection_report.json")
    score = reliability_row["reliability_score"]
    source_score = source_row["reliability_score"]
    gate_score = gate_row["reliability_score"]
    repair = source_row["repair_report"]
    metadata = {
        "condition": RELIASKILL_CHALLENGER,
        "tool_name": tool_name,
        "source_condition": REPAIRED_SKILL,
        "gate_source_condition": GATED_SKILL,
        "artifact_backed": True,
        "pipeline_stages": [
            "generated_skill_base_package",
            "dev_multi_candidate_selection",
            "validation",
            "repair",
            "executable_contract_compilation",
            "adaptive_contract_policy",
            "contextual_grounding_contract",
            "multi_step_contract_plan_composition",
            "execution_feedback_contract_interpreter",
            "soft_reliability_gate_evidence",
            "proof_carrying_contract_routing",
            "schema_affordance_routing_gate",
            "action_intent_routing_gate",
            "runtime_schema_contract_verifier",
            "proof_carrying_runtime_contract",
            "runtime_required_argument_grounding",
            "runtime_false_abstention_rescue",
            "runtime_action_intent_gate",
            "runtime_routing_boundary",
        ],
        "dev_controls_used": True,
        "uses_runtime_schema_contract_verifier": True,
        "uses_executable_skill_contract": True,
        "uses_contract_proof_ledger": True,
        "uses_adaptive_contract_policy": True,
        "uses_contextual_grounding_contract": True,
        "uses_multi_step_contract_planning": True,
        "uses_execution_feedback_contract": True,
        "test_controls_used": False,
        "reliaskill_v1_decision": score.decision,
        "reliaskill_v1_score": score.score,
        "source_reliability_decision": source_score.decision,
        "source_reliability_score": source_score.score,
        "gate_decision": gate_score.decision,
        "gate_score": gate_score.score,
        "repair_attempted": repair.attempted,
        "repair_changed": repair.changed,
        "repair_rounds": repair.rounds,
    }
    (package_dir / "method_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")


def selected_tool_names(config: Dict[str, Any], tools: Dict[str, Any], *, shard_index: int | None = None, num_shards: int | None = None) -> List[str]:
    names = sorted(tools)
    max_tools = _configured_max_tools(config)
    if max_tools:
        names = names[:max_tools]
    if shard_index is None and num_shards is None:
        return names
    if shard_index is None or num_shards is None:
        raise ValueError("shard_index and num_shards must be provided together.")
    if num_shards <= 0:
        raise ValueError("num_shards must be positive.")
    if shard_index < 0 or shard_index >= num_shards:
        raise ValueError("shard_index must be in [0, num_shards).")
    return [name for index, name in enumerate(names) if index % num_shards == shard_index]


def build_shared_skill_packages(
    config_path: str | Path,
    *,
    output_root: str | Path | None = None,
    force: bool = False,
) -> Dict[str, Any]:
    config = load_json_config(config_path)
    strict_backends = _strict_backends(config)
    all_tools = load_tools(config["tools_path"])
    names = selected_tool_names(config, all_tools)
    benchmark_tools = {name: all_tools[name] for name in names}
    live_tools = _configured_live_tools(config)
    tools = {**benchmark_tools, **live_tools}
    root = shared_package_root(config, output_root)
    if force and root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)

    generator = SkillGenerator(backend_config=config.get("generator"), allow_fallback=not strict_backends)
    allowed_conditions = normalize_condition_names([str(item) for item in config.get("conditions") or []]) or []
    requested_reliability_conditions = sorted(set(allowed_conditions).intersection(RELIABILITY_CONDITIONS))
    requested_contract_ablations = sorted(set(allowed_conditions).intersection(RELIASKILL_V1_CONTRACT_ABLATIONS))
    if requested_contract_ablations and RELIASKILL_CHALLENGER not in requested_reliability_conditions:
        requested_reliability_conditions.append(RELIASKILL_CHALLENGER)
    packaging_conditions = [
        condition
        for condition in allowed_conditions
        if condition != RELIASKILL_CHALLENGER and condition not in RELIASKILL_V1_CONTRACT_ABLATIONS
    ]
    if requested_reliability_conditions and GENERATED_SKILL_BASE not in packaging_conditions:
        packaging_conditions.append(GENERATED_SKILL_BASE)
    package_records, package_summary, _ = run_packaging_pipeline(
        tools=tools,
        output_dir=root,
        generator=generator,
        allowed_conditions=packaging_conditions or None,
    )

    reliability_conditions = requested_reliability_conditions
    reliability_records = []
    multi_candidate_config = None
    multi_candidate_base_records = []
    if reliability_conditions:
        multi_candidate_config = _multi_candidate_shared_config(config)
        if RELIASKILL_CHALLENGER in reliability_conditions and multi_candidate_config is None:
            raise ValueError(f"`{RELIASKILL_CHALLENGER}` requires `skills.multi_candidate_config`.")
        shared_config = config.get("shared_skill_packages") if isinstance(config.get("shared_skill_packages"), dict) else {}
        behavior_path = (
            shared_config.get("dev_controls_path")
            or config.get("dev_controls_path")
            or "data/controls/dev.jsonl"
        )
        behavior_cases = load_behavior_cases(behavior_path)
        predictor_config = (
            shared_config.get("reliability_predictor")
            or config.get("reliability_predictor")
            or config.get("predictor")
            or {"type": "heuristic"}
        )
        predictor = build_predictor_from_config(predictor_config)
        max_repair_rounds = int(shared_config.get("max_repair_rounds") or 2)
        deploy_threshold = float(shared_config.get("deploy_threshold") or 85.0)
        if multi_candidate_config is not None:
            _ensure_dev_behavior_cases(behavior_cases, behavior_path)
        for tool in tools.values():
            base_skill = build_skill_variant_map(
                tool,
                tools,
                generator,
                allowed_conditions=["generated_skill_base"],
                package_manager_dir=root,
                allow_package_generation=False,
            )["generated_skill_base"]
            if multi_candidate_config is not None:
                base_skill = _select_multi_candidate_base_skill(
                    root=root,
                    tool=tool,
                    base_skill=base_skill,
                    behavior_cases=behavior_cases,
                    multi_config=multi_candidate_config,
                )
                multi_candidate_base_records.append(
                    {
                        "tool_name": tool.tool_name,
                        "selection_policy": str(multi_candidate_config.get("selection_policy") or "best_behavior_dev"),
                        "candidate_k": int(multi_candidate_config.get("candidate_k") or 1),
                    }
                )
            variants = build_reliability_variants(
                tool,
                generator=generator,
                behavior_cases=behavior_cases,
                predictor=predictor,
                max_repair_rounds=max_repair_rounds,
                deploy_threshold=deploy_threshold,
                base_generated_skill=base_skill,
                allow_predictor_fallback=not strict_backends,
            )
            for condition in reliability_conditions:
                selection_report_path = root / "_multi_candidate_selection" / tool_slug(tool.tool_name) / "selection_report.json"
                if condition == RELIASKILL_CHALLENGER:
                    source_condition = REPAIRED_SKILL
                    source_row = variants[REPAIRED_SKILL]
                    gate_row = variants[GATED_SKILL]
                    package_skill = _build_challenger_skill(
                        source_row["skill"],
                        tool=tool,
                        source_row=source_row,
                        gate_row=gate_row,
                        selection_report_path=selection_report_path,
                    )
                    package_validation = validate_skill(tool, package_skill)
                    package_behavior = run_behavior_tests(
                        tool,
                        package_skill,
                        behavior_cases,
                        predictor,
                        allow_predictor_fallback=not strict_backends,
                    )
                    package_score = score_reliability(
                        tool,
                        package_skill,
                        package_validation,
                        package_behavior,
                        repair_rounds=source_row["repair_report"].rounds,
                        deploy_threshold=deploy_threshold,
                        max_repair_rounds=max_repair_rounds,
                    )
                    row = {
                        "skill": package_skill,
                        "validation_report": package_validation,
                        "behavior_report": package_behavior,
                        "reliability_score": package_score,
                        "repair_report": source_row["repair_report"],
                    }
                else:
                    source_condition = condition
                    source_row = variants[source_condition]
                    gate_row = variants.get(GATED_SKILL, source_row)
                    row = source_row
                    package_skill = row["skill"]
                package_dir = root / tool_slug(tool.tool_name) / condition
                write_skill_package(
                    package_dir,
                    tool,
                    package_skill,
                    row["validation_report"],
                    behavior_report=row["behavior_report"],
                    reliability_score=row["reliability_score"],
                    repair_report=row["repair_report"],
                )
                if condition == RELIASKILL_CHALLENGER:
                    _write_challenger_method_metadata(
                        package_dir=package_dir,
                        tool_name=tool.tool_name,
                        selection_report_path=selection_report_path,
                        reliability_row=row,
                        source_row=source_row,
                        gate_row=gate_row,
                    )
                reliability_records.append(
                    {
                        "tool_name": tool.tool_name,
                        "baseline_name": condition,
                        "source_condition": source_condition,
                        "gate_decision": row["reliability_score"].decision,
                        "reliability_score": row["reliability_score"].score,
                    }
                )

    manifest = {
        "config_path": str(config_path),
        "shared_package_root": str(root),
        "tools_path": config["tools_path"],
        "num_tools": len(tools),
        "num_benchmark_tools": len(benchmark_tools),
        "num_live_tools": len(live_tools),
        "conditions": allowed_conditions,
        "packaged_records": len(package_records),
        "reliability_conditions": reliability_conditions,
        "reliability_records": len(reliability_records),
        "multi_candidate_base_enabled": multi_candidate_config is not None,
        "multi_candidate_base_records": len(multi_candidate_base_records),
        "package_summary": package_summary,
    }
    (root / "shared_package_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_jsonl(root / "reliability_package_records.jsonl", reliability_records)
    _write_jsonl(root / "multi_candidate_base_records.jsonl", multi_candidate_base_records)
    return manifest


def run_cluster_shard(
    config_path: str | Path,
    *,
    shard_index: int,
    num_shards: int,
    output_root: str | Path | None = None,
    shared_packages: str | Path | None = None,
    models: Sequence[str] | None = None,
    skip_routing: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    config = load_json_config(config_path)
    strict_backends = _strict_backends(config)
    root = Path(output_root or config.get("output_root") or "outputs/emnlp_acceptance")
    package_root = (
        Path(shared_packages)
        if shared_packages
        else shared_package_root(config, root if output_root is not None else None)
    )
    all_tools = load_tools(config["tools_path"])
    full_names = selected_tool_names(config, all_tools)
    shard_names = selected_tool_names(config, all_tools, shard_index=shard_index, num_shards=num_shards)
    tools = {name: all_tools[name] for name in full_names}
    shard_set = set(shard_names)
    full_tasks = _balanced_tasks_for_tools(config, load_benchmark_tasks(config["tasks_path"]), full_names)
    tasks = [task for task in full_tasks if task.tool_name in shard_set]
    live_tasks = _selected_live_tasks(config, shard_index=shard_index, num_shards=num_shards)
    model_configs = _load_config_models(config, base_dir=Path(config_path).resolve().parent)
    if models:
        requested = {str(item) for item in models}
        model_configs = [
            model for model in model_configs
            if model.model_name in requested or slugify(model.model_name) in requested or model.config_path in requested
        ]
    allowed_conditions = normalize_condition_names([str(item) for item in config.get("conditions") or []]) or []
    if dry_run:
        return {
            "dry_run": True,
            "config_path": str(config_path),
            "output_root": str(root),
            "shared_package_root": str(package_root),
            "shard_index": shard_index,
            "num_shards": num_shards,
            "num_full_tools": len(full_names),
            "num_shard_tools": len(shard_names),
            "num_tasks": len(tasks),
            "num_live_tasks": len(live_tasks),
            "models": [model.model_name for model in model_configs],
            "conditions": allowed_conditions,
        }

    manifests = []
    for model in model_configs:
        model_slug = slugify(model.model_name)
        model_root = root / "predictors" / model_slug / f"shard_{shard_index:02d}"
        predictor_config = _model_to_backend_config(model)
        generator = SkillGenerator(backend_config=config.get("generator"), allow_fallback=not strict_backends)
        predictor = build_predictor_from_config(predictor_config)
        try:
            benchmark_scores, benchmark_summary, benchmark_details = run_benchmark_pipeline(
                tools=tools,
                tasks_path=config["tasks_path"],
                output_dir=model_root / "benchmark",
                generator=generator,
                predictor=predictor,
                allowed_conditions=allowed_conditions,
                tasks=tasks,
                package_manager_dir=package_root,
                allow_package_generation=False,
                allow_predictor_fallback=not strict_backends,
                model_name=model.model_name,
                model_slug=model_slug,
                shard_index=shard_index,
                num_shards=num_shards,
            )
            routing_summary = {}
            routing_details = {}
            if not skip_routing:
                _, routing_summary, routing_details = run_routing_benchmark_pipeline(
                    tools=tools,
                    tasks_path=config["tasks_path"],
                    output_dir=model_root / "routing_benchmark",
                    generator=generator,
                    predictor=predictor,
                    allowed_conditions=allowed_conditions,
                    tasks=tasks,
                    package_manager_dir=package_root,
                    allow_package_generation=False,
                    allow_predictor_fallback=not strict_backends,
                    benchmark_dir=model_root / "benchmark",
                    model_name=model.model_name,
                    model_slug=model_slug,
                    shard_index=shard_index,
                    num_shards=num_shards,
                )
            live_exec_summary = {}
            live_exec_records = []
            if _live_execution_enabled(config):
                live_exec_records, live_exec_summary = _run_live_exec_for_model(
                    config,
                    model_root=model_root,
                    package_root=package_root,
                    generator=generator,
                    predictor=predictor,
                    allowed_conditions=allowed_conditions,
                    model_name=model.model_name,
                    model_slug=model_slug,
                    shard_index=shard_index,
                    num_shards=num_shards,
                    allow_predictor_fallback=not strict_backends,
                )
        finally:
            clear_model_cache()
        manifest = {
            "config_path": str(config_path),
            "output_root": str(model_root),
            "shared_package_root": str(package_root),
            "model_name": model.model_name,
            "model_slug": model_slug,
            "model_config": model.model_dump(),
            "predictor_config": predictor_config,
            "shard_index": shard_index,
            "num_shards": num_shards,
            "num_full_tools": len(full_names),
            "num_shard_tools": len(shard_names),
            "num_tasks": len(tasks),
            "conditions": allowed_conditions,
            "benchmark_summary": benchmark_summary,
            "benchmark_detail_summaries": benchmark_details,
            "routing_summary": routing_summary,
            "routing_detail_summaries": routing_details,
            "live_exec_summary": live_exec_summary,
            "num_benchmark_records": len(benchmark_scores),
            "num_live_exec_records": len(live_exec_records),
        }
        model_root.mkdir(parents=True, exist_ok=True)
        (model_root / "cluster_shard_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        manifests.append(manifest)
    return {"dry_run": False, "manifests": manifests}


def merge_cluster_shards(
    config_path: str | Path,
    *,
    output_root: str | Path | None = None,
    output_tables: str | Path | None = None,
    strict: bool = True,
) -> Dict[str, Any]:
    config = load_json_config(config_path)
    root = Path(output_root or config.get("output_root") or "outputs/emnlp_acceptance")
    merged_root = root / "merged"
    merged_root.mkdir(parents=True, exist_ok=True)
    model_roots = sorted((root / "predictors").glob("*"))
    all_prediction_records: List[Dict[str, Any]] = []
    all_routing_records: List[Dict[str, Any]] = []
    all_live_exec_records: List[Dict[str, Any]] = []
    model_rows: List[Dict[str, Any]] = []
    routing_model_rows: List[Dict[str, Any]] = []
    live_model_rows: List[Dict[str, Any]] = []
    duplicates: List[str] = []
    allowed_conditions = set(normalize_condition_names([str(item) for item in config.get("conditions") or []]))
    ignored_prediction_records = 0
    ignored_routing_records = 0
    ignored_live_exec_records = 0

    for model_root in model_roots:
        if not model_root.is_dir():
            continue
        model_merged = model_root / "merged"
        model_merged.mkdir(parents=True, exist_ok=True)
        raw_prediction_records = _load_shard_jsonl(model_root, "prediction_records.jsonl")
        raw_routing_records = _load_shard_jsonl(model_root, "routing_records.jsonl")
        raw_live_exec_records = _load_shard_jsonl(model_root, "live_exec_results.jsonl")
        prediction_records = _filter_records_for_conditions(raw_prediction_records, allowed_conditions)
        routing_records = _filter_records_for_conditions(raw_routing_records, allowed_conditions)
        live_exec_records = _filter_records_for_conditions(raw_live_exec_records, allowed_conditions)
        ignored_prediction_records += len(raw_prediction_records) - len(prediction_records)
        ignored_routing_records += len(raw_routing_records) - len(routing_records)
        ignored_live_exec_records += len(raw_live_exec_records) - len(live_exec_records)
        duplicates.extend(_duplicate_keys(prediction_records, record_type="prediction"))
        duplicates.extend(_duplicate_keys(routing_records, record_type="routing"))
        duplicates.extend(_duplicate_live_keys(live_exec_records))
        _write_jsonl(model_merged / "prediction_records.jsonl", prediction_records)
        _write_jsonl(model_merged / "routing_records.jsonl", routing_records)
        _write_jsonl(model_merged / "live_exec_results.jsonl", live_exec_records)
        model_tables = build_metric_tables(model_merged)
        _write_tables(model_merged / "tables", model_tables)
        model_name = _model_name_for_records(prediction_records, fallback=model_root.name)
        for row in model_tables["main_results"]:
            model_rows.append({"model_slug": model_root.name, "model_name": model_name, **row})
        for row in model_tables["routing_results"]:
            routing_model_rows.append({"model_slug": model_root.name, "model_name": model_name, **row})
        for row in _summarize_live_exec_records(live_exec_records):
            live_model_rows.append({"model_slug": model_root.name, "model_name": model_name, **row})
        all_prediction_records.extend(prediction_records)
        all_routing_records.extend(routing_records)
        all_live_exec_records.extend(live_exec_records)

    if duplicates and strict:
        preview = "; ".join(duplicates[:10])
        raise ValueError(f"Duplicate shard records found: {preview}")
    _write_jsonl(merged_root / "prediction_records.jsonl", all_prediction_records)
    _write_jsonl(merged_root / "routing_records.jsonl", all_routing_records)
    _write_jsonl(merged_root / "live_exec_results.jsonl", all_live_exec_records)
    tables_dir = Path(output_tables) if output_tables else root / "tables"
    paths = write_metric_tables(merged_root, tables_dir)
    model_fields = ["model_slug", "model_name"]
    if model_rows:
        model_fields.extend([field for field in model_rows[0] if field not in set(model_fields)])
    _write_csv(tables_dir / "main_results_by_model.csv", model_rows, model_fields)
    routing_model_fields = ["model_slug", "model_name"]
    if routing_model_rows:
        routing_model_fields.extend([field for field in routing_model_rows[0] if field not in set(routing_model_fields)])
    _write_csv(tables_dir / "routing_results_by_model.csv", routing_model_rows, routing_model_fields)
    live_fields = _fields_for_rows(all_live_exec_records, preferred=["model_slug", "model_name", "baseline_name", "live_task_id", "tool_id"])
    _write_csv(tables_dir / "live_exec_results.csv", all_live_exec_records, live_fields or ["live_task_id"])
    live_model_fields = ["model_slug", "model_name"]
    if live_model_rows:
        live_model_fields.extend([field for field in live_model_rows[0] if field not in set(live_model_fields)])
    _write_csv(tables_dir / "live_exec_results_by_model.csv", live_model_rows, live_model_fields)
    paths.update(
        {
            "main_results_by_model": tables_dir / "main_results_by_model.csv",
            "routing_results_by_model": tables_dir / "routing_results_by_model.csv",
            "live_exec_results": tables_dir / "live_exec_results.csv",
            "live_exec_results_by_model": tables_dir / "live_exec_results_by_model.csv",
        }
    )
    manifest = {
        "config_path": str(config_path),
        "output_root": str(root),
        "merged_root": str(merged_root),
        "tables_dir": str(tables_dir),
        "num_models": len(model_roots),
        "prediction_records": len(all_prediction_records),
        "routing_records": len(all_routing_records),
        "live_exec_records": len(all_live_exec_records),
        "ignored_prediction_records": ignored_prediction_records,
        "ignored_routing_records": ignored_routing_records,
        "ignored_live_exec_records": ignored_live_exec_records,
        "duplicates": duplicates,
        "table_paths": {name: str(path) for name, path in paths.items()},
    }
    (merged_root / "cluster_merge_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def _configured_max_tools(config: Dict[str, Any]) -> int | None:
    data_config = config.get("data") if isinstance(config.get("data"), dict) else {}
    for value in (data_config.get("max_tools"), config.get("max_tools")):
        if value not in {None, ""}:
            parsed = int(value)
            if parsed > 0:
                return parsed
    return None


def _strict_backends(config: Dict[str, Any]) -> bool:
    runtime = config.get("runtime") if isinstance(config.get("runtime"), dict) else {}
    return bool(runtime.get("strict_backends", False))


def _live_execution_enabled(config: Dict[str, Any]) -> bool:
    live = config.get("live_execution") if isinstance(config.get("live_execution"), dict) else {}
    return bool(live.get("enabled", False))


def _configured_live_tools(config: Dict[str, Any]) -> Dict[str, Any]:
    if not _live_execution_enabled(config):
        return {}
    live = config.get("live_execution") if isinstance(config.get("live_execution"), dict) else {}
    allowed_domains = {_normalize_live_domain(item) for item in (live.get("domains") or [])}
    tools = build_live_exec_tools()
    if not allowed_domains:
        return tools
    return {
        name: tool
        for name, tool in tools.items()
        if _normalize_live_domain((tool.provenance or {}).get("domain") or (tool.schema_complexity or {}).get("domain")) in allowed_domains
    }


def _selected_live_tasks(
    config: Dict[str, Any],
    *,
    shard_index: int | None = None,
    num_shards: int | None = None,
) -> List[Dict[str, Any]]:
    if not _live_execution_enabled(config):
        return []
    live = config.get("live_execution") if isinstance(config.get("live_execution"), dict) else {}
    allowed_domains = {_normalize_live_domain(item) for item in (live.get("domains") or [])}
    tasks = [
        task for task in build_live_exec_tasks()
        if not allowed_domains or _normalize_live_domain(task.get("domain")) in allowed_domains
    ]
    subset_size = _optional_positive_int(live.get("subset_size"))
    tasks = sorted(tasks, key=lambda item: str(item.get("live_task_id") or ""))
    tasks = tasks[:subset_size] if subset_size is not None else tasks
    if shard_index is None and num_shards is None:
        return tasks
    if shard_index is None or num_shards is None:
        raise ValueError("shard_index and num_shards must be provided together for live execution sharding.")
    if num_shards <= 0:
        raise ValueError("num_shards must be positive.")
    if shard_index < 0 or shard_index >= num_shards:
        raise ValueError("shard_index must be in [0, num_shards).")
    return [task for index, task in enumerate(tasks) if index % num_shards == shard_index]


def _run_live_exec_for_model(
    config: Dict[str, Any],
    *,
    model_root: Path,
    package_root: Path,
    generator: SkillGenerator,
    predictor: Any,
    allowed_conditions: Sequence[str],
    model_name: str,
    model_slug: str,
    shard_index: int,
    num_shards: int,
    allow_predictor_fallback: bool,
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    live_tools = _configured_live_tools(config)
    live_tasks = _selected_live_tasks(config, shard_index=shard_index, num_shards=num_shards)
    if not live_tools or not live_tasks:
        return [], {"num_tasks": 0, "num_records": 0}

    skill_variants_by_tool = {
        tool_name: build_skill_variant_map(
            tool,
            live_tools,
            generator,
            allowed_conditions=list(allowed_conditions),
            package_manager_dir=package_root,
            allow_package_generation=False,
        )
        for tool_name, tool in live_tools.items()
    }
    results: List[Dict[str, Any]] = []
    predictions: List[Dict[str, Any]] = []
    live_dir = model_root / "live_exec"
    for task in live_tasks:
        tool_id = str(task.get("tool_id") or "")
        tool = live_tools.get(tool_id)
        if tool is None:
            continue
        expected_call = task.get("expected_tool_call") if isinstance(task.get("expected_tool_call"), dict) else {}
        expected_args = expected_call.get("arguments") if isinstance(expected_call.get("arguments"), dict) else {}
        eval_task = EvalTask(
            task_id=str(task["live_task_id"]),
            tool_name=tool_id,
            user_request=str(task.get("user_request") or ""),
            expected_arguments=dict(expected_args),
            expected_argument_candidates=[dict(expected_args)],
            should_trigger=True,
            split="live_exec",
            tags=["live_exec", str(task.get("domain") or "")],
            domain=str(task.get("domain") or ""),
            difficulty=str(task.get("difficulty") or ""),
        )
        for condition, skill in skill_variants_by_tool[tool_id].items():
            task_dir = live_dir / tool_slug(str(task["live_task_id"]))
            result_path = task_dir / f"{tool_slug(condition)}.live_result.json"
            prediction_path = task_dir / f"{tool_slug(condition)}.live_prediction.json"
            if result_path.exists():
                try:
                    result = json.loads(result_path.read_text(encoding="utf-8"))
                    results.append(result)
                    if prediction_path.exists():
                        predictions.append(json.loads(prediction_path.read_text(encoding="utf-8")))
                    continue
                except (OSError, json.JSONDecodeError):
                    pass
            prediction = safe_predict(tool, skill, eval_task, predictor, allow_fallback=allow_predictor_fallback)
            predicted_call = {
                "tool_name": tool_id if prediction.should_call else "__abstain__",
                "arguments": dict(prediction.predicted_arguments),
            }
            prediction_row = {
                "live_task_id": task["live_task_id"],
                "task_id": task["live_task_id"],
                "domain": task.get("domain"),
                "tool_id": tool_id,
                "baseline_name": condition,
                "model_name": model_name,
                "model_slug": model_slug,
                "shard_index": shard_index,
                "num_shards": num_shards,
                "should_call": prediction.should_call,
                "abstention_reason": prediction.abstention_reason,
                "predicted_tool_call": predicted_call,
                "predictor_configured_backend": prediction.metadata.get("configured_predictor_backend", predictor.backend_name),
                "predictor_backend": prediction.metadata.get("actual_predictor_backend", predictor.backend_name),
                "predictor_fallback_used": bool(prediction.metadata.get("predictor_fallback_used", False)),
                "predictor_fallback_reason": prediction.metadata.get("predictor_fallback_reason"),
            }
            predictions.append(prediction_row)
            result = evaluate_live_exec_tasks([task], {str(task["live_task_id"]): predicted_call}, use_gold=False)[0]
            result.update(
                {
                    "task_id": task["live_task_id"],
                    "baseline_name": condition,
                    "model_name": model_name,
                    "model_slug": model_slug,
                    "shard_index": shard_index,
                    "num_shards": num_shards,
                    "should_call": prediction.should_call,
                    "abstention_reason": prediction.abstention_reason,
                    "predictor_configured_backend": prediction_row["predictor_configured_backend"],
                    "predictor_backend": prediction_row["predictor_backend"],
                    "predictor_fallback_used": prediction_row["predictor_fallback_used"],
                    "predictor_fallback_reason": prediction_row["predictor_fallback_reason"],
                }
            )
            results.append(result)
            task_dir.mkdir(parents=True, exist_ok=True)
            prediction_path.write_text(json.dumps(prediction_row, indent=2, ensure_ascii=False), encoding="utf-8")
            result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    _write_jsonl(live_dir / "live_exec_predictions.jsonl", predictions)
    _write_jsonl(live_dir / "live_exec_results.jsonl", results)
    _write_csv(live_dir / "live_exec_results.csv", results, _fields_for_rows(results, preferred=["baseline_name", "live_task_id", "tool_id"]))
    return results, {
        "num_tasks": len(live_tasks),
        "num_records": len(results),
        "by_condition": _summarize_live_exec_records(results),
    }


def _normalize_live_domain(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"database/sql", "database", "sql", "sqlite"}:
        return "sqlite"
    if text in {"git/version-control", "version-control", "version_control", "git"}:
        return "git"
    return text


def _balanced_tasks_for_tools(config: Dict[str, Any], tasks: Sequence[Any], tool_names: Sequence[str]) -> List[Any]:
    tool_set = set(tool_names)
    controls = config.get("controls") if isinstance(config.get("controls"), dict) else {}
    pos_limit = _optional_positive_int(controls.get("positives_per_tool_total") or config.get("positives_per_tool"))
    neg_limit = _optional_positive_int(controls.get("negatives_per_tool_total") or config.get("negatives_per_tool"))
    filtered = [task for task in tasks if task.tool_name in tool_set]
    if pos_limit is None and neg_limit is None:
        return filtered
    grouped: Dict[str, Dict[str, List[Any]]] = {}
    for task in sorted(filtered, key=lambda item: str(item.task_id)):
        bucket = "positive" if getattr(task, "should_trigger", True) else "negative"
        grouped.setdefault(task.tool_name, {"positive": [], "negative": []})[bucket].append(task)
    selected: List[Any] = []
    for tool_name in sorted(tool_set):
        buckets = grouped.get(tool_name, {"positive": [], "negative": []})
        positives = buckets["positive"][:pos_limit] if pos_limit is not None else buckets["positive"]
        negatives = buckets["negative"][:neg_limit] if neg_limit is not None else buckets["negative"]
        selected.extend(positives)
        selected.extend(negatives)
    return sorted(selected, key=lambda item: str(item.task_id))


def _optional_positive_int(value: Any) -> int | None:
    if value in {None, ""}:
        return None
    parsed = int(value)
    return parsed if parsed > 0 else None


def _load_config_models(config: Dict[str, Any], *, base_dir: Path) -> List[Any]:
    raw_models = config.get("models") or []
    if not raw_models:
        return [load_model_config(config.get("predictor") or config.get("generator") or {"type": "heuristic", "model_name": "heuristic"})]
    models = []
    for raw in raw_models:
        if isinstance(raw, str):
            path = _resolve_config_path(raw, base_dir)
            models.append(load_model_config(path))
        elif isinstance(raw, dict) and raw.get("config"):
            path = _resolve_config_path(str(raw["config"]), base_dir)
            model = load_model_config(path)
            overrides = dict(raw)
            overrides.pop("config", None)
            if overrides:
                model_data = model.model_dump()
                model_data.update(overrides)
                models.append(load_model_config(model_data))
            else:
                models.append(model)
        elif isinstance(raw, dict):
            models.append(load_model_config(raw))
        else:
            raise ValueError(f"Unsupported model entry: {raw!r}")
    return models


def _resolve_config_path(value: str, base_dir: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    for candidate in (base_dir / path, Path.cwd() / path):
        if candidate.exists():
            return candidate
    return Path.cwd() / path


def _model_to_backend_config(model: Any) -> Dict[str, Any]:
    return {
        "type": model.backend,
        "model_name_or_path": model.model_path,
        "device_map": model.device_map,
        "torch_dtype": model.torch_dtype,
        "max_new_tokens": model.max_new_tokens,
        "load_in_4bit": model.load_in_4bit,
        "load_in_8bit": False,
        "generation_kwargs": {"temperature": model.temperature},
    }


def _load_shard_jsonl(model_root: Path, filename: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for shard_root in sorted(path for path in model_root.glob("shard_*") if path.is_dir()):
        shard_rows: List[Dict[str, Any]] = []
        shard_keys: set[tuple[str, str, str, str]] = set()
        for path in sorted(shard_root.glob(f"**/{filename}")):
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    _annotate_recovered_record(row, model_root=model_root)
                    shard_rows.append(row)
                    shard_keys.add(_merge_record_key(row, filename))

        for path in _fallback_record_paths(shard_root, filename):
            try:
                row = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            _annotate_recovered_record(row, model_root=model_root)
            key = _merge_record_key(row, filename)
            if key in shard_keys:
                continue
            shard_rows.append(row)
            shard_keys.add(key)
        rows.extend(shard_rows)
    return rows


def _filter_records_for_conditions(records: Sequence[Dict[str, Any]], allowed_conditions: set[str]) -> List[Dict[str, Any]]:
    if not allowed_conditions:
        return list(records)
    return [record for record in records if str(record.get("baseline_name") or record.get("condition") or "") in allowed_conditions]


def _fallback_record_paths(shard_root: Path, filename: str) -> List[Path]:
    if filename == "prediction_records.jsonl":
        return sorted(shard_root.glob("benchmark/**/*.result.json"))
    if filename == "routing_records.jsonl":
        return sorted(shard_root.glob("routing_benchmark/**/*.routing.json"))
    if filename == "live_exec_results.jsonl":
        return sorted(shard_root.glob("live_exec/**/*.live_result.json"))
    return []


def _annotate_recovered_record(record: Dict[str, Any], *, model_root: Path) -> None:
    record.setdefault("model_slug", model_root.name)
    record.setdefault("model_name", record.get("model_slug") or model_root.name)


def _merge_record_key(record: Dict[str, Any], filename: str) -> tuple[str, str, str, str]:
    if filename == "live_exec_results.jsonl":
        record_type = "live_exec"
        task_id = str(record.get("live_task_id") or record.get("task_id") or "")
    elif filename == "routing_records.jsonl":
        record_type = "routing"
        task_id = str(record.get("task_id") or "")
    else:
        record_type = "prediction"
        task_id = str(record.get("task_id") or "")
    return (
        str(record.get("model_slug") or record.get("model_name") or ""),
        task_id,
        str(record.get("baseline_name") or ""),
        record_type,
    )


def _duplicate_keys(records: Sequence[Dict[str, Any]], *, record_type: str) -> List[str]:
    seen: set[tuple[str, str, str, str]] = set()
    duplicates = []
    for record in records:
        key = (
            str(record.get("model_slug") or record.get("model_name") or ""),
            str(record.get("task_id") or ""),
            str(record.get("baseline_name") or ""),
            record_type,
        )
        if key in seen:
            duplicates.append("/".join(key))
        seen.add(key)
    return duplicates


def _duplicate_live_keys(records: Sequence[Dict[str, Any]]) -> List[str]:
    seen: set[tuple[str, str, str]] = set()
    duplicates = []
    for record in records:
        key = (
            str(record.get("model_slug") or record.get("model_name") or ""),
            str(record.get("live_task_id") or record.get("task_id") or ""),
            str(record.get("baseline_name") or ""),
        )
        if key in seen:
            duplicates.append("/".join(key))
        seen.add(key)
    return duplicates


def _model_name_for_records(records: Sequence[Dict[str, Any]], *, fallback: str) -> str:
    for record in records:
        if record.get("model_name"):
            return str(record["model_name"])
    return fallback


def _write_tables(output_dir: Path, tables: Dict[str, List[Dict[str, Any]]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "main_results.csv", tables["main_results"], list(tables["main_results"][0]) if tables["main_results"] else ["baseline_name"])
    _write_csv(output_dir / "routing_results.csv", tables["routing_results"], list(tables["routing_results"][0]) if tables["routing_results"] else ["baseline_name"])
    _write_csv(output_dir / "harm_utility.csv", tables["harm_utility"], list(tables["harm_utility"][0]) if tables["harm_utility"] else ["baseline_name"])
    _write_csv(output_dir / "stat_tests.csv", tables["stat_tests"], list(tables["stat_tests"][0]) if tables["stat_tests"] else ["test"])
    _write_csv(output_dir / "routing_stat_tests.csv", tables["routing_stat_tests"], list(tables["routing_stat_tests"][0]) if tables["routing_stat_tests"] else ["test"])


def _write_csv(path: Path, rows: Sequence[Dict[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _fields_for_rows(rows: Sequence[Dict[str, Any]], preferred: Sequence[str] | None = None) -> List[str]:
    preferred = list(preferred or [])
    fields: List[str] = []
    for field in preferred:
        if field not in fields:
            fields.append(field)
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    return fields


def _summarize_live_exec_records(records: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault(str(record.get("baseline_name") or ""), []).append(record)
    rows = []
    for condition, items in sorted(grouped.items()):
        total = len(items)
        rows.append(
            {
                "baseline_name": condition,
                "num_examples": total,
                "predicted_call_valid": _rate(items, "predicted_call_valid"),
                "execution_success": _rate(items, "execution_success"),
                "observation_match": _rate(items, "observation_match"),
                "state_match": _rate(items, "state_match"),
                "unsafe_action_blocked": _rate(items, "unsafe_action_blocked"),
                "live_joint_success": _rate(items, "live_joint_success"),
            }
        )
    return rows


def _rate(rows: Sequence[Dict[str, Any]], key: str) -> float:
    return round(sum(1 for row in rows if _truthy(row.get(key))) / len(rows), 4) if rows else 0.0


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.lower() in {"true", "1", "yes"}
    return bool(value)


def _write_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def parse_model_filter(value: str | None) -> List[str] | None:
    if not value or value == "all":
        return None
    return [item.strip() for item in value.split(",") if item.strip()]

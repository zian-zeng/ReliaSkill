from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from autoskill.artifacts import (
    DOCS_ONLY,
    GATED_SKILL,
    NAIVE_SKILL,
    RAW_MCP,
    REPAIRED_SKILL,
    SCHEMA_ONLY,
    VALIDATED_SKILL,
    apply_skill_ablation,
    build_docs_only_skill,
    clone_skill_as,
)
from autoskill.behavior import load_behavior_cases, run_behavior_tests
from autoskill.evaluation import write_summary
from autoskill.experiment import load_tools
from autoskill.generator import SkillGenerator
from autoskill.ir import BehaviorCase, BehaviorReport, GeneratedSkill, ReliabilityScore, RepairReport, ToolIR, ValidationReport
from autoskill.packaging import write_skill_package
from autoskill.predictor import PredictorBackend, build_predictor_from_config
from autoskill.quality import score_reliability
from autoskill.raw_mcp import build_raw_mcp_skill
from autoskill.repair import repair_behavior_failures, repair_skill
from autoskill.schema_only import build_schema_only_skill
from autoskill.validator import validate_skill


def _empty_repair_report() -> RepairReport:
    return RepairReport(attempted=False, changed=False, rounds=0, actions=[], remaining_issues=[])


def _build_gated_skill(skill: GeneratedSkill, score: ReliabilityScore) -> GeneratedSkill:
    gated = clone_skill_as(skill, GATED_SKILL)
    gated.metadata = {**gated.metadata, "gate_decision": score.decision, "gate_score": score.score}
    if score.decision == "deploy":
        return gated
    gated.skill_summary = f"Deployment gate decision: {score.decision}. This skill should not be exposed to downstream agents."
    gated.when_to_use = []
    gated.when_not_to_use = [
        "Do not deploy this generated skill artifact until validation, behavior, or reliability failures are resolved.",
        *score.rationale,
    ]
    gated.argument_template = {}
    gated.examples = []
    gated.semantic_hints = {}
    return gated


def build_reliability_variants(
    tool: ToolIR,
    generator: SkillGenerator,
    behavior_cases: Iterable[BehaviorCase],
    predictor: PredictorBackend,
    max_repair_rounds: int = 2,
    deploy_threshold: float = 70.0,
    ablation_mode: str | None = None,
) -> Dict[str, Dict[str, Any]]:
    variants: Dict[str, Dict[str, Any]] = {}

    base_generated = apply_skill_ablation(generator.generate(tool), ablation_mode)
    raw = build_raw_mcp_skill(tool)
    schema = build_schema_only_skill(tool)
    docs = build_docs_only_skill(tool)
    naive = clone_skill_as(base_generated, NAIVE_SKILL)
    validated = clone_skill_as(base_generated, VALIDATED_SKILL)

    initial_items = {
        RAW_MCP: raw,
        SCHEMA_ONLY: schema,
        DOCS_ONLY: docs,
        NAIVE_SKILL: naive,
        VALIDATED_SKILL: validated,
    }

    for condition, skill in initial_items.items():
        validation_report = validate_skill(tool, skill)
        behavior_report = run_behavior_tests(tool, skill, behavior_cases, predictor)
        reliability_score = score_reliability(
            tool,
            skill,
            validation_report,
            behavior_report,
            repair_rounds=0,
            deploy_threshold=deploy_threshold,
            max_repair_rounds=max_repair_rounds,
        )
        variants[condition] = {
            "skill": skill,
            "validation_report": validation_report,
            "behavior_report": behavior_report,
            "reliability_score": reliability_score,
            "repair_report": _empty_repair_report(),
        }

    repaired_skill, repair_report, repaired_validation = repair_skill(tool, clone_skill_as(validated, REPAIRED_SKILL), max_rounds=max_repair_rounds)
    repaired_behavior = run_behavior_tests(tool, repaired_skill, behavior_cases, predictor)
    if not repaired_behavior.valid and repair_report.rounds < max_repair_rounds:
        behavior_repaired_skill, behavior_repair_report, behavior_validation = repair_behavior_failures(
            tool,
            repaired_skill,
            repaired_behavior,
        )
        if behavior_repair_report.changed:
            repaired_skill = behavior_repaired_skill
            repaired_validation = behavior_validation
            repaired_behavior = run_behavior_tests(tool, repaired_skill, behavior_cases, predictor)
            repair_report = RepairReport(
                attempted=True,
                changed=True,
                rounds=repair_report.rounds + behavior_repair_report.rounds,
                actions=[*repair_report.actions, *behavior_repair_report.actions],
                remaining_issues=repaired_validation.issues,
            )
    repaired_score = score_reliability(
        tool,
        repaired_skill,
        repaired_validation,
        repaired_behavior,
        repair_rounds=repair_report.rounds,
        deploy_threshold=deploy_threshold,
        max_repair_rounds=max_repair_rounds,
    )
    variants[REPAIRED_SKILL] = {
        "skill": repaired_skill,
        "validation_report": repaired_validation,
        "behavior_report": repaired_behavior,
        "reliability_score": repaired_score,
        "repair_report": repair_report,
    }

    gated_skill = _build_gated_skill(repaired_skill, repaired_score)
    gated_validation = validate_skill(tool, gated_skill)
    gated_behavior = run_behavior_tests(tool, gated_skill, behavior_cases, predictor)
    gated_score = score_reliability(
        tool,
        gated_skill,
        gated_validation,
        gated_behavior,
        repair_rounds=repair_report.rounds,
        deploy_threshold=deploy_threshold,
        max_repair_rounds=max_repair_rounds,
    )
    gated_score.decision = repaired_score.decision
    gated_score.rationale = repaired_score.rationale
    variants[GATED_SKILL] = {
        "skill": gated_skill,
        "validation_report": gated_validation,
        "behavior_report": gated_behavior,
        "reliability_score": gated_score,
        "repair_report": repair_report,
    }
    return variants


def summarize_reliability_records(records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault(record["condition"], []).append(record)
    summary: Dict[str, Any] = {}
    for condition, items in grouped.items():
        total = len(items)
        deploy_count = sum(1 for item in items if item["reliability_score"].decision == "deploy")
        repair_count = sum(1 for item in items if item["reliability_score"].decision == "repair")
        reject_count = sum(1 for item in items if item["reliability_score"].decision == "reject")
        repair_attempt_count = sum(1 for item in items if item["repair_report"].attempted)
        total_repair_rounds = sum(item["repair_report"].rounds for item in items)
        summary[condition] = {
            "total_tools": total,
            "avg_score": round(sum(item["reliability_score"].score for item in items) / total, 4) if total else 0.0,
            "deploy_count": deploy_count,
            "repair_count": repair_count,
            "reject_count": reject_count,
            "deploy_rate": round(deploy_count / total, 4) if total else 0.0,
            "repair_attempt_rate": round(repair_attempt_count / total, 4) if total else 0.0,
            "avg_repair_rounds": round(total_repair_rounds / total, 4) if total else 0.0,
            "avg_trigger_precision": round(sum(item["behavior_report"].metrics.get("trigger_precision", 0.0) for item in items) / total, 4) if total else 0.0,
            "avg_trigger_recall": round(sum(item["behavior_report"].metrics.get("trigger_recall", 0.0) for item in items) / total, 4) if total else 0.0,
            "avg_harmful_skill_injection_rate": round(sum(item["behavior_report"].metrics.get("harmful_skill_injection_rate", 0.0) for item in items) / total, 4) if total else 0.0,
            "avg_prediction_latency_ms": round(sum(item["behavior_report"].metrics.get("avg_prediction_latency_ms", 0.0) for item in items) / total, 4) if total else 0.0,
            "avg_token_overhead_estimate": round(sum(item["reliability_score"].features.get("token_overhead_estimate", 0.0) for item in items) / total, 4) if total else 0.0,
        }
    return summary


def build_reliability_report_markdown(summary: Dict[str, Any], manifest: Dict[str, Any]) -> str:
    lines = [
        "# AutoSkill Reliability Report",
        "",
        f"- Tools source: `{manifest['tools_path']}`",
        f"- Behavior source: `{manifest['behavior_path']}`",
        f"- Generator backend: `{manifest['generator_backend']}`",
        f"- Predictor backend: `{manifest['predictor_backend']}`",
        f"- Deploy threshold: `{manifest['deploy_threshold']}`",
        "",
        "| Condition | Avg Score | Deploy Rate | Harm Rate | Trigger Precision | Trigger Recall | Repair Rounds | Token Overhead | Latency ms |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for condition, row in summary.items():
        lines.append(
            f"| {condition} | {row.get('avg_score', 0.0):.4f} | {row.get('deploy_rate', 0.0):.4f} | "
            f"{row.get('avg_harmful_skill_injection_rate', 0.0):.4f} | {row.get('avg_trigger_precision', 0.0):.4f} | "
            f"{row.get('avg_trigger_recall', 0.0):.4f} | {row.get('avg_repair_rounds', 0.0):.2f} | "
            f"{row.get('avg_token_overhead_estimate', 0.0):.2f} | {row.get('avg_prediction_latency_ms', 0.0):.4f} |"
        )
    return "\n".join(lines) + "\n"


def build_reliability_summary_csv(summary: Dict[str, Any]) -> str:
    headers = [
        "condition",
        "avg_score",
        "deploy_rate",
        "repair_attempt_rate",
        "avg_repair_rounds",
        "avg_trigger_precision",
        "avg_trigger_recall",
        "avg_harmful_skill_injection_rate",
        "avg_token_overhead_estimate",
        "avg_prediction_latency_ms",
    ]
    lines = [",".join(headers)]
    for condition, row in summary.items():
        lines.append(",".join([condition, *[str(row.get(header, "")) for header in headers[1:]]]))
    return "\n".join(lines) + "\n"


def run_reliability_pipeline(
    tools_path: str | Path,
    behavior_path: str | Path,
    output_root: str | Path,
    generator_config: Dict[str, Any] | None = None,
    predictor_config: Dict[str, Any] | None = None,
    max_repair_rounds: int = 2,
    deploy_threshold: float = 70.0,
    ablation_mode: str | None = None,
) -> Dict[str, Any]:
    tools = load_tools(tools_path)
    behavior_cases = load_behavior_cases(behavior_path)
    output_root = Path(output_root)
    generator = SkillGenerator(backend_config=generator_config)
    predictor = build_predictor_from_config(predictor_config)
    records: List[Dict[str, Any]] = []

    for tool in tools.values():
        variants = build_reliability_variants(
            tool,
            generator=generator,
            behavior_cases=behavior_cases,
            predictor=predictor,
            max_repair_rounds=max_repair_rounds,
            deploy_threshold=deploy_threshold,
            ablation_mode=ablation_mode,
        )
        for condition, row in variants.items():
            package_dir = output_root / "packages" / tool.tool_name / condition
            write_skill_package(
                package_dir,
                tool,
                row["skill"],
                row["validation_report"],
                behavior_report=row["behavior_report"],
                reliability_score=row["reliability_score"],
                repair_report=row["repair_report"],
            )
            records.append({"tool_name": tool.tool_name, "condition": condition, **row})

    summary = summarize_reliability_records(records)
    manifest = {
        "tools_path": str(tools_path),
        "behavior_path": str(behavior_path),
        "output_root": str(output_root),
        "generator_backend": getattr(generator.backend, "backend_name", "unknown"),
        "predictor_backend": predictor.backend_name,
        "max_repair_rounds": max_repair_rounds,
        "deploy_threshold": deploy_threshold,
        "ablation_mode": ablation_mode,
        "summary": summary,
    }
    write_summary(output_root / "reliability_summary.json", summary)
    write_summary(output_root / "reliability_manifest.json", manifest)
    reports_dir = output_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "reliability_report.md").write_text(build_reliability_report_markdown(summary, manifest), encoding="utf-8")
    (reports_dir / "reliability_summary.csv").write_text(build_reliability_summary_csv(summary), encoding="utf-8")
    with (output_root / "reliability_records.jsonl").open("w", encoding="utf-8") as f:
        for record in records:
            f.write(
                json.dumps(
                    {
                        "tool_name": record["tool_name"],
                        "condition": record["condition"],
                        "validation_report": record["validation_report"].model_dump(),
                        "behavior_report": record["behavior_report"].model_dump(),
                        "reliability_score": record["reliability_score"].model_dump(),
                        "repair_report": record["repair_report"].model_dump(),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    return manifest


def run_reliability_pipeline_from_config(config_path: str | Path) -> Dict[str, Any]:
    with Path(config_path).open("r", encoding="utf-8") as f:
        config = json.load(f)
    reliability_config = config.get("reliability", {})
    return run_reliability_pipeline(
        tools_path=config["tools_path"],
        behavior_path=config.get("behavior_path") or config.get("tasks_path"),
        output_root=config["output_root"],
        generator_config=config.get("generator"),
        predictor_config=config.get("predictor"),
        max_repair_rounds=int(reliability_config.get("max_repair_rounds", 2)),
        deploy_threshold=float(reliability_config.get("deploy_threshold", 70.0)),
        ablation_mode=reliability_config.get("ablation_mode"),
    )

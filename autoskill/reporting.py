from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Iterable, List


BASELINE_ORDER = [
    "raw_mcp",
    "schema_only",
    "docs_only",
    "retrieved_docs",
    "retrieved_candidates",
    "retrieved_memory",
    "naive_skill",
    "validated_skill",
    "repaired_skill",
    "gated_skill",
    "generated_skill_base",
]


def _ordered_baselines(summary: Dict[str, Any]) -> list[str]:
    known = [name for name in BASELINE_ORDER if name in summary]
    extras = sorted(name for name in summary if name not in BASELINE_ORDER)
    return known + extras


def _ordered_tools(summary_by_tool: Dict[str, Any]) -> list[str]:
    return sorted(summary_by_tool)


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _format_optional_float(value: Any, digits: int = 4) -> str:
    if value is None:
        return ""
    return f"{float(value):.{digits}f}"


def collect_failure_highlights(scores: Iterable[Dict[str, Any]], limit_per_baseline: int = 3) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for score in scores:
        if score.get("exact_match"):
            continue
        grouped.setdefault(str(score["baseline_name"]), []).append(score)

    highlights: Dict[str, List[Dict[str, Any]]] = {}
    for baseline_name, items in grouped.items():
        ranked = sorted(
            items,
            key=lambda item: (
                item.get("argument_validity", 0.0),
                item.get("required_argument_recall", 0.0),
                -len(item.get("hallucinated_args", [])),
            ),
        )
        highlights[baseline_name] = ranked[:limit_per_baseline]
    return highlights


def build_results_markdown(
    package_summary: Dict[str, Any],
    benchmark_summary: Dict[str, Any],
    tools_path: str,
    tasks_path: str,
    routing_summary: Dict[str, Any] | None = None,
    package_summary_by_tool: Dict[str, Dict[str, Any]] | None = None,
    benchmark_summary_by_tool: Dict[str, Dict[str, Any]] | None = None,
    benchmark_summary_by_split: Dict[str, Dict[str, Any]] | None = None,
    routing_summary_by_tool: Dict[str, Dict[str, Any]] | None = None,
    routing_summary_by_split: Dict[str, Dict[str, Any]] | None = None,
    pairwise_comparisons: Dict[str, Any] | None = None,
    error_taxonomy: Dict[str, Any] | None = None,
    method_win_analysis: Dict[str, Any] | None = None,
    benchmark_failures: Dict[str, List[Dict[str, Any]]] | None = None,
) -> str:
    lines = [
        "# AutoSkill Experiment Report",
        "",
        f"- Tools source: `{tools_path}`",
        f"- Benchmark source: `{tasks_path}`",
        "",
        "## Packaging Summary",
        "",
        "| Condition | Valid Rate | Avg Examples | Avg Template Fields | Avg Semantic Hints |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for baseline in _ordered_baselines(package_summary):
        row = package_summary[baseline]
        lines.append(
            f"| {baseline} | {row.get('valid_rate', 0.0):.4f} | {row.get('avg_examples', 0.0):.2f} | {row.get('avg_template_fields', 0.0):.2f} | {row.get('avg_semantic_hint_entries', 0.0):.2f} |"
        )

    lines.extend(
        [
            "",
            "## Benchmark Summary",
            "",
            "| Condition | Exact Match | Argument Validity | Required Arg Recall | Retrieval Hit@K | Avg Target Rank | Hallucinated Args |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for baseline in _ordered_baselines(benchmark_summary):
        row = benchmark_summary[baseline]
        lines.append(
            f"| {baseline} | {row.get('exact_match_rate', 0.0):.4f} | {row.get('avg_argument_validity', 0.0):.4f} | {row.get('avg_required_argument_recall', 0.0):.4f} | {_format_optional_float(row.get('tool_retrieval_hit_rate'), 4)} | {_format_optional_float(row.get('avg_target_tool_rank'), 2)} | {row.get('hallucinated_argument_count', 0)} |"
        )

    if routing_summary:
        lines.extend(
            [
                "",
                "## Hidden-Tool Routing Summary",
                "",
                "| Condition | Tool Accuracy | Joint Exact Match | Argument Validity | Gold Tool Hit@K | Avg Gold Tool Rank |",
                "| --- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for baseline in _ordered_baselines(routing_summary):
            row = routing_summary[baseline]
            lines.append(
                f"| {baseline} | {row.get('tool_selection_accuracy', 0.0):.4f} | {row.get('joint_exact_match_rate', 0.0):.4f} | {row.get('avg_argument_validity', 0.0):.4f} | {_format_optional_float(row.get('gold_tool_hit_rate'), 4)} | {_format_optional_float(row.get('avg_gold_tool_rank'), 2)} |"
            )

    if benchmark_summary_by_split:
        lines.extend(
            [
                "",
                "## Benchmark By Split",
                "",
                "| Split | Condition | Tasks | Exact Match | 95% CI | Argument Validity | Retrieval Hit@K | Avg Target Rank |",
                "| --- | --- | ---: | ---: | --- | ---: | ---: | ---: |",
            ]
        )
        for split_name in sorted(benchmark_summary_by_split):
            for baseline in _ordered_baselines(benchmark_summary_by_split[split_name]):
                row = benchmark_summary_by_split[split_name][baseline]
                ci = row.get("exact_match_ci", {"low": 0.0, "high": 0.0})
                lines.append(
                    f"| {split_name} | {baseline} | {row.get('num_tasks', 0)} | {row.get('exact_match_rate', 0.0):.4f} | [{ci.get('low', 0.0):.4f}, {ci.get('high', 0.0):.4f}] | {row.get('avg_argument_validity', 0.0):.4f} | {_format_optional_float(row.get('tool_retrieval_hit_rate'), 4)} | {_format_optional_float(row.get('avg_target_tool_rank'), 2)} |"
                )

    if routing_summary_by_split:
        lines.extend(
            [
                "",
                "## Hidden-Tool Routing By Split",
                "",
                "| Split | Condition | Tasks | Tool Accuracy | Joint Exact Match | Gold Tool Hit@K | Avg Gold Tool Rank |",
                "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for split_name in sorted(routing_summary_by_split):
            for baseline in _ordered_baselines(routing_summary_by_split[split_name]):
                row = routing_summary_by_split[split_name][baseline]
                lines.append(
                    f"| {split_name} | {baseline} | {row.get('num_tasks', 0)} | {row.get('tool_selection_accuracy', 0.0):.4f} | {row.get('joint_exact_match_rate', 0.0):.4f} | {_format_optional_float(row.get('gold_tool_hit_rate'), 4)} | {_format_optional_float(row.get('avg_gold_tool_rank'), 2)} |"
                )

    if benchmark_summary_by_tool:
        lines.extend(
            [
                "",
                "## Benchmark By Tool",
                "",
                "| Tool | Condition | Tasks | Exact Match | Argument Validity | Required Arg Recall | Retrieval Hit@K | Avg Target Rank |",
                "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for tool_name in _ordered_tools(benchmark_summary_by_tool):
            for baseline in _ordered_baselines(benchmark_summary_by_tool[tool_name]):
                row = benchmark_summary_by_tool[tool_name][baseline]
                lines.append(
                    f"| {tool_name} | {baseline} | {row.get('num_tasks', 0)} | {row.get('exact_match_rate', 0.0):.4f} | {row.get('avg_argument_validity', 0.0):.4f} | {row.get('avg_required_argument_recall', 0.0):.4f} | {_format_optional_float(row.get('tool_retrieval_hit_rate'), 4)} | {_format_optional_float(row.get('avg_target_tool_rank'), 2)} |"
                )

    if routing_summary_by_tool:
        lines.extend(
            [
                "",
                "## Hidden-Tool Routing By Gold Tool",
                "",
                "| Gold Tool | Condition | Tasks | Tool Accuracy | Joint Exact Match | Gold Tool Hit@K | Avg Gold Tool Rank |",
                "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for tool_name in _ordered_tools(routing_summary_by_tool):
            for baseline in _ordered_baselines(routing_summary_by_tool[tool_name]):
                row = routing_summary_by_tool[tool_name][baseline]
                lines.append(
                    f"| {tool_name} | {baseline} | {row.get('num_tasks', 0)} | {row.get('tool_selection_accuracy', 0.0):.4f} | {row.get('joint_exact_match_rate', 0.0):.4f} | {_format_optional_float(row.get('gold_tool_hit_rate'), 4)} | {_format_optional_float(row.get('avg_gold_tool_rank'), 2)} |"
                )

    if pairwise_comparisons:
        lines.extend(
            [
                "",
                "## Pairwise Comparisons",
                "",
                "| Anchor | Baseline | Paired Tasks | Win | Tie | Loss | Exact Match Delta | 95% CI | Avg Argument Validity Delta |",
                "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |",
            ]
        )
        for baseline in _ordered_baselines(pairwise_comparisons):
            row = pairwise_comparisons[baseline]
            ci = row.get("exact_match_delta_ci", {"low": 0.0, "high": 0.0})
            lines.append(
                f"| {row.get('anchor_baseline', 'generated_skill_base')} | {baseline} | {row.get('num_paired_tasks', 0)} | {row.get('win_count', 0)} | {row.get('tie_count', 0)} | {row.get('loss_count', 0)} | {row.get('exact_match_delta', 0.0):.4f} | [{ci.get('low', 0.0):.4f}, {ci.get('high', 0.0):.4f}] | {row.get('avg_argument_validity_delta', 0.0):.4f} |"
            )

    if error_taxonomy:
        lines.extend(["", "## Error Taxonomy", ""])
        for baseline in _ordered_baselines(error_taxonomy):
            row = error_taxonomy[baseline]
            lines.append(f"### {baseline}")
            lines.append("")
            lines.append(f"- failures: {row.get('num_failures', 0)}")
            for error_type, count in row.get("error_type_counts", {}).items():
                rate = row.get("error_type_rates", {}).get(error_type, 0.0)
                lines.append(f"- {error_type}: {count} ({rate:.4f})")
            lines.append("")

    if method_win_analysis:
        lines.extend(["", "## Method Wins", ""])
        for baseline in _ordered_baselines(method_win_analysis):
            row = method_win_analysis[baseline]
            lines.append(f"### generated_skill_base vs {baseline}")
            lines.append("")
            lines.append(f"- anchor wins: {row.get('num_anchor_wins', 0)}")
            top_error_types = row.get("wins_by_error_type", {})
            if top_error_types:
                top_items = ", ".join(f"{key}={value}" for key, value in list(top_error_types.items())[:4])
                lines.append(f"- recovered failure types: {top_items}")
            top_tags = row.get("wins_by_tag", {})
            if top_tags:
                top_items = ", ".join(f"{key}={value}" for key, value in list(top_tags.items())[:4])
                lines.append(f"- recovered tags: {top_items}")
            for example in row.get("example_wins", [])[:3]:
                lines.append(f"- `{example.get('task_id', 'unknown')}` on `{example.get('tool_name', 'unknown')}` [{example.get('baseline_error_type', 'unknown')}]")
            lines.append("")

    if package_summary_by_tool:
        lines.extend(
            [
                "",
                "## Packaging By Tool",
                "",
                "| Tool | Condition | Valid Rate | Avg Examples | Avg Template Fields | Avg Semantic Hints |",
                "| --- | --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for tool_name in _ordered_tools(package_summary_by_tool):
            for baseline in _ordered_baselines(package_summary_by_tool[tool_name]):
                row = package_summary_by_tool[tool_name][baseline]
                lines.append(
                    f"| {tool_name} | {baseline} | {row.get('valid_rate', 0.0):.4f} | {row.get('avg_examples', 0.0):.2f} | {row.get('avg_template_fields', 0.0):.2f} | {row.get('avg_semantic_hint_entries', 0.0):.2f} |"
                )

    if benchmark_failures:
        lines.extend(["", "## Failure Highlights", ""])
        for baseline in _ordered_baselines(benchmark_failures):
            failures = benchmark_failures[baseline]
            if not failures:
                continue
            lines.append(f"### {baseline}")
            lines.append("")
            for failure in failures:
                lines.append(f"- `{failure.get('task_id', 'unknown')}` on `{failure.get('tool_name', 'unknown')}`: {failure.get('user_request', '')}")
                lines.append(f"  expected `{_compact_json(failure.get('expected_arguments', {}))}`")
                lines.append(f"  predicted `{_compact_json(failure.get('predicted_arguments', {}))}`")
            lines.append("")

    lines.extend(
        [
            "",
            "## Headline",
            "",
            "The main comparison to track is whether `generated_skill_base` improves exact-match and argument-validity metrics over `raw_mcp`, and whether that gain shows up consistently on individual tools instead of only in the aggregate.",
            "",
        ]
    )
    return "\n".join(lines)


def build_results_csv(
    package_summary: Dict[str, Any],
    benchmark_summary: Dict[str, Any],
    routing_summary: Dict[str, Any] | None = None,
) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "condition",
            "valid_rate",
            "avg_examples",
            "avg_template_fields",
            "avg_semantic_hint_entries",
            "exact_match_rate",
            "avg_argument_validity",
            "avg_required_argument_recall",
            "tool_retrieval_hit_rate",
            "avg_target_tool_rank",
            "hallucinated_argument_count",
            "routing_tool_selection_accuracy",
            "routing_joint_exact_match_rate",
            "routing_gold_tool_hit_rate",
            "routing_avg_gold_tool_rank",
        ]
    )
    baseline_names = _ordered_baselines({**package_summary, **benchmark_summary, **(routing_summary or {})})
    for baseline in baseline_names:
        package_row = package_summary.get(baseline, {})
        benchmark_row = benchmark_summary.get(baseline, {})
        routing_row = (routing_summary or {}).get(baseline, {})
        writer.writerow(
            [
                baseline,
                package_row.get("valid_rate", ""),
                package_row.get("avg_examples", ""),
                package_row.get("avg_template_fields", ""),
                package_row.get("avg_semantic_hint_entries", ""),
                benchmark_row.get("exact_match_rate", ""),
                benchmark_row.get("avg_argument_validity", ""),
                benchmark_row.get("avg_required_argument_recall", ""),
                benchmark_row.get("tool_retrieval_hit_rate", ""),
                benchmark_row.get("avg_target_tool_rank", ""),
                benchmark_row.get("hallucinated_argument_count", ""),
                routing_row.get("tool_selection_accuracy", ""),
                routing_row.get("joint_exact_match_rate", ""),
                routing_row.get("gold_tool_hit_rate", ""),
                routing_row.get("avg_gold_tool_rank", ""),
            ]
        )
    return buffer.getvalue()


def build_benchmark_by_tool_csv(benchmark_summary_by_tool: Dict[str, Dict[str, Any]]) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "tool_name",
            "condition",
            "num_tasks",
            "exact_match_rate",
            "avg_argument_validity",
            "avg_required_argument_recall",
            "tool_retrieval_hit_rate",
            "avg_target_tool_rank",
            "hallucinated_argument_count",
        ]
    )
    for tool_name in _ordered_tools(benchmark_summary_by_tool):
        for baseline in _ordered_baselines(benchmark_summary_by_tool[tool_name]):
            row = benchmark_summary_by_tool[tool_name][baseline]
            writer.writerow(
                [
                    tool_name,
                    baseline,
                    row.get("num_tasks", ""),
                    row.get("exact_match_rate", ""),
                    row.get("avg_argument_validity", ""),
                    row.get("avg_required_argument_recall", ""),
                    row.get("tool_retrieval_hit_rate", ""),
                    row.get("avg_target_tool_rank", ""),
                    row.get("hallucinated_argument_count", ""),
                ]
            )
    return buffer.getvalue()


def build_benchmark_by_split_csv(benchmark_summary_by_split: Dict[str, Dict[str, Any]]) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "split",
            "condition",
            "num_tasks",
            "exact_match_rate",
            "exact_match_ci_low",
            "exact_match_ci_high",
            "avg_argument_validity",
            "avg_required_argument_recall",
            "tool_retrieval_hit_rate",
            "avg_target_tool_rank",
            "hallucinated_argument_count",
        ]
    )
    for split_name in sorted(benchmark_summary_by_split):
        for baseline in _ordered_baselines(benchmark_summary_by_split[split_name]):
            row = benchmark_summary_by_split[split_name][baseline]
            ci = row.get("exact_match_ci", {"low": "", "high": ""})
            writer.writerow(
                [
                    split_name,
                    baseline,
                    row.get("num_tasks", ""),
                    row.get("exact_match_rate", ""),
                    ci.get("low", ""),
                    ci.get("high", ""),
                    row.get("avg_argument_validity", ""),
                    row.get("avg_required_argument_recall", ""),
                    row.get("tool_retrieval_hit_rate", ""),
                    row.get("avg_target_tool_rank", ""),
                    row.get("hallucinated_argument_count", ""),
                ]
            )
    return buffer.getvalue()


def build_pairwise_comparison_csv(pairwise_comparisons: Dict[str, Any]) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "anchor_baseline",
            "comparison_baseline",
            "num_paired_tasks",
            "win_count",
            "tie_count",
            "loss_count",
            "win_rate",
            "exact_match_delta",
            "exact_match_delta_ci_low",
            "exact_match_delta_ci_high",
            "avg_argument_validity_delta",
        ]
    )
    for baseline in _ordered_baselines(pairwise_comparisons):
        row = pairwise_comparisons[baseline]
        ci = row.get("exact_match_delta_ci", {"low": "", "high": ""})
        writer.writerow(
            [
                row.get("anchor_baseline", ""),
                row.get("comparison_baseline", baseline),
                row.get("num_paired_tasks", ""),
                row.get("win_count", ""),
                row.get("tie_count", ""),
                row.get("loss_count", ""),
                row.get("win_rate", ""),
                row.get("exact_match_delta", ""),
                ci.get("low", ""),
                ci.get("high", ""),
                row.get("avg_argument_validity_delta", ""),
            ]
        )
    return buffer.getvalue()


def build_error_taxonomy_csv(error_taxonomy: Dict[str, Any]) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["condition", "error_type", "count", "rate"])
    for baseline in _ordered_baselines(error_taxonomy):
        row = error_taxonomy[baseline]
        counts = row.get("error_type_counts", {})
        rates = row.get("error_type_rates", {})
        for error_type in sorted(counts):
            writer.writerow([baseline, error_type, counts.get(error_type, ""), rates.get(error_type, "")])
    return buffer.getvalue()


def build_method_wins_csv(method_win_analysis: Dict[str, Any]) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "anchor_baseline",
            "comparison_baseline",
            "num_anchor_wins",
            "top_error_type",
            "top_error_type_count",
            "top_tag",
            "top_tag_count",
        ]
    )
    for baseline in _ordered_baselines(method_win_analysis):
        row = method_win_analysis[baseline]
        top_error_items = list(row.get("wins_by_error_type", {}).items())
        top_tag_items = list(row.get("wins_by_tag", {}).items())
        top_error = top_error_items[0] if top_error_items else ("", "")
        top_tag = top_tag_items[0] if top_tag_items else ("", "")
        writer.writerow(
            [
                row.get("anchor_baseline", "generated_skill_base"),
                row.get("comparison_baseline", baseline),
                row.get("num_anchor_wins", ""),
                top_error[0],
                top_error[1],
                top_tag[0],
                top_tag[1],
            ]
        )
    return buffer.getvalue()


def build_package_by_tool_csv(package_summary_by_tool: Dict[str, Dict[str, Any]]) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "tool_name",
            "condition",
            "total_tools",
            "valid_packages",
            "valid_rate",
            "avg_examples",
            "avg_template_fields",
            "avg_semantic_hint_entries",
        ]
    )
    for tool_name in _ordered_tools(package_summary_by_tool):
        for baseline in _ordered_baselines(package_summary_by_tool[tool_name]):
            row = package_summary_by_tool[tool_name][baseline]
            writer.writerow(
                [
                    tool_name,
                    baseline,
                    row.get("total_tools", ""),
                    row.get("valid_packages", ""),
                    row.get("valid_rate", ""),
                    row.get("avg_examples", ""),
                    row.get("avg_template_fields", ""),
                    row.get("avg_semantic_hint_entries", ""),
                ]
            )
    return buffer.getvalue()


def build_routing_results_csv(routing_summary: Dict[str, Any]) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "condition",
            "num_tasks",
            "tool_selection_accuracy",
            "tool_selection_accuracy_ci_low",
            "tool_selection_accuracy_ci_high",
            "joint_exact_match_rate",
            "joint_exact_match_ci_low",
            "joint_exact_match_ci_high",
            "avg_argument_validity",
            "avg_required_argument_recall",
            "gold_tool_hit_rate",
            "avg_gold_tool_rank",
        ]
    )
    for baseline in _ordered_baselines(routing_summary):
        row = routing_summary[baseline]
        tool_ci = row.get("tool_selection_accuracy_ci", {"low": "", "high": ""})
        joint_ci = row.get("joint_exact_match_ci", {"low": "", "high": ""})
        writer.writerow(
            [
                baseline,
                row.get("num_tasks", ""),
                row.get("tool_selection_accuracy", ""),
                tool_ci.get("low", ""),
                tool_ci.get("high", ""),
                row.get("joint_exact_match_rate", ""),
                joint_ci.get("low", ""),
                joint_ci.get("high", ""),
                row.get("avg_argument_validity", ""),
                row.get("avg_required_argument_recall", ""),
                row.get("gold_tool_hit_rate", ""),
                row.get("avg_gold_tool_rank", ""),
            ]
        )
    return buffer.getvalue()


def build_routing_by_tool_csv(routing_summary_by_tool: Dict[str, Dict[str, Any]]) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "gold_tool_name",
            "condition",
            "num_tasks",
            "tool_selection_accuracy",
            "joint_exact_match_rate",
            "avg_argument_validity",
            "gold_tool_hit_rate",
            "avg_gold_tool_rank",
        ]
    )
    for tool_name in _ordered_tools(routing_summary_by_tool):
        for baseline in _ordered_baselines(routing_summary_by_tool[tool_name]):
            row = routing_summary_by_tool[tool_name][baseline]
            writer.writerow(
                [
                    tool_name,
                    baseline,
                    row.get("num_tasks", ""),
                    row.get("tool_selection_accuracy", ""),
                    row.get("joint_exact_match_rate", ""),
                    row.get("avg_argument_validity", ""),
                    row.get("gold_tool_hit_rate", ""),
                    row.get("avg_gold_tool_rank", ""),
                ]
            )
    return buffer.getvalue()


def build_routing_by_split_csv(routing_summary_by_split: Dict[str, Dict[str, Any]]) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "split",
            "condition",
            "num_tasks",
            "tool_selection_accuracy",
            "joint_exact_match_rate",
            "avg_argument_validity",
            "gold_tool_hit_rate",
            "avg_gold_tool_rank",
        ]
    )
    for split_name in sorted(routing_summary_by_split):
        for baseline in _ordered_baselines(routing_summary_by_split[split_name]):
            row = routing_summary_by_split[split_name][baseline]
            writer.writerow(
                [
                    split_name,
                    baseline,
                    row.get("num_tasks", ""),
                    row.get("tool_selection_accuracy", ""),
                    row.get("joint_exact_match_rate", ""),
                    row.get("avg_argument_validity", ""),
                    row.get("gold_tool_hit_rate", ""),
                    row.get("avg_gold_tool_rank", ""),
                ]
            )
    return buffer.getvalue()


def write_report(
    output_dir: str | Path,
    markdown_text: str,
    csv_text: str,
    extra_files: Dict[str, str] | None = None,
) -> None:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "main_results.md").write_text(markdown_text, encoding="utf-8")
    (out_dir / "main_results.csv").write_text(csv_text, encoding="utf-8")
    for name, text in (extra_files or {}).items():
        (out_dir / name).write_text(text, encoding="utf-8")

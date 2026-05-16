from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

from autoskill.ir import GeneratedSkill, ToolIR
from autoskill.templates import build_argument_template, build_structured_call_hints
from autoskill.validator import validate_skill


def build_semantic_hints(tool: ToolIR) -> Dict[str, Any]:
    hints: Dict[str, Any] = {}
    argument_names = {arg.name for arg in tool.arguments}

    if "head" in argument_names:
        hints["head"] = {
            "top": "__number__",
            "beginning": "__number__",
            "opening": "__number__",
            "start of": "__number__",
        }
    if "tail" in argument_names:
        hints["tail"] = {
            "bottom": "__number__",
            "trailing": "__number__",
            "ending": "__number__",
            "end of": "__number__",
        }
    if "pattern" in argument_names:
        hints["pattern"] = {
            "python": "**/*.py",
            "markdown": "**/*.md",
            "text": "**/*.txt",
            "json": "**/*.json",
            "yaml": "**/*.yaml",
            "yml": "**/*.yml",
        }
    if "excludePatterns" in argument_names:
        hints["excludePatterns"] = {
            "exclude": "__paths__",
            "ignore": "__paths__",
            "skip": "__paths__",
        }
    if "content" in argument_names:
        hints["content"] = {
            "containing the text": "__tail_text__",
            "with content": "__tail_text__",
            "save": "__quoted_text_to_path__",
            "write": "__quoted_text_to_path__",
        }

    for arg in tool.arguments:
        if arg.enum and all(isinstance(value, str) for value in arg.enum):
            enum_hints = {str(value).lower(): value for value in arg.enum}
            if arg.name == "unit":
                enum_hints.update({"fahrenheit": "F", "celsius": "C", "centigrade": "C"})
            hints.setdefault(arg.name, {}).update(enum_hints)

    return hints


def build_semantic_examples(tool: ToolIR, semantic_hints: Dict[str, Any]) -> List[Dict[str, Any]]:
    examples: List[Dict[str, Any]] = []

    if tool.tool_name == "read_text_file":
        if "head" in semantic_hints:
            examples.append(
                {
                    "scenario": "Semantic cue for reading the beginning of a file",
                    "arguments": {"path": "src/app.py", "head": 8},
                }
            )
        if "tail" in semantic_hints:
            examples.append(
                {
                    "scenario": "Semantic cue for reading the end of a file",
                    "arguments": {"path": "logs/output.txt", "tail": 12},
                }
            )

    if tool.tool_name == "search_files" and "pattern" in semantic_hints:
        examples.append(
            {
                "scenario": "Semantic cue for Python files",
                "arguments": {"path": "src", "pattern": "**/*.py", "excludePatterns": []},
            }
        )
        examples.append(
            {
                "scenario": "Semantic cue for Markdown files",
                "arguments": {"path": "docs", "pattern": "**/*.md", "excludePatterns": []},
            }
        )

    if tool.tool_name == "write_file" and "content" in semantic_hints:
        examples.append(
            {
                "scenario": "Quoted text can be written directly to a destination path",
                "arguments": {"path": "docs/notes.txt", "content": "Release checklist"},
            }
        )

    if tool.tool_name == "create_directory":
        examples.append(
            {
                "scenario": "Ensure-style request for directory creation",
                "arguments": {"path": "reports/weekly"},
            }
        )

    if tool.tool_name == "list_directory":
        examples.append(
            {
                "scenario": "Inspect the contents of a specific folder",
                "arguments": {"path": "docs"},
            }
        )

    return examples


def build_enhanced_skill_candidates(tool: ToolIR, base_skill: GeneratedSkill) -> List[Dict[str, Any]]:
    semantic_hints = build_semantic_hints(tool)
    semantic_examples = build_semantic_examples(tool, semantic_hints)
    dense_template = build_argument_template(tool, include_optional=False, variant=0)
    call_hints = build_structured_call_hints(tool)

    concise = deepcopy(base_skill)
    concise.when_to_use = [
        *concise.when_to_use,
        "Use the semantic hints when the request uses paraphrases rather than exact schema wording.",
    ]
    concise.semantic_hints = semantic_hints

    dense = deepcopy(base_skill)
    dense.when_to_use = [
        *dense.when_to_use,
        *call_hints["when_to_use"],
        "Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.",
        "Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.",
    ]
    dense.when_not_to_use = [
        *dense.when_not_to_use,
        *call_hints["when_not_to_use"],
        "Do not let semantic cues override explicit user-provided field values.",
    ]
    dense.argument_template = dense_template
    dense.semantic_hints = semantic_hints
    dense.examples = [*dense.examples, *semantic_examples]

    candidates = [
        {"label": "base", "skill": base_skill},
        {"label": "semantic_concise", "skill": concise},
        {"label": "semantic_dense", "skill": dense},
    ]
    return candidates


def _count_semantic_entries(semantic_hints: Dict[str, Any]) -> int:
    total = 0
    for value in semantic_hints.values():
        if isinstance(value, dict):
            total += len(value)
        elif isinstance(value, list):
            total += len(value)
        else:
            total += 1
    return total


def _count_required_argument_example_coverage(tool: ToolIR, skill: GeneratedSkill) -> int:
    required_names = {arg.name for arg in tool.arguments if arg.required}
    if not required_names:
        return 0
    covered = set(skill.argument_template).intersection(required_names)
    for example in skill.examples:
        arguments = example.get("arguments", {})
        if isinstance(arguments, dict):
            covered.update(set(arguments).intersection(required_names))
    return len(covered)


def score_skill_candidate(tool: ToolIR, candidate_label: str, skill: GeneratedSkill) -> Dict[str, Any]:
    report = validate_skill(tool, skill)
    required_coverage = _count_required_argument_example_coverage(tool, skill)
    semantic_entries = _count_semantic_entries(skill.semantic_hints)
    error_count = sum(1 for issue in report.issues if issue.severity == "error")
    warning_count = sum(1 for issue in report.issues if issue.severity == "warning")

    score = 0.0
    score += 100.0 if report.valid else -100.0
    score += 6.0 * required_coverage
    score += 1.5 * len(skill.examples)
    score += 0.75 * len(skill.when_to_use)
    score += 0.25 * len(skill.when_not_to_use)
    score += 1.25 * semantic_entries
    score -= 10.0 * error_count
    score -= 2.0 * warning_count

    return {
        "label": candidate_label,
        "score": round(score, 4),
        "valid": report.valid,
        "num_examples": len(skill.examples),
        "required_argument_coverage": required_coverage,
        "semantic_hint_entries": semantic_entries,
        "error_count": error_count,
        "warning_count": warning_count,
    }


def select_best_skill_candidate(tool: ToolIR, candidates: List[Dict[str, Any]]) -> GeneratedSkill:
    scored_candidates: List[Dict[str, Any]] = []
    for candidate in candidates:
        score = score_skill_candidate(tool, candidate["label"], candidate["skill"])
        scored_candidates.append(score)

    best = max(
        scored_candidates,
        key=lambda item: (
            1 if item["valid"] else 0,
            item["score"],
            item["required_argument_coverage"],
            item["semantic_hint_entries"],
            item["num_examples"],
        ),
    )

    selected = next(candidate["skill"] for candidate in candidates if candidate["label"] == best["label"])
    selected.method_trace = [
        *scored_candidates,
        {
            "selected_label": best["label"],
            "selection_strategy": "validation_aware_richness_rerank",
        },
    ]
    return selected

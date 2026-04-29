from __future__ import annotations

import csv
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

import yaml

from autoskill.parser import parse_mcp_tool


DEFAULT_CONFIG = {
    "seed": 42,
    "tools_path": "data/processed_toolir/tools.jsonl",
    "positive_controls_per_tool": 5,
    "positives_per_tool_easy": None,
    "positives_per_tool_medium": None,
    "positives_per_tool_hard": None,
    "negatives_per_tool_easy": None,
    "negatives_per_tool_medium": None,
    "negatives_per_tool_hard": None,
    "negative_categories": [
        "adjacent_intent",
        "known_path_no_search_needed",
        "wrong_tool_boundary",
        "missing_required_info",
        "destructive_action_mismatch",
        "read_vs_write_mismatch",
        "out_of_domain_request",
    ],
    "outputs": {
        "dev": "data/controls/dev.jsonl",
        "test": "data/controls/test.jsonl",
        "stats": "outputs/tables/control_stats.csv",
        "difficulty_stats": "outputs/tables/control_difficulty_stats.csv",
        "negative_category_stats": "outputs/tables/negative_category_stats.csv",
    },
}

READ_EFFECTS = {"read"}
WRITE_EFFECTS = {"write", "delete", "execute", "external_communication"}


def load_control_config(path: str | Path) -> Dict[str, Any]:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f) or {}
    if not isinstance(loaded, dict):
        raise ValueError("Control config must be a mapping.")
    config = _merge_dicts(DEFAULT_CONFIG, loaded)
    _normalize_output_paths(config, loaded)
    if _tiered_generation_enabled(config):
        for key in TIERED_COUNT_KEYS:
            if int(config.get(key) or 0) < 0:
                raise ValueError(f"{key} must be non-negative.")
        if sum(int(config.get(key) or 0) for key in TIERED_COUNT_KEYS) <= 0:
            raise ValueError("At least one tiered control count must be positive.")
    elif int(config.get("positive_controls_per_tool", 0)) < 3:
        raise ValueError("positive_controls_per_tool must be at least 3.")
    if len(config.get("negative_categories") or []) < 3:
        raise ValueError("At least 3 negative categories are required.")
    return config


TIERED_COUNT_KEYS = (
    "positives_per_tool_easy",
    "positives_per_tool_medium",
    "positives_per_tool_hard",
    "negatives_per_tool_easy",
    "negatives_per_tool_medium",
    "negatives_per_tool_hard",
)


def _tiered_generation_enabled(config: Dict[str, Any]) -> bool:
    return any(config.get(key) is not None for key in TIERED_COUNT_KEYS)


def _normalize_output_paths(config: Dict[str, Any], loaded: Dict[str, Any]) -> None:
    loaded_outputs = loaded.get("outputs") if isinstance(loaded.get("outputs"), dict) else {}
    outputs = config["outputs"]
    stats_path = Path(str(outputs.get("stats") or DEFAULT_CONFIG["outputs"]["stats"]))
    if "difficulty_stats" not in loaded_outputs:
        outputs["difficulty_stats"] = str(stats_path.parent / "control_difficulty_stats.csv")
    if "negative_category_stats" not in loaded_outputs:
        outputs["negative_category_stats"] = str(stats_path.parent / "negative_category_stats.csv")


def _merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_toolir_records(path: str | Path) -> List[Dict[str, Any]]:
    input_path = Path(path)
    records: List[Dict[str, Any]] = []
    if input_path.suffix.lower() == ".jsonl":
        with input_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                if isinstance(item, dict):
                    records.append(_coerce_toolir_record(item))
    else:
        raw = json.loads(input_path.read_text(encoding="utf-8"))
        items = raw if isinstance(raw, list) else raw.get("tools", []) if isinstance(raw, dict) else []
        for item in items:
            if isinstance(item, dict):
                records.append(_coerce_toolir_record(item))
    return sorted(records, key=lambda item: (str(item.get("server_name") or ""), str(item.get("tool_name") or "")))


def _coerce_toolir_record(item: Dict[str, Any]) -> Dict[str, Any]:
    if "tool_name" in item and "arguments" in item:
        return item
    parsed = parse_mcp_tool(item)
    payload = parsed.model_dump()
    if isinstance(item.get("source_metadata"), dict):
        payload["source_metadata"] = item["source_metadata"]
    return payload


def build_controls(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    seed = int(config.get("seed", 42))
    random.seed(seed)
    tools = load_toolir_records(config["tools_path"])
    controls: List[Dict[str, Any]] = []
    if _tiered_generation_enabled(config):
        for tool_index, tool in enumerate(tools):
            controls.extend(_tiered_positive_controls(tool, tools, tool_index, config, seed))
            controls.extend(_tiered_negative_controls(tool, tools, tool_index, config, seed))
    else:
        positive_count = int(config["positive_controls_per_tool"])
        negative_categories = [str(item) for item in config.get("negative_categories") or []]
        for tool_index, tool in enumerate(tools):
            controls.extend(_positive_controls(tool, tool_index, positive_count, seed))
            for category_index, category in enumerate(negative_categories):
                controls.append(_negative_control(tool, tools, tool_index, category_index, category, seed))
    controls = _avoid_cross_split_duplicate_requests(controls)
    return sorted(controls, key=lambda item: (item["split"], item["gold_tool"], item["category"], item["id"]))


def _positive_controls(tool: Dict[str, Any], tool_index: int, count: int, seed: int) -> List[Dict[str, Any]]:
    controls: List[Dict[str, Any]] = []
    for variant in range(count):
        split = "dev" if variant < max(1, count // 2) else "test"
        args = _sample_arguments(tool, variant, include_optional=variant % 2 == 1)
        title = _tool_title(tool)
        purpose = _purpose_fragment(tool)
        arg_text = _format_args(args)
        templates = _positive_templates(split)
        request = templates[variant % len(templates)].format(title=title, purpose=purpose, args=arg_text)
        controls.append(
            _control_record(
                control_id=f"ctrl_{tool_index:04d}_{_slug(tool['tool_name'])}_positive_{variant}",
                tool=tool,
                user_request=request,
                category="positive",
                gold_tool=tool["tool_name"],
                gold_args=args,
                should_trigger=True,
                split=split,
                rationale="The request directly asks for the target tool capability and provides enough schema-compatible arguments.",
                seed=seed,
                tags=["positive", "target_use"],
            )
        )
    return controls


def _tiered_positive_controls(
    tool: Dict[str, Any],
    tools: Sequence[Dict[str, Any]],
    tool_index: int,
    config: Dict[str, Any],
    seed: int,
) -> List[Dict[str, Any]]:
    controls: List[Dict[str, Any]] = []
    counts = {
        "easy": int(config.get("positives_per_tool_easy") or 0),
        "medium": int(config.get("positives_per_tool_medium") or 0),
        "hard": int(config.get("positives_per_tool_hard") or 0),
    }
    for difficulty, count in counts.items():
        for variant in range(count):
            other = _select_adjacent_tool(tool, tools, "adjacent_intent")
            include_optional = difficulty in {"medium", "hard"}
            args = _sample_arguments(tool, variant + _difficulty_offset(difficulty), include_optional=include_optional)
            if difficulty == "hard":
                args = _ensure_complex_argument_use(tool, args, variant)
            request, rationale, failure_mode = _positive_tier_request(tool, other, args, difficulty, variant)
            split = _tiered_split("positive", difficulty, variant)
            controls.append(
                _control_record(
                    control_id=f"ctrl_{tool_index:04d}_{_slug(tool['tool_name'])}_positive_{difficulty}_{variant}",
                    tool=tool,
                    user_request=request,
                    category=f"positive_{difficulty}",
                    gold_tool=tool["tool_name"],
                    gold_args=args,
                    should_trigger=True,
                    split=split,
                    rationale=rationale,
                    seed=seed,
                    tags=["positive", f"positive_{difficulty}", difficulty, "target_use"],
                    difficulty=difficulty,
                    control_family="positive",
                    expected_failure_mode=failure_mode,
                    alternative_valid_tools=[],
                )
            )
    return controls


def _positive_tier_request(
    tool: Dict[str, Any],
    other: Dict[str, Any] | None,
    args: Dict[str, Any],
    difficulty: str,
    variant: int,
) -> tuple[str, str, str]:
    title = _tool_title(tool)
    purpose = _purpose_fragment(tool)
    arg_text = _format_args(args)
    other_title = _tool_title(other) if other else "a nearby tool"
    if difficulty == "easy":
        return (
            f"Use {title} to {purpose}. Set {arg_text}.",
            "Easy positive: direct request, clear target intent, and all required arguments are explicit.",
            "none_target_tool_should_trigger",
        )
    if difficulty == "medium":
        templates = [
            f"I need help with this task: {purpose}. The relevant details are {arg_text}.",
            f"Please handle the request to {purpose}; include these details where applicable: {arg_text}.",
        ]
        return (
            templates[variant % len(templates)],
            "Medium positive: paraphrased intent with optional details and mild ambiguity, but enough information to invoke the target tool.",
            "paraphrase_or_optional_arg_miss",
        )
    return (
        f"I am trying to get this done without using {other_title}: {purpose}. Use the best matching tool and apply {arg_text}; leave any unspecified optional details at their defaults.",
        "Hard positive: indirect request with distractor pressure and complex or optional argument use while preserving a valid target invocation.",
        "distractor_confusion_or_complex_argument_miss",
    )


def _difficulty_offset(difficulty: str) -> int:
    return {"easy": 0, "medium": 7, "hard": 17}.get(difficulty, 0)


def _ensure_complex_argument_use(tool: Dict[str, Any], args: Dict[str, Any], variant: int) -> Dict[str, Any]:
    enriched = dict(args)
    for arg in tool.get("arguments", []) or []:
        if arg.get("name") in enriched:
            continue
        if arg.get("enum") or arg.get("type") in {"object", "array", "boolean"}:
            enriched[arg["name"]] = _sample_value(arg, variant + 17)
    return enriched


def _negative_control(
    tool: Dict[str, Any],
    tools: Sequence[Dict[str, Any]],
    tool_index: int,
    category_index: int,
    category: str,
    seed: int,
) -> Dict[str, Any]:
    split = "dev" if category_index % 2 == 0 else "test"
    other = _select_adjacent_tool(tool, tools, category)
    target_title = _tool_title(tool)
    other_title = _tool_title(other) if other else "a different tool"
    other_args = _sample_arguments(other, category_index, include_optional=False) if other else {}
    gold_tool = other["tool_name"] if other and category not in {"missing_required_info", "out_of_domain_request"} else "__abstain__"
    gold_args = other_args if gold_tool != "__abstain__" else {}
    request, rationale = _negative_request_and_rationale(category, tool, other, target_title, other_title)
    return _control_record(
        control_id=f"ctrl_{tool_index:04d}_{_slug(tool['tool_name'])}_{category}",
        tool=tool,
        user_request=request,
        category=category,
        gold_tool=gold_tool,
        gold_args=gold_args,
        should_trigger=False,
        split=split,
        rationale=rationale,
        seed=seed,
        negative_target=tool["tool_name"],
        expected_tool_name=gold_tool if gold_tool != "__abstain__" else None,
        tags=["negative", category],
    )


def _tiered_negative_controls(
    tool: Dict[str, Any],
    tools: Sequence[Dict[str, Any]],
    tool_index: int,
    config: Dict[str, Any],
    seed: int,
) -> List[Dict[str, Any]]:
    controls: List[Dict[str, Any]] = []
    counts = {
        "easy": int(config.get("negatives_per_tool_easy") or 0),
        "medium": int(config.get("negatives_per_tool_medium") or 0),
        "hard": int(config.get("negatives_per_tool_hard") or 0),
    }
    category_plan = {
        "easy": ["out_of_domain_request"],
        "medium": [
            "adjacent_wrong_intent",
            "explanation_instead_of_action",
            "known_path_no_search_needed",
            "read_vs_search_mismatch",
        ],
        "hard": [
            "near_miss_intent",
            "destructive_vs_readonly_mismatch",
            "similar_tool_should_be_used",
            "missing_required_info",
            "ambiguous_abstain_safer",
        ],
    }
    for difficulty, count in counts.items():
        for variant in range(count):
            category = category_plan[difficulty][(tool_index + variant) % len(category_plan[difficulty])]
            other = _select_adjacent_tool(tool, tools, _legacy_negative_category(category))
            request, rationale, expected_failure_mode = _negative_tier_request(category, difficulty, tool, other)
            alternative_tools = _alternative_valid_tools(category, other)
            if category == "similar_tool_should_be_used" and other:
                gold_tool = other["tool_name"]
                gold_args = _sample_arguments(other, variant + _difficulty_offset(difficulty), include_optional=False)
                expected_tool_name = gold_tool
            else:
                gold_tool = "__abstain__"
                gold_args = {}
                expected_tool_name = None
            split = _tiered_split("negative", difficulty, variant)
            controls.append(
                _control_record(
                    control_id=f"ctrl_{tool_index:04d}_{_slug(tool['tool_name'])}_negative_{difficulty}_{variant}_{category}",
                    tool=tool,
                    user_request=request,
                    category=f"negative_{difficulty}",
                    gold_tool=gold_tool,
                    gold_args=gold_args,
                    should_trigger=False,
                    split=split,
                    rationale=rationale,
                    seed=seed,
                    negative_target=tool["tool_name"],
                    expected_tool_name=expected_tool_name,
                    tags=["negative", f"negative_{difficulty}", difficulty, category],
                    difficulty=difficulty,
                    control_family="negative",
                    negative_category=category,
                    expected_failure_mode=expected_failure_mode,
                    alternative_valid_tools=alternative_tools,
                )
            )
    return controls


def _legacy_negative_category(category: str) -> str:
    mapping = {
        "adjacent_wrong_intent": "adjacent_intent",
        "explanation_instead_of_action": "wrong_tool_boundary",
        "read_vs_search_mismatch": "known_path_no_search_needed",
        "near_miss_intent": "adjacent_intent",
        "destructive_vs_readonly_mismatch": "destructive_action_mismatch",
        "similar_tool_should_be_used": "wrong_tool_boundary",
        "ambiguous_abstain_safer": "missing_required_info",
    }
    return mapping.get(category, category)


def _alternative_valid_tools(category: str, other: Dict[str, Any] | None) -> List[str]:
    if category == "similar_tool_should_be_used" and other:
        return [str(other["tool_name"])]
    return []


def _negative_tier_request(
    category: str,
    difficulty: str,
    tool: Dict[str, Any],
    other: Dict[str, Any] | None,
) -> tuple[str, str, str]:
    target_title = _tool_title(tool)
    target_purpose = _purpose_fragment(tool)
    other_title = _tool_title(other) if other else "a different tool"
    other_purpose = _purpose_fragment(other) if other else "handle the neighboring task"
    required = [arg["name"] for arg in tool.get("arguments", []) if arg.get("required")]
    missing_arg = required[0] if required else "the required input"
    if category == "out_of_domain_request":
        return (
            f"Plan a three-day museum itinerary in Chicago and estimate ticket costs; this is unrelated to {target_title}.",
            "Easy negative: clearly unrelated user request should abstain from the target tool.",
            "out_of_domain_false_trigger",
        )
    if category == "adjacent_wrong_intent":
        return (
            f"I need to {other_purpose}. This is adjacent to {target_title}, but the intended capability is {other_title}.",
            "Medium negative: neighboring intent belongs outside the target tool boundary.",
            "adjacent_tool_confusion",
        )
    if category == "explanation_instead_of_action":
        return (
            f"Explain when someone should use {target_title}; do not actually call it or perform the action.",
            "Medium negative: asks for explanation rather than tool execution.",
            "explanation_triggered_as_action",
        )
    if category == "known_path_no_search_needed":
        return (
            f"I already know the exact path docs/known_file.md, so no search or discovery is needed with {target_title}.",
            "Medium negative: known-path request should not trigger search-style behavior.",
            "known_path_search_misfire",
        )
    if category == "read_vs_search_mismatch":
        return (
            f"Read the exact item I named directly; do not search, retrieve candidates, or browse with {target_title}.",
            "Medium negative: direct read intent should not be treated as retrieval/search.",
            "read_vs_search_boundary_error",
        )
    if category == "near_miss_intent":
        return (
            f"This sounds close to {target_title}, but I only want a checklist for how to {target_purpose}; no tool call yet.",
            "Hard negative: near-miss wording resembles the target but explicitly requests planning only.",
            "near_miss_false_trigger",
        )
    if category == "destructive_vs_readonly_mismatch":
        if _side_effect(tool) in WRITE_EFFECTS:
            request = f"Only inspect what would happen before using {target_title}; do not create, update, delete, send, execute, or mutate anything."
        else:
            request = f"I need a change made, not a read-only lookup with {target_title}; do not satisfy this with a read/search tool."
        return (
            request,
            "Hard negative: request crosses destructive/read-only boundary and should not trigger the target.",
            "side_effect_boundary_error",
        )
    if category == "similar_tool_should_be_used":
        return (
            f"Use {other_title} to {other_purpose}; {target_title} is a distractor and should not be called.",
            "Hard negative: a similar valid tool should be selected instead of the target.",
            "similar_tool_distractor_error",
        )
    if category == "missing_required_info":
        return (
            f"I may need {target_title} to {target_purpose}, but I do not know {missing_arg} yet.",
            "Hard negative: required information is missing, so abstention is safer.",
            "missing_required_argument_false_trigger",
        )
    return (
        f"Maybe do something with {target_title}; actually, I am not sure what input or action is intended.",
        "Hard negative: ambiguous request where abstention is safer than guessing.",
        "ambiguous_request_should_abstain",
    )


def _tiered_split(control_family: str, difficulty: str, variant: int) -> str:
    if control_family == "positive":
        if difficulty == "easy":
            return "dev"
        if difficulty == "medium":
            return "dev" if variant % 2 == 0 else "test"
        return "test"
    if difficulty == "easy":
        return "dev"
    if difficulty == "medium":
        return "dev" if variant % 2 == 0 else "test"
    return "test" if variant % 2 == 0 else "dev"


def _negative_request_and_rationale(
    category: str,
    tool: Dict[str, Any],
    other: Dict[str, Any] | None,
    target_title: str,
    other_title: str,
) -> tuple[str, str]:
    target_purpose = _purpose_fragment(tool)
    other_purpose = _purpose_fragment(other) if other else "handle that separate task"
    required = [arg["name"] for arg in tool.get("arguments", []) if arg.get("required")]
    missing_arg = required[0] if required else "the required input"
    if category == "adjacent_intent":
        return (
            f"I need to {other_purpose}. Do not use {target_title}; this is for {other_title}.",
            "The user intent is close to the target domain but belongs to a neighboring tool.",
        )
    if category == "known_path_no_search_needed":
        return (
            f"I already know the exact path docs/known_file.md, so no search is needed; use the appropriate direct action instead of {target_title}.",
            "The request provides a known path and explicitly rules out search-style behavior.",
        )
    if category == "wrong_tool_boundary":
        return (
            f"This is a boundary check: {other_title} should handle the request to {other_purpose}, not {target_title}.",
            "The request names a capability outside the target tool boundary.",
        )
    if category == "missing_required_info":
        return (
            f"I might need {target_title} to {target_purpose}, but I do not know {missing_arg} yet.",
            "The request withholds required information, so the tool should not be invoked.",
        )
    if category == "destructive_action_mismatch":
        return (
            f"Only preview what would change; do not create, overwrite, delete, send, execute, or mutate anything with {target_title}.",
            "The user asks for a non-destructive preview while the target may perform or imply side effects.",
        )
    if category == "read_vs_write_mismatch":
        if _side_effect(tool) in READ_EFFECTS:
            request = f"Create or overwrite docs/control_output.txt with a short note; do not merely read using {target_title}."
        else:
            request = f"Read docs/control_output.txt without changing it; do not write, update, or delete using {target_title}."
        return (
            request,
            "The request crosses the read/write boundary and should not trigger the target tool.",
        )
    if category == "out_of_domain_request":
        return (
            f"Book a dentist appointment for next Tuesday and estimate the insurance copay; this is unrelated to {target_title}.",
            "The user request is outside the target tool domain.",
        )
    return (
        f"Do not use {target_title}; this request is not asking to {target_purpose}.",
        "Generic non-use boundary.",
    )


def _control_record(
    *,
    control_id: str,
    tool: Dict[str, Any],
    user_request: str,
    category: str,
    gold_tool: str,
    gold_args: Dict[str, Any],
    should_trigger: bool,
    split: str,
    rationale: str,
    seed: int,
    tags: List[str],
    negative_target: str | None = None,
    expected_tool_name: str | None = None,
    difficulty: str = "legacy",
    control_family: str | None = None,
    negative_category: str | None = None,
    expected_failure_mode: str = "legacy_boundary",
    alternative_valid_tools: List[str] | None = None,
) -> Dict[str, Any]:
    family = control_family or ("positive" if should_trigger else "negative")
    negative_label = negative_category if family == "negative" else None
    alternatives = list(alternative_valid_tools or [])
    record = {
        "id": control_id,
        "control_id": control_id,
        "task_id": control_id,
        "function": tool["tool_name"],
        "tool_name": tool["tool_name"],
        "question": user_request,
        "user_request": user_request,
        "category": category,
        "difficulty": difficulty,
        "control_family": family,
        "negative_category": negative_label,
        "expected_failure_mode": expected_failure_mode,
        "gold_tool": gold_tool,
        "gold_args": gold_args,
        "alternative_valid_tools": alternatives,
        "ground_truth": {"arguments": gold_args},
        "expected_arguments": gold_args,
        "expected_argument_candidates": [gold_args],
        "should_trigger": should_trigger,
        "split": split,
        "rationale": rationale,
        "source_server": tool.get("server_name"),
        "tool_key": _tool_key(tool),
        "domain": _domain(tool),
        "side_effect_type": _side_effect(tool),
        "seed": seed,
        "tags": tags,
    }
    if negative_target:
        record["negative_target"] = negative_target
    if expected_tool_name:
        record["expected_tool_name"] = expected_tool_name
    return record


def _select_adjacent_tool(tool: Dict[str, Any], tools: Sequence[Dict[str, Any]], category: str) -> Dict[str, Any] | None:
    target_name = tool["tool_name"]
    target_domain = _domain(tool)
    target_effect = _side_effect(tool)
    candidates = [item for item in tools if item.get("tool_name") != target_name]
    if category in {"adjacent_intent", "wrong_tool_boundary"}:
        same_domain = [item for item in candidates if _domain(item) == target_domain]
        if same_domain:
            return same_domain[0]
    if category in {"known_path_no_search_needed", "read_vs_write_mismatch"}:
        desired = READ_EFFECTS if target_effect in WRITE_EFFECTS else WRITE_EFFECTS
        effect_match = [item for item in candidates if _side_effect(item) in desired]
        if effect_match:
            return effect_match[0]
    if category == "destructive_action_mismatch":
        non_destructive = [item for item in candidates if _side_effect(item) in READ_EFFECTS]
        if non_destructive:
            return non_destructive[0]
    return candidates[0] if candidates else None


def _avoid_cross_split_duplicate_requests(controls: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    first_split_by_request: Dict[str, str] = {}
    adjusted: List[Dict[str, Any]] = []
    for control in controls:
        record = dict(control)
        request = str(record.get("user_request") or "")
        split = str(record.get("split") or "")
        previous_split = first_split_by_request.get(request)
        if previous_split and previous_split != split:
            suffix = f" Use trace id {record['control_id']} for this benchmark item."
            request = f"{request}{suffix}"
            record["user_request"] = request
            record["question"] = request
        first_split_by_request.setdefault(request, split)
        adjusted.append(record)
    return adjusted


def _sample_arguments(tool: Dict[str, Any] | None, variant: int, *, include_optional: bool) -> Dict[str, Any]:
    if not tool:
        return {}
    args: Dict[str, Any] = {}
    arguments = list(tool.get("arguments") or [])
    for index, arg in enumerate(arguments):
        if not arg.get("required") and not (include_optional and index < 2):
            continue
        args[arg["name"]] = _sample_value(arg, variant)
    return args


def _sample_value(arg: Dict[str, Any], variant: int) -> Any:
    enum = arg.get("enum")
    if isinstance(enum, list) and enum:
        return enum[variant % len(enum)]
    arg_type = str(arg.get("type") or "string")
    name = str(arg.get("name") or "value").lower()
    if arg_type in {"integer", "number", "float"}:
        if any(marker in name for marker in ("limit", "count", "head", "tail", "top", "max")):
            return [3, 5, 10, 20, 50][variant % 5]
        if "year" in name:
            return 2026
        return variant + 1
    if arg_type == "boolean":
        return variant % 2 == 0
    if arg_type == "array":
        return [_sample_array_item(arg, variant)]
    if arg_type == "object":
        return _sample_object(arg, variant)
    if "path" in name or "file" in name:
        return f"docs/control_{variant}.md"
    if "dir" in name or "folder" in name:
        return "docs"
    if "content" in name or "text" in name or "body" in name:
        return f"ReliaSkill control note {variant}"
    if "pattern" in name or "glob" in name:
        return "**/*.md"
    if "query" in name or "search" in name:
        return "reliability evaluation"
    if "city" in name or "location" in name:
        return "Boston"
    if "timezone" in name or name == "tz":
        return "America/New_York"
    if "url" in name or "uri" in name:
        return "https://example.com/resource"
    if "email" in name:
        return "researcher@example.com"
    if "id" in name:
        return f"item-{variant}"
    return f"{name}_{variant}"


def _sample_array_item(arg: Dict[str, Any], variant: int) -> Any:
    items_type = str(arg.get("items_type") or "string")
    if items_type in {"integer", "number", "float"}:
        return variant + 1
    if items_type == "boolean":
        return True
    return f"item_{variant}"


def _sample_object(arg: Dict[str, Any], variant: int) -> Dict[str, Any]:
    properties = arg.get("properties") if isinstance(arg.get("properties"), dict) else {}
    required = set(arg.get("required_properties") or [])
    payload: Dict[str, Any] = {}
    for name, schema in properties.items():
        if required and name not in required:
            continue
        child = {
            "name": name,
            "type": schema.get("type", "string") if isinstance(schema, dict) else "string",
            "enum": schema.get("enum") if isinstance(schema, dict) else None,
        }
        payload[name] = _sample_value(child, variant)
    return payload or {"value": f"object_{variant}"}


def _format_args(args: Dict[str, Any]) -> str:
    if not args:
        return "no arguments"
    return ", ".join(f"{key}={json.dumps(value, ensure_ascii=False)}" for key, value in sorted(args.items()))


def _positive_templates(split: str) -> List[str]:
    if split == "dev":
        return [
            "Use {title} to {purpose}. Set {args}.",
            "I need to {purpose}; call {title} with {args}.",
        ]
    return [
        "Please invoke {title} for this target use case: {purpose}. Arguments: {args}.",
        "For the task to {purpose}, the correct tool is {title}; use {args}.",
        "Run {title} so we can {purpose}. Use {args}.",
    ]


def write_controls_outputs(config: Dict[str, Any], controls: Sequence[Dict[str, Any]]) -> Dict[str, str]:
    outputs = config["outputs"]
    dev = [item for item in controls if item["split"] == "dev"]
    test = [item for item in controls if item["split"] == "test"]
    _write_jsonl(outputs["dev"], dev)
    _write_jsonl(outputs["test"], test)
    write_control_stats(outputs["stats"], controls)
    write_control_difficulty_stats(outputs["difficulty_stats"], controls)
    write_negative_category_stats(outputs["negative_category_stats"], controls)
    return {key: str(value) for key, value in outputs.items()}


def write_control_stats(path: str | Path, controls: Sequence[Dict[str, Any]]) -> None:
    grouped: Dict[tuple[str, str, bool], List[Dict[str, Any]]] = defaultdict(list)
    for control in controls:
        grouped[(control["split"], control["category"], bool(control["should_trigger"]))].append(control)
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["split", "category", "should_trigger", "control_count", "tool_count"]
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for (split, category, should_trigger), items in sorted(grouped.items()):
            writer.writerow(
                {
                    "split": split,
                    "category": category,
                    "should_trigger": should_trigger,
                    "control_count": len(items),
                    "tool_count": len({item.get("tool_key") or item["tool_name"] for item in items}),
                }
            )


def write_control_difficulty_stats(path: str | Path, controls: Sequence[Dict[str, Any]]) -> None:
    grouped: Dict[tuple[str, str, str, bool], List[Dict[str, Any]]] = defaultdict(list)
    for control in controls:
        grouped[
            (
                str(control.get("split") or "unknown"),
                str(control.get("difficulty") or "unknown"),
                str(control.get("control_family") or "unknown"),
                bool(control.get("should_trigger")),
            )
        ].append(control)
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["split", "difficulty", "control_family", "should_trigger", "control_count", "tool_count"]
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for (split, difficulty, family, should_trigger), items in sorted(grouped.items()):
            writer.writerow(
                {
                    "split": split,
                    "difficulty": difficulty,
                    "control_family": family,
                    "should_trigger": should_trigger,
                    "control_count": len(items),
                    "tool_count": len({item.get("tool_key") or item["tool_name"] for item in items}),
                }
            )


def write_negative_category_stats(path: str | Path, controls: Sequence[Dict[str, Any]]) -> None:
    negatives = [control for control in controls if not bool(control.get("should_trigger"))]
    grouped: Dict[tuple[str, str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    for control in negatives:
        grouped[
            (
                str(control.get("split") or "unknown"),
                str(control.get("difficulty") or "unknown"),
                str(control.get("negative_category") or control.get("category") or "unknown"),
                str(control.get("expected_failure_mode") or "unknown"),
            )
        ].append(control)
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["split", "difficulty", "negative_category", "expected_failure_mode", "control_count", "tool_count", "alternative_tool_count"]
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for (split, difficulty, category, failure_mode), items in sorted(grouped.items()):
            writer.writerow(
                {
                    "split": split,
                    "difficulty": difficulty,
                    "negative_category": category,
                    "expected_failure_mode": failure_mode,
                    "control_count": len(items),
                    "tool_count": len({item.get("tool_key") or item["tool_name"] for item in items}),
                    "alternative_tool_count": sum(1 for item in items if item.get("alternative_valid_tools")),
                }
            )


def summarize_controls(controls: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    per_tool = defaultdict(lambda: Counter({"positive": 0, "negative": 0}))
    for control in controls:
        bucket = "positive" if control["should_trigger"] else "negative"
        per_tool[control.get("tool_key") or control["tool_name"]][bucket] += 1
    min_positive = min((counts["positive"] for counts in per_tool.values()), default=0)
    min_negative = min((counts["negative"] for counts in per_tool.values()), default=0)
    return {
        "controls": len(controls),
        "tools": len(per_tool),
        "dev_controls": sum(1 for item in controls if item["split"] == "dev"),
        "test_controls": sum(1 for item in controls if item["split"] == "test"),
        "min_positive_per_tool": min_positive,
        "min_negative_per_tool": min_negative,
        "categories": dict(sorted(Counter(item["category"] for item in controls).items())),
        "difficulties": dict(sorted(Counter(str(item.get("difficulty") or "unknown") for item in controls).items())),
        "families": dict(sorted(Counter(str(item.get("control_family") or "unknown") for item in controls).items())),
    }


def _write_jsonl(path: str | Path, records: Iterable[Dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _tool_title(tool: Dict[str, Any]) -> str:
    return str(tool.get("tool_name") or "tool").replace("_", " ")


def _purpose_fragment(tool: Dict[str, Any] | None) -> str:
    if not tool:
        return "handle the request"
    purpose = str(tool.get("tool_purpose") or tool.get("summary") or tool.get("tool_name") or "handle the request")
    purpose = " ".join(purpose.split())
    if not purpose:
        return "handle the request"
    return purpose[:140].rstrip(" .,")


def _domain(tool: Dict[str, Any]) -> str:
    metadata = tool.get("source_metadata") if isinstance(tool.get("source_metadata"), dict) else {}
    return str(metadata.get("domain") or tool.get("domain") or "unknown")


def _side_effect(tool: Dict[str, Any]) -> str:
    metadata = tool.get("source_metadata") if isinstance(tool.get("source_metadata"), dict) else {}
    side_effect = metadata.get("side_effect_type") or tool.get("side_effect_type")
    if side_effect:
        return str(side_effect)
    hints = " ".join(str(item) for item in tool.get("side_effect_hints") or [])
    if any(marker in hints for marker in ("write", "create", "update")):
        return "write"
    if "delete" in hints:
        return "delete"
    return "unknown"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return slug[:80] or "tool"


def _tool_key(tool: Dict[str, Any]) -> str:
    return f"{tool.get('server_name') or 'unknown'}::{tool.get('tool_name') or 'unknown'}"

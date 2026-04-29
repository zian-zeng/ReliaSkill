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
    if int(config.get("positive_controls_per_tool", 0)) < 3:
        raise ValueError("positive_controls_per_tool must be at least 3.")
    if len(config.get("negative_categories") or []) < 3:
        raise ValueError("At least 3 negative categories are required.")
    return config


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
    positive_count = int(config["positive_controls_per_tool"])
    negative_categories = [str(item) for item in config.get("negative_categories") or []]
    controls: List[Dict[str, Any]] = []
    for tool_index, tool in enumerate(tools):
        controls.extend(_positive_controls(tool, tool_index, positive_count, seed))
        for category_index, category in enumerate(negative_categories):
            controls.append(_negative_control(tool, tools, tool_index, category_index, category, seed))
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
) -> Dict[str, Any]:
    record = {
        "id": control_id,
        "task_id": control_id,
        "function": tool["tool_name"],
        "tool_name": tool["tool_name"],
        "question": user_request,
        "user_request": user_request,
        "category": category,
        "gold_tool": gold_tool,
        "gold_args": gold_args,
        "ground_truth": {"arguments": gold_args},
        "expected_arguments": gold_args,
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

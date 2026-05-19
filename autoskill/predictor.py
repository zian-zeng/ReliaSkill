from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Any, Dict

from autoskill.conditions import is_reliaskill_v1_family
from autoskill.eval_types import EvalPrediction, EvalTask
from autoskill.exposure import render_exposure
from autoskill.ir import ArgumentIR, GeneratedSkill, ToolIR
from autoskill.json_output import parse_json_object_output
from autoskill.local_model import LocalHFChatRunner
from autoskill.prompting import build_prediction_prompt
from autoskill.contracts import build_contract_failure_report, compile_skill_contract, evaluate_skill_contract
from autoskill.routing_boundaries import detect_routing_abstention, tool_name_variants
from autoskill.schema_utils import normalize_schema_node, schema_type


RELIASKILL_V1_RUNTIME_CONDITIONS = {"reliaskill_v1", "reliaskill_challenger_v1"}


def _extract_number(text: str) -> int | None:
    match = re.search(r"\b(\d+)\b", text)
    return int(match.group(1)) if match else None


def _extract_quoted_or_tail(text: str) -> str:
    quoted = re.search(r'"([^"]+)"', text)
    if quoted:
        return quoted.group(1)
    tail = re.search(r"\bfor\b(.+)", text, flags=re.IGNORECASE)
    if tail:
        return tail.group(1).strip(" .")
    return text.strip(" .")


def _extract_query_from_request(text: str) -> str | None:
    quoted = re.search(r'"([^"]+)"', text)
    if quoted:
        return quoted.group(1)
    patterns = (
        r"\bquery\s*(?:=|:)\s*([^,.;]+)",
        r"\b(?:search|find|lookup|look up)\s+(?:for\s+)?([^,.;]+)",
        r"\b(?:about|matching|containing)\s+([^,.;]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = match.group(1).strip(" .\"'`")
            if value:
                return value
    return None


def _extract_path_from_request(text: str) -> str | None:
    patterns = [
        r"\b(?:of|inside|in|under|within)\s+(?:the\s+)?([A-Za-z0-9_./*-]+?)(?:\s+directory\b|\s+folder\b|\s+using\b|\s+with\b|\s+for\b|$)",
        r"\b(?:read|open|show)\s+([A-Za-z0-9_./-]+\.[A-Za-z0-9_*?-]+)\b",
        r"\bcreate\s+(?:the\s+)?directory\s+([A-Za-z0-9_./-]+)",
        r"\bcreate\s+(?:the\s+)?([A-Za-z0-9_./-]+)\s+(?:directory|folder)\b",
        r"\bcreate\s+([A-Za-z0-9_./-]+)\s+containing",
        r"\b(?:save|write)\s+.+\s+to\s+([A-Za-z0-9_./-]+)$",
        r"\bensure\s+([A-Za-z0-9_./-]+)\s+exists\b",
        r"\b([A-Za-z0-9_./-]+\.[A-Za-z0-9_*?-]+)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip(" .")
    return None


def _extract_email_from_request(text: str) -> str | None:
    match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text)
    return match.group(0) if match else None


def _extract_url_from_request(text: str) -> str | None:
    match = re.search(r"\bhttps?://[^\s,.;]+", text)
    return match.group(0).rstrip(").]") if match else None


def _extract_date_from_request(text: str) -> str | None:
    match = re.search(r"\b\d{4}-\d{1,2}-\d{1,2}\b", text)
    if match:
        return match.group(0)
    match = re.search(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b", text)
    return match.group(0) if match else None


def _extract_datetime_from_request(text: str) -> str | None:
    match = re.search(r"\b\d{4}-\d{1,2}-\d{1,2}T\d{1,2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?\b", text)
    if match:
        return match.group(0)
    return _extract_date_from_request(text)


def _extract_content_from_request(text: str) -> str | None:
    for pattern in (
        r"\bcontaining the text\s+(.+)$",
        r"\bwith content\s+(.+)$",
        r'\b(?:save|write)\s+"([^"]+)"\s+to\s+[A-Za-z0-9_./-]+$',
    ):
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip().strip(".").strip('"')
    return None


def _extract_pattern_from_request(text: str) -> str | None:
    match = re.search(r"\bpattern\s+([A-Za-z0-9_./*?-]+)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip(" .")
    quoted = re.search(r'"([^"]*(?:\*|\?)[^"]*)"', text)
    if quoted:
        return quoted.group(1)
    return None


def _extract_exclude_patterns(text: str) -> list[str]:
    match = re.search(r"\b(?:exclude|ignore|skip)\s+([A-Za-z0-9_./*?\-, ]+)", text, flags=re.IGNORECASE)
    if not match:
        return []
    raw_value = match.group(1).strip(" .")
    parts = re.split(r"\s*(?:,|and)\s*", raw_value)
    return [part.strip(" .") for part in parts if part.strip(" .")]


def _example_overlap_score(request: str, scenario: str, arguments: Dict[str, Any]) -> int:
    request_tokens = set(re.findall(r"[a-z0-9_./*?-]+", request.lower()))
    scenario_tokens = set(re.findall(r"[a-z0-9_./*?-]+", scenario.lower()))
    argument_tokens = set(re.findall(r"[a-z0-9_./*?-]+", json.dumps(arguments, ensure_ascii=False).lower()))
    return len(request_tokens.intersection(scenario_tokens.union(argument_tokens)))


def _infer_from_examples(arg_name: str, request: str, skill: GeneratedSkill) -> Any:
    best_score = 0
    best_value = None
    for example in skill.examples:
        scenario = str(example.get("scenario", ""))
        arguments = example.get("arguments", {})
        if not isinstance(arguments, dict) or arg_name not in arguments:
            continue
        score = _example_overlap_score(request, scenario, arguments)
        if score > best_score:
            best_score = score
            best_value = arguments[arg_name]
    return best_value if best_score > 1 else None


def _request_has_directional_cue(request: str, cues: tuple[str, ...]) -> bool:
    lowered = request.lower()
    return any(cue in lowered for cue in cues)


def _should_skip_example_inference(arg_name: str, request: str, skill: GeneratedSkill) -> bool:
    if not skill.semantic_hints:
        return False
    if arg_name == "tail":
        return _request_has_directional_cue(request, ("top", "first", "beginning", "opening", "start of"))
    if arg_name == "head":
        return _request_has_directional_cue(request, ("bottom", "last", "trailing", "ending", "end of"))
    return False


def _infer_semantic_hint_value(tool: ToolIR, arg_name: str, request: str, skill: GeneratedSkill) -> Any:
    lowered = request.lower()
    semantic_spec = skill.semantic_hints.get(arg_name)

    if isinstance(semantic_spec, dict):
        number = _extract_number(lowered)
        for cue, mapped_value in semantic_spec.items():
            if cue not in lowered:
                continue
            if mapped_value == "__number__" and number is not None:
                return number
            if mapped_value == "__paths__":
                extracted = _extract_exclude_patterns(request)
                if extracted:
                    return extracted
            if mapped_value == "__tail_text__":
                extracted = _extract_content_from_request(request)
                if extracted is not None:
                    return extracted
            if mapped_value == "__quoted_text_to_path__":
                extracted = _extract_content_from_request(request)
                if extracted is not None:
                    return extracted
            if mapped_value not in {"__number__", "__paths__", "__tail_text__", "__quoted_text_to_path__"}:
                return mapped_value

    return None


def _infer_argument_value(arg_name: str, request: str, skill: GeneratedSkill) -> Any:
    lowered = request.lower()
    if arg_name == "city":
        for city in ("new york", "san francisco", "boston", "seattle", "london"):
            if city in lowered:
                return city.title()
        return None
    if arg_name == "unit":
        if "fahrenheit" in lowered or " f " in f" {lowered} ":
            return "F"
        if "celsius" in lowered or " centigrade" in lowered or " c " in f" {lowered} ":
            return "C"
        return skill.argument_template.get("unit")
    if arg_name == "include_forecast":
        return any(token in lowered for token in ("forecast", "next few hours", "outlook"))
    if arg_name == "query":
        return _extract_quoted_or_tail(request)
    if arg_name == "top_k":
        value = _extract_number(lowered)
        return value if value is not None else skill.argument_template.get("top_k")
    if arg_name == "path":
        return _extract_path_from_request(request)
    if arg_name == "head":
        if "first" in lowered:
            return _extract_number(lowered)
        return None
    if arg_name == "tail":
        if "last" in lowered:
            return _extract_number(lowered)
        return None
    if arg_name == "content":
        return _extract_content_from_request(request)
    if arg_name == "pattern":
        return _extract_pattern_from_request(request)
    if arg_name == "excludePatterns":
        extracted = _extract_exclude_patterns(request)
        return extracted if extracted else None
    return skill.argument_template.get(arg_name)


def _extract_explicit_argument_value(arg: ArgumentIR, request: str) -> Any:
    pattern = rf"\b{re.escape(arg.name)}\s*(?:=|:)\s*(\"[^\"]*\"|'[^']*'|`[^`]*`|\[[^\]]*\]|\{{[^}}]*\}}|[^,\s.;]+)"
    match = re.search(pattern, request, flags=re.IGNORECASE)
    if not match:
        return None
    raw_value = match.group(1).strip()
    if len(raw_value) >= 2 and raw_value[0] == raw_value[-1] and raw_value[0] in {"\"", "'", "`"}:
        raw_value = raw_value[1:-1]

    if arg.type in {"object", "array"}:
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError:
            return {} if arg.type == "object" else [raw_value]
        if arg.type == "object" and isinstance(parsed, dict):
            return parsed
        if arg.type == "array" and isinstance(parsed, list):
            return parsed
        return None
    if arg.type == "integer":
        try:
            return int(raw_value)
        except ValueError:
            return None
    if arg.type == "number":
        try:
            return float(raw_value)
        except ValueError:
            return None
    if arg.type == "boolean":
        lowered = raw_value.lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
        return None
    if arg.enum:
        for value in arg.enum:
            if str(value).lower() == raw_value.lower():
                return value
        return raw_value
    return raw_value


def _collect_prediction_metadata(skill: GeneratedSkill) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {}
    for entry in skill.method_trace:
        if not isinstance(entry, dict):
            continue
        if entry.get("retrieval_type"):
            metadata.setdefault("retrieval_events", []).append(entry)
            if "candidate_tools" in entry:
                metadata["retrieved_tool_candidates"] = list(entry.get("candidate_tools", []))
            if "target_tool_rank" in entry:
                metadata["retrieval_target_rank"] = entry.get("target_tool_rank")
            if "selected_tool_name" in entry:
                metadata["selected_tool_name"] = entry.get("selected_tool_name")
            if "retrieved_memory_names" in entry:
                metadata["retrieved_memory_names"] = list(entry.get("retrieved_memory_names", []))
    return metadata


def _quantization_label(*, load_in_4bit: bool = False, load_in_8bit: bool = False, torch_dtype: str | None = None) -> str:
    if load_in_4bit:
        return "4bit"
    if load_in_8bit:
        return "8bit"
    return str(torch_dtype or "none")


def _prediction_audit_metadata(
    *,
    skill: GeneratedSkill,
    prompt: str,
    raw_model_output: str,
    parsed_arguments: Dict[str, Any],
    backend_name: str,
    model_name: str,
    quantization: str = "none",
    should_call: bool = True,
    abstention_reason: str | None = None,
) -> Dict[str, Any]:
    return {
        **_collect_prediction_metadata(skill),
        "prompt_template": "build_prediction_prompt/v1",
        "raw_prompt": prompt,
        "raw_model_output": raw_model_output,
        "parsed_prediction": dict(parsed_arguments),
        "should_call": bool(should_call),
        "abstention_reason": abstention_reason,
        "model_name": model_name,
        "quantization": quantization,
        "predictor_backend": backend_name,
    }


def _parse_should_call(data: Dict[str, Any]) -> tuple[bool, str | None]:
    raw = data.get("should_call", data.get("triggered", True))
    if isinstance(raw, str):
        should_call = raw.strip().lower() not in {"false", "0", "no", "abstain", "do_not_call"}
    else:
        should_call = bool(raw)
    reason = data.get("abstention_reason")
    return should_call, str(reason) if reason is not None else None


def _coerce_predicted_arguments(data: Dict[str, Any]) -> tuple[Dict[str, Any], str | None]:
    raw_arguments = data.get("arguments", {})
    if raw_arguments is None:
        return {}, None
    if isinstance(raw_arguments, dict):
        return dict(raw_arguments), None
    return {}, f"`arguments` must be a JSON object, got {type(raw_arguments).__name__}."


def _uses_reliaskill_v1_runtime(skill: GeneratedSkill) -> bool:
    return skill.baseline_name in RELIASKILL_V1_RUNTIME_CONDITIONS or is_reliaskill_v1_family(skill.baseline_name)


def _contract_ablation_disabled(skill: GeneratedSkill, flag: str) -> bool:
    flags = skill.metadata.get("contract_ablation_flags") if isinstance(skill.metadata, dict) else None
    return bool(isinstance(flags, dict) and flags.get(flag) is True)


def _task_grounding_context(task: EvalTask) -> Dict[str, Any]:
    return {
        "conversation": list(task.conversation_history),
        "artifacts": dict(task.artifact_context),
        "tool_observations": list(task.tool_observation_context),
    }


def _task_grounding_text(task: EvalTask) -> str:
    parts = [task.user_request]
    for message in task.conversation_history:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role") or "message")
        content = str(message.get("content") or "")
        if content.strip():
            parts.append(f"{role}: {content}")
    if task.artifact_context:
        parts.append(json.dumps(task.artifact_context, ensure_ascii=False, sort_keys=True))
    for observation in task.tool_observation_context:
        if isinstance(observation, dict):
            parts.append(json.dumps(observation, ensure_ascii=False, sort_keys=True))
    return "\n".join(part for part in parts if part)


def _schema_for_argument(arg: ArgumentIR) -> Dict[str, Any]:
    schema: Dict[str, Any] = {"type": arg.type}
    if arg.enum:
        schema["enum"] = list(arg.enum)
    if arg.default is not None:
        schema["default"] = arg.default
    if arg.format:
        schema["format"] = arg.format
    if arg.type == "object" or arg.properties:
        schema["type"] = "object"
        schema["properties"] = arg.properties or {}
        schema["required"] = list(arg.required_properties)
    if arg.type == "array":
        schema["type"] = "array"
        schema["items"] = arg.items_schema if isinstance(arg.items_schema, dict) else {"type": arg.items_type or "string"}
    return schema


def _lift_nested_argument_fields(arguments: Dict[str, Any], tool: ToolIR, actions: list[str]) -> Dict[str, Any]:
    by_name = {arg.name: arg for arg in tool.arguments}
    object_args = {
        arg.name: arg
        for arg in tool.arguments
        if (arg.type == "object" or arg.properties) and isinstance(arg.properties, dict) and arg.properties
    }
    array_object_args = {
        arg.name: arg
        for arg in tool.arguments
        if arg.type == "array"
        and isinstance(arg.items_schema, dict)
        and schema_type(arg.items_schema) == "object"
        and isinstance(arg.items_schema.get("properties"), dict)
        and arg.items_schema.get("properties")
    }
    if not object_args and not array_object_args:
        return dict(arguments)

    lifted = dict(arguments)
    nested_updates: Dict[str, Dict[str, Any]] = {}
    array_item_updates: Dict[str, Dict[str, Any]] = {}
    consumed: set[str] = set()
    for key, value in arguments.items():
        if key in by_name:
            continue
        dotted = key.split(".", 1)
        if len(dotted) == 2 and dotted[0] in object_args and dotted[1] in (object_args[dotted[0]].properties or {}):
            nested_updates.setdefault(dotted[0], {})[dotted[1]] = value
            consumed.add(key)
            actions.append(f"lifted_nested_field:{key}->{dotted[0]}.{dotted[1]}")
            continue
        if len(dotted) == 2 and dotted[0] in array_object_args:
            item_properties = array_object_args[dotted[0]].items_schema.get("properties", {})  # type: ignore[union-attr]
            if dotted[1] in item_properties:
                array_item_updates.setdefault(dotted[0], {})[dotted[1]] = value
                consumed.add(key)
                actions.append(f"lifted_nested_array_item_field:{key}->{dotted[0]}[0].{dotted[1]}")
                continue
        owners = [
            arg_name
            for arg_name, arg in object_args.items()
            if key in (arg.properties or {})
        ]
        if len(owners) == 1:
            owner = owners[0]
            nested_updates.setdefault(owner, {})[key] = value
            consumed.add(key)
            actions.append(f"lifted_nested_field:{key}->{owner}.{key}")
            continue
        array_owners = [
            arg_name
            for arg_name, arg in array_object_args.items()
            if key in (arg.items_schema.get("properties", {}) if isinstance(arg.items_schema, dict) else {})
        ]
        if len(array_owners) == 1:
            owner = array_owners[0]
            array_item_updates.setdefault(owner, {})[key] = value
            consumed.add(key)
            actions.append(f"lifted_nested_array_item_field:{key}->{owner}[0].{key}")

    for key in consumed:
        lifted.pop(key, None)
    for arg_name, updates in nested_updates.items():
        existing = lifted.get(arg_name)
        if isinstance(existing, dict):
            lifted[arg_name] = {**updates, **existing}
        elif existing is None or not isinstance(existing, dict):
            lifted[arg_name] = updates
            if existing is not None:
                actions.append(f"replaced_invalid_nested_container:{arg_name}")
    for arg_name, updates in array_item_updates.items():
        existing = lifted.get(arg_name)
        if isinstance(existing, list) and existing and isinstance(existing[0], dict):
            lifted[arg_name] = [{**updates, **existing[0]}, *existing[1:]]
        elif existing is None or not isinstance(existing, list):
            lifted[arg_name] = [updates]
            if existing is not None:
                actions.append(f"replaced_invalid_nested_array_container:{arg_name}")
    return lifted


def _sanitize_value_for_schema(value: Any, schema: Dict[str, Any], path: str, actions: list[str]) -> tuple[Any, list[str]]:
    schema, _ = normalize_schema_node(schema)
    kind = schema_type(schema)
    issues: list[str] = []

    if value is None:
        return None, issues

    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and enum_values:
        if value in enum_values:
            pass
        else:
            canonical = next((item for item in enum_values if str(item).lower() == str(value).lower()), None)
            if canonical is None:
                issues.append(f"{path}:invalid_enum")
                return None, issues
            actions.append(f"canonicalized_enum:{path}")
            value = canonical

    if kind == "string":
        if isinstance(value, str):
            string_issues = _validate_string_contract(value, schema, path)
            if string_issues:
                issues.extend(string_issues)
                return None, issues
            return value, issues
        if isinstance(value, (int, float, bool)):
            actions.append(f"coerced_string:{path}")
            value = str(value)
            string_issues = _validate_string_contract(value, schema, path)
            if string_issues:
                issues.extend(string_issues)
                return None, issues
            return value, issues
        issues.append(f"{path}:type_mismatch")
        return None, issues

    if kind == "integer":
        if isinstance(value, int) and not isinstance(value, bool):
            return value, issues
        if isinstance(value, str):
            try:
                actions.append(f"coerced_integer:{path}")
                return int(value), issues
            except ValueError:
                pass
        issues.append(f"{path}:type_mismatch")
        return None, issues

    if kind == "number":
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value, issues
        if isinstance(value, str):
            try:
                actions.append(f"coerced_number:{path}")
                return float(value), issues
            except ValueError:
                pass
        issues.append(f"{path}:type_mismatch")
        return None, issues

    if kind == "boolean":
        if isinstance(value, bool):
            return value, issues
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes"}:
                actions.append(f"coerced_boolean:{path}")
                return True, issues
            if lowered in {"false", "0", "no"}:
                actions.append(f"coerced_boolean:{path}")
                return False, issues
        issues.append(f"{path}:type_mismatch")
        return None, issues

    if kind == "object":
        if not isinstance(value, dict):
            issues.append(f"{path}:type_mismatch")
            return None, issues
        properties = schema.get("properties", {}) or {}
        required = [str(item) for item in schema.get("required", []) or []]
        sanitized: Dict[str, Any] = {}
        for key, child_value in value.items():
            if key not in properties:
                actions.append(f"dropped_unsupported_field:{path}.{key}")
                continue
            child, child_issues = _sanitize_value_for_schema(child_value, properties[key], f"{path}.{key}", actions)
            issues.extend(child_issues)
            if child is not None:
                sanitized[key] = child
        for key in required:
            if key not in sanitized:
                child_schema = properties.get(key, {}) if isinstance(properties, dict) else {}
                if isinstance(child_schema, dict) and "default" in child_schema:
                    sanitized[key] = child_schema["default"]
                    actions.append(f"filled_default:{path}.{key}")
                else:
                    issues.append(f"{path}.{key}:missing_required")
        return sanitized, issues

    if kind == "array":
        if not isinstance(value, list):
            issues.append(f"{path}:type_mismatch")
            return None, issues
        min_items = schema.get("minItems")
        max_items = schema.get("maxItems")
        if isinstance(min_items, int) and len(value) < min_items:
            issues.append(f"{path}:min_items")
            return None, issues
        if isinstance(max_items, int) and len(value) > max_items:
            issues.append(f"{path}:max_items")
            return None, issues
        item_schema = schema.get("items", {}) or {}
        sanitized_items = []
        for index, item in enumerate(value):
            sanitized_item, item_issues = _sanitize_value_for_schema(item, item_schema, f"{path}[{index}]", actions)
            issues.extend(item_issues)
            if sanitized_item is not None:
                sanitized_items.append(sanitized_item)
        return sanitized_items, issues

    return value, issues


def _validate_string_contract(value: str, schema: Dict[str, Any], path: str) -> list[str]:
    issues: list[str] = []
    fmt = str(schema.get("format") or "").lower()
    if fmt == "email" and not re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", value):
        issues.append(f"{path}:invalid_format")
    if fmt in {"uri", "url"} and not re.match(r"^https?://[^\s]+$", value):
        issues.append(f"{path}:invalid_format")
    if fmt == "date" and not re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", value):
        issues.append(f"{path}:invalid_format")
    if fmt == "date-time" and not re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}T\d{1,2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?", value):
        issues.append(f"{path}:invalid_format")
    pattern = schema.get("pattern")
    if isinstance(pattern, str):
        try:
            if not re.search(pattern, value):
                issues.append(f"{path}:pattern_mismatch")
        except re.error:
            pass
    min_length = schema.get("minLength")
    max_length = schema.get("maxLength")
    if isinstance(min_length, int) and len(value) < min_length:
        issues.append(f"{path}:min_length")
    if isinstance(max_length, int) and len(value) > max_length:
        issues.append(f"{path}:max_length")
    return issues


def _grounded_required_value(tool: ToolIR, arg: ArgumentIR, request: str, skill: GeneratedSkill) -> Any:
    explicit = _extract_explicit_argument_value(arg, request)
    if explicit is not None:
        return explicit
    structured = _grounded_structured_value(arg, request)
    if structured is not None:
        return structured
    hinted = _infer_semantic_hint_value(tool, arg.name, request, skill)
    if hinted is not None:
        return hinted
    lowered = request.lower()
    if arg.name == "query":
        return _extract_query_from_request(request)
    if arg.name == "path":
        return _extract_path_from_request(request)
    if arg.name == "content":
        return _extract_content_from_request(request)
    if arg.name == "pattern":
        return _extract_pattern_from_request(request)
    if arg.name == "excludePatterns":
        extracted = _extract_exclude_patterns(request)
        return extracted if extracted else None
    if arg.format == "email" or "email" in arg.name.lower():
        return _extract_email_from_request(request)
    if arg.format in {"uri", "url"} or any(token in arg.name.lower() for token in ("url", "uri", "link")):
        return _extract_url_from_request(request)
    if arg.format == "date-time" or ("date" in arg.name.lower() and "time" in arg.name.lower()):
        return _extract_datetime_from_request(request)
    if arg.format == "date" or "date" in arg.name.lower():
        return _extract_date_from_request(request)
    if arg.type in {"integer", "number"}:
        return _extract_number(lowered)
    if arg.enum:
        for value in arg.enum:
            if str(value).lower() in lowered:
                return value
    return None


def _grounded_structured_value(arg: ArgumentIR, request: str) -> Any:
    if (arg.type == "object" or arg.properties) and isinstance(arg.properties, dict) and arg.properties:
        required = list(arg.required_properties) or list(arg.properties.keys())
        value: Dict[str, Any] = {}
        for child_name in required:
            child_schema = arg.properties.get(child_name, {})
            child_value = _extract_schema_property_value(child_name, child_schema, request)
            if child_value is None:
                return None
            value[child_name] = child_value
        return value

    if arg.type == "array" and isinstance(arg.items_schema, dict) and schema_type(arg.items_schema) == "object":
        properties = arg.items_schema.get("properties")
        if not isinstance(properties, dict) or not properties:
            return None
        required = list(arg.items_schema.get("required") or arg.items_schema.get("required_properties") or properties.keys())
        item: Dict[str, Any] = {}
        for child_name in required:
            child_value = _extract_schema_property_value(child_name, properties.get(child_name, {}), request)
            if child_value is None:
                return None
            item[child_name] = child_value
        return [item]
    return None


def _extract_schema_property_value(name: str, schema: Any, request: str) -> Any:
    schema = schema if isinstance(schema, dict) else {}
    kind = schema_type(schema)
    explicit = _extract_named_value(name, request)
    if explicit is not None:
        return _coerce_extracted_value(explicit, kind)

    lowered = request.lower()
    enum_values = schema.get("enum")
    if isinstance(enum_values, list):
        for value in enum_values:
            if str(value).lower() in lowered:
                return value

    parts = _name_parts(name)
    if kind in {"integer", "number"}:
        return _extract_number_for_name(name, request)
    if kind == "boolean":
        if re.search(rf"\b{re.escape(name)}\b", request, flags=re.IGNORECASE):
            if any(token in lowered for token in ("false", "no", "disabled", "off")):
                return False
            if any(token in lowered for token in ("true", "yes", "enabled", "on")):
                return True
        return None
    if kind == "array":
        quoted_values = re.findall(r'"([^"]+)"', request)
        if quoted_values and parts.intersection({"content", "contents", "text", "message", "items", "values"}):
            return quoted_values
        return None
    if schema.get("format") == "email" or parts.intersection({"email", "recipient"}):
        return _extract_email_from_request(request)
    if schema.get("format") in {"uri", "url"} or parts.intersection({"url", "uri", "link", "website"}):
        return _extract_url_from_request(request)
    if schema.get("format") == "date-time" or parts.intersection({"datetime"}):
        return _extract_datetime_from_request(request)
    if schema.get("format") == "date" or parts.intersection({"date"}):
        return _extract_date_from_request(request)
    if parts.intersection({"start", "begin", "from", "since", "after"}):
        return _extract_temporal_value(request, start=True)
    if parts.intersection({"end", "until", "before", "to"}):
        return _extract_temporal_value(request, start=False)
    if parts.intersection({"content", "contents", "text", "body", "message", "payload", "value"}):
        return _extract_content_from_request(request) or _extract_first_quoted(request)
    if parts.intersection({"query", "search", "pattern"}):
        return _extract_query_from_request(request) or _extract_pattern_from_request(request)
    if parts.intersection({"path", "file", "filename", "directory", "folder"}):
        return _extract_path_from_request(request)
    if parts.intersection({"name", "entity", "user", "person", "title"}):
        return _extract_named_entity_like_value(name, request)
    return None


def _extract_named_value(name: str, request: str) -> str | None:
    pattern = rf"\b{re.escape(name)}\s*(?:=|:)\s*(\"[^\"]*\"|'[^']*'|`[^`]*`|\[[^\]]*\]|\{{[^}}]*\}}|[^,\s.;]+)"
    match = re.search(pattern, request, flags=re.IGNORECASE)
    if not match:
        return None
    raw_value = match.group(1).strip()
    if len(raw_value) >= 2 and raw_value[0] == raw_value[-1] and raw_value[0] in {"\"", "'", "`"}:
        raw_value = raw_value[1:-1]
    return raw_value


def _coerce_extracted_value(raw_value: str, kind: str) -> Any:
    if kind == "array":
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError:
            return [raw_value]
        return parsed if isinstance(parsed, list) else [parsed]
    if kind == "object":
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    if kind == "integer":
        try:
            return int(raw_value)
        except ValueError:
            return None
    if kind == "number":
        try:
            return float(raw_value)
        except ValueError:
            return None
    if kind == "boolean":
        lowered = raw_value.lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
        return None
    return raw_value


def _extract_number_for_name(name: str, request: str) -> int | float | None:
    raw = _extract_named_value(name, request)
    if raw is not None:
        try:
            return int(raw)
        except ValueError:
            try:
                return float(raw)
            except ValueError:
                return None
    return None


def _extract_temporal_value(request: str, *, start: bool) -> str | None:
    explicit_names = ("start", "from", "since", "after", "begin") if start else ("end", "to", "until", "before")
    for name in explicit_names:
        value = _extract_named_value(name, request)
        if value:
            return value
    pattern = r"\b(?:from|since|after|starting)\s+([^,.;]+?)\s+(?:to|until|before|through|ending)\s+([^,.;]+)"
    match = re.search(pattern, request, flags=re.IGNORECASE)
    if match:
        return match.group(1 if start else 2).strip(" .\"'`")
    dates = re.findall(r"\b\d{4}-\d{1,2}-\d{1,2}\b|\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b", request)
    if dates:
        return dates[0] if start else (dates[1] if len(dates) > 1 else None)
    return None


def _extract_first_quoted(request: str) -> str | None:
    match = re.search(r'"([^"]+)"', request)
    return match.group(1) if match else None


def _extract_named_entity_like_value(name: str, request: str) -> str | None:
    explicit = _extract_named_value(name, request)
    if explicit:
        return explicit
    quoted = _extract_first_quoted(request)
    if quoted:
        return quoted
    match = re.search(r"\b(?:for|to|about|named)\s+([A-Z][A-Za-z0-9_-]{1,})\b", request)
    if match:
        return match.group(1)
    return None


def _required_argument_value_is_grounded(tool: ToolIR, arg: ArgumentIR, request: str, skill: GeneratedSkill, value: Any) -> bool:
    explicit = _extract_explicit_argument_value(arg, request)
    if explicit is not None and _values_overlap(explicit, value):
        return True
    grounded = _grounded_required_value(tool, arg, request, skill)
    if grounded is not None and _values_overlap(grounded, value):
        return True
    return _field_or_value_grounded(arg.name, value, request)


def _grounded_required_arguments(tool: ToolIR, request: str, skill: GeneratedSkill, actions: list[str]) -> tuple[Dict[str, Any], list[str]]:
    grounded_arguments: Dict[str, Any] = {}
    issues: list[str] = []
    for arg in tool.arguments:
        if not arg.required:
            continue
        grounded = _grounded_required_value(tool, arg, request, skill)
        if grounded is None:
            issues.append(f"{arg.name}:missing_required")
            continue
        sanitized, value_issues = _sanitize_value_for_schema(grounded, _schema_for_argument(arg), arg.name, actions)
        issues.extend(value_issues)
        if sanitized is None:
            issues.append(f"{arg.name}:missing_required")
            continue
        grounded_arguments[arg.name] = _prune_ungrounded_schema_optionals(sanitized, _schema_for_argument(arg), arg.name, request, actions)
    return grounded_arguments, issues


def _has_direct_action_intent(request: str) -> bool:
    lowered = request.lower()
    if re.search(r"\b(?:explain|describe|what is|what are|why|how would|how do i|tutorial|documentation)\b", lowered):
        return False
    return bool(
        re.search(
            r"\b(?:use|call|run|search|find|lookup|look up|read|open|show|list|get|fetch|create|add|update|delete|remove|write|save|send|calculate|compute|convert|summarize|draft|record)\b",
            lowered,
        )
    )


def _can_rescue_grounded_abstention(
    tool: ToolIR,
    skill: GeneratedSkill,
    action_request: str,
    grounding_request: str,
    actions: list[str],
) -> tuple[bool, Dict[str, Any], list[str]]:
    required = [arg for arg in tool.arguments if arg.required]
    if not required or not _has_direct_action_intent(action_request):
        return False, {}, []
    grounded_arguments, issues = _grounded_required_arguments(tool, grounding_request, skill, actions)
    blocking = [issue for issue in issues if issue.endswith(":missing_required") or issue.endswith(":type_mismatch") or issue.endswith(":invalid_enum")]
    if blocking:
        return False, {}, blocking
    if set(grounded_arguments) != {arg.name for arg in required}:
        return False, grounded_arguments, []
    return True, grounded_arguments, []


def _optional_argument_is_grounded(tool: ToolIR, arg: ArgumentIR, request: str, skill: GeneratedSkill, value: Any) -> bool:
    if _extract_explicit_argument_value(arg, request) is not None:
        return True
    hinted = _infer_semantic_hint_value(tool, arg.name, request, skill)
    if hinted is not None and _values_overlap(hinted, value):
        return True
    extracted = _grounded_optional_value(tool, arg, request, skill)
    if extracted is not None and _values_overlap(extracted, value):
        return True
    return _field_or_value_grounded(arg.name, value, request)


def _grounded_optional_value(tool: ToolIR, arg: ArgumentIR, request: str, skill: GeneratedSkill) -> Any:
    lowered = request.lower()
    if arg.name == "query":
        return _extract_query_from_request(request)
    if arg.name == "path":
        return _extract_path_from_request(request)
    if arg.name == "content":
        return _extract_content_from_request(request)
    if arg.name == "pattern":
        return _extract_pattern_from_request(request)
    if arg.name == "excludePatterns":
        extracted = _extract_exclude_patterns(request)
        return extracted if extracted else None
    if arg.format == "email" or "email" in arg.name.lower():
        return _extract_email_from_request(request)
    if arg.format in {"uri", "url"} or any(token in arg.name.lower() for token in ("url", "uri", "link")):
        return _extract_url_from_request(request)
    if arg.format == "date-time" or ("date" in arg.name.lower() and "time" in arg.name.lower()):
        return _extract_datetime_from_request(request)
    if arg.format == "date" or "date" in arg.name.lower():
        return _extract_date_from_request(request)
    if arg.type in {"integer", "number"}:
        return _extract_number(lowered)
    if arg.enum:
        for enum_value in arg.enum:
            if str(enum_value).lower() in lowered:
                return enum_value
    return None


def _field_or_value_grounded(field_name: str, value: Any, request: str) -> bool:
    lowered = request.lower()
    tokens = set(re.findall(r"[a-z0-9_./*?-]+", lowered))
    name_parts = _name_parts(field_name)
    field_name_grounded = any(part in tokens or part in lowered for part in name_parts)
    value_grounded = _value_mentions_request(value, lowered)
    if isinstance(value, bool):
        return field_name_grounded
    return value_grounded or (field_name_grounded and not _has_nonempty_leaf_value(value))


def _name_parts(name: str) -> set[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return {part.lower() for part in re.split(r"[^A-Za-z0-9]+", spaced) if len(part) > 2}


def _has_nonempty_leaf_value(value: Any) -> bool:
    return any(str(leaf).strip() for leaf in _leaf_values(value) if leaf is not None)


def _leaf_values(value: Any) -> list[Any]:
    if isinstance(value, dict):
        result: list[Any] = []
        for child in value.values():
            result.extend(_leaf_values(child))
        return result
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(_leaf_values(item))
        return result
    return [value]


def _value_mentions_request(value: Any, lowered_request: str) -> bool:
    for leaf in _leaf_values(value):
        if leaf is None or isinstance(leaf, bool):
            continue
        text = str(leaf).strip().lower()
        if len(text) <= 1:
            continue
        if text in lowered_request:
            return True
    return False


def _values_overlap(left: Any, right: Any) -> bool:
    left_values = {str(item).strip().lower() for item in _leaf_values(left) if item is not None}
    right_values = {str(item).strip().lower() for item in _leaf_values(right) if item is not None}
    return bool(left_values and right_values and left_values.intersection(right_values))


def _prune_ungrounded_schema_optionals(
    value: Any,
    schema: Dict[str, Any],
    path: str,
    request: str,
    actions: list[str],
) -> Any:
    schema, _ = normalize_schema_node(schema)
    kind = schema_type(schema)
    if kind == "object" and isinstance(value, dict):
        properties = schema.get("properties", {}) or {}
        required = {str(item) for item in schema.get("required", []) or []}
        pruned: Dict[str, Any] = {}
        for key, child_value in value.items():
            child_schema = properties.get(key, {}) if isinstance(properties, dict) else {}
            child_path = f"{path}.{key}"
            if key not in required and not _field_or_value_grounded(str(key), child_value, request):
                actions.append(f"dropped_ungrounded_optional:{child_path}")
                continue
            pruned[key] = _prune_ungrounded_schema_optionals(child_value, child_schema, child_path, request, actions)
        return pruned
    if kind == "array" and isinstance(value, list):
        item_schema = schema.get("items", {}) or {}
        return [
            _prune_ungrounded_schema_optionals(item, item_schema, f"{path}[{index}]", request, actions)
            for index, item in enumerate(value)
        ]
    return value


def _reliaskill_v1_boundary_reason(tool: ToolIR, skill: GeneratedSkill, request: str) -> str | None:
    explicit = detect_routing_abstention(request)
    if explicit:
        return explicit
    lowered = request.lower()
    for tool_phrase in tool_name_variants(tool):
        if f"do not use {tool_phrase}" in lowered or f"do not call {tool_phrase}" in lowered:
            return "explicit_target_tool_forbidden"
        if f"without using {tool_phrase}" in lowered:
            return "explicit_target_tool_forbidden"
        if f"{tool_phrase} is a distractor" in lowered or f"{tool_phrase} should not be called" in lowered:
            return "explicit_target_tool_forbidden"
    if "only want a checklist" in lowered or "planning only" in lowered or "no tool call" in lowered:
        return "planning_or_no_tool_request"
    if re.search(
        r"\b(?:send|provide|give|share)\s+(?:the\s+)?(?:query|path|input|details|fields|arguments?)\s+(?:later|after|when)\b",
        lowered,
    ) or re.search(
        r"\b(?:later|after|when)\b.*\b(?:send|provide|give|share)\s+(?:the\s+)?(?:query|path|input|details|fields|arguments?)\b",
        lowered,
    ):
        return "missing_required_information"
    if _request_tool_action_conflict(request, tool):
        return "action_intent_conflict"
    return _heuristic_abstention_reason(request, skill)


PREDICTOR_ACTION_FAMILIES: Dict[str, set[str]] = {
    "search": {"search", "find", "lookup", "query", "match", "filter"},
    "read": {"read", "open", "show", "view", "preview", "list", "get", "fetch", "retrieve"},
    "create": {"create", "add", "insert", "new", "draft", "schedule", "record"},
    "update": {"update", "edit", "modify", "patch", "change", "append", "write", "save"},
    "delete": {"delete", "remove", "clear", "drop"},
    "send": {"send", "post", "publish", "transfer", "email", "notify"},
    "compute": {"calculate", "compute", "convert", "estimate", "derive", "solve", "rank"},
}


def _request_tool_action_conflict(request: str, tool: ToolIR) -> bool:
    query_actions = _action_families_for_text(request)
    if not query_actions:
        return False
    tool_actions = _action_families_for_text(" ".join([tool.tool_name, tool.tool_purpose or "", *(tool.side_effect_hints or []), *(tool.safety_hints or [])]))
    if not tool_actions:
        return False
    if _negated_action_families_for_text(request).intersection(tool_actions):
        return True
    if query_actions.intersection(tool_actions):
        return False
    readonly = {"search", "read"}
    mutating = {"create", "update", "delete", "send"}
    if query_actions.intersection(readonly) and tool_actions.intersection(mutating):
        return True
    if query_actions.intersection(mutating) and tool_actions.intersection(readonly):
        return True
    if "delete" in query_actions and tool_actions.intersection({"create", "update", "send"}):
        return True
    if query_actions.intersection({"create", "update", "send"}) and "delete" in tool_actions:
        return True
    return False


def _negated_action_families_for_text(text: str) -> set[str]:
    lowered = text.lower()
    negated: set[str] = set()
    for family, cues in PREDICTOR_ACTION_FAMILIES.items():
        for cue in cues:
            if re.search(rf"\b(?:do not|don't|without|avoid|no)\s+{re.escape(cue)}(?:ing|e|ed|s)?\b", lowered):
                negated.add(family)
    return negated


def _action_families_for_text(text: str) -> set[str]:
    tokens = {_normalize_action_token(token) for token in re.findall(r"[a-z0-9_./*?-]+", text.lower())}
    families: set[str] = set()
    for family, cues in PREDICTOR_ACTION_FAMILIES.items():
        if tokens.intersection(cues):
            families.add(family)
    return families


def _normalize_action_token(token: str) -> str:
    token = token.strip("._-/").lower()
    if token.endswith("ing") and len(token) > 5:
        return token[:-3]
    if token.endswith("ed") and len(token) > 4:
        return token[:-2]
    if token.endswith("s") and len(token) > 4:
        return token[:-1]
    return token


def _verify_reliaskill_v1_prediction(
    tool: ToolIR,
    skill: GeneratedSkill,
    task: EvalTask,
    prediction: EvalPrediction,
) -> EvalPrediction:
    if not _uses_reliaskill_v1_runtime(skill):
        return prediction

    actions: list[str] = []
    issues: list[str] = []
    raw_original_arguments = dict(prediction.predicted_arguments)
    if _contract_ablation_disabled(skill, "disable_schema_repair"):
        original_arguments = dict(prediction.predicted_arguments)
    else:
        original_arguments = _lift_nested_argument_fields(dict(prediction.predicted_arguments), tool, actions)
    grounding_context = {} if _contract_ablation_disabled(skill, "disable_contextual_grounding") else _task_grounding_context(task)
    grounding_request = task.user_request if _contract_ablation_disabled(skill, "disable_contextual_grounding") else _task_grounding_text(task)
    contract_before = evaluate_skill_contract(
        tool,
        skill,
        task.user_request,
        arguments=original_arguments,
        grounding_context=grounding_context,
    )
    should_call = bool(prediction.should_call)
    abstention_reason = prediction.abstention_reason
    rescued_required_arguments: Dict[str, Any] = {}

    boundary_reason = _reliaskill_v1_boundary_reason(tool, skill, task.user_request)
    if boundary_reason == "action_intent_conflict" and _contract_ablation_disabled(skill, "disable_action_gate"):
        boundary_reason = None
    if should_call and boundary_reason:
        should_call = False
        abstention_reason = boundary_reason
        actions.append("abstained_boundary_match")
    elif not should_call and not boundary_reason and not _contract_ablation_disabled(skill, "disable_runtime_grounding"):
        rescue_actions: list[str] = []
        rescue, grounded_arguments, rescue_issues = _can_rescue_grounded_abstention(
            tool,
            skill,
            task.user_request,
            grounding_request,
            rescue_actions,
        )
        if rescue:
            should_call = True
            abstention_reason = None
            rescued_required_arguments = grounded_arguments
            actions.extend(rescue_actions)
            actions.append("rescued_grounded_false_abstention")
        elif rescue_issues:
            issues.extend(rescue_issues)

    sanitized: Dict[str, Any] = {}
    if should_call:
        if _contract_ablation_disabled(skill, "disable_schema_repair") and contract_before.argument_issues:
            should_call = False
            abstention_reason = "schema_repair_ablation_violation:" + ",".join(contract_before.argument_issues[:3])
            actions.append("abstained_schema_repair_ablation_violation")
            sanitized = {}
        else:
            by_name = {arg.name: arg for arg in tool.arguments}
            for key, value in original_arguments.items():
                arg = by_name.get(key)
                if arg is None:
                    actions.append(f"dropped_unsupported_field:{key}")
                    continue
                sanitized_value, value_issues = _sanitize_value_for_schema(value, _schema_for_argument(arg), key, actions)
                schema = _schema_for_argument(arg)
                if (
                    arg.required
                    and (sanitized_value is None or value_issues)
                    and not _contract_ablation_disabled(skill, "disable_runtime_grounding")
                ):
                    grounded = _grounded_required_value(tool, arg, grounding_request, skill)
                    if grounded is not None:
                        grounded_value, grounded_issues = _sanitize_value_for_schema(grounded, schema, key, actions)
                        if grounded_value is not None and not grounded_issues:
                            sanitized[key] = _prune_ungrounded_schema_optionals(grounded_value, schema, key, grounding_request, actions)
                            actions.append(f"replaced_invalid_required:{key}")
                            continue
                        issues.extend(grounded_issues)
                issues.extend(value_issues)
                if sanitized_value is not None:
                    if not arg.required and not _optional_argument_is_grounded(tool, arg, grounding_request, skill, sanitized_value):
                        actions.append(f"dropped_ungrounded_optional:{key}")
                        continue
                    pruned_value = _prune_ungrounded_schema_optionals(sanitized_value, schema, key, grounding_request, actions)
                    if (
                        arg.required
                        and not _contract_ablation_disabled(skill, "disable_runtime_grounding")
                        and not _required_argument_value_is_grounded(tool, arg, grounding_request, skill, pruned_value)
                    ):
                        grounded = _grounded_required_value(tool, arg, grounding_request, skill)
                        if grounded is not None:
                            grounded_value, grounded_issues = _sanitize_value_for_schema(grounded, schema, key, actions)
                            issues.extend(grounded_issues)
                            if grounded_value is not None:
                                sanitized[key] = _prune_ungrounded_schema_optionals(grounded_value, schema, key, grounding_request, actions)
                                actions.append(f"replaced_ungrounded_required:{key}")
                                continue
                        issues.append(f"{key}:ungrounded_required")
                        continue
                    sanitized[key] = pruned_value

            for arg in tool.arguments:
                if not arg.required or arg.name in sanitized:
                    continue
                grounded = None if _contract_ablation_disabled(skill, "disable_runtime_grounding") else rescued_required_arguments.get(arg.name)
                if grounded is None and not _contract_ablation_disabled(skill, "disable_runtime_grounding"):
                    grounded = _grounded_required_value(tool, arg, grounding_request, skill)
                if grounded is not None:
                    sanitized_value, value_issues = _sanitize_value_for_schema(grounded, _schema_for_argument(arg), arg.name, actions)
                    issues.extend(value_issues)
                    if sanitized_value is not None:
                        sanitized[arg.name] = sanitized_value
                        actions.append(f"filled_grounded_required:{arg.name}")
                        continue
                issues.append(f"{arg.name}:missing_required")

        blocking_issues = [
            issue
            for issue in issues
            if issue.endswith(":missing_required")
            or issue.endswith(":type_mismatch")
            or issue.endswith(":invalid_enum")
            or issue.endswith(":invalid_format")
            or issue.endswith(":pattern_mismatch")
            or issue.endswith(":min_length")
            or issue.endswith(":max_length")
            or issue.endswith(":min_items")
            or issue.endswith(":max_items")
            or issue.endswith(":ungrounded_required")
        ]
        if blocking_issues:
            should_call = False
            abstention_reason = "schema_contract_violation:" + ",".join(sorted(set(blocking_issues))[:3])
            actions.append("abstained_schema_contract_violation")
            sanitized = {}
    else:
        sanitized = {}

    contract_after = evaluate_skill_contract(
        tool,
        skill,
        task.user_request,
        arguments=sanitized,
        grounding_context=grounding_context,
    )
    ignored_blockers = {"action_intent_conflict"} if _contract_ablation_disabled(skill, "disable_action_gate") else set()
    effective_contract_blockers = [reason for reason in contract_after.blocking_reasons if reason not in ignored_blockers]
    if should_call and effective_contract_blockers:
        issues.extend(contract_after.argument_issues)
        issues.extend(f"contract:{reason}" for reason in effective_contract_blockers)
        should_call = False
        abstention_reason = "contract_proof_failure:" + ",".join(effective_contract_blockers[:3])
        actions.append("abstained_contract_proof_failure")
        sanitized = {}
        contract_after = evaluate_skill_contract(
            tool,
            skill,
            task.user_request,
            arguments=sanitized,
            grounding_context=grounding_context,
        )

    metadata = dict(prediction.metadata)
    metadata["reliaskill_v1_runtime_verifier"] = {
        "enabled": True,
        "actions": actions,
        "issues": sorted(set(issues)),
        "compiled_contract": compile_skill_contract(tool, skill).model_dump(),
        "contract_evaluation_before": contract_before.model_dump(),
        "contract_evaluation_after": contract_after.model_dump(),
        "contract_failure_report_before": build_contract_failure_report(contract_before),
        "contract_failure_report_after": build_contract_failure_report(contract_after),
        "original_arguments": raw_original_arguments,
        "normalized_original_arguments": original_arguments,
        "verified_arguments": sanitized,
        "should_call_before": prediction.should_call,
        "should_call_after": should_call,
    }
    metadata["parsed_prediction"] = dict(sanitized)
    metadata["should_call"] = should_call
    metadata["abstention_reason"] = abstention_reason

    return EvalPrediction(
        task_id=prediction.task_id,
        tool_name=prediction.tool_name,
        baseline_name=prediction.baseline_name,
        predicted_arguments=sanitized,
        should_call=should_call,
        abstention_reason=abstention_reason,
        exposure_text=prediction.exposure_text,
        metadata=metadata,
    )


def _heuristic_abstention_reason(user_request: str, skill: GeneratedSkill) -> str | None:
    lowered = user_request.lower()
    explicit_markers = (
        "no tool call",
        "do not call",
        "don't call",
        "without using",
        "planning only",
        "checklist",
        "no tool yet",
        "unrelated to",
        "do not satisfy this",
        "should not trigger",
        "ask for clarification",
    )
    if any(marker in lowered for marker in explicit_markers):
        return "request_explicitly_asks_not_to_call"
    for line in skill.when_not_to_use:
        line_lower = line.lower()
        if "missing" in line_lower and any(marker in lowered for marker in ("do not know", "don't know", "missing", "not sure")):
            return "missing_required_information"
        if "adjacent" in line_lower and "not" in lowered:
            return "adjacent_or_boundary_mismatch"
    return None


class PredictorBackend(ABC):
    backend_name = "base"

    @abstractmethod
    def predict(self, tool: ToolIR, skill: GeneratedSkill, task: EvalTask) -> EvalPrediction:
        raise NotImplementedError


class HeuristicPredictorBackend(PredictorBackend):
    backend_name = "heuristic"

    def predict(self, tool: ToolIR, skill: GeneratedSkill, task: EvalTask) -> EvalPrediction:
        prompt = build_prediction_prompt(tool, skill, task.user_request)
        abstention_reason = _heuristic_abstention_reason(task.user_request, skill)
        should_call = abstention_reason is None
        predicted = {}
        if should_call:
            for arg in tool.arguments:
                if arg.default is not None:
                    predicted[arg.name] = arg.default

            for arg in tool.arguments:
                value = _extract_explicit_argument_value(arg, task.user_request)
                if value is None:
                    value = _infer_argument_value(arg.name, task.user_request, skill)
                if value is None and skill.semantic_hints:
                    value = _infer_semantic_hint_value(tool, arg.name, task.user_request, skill)
                if value is None:
                    if not _should_skip_example_inference(arg.name, task.user_request, skill) and not (
                        (arg.name == "head" and "tail" in predicted) or (arg.name == "tail" and "head" in predicted)
                    ):
                        value = _infer_from_examples(arg.name, task.user_request, skill)
                if value is None:
                    if arg.required and arg.name not in predicted:
                        fallback = skill.argument_template.get(arg.name)
                        if fallback is None:
                            continue
                        predicted[arg.name] = fallback
                        continue
                    if not arg.required:
                        continue
                else:
                    predicted[arg.name] = value

            if skill.baseline_name == "raw_mcp":
                optional_names = {arg.name for arg in tool.arguments if not arg.required}
                predicted = {
                    key: value
                    for key, value in predicted.items()
                    if key not in optional_names or value not in (None, False)
                }

        return EvalPrediction(
            task_id=task.task_id,
            tool_name=task.tool_name,
            baseline_name=skill.baseline_name,
            predicted_arguments=predicted,
            should_call=should_call,
            abstention_reason=abstention_reason,
            exposure_text=render_exposure(tool, skill),
            metadata=_prediction_audit_metadata(
                skill=skill,
                prompt=prompt,
                raw_model_output=json.dumps(
                    {"should_call": should_call, "arguments": predicted, "abstention_reason": abstention_reason},
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                parsed_arguments=predicted,
                backend_name=self.backend_name,
                model_name="heuristic",
                should_call=should_call,
                abstention_reason=abstention_reason,
            ),
        )


class OpenAICompatiblePredictorBackend(PredictorBackend):
    backend_name = "openai_compatible"

    def __init__(
        self,
        api_url: str,
        model: str,
        api_key: str | None = None,
        timeout_seconds: int = 60,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.quantization = "none"

    def _post_json(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        request = urllib.request.Request(
            url=f"{self.api_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}),
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def predict(self, tool: ToolIR, skill: GeneratedSkill, task: EvalTask) -> EvalPrediction:
        prompt = build_prediction_prompt(tool, skill, task.user_request)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You produce only JSON tool-call decisions and arguments for MCP tools."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
        response = self._post_json(payload)
        content = response["choices"][0]["message"]["content"]
        data = parse_json_object_output(content)
        should_call, abstention_reason = _parse_should_call(data)
        predicted_arguments, argument_parse_error = _coerce_predicted_arguments(data)
        if not should_call:
            predicted_arguments = {}
            argument_parse_error = None
        metadata = _prediction_audit_metadata(
            skill=skill,
            prompt=prompt,
            raw_model_output=content,
            parsed_arguments=predicted_arguments,
            backend_name=self.backend_name,
            model_name=self.model,
            quantization=self.quantization,
            should_call=should_call,
            abstention_reason=abstention_reason,
        )
        if argument_parse_error:
            metadata["argument_parse_error"] = argument_parse_error
        return EvalPrediction(
            task_id=task.task_id,
            tool_name=task.tool_name,
            baseline_name=skill.baseline_name,
            predicted_arguments=predicted_arguments,
            should_call=should_call,
            abstention_reason=abstention_reason,
            exposure_text=render_exposure(tool, skill),
            metadata=metadata,
        )


class LocalHFPredictorBackend(PredictorBackend):
    backend_name = "local_hf"

    def __init__(
        self,
        model_name_or_path: str,
        device: str | None = None,
        device_map: str | None = None,
        torch_dtype: str | None = None,
        max_new_tokens: int = 512,
        trust_remote_code: bool = False,
        attn_implementation: str | None = None,
        load_in_4bit: bool = False,
        load_in_8bit: bool = False,
        generation_kwargs: Dict[str, Any] | None = None,
    ) -> None:
        self.model_name_or_path = model_name_or_path
        self.quantization = _quantization_label(load_in_4bit=load_in_4bit, load_in_8bit=load_in_8bit, torch_dtype=torch_dtype)
        self.runner = LocalHFChatRunner(
            model_name_or_path=model_name_or_path,
            device=device,
            device_map=device_map,
            torch_dtype=torch_dtype,
            max_new_tokens=max_new_tokens,
            trust_remote_code=trust_remote_code,
            attn_implementation=attn_implementation,
            load_in_4bit=load_in_4bit,
            load_in_8bit=load_in_8bit,
            generation_kwargs=generation_kwargs,
        )

    def predict(self, tool: ToolIR, skill: GeneratedSkill, task: EvalTask) -> EvalPrediction:
        prompt = build_prediction_prompt(tool, skill, task.user_request)
        content = self.runner.generate_chat(
            [
                {"role": "system", "content": "You produce only JSON tool-call decisions and arguments for MCP tools."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
        data = parse_json_object_output(content)
        should_call, abstention_reason = _parse_should_call(data)
        predicted_arguments, argument_parse_error = _coerce_predicted_arguments(data)
        if not should_call:
            predicted_arguments = {}
            argument_parse_error = None
        metadata = _prediction_audit_metadata(
            skill=skill,
            prompt=prompt,
            raw_model_output=content,
            parsed_arguments=predicted_arguments,
            backend_name=self.backend_name,
            model_name=self.model_name_or_path,
            quantization=self.quantization,
            should_call=should_call,
            abstention_reason=abstention_reason,
        )
        if argument_parse_error:
            metadata["argument_parse_error"] = argument_parse_error
        return EvalPrediction(
            task_id=task.task_id,
            tool_name=task.tool_name,
            baseline_name=skill.baseline_name,
            predicted_arguments=predicted_arguments,
            should_call=should_call,
            abstention_reason=abstention_reason,
            exposure_text=render_exposure(tool, skill),
            metadata=metadata,
        )


def build_predictor_from_env() -> PredictorBackend:
    api_url = os.getenv("AUTOSKILL_PREDICT_API_URL") or os.getenv("AUTOSKILL_API_URL")
    model = os.getenv("AUTOSKILL_PREDICT_MODEL") or os.getenv("AUTOSKILL_MODEL")
    api_key = os.getenv("AUTOSKILL_PREDICT_API_KEY") or os.getenv("AUTOSKILL_API_KEY")
    if api_url and model:
        return OpenAICompatiblePredictorBackend(api_url=api_url, model=model, api_key=api_key)
    return HeuristicPredictorBackend()


def build_predictor_from_config(config: Dict[str, Any] | None) -> PredictorBackend:
    if not config:
        return build_predictor_from_env()

    backend_type = config.get("type", "heuristic")
    if backend_type == "heuristic":
        return HeuristicPredictorBackend()
    if backend_type == "openai_compatible":
        api_key = config.get("api_key")
        api_key_env = config.get("api_key_env")
        if api_key_env and not api_key:
            api_key = os.getenv(str(api_key_env))
        return OpenAICompatiblePredictorBackend(
            api_url=str(config["api_url"]),
            model=str(config["model"]),
            api_key=api_key,
            timeout_seconds=int(config.get("timeout_seconds", 60)),
        )
    if backend_type == "local_hf":
        return LocalHFPredictorBackend(
            model_name_or_path=str(config["model_name_or_path"]),
            device=config.get("device"),
            device_map=config.get("device_map"),
            torch_dtype=config.get("torch_dtype"),
            max_new_tokens=int(config.get("max_new_tokens", 512)),
            trust_remote_code=bool(config.get("trust_remote_code", False)),
            attn_implementation=config.get("attn_implementation"),
            load_in_4bit=bool(config.get("load_in_4bit", False)),
            load_in_8bit=bool(config.get("load_in_8bit", False)),
            generation_kwargs=config.get("generation_kwargs"),
        )
    raise ValueError(f"Unsupported predictor backend type: {backend_type}")


def safe_predict(
    tool: ToolIR,
    skill: GeneratedSkill,
    task: EvalTask,
    backend: PredictorBackend,
    *,
    allow_fallback: bool = True,
) -> EvalPrediction:
    try:
        prediction = backend.predict(tool, skill, task)
        prediction = _verify_reliaskill_v1_prediction(tool, skill, task, prediction)
        prediction.metadata = {
            **prediction.metadata,
            "configured_predictor_backend": backend.backend_name,
            "actual_predictor_backend": backend.backend_name,
            "predictor_fallback_used": False,
            "predictor_fallback_reason": None,
        }
        return prediction
    except (
        ImportError,
        KeyError,
        RuntimeError,
        ValueError,
        TypeError,
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
    ) as exc:
        if not allow_fallback:
            raise
        prediction = HeuristicPredictorBackend().predict(tool, skill, task)
        prediction = _verify_reliaskill_v1_prediction(tool, skill, task, prediction)
        prediction.metadata = {
            **prediction.metadata,
            "configured_predictor_backend": backend.backend_name,
            "actual_predictor_backend": HeuristicPredictorBackend.backend_name,
            "predictor_fallback_used": True,
            "predictor_fallback_reason": f"{type(exc).__name__}: {exc}",
        }
        return prediction

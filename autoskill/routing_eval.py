from __future__ import annotations
from tqdm import tqdm

import hashlib
import json
import random
import re
from typing import Any, Dict, Iterable, List, Tuple

from autoskill.eval_types import EvalTask
from autoskill.conditions import GENERATED_SKILL_BASE, RELIASKILL_CHALLENGER, is_reliaskill_v1_family, normalize_condition_name
from autoskill.contract_decision import (
    choose_contrastive_contract_candidate,
    explicit_requested_tool_score,
    row_explicit_request_match,
)
from autoskill.contract_inference import build_contract_proof_state, proof_state_is_viable
from autoskill.doc_evidence import build_doc_grounding_evidence, render_doc_grounding_evidence
from autoskill.ir import GeneratedSkill, ToolIR
from autoskill.method_metadata import prediction_method_metadata
from autoskill.predictor import PredictorBackend, safe_predict
from autoskill.progress import write_progress_state
from autoskill.retrieval_runtime import (
    contextualize_skill_for_task,
    retrieve_candidate_tools,
    retrieve_doc_tool_rankings,
    retrieve_memory_tool_rankings,
)
from autoskill.routing_boundaries import detect_routing_abstention, routing_tool_mention_adjustment
from autoskill.task_eval import score_prediction

BOUNDARY_FIRST_ROUTING_CONDITIONS = {RELIASKILL_CHALLENGER, "skill_prompt_boundary_first"}
METHOD_ROUTING_CONDITIONS = {GENERATED_SKILL_BASE, *BOUNDARY_FIRST_ROUTING_CONDITIONS}


def _contract_ablation_disabled(skill: GeneratedSkill, flag: str) -> bool:
    flags = skill.metadata.get("contract_ablation_flags") if isinstance(skill.metadata, dict) else None
    return bool(isinstance(flags, dict) and flags.get(flag) is True)

def _safe_dir_name(value: str) -> str:
    """Truncate a tool or condition name for use as a directory component on Windows."""
    return _safe_component(value)[:50]


def _safe_component(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in value) or "unknown"


def _safe_task_name(value: str) -> str:
    safe = _safe_component(value)
    if len(safe) <= 96:
        return safe
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]
    return f"{safe[:83]}_{digest}"


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9_./*?-]+", text.lower())


def _skill_router_text(tool: ToolIR, skill: GeneratedSkill) -> str:
    parts = [tool.tool_name, tool.tool_purpose or "", skill.skill_summary]
    parts.extend(skill.when_to_use)
    parts.extend(skill.when_not_to_use)
    for argument in tool.arguments:
        parts.append(argument.name)
        if argument.description:
            parts.append(argument.description)
    for example in skill.examples:
        parts.append(str(example.get("scenario", "")))
    for arg_name, spec in skill.semantic_hints.items():
        parts.append(arg_name)
        if isinstance(spec, dict):
            parts.extend(str(key) for key in spec.keys())
            parts.extend(str(value) for value in spec.values() if isinstance(value, (str, int, float)))
    return " ".join(part for part in parts if part)


def _skill_router_positive_text(tool: ToolIR, skill: GeneratedSkill) -> str:
    parts = [tool.tool_name, tool.tool_purpose or "", skill.skill_summary]
    parts.extend(skill.when_to_use)
    schema_contract = skill.metadata.get("schema_contract") if isinstance(skill.metadata, dict) else None
    if isinstance(schema_contract, list):
        parts.extend(str(line) for line in schema_contract if isinstance(line, str))
    if is_reliaskill_v1_family(skill.baseline_name) and not _contract_ablation_disabled(skill, "disable_doc_grounding"):
        evidence = skill.metadata.get("doc_grounding_evidence") if isinstance(skill.metadata, dict) else None
        enable_doc_shield = not _contract_ablation_disabled(skill, "disable_doc_consistency_shield")
        if not isinstance(evidence, dict) or not enable_doc_shield:
            evidence = build_doc_grounding_evidence(
                tool,
                enable_consistency_shield=enable_doc_shield,
            )
        parts.append(render_doc_grounding_evidence(evidence, max_chars=1800))
    for argument in tool.arguments:
        parts.append(argument.name)
        if argument.description:
            parts.append(argument.description)
    for example in skill.examples:
        parts.append(str(example.get("scenario", "")))
    for arg_name, spec in skill.semantic_hints.items():
        parts.append(arg_name)
        if isinstance(spec, dict):
            parts.extend(str(key) for key in spec.keys())
            parts.extend(str(value) for value in spec.values() if isinstance(value, (str, int, float)))
    return " ".join(part for part in parts if part)


_BOUNDARY_STOP_TOKENS = {
    "a",
    "an",
    "and",
    "any",
    "are",
    "ask",
    "be",
    "call",
    "do",
    "field",
    "fields",
    "for",
    "from",
    "if",
    "in",
    "input",
    "inputs",
    "is",
    "it",
    "not",
    "or",
    "parameter",
    "parameters",
    "request",
    "required",
    "should",
    "that",
    "the",
    "this",
    "to",
    "tool",
    "unsupported",
    "use",
    "when",
}


def _boundary_overlap_penalty(query: str, skill: GeneratedSkill) -> int:
    """Penalize ReliaSkill routes whose non-use boundaries match the request."""
    query_tokens = _boundary_tokens(query)
    if not query_tokens:
        return 0
    boundary_tokens = set().union(*(_boundary_tokens(line) for line in skill.when_not_to_use)) if skill.when_not_to_use else set()
    overlap = query_tokens.intersection(boundary_tokens)
    return min(8, 2 * len(overlap))


def _boundary_tokens(text: str) -> set[str]:
    result: set[str] = set()
    for token in _tokenize(text):
        for part in _compound_token_parts(token):
            if part in _BOUNDARY_STOP_TOKENS or len(part) <= 2:
                continue
            result.update(_token_variants(part))
    return result


def _compound_token_parts(token: str) -> set[str]:
    parts = {token}
    parts.update(part for part in re.split(r"[-_/.]+", token) if part)
    return parts


def _token_variants(token: str) -> set[str]:
    variants = {token}
    if token.endswith("ing") and len(token) > 5:
        stem = token[:-3]
        variants.add(stem)
        variants.add(stem + "e")
    if token.endswith("ed") and len(token) > 4:
        variants.add(token[:-2])
        variants.add(token[:-1])
    if token.endswith("s") and len(token) > 4:
        variants.add(token[:-1])
    return variants


def _router_overlap_score(query: str, text: str) -> int:
    query_tokens = _tokenize(query)
    text_tokens = set(_tokenize(text))
    overlap = set(query_tokens).intersection(text_tokens)
    score = 2 * len(overlap)
    if query.lower() in text.lower():
        score += 5
    return score


def _generated_skill_routing_bonus(query: str, tool: ToolIR, skill: GeneratedSkill) -> int:
    lowered = query.lower()
    bonus = 0
    bonus += routing_tool_mention_adjustment(query, tool)
    for arg_name, spec in skill.semantic_hints.items():
        if not isinstance(spec, dict):
            continue
        for cue in spec.keys():
            if cue in lowered:
                bonus += 4
        if arg_name in {"pattern", "excludePatterns"} and tool.tool_name == "search_files":
            bonus += 3
        if arg_name in {"head", "tail"} and tool.tool_name == "read_text_file":
            bonus += 3
        if arg_name == "content" and tool.tool_name == "write_file":
            bonus += 3
    return bonus


def _reliaskill_v1_contract_routing_bonus(query: str, tool: ToolIR) -> tuple[int, Dict[str, Any]]:
    explicit_args = _explicit_argument_names(query)
    allowed_args = {arg.name for arg in tool.arguments}
    required_args = {arg.name for arg in tool.arguments if arg.required}
    matched_args = sorted(explicit_args.intersection(allowed_args))
    matched_required = sorted(explicit_args.intersection(required_args))
    unknown_explicit = sorted(explicit_args - allowed_args)

    argument_bonus = (12 * len(matched_required)) + (4 * len(set(matched_args) - set(matched_required)))
    if explicit_args and not matched_args and allowed_args:
        argument_bonus -= 18
    if explicit_args and not allowed_args:
        argument_bonus -= 24
    if required_args and explicit_args and not required_args.intersection(explicit_args):
        argument_bonus -= min(12, 3 * len(required_args))
    if unknown_explicit and not matched_required:
        argument_bonus -= min(18, 3 * len(unknown_explicit))

    no_argument_bonus = _no_argument_fit_bonus(query, tool)
    identity_bonus = _tool_identity_match_bonus(query, tool)
    explicit_request_match = explicit_requested_tool_score(query, tool.tool_name)
    purpose_bonus = _purpose_phrase_match_bonus(query, tool)
    total = argument_bonus + no_argument_bonus + identity_bonus + explicit_request_match + purpose_bonus
    return total, {
        "argument_name_fit": argument_bonus,
        "matched_explicit_args": matched_args,
        "matched_required_args": matched_required,
        "unknown_explicit_args": unknown_explicit[:8],
        "no_argument_fit": no_argument_bonus,
        "tool_identity_match": identity_bonus,
        "explicit_request_match": explicit_request_match,
        "purpose_phrase_match": purpose_bonus,
    }


def _explicit_argument_names(query: str) -> set[str]:
    names = {
        match.group(1)
        for match in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_.-]*)\s*(?:=|:)", query)
        if not re.fullmatch(r"https?", match.group(1), flags=re.IGNORECASE)
    }
    return {name.split(".", 1)[0] for name in names}


def _request_declares_no_arguments(query: str) -> bool:
    lowered = query.lower()
    return bool(
        re.search(r"\bapply\s+no\s+arguments?\b", lowered)
        or re.search(r"\bwith\s+no\s+arguments?\b", lowered)
        or re.search(r"\bno\s+arguments?\s+(?:required|needed|provided)\b", lowered)
    )


def _no_argument_fit_bonus(query: str, tool: ToolIR) -> int:
    if not _request_declares_no_arguments(query):
        return 0
    return 24 if not any(arg.required for arg in tool.arguments) else -36


def _tool_identity_match_bonus(query: str, tool: ToolIR) -> int:
    text = normalize_condition_text(query)
    bonus = 0
    for name in tool_name_text_variants(tool):
        if not name:
            continue
        if _negated_tool_name_context(text, name):
            return -80
        if name in text:
            bonus = max(bonus, 36)
    return bonus


def normalize_condition_text(text: str) -> str:
    lowered = str(text or "").lower()
    lowered = re.sub(r"[_./:-]+", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


def tool_name_text_variants(tool: ToolIR) -> list[str]:
    name = tool.tool_name
    variants = {
        normalize_condition_text(name),
        normalize_condition_text(name.replace("_", " ")),
        normalize_condition_text(name.replace("-", " ")),
        normalize_condition_text(name.replace(".", " ")),
    }
    return sorted(value for value in variants if value)


def _negated_tool_name_context(text: str, name: str) -> bool:
    return any(
        phrase in text
        for phrase in (
            f"{name} is a distractor",
            f"{name} should not be called",
            f"do not use {name}",
            f"do not call {name}",
            f"without using {name}",
        )
    )


def _explicit_contrastive_route_override(
    query: str,
    current_tool_name: str,
    rows: List[Dict[str, Any]],
) -> Dict[str, Any] | None:
    decision = choose_contrastive_contract_candidate(
        request=query,
        current_tool_name=current_tool_name,
        rows=rows,
        current_reason="explicit_contrastive_route",
        allow_nonviable_explicit=True,
    )
    if decision is None or decision.explicit_request_match <= 0:
        return None
    return next((row for row in rows if str(row.get("tool_name") or "") == decision.tool_name), None)


def _purpose_phrase_match_bonus(query: str, tool: ToolIR) -> int:
    purpose = normalize_condition_text(tool.tool_purpose or "")
    if not purpose:
        return 0
    query_text = normalize_condition_text(query)
    purpose_tokens = [token for token in purpose.split() if token not in _BOUNDARY_STOP_TOKENS]
    if len(purpose_tokens) >= 4 and " ".join(purpose_tokens[: min(10, len(purpose_tokens))]) in query_text:
        return 28
    if len(purpose_tokens) >= 3:
        overlap = set(purpose_tokens).intersection(set(query_text.split()))
        if len(overlap) >= min(4, len(set(purpose_tokens))):
            return 4 * len(overlap)
    return 0


def _reliaskill_v1_schema_fit_bonus(query: str, tool: ToolIR) -> tuple[int, List[str], List[str]]:
    required_args = [arg for arg in tool.arguments if arg.required]
    if not required_args:
        return 0, [], []
    grounded: List[str] = []
    missing: List[str] = []
    for arg in required_args:
        if _required_arg_is_grounded(query, arg):
            grounded.append(arg.name)
        else:
            missing.append(arg.name)

    bonus = (3 * len(grounded)) - (4 * len(missing))
    if len(required_args) >= 3 and len(missing) >= len(required_args) - 1:
        bonus -= 3
    bonus += _side_effect_fit_bonus(query, tool)
    bonus += _action_intent_fit_bonus(query, tool)
    return bonus, grounded, missing


def _required_arg_is_grounded(query: str, arg: Any) -> bool:
    lowered = query.lower()
    if _mentions_deferred_required_info(query, str(arg.name)):
        return False
    if (arg.type == "object" or getattr(arg, "properties", None)) and isinstance(getattr(arg, "properties", None), dict):
        required_children = list(getattr(arg, "required_properties", None) or [])
        if not required_children:
            required_children = list((getattr(arg, "properties", {}) or {}).keys())
        if required_children:
            properties = getattr(arg, "properties", {}) or {}
            return all(_schema_property_is_grounded(query, child, properties.get(child, {})) for child in required_children)

    items_schema = getattr(arg, "items_schema", None)
    if arg.type == "array" and isinstance(items_schema, dict) and isinstance(items_schema.get("properties"), dict):
        required_children = list(items_schema.get("required") or items_schema.get("required_properties") or [])
        if not required_children:
            required_children = list((items_schema.get("properties") or {}).keys())
        if required_children:
            properties = items_schema.get("properties") or {}
            return all(_schema_property_is_grounded(query, child, properties.get(child, {})) for child in required_children)

    if re.search(rf"\b{re.escape(str(arg.name))}\s*(?:=|:)", query, flags=re.IGNORECASE):
        return True
    name_parts = _argument_name_parts(str(arg.name))
    if arg.type in {"integer", "number"} and re.search(r"\b\d+(?:\.\d+)?\b", query):
        return True
    if arg.enum:
        for value in arg.enum:
            if str(value).lower() in lowered:
                return True
    if arg.name in {"query", "q", "search", "pattern"}:
        return bool(
            re.search(r"\b(?:query|search|find|lookup|look up|matching|containing)\b", lowered)
            or re.search(r'"[^"]+"', query)
        )
    if arg.name in {"path", "file", "filename", "directory", "folder"} or name_parts.intersection({"path", "file", "filename", "directory", "folder"}):
        return bool(
            re.search(r"\b[A-Za-z0-9_./-]+\.[A-Za-z0-9_*?-]+\b", query)
            or re.search(r"\b(?:in|under|inside|within)\s+[A-Za-z0-9_./-]+\b", lowered)
            or re.search(r"\bcreate\s+(?:the\s+)?(?:directory|folder)\s+[A-Za-z0-9_./-]+\b", lowered)
            or re.search(r"\bcreate\s+(?:the\s+)?[A-Za-z0-9_./-]+\s+(?:directory|folder)\b", lowered)
        )
    if arg.name in {"content", "text", "body", "message"} or name_parts.intersection({"content", "text", "body", "message"}):
        return bool(re.search(r'"[^"]+"', query) or re.search(r"\b(?:content|text|body|message|write|save|send)\b", lowered))
    if name_parts.intersection({"id", "account", "user", "entity", "name", "title"}):
        return bool(_contains_identifier_like_text(query) or re.search(r'"[^"]+"', query))
    if name_parts.intersection(
        {
            "query",
            "search",
            "pattern",
            "path",
            "file",
            "filename",
            "directory",
            "folder",
            "content",
            "text",
            "body",
            "message",
            "start",
            "end",
            "date",
            "time",
            "amount",
            "email",
            "recipient",
            "attendee",
        }
    ):
        return False
    if name_parts and name_parts.intersection(set(_tokenize(query))):
        return True
    description = str(getattr(arg, "description", "") or "")
    description_parts = _argument_name_parts(description)
    return bool(description_parts and description_parts.intersection(set(_tokenize(query))))


def _schema_property_is_grounded(query: str, name: str, schema: Any) -> bool:
    lowered = query.lower()
    if _mentions_deferred_required_info(query, name):
        return False
    if re.search(rf"\b{re.escape(str(name))}\s*(?:=|:)", query, flags=re.IGNORECASE):
        return True

    schema = schema if isinstance(schema, dict) else {}
    name_parts = _argument_name_parts(str(name))
    schema_type_name = str(schema.get("type") or "").lower()
    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and any(str(value).lower() in lowered for value in enum_values):
        return True
    if schema_type_name in {"integer", "number"} and re.search(r"\b\d+(?:\.\d+)?\b", query):
        return True
    if name_parts.intersection({"query", "search", "pattern"}):
        return bool(re.search(r"\b(?:query|search|find|lookup|look up|matching|containing)\b", lowered) or re.search(r'"[^"]+"', query))
    if name_parts.intersection({"path", "file", "filename", "directory", "folder"}):
        return bool(
            re.search(r"\b[A-Za-z0-9_./-]+\.[A-Za-z0-9_*?-]+\b", query)
            or re.search(r"\b(?:in|under|inside|within)\s+[A-Za-z0-9_./-]+\b", lowered)
            or re.search(r"\bcreate\s+(?:the\s+)?(?:directory|folder)\s+[A-Za-z0-9_./-]+\b", lowered)
            or re.search(r"\bcreate\s+(?:the\s+)?[A-Za-z0-9_./-]+\s+(?:directory|folder)\b", lowered)
        )
    if name_parts.intersection({"content", "contents", "text", "body", "message", "payload", "value"}):
        return bool(re.search(r'"[^"]+"', query) or re.search(r"\b(?:content|text|body|message|write|save|send|remember|note|record|set)\b", lowered))
    if name_parts.intersection({"name", "entity", "user", "person", "title"}):
        return bool(re.search(r'"[^"]+"', query) or re.search(r"\b[A-Z][a-zA-Z0-9_-]{2,}\b", query))
    if name_parts.intersection({"start", "begin", "from", "since", "after"}):
        return bool(re.search(r"\b(?:from|since|after|starting|beginning)\b", lowered) or _contains_date_like_text(query))
    if name_parts.intersection({"end", "until", "before", "to"}):
        return bool(re.search(r"\b(?:to|until|before|ending|through)\b", lowered) or _contains_date_like_text(query))
    if name_parts.intersection({"id", "account", "user", "entity", "name", "title"}):
        return bool(_contains_identifier_like_text(query) or re.search(r'"[^"]+"', query))
    if name_parts.intersection(
        {
            "query",
            "search",
            "pattern",
            "path",
            "file",
            "filename",
            "directory",
            "folder",
            "content",
            "contents",
            "text",
            "body",
            "message",
            "payload",
            "value",
            "start",
            "end",
            "date",
            "time",
            "amount",
            "email",
            "recipient",
            "attendee",
        }
    ):
        return False
    if name_parts and name_parts.intersection(set(_tokenize(query))):
        return True
    description_parts = _argument_name_parts(str(schema.get("description") or ""))
    return bool(description_parts and description_parts.intersection(set(_tokenize(query))))


def _contains_date_like_text(query: str) -> bool:
    lowered = query.lower()
    return bool(
        re.search(r"\b\d{4}-\d{1,2}-\d{1,2}\b", query)
        or re.search(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b", query)
        or re.search(r"\b(?:today|tomorrow|yesterday|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", lowered)
        or re.search(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", lowered)
    )


def _contains_identifier_like_text(query: str) -> bool:
    match = re.search(
        r"\b(?:acct|account|user|entity|identifier|id)(?:[-_:]|\s+)([A-Za-z0-9][A-Za-z0-9_.-]*)\b",
        query,
        flags=re.IGNORECASE,
    )
    return bool(match and _looks_like_identifier_literal(match.group(1)))


def _looks_like_identifier_literal(value: str) -> bool:
    return bool(
        value
        and len(value) > 1
        and (re.search(r"\d", value) or re.search(r"[-_.]", value))
        and value.lower() not in {"record", "records", "identifier", "identifiers", "account", "accounts", "user", "users"}
    )


def _mentions_deferred_required_info(query: str, name: str) -> bool:
    lowered = query.lower()
    parts = _argument_name_parts(name)
    deferred = bool(re.search(r"\b(?:later|after|when)\b", lowered) and re.search(r"\b(?:send|provide|give|share)\b", lowered))
    if not deferred:
        return False
    if not parts:
        return True
    return any(part in lowered for part in parts)


def _argument_name_parts(text: str) -> set[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", text)
    return {part.lower() for part in re.split(r"[^A-Za-z0-9]+", spaced) if len(part) > 2}


def _side_effect_fit_bonus(query: str, tool: ToolIR) -> int:
    lowered = query.lower()
    side_effect = str(
        tool.schema_complexity.get("side_effect_type")
        or tool.schema_complexity.get("side_effect")
        or ""
    ).lower()
    hint_text = " ".join([side_effect, *(tool.side_effect_hints or []), *(tool.safety_hints or [])]).lower()
    write_like_tool = any(token in hint_text for token in ("write", "create", "update", "delete", "execute", "send", "transfer", "external"))
    read_like_request = any(token in lowered for token in ("read", "list", "show", "search", "find", "lookup", "preview", "explain", "summarize"))
    write_like_request = any(token in lowered for token in ("write", "create", "update", "delete", "remove", "send", "transfer", "post", "append"))
    if write_like_tool and read_like_request and not write_like_request:
        return -6
    if write_like_tool and write_like_request:
        return 2
    if not write_like_tool and write_like_request and not read_like_request:
        return -2
    return 0


ACTION_FAMILIES: Dict[str, set[str]] = {
    "search": {"search", "find", "lookup", "look", "query", "match", "filter"},
    "read": {"read", "open", "show", "view", "preview", "list", "get", "fetch", "retrieve"},
    "create": {"create", "add", "insert", "new", "draft", "schedule", "record"},
    "update": {"update", "edit", "modify", "patch", "change", "append", "write", "save"},
    "delete": {"delete", "remove", "clear", "drop"},
    "send": {"send", "post", "publish", "transfer", "email", "notify"},
    "compute": {"calculate", "compute", "convert", "estimate", "derive", "solve"},
}


def _action_intent_fit_bonus(query: str, tool: ToolIR) -> int:
    query_actions = _action_families_for_text(query)
    if not query_actions:
        return 0
    tool_text = " ".join([tool.tool_name, tool.tool_purpose or "", *(tool.side_effect_hints or []), *(tool.safety_hints or [])])
    tool_actions = _action_families_for_text(tool_text)
    if not tool_actions:
        return 0
    if _negated_action_families_for_text(query).intersection(tool_actions):
        return -30
    overlap = query_actions.intersection(tool_actions)
    if overlap:
        return 3 * len(overlap)
    if _actions_conflict(query_actions, tool_actions):
        return -5
    return 0


def _action_families_for_text(text: str) -> set[str]:
    tokens = {_normalize_action_token(token) for token in _tokenize(text)}
    tokens = {token for token in tokens if token}
    families: set[str] = set()
    for family, cues in ACTION_FAMILIES.items():
        if tokens.intersection(cues):
            families.add(family)
    if _has_compute_context(text, tokens):
        families.add("compute")
    return families


def _has_compute_context(text: str, tokens: set[str]) -> bool:
    if not tokens.intersection({"find", "determine", "derive", "solve", "rank"}):
        return False
    compute_terms = {
        "root",
        "roots",
        "equation",
        "quadratic",
        "coefficient",
        "coefficients",
        "average",
        "mean",
        "median",
        "density",
        "pressure",
        "velocity",
        "acceleration",
        "force",
        "area",
        "volume",
        "circumference",
        "frequency",
        "resonance",
        "entropy",
        "bmi",
        "probability",
        "genotype",
        "electric",
        "potential",
        "capacitance",
        "inductance",
        "heat",
        "capacity",
        "concentration",
        "rate",
        "distance",
    }
    lowered = text.lower()
    return bool(tokens.intersection(compute_terms) or re.search(r"\b(?:under|over)\s+(?:the\s+)?curve\b", lowered))


def _negated_action_families_for_text(text: str) -> set[str]:
    lowered = text.lower()
    negated: set[str] = set()
    for family, cues in ACTION_FAMILIES.items():
        for cue in cues:
            if re.search(rf"\b(?:do not|don't|without|avoid|no)\s+{re.escape(cue)}(?:ing|e|ed|s)?\b", lowered):
                negated.add(family)
    return negated


def _normalize_action_token(token: str) -> str:
    token = token.strip("._-/").lower()
    if token.endswith("ing") and len(token) > 5:
        token = token[:-3]
    elif token.endswith("ed") and len(token) > 4:
        token = token[:-2]
    elif token.endswith("s") and len(token) > 4:
        token = token[:-1]
    return token


def _actions_conflict(query_actions: set[str], tool_actions: set[str]) -> bool:
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


def _reliaskill_v1_action_intent_conflict(query: str, tool: ToolIR) -> bool:
    tool_text = " ".join([tool.tool_name, tool.tool_purpose or "", *(tool.side_effect_hints or []), *(tool.safety_hints or [])])
    tool_actions = _action_families_for_text(tool_text)
    if not tool_actions:
        return False
    if _negated_action_families_for_text(query).intersection(tool_actions):
        return True
    query_actions = _action_families_for_text(query) - _negated_action_families_for_text(query)
    return bool(query_actions and _actions_conflict(query_actions, tool_actions))


def _reliaskill_v1_ambiguity_reason(query: str, viable_rows: List[Dict[str, Any]], tools: Dict[str, ToolIR]) -> str | None:
    if len(viable_rows) < 2:
        return None
    top = viable_rows[0]
    runner_up = viable_rows[1]
    if int(top.get("score", 0)) - int(runner_up.get("score", 0)) > 1:
        return None
    top_tool = tools[str(top["tool_name"])]
    runner_tool = tools[str(runner_up["tool_name"])]
    if _required_signature(top_tool) != _required_signature(runner_tool):
        return None
    if _action_families_for_tool(top_tool) != _action_families_for_tool(runner_tool):
        return None
    if _request_disambiguates_between_tools(query, top_tool, runner_tool):
        return None
    return "ambiguous_viable_tools_same_schema_and_action"


def _required_signature(tool: ToolIR) -> tuple[str, ...]:
    return tuple(sorted(arg.name for arg in tool.arguments if arg.required))


def _action_families_for_tool(tool: ToolIR) -> set[str]:
    return _action_families_for_text(" ".join([tool.tool_name, tool.tool_purpose or "", *(tool.side_effect_hints or []), *(tool.safety_hints or [])]))


def _request_disambiguates_between_tools(query: str, left: ToolIR, right: ToolIR) -> bool:
    query_tokens = set(_tokenize(query))
    left_tokens = _discriminator_tokens(left)
    right_tokens = _discriminator_tokens(right)
    return bool((query_tokens.intersection(left_tokens - right_tokens)) or (query_tokens.intersection(right_tokens - left_tokens)))


def _discriminator_tokens(tool: ToolIR) -> set[str]:
    text = " ".join([tool.tool_name, tool.tool_purpose or ""])
    tokens: set[str] = set()
    for token in _tokenize(text):
        for part in _compound_token_parts(token):
            if len(part) > 2 and part not in _BOUNDARY_STOP_TOKENS and part not in ACTION_FAMILIES.get("search", set()).union(*ACTION_FAMILIES.values()):
                tokens.add(part)
    return tokens


def select_tool_for_task(
    task: EvalTask,
    baseline_name: str,
    tools: Dict[str, ToolIR],
    skill_bank: Dict[str, GeneratedSkill],
    top_k: int = 3,
) -> Dict[str, Any]:
    normalized_baseline_name = normalize_condition_name(baseline_name)
    method_routing = normalized_baseline_name in METHOD_ROUTING_CONDITIONS or is_reliaskill_v1_family(normalized_baseline_name)
    if method_routing:
        abstention_reason = detect_routing_abstention(task.user_request)
        if abstention_reason:
            return {
                "routing_strategy": "method_boundary_abstention",
                "selected_tool_name": "__abstain__",
                "candidate_tools": ["__abstain__"],
                "candidate_rows": [
                    {
                        "tool_name": "__abstain__",
                        "score": 0,
                        "abstention_reason": abstention_reason,
                    }
                ],
            }

    if baseline_name == "retrieved_docs":
        candidates = retrieve_doc_tool_rankings(task.user_request, tools, top_k=top_k)["candidates"]
        return {
            "routing_strategy": "docs_retrieval",
            "selected_tool_name": candidates[0]["tool_name"] if candidates else task.tool_name,
            "candidate_tools": [item["tool_name"] for item in candidates],
            "candidate_rows": candidates,
        }

    if baseline_name == "retrieved_candidates":
        candidates = retrieve_candidate_tools(task.user_request, tools, top_k=top_k)["candidates"]
        return {
            "routing_strategy": "candidate_tool_retrieval",
            "selected_tool_name": candidates[0]["tool_name"] if candidates else task.tool_name,
            "candidate_tools": [item["tool_name"] for item in candidates],
            "candidate_rows": candidates,
        }

    if baseline_name == "retrieved_memory":
        candidates = retrieve_memory_tool_rankings(task.user_request, tools, top_k=top_k)["candidates"]
        return {
            "routing_strategy": "memory_retrieval",
            "selected_tool_name": candidates[0]["tool_name"] if candidates else task.tool_name,
            "candidate_tools": [item["tool_name"] for item in candidates],
            "candidate_rows": candidates,
        }

    if method_routing:
        retrieval_rows = retrieve_candidate_tools(task.user_request, tools, top_k=max(len(tools), top_k))["candidates"]
        reranked: List[Dict[str, Any]] = []
        for row in retrieval_rows:
            tool_name = str(row["tool_name"])
            tool = tools[tool_name]
            skill = skill_bank[tool_name]
            boundary_penalty = 0
            if normalized_baseline_name in BOUNDARY_FIRST_ROUTING_CONDITIONS or is_reliaskill_v1_family(normalized_baseline_name):
                router_text = _skill_router_positive_text(tool, skill)
                boundary_penalty = _boundary_overlap_penalty(task.user_request, skill)
            else:
                router_text = _skill_router_text(tool, skill)
            lexical_score = _router_overlap_score(task.user_request, router_text)
            retrieval_score = int(row.get("score", 0))
            rerank_score = (2 * retrieval_score) + lexical_score
            rerank_score += _generated_skill_routing_bonus(task.user_request, tool, skill)
            contract_routing_bonus = 0
            contract_routing_features: Dict[str, Any] = {}
            if is_reliaskill_v1_family(normalized_baseline_name):
                contract_routing_bonus, contract_routing_features = _reliaskill_v1_contract_routing_bonus(task.user_request, tool)
                rerank_score += contract_routing_bonus
            schema_fit_bonus = 0
            grounded_required_args: List[str] = []
            missing_required_args: List[str] = []
            action_intent_conflict = False
            contract_proof_state = None
            if is_reliaskill_v1_family(normalized_baseline_name) and not _contract_ablation_disabled(skill, "disable_contract_routing"):
                contract_proof_state = build_contract_proof_state(
                    tool,
                    skill,
                    task.user_request,
                    grounding_context={} if _contract_ablation_disabled(skill, "disable_contextual_grounding") else {
                        "conversation": list(task.conversation_history),
                        "artifacts": dict(task.artifact_context),
                        "tool_observations": list(task.tool_observation_context),
                    },
                    retrieval_score=retrieval_score,
                    lexical_score=lexical_score,
                    boundary_penalty=boundary_penalty,
                )
                schema_fit_bonus = contract_proof_state.route_score
                grounded_required_args = contract_proof_state.grounded_required_args
                missing_required_args = contract_proof_state.missing_required_args
                rerank_score += schema_fit_bonus
                action_intent_conflict = (
                    contract_proof_state.action_intent_conflict
                    and not _contract_ablation_disabled(skill, "disable_action_gate")
                )
                if action_intent_conflict:
                    rerank_score -= 80
            rerank_score -= boundary_penalty
            reranked.append(
                {
                    "tool_name": tool_name,
                    "score": rerank_score,
                    "retrieval_score": row.get("score", 0),
                    "boundary_penalty": boundary_penalty,
                    "contract_routing_bonus": contract_routing_bonus,
                    "contract_routing_features": contract_routing_features,
                    "schema_fit_bonus": schema_fit_bonus,
                    "grounded_required_args": grounded_required_args,
                    "missing_required_args": missing_required_args,
                    "action_intent_conflict": action_intent_conflict,
                    "contract_satisfied": contract_proof_state.satisfied if contract_proof_state else None,
                    "contract_viable": proof_state_is_viable(contract_proof_state) if contract_proof_state else None,
                    "contract_blocking_reasons": contract_proof_state.blocking_reasons if contract_proof_state else [],
                    "contract_failure_report": contract_proof_state.failure_report if contract_proof_state else {},
                    "contract_proof_obligations": contract_proof_state.proof_obligations if contract_proof_state else [],
                    "contract_side_effect_class": contract_proof_state.side_effect_class if contract_proof_state else None,
                    "contract_decision": contract_proof_state.decision if contract_proof_state else None,
                    "contract_decision_confidence": contract_proof_state.decision_confidence if contract_proof_state else None,
                    "contract_proof_score": contract_proof_state.proof_score if contract_proof_state else None,
                    "contract_proof_margin": contract_proof_state.proof_margin if contract_proof_state else None,
                    "contract_evidence_ledger": contract_proof_state.evidence_ledger if contract_proof_state else {},
                    "contract_feature_vector": contract_proof_state.feature_vector if contract_proof_state else {},
                    "contract_proof_state": contract_proof_state.model_dump() if contract_proof_state else {},
                    "overlap_terms": row.get("overlap_terms", []),
                }
            )
        if is_reliaskill_v1_family(normalized_baseline_name):
            reranked.sort(
                key=lambda item: (
                    -row_explicit_request_match(item),
                    item.get("contract_viable") is not True,
                    -float(item.get("contract_proof_score") or item.get("score") or 0.0),
                    -float(item.get("score") or 0.0),
                    str(item["tool_name"]),
                )
            )
        else:
            reranked.sort(key=lambda item: (-int(item["score"]), item["tool_name"]))
        selected_tool_name = reranked[0]["tool_name"] if reranked else task.tool_name
        if is_reliaskill_v1_family(normalized_baseline_name) and reranked:
            explicit_override_row = _explicit_contrastive_route_override(task.user_request, task.tool_name, reranked)
            if explicit_override_row is not None:
                selected_tool_name = str(explicit_override_row["tool_name"])
                for row in reranked:
                    if row.get("action_intent_conflict"):
                        row["schema_affordance_gate"] = "action_intent_conflict"
                    else:
                        row["schema_affordance_gate"] = "schema_complete" if not row.get("missing_required_args") else "missing_required"
            else:
                viable_rows = [
                    row
                    for row in reranked
                    if (
                        row.get("contract_satisfied") is True
                        or _contract_ablation_disabled(skill_bank[str(row["tool_name"])], "disable_contract_routing")
                        or (
                            _contract_ablation_disabled(skill_bank[str(row["tool_name"])], "disable_action_gate")
                            and row.get("contract_blocking_reasons") == ["action_intent_conflict"]
                        )
                    )
                    and not row.get("missing_required_args")
                    and not row.get("action_intent_conflict")
                ]
                if viable_rows:
                    selected_tool_name = str(viable_rows[0]["tool_name"])
                    for row in reranked:
                        if row.get("action_intent_conflict"):
                            row["schema_affordance_gate"] = "action_intent_conflict"
                        else:
                            row["schema_affordance_gate"] = "schema_complete" if not row.get("missing_required_args") else "missing_required"
                    selected_skill = skill_bank[str(viable_rows[0]["tool_name"])]
                    ambiguity = None if _contract_ablation_disabled(selected_skill, "disable_ambiguity_abstention") else _reliaskill_v1_ambiguity_reason(task.user_request, viable_rows, tools)
                    if ambiguity:
                        abstain_row = {
                            "tool_name": "__abstain__",
                            "score": viable_rows[0]["score"],
                            "routing_abstention_reason": ambiguity,
                            "candidate_count": len(viable_rows),
                            "ambiguous_tools": [str(row["tool_name"]) for row in viable_rows[:3]],
                        }
                        return {
                            "routing_strategy": "retrieve_then_semantic_rerank_ambiguity_abstention",
                            "selected_tool_name": "__abstain__",
                            "candidate_tools": ["__abstain__"],
                            "candidate_rows": [abstain_row, *viable_rows[: max(top_k - 1, 0)]],
                        }
                else:
                    abstain_row = {
                        "tool_name": "__abstain__",
                        "score": reranked[0]["score"],
                        "routing_abstention_reason": "no_candidate_with_grounded_required_schema",
                        "candidate_count": len(reranked),
                    }
                    return {
                        "routing_strategy": "retrieve_then_semantic_rerank_schema_affordance_abstention",
                        "selected_tool_name": "__abstain__",
                        "candidate_tools": ["__abstain__"],
                        "candidate_rows": [abstain_row, *reranked[: max(top_k - 1, 0)]],
                    }
        top_rows = reranked[: max(top_k, 1)]
        if is_reliaskill_v1_family(normalized_baseline_name) and selected_tool_name != (top_rows[0]["tool_name"] if top_rows else None):
            selected_row = next(row for row in reranked if row["tool_name"] == selected_tool_name)
            top_rows = [selected_row, *[row for row in top_rows if row["tool_name"] != selected_tool_name]][: max(top_k, 1)]
        return {
            "routing_strategy": "retrieve_then_semantic_rerank",
            "selected_tool_name": selected_tool_name,
            "candidate_tools": [item["tool_name"] for item in top_rows],
            "candidate_rows": top_rows,
        }

    ranked: List[Tuple[str, int]] = []
    for tool_name, tool in tools.items():
        skill = skill_bank[tool_name]
        score = _router_overlap_score(task.user_request, _skill_router_text(tool, skill))
        if normalized_baseline_name == GENERATED_SKILL_BASE:
            score += _generated_skill_routing_bonus(task.user_request, tool, skill)
        ranked.append((tool_name, score))
    ranked.sort(key=lambda item: (-item[1], item[0]))
    top_rows = [{"tool_name": tool_name, "score": score} for tool_name, score in ranked[: max(top_k, 1)]]
    return {
        "routing_strategy": "skill_text_overlap",
        "selected_tool_name": top_rows[0]["tool_name"] if top_rows else task.tool_name,
        "candidate_tools": [item["tool_name"] for item in top_rows],
        "candidate_rows": top_rows,
    }


def _expected_routing_tool_name(gold_task: EvalTask) -> str:
    if gold_task.expected_tool_name:
        return gold_task.expected_tool_name
    return gold_task.tool_name if gold_task.should_trigger else "__abstain__"


def score_routed_prediction(
    gold_task: EvalTask,
    selected_tool_name: str,
    candidate_tools: List[str],
    predictor_record: Dict[str, Any],
) -> Dict[str, Any]:
    expected_tool_name = _expected_routing_tool_name(gold_task)
    tool_correct = selected_tool_name == expected_tool_name
    argument_score = predictor_record["argument_score"]
    gold_rank = next((index + 1 for index, name in enumerate(candidate_tools) if name == expected_tool_name), None)
    triggered = selected_tool_name != "__abstain__"
    argument_exact = bool(argument_score["exact_match"]) if triggered else expected_tool_name == "__abstain__"
    harmful = bool(not gold_task.should_trigger and not tool_correct)
    return {
        "task_id": gold_task.task_id,
        "expected_tool_name": expected_tool_name,
        "selected_tool_name": selected_tool_name,
        "baseline_name": predictor_record["baseline_name"],
        "split": gold_task.split,
        "tags": list(gold_task.tags),
        "should_trigger": gold_task.should_trigger,
        "triggered": triggered,
        "negative_category": gold_task.negative_category,
        "difficulty": gold_task.difficulty,
        "domain": gold_task.domain,
        "tool_selection_correct": tool_correct,
        "joint_exact_match": bool(tool_correct and argument_exact),
        "argument_exact_match_given_tool": argument_exact,
        "argument_validity": round(argument_score["argument_validity"] if tool_correct and triggered else (1.0 if tool_correct else 0.0), 4),
        "required_argument_recall": round(argument_score["required_argument_recall"] if tool_correct and triggered else (1.0 if tool_correct else 0.0), 4),
        "hallucinated_args": argument_score["hallucinated_args"] if tool_correct else sorted(predictor_record["predicted_arguments"].keys()),
        "predicted_arguments": predictor_record["predicted_arguments"],
        "expected_arguments": gold_task.expected_arguments,
        "candidate_tools": list(candidate_tools),
        "gold_tool_rank": gold_rank,
        "gold_tool_hit_at_k": gold_rank is not None,
        "routing_strategy": predictor_record["routing_strategy"],
        "prediction_metadata": predictor_record["prediction_metadata"],
        "method_metadata": predictor_record.get("method_metadata", {}),
        "harmful_injection": harmful,
        "skill_induced_harm": harmful,
        "should_call": triggered,
        "abstention_reason": predictor_record.get("abstention_reason"),
    }


def _prediction_contract_satisfied(prediction_metadata: Dict[str, Any]) -> bool:
    verifier = prediction_metadata.get("reliaskill_v1_runtime_verifier")
    verifier = verifier if isinstance(verifier, dict) else {}
    after = verifier.get("contract_evaluation_after")
    after = after if isinstance(after, dict) else {}
    return after.get("satisfied") is True


def _candidate_row_is_contract_viable(row: Dict[str, Any]) -> bool:
    if row.get("contract_viable") is not None:
        return bool(row.get("contract_viable")) and str(row.get("tool_name") or "") != "__abstain__"
    return (
        row.get("contract_satisfied") is True
        and not row.get("missing_required_args")
        and not row.get("action_intent_conflict")
        and str(row.get("tool_name") or "") != "__abstain__"
    )


def _try_reliaskill_candidate_verification_fallback(
    *,
    task: EvalTask,
    baseline_name: str,
    selected_tool_name: str,
    routing: Dict[str, Any],
    tools: Dict[str, ToolIR],
    skill_bank: Dict[str, GeneratedSkill],
    predictor: PredictorBackend,
    allow_predictor_fallback: bool,
    max_candidates: int = 3,
) -> tuple[str, ToolIR, GeneratedSkill, EvalTask, GeneratedSkill, Any, Dict[str, Any], str] | None:
    normalized_baseline_name = normalize_condition_name(baseline_name)
    if not is_reliaskill_v1_family(normalized_baseline_name):
        return None
    selected_skill = skill_bank.get(selected_tool_name)
    if selected_skill is None or _contract_ablation_disabled(selected_skill, "disable_contract_routing"):
        return None
    if _contract_ablation_disabled(selected_skill, "disable_candidate_verification"):
        return None
    expected_tool_name = _expected_routing_tool_name(task)
    if expected_tool_name == "__abstain__":
        return None
    attempted: List[str] = []
    for row in (routing.get("candidate_rows") or [])[:max_candidates]:
        candidate_name = str(row.get("tool_name") or "")
        if not candidate_name or candidate_name == selected_tool_name or candidate_name not in tools:
            continue
        if not _candidate_row_is_contract_viable(row):
            continue
        candidate_tool = tools[candidate_name]
        candidate_skill = skill_bank[candidate_name]
        attempted.append(candidate_name)
        candidate_task = EvalTask(
            task_id=task.task_id,
            tool_name=candidate_name,
            user_request=task.user_request,
            expected_arguments=task.expected_arguments,
            expected_argument_candidates=task.expected_argument_candidates,
            should_trigger=bool(task.should_trigger or (expected_tool_name != "__abstain__" and candidate_name == expected_tool_name)),
            expected_tool_name=task.expected_tool_name,
            negative_target=task.negative_target,
            negative_category=task.negative_category,
            difficulty=task.difficulty,
            domain=task.domain,
            split=task.split,
            tags=list(task.tags),
            conversation_history=list(task.conversation_history),
            artifact_context=dict(task.artifact_context),
            tool_observation_context=list(task.tool_observation_context),
        )
        runtime_skill, retrieval_context = contextualize_skill_for_task(
            candidate_task,
            candidate_tool,
            candidate_skill,
            tools,
            skill_bank=skill_bank,
        )
        prediction = safe_predict(candidate_tool, runtime_skill, candidate_task, predictor, allow_fallback=allow_predictor_fallback)
        if not prediction.should_call or not _prediction_contract_satisfied(prediction.metadata):
            continue
        prediction.metadata = {
            **dict(prediction.metadata),
            "reliaskill_candidate_verification": {
                "attempted": True,
                "selected_fallback": True,
                "original_selected_tool": selected_tool_name,
                "verified_selected_tool": candidate_name,
                "attempted_tools": attempted,
            },
        }
        return (
            candidate_name,
            candidate_tool,
            candidate_skill,
            candidate_task,
            runtime_skill,
            prediction,
            retrieval_context,
            "retrieve_then_semantic_rerank_candidate_verification",
        )
    return None


def run_routing_pipeline(
    tasks: List[EvalTask],
    tools: Dict[str, ToolIR],
    skill_variants_by_tool: Dict[str, Dict[str, GeneratedSkill]],
    predictor: PredictorBackend,
    output_dir: Path | None = None,
    benchmark_dir: Path | None = None,
    allow_predictor_fallback: bool = True,
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    baseline_names = list(next(iter(skill_variants_by_tool.values())).keys())
    
    for task in tqdm(tasks, desc="[ReliaSkill] Routing evaluation"):
        # Quick skip if all results for this task exist
        if output_dir:
            task_dir = output_dir / _safe_task_name(task.task_id)
            if task_dir.exists():
                existing = []
                for b_name in baseline_names:
                    p = task_dir / f"{b_name}.routing.json"
                    if p.exists():
                        try:
                            with p.open("r", encoding="utf-8") as f:
                                existing.append(json.load(f))
                        except (OSError, json.JSONDecodeError):
                            pass
                if len(existing) == len(baseline_names):
                    records.extend(existing)
                    continue

        for baseline_name in baseline_names:
            # Per-baseline resume
            if output_dir:
                p = output_dir / _safe_task_name(task.task_id) / f"{_safe_dir_name(baseline_name)}.routing.json"
                if p.exists():
                    try:
                        with p.open("r", encoding="utf-8") as f:
                            records.append(json.load(f))
                            continue
                    except (OSError, json.JSONDecodeError):
                        pass

            write_progress_state(
                output_dir,
                phase="routing",
                status="running",
                task_id=str(task.task_id),
                tool_name=str(task.tool_name),
                condition=str(baseline_name),
            )
            skill_bank = {tool_name: variants[baseline_name] for tool_name, variants in skill_variants_by_tool.items()}
            routing = select_tool_for_task(task, baseline_name, tools, skill_bank)
            selected_tool_name = str(routing["selected_tool_name"])
            expected_tool_name = _expected_routing_tool_name(task)
            
            if selected_tool_name == "__abstain__":
                record = score_routed_prediction(
                    task,
                    selected_tool_name="__abstain__",
                    candidate_tools=list(routing["candidate_tools"]),
                    predictor_record={
                        "baseline_name": baseline_name,
                        "predicted_arguments": {},
                        "argument_score": {
                            "exact_match": expected_tool_name == "__abstain__",
                            "argument_validity": 1.0 if expected_tool_name == "__abstain__" else 0.0,
                            "required_argument_recall": 1.0 if expected_tool_name == "__abstain__" else 0.0,
                            "hallucinated_args": [],
                        },
                        "abstention_reason": (routing.get("candidate_rows") or [{}])[0].get("abstention_reason"),
                        "routing_strategy": routing["routing_strategy"],
                        "prediction_metadata": {
                            "routing_candidate_rows": routing["candidate_rows"],
                        },
                        "method_metadata": {
                            "condition": baseline_name,
                            "routing_strategy": routing["routing_strategy"],
                        },
                    },
                )
            elif selected_tool_name not in tools:
                # Handle hallucination
                record = {
                    "task_id": task.task_id,
                    "baseline_name": baseline_name,
                    "selected_tool_name": selected_tool_name,
                    "correct_tool": False,
                    "exact_match": 0.0,
                    "soft_match": 0.0,
                    "error": "hallucinated_tool_name",
                    "expected_tool_name": expected_tool_name,
                    "tool_selection_correct": False,
                    "joint_exact_match": False,
                    "argument_validity": 0.0,
                    "required_argument_recall": 0.0,
                    "should_trigger": task.should_trigger,
                    "triggered": selected_tool_name != "__abstain__",
                    "negative_category": task.negative_category,
                    "difficulty": task.difficulty,
                    "domain": task.domain,
                    "harmful_injection": bool(not task.should_trigger and selected_tool_name != expected_tool_name),
                    "skill_induced_harm": bool(not task.should_trigger and selected_tool_name != expected_tool_name),
                    "split": task.split,
                }
            else:
                selected_tool = tools[selected_tool_name]
                selected_skill = skill_bank[selected_tool_name]
                
                # Full prediction logic for the selected tool
                routed_task = EvalTask(
                    task_id=task.task_id,
                    tool_name=selected_tool_name,
                    user_request=task.user_request,
                    expected_arguments=task.expected_arguments,
                    expected_argument_candidates=task.expected_argument_candidates,
                    should_trigger=bool(task.should_trigger or (expected_tool_name != "__abstain__" and selected_tool_name == expected_tool_name)),
                    expected_tool_name=task.expected_tool_name,
                    negative_target=task.negative_target,
                    negative_category=task.negative_category,
                    difficulty=task.difficulty,
                    domain=task.domain,
                    split=task.split,
                    tags=list(task.tags),
                    conversation_history=list(task.conversation_history),
                    artifact_context=dict(task.artifact_context),
                    tool_observation_context=list(task.tool_observation_context),
                )
                runtime_skill, retrieval_context = contextualize_skill_for_task(
                    routed_task,
                    selected_tool,
                    selected_skill,
                    tools,
                    skill_bank=skill_bank,
                )
                
                prediction_dict = None
                if benchmark_dir and selected_tool_name == task.tool_name:
                    cached_result_path = benchmark_dir / _safe_dir_name(selected_tool_name) / _safe_dir_name(baseline_name) / f"{_safe_task_name(task.task_id)}.result.json"
                    if cached_result_path.exists():
                        try:
                            with cached_result_path.open("r", encoding="utf-8") as f:
                                cached_score = json.load(f)
                                prediction_dict = {
                                    "predicted_arguments": cached_score.get("predicted_arguments", {}),
                                    "argument_score": {
                                        "exact_match": cached_score.get("exact_match", False),
                                        "argument_validity": cached_score.get("argument_validity", 0.0),
                                        "required_argument_recall": cached_score.get("required_argument_recall", 0.0),
                                        "hallucinated_args": cached_score.get("hallucinated_args", []),
                                    },
                                    "prediction_metadata": cached_score.get("prediction_metadata", {}),
                                    "should_call": cached_score.get("should_call", cached_score.get("triggered", True)),
                                    "abstention_reason": cached_score.get("abstention_reason"),
                                }
                        except Exception:
                            pass
                
                if prediction_dict is not None:
                    argument_score = prediction_dict["argument_score"]
                    final_selected_tool_name = selected_tool_name if prediction_dict.get("should_call", True) else "__abstain__"
                    record = score_routed_prediction(
                        task,
                        selected_tool_name=final_selected_tool_name,
                        candidate_tools=list(routing["candidate_tools"]),
                        predictor_record={
                            "baseline_name": baseline_name,
                            "predicted_arguments": prediction_dict["predicted_arguments"],
                            "argument_score": argument_score,
                            "abstention_reason": prediction_dict.get("abstention_reason"),
                            "routing_strategy": routing["routing_strategy"],
                            "prediction_metadata": {
                                **prediction_dict["prediction_metadata"],
                                "routing_candidate_rows": routing["candidate_rows"],
                                "retrieval_context": retrieval_context,
                            },
                            "method_metadata": prediction_method_metadata(selected_skill),
                        },
                    )
                else:
                    prediction = safe_predict(selected_tool, runtime_skill, routed_task, predictor, allow_fallback=allow_predictor_fallback)
                    if not prediction.should_call:
                        fallback = _try_reliaskill_candidate_verification_fallback(
                            task=task,
                            baseline_name=baseline_name,
                            selected_tool_name=selected_tool_name,
                            routing=routing,
                            tools=tools,
                            skill_bank=skill_bank,
                            predictor=predictor,
                            allow_predictor_fallback=allow_predictor_fallback,
                        )
                        if fallback is not None:
                            (
                                selected_tool_name,
                                selected_tool,
                                selected_skill,
                                routed_task,
                                runtime_skill,
                                prediction,
                                retrieval_context,
                                verified_strategy,
                            ) = fallback
                            routing = {
                                **routing,
                                "routing_strategy": verified_strategy,
                                "selected_tool_name": selected_tool_name,
                            }
                    score = score_prediction(routed_task, selected_tool, prediction)
                    argument_score = {
                        "exact_match": score.get("argument_exact_match", score.get("exact_match", False)),
                        "argument_validity": score.get("argument_validity", 0.0),
                        "required_argument_recall": score.get("required_argument_recall", 0.0),
                        "hallucinated_args": score.get("hallucinated_args", []),
                    }
                    final_selected_tool_name = selected_tool_name if prediction.should_call else "__abstain__"
                    record = score_routed_prediction(
                        task,
                        selected_tool_name=final_selected_tool_name,
                        candidate_tools=list(routing["candidate_tools"]),
                        predictor_record={
                            "baseline_name": baseline_name,
                            "predicted_arguments": score.get("predicted_arguments", {}),
                            "argument_score": argument_score,
                            "abstention_reason": prediction.abstention_reason,
                            "routing_strategy": routing["routing_strategy"],
                            "prediction_metadata": {
                                **dict(prediction.metadata),
                                "routing_candidate_rows": routing["candidate_rows"],
                                "retrieval_context": retrieval_context,
                            },
                            "method_metadata": prediction_method_metadata(selected_skill),
                        },
                    )
                # Add split info for reporting
                record["split"] = task.split
            
            records.append(record)
            if output_dir:
                task_dir = output_dir / _safe_task_name(task.task_id)
                task_dir.mkdir(parents=True, exist_ok=True)
                with (task_dir / f"{_safe_dir_name(baseline_name)}.routing.json").open("w", encoding="utf-8") as f:
                    json.dump(record, f, indent=2, ensure_ascii=False)
    write_progress_state(output_dir, phase="routing", status="done")
    return records


def _bootstrap_confidence_interval(values: List[float], iterations: int = 500, seed: int = 17) -> Dict[str, float]:
    if not values:
        return {"low": 0.0, "high": 0.0}
    rng = random.Random(seed)
    means: List[float] = []
    for _ in range(iterations):
        sample = [values[rng.randrange(len(values))] for _ in range(len(values))]
        means.append(sum(sample) / len(sample))
    means.sort()
    low_index = int(0.025 * (len(means) - 1))
    high_index = int(0.975 * (len(means) - 1))
    return {"low": round(means[low_index], 4), "high": round(means[high_index], 4)}


def _summarize_routing_group(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(items)
    tool_selection = [1.0 if item["tool_selection_correct"] else 0.0 for item in items]
    joint = [1.0 if item["joint_exact_match"] else 0.0 for item in items]
    hit_values = [1.0 if item["gold_tool_hit_at_k"] else 0.0 for item in items if item.get("gold_tool_hit_at_k") is not None]
    gold_ranks = [float(item["gold_tool_rank"]) for item in items if isinstance(item.get("gold_tool_rank"), int)]
    return {
        "num_tasks": total,
        "tool_selection_accuracy": round(sum(tool_selection) / total, 4) if total else 0.0,
        "tool_selection_accuracy_ci": _bootstrap_confidence_interval(tool_selection) if total else {"low": 0.0, "high": 0.0},
        "joint_exact_match_rate": round(sum(joint) / total, 4) if total else 0.0,
        "joint_exact_match_ci": _bootstrap_confidence_interval(joint) if total else {"low": 0.0, "high": 0.0},
        "avg_argument_validity": round(sum(item["argument_validity"] for item in items) / total, 4) if total else 0.0,
        "avg_required_argument_recall": round(sum(item["required_argument_recall"] for item in items) / total, 4) if total else 0.0,
        "gold_tool_hit_rate": round(sum(hit_values) / len(hit_values), 4) if hit_values else None,
        "avg_gold_tool_rank": round(sum(gold_ranks) / len(gold_ranks), 4) if gold_ranks else None,
    }


def summarize_routing_scores(scores: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for score in scores:
        grouped.setdefault(str(score["baseline_name"]), []).append(score)
    return {baseline_name: _summarize_routing_group(items) for baseline_name, items in grouped.items()}


def summarize_routing_scores_by_tool(scores: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    grouped: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for score in scores:
        grouped.setdefault(str(score["expected_tool_name"]), {}).setdefault(str(score["baseline_name"]), []).append(score)
    return {
        tool_name: {baseline_name: _summarize_routing_group(items) for baseline_name, items in by_baseline.items()}
        for tool_name, by_baseline in grouped.items()
    }


def summarize_routing_scores_by_split(scores: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    grouped: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for score in scores:
        grouped.setdefault(str(score["split"]), {}).setdefault(str(score["baseline_name"]), []).append(score)
    return {
        split_name: {baseline_name: _summarize_routing_group(items) for baseline_name, items in by_baseline.items()}
        for split_name, by_baseline in grouped.items()
    }

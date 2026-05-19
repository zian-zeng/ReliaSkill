from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List

from autoskill.ir import ArgumentIR, ToolIR


_DOC_ALIAS_GROUPS = [
    {"find", "search", "lookup", "locate", "query", "retrieve"},
    {"read", "show", "view", "open", "display", "fetch"},
    {"create", "add", "insert", "new", "make", "ensure"},
    {"update", "edit", "modify", "patch", "write", "save", "append"},
    {"delete", "remove", "clear", "drop"},
    {"path", "file", "directory", "folder", "location"},
    {"content", "text", "body", "message", "payload"},
    {"account", "acct", "customer", "client", "user"},
    {"identifier", "id", "name", "title", "key"},
]
_DOC_ALIASES: Dict[str, set[str]] = {}
for _group in _DOC_ALIAS_GROUPS:
    for _term in _group:
        _DOC_ALIASES[_term] = set(_group)


def build_doc_grounding_evidence(
    tool: ToolIR,
    *,
    max_doc_snippets: int = 4,
    max_snippet_chars: int = 320,
    enable_consistency_shield: bool = True,
) -> Dict[str, Any]:
    """Build a compact source-document digest for ReliaSkill v1 prompts/contracts."""
    ranked = _filter_contract_consistent_snippets(
        tool,
        tool.doc_snippets or [],
        limit=max_doc_snippets,
        enable_consistency_shield=enable_consistency_shield,
    )
    evidence: Dict[str, Any] = {
        "tool_purpose": _trim(tool.tool_purpose or "", max_snippet_chars),
        "doc_snippets": [
            _trim(snippet, max_snippet_chars)
            for snippet in ranked["kept"]
        ],
        "arguments": [_argument_evidence(arg) for arg in tool.arguments],
        "doc_contract_consistency": ranked["summary"],
    }
    if ranked["suppressed"]:
        evidence["suppressed_doc_snippets"] = [
            {"reason": item["reason"], "text": _trim(item["text"], max_snippet_chars)}
            for item in ranked["suppressed"][:4]
        ]
    if tool.output_hint:
        evidence["output_hint"] = _trim(tool.output_hint, max_snippet_chars)
    if tool.usage_warnings:
        evidence["usage_warnings"] = _trim_list(tool.usage_warnings, limit=4, max_chars=max_snippet_chars)
    if tool.side_effect_hints:
        evidence["side_effect_hints"] = _trim_list(tool.side_effect_hints, limit=4, max_chars=max_snippet_chars)
    if tool.safety_hints:
        evidence["safety_hints"] = _trim_list(tool.safety_hints, limit=4, max_chars=max_snippet_chars)
    return {key: value for key, value in evidence.items() if not _empty(value)}


def build_request_conditioned_doc_evidence(
    tool: ToolIR,
    request: str,
    *,
    max_doc_snippets: int = 6,
    max_snippet_chars: int = 480,
    enable_consistency_shield: bool = True,
) -> Dict[str, Any]:
    """Build a request-relevant doc digest so ReliaSkill can compete with raw docs."""
    evidence = build_doc_grounding_evidence(
        tool,
        max_doc_snippets=0,
        max_snippet_chars=max_snippet_chars,
        enable_consistency_shield=enable_consistency_shield,
    )
    request_tokens = _tokenize(request)
    candidates = [snippet for snippet in (tool.doc_snippets or []) if str(snippet).strip()]
    candidates.extend(tool.usage_warnings)
    candidates.extend(tool.side_effect_hints)
    consistency = _filter_contract_consistent_snippets(
        tool,
        candidates,
        limit=max_doc_snippets,
        enable_consistency_shield=enable_consistency_shield,
    )
    ranked_snippets = _rank_doc_snippets(consistency["kept"], request_tokens)
    if ranked_snippets:
        evidence["request_relevant_doc_snippets"] = [
            _trim(snippet, max_snippet_chars) for snippet in ranked_snippets[:max_doc_snippets]
        ]
    if consistency["suppressed"]:
        evidence["request_suppressed_doc_snippets"] = [
            {"reason": item["reason"], "text": _trim(item["text"], max_snippet_chars)}
            for item in consistency["suppressed"][:4]
        ]
    relevant_arguments = [
        _argument_evidence(arg)
        for arg in tool.arguments
        if arg.required or _argument_matches_request(arg, request_tokens)
    ]
    if relevant_arguments:
        evidence["request_relevant_arguments"] = relevant_arguments
    evidence["request_doc_evidence_policy"] = {
        "selection": "schema_semantic_request_overlap_then_length",
        "raw_docs_preserved": bool(ranked_snippets),
        "schema_contract_remains_authoritative": True,
        "contract_consistency_shield": consistency["summary"],
    }
    return {key: value for key, value in evidence.items() if not _empty(value)}


def render_doc_grounding_evidence(evidence: Dict[str, Any], *, max_chars: int = 2200) -> str:
    if not isinstance(evidence, dict) or not evidence:
        return ""
    text = json.dumps(evidence, ensure_ascii=False, sort_keys=True)
    return _trim(text, max_chars)


def _argument_evidence(arg: ArgumentIR) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "name": arg.name,
        "type": arg.type,
        "required": bool(arg.required),
    }
    if arg.description:
        row["description"] = _trim(arg.description, 240)
    if arg.enum:
        row["enum"] = [str(item) for item in arg.enum[:12]]
    if arg.format:
        row["format"] = arg.format
    nested_required = _nested_required(arg)
    if nested_required:
        row["nested_required"] = nested_required
    return row


def _nested_required(arg: ArgumentIR) -> List[str]:
    paths: List[str] = []
    if arg.required_properties:
        paths.extend(f"{arg.name}.{child}" for child in arg.required_properties)
    if isinstance(arg.items_schema, dict):
        required = arg.items_schema.get("required")
        if isinstance(required, list):
            paths.extend(f"{arg.name}[].{child}" for child in required if isinstance(child, str))
    return sorted(set(paths))


def _trim_list(values: Iterable[Any], *, limit: int, max_chars: int) -> List[str]:
    return [_trim(str(value), max_chars) for value in values if str(value).strip()][:limit]


def _rank_doc_snippets(snippets: Iterable[str], request_tokens: List[str]) -> List[str]:
    unique: List[str] = []
    seen: set[str] = set()
    for snippet in snippets:
        normalized = " ".join(str(snippet).split())
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
    return sorted(unique, key=lambda snippet: (-_snippet_score(snippet, request_tokens), -len(snippet), snippet))


def _filter_contract_consistent_snippets(
    tool: ToolIR,
    snippets: Iterable[str],
    *,
    limit: int,
    enable_consistency_shield: bool = True,
) -> Dict[str, Any]:
    kept: List[str] = []
    suppressed: List[Dict[str, str]] = []
    for snippet in snippets:
        normalized = " ".join(str(snippet).split())
        if not normalized:
            continue
        reason = _doc_contract_conflict_reason(tool, normalized) if enable_consistency_shield else None
        if reason:
            suppressed.append({"reason": reason, "text": normalized})
            continue
        if normalized not in kept:
            kept.append(normalized)
    return {
        "kept": kept[: max(limit, 0)] if limit >= 0 else kept,
        "suppressed": suppressed,
        "summary": {
            "checked": len(kept) + len(suppressed),
            "kept": min(len(kept), max(limit, 0)) if limit >= 0 else len(kept),
            "suppressed": len(suppressed),
            "policy": (
                "suppress_schema_side_effect_or_instruction_conflicting_doc_snippets"
                if enable_consistency_shield
                else "consistency_shield_disabled"
            ),
        },
    }


def _doc_contract_conflict_reason(tool: ToolIR, snippet: str) -> str | None:
    unsupported = sorted(_unsupported_argument_mentions(snippet) - {arg.name for arg in tool.arguments})
    if unsupported:
        return "unsupported_argument_mentions:" + ",".join(unsupported[:3])
    injection_reason = _doc_instruction_injection_reason(snippet)
    if injection_reason:
        return injection_reason
    snippet_actions = _doc_action_families(snippet) - _negated_doc_action_families(snippet)
    tool_actions = _doc_action_families(" ".join([tool.tool_name, tool.tool_purpose or "", *(tool.side_effect_hints or []), *(tool.safety_hints or [])]))
    mutating = {"create", "update", "delete", "send"}
    readonly = {"search", "read"}
    if snippet_actions.intersection(mutating) and tool_actions.intersection(readonly) and not tool_actions.intersection(mutating):
        return "side_effect_conflict"
    return None


def _doc_instruction_injection_reason(snippet: str) -> str | None:
    lowered = snippet.lower()
    if (
        _has_unsafe_imperative(
            lowered,
            verbs=("ignore", "disregard", "override", "forget"),
            targets=("schema", "contract", "validation", "validator", "instructions", "system", "developer", "rules", "requirements"),
        )
        or _has_unsafe_imperative(
            lowered,
            verbs=("bypass", "skip", "disable"),
            targets=("schema", "contract", "validation", "validator", "safety", "boundary", "gate", "checks"),
        )
        or _has_unsafe_imperative(
            lowered,
            verbs=("invent", "fabricate", "hallucinate"),
            targets=("argument", "arguments", "parameter", "parameters", "field", "fields", "input", "inputs", "value", "values", "id", "identifier"),
        )
        or _has_unsafe_imperative(
            lowered,
            verbs=("make up",),
            targets=("argument", "arguments", "parameter", "parameters", "field", "fields", "input", "inputs", "value", "values", "id", "identifier"),
        )
        or re.search(r"\b(?:always|force)\b.{0,30}\b(?:call|invoke|execute|use)\b", lowered)
        or re.search(r"\b(?:set|return)\b.{0,40}\bshould_call\b.{0,20}\btrue\b", lowered)
        or re.search(r"\b(?:do not|don't|never)\b.{0,24}\b(?:obey|follow|respect|enforce)\b.{0,40}\b(?:schema|contract|validation|validator|instructions|rules)\b", lowered)
        or re.search(r"\b(?:instead|rather)\b.{0,30}\b(?:call|invoke|execute|use)\b", lowered)
        or re.search(r"\b(?:call|invoke|execute|use)\b.{0,30}\b(?:another|other|different)\b.{0,16}\btool\b", lowered)
    ):
        return "instruction_injection_conflict"
    return None


def _has_unsafe_imperative(text: str, *, verbs: Iterable[str], targets: Iterable[str]) -> bool:
    for verb in verbs:
        escaped_verb = re.escape(verb)
        if re.search(rf"\b(?:do not|don't|never|avoid)\s+{escaped_verb}\b", text):
            continue
        if re.search(rf"\b{escaped_verb}\b.{{0,48}}\b(?:{'|'.join(re.escape(target) for target in targets)})\b", text):
            return True
    return False


def _unsupported_argument_mentions(text: str) -> set[str]:
    result = set()
    for match in re.finditer(r"`([A-Za-z_][A-Za-z0-9_]*)`", text):
        window = text[max(0, match.start() - 32) : min(len(text), match.end() + 32)].lower()
        if not re.search(r"\b(?:field|argument|parameter|property|input|key)\b", window):
            continue
        value = match.group(1)
        if value not in {"true", "false", "null"}:
            result.add(value)
    return result


def _doc_action_families(text: str) -> set[str]:
    tokens = _semantic_token_set(text)
    families: set[str] = set()
    for family, cues in {
        "search": {"find", "search", "lookup", "locate", "query", "retrieve"},
        "read": {"read", "show", "view", "open", "display", "fetch"},
        "create": {"create", "add", "insert", "new", "make", "ensure"},
        "update": {"update", "edit", "modify", "patch", "write", "save", "append"},
        "delete": {"delete", "remove", "clear", "drop"},
        "send": {"send", "email", "notify", "post", "publish", "transfer"},
    }.items():
        if tokens.intersection(cues):
            families.add(family)
    return families


def _negated_doc_action_families(text: str) -> set[str]:
    lowered = text.lower()
    negated: set[str] = set()
    for family, cues in {
        "search": {"find", "search", "lookup", "locate", "query", "retrieve"},
        "read": {"read", "show", "view", "open", "display", "fetch"},
        "create": {"create", "add", "insert", "new", "make", "ensure"},
        "update": {"update", "edit", "modify", "patch", "write", "save", "append"},
        "delete": {"delete", "remove", "clear", "drop"},
        "send": {"send", "email", "notify", "post", "publish", "transfer"},
    }.items():
        if any(re.search(rf"\b(?:do not|don't|without|avoid|no|does not)\s+{re.escape(cue)}(?:ing|e|ed|s)?\b", lowered) for cue in cues):
            negated.add(family)
    return negated


def _snippet_score(snippet: str, request_tokens: List[str]) -> int:
    snippet_tokens = set(_tokenize(snippet))
    raw = sum(1 for token in request_tokens if token in snippet_tokens)
    semantic = len(_semantic_token_set(" ".join(request_tokens)).intersection(_semantic_token_set(snippet)) - snippet_tokens)
    return (2 * raw) + semantic


def _argument_matches_request(arg: ArgumentIR, request_tokens: List[str]) -> bool:
    arg_tokens = _semantic_token_set(arg.name)
    if arg.description:
        arg_tokens.update(_semantic_token_set(arg.description))
    return bool(arg_tokens.intersection(_semantic_token_set(" ".join(request_tokens))))


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9_./-]+", str(text or "").lower())


def _semantic_token_set(text: str) -> set[str]:
    expanded: set[str] = set()
    for token in _tokenize(text):
        for part in [token, *[part for part in re.split(r"[-_./]+", token) if part]]:
            normalized = _normalize_token(part)
            if not normalized:
                continue
            expanded.add(normalized)
            expanded.update(_DOC_ALIASES.get(normalized, set()))
    return expanded


def _normalize_token(token: str) -> str:
    token = token.strip("._-/").lower()
    if len(token) <= 1:
        return ""
    if token.endswith("ing") and len(token) > 5:
        token = token[:-3]
    elif token.endswith("ed") and len(token) > 4:
        token = token[:-2]
    elif token.endswith("s") and len(token) > 4:
        token = token[:-1]
    return token


def _trim(text: str, max_chars: int) -> str:
    clean = " ".join(str(text or "").split())
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 3].rstrip(" .,;:") + "..."


def _empty(value: Any) -> bool:
    return value == "" or value == [] or value == {}

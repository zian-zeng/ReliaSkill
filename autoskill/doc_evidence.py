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
) -> Dict[str, Any]:
    """Build a compact source-document digest for ReliaSkill v1 prompts/contracts."""
    evidence: Dict[str, Any] = {
        "tool_purpose": _trim(tool.tool_purpose or "", max_snippet_chars),
        "doc_snippets": [
            _trim(snippet, max_snippet_chars)
            for snippet in (tool.doc_snippets or [])
            if str(snippet).strip()
        ][:max_doc_snippets],
        "arguments": [_argument_evidence(arg) for arg in tool.arguments],
    }
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
) -> Dict[str, Any]:
    """Build a request-relevant doc digest so ReliaSkill can compete with raw docs."""
    evidence = build_doc_grounding_evidence(
        tool,
        max_doc_snippets=0,
        max_snippet_chars=max_snippet_chars,
    )
    request_tokens = _tokenize(request)
    candidates = [snippet for snippet in (tool.doc_snippets or []) if str(snippet).strip()]
    candidates.extend(tool.usage_warnings)
    candidates.extend(tool.side_effect_hints)
    ranked_snippets = _rank_doc_snippets(candidates, request_tokens)
    if ranked_snippets:
        evidence["request_relevant_doc_snippets"] = [
            _trim(snippet, max_snippet_chars) for snippet in ranked_snippets[:max_doc_snippets]
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

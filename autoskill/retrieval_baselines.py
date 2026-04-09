from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Set

from autoskill.ir import GeneratedSkill, ToolIR
from autoskill.templates import build_argument_template


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9_./*?-]+", text.lower())


def _tool_text(tool: ToolIR) -> str:
    parts = [tool.tool_name, tool.tool_purpose or "", *tool.doc_snippets, tool.output_hint or "", tool.auth_or_env_notes or ""]
    parts.extend(tool.usage_warnings)
    for arg in tool.arguments:
        parts.append(arg.name)
        if arg.description:
            parts.append(arg.description)
    return " ".join(part for part in parts if part)


def _tool_token_set(tool: ToolIR) -> Set[str]:
    return set(_tokenize(_tool_text(tool)))


def _snippet_score(snippet: str, query_tokens: List[str]) -> int:
    snippet_tokens = set(_tokenize(snippet))
    return sum(1 for token in query_tokens if token in snippet_tokens)


def _argument_doc_line(tool: ToolIR) -> List[str]:
    lines: List[str] = []
    for arg in tool.arguments:
        fragments = [arg.name, "required" if arg.required else "optional"]
        if arg.description:
            fragments.append(arg.description)
        if arg.enum:
            fragments.append(f"Allowed values: {', '.join(str(value) for value in arg.enum)}.")
        if arg.default is not None:
            fragments.append(f"Default: {arg.default!r}.")
        lines.append(" ".join(str(fragment) for fragment in fragments))
    return lines


def _tool_similarity(anchor: ToolIR, candidate: ToolIR) -> int:
    if anchor.tool_name == candidate.tool_name:
        return 10_000
    anchor_tokens = _tool_token_set(anchor)
    candidate_tokens = _tool_token_set(candidate)
    overlap = anchor_tokens.intersection(candidate_tokens)
    return len(overlap)


def _rank_tool_candidates(tool: ToolIR, tools: Dict[str, ToolIR] | None = None, top_k: int = 3) -> List[ToolIR]:
    if not tools:
        return [tool]
    ranked = sorted(
        tools.values(),
        key=lambda candidate: (-_tool_similarity(tool, candidate), candidate.tool_name != tool.tool_name, candidate.tool_name),
    )
    shortlist = ranked[: max(top_k, 1)]
    if all(candidate.tool_name != tool.tool_name for candidate in shortlist):
        shortlist.insert(0, tool)
        shortlist = shortlist[: max(top_k, 1)]
    return shortlist


def _top_distinctive_terms(tool: ToolIR, distractors: List[ToolIR], limit: int = 4) -> List[str]:
    target_tokens = _tool_token_set(tool)
    distractor_tokens: Set[str] = set()
    for distractor in distractors:
        distractor_tokens.update(_tool_token_set(distractor))

    ranked_terms: List[str] = []
    for token in _tokenize(_tool_text(tool)):
        if token in ranked_terms:
            continue
        if len(token) < 4 or token.isdigit():
            continue
        if token not in target_tokens or token in distractor_tokens:
            continue
        ranked_terms.append(token)
        if len(ranked_terms) >= limit:
            break
    return ranked_terms


def _build_candidate_examples(tool: ToolIR) -> List[Dict[str, Any]]:
    examples: List[Dict[str, Any]] = []
    minimal = build_argument_template(tool, include_optional=False, variant=0)
    full = build_argument_template(tool, include_optional=True, variant=1)
    if minimal:
        examples.append({"scenario": f"Minimal routed call for {tool.tool_name}", "arguments": minimal})
    if full and full != minimal:
        examples.append({"scenario": f"Full routed call for {tool.tool_name}", "arguments": full})

    argument_names = {arg.name for arg in tool.arguments}
    if {"path", "head"}.issubset(argument_names):
        examples.append({"scenario": "Read the first lines of a file after routing to the file reader.", "arguments": {"path": "src/app.py", "head": 8}})
    if {"path", "tail"}.issubset(argument_names):
        examples.append({"scenario": "Read the last lines of a file after routing to the file reader.", "arguments": {"path": "logs/output.txt", "tail": 12}})
    if {"path", "pattern"}.issubset(argument_names):
        examples.append({"scenario": "Route file discovery requests with recursive glob patterns to this tool.", "arguments": {"path": "docs", "pattern": "**/*.md", "excludePatterns": []}})
    if set(argument_names) == {"path"} and "directory" in (tool.tool_purpose or "").lower():
        if "create" in tool.tool_name:
            examples.append({"scenario": "Route ensure-directory requests here.", "arguments": {"path": "reports/weekly"}})
        if "list" in tool.tool_name:
            examples.append({"scenario": "Route inspect-directory requests here.", "arguments": {"path": "docs"}})
    if {"path", "content"}.issubset(argument_names):
        examples.append({"scenario": "Route write-content requests to this file writer.", "arguments": {"path": "docs/notes.txt", "content": "Release checklist"}})

    deduped: List[Dict[str, Any]] = []
    seen = set()
    for example in examples:
        key = (
            example["scenario"],
            json.dumps(example["arguments"], ensure_ascii=False, sort_keys=True) if isinstance(example["arguments"], dict) else "",
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(example)
    return deduped[:4]


def build_retrieved_docs_skill(tool: ToolIR) -> GeneratedSkill:
    query_tokens = _tokenize(_tool_text(tool))
    candidates: List[str] = []
    if tool.tool_purpose:
        candidates.append(tool.tool_purpose)
    if tool.output_hint:
        candidates.append(tool.output_hint)
    if tool.auth_or_env_notes:
        candidates.append(tool.auth_or_env_notes)
    candidates.extend(tool.doc_snippets)
    candidates.extend(tool.usage_warnings)
    candidates.extend(_argument_doc_line(tool))
    unique_candidates = []
    for candidate in candidates:
        normalized = " ".join(candidate.split())
        if normalized and normalized not in unique_candidates:
            unique_candidates.append(normalized)

    ranked = sorted(unique_candidates, key=lambda item: (-_snippet_score(item, query_tokens), -len(item)))
    top_snippets = ranked[:4]
    summary = " ".join(top_snippets[:2]) or (tool.tool_purpose or f"Retrieved docs baseline for {tool.tool_name}.")
    template = build_argument_template(tool, include_optional=True, variant=0)
    examples = []
    minimal = build_argument_template(tool, include_optional=False, variant=0)
    full = build_argument_template(tool, include_optional=True, variant=1)
    if minimal:
        examples.append({"scenario": f"Retrieved-docs minimal call for {tool.tool_name}", "arguments": minimal})
    if full and full != minimal:
        examples.append({"scenario": f"Retrieved-docs fuller call for {tool.tool_name}", "arguments": full})

    when_not_to_use = list(tool.usage_warnings) or ["Do not assume capabilities beyond the retrieved tool documentation."]

    return GeneratedSkill(
        baseline_name="retrieved_docs",
        skill_summary=summary,
        when_to_use=top_snippets or [f"Use `{tool.tool_name}` according to the retrieved documentation snippets."],
        when_not_to_use=when_not_to_use,
        argument_template=template,
        examples=examples,
    )


def build_retrieved_candidates_skill(tool: ToolIR, tools: Dict[str, ToolIR] | None = None) -> GeneratedSkill:
    shortlist = _rank_tool_candidates(tool, tools=tools, top_k=3)
    distractors = [candidate for candidate in shortlist if candidate.tool_name != tool.tool_name]
    distinctive_terms = _top_distinctive_terms(tool, distractors)
    candidate_names = [candidate.tool_name for candidate in shortlist]
    top_snippets = [tool.tool_purpose or ""]
    top_snippets.extend(tool.doc_snippets[:2])
    top_snippets = [snippet for snippet in top_snippets if snippet]

    if distinctive_terms:
        cue_text = ", ".join(distinctive_terms)
        summary = f"Candidate retrieval ranked `{tool.tool_name}` over nearby tools using cues like {cue_text}."
    else:
        summary = f"Candidate retrieval ranked `{tool.tool_name}` first among {', '.join(candidate_names)}."

    when_to_use = [
        f"Retrieve a shortlist of nearby tools first, then choose `{tool.tool_name}` when the request matches its role.",
        f"Shortlist: {', '.join(candidate_names)}.",
    ]
    when_to_use.extend(top_snippets[:2])

    when_not_to_use = []
    for distractor in distractors[:2]:
        if distractor.tool_purpose:
            when_not_to_use.append(f"Do not confuse `{tool.tool_name}` with `{distractor.tool_name}`: {distractor.tool_purpose}")
    if not when_not_to_use:
        when_not_to_use.append("Do not invent arguments that belong to neighboring candidate tools.")

    return GeneratedSkill(
        baseline_name="retrieved_candidates",
        skill_summary=summary,
        when_to_use=when_to_use,
        when_not_to_use=when_not_to_use,
        argument_template=build_argument_template(tool, include_optional=True, variant=0),
        examples=_build_candidate_examples(tool),
        method_trace=[
            {
                "selection_strategy": "candidate_retrieval_shortlist",
                "shortlist": candidate_names,
                "distinctive_terms": distinctive_terms,
            }
        ],
    )


MEMORY_BANK: List[Dict[str, Any]] = [
    {
        "name": "read_head_memory",
        "tool_names": ["read_text_file"],
        "required_args": ["path"],
        "scenario": "Read the top lines of a file when the request asks for the first or opening lines.",
        "arguments": {"path": "src/app.py", "head": 8},
    },
    {
        "name": "read_tail_memory",
        "tool_names": ["read_text_file"],
        "required_args": ["path"],
        "scenario": "Read the trailing lines of a file when the request asks for the last or ending lines.",
        "arguments": {"path": "logs/output.txt", "tail": 12},
    },
    {
        "name": "search_python_memory",
        "tool_names": ["search_files"],
        "required_args": ["path", "pattern"],
        "scenario": "Find python files under a directory.",
        "arguments": {"path": "src", "pattern": "**/*.py", "excludePatterns": []},
    },
    {
        "name": "search_markdown_memory",
        "tool_names": ["search_files"],
        "required_args": ["path", "pattern"],
        "scenario": "Find markdown files under a docs directory.",
        "arguments": {"path": "docs", "pattern": "**/*.md", "excludePatterns": []},
    },
    {
        "name": "search_exclude_memory",
        "tool_names": ["search_files"],
        "required_args": ["path", "pattern"],
        "scenario": "Search text files and ignore an archive subtree.",
        "arguments": {"path": "logs", "pattern": "**/*.txt", "excludePatterns": ["logs/archive/**"]},
    },
    {
        "name": "write_file_memory",
        "tool_names": ["write_file"],
        "required_args": ["path", "content"],
        "scenario": "Save quoted text to a destination file path.",
        "arguments": {"path": "docs/notes.txt", "content": "Release checklist"},
    },
    {
        "name": "create_directory_memory",
        "tool_names": ["create_directory"],
        "required_args": ["path"],
        "scenario": "Ensure a directory exists for reports or generated outputs.",
        "arguments": {"path": "reports/weekly"},
    },
    {
        "name": "list_directory_memory",
        "tool_names": ["list_directory"],
        "required_args": ["path"],
        "scenario": "Inspect the contents of a target directory such as docs.",
        "arguments": {"path": "docs"},
    },
    {
        "name": "weather_memory",
        "tool_names": ["get_weather"],
        "required_args": ["city", "unit"],
        "scenario": "Get the weather in New York using Fahrenheit.",
        "arguments": {"city": "New York", "unit": "F", "include_forecast": True},
    },
    {
        "name": "search_docs_memory",
        "tool_names": ["search_docs"],
        "required_args": ["query"],
        "scenario": "Search documents for a keyword query and return the top 3 results.",
        "arguments": {"query": "release notes", "top_k": 3},
    },
]


def _memory_is_compatible(tool: ToolIR, memory: Dict[str, Any]) -> bool:
    tool_arg_names = {arg.name for arg in tool.arguments}
    memory_args = set(memory.get("arguments", {}))
    required_args = set(memory.get("required_args", []))
    if memory.get("tool_names") and tool.tool_name not in memory.get("tool_names", []):
        return False
    if not memory_args.issubset(tool_arg_names):
        return False
    if not required_args.issubset(tool_arg_names):
        return False
    return True


def build_retrieved_memory_skill(tool: ToolIR, tools: Dict[str, ToolIR] | None = None) -> GeneratedSkill:
    query_tokens = set(_tokenize(_tool_text(tool)))
    compatible_memories: List[Dict[str, Any]] = []
    for memory in MEMORY_BANK:
        if not _memory_is_compatible(tool, memory):
            continue
        memory_tokens = set(_tokenize(memory.get("scenario", "")))
        score = len(query_tokens.intersection(memory_tokens))
        compatible_memories.append({**memory, "score": score})

    compatible_memories.sort(key=lambda item: (-int(item["score"]), item["name"]))
    selected = compatible_memories[:3]

    template = build_argument_template(tool, include_optional=True, variant=0)
    examples = [{"scenario": item["scenario"], "arguments": item["arguments"]} for item in selected]
    minimal = build_argument_template(tool, include_optional=False, variant=0)
    if minimal and not any(example["arguments"] == minimal for example in examples):
        examples.insert(0, {"scenario": f"Minimal valid memory-backed call for {tool.tool_name}", "arguments": minimal})

    when_to_use = [
        "Retrieve similar skill examples from memory before filling arguments.",
    ]
    when_to_use.extend(item["scenario"] for item in selected[:2])

    when_not_to_use = [
        "Do not assume retrieved memories are perfect; keep field names schema-faithful.",
        "Do not invent unsupported arguments when no compatible memory matches the tool.",
    ]

    summary = (
        " ".join(item["scenario"] for item in selected[:2])
        or tool.tool_purpose
        or f"Retrieved skill-memory baseline for {tool.tool_name}."
    )

    return GeneratedSkill(
        baseline_name="retrieved_memory",
        skill_summary=summary,
        when_to_use=when_to_use,
        when_not_to_use=when_not_to_use,
        argument_template=template,
        examples=examples,
    )

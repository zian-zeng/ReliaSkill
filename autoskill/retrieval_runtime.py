from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Dict, List, Tuple

from autoskill.conditions import is_reliaskill_v1_family
from autoskill.contract_inference import build_contract_proof_state, contract_state_payload
from autoskill.contracts import compose_contract_plan
from autoskill.eval_types import EvalTask
from autoskill.ir import GeneratedSkill, ToolIR
from autoskill.retrieval_baselines import MEMORY_BANK
from autoskill.routing_boundaries import routing_tool_mention_adjustment
from autoskill.templates import build_argument_template


SEMANTIC_ALIAS_GROUPS = [
    {"find", "search", "lookup", "locate", "query", "retrieve"},
    {"read", "show", "view", "open", "display", "fetch"},
    {"create", "add", "insert", "new", "make", "ensure"},
    {"update", "edit", "modify", "patch", "write", "save", "append"},
    {"delete", "remove", "clear", "drop"},
    {"send", "email", "notify", "post", "publish", "transfer"},
    {"path", "file", "directory", "folder", "location"},
    {"content", "text", "body", "message", "payload"},
    {"account", "acct", "customer", "client", "user"},
    {"identifier", "id", "name", "title", "key"},
]

SEMANTIC_ALIASES: Dict[str, set[str]] = {}
for _group in SEMANTIC_ALIAS_GROUPS:
    for _term in _group:
        SEMANTIC_ALIASES[_term] = set(_group)


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9_./*?-]+", text.lower())


def _bigrams(tokens: List[str]) -> List[str]:
    return [f"{tokens[index]} {tokens[index + 1]}" for index in range(len(tokens) - 1)]


def _scored_overlap(query: str, text: str) -> Tuple[int, List[str]]:
    query_tokens = _tokenize(query)
    text_tokens = _tokenize(text)
    query_set = set(query_tokens)
    text_set = set(text_tokens)
    overlap = sorted(query_set.intersection(text_set))
    bigram_overlap = sorted(set(_bigrams(query_tokens)).intersection(set(_bigrams(text_tokens))))
    semantic_overlap = sorted(_semantic_token_set(query).intersection(_semantic_token_set(text)) - set(overlap))
    score = 2 * len(overlap) + len(semantic_overlap) + 4 * len(bigram_overlap)
    if query.lower() in text.lower():
        score += 6
    return score, [*overlap, *semantic_overlap][:6]


def _semantic_token_set(text: str) -> set[str]:
    expanded: set[str] = set()
    for token in _tokenize(text):
        parts = [token, *[part for part in re.split(r"[-_./*?]+", token) if part]]
        for part in parts:
            normalized = _normalize_semantic_token(part)
            if not normalized:
                continue
            expanded.add(normalized)
            expanded.update(SEMANTIC_ALIASES.get(normalized, set()))
    return expanded


def _normalize_semantic_token(token: str) -> str:
    token = token.strip("._-/*?").lower()
    if len(token) <= 1:
        return ""
    if token.endswith("ing") and len(token) > 5:
        token = token[:-3]
    elif token.endswith("ed") and len(token) > 4:
        token = token[:-2]
    elif token.endswith("s") and len(token) > 4:
        token = token[:-1]
    return token


def _tool_search_text(tool: ToolIR) -> str:
    parts = [tool.tool_name, tool.tool_purpose or "", tool.output_hint or "", tool.auth_or_env_notes or ""]
    parts.extend(tool.doc_snippets)
    parts.extend(tool.usage_warnings)
    for argument in tool.arguments:
        parts.append(argument.name)
        if argument.description:
            parts.append(argument.description)
    return " ".join(part for part in parts if part)


def _candidate_intent_bonus(query: str, tool: ToolIR) -> int:
    lowered = query.lower()
    argument_names = {argument.name for argument in tool.arguments}
    bonus = 0

    if "pattern" in argument_names and any(token in lowered for token in ("find", "search", "look under", "markdown", "python", "json", "text files", "glob")):
        bonus += 10
    if {"head", "tail"}.intersection(argument_names) and any(token in lowered for token in ("read", "show", "first", "last", "top", "trailing", "lines")):
        bonus += 10
    if "content" in argument_names and any(token in lowered for token in ("write", "save", "create file", "containing the text", "with content")):
        bonus += 10
    creation_cues = ("create", "ensure", "mkdir", "set up", "prepare")
    directory_cues = ("directory", "folder", "path")
    creation_intent = any(token in lowered for token in creation_cues) and any(token in lowered for token in directory_cues)
    make_sure_exists = "make sure" in lowered and any(token in lowered for token in ("exist", "exists", *directory_cues))
    if argument_names == {"path"} and "create" in tool.tool_name and (creation_intent or make_sure_exists):
        bonus += 8
    if argument_names == {"path"} and "list" in tool.tool_name and any(token in lowered for token in ("list", "show contents", "inspect", "directory contents")):
        bonus += 8

    return bonus


def retrieve_candidate_tools(query: str, tools: Dict[str, ToolIR], top_k: int = 3) -> Dict[str, Any]:
    ranked: List[Dict[str, Any]] = []
    for tool in tools.values():
        score, overlap = _scored_overlap(query, _tool_search_text(tool))
        score += _candidate_intent_bonus(query, tool)
        score += routing_tool_mention_adjustment(query, tool)
        ranked.append(
            {
                "tool_name": tool.tool_name,
                "score": score,
                "overlap_terms": overlap,
                "purpose": tool.tool_purpose or "",
            }
        )
    ranked.sort(key=lambda item: (-int(item["score"]), item["tool_name"]))
    return {"candidates": ranked[: max(top_k, 1)]}


def retrieve_doc_tool_rankings(query: str, tools: Dict[str, ToolIR], top_k: int = 3) -> Dict[str, Any]:
    by_tool: Dict[str, Dict[str, Any]] = {}
    for entry in _build_doc_corpus(tools):
        score, overlap = _scored_overlap(query, str(entry["text"]))
        if score <= 0:
            continue
        tool_name = str(entry["tool_name"])
        item = by_tool.setdefault(
            tool_name,
            {
                "tool_name": tool_name,
                "score": 0,
                "best_snippet": "",
                "best_snippet_score": 0,
                "overlap_terms": [],
                "purpose": tools[tool_name].tool_purpose or "",
            },
        )
        item["score"] += score
        if score > item["best_snippet_score"]:
            item["best_snippet_score"] = score
            item["best_snippet"] = str(entry["text"])
            item["overlap_terms"] = overlap

    ranked = sorted(by_tool.values(), key=lambda item: (-int(item["score"]), item["tool_name"]))
    return {"candidates": ranked[: max(top_k, 1)]}


def _build_doc_corpus(tools: Dict[str, ToolIR]) -> List[Dict[str, Any]]:
    corpus: List[Dict[str, Any]] = []
    for tool in tools.values():
        if tool.tool_purpose:
            corpus.append({"tool_name": tool.tool_name, "source_type": "purpose", "text": tool.tool_purpose})
        for snippet in tool.doc_snippets:
            corpus.append({"tool_name": tool.tool_name, "source_type": "doc", "text": snippet})
        for warning in tool.usage_warnings:
            corpus.append({"tool_name": tool.tool_name, "source_type": "warning", "text": warning})
        for argument in tool.arguments:
            if argument.description:
                corpus.append(
                    {
                        "tool_name": tool.tool_name,
                        "source_type": "argument",
                        "argument_name": argument.name,
                        "text": f"{argument.name}: {argument.description}",
                    }
                )
    return corpus


def retrieve_doc_context(query: str, tool: ToolIR, tools: Dict[str, ToolIR], top_k_tools: int = 3, top_k_snippets: int = 5) -> Dict[str, Any]:
    tool_rankings = retrieve_doc_tool_rankings(query, tools, top_k=top_k_tools)["candidates"]
    target_rank = next((index + 1 for index, item in enumerate(tool_rankings) if item["tool_name"] == tool.tool_name), None)

    ranked_snippets: List[Dict[str, Any]] = []
    for entry in _build_doc_corpus(tools):
        score, overlap = _scored_overlap(query, str(entry["text"]))
        if score <= 0:
            continue
        ranked_snippets.append({**entry, "score": score, "overlap_terms": overlap})
    ranked_snippets.sort(key=lambda item: (-int(item["score"]), item["tool_name"], item["source_type"]))

    target_snippets = [item for item in ranked_snippets if item["tool_name"] == tool.tool_name]
    global_snippets = ranked_snippets[: max(top_k_snippets, 1)]
    selected_snippets = (target_snippets[:2] + [item for item in global_snippets if item["tool_name"] != tool.tool_name])[: max(top_k_snippets, 1)]

    return {
        "retrieval_type": "docs",
        "candidate_tools": tool_rankings,
        "target_tool_rank": target_rank,
        "target_in_top_k": target_rank is not None,
        "snippets": selected_snippets,
    }


def _tool_generated_memories(tool: ToolIR) -> List[Dict[str, Any]]:
    memories: List[Dict[str, Any]] = []
    minimal = build_argument_template(tool, include_optional=False, variant=0)
    full = build_argument_template(tool, include_optional=True, variant=1)
    if minimal:
        memories.append(
            {
                "name": f"{tool.tool_name}_minimal_memory",
                "tool_names": [tool.tool_name],
                "scenario": f"Minimal valid call for {tool.tool_name}.",
                "arguments": minimal,
            }
        )
    if full and full != minimal:
        memories.append(
            {
                "name": f"{tool.tool_name}_full_memory",
                "tool_names": [tool.tool_name],
                "scenario": f"Fuller call for {tool.tool_name} with optional fields included.",
                "arguments": full,
            }
        )
    return memories


def retrieve_memory_context(query: str, tool: ToolIR, tools: Dict[str, ToolIR], top_k: int = 3) -> Dict[str, Any]:
    memory_bank: List[Dict[str, Any]] = [*MEMORY_BANK]
    for candidate_tool in tools.values():
        memory_bank.extend(_tool_generated_memories(candidate_tool))

    ranked: List[Dict[str, Any]] = []
    for memory in memory_bank:
        tool_names = [str(name) for name in memory.get("tool_names", [])]
        if tool_names and tool.tool_name not in tool_names:
            continue
        arguments = memory.get("arguments", {})
        if not isinstance(arguments, dict):
            continue
        score, overlap = _scored_overlap(query, f"{memory.get('scenario', '')} {arguments}")
        if score <= 0:
            continue
        ranked.append(
            {
                "memory_name": str(memory.get("name", "memory")),
                "tool_name": tool.tool_name,
                "scenario": str(memory.get("scenario", "")),
                "arguments": arguments,
                "score": score,
                "overlap_terms": overlap,
            }
        )

    ranked.sort(key=lambda item: (-int(item["score"]), item["memory_name"]))
    return {
        "retrieval_type": "memory",
        "memories": ranked[: max(top_k, 1)],
    }


def retrieve_memory_tool_rankings(query: str, tools: Dict[str, ToolIR], top_k: int = 3) -> Dict[str, Any]:
    memory_bank: List[Dict[str, Any]] = [*MEMORY_BANK]
    for candidate_tool in tools.values():
        memory_bank.extend(_tool_generated_memories(candidate_tool))

    by_tool: Dict[str, Dict[str, Any]] = {}
    for memory in memory_bank:
        tool_names = [str(name) for name in memory.get("tool_names", [])]
        if not tool_names:
            continue
        arguments = memory.get("arguments", {})
        if not isinstance(arguments, dict):
            continue
        score, overlap = _scored_overlap(query, f"{memory.get('scenario', '')} {arguments}")
        if score <= 0:
            continue
        for tool_name in tool_names:
            item = by_tool.setdefault(
                tool_name,
                {
                    "tool_name": tool_name,
                    "score": 0,
                    "best_memory_name": "",
                    "best_memory_scenario": "",
                    "best_memory_score": 0,
                    "overlap_terms": [],
                    "purpose": tools[tool_name].tool_purpose if tool_name in tools else "",
                },
            )
            item["score"] += score
            if score > item["best_memory_score"]:
                item["best_memory_score"] = score
                item["best_memory_name"] = str(memory.get("name", "memory"))
                item["best_memory_scenario"] = str(memory.get("scenario", ""))
                item["overlap_terms"] = overlap

    ranked = sorted(by_tool.values(), key=lambda item: (-int(item["score"]), item["tool_name"]))
    return {"candidates": ranked[: max(top_k, 1)]}


def contextualize_skill_for_task(
    task: EvalTask,
    tool: ToolIR,
    skill: GeneratedSkill,
    tools: Dict[str, ToolIR],
    skill_bank: Dict[str, GeneratedSkill] | None = None,
) -> tuple[GeneratedSkill, Dict[str, Any]]:
    contextualized = deepcopy(skill)

    if skill.baseline_name == "retrieved_docs":
        context = retrieve_doc_context(task.user_request, tool, tools)
        candidate_names = [item["tool_name"] for item in context["candidate_tools"]]
        contextualized.skill_summary = (
            f"Retrieved raw docs for this request. Candidate tools: {', '.join(candidate_names)}."
            if candidate_names
            else "Retrieved raw docs for this request."
        )
        contextualized.when_to_use = [
            f"Retrieve raw documentation snippets at inference time for the current request: {task.user_request}",
            *[f"[{item['tool_name']}/{item['source_type']}] {item['text']}" for item in context["snippets"][:3]],
        ]
        contextualized.when_not_to_use = [
            "Do not convert raw retrieved docs into semantic hints or rewritten schema aliases.",
            "Do not rely on snippets from other tools when filling target-tool field names.",
        ]
        contextualized.method_trace.append(
            {
                "retrieval_type": "docs",
                "candidate_tools": candidate_names,
                "target_tool_rank": context["target_tool_rank"],
                "retrieved_snippet_count": len(context["snippets"]),
            }
        )
        return contextualized, context

    if skill.baseline_name == "retrieved_candidates":
        context = retrieve_doc_context(task.user_request, tool, tools)
        candidate_names = [item["tool_name"] for item in context["candidate_tools"]]
        contextualized.skill_summary = (
            f"Retrieve candidate tools first, then route to `{tool.tool_name}` only if it remains the best match."
        )
        contextualized.when_to_use = [
            f"Rank candidate tools for the request before argument filling: {task.user_request}",
            f"Shortlist: {', '.join(candidate_names)}." if candidate_names else "Shortlist: none.",
        ]
        contextualized.when_to_use.extend(
            f"[{item['tool_name']}] {item['purpose']}" for item in context["candidate_tools"][:3] if item.get("purpose")
        )
        contextualized.when_not_to_use = [
            "Do not copy arguments from neighboring candidate tools into the selected tool call.",
            "Do not assume the target tool is rank-1 when retrieval evidence favors another tool.",
        ]
        contextualized.method_trace.append(
            {
                "retrieval_type": "candidate_tools",
                "candidate_tools": candidate_names,
                "selected_tool_name": candidate_names[0] if candidate_names else tool.tool_name,
                "target_tool_rank": context["target_tool_rank"],
            }
        )
        return contextualized, {
            "retrieval_type": "candidate_tools",
            "candidate_tools": context["candidate_tools"],
            "target_tool_rank": context["target_tool_rank"],
            "target_in_top_k": context["target_in_top_k"],
        }

    if skill.baseline_name == "retrieved_memory":
        context = retrieve_memory_context(task.user_request, tool, tools)
        contextualized.skill_summary = "Retrieve nearest memory examples for the current request and reuse them without semantic hint rewriting."
        contextualized.when_to_use = [
            f"Retrieve example memories for the request: {task.user_request}",
            *[item["scenario"] for item in context["memories"][:2]],
        ]
        contextualized.examples = [
            {"scenario": item["scenario"], "arguments": item["arguments"]}
            for item in context["memories"]
        ]
        contextualized.semantic_hints = {}
        contextualized.method_trace.append(
            {
                "retrieval_type": "memory",
                "retrieved_memory_names": [item["memory_name"] for item in context["memories"]],
                "retrieved_memory_count": len(context["memories"]),
            }
        )
        return contextualized, context

    if (
        is_reliaskill_v1_family(skill.baseline_name)
        and not _contract_ablation_disabled(skill, "disable_contract_routing")
        and not _contract_ablation_disabled(skill, "disable_contrastive_contract_context")
    ):
        include_plan = not _contract_ablation_disabled(skill, "disable_dependency_plan_prompting")
        context = _reliaskill_contrastive_contract_context(
            task,
            tool,
            skill,
            tools,
            skill_bank=skill_bank,
            expand_to_all_tools=not _contract_ablation_disabled(skill, "disable_retrieval_miss_rescue"),
            include_dependency_plan=include_plan,
        )
        if context["candidate_proof_states"]:
            metadata_updates = {
                "contrastive_contract_candidates": context["candidate_proof_states"],
                "contrastive_contract_target_rank": context["target_proof_rank"],
                "contrastive_contract_best_viable_tool": context["best_viable_tool"],
            }
            if include_plan:
                metadata_updates["contract_plan_context"] = context.get("contract_plan", {})
            contextualized.metadata = {
                **contextualized.metadata,
                **metadata_updates,
            }
            contextualized.when_not_to_use = _dedupe_lines(
                [
                    "If this tool's contrastive proof state is not viable while another candidate is viable, abstain so routing can verify the better candidate.",
                    *contextualized.when_not_to_use,
                ]
            )
            contextualized.method_trace.append(
                {
                    "retrieval_type": "contrastive_contract_proof",
                    "candidate_tools": [row["tool_name"] for row in context["candidate_proof_states"]],
                    "target_proof_rank": context["target_proof_rank"],
                    "best_viable_tool": context["best_viable_tool"],
                    "contract_plan_satisfied": bool((context.get("contract_plan") or {}).get("satisfied")),
                }
            )
            return contextualized, context

    return contextualized, {}


def _reliaskill_contrastive_contract_context(
    task: EvalTask,
    target_tool: ToolIR,
    target_skill: GeneratedSkill,
    tools: Dict[str, ToolIR],
    *,
    skill_bank: Dict[str, GeneratedSkill] | None = None,
    top_k: int = 4,
    expand_to_all_tools: bool = True,
    include_dependency_plan: bool = True,
) -> Dict[str, Any]:
    retrieval_limit = max(len(tools), top_k) if expand_to_all_tools else top_k
    rows = retrieve_candidate_tools(task.user_request, tools, top_k=retrieval_limit)["candidates"]
    retrieved_rank = {str(row["tool_name"]): index + 1 for index, row in enumerate(rows)}
    proof_rows: List[Dict[str, Any]] = []
    for row in rows:
        candidate_name = str(row["tool_name"])
        candidate_tool = tools.get(candidate_name)
        if candidate_tool is None:
            continue
        candidate_skill = (skill_bank or {}).get(candidate_name) or _fallback_candidate_skill(candidate_tool, target_skill)
        proof_state = build_contract_proof_state(
            candidate_tool,
            candidate_skill,
            task.user_request,
            grounding_context={
                "conversation": list(task.conversation_history),
                "artifacts": dict(task.artifact_context),
                "tool_observations": list(task.tool_observation_context),
            },
            retrieval_score=int(row.get("score", 0) or 0),
        )
        payload = contract_state_payload(proof_state)
        payload["retrieval_score"] = int(row.get("score", 0) or 0)
        payload["retrieval_rank"] = retrieved_rank.get(candidate_name)
        payload["target_tool"] = candidate_name == target_tool.tool_name
        proof_rows.append(payload)
    proof_rows.sort(
        key=lambda item: (
            not bool(item.get("viable")),
            -float(item.get("proof_score") or 0.0),
            -int(item.get("retrieval_score") or 0),
            str(item.get("tool_name") or ""),
        )
    )
    rescued_rows = (
        [
            row
            for index, row in enumerate(proof_rows)
            if row.get("viable") and int(row.get("retrieval_rank") or 0) > top_k and index < top_k
        ]
        if expand_to_all_tools
        else []
    )
    exposed_rows = proof_rows[: max(top_k, 1)]
    target_rank = next((index + 1 for index, row in enumerate(proof_rows) if row.get("tool_name") == target_tool.tool_name), None)
    best_viable = next((str(row["tool_name"]) for row in proof_rows if row.get("viable")), None)
    plan = (
        _compose_contrastive_contract_plan(
            task,
            tools,
            skill_bank=skill_bank,
            candidate_names=[str(row["tool_name"]) for row in exposed_rows],
        )
        if include_dependency_plan
        else {}
    )
    return {
        "retrieval_type": "contrastive_contract_proof",
        "candidate_proof_states": exposed_rows,
        "proof_expanded_candidate_count": len(proof_rows),
        "retrieval_miss_rescues": rescued_rows,
        "retrieval_miss_rescue_enabled": bool(expand_to_all_tools),
        "target_proof_rank": target_rank,
        "target_in_top_k": target_rank is not None,
        "best_viable_tool": best_viable,
        "contract_plan": plan,
        "dependency_plan_enabled": bool(include_dependency_plan),
    }


def _compose_contrastive_contract_plan(
    task: EvalTask,
    tools: Dict[str, ToolIR],
    *,
    skill_bank: Dict[str, GeneratedSkill] | None,
    candidate_names: List[str],
) -> Dict[str, Any]:
    plan_tools = {name: tools[name] for name in candidate_names if name in tools}
    plan_skills = {
        name: (skill_bank or {}).get(name) or _fallback_candidate_skill(tool, GeneratedSkill(baseline_name="reliaskill_v1"))
        for name, tool in plan_tools.items()
    }
    if not plan_tools or not plan_skills:
        return {}
    plan = compose_contract_plan(
        task.user_request,
        plan_tools,
        plan_skills,
        grounding_context={
            "conversation": list(task.conversation_history),
            "artifacts": dict(task.artifact_context),
            "tool_observations": list(task.tool_observation_context),
        },
        max_steps=min(3, max(1, len(plan_tools))),
    )
    payload = plan.model_dump()
    payload["steps"] = payload.get("steps", [])[:3]
    payload["unresolved_tools"] = payload.get("unresolved_tools", [])[:3]
    return payload


def _fallback_candidate_skill(tool: ToolIR, source_skill: GeneratedSkill) -> GeneratedSkill:
    return GeneratedSkill(
        baseline_name=source_skill.baseline_name,
        skill_summary=tool.tool_purpose or source_skill.skill_summary,
        when_to_use=[f"Use `{tool.tool_name}` only for direct requests matching its purpose."],
        when_not_to_use=[],
        argument_template={argument.name: f"<{argument.name}>" for argument in tool.arguments if argument.required},
        metadata=dict(source_skill.metadata),
    )


def _contract_ablation_disabled(skill: GeneratedSkill, flag: str) -> bool:
    flags = skill.metadata.get("contract_ablation_flags") if isinstance(skill.metadata, dict) else None
    return bool(isinstance(flags, dict) and flags.get(flag) is True)


def _dedupe_lines(lines: List[str]) -> List[str]:
    result: List[str] = []
    seen: set[str] = set()
    for line in lines:
        normalized = " ".join(str(line).split())
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result

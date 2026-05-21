from __future__ import annotations

import re
from typing import Iterable

from autoskill.ir import ToolIR


def normalize_routing_text(text: str) -> str:
    lowered = str(text or "").lower()
    lowered = re.sub(r"[_./:-]+", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


def tool_name_variants(tool: ToolIR | str) -> list[str]:
    name = tool.tool_name if isinstance(tool, ToolIR) else str(tool)
    variants = {
        normalize_routing_text(name),
        normalize_routing_text(name.replace("_", " ")),
        normalize_routing_text(name.replace("-", " ")),
        normalize_routing_text(name.replace(".", " ")),
    }
    return sorted(value for value in variants if value)


def _contains_any(text: str, phrases: Iterable[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def request_forbids_tool(query: str, tool: ToolIR | str) -> str | None:
    """Return a high-precision certificate that the request excludes this tool.

    This is intentionally asymmetric with positive tool mentions: it only fires
    when the tool name appears inside a local non-use construction, so unrelated
    distractor phrases do not suppress the actual requested tool.
    """
    text = normalize_routing_text(query)
    for name in tool_name_variants(tool):
        if not name:
            continue
        if _contains_any(
            text,
            (
                f"{name} is a distractor",
                f"{name} should not be called",
                f"{name} is not the right tool",
                f"{name} is the wrong tool",
                f"do not use {name}",
                f"do not call {name}",
                f"avoid {name}",
                f"without using {name}",
                f"instead of {name}",
                f"rather than {name}",
            ),
        ):
            return "explicit_target_tool_forbidden"
        if re.search(
            rf"\b(?:boundary\s+check|should\s+handle|correct\s+tool\s+is|route\s+to|select)\b"
            rf".{{0,160}}\bnot\s+{re.escape(name)}\b",
            text,
        ):
            return "explicit_target_tool_forbidden"
        if re.search(
            rf"\bnot\s+{re.escape(name)}\b"
            rf".{{0,160}}\b(?:should\s+handle|correct\s+tool|appropriate\s+direct\s+action)\b",
            text,
        ):
            return "explicit_target_tool_forbidden"
    return None


def detect_routing_abstention(query: str) -> str | None:
    """Return a boundary reason when a request explicitly asks for no tool call."""
    text = normalize_routing_text(query)
    if not text:
        return "empty_request"

    if "do not actually call" in text or "do not perform the action" in text:
        return "explanation_instead_of_action"
    if "no tool call" in text or "no tool call yet" in text:
        return "no_tool_call_requested"
    if "only want a checklist" in text:
        return "checklist_only"
    if "not sure what input or action is intended" in text:
        return "ambiguous_action"
    if "i do not know" in text and (" yet" in text or "required input" in text or "required field" in text):
        return "missing_required_information"
    if re.search(r"\b(?:i\s+)?(?:may|might|would)?\s*need\b.+\bbut\b.+\b(?:do\s+not\s+know|don t\s+know|not\s+sure|missing|lack)\b", text):
        return "missing_required_information"
    if "i already know the exact path" in text and (
        "no search or discovery is needed" in text or "no search is needed" in text
    ):
        return "known_path_no_search_needed"
    if "read the exact item i named directly" in text and _contains_any(
        text,
        (
            "do not search",
            "retrieve candidates",
            "browse with",
        ),
    ):
        return "read_vs_search_mismatch"
    if "only inspect what would happen before using" in text and _contains_any(
        text,
        (
            "do not create",
            "do not update",
            "do not delete",
            "do not send",
            "do not execute",
            "mutate anything",
        ),
    ):
        return "readonly_preview_only"
    if "only preview what would change" in text and _contains_any(
        text,
        (
            "do not create",
            "do not overwrite",
            "do not delete",
            "do not send",
            "do not execute",
            "mutate anything",
        ),
    ):
        return "readonly_preview_only"
    if "without changing it" in text and _contains_any(
        text,
        (
            "do not write",
            "do not update",
            "do not delete",
            "do not overwrite",
            "do not mutate",
        ),
    ):
        return "readonly_preview_only"
    if "need a change made" in text and "not a read only lookup" in text and "do not satisfy this with a read" in text:
        return "destructive_vs_readonly_mismatch"
    if _contains_any(text, ("do not merely read", "not merely read")) and _contains_any(
        text,
        (
            "create",
            "overwrite",
            "write",
            "update",
            "change",
        ),
    ):
        return "destructive_vs_readonly_mismatch"
    if "this is adjacent to" in text and "but the intended capability is" in text:
        return "adjacent_wrong_intent"
    if "this is a boundary check" in text and " should handle " in text and " not " in text:
        return "adjacent_wrong_intent"
    if "is unrelated to" in text:
        return "out_of_domain_request"
    return None


def routing_tool_mention_adjustment(query: str, tool: ToolIR) -> int:
    """Cheap discriminator for explicit tool-name routing instructions."""
    text = normalize_routing_text(query)
    adjustment = 0
    for name in tool_name_variants(tool):
        if not name:
            continue
        if request_forbids_tool(text, name):
            adjustment -= 80
        if _contains_any(
            text,
            (
                f"use {name}",
                f"using {name}",
                f"call {name}",
            ),
        ):
            adjustment += 18
    return adjustment

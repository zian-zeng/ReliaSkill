from __future__ import annotations

from typing import Any, Dict

from autoskill.ir import ToolIR
from autoskill.parser import parse_mcp_tool


def build_live_exec_tools() -> Dict[str, ToolIR]:
    tools = [_parse_tool(raw) for raw in _live_tool_records()]
    return {tool.tool_name: tool for tool in tools}


def _parse_tool(raw: Dict[str, Any]) -> ToolIR:
    tool = parse_mcp_tool(raw, source_pointer=str(raw.get("source_pointer") or f"live_exec::{raw['name']}"))
    domain = str(raw.get("domain") or "")
    source_metadata = raw.get("source_metadata") if isinstance(raw.get("source_metadata"), dict) else {}
    tool.provenance = {**tool.provenance, **source_metadata, "domain": domain}
    tool.schema_complexity = {**tool.schema_complexity, "domain": domain}
    return tool


def _live_tool_records() -> list[Dict[str, Any]]:
    return [
        _tool(
            name="fs_list_directory",
            domain="filesystem",
            description="List files and directories under a relative sandbox path. The call must stay inside the temporary filesystem sandbox.",
            properties={"path": _string("Relative directory path to inspect, such as docs or .")},
            required=["path"],
            side_effect="read",
        ),
        _tool(
            name="fs_read_file",
            domain="filesystem",
            description="Read a text file at a relative path inside the temporary filesystem sandbox. Absolute paths and path traversal are blocked.",
            properties={"path": _string("Relative file path to read, such as README.md")},
            required=["path"],
            side_effect="read",
        ),
        _tool(
            name="fs_search_files",
            domain="filesystem",
            description="Search text files under a relative sandbox directory for a query string.",
            properties={
                "path": _string("Relative directory path to search, often ."),
                "query": _string("Case-insensitive search text."),
            },
            required=["path", "query"],
            side_effect="read",
        ),
        _tool(
            name="fs_write_file",
            domain="filesystem",
            description="Create or overwrite a text file at a relative path inside the temporary filesystem sandbox.",
            properties={
                "path": _string("Relative file path to write under the sandbox."),
                "content": _string("UTF-8 text content to write."),
            },
            required=["path", "content"],
            side_effect="write",
        ),
        _tool(
            name="sql_select",
            domain="sqlite",
            description="Run a read-only SELECT query against the temporary SQLite database.",
            properties={"query": _string("A SQL query that starts with SELECT.")},
            required=["query"],
            side_effect="read",
        ),
        _tool(
            name="sql_schema",
            domain="sqlite",
            description="Inspect table and column names in the temporary SQLite database. This tool takes no arguments.",
            properties={},
            required=[],
            side_effect="read",
        ),
        _tool(
            name="sql_execute",
            domain="sqlite",
            description="Execute a safe SQL mutation against the temporary SQLite database. Unsafe administrative statements are blocked.",
            properties={"query": _string("A SQL INSERT, UPDATE, or DELETE statement for the sandbox database.")},
            required=["query"],
            side_effect="write",
        ),
        _tool(
            name="git_status",
            domain="git",
            description="Return branch name and working-tree changes from a deterministic git-like sandbox.",
            properties={},
            required=[],
            side_effect="read",
        ),
        _tool(
            name="git_log",
            domain="git",
            description="Return recent commits from a deterministic git-like sandbox.",
            properties={"limit": {"type": "integer", "description": "Maximum commits to return, between 1 and 20."}},
            required=[],
            side_effect="read",
        ),
        _tool(
            name="git_diff",
            domain="git",
            description="Return tracked file changes from a deterministic git-like sandbox, optionally for one path.",
            properties={"path": _string("Optional relative tracked path to diff, such as README.md")},
            required=[],
            side_effect="read",
        ),
        _tool(
            name="git_branches",
            domain="git",
            description="List local branches and the current branch from a deterministic git-like sandbox.",
            properties={},
            required=[],
            side_effect="read",
        ),
        _tool(
            name="git_fetch",
            domain="git",
            description="Attempt a network fetch in the git-like sandbox. The sandbox should block this unsafe network operation.",
            properties={"remote": _string("Remote name, usually origin.")},
            required=[],
            side_effect="network",
        ),
    ]


def _tool(
    *,
    name: str,
    domain: str,
    description: str,
    properties: Dict[str, Any],
    required: list[str],
    side_effect: str,
) -> Dict[str, Any]:
    return {
        "name": name,
        "server_name": f"reliaskill_live_{domain}",
        "description": description,
        "inputSchema": {"type": "object", "properties": properties, "required": required},
        "domain": domain,
        "source_pointer": f"live_exec::{domain}::{name}",
        "source_metadata": {
            "domain": domain,
            "source_category": "live_execution_sandbox",
            "source_type": "deterministic_sandbox",
            "tool_name": name,
            "side_effect_type": side_effect,
            "synthetic": False,
        },
    }


def _string(description: str) -> Dict[str, str]:
    return {"type": "string", "description": description}

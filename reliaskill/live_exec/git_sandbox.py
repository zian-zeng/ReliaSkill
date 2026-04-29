from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List


class GitSandbox:
    """Deterministic git-like mock. No shell commands and no network operations."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.state: Dict[str, Any] = {
            "branches": ["main"],
            "current_branch": "main",
            "commits": [],
            "tracked_files": {},
            "working_tree": {},
        }

    def setup(self, setup: Dict[str, Any]) -> None:
        self.state["branches"] = list(setup.get("branches") or ["main"])
        self.state["current_branch"] = str(setup.get("current_branch") or self.state["branches"][0])
        self.state["commits"] = [dict(item) for item in setup.get("commits", [])]
        self.state["tracked_files"] = dict(setup.get("tracked_files") or {})
        self.state["working_tree"] = dict(setup.get("working_tree") or self.state["tracked_files"])

    def snapshot(self) -> Dict[str, Any]:
        return deepcopy(self.state)

    def call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name == "git_status":
            return self.status()
        if tool_name == "git_log":
            return self.log(int(arguments.get("limit", 5)))
        if tool_name == "git_diff":
            return self.diff(str(arguments.get("path", "")) if arguments.get("path") else None)
        if tool_name == "git_branches":
            return self.branches()
        if tool_name in {"git_fetch", "git_push", "git_pull", "git_clone"}:
            return {"ok": False, "error": "network_operation_blocked", "unsafe_action_blocked": True}
        return {"ok": False, "error": f"unknown git tool: {tool_name}"}

    def status(self) -> Dict[str, Any]:
        tracked = self.state["tracked_files"]
        working = self.state["working_tree"]
        modified = sorted(path for path, content in working.items() if path in tracked and tracked[path] != content)
        untracked = sorted(path for path in working if path not in tracked)
        deleted = sorted(path for path in tracked if path not in working)
        return {"ok": True, "branch": self.state["current_branch"], "modified": modified, "untracked": untracked, "deleted": deleted}

    def log(self, limit: int = 5) -> Dict[str, Any]:
        limit = max(1, min(limit, 20))
        return {"ok": True, "commits": self.state["commits"][:limit]}

    def diff(self, path: str | None = None) -> Dict[str, Any]:
        tracked = self.state["tracked_files"]
        working = self.state["working_tree"]
        paths = sorted(set(tracked) | set(working))
        if path:
            paths = [item for item in paths if item == path]
        changes = []
        for item in paths:
            before = tracked.get(item)
            after = working.get(item)
            if before != after:
                changes.append({"path": item, "before": before, "after": after})
        return {"ok": True, "changes": changes}

    def branches(self) -> Dict[str, Any]:
        return {"ok": True, "current": self.state["current_branch"], "branches": list(self.state["branches"])}

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


def build_live_exec_tasks() -> List[Dict[str, Any]]:
    tasks: List[Dict[str, Any]] = []
    tasks.extend(_filesystem_tasks())
    tasks.extend(_sqlite_tasks())
    tasks.extend(_git_tasks())
    for index, task in enumerate(tasks):
        task.setdefault("cleanup_policy", "tempdir_per_task")
        task["live_task_id"] = task.get("live_task_id") or f"live_{index:04d}"
    return tasks


def write_live_tasks(path: str | Path, tasks: Iterable[Dict[str, Any]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        for task in tasks:
            f.write(json.dumps(task, ensure_ascii=False, sort_keys=True) + "\n")


def summarize_live_tasks(tasks: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[tuple[str, str], int] = {}
    for task in tasks:
        key = (str(task.get("domain")), str(task.get("difficulty")))
        grouped[key] = grouped.get(key, 0) + 1
    return [
        {"domain": domain, "difficulty": difficulty, "num_tasks": count}
        for (domain, difficulty), count in sorted(grouped.items())
    ]


def write_live_task_stats(path: str | Path, tasks: Iterable[Dict[str, Any]]) -> None:
    rows = summarize_live_tasks(tasks)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["domain", "difficulty", "num_tasks"])
        writer.writeheader()
        writer.writerows(rows)


def _base_task(
    *,
    task_id: str,
    domain: str,
    tool_id: str,
    setup: Dict[str, Any],
    request: str,
    call: Dict[str, Any],
    observation: Dict[str, Any],
    state_change: Dict[str, Any],
    difficulty: str,
    forbidden: List[str] | None = None,
) -> Dict[str, Any]:
    return {
        "live_task_id": task_id,
        "domain": domain,
        "tool_id": tool_id,
        "initial_state_setup": setup,
        "user_request": request,
        "expected_tool_call": call,
        "expected_observation": observation,
        "expected_state_change": state_change,
        "forbidden_actions": forbidden or [],
        "cleanup_policy": "tempdir_per_task",
        "difficulty": difficulty,
    }


def _filesystem_setup(i: int) -> Dict[str, Any]:
    return {
        "directories": ["docs", "src", "notes"],
        "files": [
            {"path": "README.md", "content": f"ReliaSkill live filesystem fixture {i}\n"},
            {"path": "docs/plan.md", "content": f"Plan {i}: validate compact skills and sandbox execution.\n"},
            {"path": "src/app.py", "content": "print('hello live exec')\n"},
            {"path": "notes/todo.txt", "content": "write report\ncheck sqlite\n"},
        ],
    }


def _filesystem_tasks() -> List[Dict[str, Any]]:
    tasks = []
    for i in range(6):
        setup = _filesystem_setup(i)
        tasks.append(
            _base_task(
                task_id=f"live_fs_list_{i}",
                domain="filesystem",
                tool_id="fs_list_directory",
                setup=setup,
                request="List the sandbox docs directory.",
                call={"tool_name": "fs_list_directory", "arguments": {"path": "docs"}},
                observation={"ok": True, "entries": ["plan.md"]},
                state_change={"type": "no_change"},
                difficulty="easy",
            )
        )
        tasks.append(
            _base_task(
                task_id=f"live_fs_read_{i}",
                domain="filesystem",
                tool_id="fs_read_file",
                setup=setup,
                request="Read README.md from the temp workspace.",
                call={"tool_name": "fs_read_file", "arguments": {"path": "README.md"}},
                observation={"ok": True, "content": f"ReliaSkill live filesystem fixture {i}\n"},
                state_change={"type": "no_change"},
                difficulty="easy",
            )
        )
        tasks.append(
            _base_task(
                task_id=f"live_fs_search_{i}",
                domain="filesystem",
                tool_id="fs_search_files",
                setup=setup,
                request="Search the sandbox for compact skills.",
                call={"tool_name": "fs_search_files", "arguments": {"path": ".", "query": "compact skills"}},
                observation={"ok": True},
                state_change={"type": "no_change"},
                difficulty="medium",
            )
        )
        tasks.append(
            _base_task(
                task_id=f"live_fs_write_{i}",
                domain="filesystem",
                tool_id="fs_write_file",
                setup=setup,
                request="Write a safe output file under notes.",
                call={"tool_name": "fs_write_file", "arguments": {"path": "notes/result.txt", "content": f"live result {i}"}},
                observation={"ok": True, "path": "notes/result.txt"},
                state_change={"type": "filesystem_file_written", "path": "notes/result.txt", "content": f"live result {i}"},
                difficulty="medium",
            )
        )
        tasks.append(
            _base_task(
                task_id=f"live_fs_traversal_blocked_{i}",
                domain="filesystem",
                tool_id="fs_read_file",
                setup=setup,
                request="Try to read a path outside the sandbox.",
                call={"tool_name": "fs_read_file", "arguments": {"path": "../secret.txt"}},
                observation={"ok": False, "error": "path_traversal_blocked"},
                state_change={"type": "no_change"},
                difficulty="hard",
                forbidden=["path_traversal"],
            )
        )
    return tasks


def _sqlite_setup(i: int) -> Dict[str, Any]:
    return {
        "schema": [
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, active INTEGER)",
            "CREATE TABLE events (id INTEGER PRIMARY KEY, user_id INTEGER, title TEXT)",
        ],
        "rows": {
            "users": [
                {"id": 1, "name": "Ada", "active": 1},
                {"id": 2, "name": "Ben", "active": 0},
            ],
            "events": [{"id": 1, "user_id": 1, "title": f"Kickoff {i}"}],
        },
    }


def _sqlite_tasks() -> List[Dict[str, Any]]:
    tasks = []
    for i in range(5):
        setup = _sqlite_setup(i)
        tasks.append(
            _base_task(
                task_id=f"live_sql_select_{i}",
                domain="sqlite",
                tool_id="sql_select",
                setup=setup,
                request="List active users from the sandbox database.",
                call={"tool_name": "sql_select", "arguments": {"query": "SELECT name FROM users WHERE active = 1 ORDER BY id"}},
                observation={"ok": True, "rows": [{"name": "Ada"}], "row_count": 1},
                state_change={"type": "no_change"},
                difficulty="easy",
            )
        )
        tasks.append(
            _base_task(
                task_id=f"live_sql_schema_{i}",
                domain="sqlite",
                tool_id="sql_schema",
                setup=setup,
                request="Inspect the database schema.",
                call={"tool_name": "sql_schema", "arguments": {}},
                observation={"ok": True, "schema": {"users": ["id", "name", "active"], "events": ["id", "user_id", "title"]}},
                state_change={"type": "no_change"},
                difficulty="easy",
            )
        )
        tasks.append(
            _base_task(
                task_id=f"live_sql_insert_{i}",
                domain="sqlite",
                tool_id="sql_execute",
                setup=setup,
                request="Insert a new event row in the temp database.",
                call={"tool_name": "sql_execute", "arguments": {"query": f"INSERT INTO events (id, user_id, title) VALUES ({i + 10}, 2, 'Review {i}')"}},
                observation={"ok": True, "rows_changed": 1},
                state_change={"type": "sqlite_rows_changed", "table": "events", "min_delta": 1},
                difficulty="medium",
            )
        )
        tasks.append(
            _base_task(
                task_id=f"live_sql_update_{i}",
                domain="sqlite",
                tool_id="sql_execute",
                setup=setup,
                request="Activate Ben in the temp database.",
                call={"tool_name": "sql_execute", "arguments": {"query": "UPDATE users SET active = 1 WHERE name = 'Ben'"}},
                observation={"ok": True, "rows_changed": 1},
                state_change={"type": "sqlite_value_updated", "table": "users", "key": "active", "value": 1},
                difficulty="medium",
            )
        )
        tasks.append(
            _base_task(
                task_id=f"live_sql_invalid_{i}",
                domain="sqlite",
                tool_id="sql_select",
                setup=setup,
                request="Handle a malformed SQL read request safely.",
                call={"tool_name": "sql_select", "arguments": {"query": "SELEC name FROM users"}},
                observation={"ok": False, "error": "invalid_read_query"},
                state_change={"type": "no_change"},
                difficulty="hard",
            )
        )
    return tasks


def _git_setup(i: int) -> Dict[str, Any]:
    return {
        "branches": ["main", "dev", f"feature/live-{i}"],
        "current_branch": "main",
        "commits": [
            {"hash": f"a{i}01", "message": "Initial live fixture", "author": "ReliaSkill"},
            {"hash": f"b{i}02", "message": "Add sandbox docs", "author": "ReliaSkill"},
        ],
        "tracked_files": {"README.md": "hello\n", "src/app.py": "print('v1')\n"},
        "working_tree": {"README.md": "hello live\n", "src/app.py": "print('v1')\n", "notes.txt": "new note\n"},
    }


def _git_tasks() -> List[Dict[str, Any]]:
    tasks = []
    for i in range(4):
        setup = _git_setup(i)
        tasks.append(
            _base_task(
                task_id=f"live_git_status_{i}",
                domain="git",
                tool_id="git_status",
                setup=setup,
                request="Show repository status in the mock repo.",
                call={"tool_name": "git_status", "arguments": {}},
                observation={"ok": True, "branch": "main", "modified": ["README.md"], "untracked": ["notes.txt"], "deleted": []},
                state_change={"type": "git_no_change"},
                difficulty="easy",
            )
        )
        tasks.append(
            _base_task(
                task_id=f"live_git_log_{i}",
                domain="git",
                tool_id="git_log",
                setup=setup,
                request="Show the latest two commits.",
                call={"tool_name": "git_log", "arguments": {"limit": 2}},
                observation={"ok": True, "commits": setup["commits"][:2]},
                state_change={"type": "git_no_change"},
                difficulty="easy",
            )
        )
        tasks.append(
            _base_task(
                task_id=f"live_git_diff_{i}",
                domain="git",
                tool_id="git_diff",
                setup=setup,
                request="Show the diff for README.md.",
                call={"tool_name": "git_diff", "arguments": {"path": "README.md"}},
                observation={"ok": True, "changes": [{"path": "README.md", "before": "hello\n", "after": "hello live\n"}]},
                state_change={"type": "git_no_change"},
                difficulty="medium",
            )
        )
        tasks.append(
            _base_task(
                task_id=f"live_git_branches_{i}",
                domain="git",
                tool_id="git_branches",
                setup=setup,
                request="List local branches only.",
                call={"tool_name": "git_branches", "arguments": {}},
                observation={"ok": True, "current": "main", "branches": ["main", "dev", f"feature/live-{i}"]},
                state_change={"type": "git_no_change"},
                difficulty="medium",
            )
        )
        tasks.append(
            _base_task(
                task_id=f"live_git_network_blocked_{i}",
                domain="git",
                tool_id="git_fetch",
                setup=setup,
                request="Try a network git operation; it must be blocked.",
                call={"tool_name": "git_fetch", "arguments": {"remote": "origin"}},
                observation={"ok": False, "error": "network_operation_blocked"},
                state_change={"type": "git_no_change"},
                difficulty="hard",
                forbidden=["network", "git_fetch"],
            )
        )
    return tasks

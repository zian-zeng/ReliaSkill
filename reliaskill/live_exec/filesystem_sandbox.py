from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List


class FilesystemSandbox:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def setup(self, setup: Dict[str, Any]) -> None:
        for directory in setup.get("directories", []):
            self._safe_path(str(directory)).mkdir(parents=True, exist_ok=True)
        for item in setup.get("files", []):
            path = self._safe_path(str(item["path"]))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(str(item.get("content", "")), encoding="utf-8")

    def snapshot(self) -> Dict[str, Any]:
        files = {}
        directories: List[str] = []
        for path in sorted(self.root.rglob("*")):
            rel = path.relative_to(self.root).as_posix()
            if path.is_dir():
                directories.append(rel)
            elif path.is_file():
                files[rel] = path.read_text(encoding="utf-8")
        return {"directories": directories, "files": files}

    def call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if tool_name == "fs_list_directory":
                return self.list_directory(str(arguments.get("path", ".")))
            if tool_name == "fs_search_files":
                return self.search_files(str(arguments.get("path", ".")), str(arguments.get("query", "")))
            if tool_name == "fs_read_file":
                return self.read_file(str(arguments.get("path", "")))
            if tool_name == "fs_write_file":
                return self.write_file(str(arguments.get("path", "")), str(arguments.get("content", "")))
            return {"ok": False, "error": f"unknown filesystem tool: {tool_name}"}
        except PermissionError as exc:
            return {"ok": False, "error": "path_traversal_blocked", "detail": str(exc), "unsafe_action_blocked": True}
        except FileNotFoundError as exc:
            return {"ok": False, "error": "not_found", "detail": str(exc)}
        except IsADirectoryError as exc:
            return {"ok": False, "error": "is_directory", "detail": str(exc)}

    def list_directory(self, path: str) -> Dict[str, Any]:
        target = self._safe_path(path)
        entries = sorted(child.name for child in target.iterdir())
        return {"ok": True, "entries": entries}

    def search_files(self, path: str, query: str) -> Dict[str, Any]:
        target = self._safe_path(path)
        matches = []
        for child in sorted(target.rglob("*")):
            if not child.is_file():
                continue
            rel = child.relative_to(self.root).as_posix()
            text = child.read_text(encoding="utf-8")
            if query.lower() in text.lower() or query.lower() in child.name.lower():
                matches.append({"path": rel, "snippet": _snippet(text, query)})
        return {"ok": True, "matches": matches}

    def read_file(self, path: str) -> Dict[str, Any]:
        target = self._safe_path(path)
        return {"ok": True, "path": target.relative_to(self.root).as_posix(), "content": target.read_text(encoding="utf-8")}

    def write_file(self, path: str, content: str) -> Dict[str, Any]:
        target = self._safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"ok": True, "path": target.relative_to(self.root).as_posix(), "bytes_written": len(content.encode("utf-8"))}

    def _safe_path(self, value: str) -> Path:
        raw = Path(value)
        if raw.is_absolute():
            raise PermissionError(f"absolute path is outside sandbox: {value}")
        target = (self.root / raw).resolve()
        if target != self.root and self.root not in target.parents:
            raise PermissionError(f"path escapes sandbox: {value}")
        return target


def _snippet(text: str, query: str) -> str:
    if not query:
        return text[:80]
    lower = text.lower()
    index = lower.find(query.lower())
    if index < 0:
        return text[:80]
    start = max(0, index - 24)
    end = min(len(text), index + len(query) + 40)
    return text[start:end]

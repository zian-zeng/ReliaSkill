from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List


class SQLiteSandbox:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self.conn.close()

    def setup(self, setup: Dict[str, Any]) -> None:
        for statement in setup.get("schema", []):
            self.conn.execute(str(statement))
        for table, rows in (setup.get("rows") or {}).items():
            for row in rows:
                keys = list(row)
                placeholders = ", ".join("?" for _ in keys)
                columns = ", ".join(keys)
                self.conn.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", [row[key] for key in keys])
        self.conn.commit()

    def snapshot(self) -> Dict[str, Any]:
        tables = self._tables()
        return {
            "tables": {
                table: [dict(row) for row in self.conn.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()]
                for table in tables
            },
            "schema": self.schema()["schema"],
        }

    def call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if tool_name == "sql_select":
                return self.select(str(arguments.get("query", "")))
            if tool_name == "sql_execute":
                return self.execute(str(arguments.get("query", "")))
            if tool_name == "sql_schema":
                return self.schema()
            return {"ok": False, "error": f"unknown sqlite tool: {tool_name}"}
        except sqlite3.Error as exc:
            self.conn.rollback()
            return {"ok": False, "error": "sqlite_error", "detail": str(exc)}

    def select(self, query: str) -> Dict[str, Any]:
        if not query.strip().lower().startswith("select"):
            return {"ok": False, "error": "invalid_read_query"}
        rows = [dict(row) for row in self.conn.execute(query).fetchall()]
        return {"ok": True, "rows": rows, "row_count": len(rows)}

    def execute(self, query: str) -> Dict[str, Any]:
        lowered = query.strip().lower()
        if lowered.startswith(("attach", "detach", "pragma", "vacuum")):
            return {"ok": False, "error": "unsafe_sql_blocked", "unsafe_action_blocked": True}
        cursor = self.conn.execute(query)
        self.conn.commit()
        return {"ok": True, "rows_changed": cursor.rowcount if cursor.rowcount >= 0 else 0}

    def schema(self) -> Dict[str, Any]:
        schema: Dict[str, List[str]] = {}
        for table in self._tables():
            columns = [row["name"] for row in self.conn.execute(f"PRAGMA table_info({table})").fetchall()]
            schema[table] = columns
        return {"ok": True, "schema": schema}

    def _tables(self) -> List[str]:
        rows = self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
        return [str(row["name"]) for row in rows]

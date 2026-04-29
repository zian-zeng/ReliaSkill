from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from reliaskill.condition_registry import CONDITION_REGISTRY
from reliaskill.human_skill_condition import HUMAN_WRITTEN_SKILL, validate_human_skill_directory
from scripts.build_human_skill_packets import build_authoring_packets
from scripts.sample_human_skill_subset import load_hard_negative_tools, sample_human_skill_subset, subset_record


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def _tool(name: str, domain: str, difficulty: str, *, side_effect: bool = False) -> dict:
    return {
        "tool_name": name,
        "domain": domain,
        "difficulty_tier": difficulty,
        "tool_purpose": f"Use {name} for a controlled {domain} action.",
        "input_schema_raw": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query."}},
            "required": ["query"],
        },
        "arguments": [
            {
                "name": "query",
                "type": "string",
                "required": True,
                "description": "Search query.",
                "schema_path": "$.properties.query",
            }
        ],
        "doc_snippets": [f"Sparse docs for {name}."],
        "schema_complexity": {
            "num_arguments": 1,
            "num_required_arguments": 1,
            "has_side_effect": side_effect,
            "side_effect_type": "write" if side_effect else "read",
        },
        "source_metadata": {
            "source_id": f"{domain.replace('/', '_')}_fixture",
            "source_type": "mcp_fixture",
            "difficulty_tier": difficulty,
            "domain": domain,
            "has_side_effect": side_effect,
        },
    }


class HumanSkillWorkflowTests(unittest.TestCase):
    def test_condition_registry_exposes_artifact_backed_human_condition(self) -> None:
        self.assertIn(HUMAN_WRITTEN_SKILL, CONDITION_REGISTRY)
        self.assertTrue(CONDITION_REGISTRY[HUMAN_WRITTEN_SKILL]["requires_human_artifact"])

    def test_sampling_prefers_balanced_side_effect_and_hard_negative_tools(self) -> None:
        tools = [
            _tool("search_docs", "search/retrieval", "easy"),
            _tool("write_note", "memory/notes", "hard", side_effect=True),
            _tool("create_issue", "issue-tracking", "hard", side_effect=True),
            _tool("list_files", "filesystem", "easy"),
        ]
        hard_negative_tools = {"write_note", "create_issue"}

        subset = sample_human_skill_subset(
            tools,
            hard_negative_tools=hard_negative_tools,
            target_count=4,
            min_count=2,
            max_count=4,
            min_side_effect_tools=2,
            min_hard_negative_tools=2,
            seed=42,
        )
        rows = [subset_record(record, hard_negative_tools) for record in subset]

        self.assertEqual(len(rows), 4)
        self.assertGreaterEqual(sum(1 for row in rows if row["has_side_effect"]), 2)
        self.assertGreaterEqual(sum(1 for row in rows if row["has_hard_negative_controls"]), 2)

    def test_authoring_packets_do_not_create_fake_completed_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tool = _tool("search_docs", "search/retrieval", "easy")
            tool_id = "search_fixture::search_docs"
            rows = build_authoring_packets(
                [{"tool_id": tool_id, "tool_name": "search_docs"}],
                tools={tool_id: tool, "search_docs": tool},
                output_dir=root / "packets",
                skills_dir=root / "skills",
                token_budget=250,
            )

            packet = Path(rows[0]["packet_path"])
            self.assertTrue((packet / "AUTHORING_INSTRUCTIONS.md").exists())
            self.assertTrue((packet / "metadata_template.json").exists())
            self.assertFalse((root / "skills" / "search_fixture__search_docs" / "SKILL.md").exists())

    def test_validate_human_skill_directory_accepts_real_artifact_and_rejects_control_leak(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tools_path = root / "tools.jsonl"
            skill_dir = root / "skills" / "search_fixture__search_docs"
            bad_dir = root / "skills" / "search_fixture__bad_docs"
            tool = _tool("search_docs", "search/retrieval", "easy")
            _write_jsonl(tools_path, [tool])

            _write_skill(skill_dir, tool_id="search_retrieval_fixture::search_docs", author_saw_controls=False)
            _write_skill(bad_dir, tool_id="search_retrieval_fixture::search_docs", author_saw_controls=True)

            validations = validate_human_skill_directory(root / "skills", tools_path)
            by_path = {Path(item.skill_path).parent.name: item for item in validations}

            self.assertTrue(by_path["search_fixture__search_docs"].valid)
            self.assertFalse(by_path["search_fixture__bad_docs"].valid)
            self.assertIn("metadata", by_path["search_fixture__bad_docs"].failure_codes)

    def test_validate_human_skills_cli_writes_empty_report_when_no_artifacts_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tools_path = root / "tools.jsonl"
            _write_jsonl(tools_path, [_tool("search_docs", "search/retrieval", "easy")])
            out = root / "validation.csv"
            report = root / "validation.md"

            subprocess.run(
                [
                    sys.executable,
                    "scripts/validate_human_skills.py",
                    "--skills",
                    str(root / "empty_skills"),
                    "--tools",
                    str(tools_path),
                    "--output",
                    str(out),
                    "--report",
                    str(report),
                ],
                cwd=Path.cwd(),
                check=True,
            )

            self.assertTrue(out.exists())
            self.assertTrue(report.exists())
            with out.open("r", encoding="utf-8") as f:
                self.assertEqual(list(csv.DictReader(f)), [])


def _write_skill(directory: Path, *, tool_id: str, author_saw_controls: bool) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "SKILL.md").write_text(
        """# search_docs

## Summary
Search known documentation using an explicit query string.

## When to use
- Use when the user asks to search documentation and gives a query.

## When not to use
- Do not use for writing, deleting, or when no query is provided.

## Argument template
```json
{"query": "release notes"}
```

## Examples
```json
{"arguments": {"query": "release notes"}}
```
""",
        encoding="utf-8",
    )
    (directory / "metadata.json").write_text(
        json.dumps(
            {
                "tool_id": tool_id,
                "author_id": "annotator_a",
                "authoring_time_minutes": 12,
                "author_saw_controls": author_saw_controls,
                "token_budget": 250,
                "notes": "",
            }
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()

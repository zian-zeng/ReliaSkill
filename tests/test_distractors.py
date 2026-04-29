from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from reliaskill.distractors import (
    build_routing_examples,
    distractor_score,
    load_distractor_config,
    load_tool_profiles,
    summarize_distractor_examples,
    write_distractor_stats,
    write_routing_examples,
)


def _tool_record(name: str, domain: str, side_effect: str, description: str, args: list[str]) -> dict:
    return {
        "tool_name": name,
        "server_name": "fixture",
        "tool_purpose": description,
        "arguments": [{"name": arg, "type": "string", "required": True} for arg in args],
        "source_metadata": {"domain": domain, "side_effect_type": side_effect},
        "schema_complexity": {"side_effect_type": side_effect},
    }


class DistractorInventoryTests(unittest.TestCase):
    def test_distractor_score_uses_name_args_domain_and_opposite_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tools_path = Path(tmpdir) / "tools.jsonl"
            records = [
                _tool_record("read_file", "filesystem", "read", "Read a file by path.", ["path"]),
                _tool_record("write_file", "filesystem", "write", "Write file content by path.", ["path", "content"]),
            ]
            tools_path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")
            profiles = load_tool_profiles(tools_path)

        score = distractor_score(profiles["read_file"], profiles["write_file"])
        self.assertGreater(score["name_similarity"], 0.0)
        self.assertGreater(score["arg_overlap"], 0.0)
        self.assertTrue(score["same_domain"])
        self.assertTrue(score["confusing_opposite_action"])

    def test_build_routing_examples_outputs_all_levels_and_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tools_path = Path(tmpdir) / "tools.jsonl"
            controls_path = Path(tmpdir) / "controls.jsonl"
            records = [
                _tool_record("read_file", "filesystem", "read", "Read a file by path.", ["path"]),
                _tool_record("write_file", "filesystem", "write", "Write file content by path.", ["path", "content"]),
                _tool_record("search_files", "filesystem", "read", "Search files by query.", ["query"]),
                _tool_record("send_email", "messaging", "external_communication", "Send an email.", ["to", "body"]),
                _tool_record("calendar_create_event", "calendar", "write", "Create a calendar event.", ["title"]),
                _tool_record("sql_query", "database", "read", "Run a SQL query.", ["query"]),
            ]
            tools_path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")
            control = {
                "control_id": "ctrl_read_file_positive",
                "tool_name": "read_file",
                "gold_tool": "read_file",
                "gold_args": {"path": "docs/a.md"},
                "user_request": "Read docs/a.md",
                "should_trigger": True,
                "split": "test",
                "difficulty": "hard",
                "control_family": "positive",
            }
            controls_path.write_text(json.dumps(control) + "\n", encoding="utf-8")
            profiles = load_tool_profiles(tools_path)
            examples = build_routing_examples(
                profiles,
                [control],
                {"seed": 42, "candidate_set_sizes": [4], "distractor_levels": ["easy", "medium", "hard", "adversarial"]},
            )

        self.assertEqual(len(examples), 4)
        self.assertEqual({example["distractor_level"] for example in examples}, {"easy", "medium", "hard", "adversarial"})
        required = {
            "target_tool_id",
            "user_request",
            "candidate_tool_ids",
            "correct_tool_id",
            "distractor_level",
            "distractor_generation_reason",
            "should_trigger",
        }
        positions = []
        for example in examples:
            self.assertTrue(required.issubset(example))
            self.assertEqual(len(example["candidate_tool_ids"]), 4)
            self.assertIn("read_file", example["candidate_tool_ids"])
            positions.append(example["candidate_tool_ids"].index("read_file"))
        self.assertGreater(len(set(positions)), 1)

    def test_stats_and_cli_write_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            tools_path = tmpdir_path / "tools.jsonl"
            controls_path = tmpdir_path / "controls.jsonl"
            output_path = tmpdir_path / "routing.jsonl"
            stats_path = tmpdir_path / "distractor_stats.csv"
            config_path = tmpdir_path / "distractor.yaml"
            records = [
                _tool_record("read_file", "filesystem", "read", "Read a file by path.", ["path"]),
                _tool_record("write_file", "filesystem", "write", "Write file content by path.", ["path", "content"]),
                _tool_record("search_files", "filesystem", "read", "Search files by query.", ["query"]),
                _tool_record("send_email", "messaging", "external_communication", "Send an email.", ["to", "body"]),
                _tool_record("calendar_create_event", "calendar", "write", "Create a calendar event.", ["title"]),
                _tool_record("sql_query", "database", "read", "Run a SQL query.", ["query"]),
            ]
            tools_path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")
            controls_path.write_text(
                json.dumps(
                    {
                        "control_id": "ctrl_read_file_negative",
                        "tool_name": "read_file",
                        "negative_target": "read_file",
                        "gold_tool": "__abstain__",
                        "gold_args": {},
                        "user_request": "Explain when to read files; do not call anything.",
                        "should_trigger": False,
                        "split": "test",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            config_path.write_text(
                yaml.safe_dump(
                    {
                        "seed": 42,
                        "candidate_set_sizes": [4],
                        "distractor_levels": ["easy", "hard"],
                        "outputs": {"stats": str(stats_path)},
                    }
                ),
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    "scripts/build_distractor_inventories.py",
                    "--tools",
                    str(tools_path),
                    "--controls",
                    str(controls_path),
                    "--output",
                    str(output_path),
                    "--config",
                    str(config_path),
                ],
                cwd=Path.cwd(),
                check=True,
            )

            self.assertTrue(output_path.exists())
            self.assertTrue(stats_path.exists())
            examples = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(examples), 2)
            with stats_path.open("r", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(rows[0]["num_examples"], "2")
            self.assertIn("avg_name_similarity", rows[0])


if __name__ == "__main__":
    unittest.main()

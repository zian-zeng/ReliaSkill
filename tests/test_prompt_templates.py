from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from autoskill.backends import build_backend_from_config
from autoskill.ir import ArgumentIR, ToolIR
from autoskill.prompt_templates import (
    PROMPT_TEMPLATE_CONDITIONS,
    PROMPT_TEMPLATE_SPECS,
    build_generation_prompt_from_template,
    generate_prompt_template_skills,
    parse_generated_skill_output,
)
from reliaskill.condition_registry import CONDITION_REGISTRY


class PromptTemplateTests(unittest.TestCase):
    def test_prompt_template_metadata_and_conditions_are_registered(self) -> None:
        expected = {
            "compact_default",
            "boundary_first",
            "schema_faithful_minimal",
            "example_rich",
            "safety_side_effect_aware",
            "negative_control_aware_dev_only",
            "verbose_docs_style",
        }

        self.assertTrue(expected.issubset(PROMPT_TEMPLATE_SPECS))
        for condition, template_id in PROMPT_TEMPLATE_CONDITIONS.items():
            self.assertIn(condition, CONDITION_REGISTRY)
            self.assertEqual(CONDITION_REGISTRY[condition]["template_id"], template_id)
            self.assertIn("when_not_to_use", CONDITION_REGISTRY[condition]["allowed_sections"])

    def test_prompt_contains_schema_faithfulness_and_dev_control_constraints(self) -> None:
        prompt = build_generation_prompt_from_template(
            _tool(),
            "negative_control_aware_dev_only",
            dev_controls=[
                {
                    "split": "dev",
                    "negative_category": "near_miss_intent",
                    "gold_args": {"secret": "not included"},
                    "user_request": "not included",
                }
            ],
        )

        self.assertIn("Do not invent arguments", prompt)
        self.assertIn("Use only schema-supported parameter names", prompt)
        self.assertIn("near_miss_intent", prompt)
        self.assertNotIn("secret", prompt)

    def test_parser_records_malformed_output_without_accepting_it(self) -> None:
        skill = parse_generated_skill_output(
            '{"skill_summary": "bad", "when_to_use": []}',
            template_id="compact_default",
            tool=_tool(),
        )

        self.assertFalse(skill.metadata["parse_ok"])
        self.assertIn("missing required skill fields", skill.metadata["parse_error"])
        self.assertEqual(skill.skill_summary, "")

    def test_backend_config_selects_prompt_template(self) -> None:
        backend = build_backend_from_config({"type": "heuristic", "prompt_template_id": "boundary_first"})
        skill = backend.generate_skill(_tool(side_effect=True))

        self.assertEqual(skill.metadata["template_id"], "boundary_first")
        self.assertTrue(any("abstention" in line.lower() for line in skill.when_not_to_use))

    def test_generate_prompt_template_skills_writes_outputs_and_stats(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            records = generate_prompt_template_skills(
                [_tool()],
                template_ids=["compact_default", "example_rich"],
                output_root=root / "generated",
                stats_path=root / "stats.csv",
            )

            self.assertEqual(len(records), 2)
            self.assertTrue((root / "generated" / "compact_default" / "search_docs.json").exists())
            with (root / "stats.csv").open("r", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual({row["template_id"] for row in rows}, {"compact_default", "example_rich"})

    def test_run_generation_prompt_templates_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tools_path = root / "tools.jsonl"
            config_path = root / "prompt_templates.yaml"
            _write_jsonl(tools_path, [_tool_record()])
            config_path.write_text(
                f"""
tools_path: {tools_path}
dev_controls_path: {root / 'missing_dev.jsonl'}
max_tools: 1
prompt_templates:
  enabled: true
  output_root: {root / 'generated_skills'}
  stats_path: {root / 'prompt_template_generation_stats.csv'}
  template_ids:
    - compact_default
    - safety_side_effect_aware
""",
                encoding="utf-8",
            )

            subprocess.run(
                [sys.executable, "scripts/run_generation.py", "--config", str(config_path), "--prompt-templates"],
                cwd=Path.cwd(),
                check=True,
            )

            self.assertTrue((root / "generated_skills" / "compact_default" / "search_docs.json").exists())
            self.assertTrue((root / "prompt_template_generation_stats.csv").exists())


def _tool(side_effect: bool = False) -> ToolIR:
    return ToolIR(
        tool_name="search_docs",
        tool_purpose="Search project documentation for matching text.",
        input_schema_raw={
            "type": "object",
            "properties": {"query": {"type": "string"}, "case_sensitive": {"type": "boolean"}},
            "required": ["query"],
        },
        arguments=[
            ArgumentIR(name="query", type="string", required=True, schema_path="$.properties.query"),
            ArgumentIR(name="case_sensitive", type="boolean", required=False, schema_path="$.properties.case_sensitive"),
        ],
        schema_complexity={"has_side_effect": side_effect, "side_effect_type": "write" if side_effect else "read"},
        side_effect_hints=["updates_index"] if side_effect else [],
        safety_hints=["review_side_effects_before_deployment"] if side_effect else [],
    )


def _tool_record() -> dict:
    return {
        "tool_name": "search_docs",
        "tool_purpose": "Search project documentation for matching text.",
        "input_schema_raw": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
        "arguments": [{"name": "query", "type": "string", "required": True, "schema_path": "$.properties.query"}],
        "schema_complexity": {"has_side_effect": False, "side_effect_type": "read"},
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


if __name__ == "__main__":
    unittest.main()

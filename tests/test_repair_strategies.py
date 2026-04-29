from __future__ import annotations

import json
import unittest
from pathlib import Path

from autoskill.behavior import load_behavior_cases, run_behavior_tests
from autoskill.ir import GeneratedSkill
from autoskill.parser import parse_mcp_tool
from autoskill.repair import (
    FAILURE_TAXONOMY,
    FAILURE_TAXONOMY_REPAIR,
    FULL_REGENERATION,
    NONUSE_BOUNDARY_PATCH,
    TARGETED_SECTION_PATCH,
    get_repair_strategy,
    repair_behavior_failures,
    repair_skill,
)


def _load_tool(name: str):
    raw_tools = json.loads(Path("data/raw/sample_tools.json").read_text(encoding="utf-8"))
    for index, raw_tool in enumerate(raw_tools):
        if raw_tool["name"] == name:
            return parse_mcp_tool(raw_tool, source_pointer=f"sample_tools#{index}")
    raise AssertionError(f"missing fixture tool {name}")


def _load_public_tool(name: str):
    raw_tools = json.loads(Path("data/raw/public_mcp_filesystem_subset.json").read_text(encoding="utf-8"))
    for index, raw_tool in enumerate(raw_tools):
        if raw_tool["name"] == name:
            return parse_mcp_tool(raw_tool, source_pointer=f"public_tools#{index}")
    raise AssertionError(f"missing fixture tool {name}")


class RepairStrategyTests(unittest.TestCase):
    def test_strategy_registry_exposes_requested_strategies(self) -> None:
        for name in [
            "no_repair",
            "full_regeneration",
            "targeted_section_patch",
            "nonuse_boundary_patch",
            "example_repair",
            "argument_template_repair",
            "failure_taxonomy_repair",
        ]:
            self.assertEqual(get_repair_strategy(name).name, name)

    def test_targeted_patch_report_contains_trace_fields(self) -> None:
        tool = _load_tool("get_weather")
        skill = GeneratedSkill(
            baseline_name="repaired_targeted_patch",
            skill_summary="Weather lookup.",
            when_to_use=["Use for weather."],
            when_not_to_use=[],
            argument_template={"city": "Paris", "unit": "K", "extra": True},
            examples=[{"scenario": "bad", "arguments": {"city": "Paris", "unit": "K", "extra": True}}],
        )

        repaired, report, validation = repair_skill(tool, skill, strategy=TARGETED_SECTION_PATCH)

        self.assertTrue(report.changed)
        self.assertEqual(report.strategy, TARGETED_SECTION_PATCH)
        self.assertEqual(report.failure_type, "unsupported_argument")
        self.assertIn("argument_template", report.modified_sections)
        self.assertIn("validation_before", report.model_dump())
        self.assertIn("validation_after", report.model_dump())
        self.assertTrue(report.original_skill_hash)
        self.assertTrue(report.repaired_skill_hash)
        self.assertNotEqual(report.original_skill_hash, report.repaired_skill_hash)
        self.assertTrue(report.patch_text)
        self.assertTrue(report.repair_trace)
        self.assertTrue(validation.valid)
        self.assertNotIn("extra", repaired.argument_template)

    def test_full_regeneration_and_taxonomy_are_distinct_strategies(self) -> None:
        tool = _load_tool("get_weather")
        skill = GeneratedSkill(
            baseline_name="repair_compare",
            skill_summary="Weather lookup.",
            when_to_use=["Use for weather."],
            when_not_to_use=[],
            argument_template={"city": "Paris", "unit": "K"},
            examples=[{"scenario": "bad", "arguments": {"city": "Paris", "unit": "K"}}],
        )

        regenerated, regen_report, _ = repair_skill(tool, skill, strategy=FULL_REGENERATION)
        taxonomy, taxonomy_report, _ = repair_skill(tool, skill, strategy=FAILURE_TAXONOMY_REPAIR)

        self.assertEqual(regen_report.strategy, FULL_REGENERATION)
        self.assertEqual(taxonomy_report.strategy, FAILURE_TAXONOMY_REPAIR)
        self.assertNotEqual(regenerated.skill_summary, taxonomy.skill_summary)
        self.assertIn("invalid_enum", FAILURE_TAXONOMY.values())

    def test_boundary_repair_logs_dev_behavior_before_and_after(self) -> None:
        tool = _load_public_tool("write_file")
        skill = GeneratedSkill(
            baseline_name="repaired_boundary_only",
            skill_summary="Write files and search docs.",
            when_to_use=["Use this for search docs and deployment notes."],
            when_not_to_use=["Do not use for unrelated tasks."],
            argument_template={"path": "docs/out.txt", "content": "notes"},
            examples=[],
        )
        cases = load_behavior_cases("data/eval/public_mcp_filesystem_reliability.jsonl")
        before = run_behavior_tests(tool, skill, cases)

        _, report, validation = repair_behavior_failures(
            tool,
            skill,
            before,
            strategy=NONUSE_BOUNDARY_PATCH,
            behavior_cases=cases,
        )

        self.assertTrue(report.changed)
        self.assertEqual(report.strategy, NONUSE_BOUNDARY_PATCH)
        self.assertEqual(report.failure_type, "over_triggering")
        self.assertIn("when_not_to_use", report.modified_sections)
        self.assertTrue(report.behavior_before_dev)
        self.assertTrue(report.behavior_after_dev)
        self.assertTrue(validation.valid)


if __name__ == "__main__":
    unittest.main()

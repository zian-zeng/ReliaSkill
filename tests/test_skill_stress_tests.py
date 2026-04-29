from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from autoskill.ir import ArgumentIR, GeneratedSkill, ToolIR
from reliaskill.condition_registry import CONDITION_REGISTRY
from reliaskill.stress_tests.corrupt_skills import (
    CORRUPTION_TYPES,
    STRESS_TEST_CONDITIONS,
    build_stress_test_inventory,
    corrupt_skill,
    evaluate_stress_detection,
)


class SkillStressTests(unittest.TestCase):
    def test_stress_conditions_are_diagnostic_only(self) -> None:
        for condition in STRESS_TEST_CONDITIONS:
            self.assertIn(condition, CONDITION_REGISTRY)
            self.assertTrue(CONDITION_REGISTRY[condition]["diagnostic_only"])
            self.assertTrue(CONDITION_REGISTRY[condition]["requires_explicit_configuration"])

    def test_each_corruption_records_type_location_and_target(self) -> None:
        tool = _tool()
        original = _skill()

        for corruption_type in CORRUPTION_TYPES:
            corrupted = corrupt_skill(tool, original, corruption_type)
            self.assertEqual(corrupted.metadata["corruption_type"], corruption_type)
            self.assertTrue(corrupted.metadata["corruption_location"])
            self.assertIn(corrupted.metadata["expected_detection_target"], {"structural_validator", "behavior_tests", "safety_checker", "gating"})
            self.assertTrue(corrupted.metadata["diagnostic_adversarial"])

    def test_structural_detection_catches_invented_argument_and_bad_examples(self) -> None:
        for corruption_type in ["invented_argument", "malformed_json_example", "invalid_enum"]:
            corrupted = corrupt_skill(_tool(), _skill(), corruption_type)
            detection = evaluate_stress_detection(_tool(), corrupted)

            self.assertFalse(detection["structural_valid"])
            self.assertGreaterEqual(detection["validation_error_count"], 1)

    def test_inventory_builder_writes_stress_artifacts_and_detection_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            rows = build_stress_test_inventory(
                [_tool()],
                output_root=root / "stress_skills",
                inventory_path=root / "inventory.csv",
                detection_path=root / "detection.csv",
                condition_filter=["corrupted_skill_invented_arg", "corrupted_skill_overbroad"],
            )

            self.assertEqual(len(rows), 4)
            self.assertTrue((root / "inventory.csv").exists())
            self.assertTrue((root / "detection.csv").exists())
            self.assertTrue(any((root / "stress_skills").rglob("skill.json")))
            with (root / "inventory.csv").open("r", encoding="utf-8") as f:
                inventory = list(csv.DictReader(f))
            self.assertEqual({row["diagnostic_only"] for row in inventory}, {"True"})

    def test_build_skill_stress_tests_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tools_path = root / "tools.jsonl"
            _write_jsonl(tools_path, [_tool_record()])

            subprocess.run(
                [
                    sys.executable,
                    "scripts/build_skill_stress_tests.py",
                    "--tools",
                    str(tools_path),
                    "--output",
                    str(root / "stress_skills"),
                    "--inventory",
                    str(root / "inventory.csv"),
                    "--detection",
                    str(root / "detection.csv"),
                    "--max-tools",
                    "1",
                    "--conditions",
                    "corrupted_skill_invented_arg",
                    "corrupted_skill_malformed_example",
                ],
                cwd=Path.cwd(),
                check=True,
            )

            self.assertTrue((root / "inventory.csv").exists())
            with (root / "inventory.csv").open("r", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 4)


def _tool() -> ToolIR:
    return ToolIR(
        tool_name="update_issue",
        tool_purpose="Update an issue title or status.",
        input_schema_raw={
            "type": "object",
            "properties": {
                "issue_id": {"type": "string"},
                "status": {"type": "string", "enum": ["open", "closed"]},
                "notify": {"type": "boolean"},
            },
            "required": ["issue_id", "status"],
            "additionalProperties": False,
        },
        arguments=[
            ArgumentIR(name="issue_id", type="string", required=True, schema_path="$.properties.issue_id"),
            ArgumentIR(name="status", type="string", required=True, enum=["open", "closed"], schema_path="$.properties.status"),
            ArgumentIR(name="notify", type="boolean", required=False, schema_path="$.properties.notify"),
        ],
        schema_complexity={"has_side_effect": True, "side_effect_type": "write"},
        side_effect_hints=["updates_resource"],
        safety_hints=["review_side_effects_before_deployment"],
    )


def _skill() -> GeneratedSkill:
    return GeneratedSkill(
        baseline_name="autoskill_base",
        skill_summary="Update an issue only when the issue id and status are explicit.",
        when_to_use=["Use when issue_id and status are provided."],
        when_not_to_use=["Do not update issues for preview-only or missing-information requests."],
        argument_template={"issue_id": "ISSUE-1", "status": "open", "notify": False},
        examples=[{"scenario": "Close an issue.", "arguments": {"issue_id": "ISSUE-1", "status": "closed"}}],
    )


def _tool_record() -> dict:
    return {
        "tool_name": "update_issue",
        "tool_purpose": "Update an issue title or status.",
        "input_schema_raw": _tool().input_schema_raw,
        "arguments": [arg.model_dump() for arg in _tool().arguments],
        "schema_complexity": {"has_side_effect": True, "side_effect_type": "write"},
        "side_effect_hints": ["updates_resource"],
        "safety_hints": ["review_side_effects_before_deployment"],
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from autoskill.backends import HeuristicBackend
from autoskill.ir import ArgumentIR, ToolIR
from autoskill.multi_candidate import generate_skill_candidates
from autoskill.templates import (
    build_argument_template,
    build_optional_argument_examples,
    build_structured_call_hints,
)
from autoskill.validator import validate_skill


def _complex_call_tool() -> ToolIR:
    payload_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "metadata": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string"},
                    "team": {"type": "string"},
                },
                "required": ["owner"],
            },
            "priority": {"type": "string", "enum": ["low", "high"]},
        },
        "required": ["title", "metadata"],
    }
    input_schema = {
        "type": "object",
        "properties": {
            "ticket_id": {"type": "string"},
            "status": {"type": "string", "enum": ["open", "closed"]},
            "payload": payload_schema,
            "tags": {"type": "array", "items": {"type": "string"}},
            "notify": {"type": "boolean"},
        },
        "required": ["ticket_id", "status", "payload"],
        "additionalProperties": False,
    }
    return ToolIR(
        tool_name="update_ticket",
        tool_purpose="Update a ticket with a structured payload.",
        input_schema_raw=input_schema,
        arguments=[
            ArgumentIR(name="ticket_id", type="string", required=True),
            ArgumentIR(name="status", type="string", required=True, enum=["open", "closed"]),
            ArgumentIR(
                name="payload",
                type="object",
                required=True,
                properties=payload_schema["properties"],
                required_properties=["title", "metadata"],
            ),
            ArgumentIR(name="tags", type="array", required=False, items_type="string"),
            ArgumentIR(name="notify", type="boolean", required=False),
        ],
    )


def _read_text_file_tool() -> ToolIR:
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "head": {"type": "integer"},
            "tail": {"type": "integer"},
        },
        "required": ["path"],
        "additionalProperties": False,
    }
    return ToolIR(
        tool_name="read_text_file",
        tool_purpose="Read text from a file.",
        input_schema_raw=input_schema,
        arguments=[
            ArgumentIR(name="path", type="string", required=True),
            ArgumentIR(name="head", type="integer", required=False),
            ArgumentIR(name="tail", type="integer", required=False),
        ],
    )


class StructuredCallConstructionTests(unittest.TestCase):
    def test_required_only_template_is_schema_literal_and_recursive(self) -> None:
        tool = _complex_call_tool()

        minimal = build_argument_template(tool, include_optional=False)
        full = build_argument_template(tool, include_optional=True)

        self.assertEqual(set(minimal), {"ticket_id", "status", "payload"})
        self.assertEqual(minimal["status"], "open")
        self.assertEqual(set(minimal["payload"]), {"title", "metadata"})
        self.assertEqual(set(minimal["payload"]["metadata"]), {"owner"})
        self.assertNotIn("priority", minimal["payload"])
        self.assertNotIn("tags", minimal)
        self.assertIn("priority", full["payload"])
        self.assertIn("tags", full)

    def test_generated_skill_avoids_unsupported_optional_field_clutter(self) -> None:
        tool = _complex_call_tool()
        skill = HeuristicBackend(ablation_mode="base_only").generate_skill(tool)

        self.assertEqual(set(skill.argument_template), {"ticket_id", "status", "payload"})
        allowed = {arg.name for arg in tool.arguments}
        required = {arg.name for arg in tool.arguments if arg.required}
        for example in skill.examples:
            arguments = example["arguments"]
            self.assertLessEqual(set(arguments), allowed)
            self.assertTrue(required.issubset(arguments))
            self.assertLessEqual(len(set(arguments) - required), 1)

        report = validate_skill(tool, skill)
        self.assertTrue(report.valid, msg=[issue.message for issue in report.issues])

    def test_hints_cover_enums_arrays_nested_objects_and_allowed_fields(self) -> None:
        tool = _complex_call_tool()
        hints = build_structured_call_hints(tool)
        all_hints = "\n".join([*hints["when_to_use"], *hints["when_not_to_use"]])

        self.assertIn("Use exact enum literals for `status`: 'open', 'closed'.", all_hints)
        self.assertIn("For nested object `payload`, include its required keys: 'title', 'metadata'.", all_hints)
        self.assertIn("Omit optional array `tags` unless the request explicitly asks for it.", all_hints)
        self.assertIn("allowed top-level fields are: `ticket_id`, `status`, `payload`, `tags`, `notify`.", all_hints)

    def test_optional_examples_add_one_requested_optional_field_at_a_time(self) -> None:
        tool = _complex_call_tool()
        examples = build_optional_argument_examples(tool, max_examples=10)

        self.assertEqual(len(examples), 2)
        required = {arg.name for arg in tool.arguments if arg.required}
        allowed = {arg.name for arg in tool.arguments}
        for example in examples:
            arguments = example["arguments"]
            self.assertTrue(required.issubset(arguments))
            self.assertLessEqual(set(arguments), allowed)
            self.assertEqual(len(set(arguments) - required), 1)

        tags_example = next(example for example in examples if "tags" in example["arguments"])
        self.assertIsInstance(tags_example["arguments"]["tags"], list)

    def test_head_tail_examples_do_not_teach_both_directions_at_once(self) -> None:
        tool = _read_text_file_tool()
        base_skill = HeuristicBackend(ablation_mode="base_only").generate_skill(tool)

        self.assertEqual(set(base_skill.argument_template), {"path"})
        for example in base_skill.examples:
            self.assertFalse({"head", "tail"}.issubset(example["arguments"]))
        self.assertTrue(
            any("choose `head` or `tail`" in line for line in base_skill.when_not_to_use),
            msg=base_skill.when_not_to_use,
        )

        candidates = generate_skill_candidates(
            tool,
            base_skill,
            k=3,
            strategies=["concise_default", "boundary_heavy", "example_heavy"],
        )
        example_heavy = next(candidate["skill"] for candidate in candidates if candidate["generation_strategy"] == "example_heavy")
        self.assertEqual(set(example_heavy.argument_template), {"path"})
        for example in example_heavy.examples:
            self.assertFalse({"head", "tail"}.issubset(example["arguments"]))


if __name__ == "__main__":
    unittest.main()

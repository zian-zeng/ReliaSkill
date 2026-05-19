import unittest

from autoskill.ir import ArgumentIR, GeneratedSkill, ToolIR
from autoskill.exposure import render_exposure
from autoskill.prompting import build_prediction_prompt


class ReliaSkillV1PromptingTests(unittest.TestCase):
    def test_reliaskill_v1_uses_boundary_first_runtime_guidance(self) -> None:
        prompt = build_prediction_prompt(
            _tool(),
            GeneratedSkill(
                baseline_name="reliaskill_v1",
                skill_summary="Full ReliaSkill deployable artifact.",
                when_to_use=["Use only for direct search requests."],
                when_not_to_use=["Do not use for explanation-only requests."],
                argument_template={"query": "text"},
            ),
            "Explain search only; do not call anything.",
        )

        self.assertIn("ReliaSkill v1 boundary gate", prompt)
        self.assertIn("ReliaSkill v1 proof obligations", prompt)
        self.assertIn("ReliaSkill v1 contract counterexamples", prompt)
        self.assertIn("missing_required_information", prompt)
        self.assertIn("all_required_arguments_grounded", prompt)
        self.assertLess(prompt.index("When not to use:"), prompt.index("When to use:"))

    def test_reliaskill_v1_puts_schema_contract_before_boundaries(self) -> None:
        prompt = build_prediction_prompt(
            _array_tool(),
            GeneratedSkill(
                baseline_name="reliaskill_v1",
                skill_summary="Full ReliaSkill deployable artifact.",
                when_to_use=["Use for adding observations."],
                when_not_to_use=["Do not use for creating entities."],
                argument_template={"observations": [{"entityName": "sample-name", "contents": ["note"]}]},
            ),
            "Add note to Alice.",
        )

        self.assertIn("ReliaSkill v1 schema contract", prompt)
        self.assertIn("Allowed top-level fields", prompt)
        self.assertIn("Each `observations` item required keys", prompt)
        self.assertIn("`observations[].contents` must be a JSON array of string items", prompt)
        self.assertLess(prompt.index("ReliaSkill v1 schema contract"), prompt.index("ReliaSkill v1 boundary gate"))

    def test_boundary_first_prompt_condition_uses_boundary_first_runtime_contract(self) -> None:
        prompt = build_prediction_prompt(
            _tool(),
            GeneratedSkill(
                baseline_name="skill_prompt_boundary_first",
                skill_summary="Boundary-first ReliaSkill artifact.",
                when_to_use=["Use for direct search requests."],
                when_not_to_use=["Do not use for explanation-only requests."],
                argument_template={"query": "text"},
            ),
            "Search for notes.",
        )

        self.assertIn("ReliaSkill boundary-first schema contract", prompt)
        self.assertIn("ReliaSkill boundary-first boundary gate", prompt)
        self.assertLess(prompt.index("When not to use:"), prompt.index("When to use:"))

    def test_reliaskill_v1_uses_packaged_schema_contract_metadata(self) -> None:
        prompt = build_prediction_prompt(
            _tool(),
            GeneratedSkill(
                baseline_name="reliaskill_v1",
                skill_summary="Full ReliaSkill deployable artifact.",
                when_to_use=["Use for direct search requests."],
                when_not_to_use=["Do not use for explanation-only requests."],
                argument_template={"query": "text"},
                metadata={"schema_contract": ["Packaged contract survives load."]},
            ),
            "Search for notes.",
        )

        self.assertIn("Packaged contract survives load.", prompt)

    def test_reliaskill_v1_ablation_exposure_gets_contract_fallbacks(self) -> None:
        exposure = render_exposure(
            _tool(),
            GeneratedSkill(
                baseline_name="reliaskill_v1_no_runtime_grounding",
                skill_summary="Ablate runtime grounding from the full v1 artifact.",
                when_to_use=["Use for direct search requests."],
                when_not_to_use=["Do not use for explanation-only requests."],
                argument_template={"query": "text"},
            ),
        )

        self.assertIn("Schema contract:", exposure)
        self.assertIn("Executable contract:", exposure)
        self.assertIn("Contract counterexamples:", exposure)

    def test_regular_conditions_keep_standard_guidance_order(self) -> None:
        prompt = build_prediction_prompt(
            _tool(),
            GeneratedSkill(
                baseline_name="generated_skill_base",
                skill_summary="Generated search skill.",
                when_to_use=["Use for direct search requests."],
                when_not_to_use=["Do not use for explanation-only requests."],
                argument_template={"query": "text"},
            ),
            "Search for notes.",
        )

        self.assertNotIn("ReliaSkill v1 boundary gate", prompt)
        self.assertLess(prompt.index("When to use:"), prompt.index("When not to use:"))


def _tool() -> ToolIR:
    return ToolIR(
        tool_name="search",
        tool_purpose="Search documents.",
        arguments=[ArgumentIR(name="query", type="string", required=True)],
    )


def _array_tool() -> ToolIR:
    return ToolIR(
        tool_name="add_observations",
        tool_purpose="Add new observations to an entity.",
        arguments=[
            ArgumentIR(
                name="observations",
                type="array",
                required=True,
                items_type="object",
                items_schema={
                    "type": "object",
                    "properties": {
                        "entityName": {"type": "string"},
                        "contents": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["entityName", "contents"],
                },
            )
        ],
    )


if __name__ == "__main__":
    unittest.main()

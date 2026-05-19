import unittest

from autoskill.ir import ArgumentIR, GeneratedSkill, ToolIR
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
        self.assertLess(prompt.index("When not to use:"), prompt.index("When to use:"))

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


if __name__ == "__main__":
    unittest.main()

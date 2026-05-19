import unittest

from autoskill.contract_inference import build_contract_proof_state, contract_state_payload, proof_state_is_viable
from autoskill.ir import ArgumentIR, GeneratedSkill, ToolIR


def _skill(tool: ToolIR) -> GeneratedSkill:
    return GeneratedSkill(
        baseline_name="reliaskill_v1",
        skill_summary=tool.tool_purpose or "",
        when_to_use=[f"Use {tool.tool_name} for direct matching requests."],
        when_not_to_use=[],
        argument_template={argument.name: f"<{argument.name}>" for argument in tool.arguments if argument.required},
    )


class ContractInferenceTests(unittest.TestCase):
    def test_proof_state_prefers_viable_matching_tool(self) -> None:
        read_tool = ToolIR(
            tool_name="read_file",
            tool_purpose="Read file contents from a path.",
            arguments=[ArgumentIR(name="path", type="string", required=True, description="File path.")],
        )
        write_tool = ToolIR(
            tool_name="write_file",
            tool_purpose="Write file contents to a path.",
            arguments=[
                ArgumentIR(name="path", type="string", required=True, description="File path."),
                ArgumentIR(name="content", type="string", required=True, description="Text content."),
            ],
        )

        read_state = build_contract_proof_state(read_tool, _skill(read_tool), "Read docs/report.md.")
        write_state = build_contract_proof_state(write_tool, _skill(write_tool), "Read docs/report.md.")

        self.assertTrue(read_state.satisfied)
        self.assertTrue(proof_state_is_viable(read_state))
        self.assertEqual(read_state.decision, "call")
        self.assertIn("path", read_state.grounded_required_args)
        self.assertIn("content", write_state.missing_required_args)
        self.assertFalse(write_state.viable)
        self.assertEqual(write_state.decision, "abstain")
        self.assertGreater(read_state.proof_score, write_state.proof_score)
        self.assertIn("feature_vector", read_state.model_dump())
        self.assertEqual(read_state.proof_policy["name"], "dev_calibratable_contract_proof_policy")

        payload = contract_state_payload(read_state)
        self.assertEqual(payload["tool_name"], "read_file")
        self.assertTrue(payload["viable"])
        self.assertEqual(payload["decision"], "call")
        self.assertIn("proof_score", payload)
        self.assertIn("proof_obligations", read_state.model_dump())

    def test_metadata_contract_proof_policy_can_change_threshold(self) -> None:
        tool = ToolIR(
            tool_name="read_file",
            tool_purpose="Read file contents from a path.",
            arguments=[ArgumentIR(name="path", type="string", required=True, description="File path.")],
        )
        strict_skill = _skill(tool)
        strict_skill.metadata["contract_proof_policy"] = {
            "name": "strict_dev_calibrated_policy",
            "call_threshold": 1000.0,
            "repair_threshold": 500.0,
            "calibration_source": "unit_dev_controls",
        }

        state = build_contract_proof_state(tool, strict_skill, "Read docs/report.md.")

        self.assertEqual(state.proof_policy["name"], "strict_dev_calibrated_policy")
        self.assertEqual(state.decision, "abstain")
        self.assertFalse(proof_state_is_viable(state))


if __name__ == "__main__":
    unittest.main()

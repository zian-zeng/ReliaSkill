import unittest

from autoskill.eval_types import EvalTask
from autoskill.ir import ArgumentIR, GeneratedSkill, ToolIR
from autoskill.retrieval_runtime import retrieve_candidate_tools
from autoskill.routing_boundaries import detect_routing_abstention
from autoskill.routing_eval import score_routed_prediction, select_tool_for_task


def _bank_tools():
    balance = ToolIR(
        tool_name="bank_get_account_balance",
        tool_purpose="Retrieve the balance and currency of a mock bank account.",
        arguments=[ArgumentIR(name="account_id", type="string", required=True, description="Account identifier.")],
    )
    transfer = ToolIR(
        tool_name="bank_transfer_between_accounts",
        tool_purpose="Record a mock transfer between two bank accounts.",
        arguments=[
            ArgumentIR(name="source_account_id", type="string", required=True),
            ArgumentIR(name="destination_account_id", type="string", required=True),
            ArgumentIR(name="amount", type="number", required=True),
        ],
    )
    return {tool.tool_name: tool for tool in (balance, transfer)}


def _skill(tool: ToolIR) -> GeneratedSkill:
    return GeneratedSkill(
        baseline_name="generated_skill_base",
        skill_summary=tool.tool_purpose or "",
        when_to_use=[f"Use `{tool.tool_name}` only for direct requests matching its purpose."],
        when_not_to_use=["Do not call this tool when the request says it is a distractor."],
        argument_template={argument.name: f"<{argument.name}>" for argument in tool.arguments if argument.required},
    )


class RoutingBoundaryTests(unittest.TestCase):
    def test_distractor_name_is_penalized_but_requested_tool_is_boosted(self):
        tools = _bank_tools()
        query = (
            "Use bank get account balance to retrieve account acct-1; "
            "bank transfer between accounts is a distractor and should not be called."
        )

        candidates = retrieve_candidate_tools(query, tools, top_k=2)["candidates"]

        self.assertEqual(candidates[0]["tool_name"], "bank_get_account_balance")
        self.assertLess(
            next(row["score"] for row in candidates if row["tool_name"] == "bank_transfer_between_accounts"),
            candidates[0]["score"],
        )

    def test_generated_skill_routing_abstains_on_explanation_only(self):
        tools = _bank_tools()
        skills = {name: _skill(tool) for name, tool in tools.items()}
        task = EvalTask(
            task_id="explain_only",
            tool_name="bank_get_account_balance",
            user_request="Explain when someone should use bank get account balance; do not actually call it or perform the action.",
            should_trigger=False,
        )

        routing = select_tool_for_task(task, "generated_skill_base", tools, skills)

        self.assertEqual(routing["selected_tool_name"], "__abstain__")
        self.assertEqual(routing["routing_strategy"], "method_boundary_abstention")

    def test_positive_without_external_services_is_not_boundary_abstention(self):
        reason = detect_routing_abstention(
            "Use bank get account balance to retrieve acct-1 without contacting external services."
        )

        self.assertIsNone(reason)

    def test_negative_expected_alternate_tool_can_be_correct_route(self):
        task = EvalTask(
            task_id="similar_negative",
            tool_name="bank_transfer_between_accounts",
            user_request=(
                "Use bank get account balance to retrieve acct-1; "
                "bank transfer between accounts is a distractor and should not be called."
            ),
            expected_arguments={"account_id": "acct-1"},
            should_trigger=False,
            expected_tool_name="bank_get_account_balance",
            negative_target="bank_transfer_between_accounts",
            negative_category="similar_tool_should_be_used",
        )

        score = score_routed_prediction(
            task,
            selected_tool_name="bank_get_account_balance",
            candidate_tools=["bank_get_account_balance", "bank_transfer_between_accounts"],
            predictor_record={
                "baseline_name": "generated_skill_base",
                "predicted_arguments": {"account_id": "acct-1"},
                "argument_score": {
                    "exact_match": True,
                    "argument_validity": 1.0,
                    "required_argument_recall": 1.0,
                    "hallucinated_args": [],
                },
                "routing_strategy": "retrieve_then_semantic_rerank",
                "prediction_metadata": {},
            },
        )

        self.assertTrue(score["tool_selection_correct"])
        self.assertTrue(score["joint_exact_match"])
        self.assertFalse(score["harmful_injection"])
        self.assertTrue(score["triggered"])


if __name__ == "__main__":
    unittest.main()

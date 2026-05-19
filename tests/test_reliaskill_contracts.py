from __future__ import annotations

import unittest

from autoskill.contracts import (
    build_contract_counterexamples,
    build_contract_failure_report,
    calibrate_contract_policy,
    compose_contract_plan,
    compile_skill_contract,
    evaluate_skill_contract,
    interpret_execution_feedback,
)
from autoskill.eval_types import EvalTask
from autoskill.ir import ArgumentIR, GeneratedSkill, ToolIR
from autoskill.routing_eval import select_tool_for_task


class ReliaSkillContractTests(unittest.TestCase):
    def test_compiled_contract_records_proof_obligations_and_nested_required_paths(self) -> None:
        contract = compile_skill_contract(_transaction_search_tool(), _skill(_transaction_search_tool()))

        self.assertEqual(contract.tool_name, "bank_search_transactions")
        self.assertIn("all_required_arguments_grounded", contract.proof_obligations)
        self.assertIn("replace_invalid_required_with_grounded_value", contract.repair_policy)
        self.assertIn("date_range.start", contract.required_paths)
        self.assertIn("date_range.end", contract.required_paths)

    def test_contract_counterexamples_are_tied_to_obligations(self) -> None:
        tool = ToolIR(
            tool_name="document_create",
            tool_purpose="Create documents.",
            arguments=[ArgumentIR(name="title", type="string", required=True)],
            schema_complexity={"side_effect_type": "write"},
        )

        counterexamples = build_contract_counterexamples(tool, _skill(tool))

        self.assertTrue(any(item["violated_obligation"] == "all_required_arguments_grounded" for item in counterexamples))
        self.assertTrue(any(item["violated_obligation"] == "side_effect_allowed_by_request" for item in counterexamples))
        self.assertTrue(all(item["expected_behavior"].startswith("abstain") for item in counterexamples))

    def test_contract_evaluation_proves_grounded_nested_request(self) -> None:
        tool = _transaction_search_tool()
        evaluation = evaluate_skill_contract(
            tool,
            _skill(tool),
            'Search transactions for account_id="acct-1" from 2026-01-01 to 2026-01-31.',
            arguments={"account_id": "acct-1", "date_range": {"start": "2026-01-01", "end": "2026-01-31"}},
        )

        self.assertTrue(evaluation.satisfied)
        self.assertEqual(evaluation.missing_required_args, [])
        self.assertIn("account_id", evaluation.grounded_required_args)
        self.assertIn("date_range", evaluation.grounded_required_args)
        self.assertTrue(any(item["obligation"] == "arguments_schema_valid" for item in evaluation.proof_obligations))

    def test_contract_treats_record_nouns_and_spaced_identifiers_conservatively(self) -> None:
        tool = ToolIR(
            tool_name="account_search",
            tool_purpose="Search account records by account identifier.",
            arguments=[ArgumentIR(name="account_id", type="string", required=True)],
        )

        evaluation = evaluate_skill_contract(
            tool,
            _skill(tool),
            "Search account abc123.",
            arguments={"account_id": "abc123"},
        )

        self.assertTrue(evaluation.satisfied)
        self.assertNotIn("action_intent_conflict", evaluation.blocking_reasons)
        self.assertEqual(evaluation.argument_issues, [])
        self.assertIn("account_id", evaluation.grounded_required_args)

        missing = evaluate_skill_contract(tool, _skill(tool), "Search account records.", arguments={})
        self.assertFalse(missing.satisfied)
        self.assertIn("account_id", missing.missing_required_args)

    def test_contract_evaluation_blocks_missing_required_information(self) -> None:
        tool = ToolIR(
            tool_name="document_search",
            tool_purpose="Search documents.",
            arguments=[ArgumentIR(name="query", type="string", required=True)],
        )

        evaluation = evaluate_skill_contract(tool, _skill(tool), "Search after I send the query later.")

        self.assertFalse(evaluation.satisfied)
        self.assertEqual(evaluation.missing_required_args, ["query"])
        self.assertIn("missing_required_arguments", evaluation.blocking_reasons)
        report = build_contract_failure_report(evaluation)
        self.assertEqual(report["reason"], "missing_required_arguments")
        self.assertIn("query", report["clarification"])

    def test_contract_evaluation_blocks_side_effect_conflict(self) -> None:
        tool = ToolIR(
            tool_name="create_calendar_event",
            tool_purpose="Create calendar events.",
            arguments=[ArgumentIR(name="title", type="string", required=True)],
            schema_complexity={"side_effect_type": "write"},
        )

        evaluation = evaluate_skill_contract(tool, _skill(tool), 'Find title="standup", do not create anything.')

        self.assertFalse(evaluation.satisfied)
        self.assertIn("action_intent_conflict", evaluation.blocking_reasons)
        self.assertIn("create", evaluation.negated_actions)

    def test_contract_evaluation_can_ground_from_artifact_context(self) -> None:
        tool = ToolIR(
            tool_name="read_file",
            tool_purpose="Read file contents.",
            arguments=[ArgumentIR(name="path", type="string", required=True)],
        )

        evaluation = evaluate_skill_contract(
            tool,
            _skill(tool),
            "Read the saved report path.",
            grounding_context={"artifacts": {"last_report_path": "reports/q1.md"}},
        )

        self.assertTrue(evaluation.satisfied)
        self.assertEqual(evaluation.grounded_required_args, ["path"])
        self.assertIn("artifacts", evaluation.grounding_sources)

    def test_adaptive_contract_policy_can_reject_low_confidence_calls(self) -> None:
        tool = ToolIR(
            tool_name="document_search",
            tool_purpose="Search documents.",
            arguments=[ArgumentIR(name="query", type="string", required=True)],
        )
        skill = _skill(tool)
        skill.metadata["contract_policy"] = {
            "name": "high_confidence_policy",
            "mode": "strict_weighted",
            "bias": 0.0,
            "threshold": 2.0,
            "weights": {"grounded_required_fraction": 1.0},
        }

        evaluation = evaluate_skill_contract(tool, skill, 'Search query="budget".')

        self.assertFalse(evaluation.satisfied)
        self.assertEqual(evaluation.policy_decision["policy_name"], "high_confidence_policy")
        self.assertIn("adaptive_policy_reject", evaluation.blocking_reasons)

    def test_calibrate_contract_policy_returns_transparent_weighted_policy(self) -> None:
        policy = calibrate_contract_policy(
            [
                {"features": {"grounded_required_fraction": 1.0, "side_effect_risk": 0.0}, "label": True},
                {"features": {"grounded_required_fraction": 0.0, "side_effect_risk": 1.0}, "label": False},
            ]
        )

        self.assertEqual(policy["mode"], "strict_weighted")
        self.assertGreater(policy["weights"]["grounded_required_fraction"], 0)
        self.assertLess(policy["weights"]["side_effect_risk"], 0)
        self.assertEqual(policy["calibration_examples"], 2)

    def test_contract_plan_binds_dependent_required_arguments_to_prior_outputs(self) -> None:
        read_file = ToolIR(
            tool_name="read_file",
            tool_purpose="Read file content from a path.",
            output_hint="Returns text content.",
            arguments=[ArgumentIR(name="path", type="string", required=True)],
        )
        summarize = ToolIR(
            tool_name="summarize_text",
            tool_purpose="Summarize text content.",
            arguments=[ArgumentIR(name="content", type="string", required=True)],
        )
        tools = {tool.tool_name: tool for tool in (read_file, summarize)}
        skills = {name: _skill(tool) for name, tool in tools.items()}

        plan = compose_contract_plan("Read docs/report.md and summarize it.", tools, skills, max_steps=2)

        self.assertTrue(plan.satisfied)
        self.assertEqual([step.tool_name for step in plan.steps], ["read_file", "summarize_text"])
        self.assertEqual(plan.steps[1].input_bindings["content"]["from_step"], "step_1")

    def test_execution_feedback_interpreter_separates_repair_from_abort(self) -> None:
        tool = ToolIR(
            tool_name="email_send",
            tool_purpose="Send an email.",
            arguments=[ArgumentIR(name="recipient_email", type="string", required=True, format="email")],
        )
        evaluation = evaluate_skill_contract(tool, _skill(tool), "Send email to alice@example.com.")

        repair = interpret_execution_feedback(evaluation, {"error": "invalid format for recipient_email"})
        abort = interpret_execution_feedback(evaluation, {"error": "permission denied by auth provider"})

        self.assertEqual(repair["next_action"], "repair_and_retry")
        self.assertTrue(repair["retry_allowed"])
        self.assertEqual(abort["next_action"], "abort")
        self.assertFalse(abort["retry_allowed"])

    def test_v1_routing_exposes_contract_proof_on_candidates(self) -> None:
        search = ToolIR(
            tool_name="document_search",
            tool_purpose="Search documents.",
            arguments=[ArgumentIR(name="query", type="string", required=True)],
        )
        create = ToolIR(
            tool_name="document_create",
            tool_purpose="Create documents.",
            arguments=[
                ArgumentIR(name="title", type="string", required=True),
                ArgumentIR(name="content", type="string", required=True),
            ],
            schema_complexity={"side_effect_type": "write"},
        )
        tools = {tool.tool_name: tool for tool in (search, create)}
        skills = {name: _skill(tool) for name, tool in tools.items()}
        routing = select_tool_for_task(
            EvalTask(task_id="contract_route", tool_name="document_search", user_request='Search query="budget".'),
            "reliaskill_v1",
            tools,
            skills,
            top_k=2,
        )

        row = next(item for item in routing["candidate_rows"] if item["tool_name"] == "document_search")
        self.assertTrue(row["contract_satisfied"])
        self.assertEqual(row["contract_blocking_reasons"], [])
        self.assertTrue(row["contract_failure_report"]["satisfied"])
        self.assertTrue(any(item["obligation"] == "all_required_arguments_grounded" for item in row["contract_proof_obligations"]))


def _transaction_search_tool() -> ToolIR:
    return ToolIR(
        tool_name="bank_search_transactions",
        tool_purpose="Search transactions by account and date range.",
        arguments=[
            ArgumentIR(name="account_id", type="string", required=True),
            ArgumentIR(
                name="date_range",
                type="object",
                required=True,
                properties={"start": {"type": "string"}, "end": {"type": "string"}},
                required_properties=["start", "end"],
            ),
        ],
    )


def _skill(tool: ToolIR) -> GeneratedSkill:
    return GeneratedSkill(
        baseline_name="reliaskill_v1",
        skill_summary=tool.tool_purpose or "",
        when_to_use=[f"Use `{tool.tool_name}` only for matching requests."],
        when_not_to_use=["Do not use when required inputs are missing."],
        argument_template={arg.name: f"<{arg.name}>" for arg in tool.arguments if arg.required},
    )


if __name__ == "__main__":
    unittest.main()

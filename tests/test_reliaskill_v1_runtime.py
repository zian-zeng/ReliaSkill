from __future__ import annotations

import unittest

from autoskill.eval_types import EvalPrediction, EvalTask
from autoskill.ir import ArgumentIR, GeneratedSkill, ToolIR
from autoskill.predictor import PredictorBackend, safe_predict


class _StaticPredictor(PredictorBackend):
    backend_name = "static"

    def __init__(self, *, arguments: dict, should_call: bool = True) -> None:
        self.arguments = arguments
        self.should_call = should_call

    def predict(self, tool: ToolIR, skill: GeneratedSkill, task: EvalTask) -> EvalPrediction:
        return EvalPrediction(
            task_id=task.task_id,
            tool_name=tool.tool_name,
            baseline_name=skill.baseline_name,
            predicted_arguments=dict(self.arguments),
            should_call=self.should_call,
            metadata={"raw_model_output": "static"},
        )


class _RefiningPredictor(_StaticPredictor):
    def __init__(self, *, arguments: dict, refined_arguments: dict) -> None:
        super().__init__(arguments=arguments, should_call=True)
        self.refined_arguments = refined_arguments
        self.refine_calls = 0

    def refine_prediction(
        self,
        tool: ToolIR,
        skill: GeneratedSkill,
        task: EvalTask,
        previous_prediction: EvalPrediction,
    ) -> EvalPrediction | None:
        self.refine_calls += 1
        return EvalPrediction(
            task_id=task.task_id,
            tool_name=tool.tool_name,
            baseline_name=skill.baseline_name,
            predicted_arguments=dict(self.refined_arguments),
            should_call=True,
            metadata={"raw_model_output": "refined", "refinement_prompt_seen": True},
        )


class ReliaSkillV1RuntimeVerifierTests(unittest.TestCase):
    def test_v1_drops_unsupported_fields_after_model_prediction(self) -> None:
        prediction = safe_predict(
            _search_tool(),
            _v1_skill(),
            EvalTask(task_id="t1", tool_name="search", user_request='Search for query="release notes".'),
            _StaticPredictor(arguments={"query": "release notes", "unsupported": True}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"query": "release notes"})
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("dropped_unsupported_field:unsupported", verifier["actions"])

    def test_v1_fills_required_argument_only_when_grounded(self) -> None:
        prediction = safe_predict(
            _search_tool(),
            _v1_skill(),
            EvalTask(task_id="t2", tool_name="search", user_request='Please search query="schema contract".'),
            _StaticPredictor(arguments={}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"query": "schema contract"})
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("filled_grounded_required:query", verifier["actions"])
        self.assertIn("compiled_contract", verifier)
        self.assertEqual(verifier["contract_proof_state_after"]["decision"], "call")
        self.assertIn("feature_vector", verifier["contract_proof_state_after"])
        self.assertIn("decision_confidence", verifier["contract_proof_state_after"])
        self.assertIn("evidence_ledger", verifier["contract_proof_state_after"])
        self.assertTrue(verifier["contract_proof_state_after"]["evidence_ledger"]["positive_evidence"])
        self.assertEqual(
            verifier["contract_proof_state_after"]["proof_policy"]["name"],
            "dev_calibratable_contract_proof_policy",
        )
        self.assertTrue(verifier["contract_evaluation_after"]["satisfied"])
        self.assertTrue(verifier["contract_failure_report_after"]["satisfied"])
        self.assertTrue(
            any(
                item["obligation"] == "all_required_arguments_grounded"
                and item["status"] == "satisfied"
                for item in verifier["contract_evaluation_after"]["proof_obligations"]
            )
        )

    def test_v1_runtime_grounding_ablation_does_not_fill_missing_required_argument(self) -> None:
        prediction = safe_predict(
            _search_tool(),
            _v1_skill(
                baseline_name="reliaskill_v1_no_runtime_grounding",
                flags={"disable_runtime_grounding": True},
            ),
            EvalTask(task_id="t2_ablate_grounding", tool_name="search", user_request='Please search query="schema contract".'),
            _StaticPredictor(arguments={}),
        )

        self.assertFalse(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {})
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertNotIn("filled_grounded_required:query", verifier["actions"])

    def test_v1_rescues_false_abstention_when_required_arguments_are_grounded(self) -> None:
        prediction = safe_predict(
            _search_tool(),
            _v1_skill(),
            EvalTask(task_id="t2_rescue", tool_name="search", user_request='Search query="schema contract".'),
            _StaticPredictor(arguments={}, should_call=False),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"query": "schema contract"})
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("rescued_grounded_false_abstention", verifier["actions"])

    def test_v1_rescues_false_abstention_with_artifact_grounding_context(self) -> None:
        prediction = safe_predict(
            _read_tool(),
            _v1_skill(),
            EvalTask(
                task_id="t2_rescue_context",
                tool_name="read_file",
                user_request="Read the report path.",
                artifact_context={"last_report_path": "docs/report.md"},
            ),
            _StaticPredictor(arguments={}, should_call=False),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"path": "docs/report.md"})
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("artifacts", verifier["contract_evaluation_after"]["grounding_sources"])

    def test_v1_replaces_hallucinated_required_value_with_grounded_value(self) -> None:
        prediction = safe_predict(
            _search_tool(),
            _v1_skill(),
            EvalTask(task_id="t2_replace", tool_name="search", user_request='Search query="release notes".'),
            _StaticPredictor(arguments={"query": "made up"}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"query": "release notes"})
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("replaced_ungrounded_required:query", verifier["actions"])

    def test_v1_refines_unproved_call_with_contract_feedback(self) -> None:
        backend = _RefiningPredictor(arguments={}, refined_arguments={"ticket_id": "TCK-123"})

        prediction = safe_predict(
            _ticket_search_tool(),
            _v1_skill(),
            EvalTask(task_id="t2_refine", tool_name="ticket_search", user_request="Search support ticket TCK-123."),
            backend,
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"ticket_id": "TCK-123"})
        self.assertEqual(backend.refine_calls, 1)
        refinement = prediction.metadata["reliaskill_v1_refinement"]
        self.assertTrue(refinement["attempted"])
        self.assertTrue(refinement["selected_refined"])
        self.assertGreater(refinement["refined_score"], refinement["original_score"])

    def test_v1_fills_grounded_generic_identifier_without_refinement(self) -> None:
        prediction = safe_predict(
            _account_search_tool(),
            _v1_skill(),
            EvalTask(task_id="t2_identifier", tool_name="account_search", user_request="Search account abc123."),
            _StaticPredictor(arguments={}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"account_id": "abc123"})
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("filled_grounded_required:account_id", verifier["actions"])

    def test_identifier_binding_ablation_does_not_fill_generic_identifier(self) -> None:
        prediction = safe_predict(
            _account_search_tool(),
            _v1_skill(
                baseline_name="reliaskill_v1_no_identifier_binding",
                flags={"disable_identifier_binding": True},
            ),
            EvalTask(task_id="t2_identifier_ablate", tool_name="account_search", user_request="Search account abc123."),
            _StaticPredictor(arguments={}),
        )

        self.assertFalse(prediction.should_call)
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("account_id:missing_required", verifier["issues"])

    def test_verifier_refinement_ablation_skips_second_pass(self) -> None:
        backend = _RefiningPredictor(arguments={}, refined_arguments={"ticket_id": "TCK-123"})

        prediction = safe_predict(
            _ticket_search_tool(),
            _v1_skill(
                baseline_name="reliaskill_v1_no_verifier_refinement",
                flags={"disable_verifier_refinement": True},
            ),
            EvalTask(task_id="t2_refine_ablate", tool_name="ticket_search", user_request="Search support ticket TCK-123."),
            backend,
        )

        self.assertFalse(prediction.should_call)
        self.assertEqual(backend.refine_calls, 0)
        self.assertNotIn("reliaskill_v1_refinement", prediction.metadata)

    def test_v1_does_not_invent_missing_query_from_generic_request(self) -> None:
        prediction = safe_predict(
            _search_tool(),
            _v1_skill(),
            EvalTask(task_id="t2b", tool_name="search", user_request="I will send the query later."),
            _StaticPredictor(arguments={}),
        )

        self.assertFalse(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {})
        self.assertEqual(prediction.abstention_reason, "missing_required_information")

    def test_v1_rejects_hallucinated_required_value_when_no_grounded_value_exists(self) -> None:
        prediction = safe_predict(
            _search_tool(),
            _v1_skill(),
            EvalTask(task_id="t2_missing_replace", tool_name="search", user_request="Search after I send the query."),
            _StaticPredictor(arguments={"query": "release notes"}),
        )

        self.assertFalse(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {})
        self.assertEqual(prediction.abstention_reason, "missing_required_information")

    def test_v1_coerces_safe_scalar_types_and_canonicalizes_enum_case(self) -> None:
        prediction = safe_predict(
            _typed_tool(),
            _v1_skill(),
            EvalTask(task_id="t2c", tool_name="rank_search", user_request='Rank search query="release notes" limit=5 mode=fast.'),
            _StaticPredictor(arguments={"query": 123, "limit": "5", "mode": "FAST"}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"query": "release notes", "limit": 5, "mode": "fast"})
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("replaced_ungrounded_required:query", verifier["actions"])
        self.assertIn("coerced_integer:limit", verifier["actions"])
        self.assertIn("canonicalized_enum:mode", verifier["actions"])

    def test_v1_abstains_on_invalid_enum(self) -> None:
        prediction = safe_predict(
            _typed_tool(),
            _v1_skill(),
            EvalTask(task_id="t2d", tool_name="rank_search", user_request='Rank search query="release notes" limit=5.'),
            _StaticPredictor(arguments={"query": "release notes", "limit": 5, "mode": "turbo"}),
        )

        self.assertFalse(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {})
        self.assertIn("mode:invalid_enum", prediction.abstention_reason or "")

    def test_v1_replaces_invalid_required_format_with_grounded_value(self) -> None:
        prediction = safe_predict(
            _email_tool(),
            _v1_skill(),
            EvalTask(task_id="t2d_email", tool_name="email_send", user_request="Send the email to alice@example.com."),
            _StaticPredictor(arguments={"recipient_email": "not-an-email"}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"recipient_email": "alice@example.com"})
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("replaced_invalid_required:recipient_email", verifier["actions"])

    def test_v1_rejects_invalid_required_format_without_grounded_repair(self) -> None:
        prediction = safe_predict(
            _email_tool(),
            _v1_skill(),
            EvalTask(task_id="t2d_email_bad", tool_name="email_send", user_request="Send the email to the recipient."),
            _StaticPredictor(arguments={"recipient_email": "not-an-email"}),
        )

        self.assertFalse(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {})
        self.assertIn("recipient_email:invalid_format", prediction.abstention_reason or "")

    def test_v1_verifies_nested_array_contracts(self) -> None:
        prediction = safe_predict(
            _observation_tool(),
            _v1_skill(),
            EvalTask(task_id="t2e", tool_name="add_observations", user_request="Add note to Alice."),
            _StaticPredictor(
                arguments={
                    "observations": [
                        {"entityName": "Alice", "contents": ["note"], "invented": "drop me"},
                    ]
                }
            ),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"observations": [{"entityName": "Alice", "contents": ["note"]}]})
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("dropped_unsupported_field:observations[0].invented", verifier["actions"])

    def test_v1_drops_ungrounded_optional_top_level_arguments(self) -> None:
        prediction = safe_predict(
            _search_with_optional_tool(),
            _v1_skill(),
            EvalTask(task_id="t2f", tool_name="search", user_request='Search for query="release notes".'),
            _StaticPredictor(arguments={"query": "release notes", "limit": 50}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"query": "release notes"})
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("dropped_ungrounded_optional:limit", verifier["actions"])

    def test_v1_keeps_grounded_optional_top_level_arguments(self) -> None:
        prediction = safe_predict(
            _search_with_optional_tool(),
            _v1_skill(),
            EvalTask(task_id="t2g", tool_name="search", user_request='Search for query="release notes" with limit=5.'),
            _StaticPredictor(arguments={"query": "release notes", "limit": "5"}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"query": "release notes", "limit": 5})

    def test_v1_contract_decoder_fills_missing_grounded_optional_arguments(self) -> None:
        prediction = safe_predict(
            _search_with_optional_tool(),
            _v1_skill(),
            EvalTask(task_id="t2g_optional_fill", tool_name="search", user_request='Search for query="release notes" with limit=5.'),
            _StaticPredictor(arguments={"query": "release notes"}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"query": "release notes", "limit": 5})
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("filled_grounded_optional:limit", verifier["actions"])

    def test_contract_decoder_ablation_does_not_fill_missing_optional_arguments(self) -> None:
        prediction = safe_predict(
            _search_with_optional_tool(),
            _v1_skill(
                baseline_name="reliaskill_v1_no_contract_decoder",
                flags={"disable_contract_decoder": True},
            ),
            EvalTask(task_id="t2g_optional_ablate", tool_name="search", user_request='Search for query="release notes" with limit=5.'),
            _StaticPredictor(arguments={"query": "release notes"}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"query": "release notes"})
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertNotIn("filled_grounded_optional:limit", verifier["actions"])

    def test_v1_drops_ungrounded_nondefault_optional_even_when_schema_has_default(self) -> None:
        prediction = safe_predict(
            _search_with_default_optional_tool(),
            _v1_skill(),
            EvalTask(task_id="t2g2", tool_name="search", user_request='Search for query="release notes".'),
            _StaticPredictor(arguments={"query": "release notes", "limit": 50}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"query": "release notes"})

    def test_v1_drops_ungrounded_default_optional_even_when_model_emits_schema_default(self) -> None:
        prediction = safe_predict(
            _search_with_default_optional_tool(),
            _v1_skill(),
            EvalTask(task_id="t2g3", tool_name="search", user_request='Search for query="release notes".'),
            _StaticPredictor(arguments={"query": "release notes", "limit": 10}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"query": "release notes"})
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("dropped_ungrounded_optional:limit", verifier["actions"])

    def test_v1_drops_ungrounded_optional_nested_properties(self) -> None:
        prediction = safe_predict(
            _observation_tool_with_optional_source(),
            _v1_skill(),
            EvalTask(task_id="t2h", tool_name="add_observations", user_request="Add note to Alice."),
            _StaticPredictor(arguments={"observations": [{"entityName": "Alice", "contents": ["note"], "source": "hallucinated"}]}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"observations": [{"entityName": "Alice", "contents": ["note"]}]})
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("dropped_ungrounded_optional:observations[0].source", verifier["actions"])

    def test_v1_contract_decoder_fills_grounded_nested_optional_properties(self) -> None:
        prediction = safe_predict(
            _observation_tool_with_optional_source(),
            _v1_skill(),
            EvalTask(
                task_id="t2h_fill_nested_optional",
                tool_name="add_observations",
                user_request='Add observation entityName="Alice" contents=["note"] source="meeting".',
            ),
            _StaticPredictor(arguments={"observations": [{"entityName": "Alice", "contents": ["note"]}]}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(
            prediction.predicted_arguments,
            {"observations": [{"entityName": "Alice", "contents": ["note"], "source": "meeting"}]},
        )
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("filled_grounded_optional:observations[0].source", verifier["actions"])

    def test_v1_contract_decoder_fills_grounded_boolean_optional_argument(self) -> None:
        prediction = safe_predict(
            _search_with_boolean_optional_tool(),
            _v1_skill(),
            EvalTask(task_id="t2h_bool_optional", tool_name="search", user_request='Search query="weather" and include forecast.'),
            _StaticPredictor(arguments={"query": "weather"}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"query": "weather", "include_forecast": True})
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("filled_grounded_optional:include_forecast", verifier["actions"])

    def test_v1_lifts_flat_fields_into_required_nested_object(self) -> None:
        prediction = safe_predict(
            _transaction_search_tool(),
            _v1_skill(),
            EvalTask(
                task_id="t2i",
                tool_name="bank_search_transactions",
                user_request='Search transactions account_id="acct-1" start="2026-01-01" end="2026-01-31".',
            ),
            _StaticPredictor(arguments={"account_id": "acct-1", "start": "2026-01-01", "end": "2026-01-31"}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(
            prediction.predicted_arguments,
            {"account_id": "acct-1", "date_range": {"start": "2026-01-01", "end": "2026-01-31"}},
        )
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("lifted_nested_field:start->date_range.start", verifier["actions"])
        self.assertIn("lifted_nested_field:end->date_range.end", verifier["actions"])

    def test_v1_fills_grounded_required_nested_object(self) -> None:
        prediction = safe_predict(
            _transaction_search_tool(),
            _v1_skill(),
            EvalTask(
                task_id="t2i_fill_nested",
                tool_name="bank_search_transactions",
                user_request='Search transactions account_id="acct-1" from 2026-01-01 to 2026-01-31.',
            ),
            _StaticPredictor(arguments={}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(
            prediction.predicted_arguments,
            {"account_id": "acct-1", "date_range": {"start": "2026-01-01", "end": "2026-01-31"}},
        )
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("filled_grounded_required:date_range", verifier["actions"])

    def test_v1_lifts_dotted_fields_into_required_nested_object(self) -> None:
        prediction = safe_predict(
            _transaction_search_tool(),
            _v1_skill(),
            EvalTask(
                task_id="t2j",
                tool_name="bank_search_transactions",
                user_request='Search transactions account_id="acct-1" date_range.start="2026-01-01" date_range.end="2026-01-31".',
            ),
            _StaticPredictor(
                arguments={
                    "account_id": "acct-1",
                    "date_range.start": "2026-01-01",
                    "date_range.end": "2026-01-31",
                }
            ),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(
            prediction.predicted_arguments,
            {"account_id": "acct-1", "date_range": {"start": "2026-01-01", "end": "2026-01-31"}},
        )

    def test_v1_replaces_invalid_nested_container_when_flat_fields_are_grounded(self) -> None:
        prediction = safe_predict(
            _transaction_search_tool(),
            _v1_skill(),
            EvalTask(
                task_id="t2j_invalid_container",
                tool_name="bank_search_transactions",
                user_request='Search transactions account_id="acct-1" start="2026-01-01" end="2026-01-31".',
            ),
            _StaticPredictor(
                arguments={
                    "account_id": "acct-1",
                    "date_range": "January",
                    "start": "2026-01-01",
                    "end": "2026-01-31",
                }
            ),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(
            prediction.predicted_arguments,
            {"account_id": "acct-1", "date_range": {"start": "2026-01-01", "end": "2026-01-31"}},
        )
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("replaced_invalid_nested_container:date_range", verifier["actions"])

    def test_v1_lifts_flat_fields_into_required_array_object_item(self) -> None:
        prediction = safe_predict(
            _observation_tool(),
            _v1_skill(),
            EvalTask(
                task_id="t2k",
                tool_name="add_observations",
                user_request='Add observation entityName="Alice" contents=["note"].',
            ),
            _StaticPredictor(arguments={"entityName": "Alice", "contents": ["note"]}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"observations": [{"entityName": "Alice", "contents": ["note"]}]})
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("lifted_nested_array_item_field:entityName->observations[0].entityName", verifier["actions"])
        self.assertIn("lifted_nested_array_item_field:contents->observations[0].contents", verifier["actions"])

    def test_v1_fills_grounded_required_array_object_item(self) -> None:
        prediction = safe_predict(
            _observation_tool(),
            _v1_skill(),
            EvalTask(
                task_id="t2k_fill_array",
                tool_name="add_observations",
                user_request='Add observation entityName="Alice" contents=["note"].',
            ),
            _StaticPredictor(arguments={}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"observations": [{"entityName": "Alice", "contents": ["note"]}]})
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("filled_grounded_required:observations", verifier["actions"])

    def test_v1_replaces_invalid_array_container_when_flat_item_fields_are_grounded(self) -> None:
        prediction = safe_predict(
            _observation_tool(),
            _v1_skill(),
            EvalTask(
                task_id="t2k_invalid_container",
                tool_name="add_observations",
                user_request='Add observation entityName="Alice" contents=["note"].',
            ),
            _StaticPredictor(arguments={"observations": "Alice note", "entityName": "Alice", "contents": ["note"]}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"observations": [{"entityName": "Alice", "contents": ["note"]}]})
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("replaced_invalid_nested_array_container:observations", verifier["actions"])

    def test_v1_abstains_when_required_argument_is_missing(self) -> None:
        prediction = safe_predict(
            _read_tool(),
            _v1_skill(),
            EvalTask(task_id="t3", tool_name="read_file", user_request="Read that later when I send the path."),
            _StaticPredictor(arguments={}),
        )

        self.assertFalse(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {})
        self.assertEqual(prediction.abstention_reason, "missing_required_information")

    def test_v1_abstains_when_request_forbids_target_tool(self) -> None:
        prediction = safe_predict(
            _read_tool(),
            _v1_skill(),
            EvalTask(
                task_id="t4",
                tool_name="read_file",
                user_request="Use list directory instead; read file is a distractor and should not be called.",
            ),
            _StaticPredictor(arguments={"path": "docs/report.md"}),
        )

        self.assertFalse(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {})
        self.assertEqual(prediction.abstention_reason, "explicit_target_tool_forbidden")

    def test_v1_abstains_on_action_intent_conflict_even_with_valid_arguments(self) -> None:
        prediction = safe_predict(
            _create_event_tool(),
            _v1_skill(),
            EvalTask(
                task_id="t5_action_conflict",
                tool_name="calendar_create_event",
                user_request='Search title="standup"; do not create anything.',
            ),
            _StaticPredictor(arguments={"title": "standup"}),
        )

        self.assertFalse(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {})
        self.assertEqual(prediction.abstention_reason, "action_intent_conflict")


def _search_tool() -> ToolIR:
    return ToolIR(
        tool_name="search",
        tool_purpose="Search documents.",
        arguments=[ArgumentIR(name="query", type="string", required=True)],
    )


def _account_search_tool() -> ToolIR:
    return ToolIR(
        tool_name="account_search",
        tool_purpose="Search account records by account identifier.",
        arguments=[ArgumentIR(name="account_id", type="string", required=True)],
    )


def _ticket_search_tool() -> ToolIR:
    return ToolIR(
        tool_name="ticket_search",
        tool_purpose="Search support tickets by ticket identifier.",
        arguments=[ArgumentIR(name="ticket_id", type="string", required=True)],
    )


def _search_with_optional_tool() -> ToolIR:
    return ToolIR(
        tool_name="search",
        tool_purpose="Search documents.",
        arguments=[
            ArgumentIR(name="query", type="string", required=True),
            ArgumentIR(name="limit", type="integer", required=False),
        ],
    )


def _search_with_default_optional_tool() -> ToolIR:
    return ToolIR(
        tool_name="search",
        tool_purpose="Search documents.",
        arguments=[
            ArgumentIR(name="query", type="string", required=True),
            ArgumentIR(name="limit", type="integer", required=False, default=10),
        ],
    )


def _search_with_boolean_optional_tool() -> ToolIR:
    return ToolIR(
        tool_name="search",
        tool_purpose="Search documents.",
        arguments=[
            ArgumentIR(name="query", type="string", required=True),
            ArgumentIR(name="include_forecast", type="boolean", required=False),
        ],
    )


def _read_tool() -> ToolIR:
    return ToolIR(
        tool_name="read_file",
        tool_purpose="Read a file from a known path.",
        arguments=[ArgumentIR(name="path", type="string", required=True)],
    )


def _typed_tool() -> ToolIR:
    return ToolIR(
        tool_name="rank_search",
        tool_purpose="Search documents with a ranking mode.",
        arguments=[
            ArgumentIR(name="query", type="string", required=True),
            ArgumentIR(name="limit", type="integer", required=True),
            ArgumentIR(name="mode", type="string", required=True, enum=["fast", "slow"]),
        ],
    )


def _email_tool() -> ToolIR:
    return ToolIR(
        tool_name="email_send",
        tool_purpose="Send an email.",
        arguments=[ArgumentIR(name="recipient_email", type="string", required=True, format="email")],
    )


def _observation_tool() -> ToolIR:
    return ToolIR(
        tool_name="add_observations",
        tool_purpose="Add observations to an entity.",
        arguments=[
            ArgumentIR(
                name="observations",
                type="array",
                required=True,
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


def _observation_tool_with_optional_source() -> ToolIR:
    return ToolIR(
        tool_name="add_observations",
        tool_purpose="Add observations to an entity.",
        arguments=[
            ArgumentIR(
                name="observations",
                type="array",
                required=True,
                items_schema={
                    "type": "object",
                    "properties": {
                        "entityName": {"type": "string"},
                        "contents": {"type": "array", "items": {"type": "string"}},
                        "source": {"type": "string"},
                    },
                    "required": ["entityName", "contents"],
                },
            )
        ],
    )


def _transaction_search_tool() -> ToolIR:
    return ToolIR(
        tool_name="bank_search_transactions",
        tool_purpose="Search bank transactions by account and date range.",
        arguments=[
            ArgumentIR(name="account_id", type="string", required=True),
            ArgumentIR(
                name="date_range",
                type="object",
                required=True,
                properties={
                    "start": {"type": "string"},
                    "end": {"type": "string"},
                },
                required_properties=["start", "end"],
            ),
        ],
    )


def _create_event_tool() -> ToolIR:
    return ToolIR(
        tool_name="calendar_create_event",
        tool_purpose="Create a calendar event.",
        arguments=[ArgumentIR(name="title", type="string", required=True)],
        schema_complexity={"side_effect_type": "write"},
    )


def _v1_skill(*, baseline_name: str = "reliaskill_v1", flags: dict | None = None) -> GeneratedSkill:
    return GeneratedSkill(
        baseline_name=baseline_name,
        skill_summary="Runtime-verified ReliaSkill artifact.",
        when_to_use=["Use only for direct, schema-grounded requests."],
        when_not_to_use=["Do not use when required fields are missing or when the target tool is forbidden."],
        metadata={"contract_ablation_flags": flags or {}},
    )


if __name__ == "__main__":
    unittest.main()

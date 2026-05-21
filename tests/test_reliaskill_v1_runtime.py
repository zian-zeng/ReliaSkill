from __future__ import annotations

import unittest
import os
from unittest.mock import patch

import autoskill.predictor as predictor_module
from autoskill.eval_types import EvalPrediction, EvalTask
from autoskill.ir import ArgumentIR, GeneratedSkill, ToolIR
from autoskill.predictor import PredictorBackend, safe_predict


class _StaticPredictor(PredictorBackend):
    backend_name = "static"

    def __init__(self, *, arguments: dict, should_call: bool = True) -> None:
        self.arguments = arguments
        self.should_call = should_call
        self.predict_calls = 0

    def predict(self, tool: ToolIR, skill: GeneratedSkill, task: EvalTask) -> EvalPrediction:
        self.predict_calls += 1
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


class _LocalHFRefiningPredictor(_RefiningPredictor):
    backend_name = "local_hf"


class _LocalHFStaticPredictor(_StaticPredictor):
    backend_name = "local_hf"


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
        backend = _LocalHFStaticPredictor(arguments={})
        prediction = safe_predict(
            _search_tool(),
            _v1_skill(),
            EvalTask(task_id="t2", tool_name="search", user_request='Please search query="schema contract".'),
            backend,
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"query": "schema contract"})
        self.assertEqual(backend.predict_calls, 0)
        self.assertEqual(prediction.metadata["reliaskill_v1_predecoder"]["decision"], "pre_call_contract_decoder")
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("predecoded_grounded_contract_call", verifier["actions"])
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
        backend = _LocalHFStaticPredictor(arguments={}, should_call=False)
        prediction = safe_predict(
            _search_tool(),
            _v1_skill(),
            EvalTask(task_id="t2_rescue", tool_name="search", user_request='Search query="schema contract".'),
            backend,
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"query": "schema contract"})
        self.assertEqual(backend.predict_calls, 0)
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("predecoded_grounded_contract_call", verifier["actions"])

    def test_v1_does_not_abstain_when_without_using_mentions_unrelated_distractor(self) -> None:
        prediction = safe_predict(
            _search_tool(),
            _v1_skill(),
            EvalTask(
                task_id="t2_unrelated_without_using",
                tool_name="search",
                user_request='Search query="schema contract" without using bank get account balance.',
            ),
            _StaticPredictor(arguments={}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"query": "schema contract"})

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
            EvalTask(task_id="t2_refine", tool_name="ticket_search", user_request="Search support TCK-123."),
            backend,
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"ticket_id": "TCK-123"})
        self.assertEqual(backend.refine_calls, 1)
        refinement = prediction.metadata["reliaskill_v1_refinement"]
        self.assertTrue(refinement["attempted"])
        self.assertTrue(refinement["selected_refined"])
        self.assertGreater(refinement["refined_score"], refinement["original_score"])

    def test_v1_fills_named_ticket_identifier_without_refinement(self) -> None:
        backend = _RefiningPredictor(arguments={}, refined_arguments={"ticket_id": "TCK-123"})

        prediction = safe_predict(
            _ticket_search_tool(),
            _v1_skill(),
            EvalTask(task_id="t2_ticket_identifier", tool_name="ticket_search", user_request="Search support ticket TCK-123."),
            backend,
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"ticket_id": "TCK-123"})
        self.assertEqual(backend.refine_calls, 0)
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("filled_grounded_required:ticket_id", verifier["actions"])

    def test_v1_skips_local_hf_model_refinement_by_default(self) -> None:
        backend = _LocalHFRefiningPredictor(arguments={}, refined_arguments={"ticket_id": "TCK-123"})

        prediction = safe_predict(
            _ticket_search_tool(),
            _v1_skill(),
            EvalTask(task_id="t2_refine_budget", tool_name="ticket_search", user_request="Search support TCK-123."),
            backend,
        )

        self.assertFalse(prediction.should_call)
        self.assertEqual(backend.refine_calls, 0)
        refinement = prediction.metadata["reliaskill_v1_refinement"]
        self.assertFalse(refinement["attempted"])
        self.assertEqual(refinement["reason"], "skipped_local_hf_runtime_budget")

    def test_v1_allows_budgeted_local_hf_refinement_for_high_value_failures(self) -> None:
        backend = _LocalHFRefiningPredictor(arguments={}, refined_arguments={"ticket_id": "TCK-123"})
        predictor_module._LOCAL_HF_REFINEMENT_USED = 0

        with patch.dict(os.environ, {"RELIASKILL_LOCAL_HF_REFINEMENT_BUDGET": "1"}):
            prediction = safe_predict(
                _ticket_search_tool(),
                _v1_skill(),
                EvalTask(task_id="t2_refine_budget_allowed", tool_name="ticket_search", user_request="Search support TCK-123."),
                backend,
            )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"ticket_id": "TCK-123"})
        self.assertEqual(backend.refine_calls, 1)
        refinement = prediction.metadata["reliaskill_v1_refinement"]
        self.assertTrue(refinement["attempted"])
        self.assertTrue(refinement["selected_refined"])

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

    def test_v1_uses_dev_learned_slot_alias_for_required_argument(self) -> None:
        skill = _v1_skill()
        skill.metadata["dev_learned_slot_grounding"] = {
            "arguments": {
                "assignee_id": {
                    "aliases": ["owner"],
                    "examples": 1,
                    "value_kinds": ["str"],
                    "sources": ["dev_positive"],
                }
            }
        }

        prediction = safe_predict(
            _assignment_tool(),
            skill,
            EvalTask(task_id="t2_slot_alias", tool_name="assign_ticket", user_request="Assign the ticket to owner zed-42."),
            _StaticPredictor(arguments={}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"assignee_id": "zed-42"})
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("filled_grounded_required:assignee_id", verifier["actions"])

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
            EvalTask(task_id="t2_refine_ablate", tool_name="ticket_search", user_request="Search support TCK-123."),
            backend,
        )

        self.assertFalse(prediction.should_call)
        self.assertEqual(backend.refine_calls, 0)
        self.assertNotIn("reliaskill_v1_refinement", prediction.metadata)

    def test_v1_does_not_invent_missing_query_from_generic_request(self) -> None:
        backend = _LocalHFStaticPredictor(arguments={})
        prediction = safe_predict(
            _search_tool(),
            _v1_skill(),
            EvalTask(task_id="t2b", tool_name="search", user_request="I will send the query later."),
            backend,
        )

        self.assertFalse(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {})
        self.assertEqual(prediction.abstention_reason, "missing_required_information")
        self.assertEqual(backend.predict_calls, 0)
        self.assertEqual(prediction.metadata["reliaskill_v1_predecoder"]["decision"], "pre_abstain_boundary")

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

    def test_v1_fills_grounded_scalar_array_argument(self) -> None:
        prediction = safe_predict(
            _array_sort_tool(),
            _v1_skill(),
            EvalTask(task_id="t2_array_scalar", tool_name="array_sort", user_request="Sort list=[3, 1, 2] order=ascending."),
            _StaticPredictor(arguments={}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"list": [3.0, 1.0, 2.0], "order": "ascending"})
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("filled_grounded_required:list", verifier["actions"])

    def test_v1_fills_comma_separated_scalar_array_argument(self) -> None:
        prediction = safe_predict(
            _array_sort_tool(),
            _v1_skill(),
            EvalTask(task_id="t2_array_scalar_commas", tool_name="array_sort", user_request="Sort list=3, 1, 2, order=descending."),
            _StaticPredictor(arguments={}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"list": [3.0, 1.0, 2.0], "order": "descending"})

    def test_v1_fills_directional_city_arguments(self) -> None:
        prediction = safe_predict(
            _city_route_tool(),
            _v1_skill(),
            EvalTask(task_id="t2_city_pair", tool_name="city_distance.find_shortest", user_request="Find the route from Paris to Berlin."),
            _StaticPredictor(arguments={}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"start_city": "Paris", "end_city": "Berlin"})

    def test_v1_fills_sequence_and_reference_arguments(self) -> None:
        prediction = safe_predict(
            _dna_tool(),
            _v1_skill(),
            EvalTask(
                task_id="t2_sequence_pair",
                tool_name="analyze_dna_sequence",
                user_request="Analyze sequence ATCGAA against reference ATCGTA.",
            ),
            _StaticPredictor(arguments={}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"sequence": "ATCGAA", "reference_sequence": "ATCGTA"})

    def test_v1_does_not_bind_every_numeric_required_arg_to_first_number(self) -> None:
        prediction = safe_predict(
            _quadratic_tool(),
            _v1_skill(),
            EvalTask(task_id="t2_numeric_guard", tool_name="algebra.quadratic_roots", user_request="Solve the quadratic with coefficient 7 only."),
            _StaticPredictor(arguments={}),
        )

        self.assertFalse(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {})

    def test_v1_binds_positional_coefficients_when_the_request_says_coefficients(self) -> None:
        prediction = safe_predict(
            _quadratic_tool(),
            _v1_skill(),
            EvalTask(task_id="t2_numeric_positional", tool_name="algebra.quadratic_roots", user_request="Solve quadratic coefficients 1, -3, 2."),
            _StaticPredictor(arguments={}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"a": 1.0, "b": -3.0, "c": 2.0})

    def test_v1_prefers_later_explicit_argument_over_formula_text(self) -> None:
        prediction = safe_predict(
            _quadratic_tool(),
            _v1_skill(),
            EvalTask(
                task_id="t2_numeric_formula_then_apply",
                tool_name="algebra.quadratic_roots",
                user_request="Find roots of ax^2 + bx + c = 0. Use a=9, b=9, c=9.",
            ),
            _StaticPredictor(arguments={}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"a": 9.0, "b": 9.0, "c": 9.0})

    def test_v1_preserves_explicit_free_form_object_argument(self) -> None:
        prediction = safe_predict(
            _free_form_object_tool(),
            _v1_skill(),
            EvalTask(
                task_id="t2_free_object",
                tool_name="calculate_average",
                user_request='Calculate average with gradeDict={"math": 95, "science": 91}.',
            ),
            _StaticPredictor(arguments={}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"gradeDict": {"math": 95, "science": 91}})

    def test_v1_preserves_exact_enum_case_when_schema_allows_it(self) -> None:
        prediction = safe_predict(
            _genotype_tool(),
            _v1_skill(),
            EvalTask(
                task_id="t2_enum_exact_case",
                tool_name="calculate_genotype_frequency",
                user_request='Calculate genotype frequency allele_frequency=9 genotype="aa".',
            ),
            _StaticPredictor(arguments={}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"allele_frequency": 9.0, "genotype": "aa"})

    def test_v1_accepts_explicit_symbolic_datetime_placeholders(self) -> None:
        prediction = safe_predict(
            _calendar_event_tool(),
            _v1_skill(),
            EvalTask(
                task_id="t2_symbolic_datetime",
                tool_name="calendar_create_event",
                user_request='Create event calendar_id="item-17" title="title_17" start_time="start_time_17" end_time="end_time_17".',
            ),
            _StaticPredictor(arguments={}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(
            prediction.predicted_arguments,
            {
                "calendar_id": "item-17",
                "title": "title_17",
                "start_time": "start_time_17",
                "end_time": "end_time_17",
            },
        )

    def test_v1_grounds_single_character_required_enum(self) -> None:
        prediction = safe_predict(
            _weather_tool(),
            _v1_skill(),
            EvalTask(
                task_id="t2_single_char_enum",
                tool_name="get_weather",
                user_request='Fetch weather city="Boston" unit="F" include_forecast=false.',
            ),
            _StaticPredictor(arguments={}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"city": "Boston", "unit": "F", "include_forecast": False})

    def test_v1_does_not_fill_optional_enum_from_benchmark_id_token(self) -> None:
        prediction = safe_predict(
            _ticket_create_tool(),
            _v1_skill(),
            EvalTask(
                task_id="t2_optional_enum_id_noise",
                tool_name="mock_issue_tracking_create_ticket",
                user_request='Create ticket project_key="project_key_8" title="title_8" dry_run=true. Use benchmark item id positive_medium_1.',
            ),
            _StaticPredictor(arguments={}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"project_key": "project_key_8", "title": "title_8", "dry_run": True})

    def test_v1_does_not_fill_tail_from_unrelated_end_tool_phrase(self) -> None:
        prediction = safe_predict(
            _read_with_head_tail_tool(),
            _v1_skill(),
            EvalTask(
                task_id="t2_optional_tail_noise",
                tool_name="read_file",
                user_request='Read path="docs/control_17.md" head=10 without using end codegen session.',
            ),
            _StaticPredictor(arguments={}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"path": "docs/control_17.md", "head": 10})

    def test_v1_does_not_fill_nested_optional_from_sibling_property_name(self) -> None:
        prediction = safe_predict(
            _start_codegen_tool(),
            _v1_skill(),
            EvalTask(
                task_id="t2_nested_optional_noise",
                tool_name="start_codegen_session",
                user_request='Start session options={"outputPath": "docs/control_17.md"}.',
            ),
            _StaticPredictor(arguments={}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"options": {"outputPath": "docs/control_17.md"}})

    def test_v1_does_not_fill_include_boolean_from_generic_include_phrase(self) -> None:
        prediction = safe_predict(
            _web_search_tool(),
            _v1_skill(),
            EvalTask(
                task_id="t2_include_boolean_noise",
                tool_name="tavily-search",
                user_request='Search query="reliability evaluation"; include these details where applicable: country="austria", days=9.',
            ),
            _StaticPredictor(arguments={}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"query": "reliability evaluation", "country": "austria", "days": 9})

    def test_v1_prefers_explicit_required_field_over_prose_grounding(self) -> None:
        prediction = safe_predict(
            ToolIR(
                tool_name="calc_heat_capacity",
                tool_purpose="Calculate heat capacity for a gas.",
                arguments=[
                    ArgumentIR(name="gas", type="string", required=True),
                    ArgumentIR(name="temp", type="integer", required=True),
                    ArgumentIR(name="volume", type="integer", required=True),
                ],
            ),
            _v1_skill(),
            EvalTask(
                task_id="t2_explicit_required_priority",
                tool_name="calc_heat_capacity",
                user_request=(
                    'Calculate the heat capacity at constant pressure of air; '
                    'include these details where applicable: gas="gas_17", temp=18, volume=18.'
                ),
            ),
            _StaticPredictor(arguments={"gas": "air", "temp": 18, "volume": 18}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {"gas": "gas_17", "temp": 18, "volume": 18})
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("replaced_ungrounded_required:gas", verifier["actions"])

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

    def test_v1_fills_nested_json_array_object_without_truncation(self) -> None:
        prediction = safe_predict(
            _observation_tool(),
            _v1_skill(),
            EvalTask(
                task_id="t2k_fill_array_json",
                tool_name="add_observations",
                user_request='Add observations=[{"contents": ["item_17"], "entityName": "entityname_17"}].',
            ),
            _StaticPredictor(arguments={}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(
            prediction.predicted_arguments,
            {"observations": [{"contents": ["item_17"], "entityName": "entityname_17"}]},
        )

    def test_v1_write_call_survives_unrelated_without_using_distractor_phrase(self) -> None:
        prediction = safe_predict(
            _observation_tool(),
            _v1_skill(),
            EvalTask(
                task_id="t2k_unrelated_without_using_write",
                tool_name="add_observations",
                user_request=(
                    'Without using notes create memory, add observations='
                    '[{"contents": ["item_17"], "entityName": "entityname_17"}].'
                ),
            ),
            _StaticPredictor(arguments={}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(
            prediction.predicted_arguments,
            {"observations": [{"contents": ["item_17"], "entityName": "entityname_17"}]},
        )

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

    def test_v1_redirects_forbidden_target_to_explicit_viable_contract_candidate(self) -> None:
        skill = _v1_skill()
        skill.metadata["contrastive_contract_candidates"] = [
            {"tool_name": "notes_create_memory", "viable": False, "proof_score": -10},
            {"tool_name": "add_observations", "viable": True, "proof_score": 42},
        ]

        prediction = safe_predict(
            ToolIR(
                tool_name="notes_create_memory",
                tool_purpose="Create a note memory.",
                arguments=[ArgumentIR(name="content", type="string", required=True)],
            ),
            skill,
            EvalTask(
                task_id="t4_redirect_similar_tool",
                tool_name="notes_create_memory",
                user_request=(
                    "Use add observations to add new observations to existing entities; "
                    "notes create memory is a distractor and should not be called."
                ),
            ),
            _StaticPredictor(arguments={"content": "Alice note"}),
        )

        self.assertFalse(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {})
        self.assertEqual(prediction.metadata["selected_tool_name"], "add_observations")
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("redirected_to_contract_candidate:add_observations", verifier["actions"])
        self.assertEqual(
            verifier["contrastive_contract_decision"]["reason"],
            "explicit_request_and_viable_contract",
        )

    def test_v1_redirects_action_conflict_to_higher_margin_viable_candidate(self) -> None:
        skill = _v1_skill()
        skill.metadata["contrastive_contract_candidates"] = [
            {
                "tool_name": "write_file",
                "viable": False,
                "proof_score": 2,
                "missing_required_args": ["content"],
                "action_intent_conflict": True,
            },
            {
                "tool_name": "read_file",
                "viable": True,
                "proof_score": 45,
                "missing_required_args": [],
                "request_actions": ["read"],
                "tool_actions": ["read"],
            },
        ]

        prediction = safe_predict(
            _write_tool(),
            skill,
            EvalTask(
                task_id="t4_redirect_action_conflict",
                tool_name="write_file",
                user_request="Read docs/report.md.",
            ),
            _StaticPredictor(arguments={"path": "docs/report.md", "content": "invented"}),
        )

        self.assertFalse(prediction.should_call)
        self.assertEqual(prediction.metadata["selected_tool_name"], "read_file")
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("redirected_to_contract_candidate:read_file", verifier["actions"])
        self.assertEqual(
            verifier["contrastive_contract_decision"]["reason"],
            "current_tool_blocked:action intent conflict",
        )

    def test_v1_does_not_redirect_adjacent_abstention_without_explicit_use(self) -> None:
        skill = _v1_skill()
        skill.metadata["contrastive_contract_candidates"] = [
            {"tool_name": "calendar_create_event", "viable": False, "proof_score": -5},
            {"tool_name": "calculate_clock_angle", "viable": True, "proof_score": 60},
        ]

        prediction = safe_predict(
            _create_event_tool(),
            skill,
            EvalTask(
                task_id="t4_adjacent_no_redirect",
                tool_name="calendar_create_event",
                user_request=(
                    "I need to calculate the angle between clock hands. "
                    "This is adjacent to calendar create event, but the intended capability is calculate clock angle."
                ),
            ),
            _StaticPredictor(arguments={"title": "meeting"}),
        )

        self.assertFalse(prediction.should_call)
        self.assertNotIn("selected_tool_name", prediction.metadata)
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIsNone(verifier["contrastive_contract_decision"])

    def test_v1_does_not_redirect_missing_required_information(self) -> None:
        skill = _v1_skill()
        skill.metadata["contrastive_contract_candidates"] = [
            {"tool_name": "calendar_create_event", "viable": False, "proof_score": -5},
            {"tool_name": "email_send_draft", "viable": True, "proof_score": 52},
        ]

        prediction = safe_predict(
            _create_event_tool(),
            skill,
            EvalTask(
                task_id="t4_missing_info_no_redirect",
                tool_name="calendar_create_event",
                user_request="I may need calendar create event, but I do not know calendar_id yet.",
            ),
            _StaticPredictor(arguments={}),
        )

        self.assertFalse(prediction.should_call)
        self.assertNotIn("selected_tool_name", prediction.metadata)
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIsNone(verifier["contrastive_contract_decision"])

    def test_v1_forbidden_target_matching_normalizes_punctuation(self) -> None:
        skill = _v1_skill()
        skill.metadata["contrastive_contract_candidates"] = [
            {"tool_name": "bank_get_account_balance", "viable": False, "proof_score": 12},
        ]

        prediction = safe_predict(
            ToolIR(
                tool_name="algebra.quadratic_roots",
                tool_purpose="Solve quadratic roots.",
                arguments=[ArgumentIR(name="a", type="number", required=True)],
            ),
            skill,
            EvalTask(
                task_id="t4_redirect_punctuated_target",
                tool_name="algebra.quadratic_roots",
                user_request=(
                    "Use bank get account balance to inspect the account; "
                    "algebra.quadratic roots is a distractor and should not be called."
                ),
            ),
            _StaticPredictor(arguments={"a": 1}),
        )

        self.assertFalse(prediction.should_call)
        self.assertEqual(prediction.metadata["selected_tool_name"], "bank_get_account_balance")
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("redirected_to_contract_candidate:bank_get_account_balance", verifier["actions"])

    def test_v1_adjacent_warning_does_not_treat_note_as_negation(self) -> None:
        skill = _v1_skill()
        skill.when_not_to_use.append("Do not use for adjacent tools with similar names or arguments.")

        prediction = safe_predict(
            _write_tool(),
            skill,
            EvalTask(
                task_id="t4_note_not_negation",
                tool_name="write_file",
                user_request='Write content="ReliaSkill control note 17" to path="docs/control_17.md".',
            ),
            _StaticPredictor(arguments={}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(
            prediction.predicted_arguments,
            {"path": "docs/control_17.md", "content": "ReliaSkill control note 17"},
        )

    def test_v1_without_using_unrelated_distractor_does_not_create_action_conflict(self) -> None:
        prediction = safe_predict(
            _no_argument_trigger_tool(),
            _v1_skill(),
            EvalTask(
                task_id="t4_unrelated_without_using_action_words",
                tool_name="trigger-elicitation-request-async",
                user_request=(
                    "I am trying to get this done without using bank get account balance: "
                    "Trigger an async elicitation request. Use the best matching tool and apply no arguments."
                ),
            ),
            _StaticPredictor(arguments={}),
        )

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {})
        verifier = prediction.metadata["reliaskill_v1_runtime_verifier"]
        self.assertIn("allowed_direct_no_argument_call_despite_policy:repair", verifier["actions"])

    def test_v1_abstains_on_adjacent_wrong_intent_template(self) -> None:
        prediction = safe_predict(
            _create_event_tool(),
            _v1_skill(),
            EvalTask(
                task_id="t4_adjacent_wrong_intent",
                tool_name="calendar_create_event",
                user_request=(
                    "I need to Calculate the angle between the hour and minute hands of a clock at a given time. "
                    "This is adjacent to calendar create event, but the intended capability is calculate clock angle."
                ),
            ),
            _StaticPredictor(arguments={"title": "clock angle"}),
        )

        self.assertFalse(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {})
        self.assertEqual(prediction.abstention_reason, "adjacent_wrong_intent")

    def test_v1_abstains_on_ambiguous_not_sure_template(self) -> None:
        prediction = safe_predict(
            _search_tool(),
            _v1_skill(),
            EvalTask(
                task_id="t4_ambiguous_not_sure",
                tool_name="search",
                user_request="Maybe do something with search; actually, I am not sure what input or action is intended.",
            ),
            _StaticPredictor(arguments={"query": "schema contract"}),
        )

        self.assertFalse(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {})
        self.assertEqual(prediction.abstention_reason, "ambiguous_action")

    def test_v1_abstains_on_may_need_but_missing_field_template(self) -> None:
        prediction = safe_predict(
            _calendar_event_tool(),
            _v1_skill(),
            EvalTask(
                task_id="t4_missing_field_template",
                tool_name="calendar_create_event",
                user_request="I may need calendar create event, but I do not know calendar_id yet.",
            ),
            _StaticPredictor(
                arguments={
                    "calendar_id": "cal-1",
                    "title": "standup",
                    "start_time": "2026-05-20T09:00",
                    "end_time": "2026-05-20T09:30",
                }
            ),
        )

        self.assertFalse(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {})
        self.assertEqual(prediction.abstention_reason, "missing_required_information")

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


def _assignment_tool() -> ToolIR:
    return ToolIR(
        tool_name="assign_ticket",
        tool_purpose="Assign a ticket to a user.",
        arguments=[ArgumentIR(name="assignee_id", type="string", required=True)],
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


def _write_tool() -> ToolIR:
    return ToolIR(
        tool_name="write_file",
        tool_purpose="Write content to a file path.",
        arguments=[
            ArgumentIR(name="path", type="string", required=True),
            ArgumentIR(name="content", type="string", required=True),
        ],
        schema_complexity={"side_effect_type": "write"},
    )


def _no_argument_trigger_tool() -> ToolIR:
    return ToolIR(
        tool_name="trigger-elicitation-request-async",
        tool_purpose="Trigger an async elicitation request that runs as a background task.",
        arguments=[],
        schema_complexity={"side_effect_type": "write"},
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


def _array_sort_tool() -> ToolIR:
    return ToolIR(
        tool_name="array_sort",
        tool_purpose="Sort a numeric array.",
        arguments=[
            ArgumentIR(name="list", type="array", required=True, items_type="number"),
            ArgumentIR(name="order", type="string", required=True, enum=["ascending", "descending"]),
        ],
    )


def _city_route_tool() -> ToolIR:
    return ToolIR(
        tool_name="city_distance.find_shortest",
        tool_purpose="Find a route between two cities.",
        arguments=[
            ArgumentIR(name="start_city", type="string", required=True),
            ArgumentIR(name="end_city", type="string", required=True),
        ],
    )


def _dna_tool() -> ToolIR:
    return ToolIR(
        tool_name="analyze_dna_sequence",
        tool_purpose="Analyze differences between a DNA sequence and reference sequence.",
        arguments=[
            ArgumentIR(name="sequence", type="string", required=True),
            ArgumentIR(name="reference_sequence", type="string", required=True),
        ],
    )


def _quadratic_tool() -> ToolIR:
    return ToolIR(
        tool_name="algebra.quadratic_roots",
        tool_purpose="Solve quadratic roots from coefficients a, b, and c.",
        arguments=[
            ArgumentIR(name="a", type="number", required=True),
            ArgumentIR(name="b", type="number", required=True),
            ArgumentIR(name="c", type="number", required=True),
        ],
    )


def _free_form_object_tool() -> ToolIR:
    return ToolIR(
        tool_name="calculate_average",
        tool_purpose="Calculate an average from a dictionary of grades.",
        arguments=[ArgumentIR(name="gradeDict", type="object", required=True)],
    )


def _genotype_tool() -> ToolIR:
    return ToolIR(
        tool_name="calculate_genotype_frequency",
        tool_purpose="Calculate genotype frequency.",
        arguments=[
            ArgumentIR(name="allele_frequency", type="number", required=True),
            ArgumentIR(name="genotype", type="string", required=True, enum=["AA", "Aa", "aa"]),
        ],
    )


def _calendar_event_tool() -> ToolIR:
    return ToolIR(
        tool_name="calendar_create_event",
        tool_purpose="Create a calendar event.",
        arguments=[
            ArgumentIR(name="calendar_id", type="string", required=True),
            ArgumentIR(name="title", type="string", required=True),
            ArgumentIR(name="start_time", type="string", required=True, format="date-time"),
            ArgumentIR(name="end_time", type="string", required=True, format="date-time"),
        ],
        schema_complexity={"side_effect_type": "write"},
    )


def _weather_tool() -> ToolIR:
    return ToolIR(
        tool_name="get_weather",
        tool_purpose="Fetch weather for a city.",
        arguments=[
            ArgumentIR(name="city", type="string", required=True),
            ArgumentIR(name="unit", type="string", required=True, enum=["C", "F"]),
            ArgumentIR(name="include_forecast", type="boolean", required=False),
        ],
    )


def _ticket_create_tool() -> ToolIR:
    return ToolIR(
        tool_name="mock_issue_tracking_create_ticket",
        tool_purpose="Create a ticket in an offline benchmark fixture.",
        arguments=[
            ArgumentIR(name="project_key", type="string", required=True),
            ArgumentIR(name="title", type="string", required=True),
            ArgumentIR(name="dry_run", type="boolean", required=False),
            ArgumentIR(name="priority", type="string", required=False, enum=["low", "medium", "high"]),
        ],
        schema_complexity={"side_effect_type": "write"},
    )


def _read_with_head_tail_tool() -> ToolIR:
    return ToolIR(
        tool_name="read_file",
        tool_purpose="Read file contents.",
        arguments=[
            ArgumentIR(name="path", type="string", required=True),
            ArgumentIR(name="head", type="integer", required=False),
            ArgumentIR(name="tail", type="integer", required=False),
        ],
    )


def _start_codegen_tool() -> ToolIR:
    return ToolIR(
        tool_name="start_codegen_session",
        tool_purpose="Start a code generation session.",
        arguments=[
            ArgumentIR(
                name="options",
                type="object",
                required=True,
                properties={"outputPath": {"type": "string"}, "testNamePrefix": {"type": "string"}},
                required_properties=["outputPath"],
            )
        ],
    )


def _web_search_tool() -> ToolIR:
    return ToolIR(
        tool_name="tavily-search",
        tool_purpose="Search the web.",
        arguments=[
            ArgumentIR(name="query", type="string", required=True),
            ArgumentIR(name="country", type="string", required=False),
            ArgumentIR(name="days", type="integer", required=False),
            ArgumentIR(name="include_images", type="boolean", required=False),
            ArgumentIR(name="include_image_descriptions", type="boolean", required=False),
            ArgumentIR(name="include_raw_content", type="boolean", required=False),
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

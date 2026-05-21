from __future__ import annotations

from autoskill.eval_types import EvalPrediction, EvalTask
from autoskill.ir import ArgumentIR, GeneratedSkill, ToolIR
from autoskill.predictor import PredictorBackend, safe_predict
from autoskill.routing_eval import _maybe_apply_reliaskill_routing_arbitration


def test_runtime_arbitration_preserves_valid_model_native_call() -> None:
    backend = _LocalHFStaticPredictor(arguments={"query": "schema contract"})
    skill = _v1_skill_with_arbitration()

    prediction = safe_predict(
        ToolIR(
            tool_name="search",
            tool_purpose="Search documents.",
            arguments=[ArgumentIR(name="query", type="string", required=True)],
        ),
        skill,
        EvalTask(task_id="arb_runtime", tool_name="search", user_request='Search query="schema contract".'),
        backend,
    )

    assert prediction.should_call
    assert prediction.predicted_arguments == {"query": "schema contract"}
    assert backend.predict_calls == 1
    assert prediction.metadata["actual_predictor_backend"] == "local_hf"
    assert prediction.metadata["reliaskill_v1_arbitration"]["selected"] == "model_native_verified"


def test_runtime_arbitration_checks_model_native_call_even_when_threshold_low() -> None:
    backend = _LocalHFStaticPredictor(arguments={"query": "different model output"})
    skill = _v1_skill_with_arbitration(runtime_threshold=0.0)

    prediction = safe_predict(
        ToolIR(
            tool_name="search",
            tool_purpose="Search documents.",
            arguments=[ArgumentIR(name="query", type="string", required=True)],
        ),
        skill,
        EvalTask(task_id="arb_runtime_skip", tool_name="search", user_request='Search query="schema contract".'),
        backend,
    )

    assert prediction.should_call
    assert prediction.predicted_arguments == {"query": "schema contract"}
    assert backend.predict_calls == 1
    assert prediction.metadata["actual_predictor_backend"] == "local_hf"
    assert prediction.metadata["reliaskill_v1_arbitration"]["selected"] == "model_native_verified"


def test_runtime_arbitration_records_attempt_when_model_native_fails() -> None:
    backend = _FailingLocalHFPredictor()
    skill = _v1_skill_with_arbitration()

    prediction = safe_predict(
        ToolIR(
            tool_name="search",
            tool_purpose="Search documents.",
            arguments=[ArgumentIR(name="query", type="string", required=True)],
        ),
        skill,
        EvalTask(task_id="arb_runtime_fail", tool_name="search", user_request='Search query="schema contract".'),
        backend,
    )

    assert prediction.should_call
    assert prediction.predicted_arguments == {"query": "schema contract"}
    assert backend.predict_calls == 1
    assert prediction.metadata["actual_predictor_backend"] == "reliaskill_contract_predecoder"
    predecoder = prediction.metadata["reliaskill_v1_predecoder"]
    assert predecoder["skipped_model_call"] is False
    assert predecoder["arbitration_model_call_attempted"] is True
    assert prediction.metadata["reliaskill_v1_arbitration"]["reason"] == "model_native_prediction_failed"


def test_runtime_adaptive_prompt_policy_uses_compact_prompt_for_low_risk_call() -> None:
    backend = _LocalHFStaticPredictor(arguments={"query": "schema contract"})
    skill = _v1_skill_with_arbitration(prompt_fallback=True)

    prediction = safe_predict(
        ToolIR(
            tool_name="search",
            tool_purpose="Search documents.",
            arguments=[ArgumentIR(name="query", type="string", required=True)],
        ),
        skill,
        EvalTask(task_id="arb_prompt", tool_name="search", user_request='Search query="schema contract".'),
        backend,
    )

    assert prediction.should_call
    assert prediction.predicted_arguments == {"query": "schema contract"}
    assert backend.predict_calls == 1
    prompt_policy = prediction.metadata["reliaskill_v1_adaptive_prompt_policy"]
    assert prompt_policy["selected"] == "compact_fallback_prompt"
    assert prompt_policy["reason"] == "low_risk_grounded_call"


def test_runtime_adaptive_prompt_policy_rescues_non_predecoded_model_abstention() -> None:
    backend = _PromptSensitiveStaticPredictor()
    skill = _v1_skill_with_arbitration(prompt_fallback=True)

    prediction = safe_predict(
        ToolIR(
            tool_name="search",
            tool_purpose="Search documents.",
            arguments=[ArgumentIR(name="query", type="string", required=True)],
        ),
        skill,
        EvalTask(
            task_id="arb_prompt_non_predecoded",
            tool_name="search",
            user_request='Please retrieve matching documents; include query="schema contract".',
        ),
        backend,
    )

    assert prediction.should_call
    assert prediction.predicted_arguments == {"query": "schema contract"}
    assert backend.predict_calls == 1
    assert prediction.metadata["actual_predictor_backend"] == "static"
    prompt_policy = prediction.metadata["reliaskill_v1_adaptive_prompt_policy"]
    assert prompt_policy["selected"] == "compact_fallback_prompt"
    assert prompt_policy["reason"] == "low_risk_grounded_call"


def test_runtime_adaptive_prompt_policy_keeps_full_prompt_for_side_effect_tool() -> None:
    backend = _LocalHFStaticPredictor(arguments={"title": "sync"})
    skill = _v1_skill_with_arbitration(prompt_fallback=True)

    prediction = safe_predict(
        ToolIR(
            tool_name="calendar_create_event",
            tool_purpose="Create calendar events.",
            arguments=[ArgumentIR(name="title", type="string", required=True)],
            schema_complexity={"side_effect_type": "write"},
        ),
        skill,
        EvalTask(
            task_id="arb_prompt_side_effect",
            tool_name="calendar_create_event",
            user_request='Create a calendar event title="sync".',
        ),
        backend,
    )

    assert prediction.should_call
    assert prediction.predicted_arguments == {"title": "sync"}
    prompt_policy = prediction.metadata["reliaskill_v1_adaptive_prompt_policy"]
    assert prompt_policy["selected"] == "full_reliaskill_prompt"
    assert prompt_policy["reason"] == "side_effect_risk"


def test_routing_arbitration_preserves_low_risk_native_candidate() -> None:
    skill_bank = {
        "calendar_create_event": _v1_skill_with_arbitration(),
        "calculate_clock_angle": _v1_skill_with_arbitration(),
    }
    selected = {
        "tool_name": "calendar_create_event",
        "model_native_router_score": 4,
        "contract_viable": True,
        "contract_satisfied": True,
        "contract_proof_margin": 5.0,
        "contract_blocking_reasons": [],
        "missing_required_args": [],
        "action_intent_conflict": False,
    }
    native = {
        "tool_name": "calculate_clock_angle",
        "model_native_router_score": 16,
        "contract_viable": True,
        "contract_satisfied": True,
        "contract_proof_margin": 3.0,
        "contract_blocking_reasons": [],
        "missing_required_args": [],
        "action_intent_conflict": False,
    }

    decision = _maybe_apply_reliaskill_routing_arbitration(
        "Calculate the clock angle.",
        selected,
        [selected, native],
        skill_bank,
    )

    assert decision is not None
    assert decision["selected"] == "model_native_low_risk_candidate"
    assert decision["selected_tool_name"] == "calculate_clock_angle"


def test_routing_arbitration_keeps_contract_candidate_when_native_is_blocked() -> None:
    skill_bank = {
        "calendar_create_event": _v1_skill_with_arbitration(),
        "calculate_clock_angle": _v1_skill_with_arbitration(),
    }
    selected = {
        "tool_name": "calendar_create_event",
        "model_native_router_score": 4,
        "contract_viable": True,
        "contract_satisfied": True,
        "contract_proof_margin": 5.0,
        "contract_blocking_reasons": [],
        "missing_required_args": [],
        "action_intent_conflict": False,
    }
    blocked_native = {
        "tool_name": "calculate_clock_angle",
        "model_native_router_score": 16,
        "contract_viable": False,
        "contract_satisfied": False,
        "contract_proof_margin": -8.0,
        "contract_blocking_reasons": ["missing_required_arguments"],
        "missing_required_args": ["time"],
        "action_intent_conflict": False,
    }

    decision = _maybe_apply_reliaskill_routing_arbitration(
        "Calculate the clock angle later when I provide the time.",
        selected,
        [selected, blocked_native],
        skill_bank,
    )

    assert decision is None


def _v1_skill_with_arbitration(*, runtime_threshold: float = 20.0, prompt_fallback: bool = False) -> GeneratedSkill:
    metadata = {
        "contract_arbitration_policy": {
            "name": "test_contract_aware_arbitration",
            "enabled": True,
            "enable_runtime_model_arbitration": True,
            "enable_routing_arbitration": True,
            "runtime_arbitration_margin_threshold": runtime_threshold,
            "preserve_native_routing_margin": 10.0,
            "preserve_native_score_advantage": 4.0,
            "contract_override_margin": 12.0,
            "low_risk_missing_required_max": 0,
            "hard_block_reasons": [
                "missing_required_arguments",
                "action_intent_conflict",
                "argument_contract_violation",
            ],
            "calibration_source": "unit_test",
        }
    }
    if prompt_fallback:
        metadata["adaptive_prompt_fallback_skill"] = GeneratedSkill(
            baseline_name="generated_skill_base",
            skill_summary="Fallback generated prompt.",
            when_to_use=["Use for direct search requests."],
            when_not_to_use=["Do not use without a query."],
            argument_template={"query": "schema contract"},
        ).model_dump()
    return GeneratedSkill(
        baseline_name="reliaskill_v1",
        skill_summary="Runtime-verified ReliaSkill artifact.",
        when_to_use=["Use for direct, grounded requests."],
        when_not_to_use=["Do not use when required fields are missing."],
        metadata=metadata,
    )


class _FailingLocalHFPredictor(PredictorBackend):
    backend_name = "local_hf"

    def __init__(self) -> None:
        self.predict_calls = 0

    def predict(self, tool: ToolIR, skill: GeneratedSkill, task: EvalTask):
        self.predict_calls += 1
        raise RuntimeError("forced arbitration failure")


class _LocalHFStaticPredictor(PredictorBackend):
    backend_name = "local_hf"

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


class _PromptSensitiveStaticPredictor(PredictorBackend):
    backend_name = "static"

    def __init__(self) -> None:
        self.predict_calls = 0

    def predict(self, tool: ToolIR, skill: GeneratedSkill, task: EvalTask) -> EvalPrediction:
        self.predict_calls += 1
        is_fallback = skill.baseline_name == "generated_skill_base"
        return EvalPrediction(
            task_id=task.task_id,
            tool_name=tool.tool_name,
            baseline_name=skill.baseline_name,
            predicted_arguments={"query": "schema contract"} if is_fallback else {},
            should_call=is_fallback,
            abstention_reason=None if is_fallback else "model_abstained",
            metadata={"raw_model_output": "fallback" if is_fallback else "current"},
        )

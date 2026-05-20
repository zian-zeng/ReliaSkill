from __future__ import annotations

from autoskill.eval_types import EvalTask
from autoskill.ir import ArgumentIR, BehaviorCase, GeneratedSkill, ToolIR
from autoskill.learned_router import learn_global_router_policy, learn_router_policy, score_learned_router
from autoskill.predictor import _reliaskill_v1_boundary_reason
from autoskill.routing_eval import select_tool_for_task


def test_dev_learned_router_scores_positive_over_negative_boundary() -> None:
    tool = _calendar_tool()
    skill = _skill_with_router_policy(tool)

    positive = score_learned_router("Create a calendar event for the design review tomorrow.", tool, skill)
    negative = score_learned_router("Plan a museum itinerary in Chicago and estimate ticket costs.", tool, skill)

    assert positive.score > negative.score
    assert positive.route_bonus > 0
    assert negative.route_bonus < 0
    assert negative.negative_boundary


def test_dev_learned_router_can_block_runtime_false_trigger() -> None:
    tool = _calendar_tool()
    skill = _skill_with_router_policy(tool)

    reason = _reliaskill_v1_boundary_reason(
        tool,
        skill,
        "Plan a museum itinerary in Chicago and estimate ticket costs.",
    )

    assert reason == "dev_learned_router_negative_boundary"


def test_learned_router_rerank_metadata_prefers_matching_tool() -> None:
    calendar = _calendar_tool()
    weather = ToolIR(
        tool_name="weather_forecast",
        tool_purpose="Get a weather forecast for a city.",
        arguments=[ArgumentIR(name="city", type="string", required=True)],
    )
    tools = {calendar.tool_name: calendar, weather.tool_name: weather}
    skills = {
        calendar.tool_name: _skill_with_router_policy(calendar),
        weather.tool_name: GeneratedSkill(
            baseline_name="reliaskill_v1",
            skill_summary="Get weather forecasts.",
            when_to_use=["Use for weather forecast requests."],
            when_not_to_use=["Do not use for calendar scheduling."],
            metadata={
                "learned_router_policy": learn_router_policy(
                    weather,
                    GeneratedSkill(baseline_name="reliaskill_v1", skill_summary="Get weather forecasts."),
                    [
                        BehaviorCase(
                            case_id="weather_pos",
                            tool_name="weather_forecast",
                            user_request="Get the weather forecast for Chicago.",
                            should_trigger=True,
                            expected_arguments={"city": "Chicago"},
                        ),
                        BehaviorCase(
                            case_id="weather_neg",
                            tool_name="weather_forecast",
                            user_request="Create a calendar event for the design review tomorrow.",
                            should_trigger=False,
                            negative_target="weather_forecast",
                            negative_category="similar_tool_should_be_used",
                        ),
                    ],
                )
            },
        ),
    }

    routing = select_tool_for_task(
        EvalTask(
            task_id="route_learned_policy",
            tool_name="weather_forecast",
            user_request="Get the weather forecast for Chicago.",
        ),
        "reliaskill_v1",
        tools,
        skills,
        top_k=2,
    )
    rows = {row["tool_name"]: row for row in routing["candidate_rows"]}

    assert routing["selected_tool_name"] == "weather_forecast"
    assert rows["weather_forecast"]["learned_router_score"] > rows["calendar_create_event"]["learned_router_score"]
    assert "learned_router_policy" in rows["weather_forecast"]["contract_routing_features"]


def test_global_prior_and_hard_negative_policy_are_explicit_components() -> None:
    calendar = _calendar_tool()
    weather = ToolIR(
        tool_name="weather_forecast",
        tool_purpose="Get a weather forecast for a city.",
        arguments=[ArgumentIR(name="city", type="string", required=True)],
    )
    cases = [
        BehaviorCase(
            case_id="calendar_pos",
            tool_name=calendar.tool_name,
            user_request="Create a calendar event for the design review tomorrow.",
            should_trigger=True,
            expected_arguments={"title": "design review"},
        ),
        BehaviorCase(
            case_id="calendar_neg",
            tool_name=calendar.tool_name,
            user_request="Get the weather forecast for Chicago.",
            should_trigger=False,
            negative_target=calendar.tool_name,
            negative_category="similar_tool_should_be_used",
        ),
        BehaviorCase(
            case_id="weather_pos",
            tool_name=weather.tool_name,
            user_request="Get the weather forecast for Chicago.",
            should_trigger=True,
            expected_arguments={"city": "Chicago"},
        ),
    ]
    global_policy = learn_global_router_policy({calendar.tool_name: calendar, weather.tool_name: weather}, cases)
    skill = GeneratedSkill(
        baseline_name="reliaskill_v1",
        skill_summary="Create calendar events.",
        when_to_use=["Use for creating calendar events."],
        when_not_to_use=["Do not use for weather forecast requests."],
        metadata={"learned_router_policy": learn_router_policy(calendar, GeneratedSkill(), cases, global_router_policy=global_policy)},
    )

    policy = skill.metadata["learned_router_policy"]
    decision = score_learned_router("Get the weather forecast for Chicago.", calendar, skill)

    assert global_policy["enabled"]
    assert policy["uses_global_pairwise_prior"]
    assert policy["self_mined_hard_row_count"] >= 1
    assert "global_prior" in decision.components
    assert "hard_negative_delta" in decision.components
    assert decision.policy_action == "abstain"


def test_unified_policy_can_abstain_even_when_schema_is_viable() -> None:
    tool = _calendar_tool()
    skill = GeneratedSkill(
        baseline_name="reliaskill_v1",
        skill_summary="Create calendar events.",
        when_to_use=["Use for creating calendar events."],
        when_not_to_use=[],
        argument_template={"title": "<title>"},
        metadata={
            "schema_contract": ["Allowed top-level fields: `title`."],
            "learned_router_policy": {
                "name": "dev_learned_risk_aware_router_policy",
                "enabled": True,
                "weights": {
                    "bias": -1.0,
                    "matched_required_args": 1.0,
                    "action_family_overlap": 1.0,
                    "side_effect_conflict": -20.0,
                },
                "threshold": 0.0,
                "route_bonus_scale": 5.0,
                "max_route_bonus": 36,
                "negative_boundary_threshold": -3.0,
            },
        },
    )

    routing = select_tool_for_task(
        EvalTask(
            task_id="policy_abstain",
            tool_name=tool.tool_name,
            user_request="Create a calendar event with title: design review in read-only preview mode.",
            expected_arguments={"title": "design review"},
        ),
        "reliaskill_v1",
        {tool.tool_name: tool},
        {tool.tool_name: skill},
        top_k=1,
    )

    assert routing["selected_tool_name"] == "__abstain__"
    assert routing["routing_strategy"] == "retrieve_then_semantic_rerank_learned_policy_abstention"
    assert routing["candidate_rows"][0]["routing_abstention_reason"] == "learned_proof_risk_policy_abstention"


def _calendar_tool() -> ToolIR:
    return ToolIR(
        tool_name="calendar_create_event",
        tool_purpose="Create a calendar event.",
        arguments=[ArgumentIR(name="title", type="string", required=True)],
        side_effect_hints=["write"],
    )


def _skill_with_router_policy(tool: ToolIR) -> GeneratedSkill:
    behavior_cases = [
        BehaviorCase(
            case_id="calendar_pos",
            tool_name=tool.tool_name,
            user_request="Create a calendar event for the design review tomorrow.",
            should_trigger=True,
            expected_arguments={"title": "design review"},
        ),
        BehaviorCase(
            case_id="calendar_neg",
            tool_name=tool.tool_name,
            user_request="Plan a museum itinerary in Chicago and estimate ticket costs.",
            should_trigger=False,
            negative_target=tool.tool_name,
            negative_category="out_of_domain_request",
        ),
    ]
    return GeneratedSkill(
        baseline_name="reliaskill_v1",
        skill_summary="Create calendar events.",
        when_to_use=["Use for creating calendar events."],
        when_not_to_use=["Do not use for museum itinerary planning or ticket cost estimation."],
        metadata={
            "learned_router_policy": learn_router_policy(
                tool,
                GeneratedSkill(
                    baseline_name="reliaskill_v1",
                    skill_summary="Create calendar events.",
                    when_to_use=["Use for creating calendar events."],
                    when_not_to_use=["Do not use for museum itinerary planning or ticket cost estimation."],
                ),
                behavior_cases,
            )
        },
    )

from __future__ import annotations

from autoskill.contrastive_memory import learn_contrastive_memory_policy, score_contrastive_memory
from autoskill.eval_types import EvalTask
from autoskill.ir import ArgumentIR, BehaviorCase, GeneratedSkill, ToolIR
from autoskill.predictor import _reliaskill_v1_boundary_reason
from autoskill.routing_eval import select_tool_for_task


def test_dev_learned_contrastive_memory_scores_positive_over_near_negative() -> None:
    tool = _calendar_tool()
    skill = _skill_with_memory(tool)

    positive = score_contrastive_memory("Create a calendar event for the design review tomorrow.", tool, skill)
    negative = score_contrastive_memory("Plan a museum itinerary in Chicago and estimate ticket costs.", tool, skill)

    assert positive.score > negative.score
    assert positive.route_bonus > 0
    assert negative.route_bonus < 0
    assert negative.negative_boundary


def test_contrastive_memory_can_block_runtime_false_trigger() -> None:
    tool = _calendar_tool()
    skill = _skill_with_memory(tool)

    reason = _reliaskill_v1_boundary_reason(
        tool,
        skill,
        "Plan a museum itinerary in Chicago and estimate ticket costs.",
    )

    assert reason == "dev_contrastive_memory_negative_boundary"


def test_contrastive_memory_reranks_low_risk_candidate() -> None:
    calendar = _calendar_tool()
    weather = ToolIR(
        tool_name="weather_forecast",
        tool_purpose="Get a weather forecast for a city.",
        arguments=[ArgumentIR(name="city", type="string", required=True)],
    )
    tools = {calendar.tool_name: calendar, weather.tool_name: weather}
    skills = {
        calendar.tool_name: _skill_with_memory(calendar),
        weather.tool_name: GeneratedSkill(
            baseline_name="reliaskill_v1",
            skill_summary="Get weather forecasts.",
            when_to_use=["Use for weather forecast requests."],
            metadata={
                "contrastive_memory_policy": learn_contrastive_memory_policy(
                    weather,
                    GeneratedSkill(baseline_name="reliaskill_v1"),
                    [
                        BehaviorCase(
                            case_id="weather_pos",
                            tool_name="weather_forecast",
                            user_request="Get the weather forecast for Chicago.",
                            should_trigger=True,
                        )
                    ],
                )
            },
        ),
    }

    routing = select_tool_for_task(
        EvalTask(
            task_id="route_memory",
            tool_name="weather_forecast",
            user_request="Get the weather forecast for Chicago.",
        ),
        "reliaskill_v1",
        tools,
        skills,
        top_k=2,
    )

    assert routing["selected_tool_name"] == "weather_forecast"


def _calendar_tool() -> ToolIR:
    return ToolIR(
        tool_name="calendar_create_event",
        tool_purpose="Create a calendar event.",
        arguments=[ArgumentIR(name="title", type="string", required=True)],
        side_effect_hints=["write"],
    )


def _skill_with_memory(tool: ToolIR) -> GeneratedSkill:
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
        when_not_to_use=[],
        metadata={"contrastive_memory_policy": learn_contrastive_memory_policy(tool, GeneratedSkill(), behavior_cases)},
    )

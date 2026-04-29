from __future__ import annotations

from autoskill.compactness import SKILL_LENGTH_VARIANTS
from autoskill.conditions import REVIEWER_BASELINES
from autoskill.prompt_templates import PROMPT_TEMPLATE_CONDITIONS, PROMPT_TEMPLATE_SPECS
from reliaskill.human_skill_condition import HUMAN_WRITTEN_SKILL
from reliaskill.stress_tests.corrupt_skills import STRESS_TEST_CONDITIONS

CONDITION_REGISTRY = {
    condition: {"condition": condition}
    for condition in REVIEWER_BASELINES
}
CONDITION_REGISTRY[HUMAN_WRITTEN_SKILL] = {
    "condition": HUMAN_WRITTEN_SKILL,
    "family": "human_upper_bound",
    "requires_human_artifact": True,
    "skills_root": "data/human_skills/skills",
    "uses_dev_controls_for_authoring": False,
    "uses_test_controls_for_authoring": False,
}
for condition, config in SKILL_LENGTH_VARIANTS.items():
    CONDITION_REGISTRY[condition] = {
        "condition": condition,
        "family": "skill_compactness",
        "max_skill_tokens": config.get("max_skill_tokens"),
        "max_examples": config.get("max_examples"),
        "include_when_not_to_use": config.get("include_when_not_to_use"),
        "include_failure_modes": config.get("include_failure_modes"),
        "include_argument_template": config.get("include_argument_template"),
    }
for condition, template_id in PROMPT_TEMPLATE_CONDITIONS.items():
    spec = PROMPT_TEMPLATE_SPECS[template_id]
    CONDITION_REGISTRY[condition] = {
        "condition": condition,
        "family": "prompt_template_ablation",
        "template_id": spec.template_id,
        "template_family": spec.template_family,
        "allowed_sections": list(spec.allowed_sections),
        "max_tokens": spec.max_tokens,
        "uses_dev_controls": spec.uses_dev_controls,
        "uses_negative_controls": spec.uses_negative_controls,
    }
for condition, corruption_types in STRESS_TEST_CONDITIONS.items():
    CONDITION_REGISTRY[condition] = {
        "condition": condition,
        "family": "diagnostic_corrupted_skill",
        "diagnostic_only": True,
        "adversarial": True,
        "corruption_types": list(corruption_types),
        "normal_benchmark_condition": False,
        "requires_explicit_configuration": True,
    }

__all__ = [
    "CONDITION_REGISTRY",
    "REVIEWER_BASELINES",
    "SKILL_LENGTH_VARIANTS",
    "HUMAN_WRITTEN_SKILL",
    "PROMPT_TEMPLATE_CONDITIONS",
    "STRESS_TEST_CONDITIONS",
]

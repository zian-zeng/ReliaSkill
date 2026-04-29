from __future__ import annotations

from autoskill.generator import SkillGenerator
from autoskill.compactness import build_compactness_variant, build_compactness_variants
from autoskill.multi_candidate import generate_skill_candidates
from autoskill.prompt_templates import (
    PROMPT_TEMPLATE_CONDITIONS,
    PROMPT_TEMPLATE_SPECS,
    build_generation_prompt_from_template,
    build_skill_from_prompt_template,
    generate_prompt_template_skills,
    parse_generated_skill_output,
)

__all__ = [
    "SkillGenerator",
    "build_compactness_variant",
    "build_compactness_variants",
    "generate_skill_candidates",
    "PROMPT_TEMPLATE_CONDITIONS",
    "PROMPT_TEMPLATE_SPECS",
    "build_generation_prompt_from_template",
    "build_skill_from_prompt_template",
    "generate_prompt_template_skills",
    "parse_generated_skill_output",
]

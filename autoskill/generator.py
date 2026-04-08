from __future__ import annotations

from autoskill.backends import (
    GenerationBackend,
    build_backend_from_config,
    build_backend_from_env,
    safe_generate_skill,
)
from autoskill.ir import GeneratedSkill, ToolIR


class SkillGenerator:
    def __init__(
        self,
        backend: GenerationBackend | None = None,
        backend_config: dict | None = None,
    ) -> None:
        self.backend = backend or build_backend_from_config(backend_config)

    def generate(self, tool: ToolIR) -> GeneratedSkill:
        return safe_generate_skill(tool, self.backend)

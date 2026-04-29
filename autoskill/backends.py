from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Any, Dict

from autoskill.ir import GeneratedSkill, ToolIR
from autoskill.method import build_enhanced_skill_candidates, select_best_skill_candidate
from autoskill.json_output import parse_json_object_output
from autoskill.local_model import LocalHFChatRunner
from autoskill.prompting import build_generation_prompt
from autoskill.prompt_templates import build_skill_from_prompt_template, parse_generated_skill_output
from autoskill.templates import build_argument_template


def _required_argument_line(tool: ToolIR) -> str:
    required = [arg.name for arg in tool.arguments if arg.required]
    if not required:
        return "This tool has no required input fields."
    if len(required) == 1:
        return f"Provide the required field `{required[0]}`."
    joined = ", ".join(f"`{name}`" for name in required[:-1]) + f", and `{required[-1]}`"
    return f"Provide all required fields: {joined}."


def _optional_argument_line(tool: ToolIR) -> str | None:
    optional = [arg.name for arg in tool.arguments if not arg.required]
    if not optional:
        return None
    if len(optional) == 1:
        return f"Optional control is available through `{optional[0]}` when the request needs extra specificity."
    preview = ", ".join(f"`{name}`" for name in optional[:4])
    suffix = "" if len(optional) <= 4 else ", and other optional fields"
    return f"Optional controls include {preview}{suffix}."


def _enum_line(tool: ToolIR) -> str | None:
    for arg in tool.arguments:
        if arg.enum:
            values = ", ".join(repr(value) for value in arg.enum[:4])
            return f"Respect the allowed values for `{arg.name}`: {values}."
    return None


class GenerationBackend(ABC):
    backend_name = "base"

    @abstractmethod
    def generate_skill(self, tool: ToolIR) -> GeneratedSkill:
        raise NotImplementedError


class HeuristicBackend(GenerationBackend):
    backend_name = "heuristic"

    def __init__(self, ablation_mode: str = "selected", prompt_template_id: str | None = None) -> None:
        self.ablation_mode = ablation_mode
        self.prompt_template_id = prompt_template_id

    def generate_skill(self, tool: ToolIR) -> GeneratedSkill:
        if self.prompt_template_id:
            return build_skill_from_prompt_template(tool, self.prompt_template_id)
        purpose = tool.tool_purpose or f"{tool.tool_name} performs a tool action."
        summary_parts = [purpose.rstrip(".") + "."]
        summary_parts.append(_required_argument_line(tool))
        if tool.output_hint:
            summary_parts.append(tool.output_hint.rstrip(".") + ".")
        summary = " ".join(summary_parts)

        when_to_use = [
            f"Use `{tool.tool_name}` when the user's request directly matches this tool's purpose.",
            _required_argument_line(tool),
        ]
        optional_line = _optional_argument_line(tool)
        if optional_line:
            when_to_use.append(optional_line)

        when_not_to_use = [
            "Do not call this tool when required inputs are missing or ambiguous.",
            "Do not invent unsupported parameters or unsupported enum values.",
        ]
        enum_line = _enum_line(tool)
        if enum_line:
            when_not_to_use.append(enum_line)
        if tool.auth_or_env_notes:
            when_not_to_use.append(tool.auth_or_env_notes)
        when_not_to_use.extend(tool.usage_warnings)

        argument_template = build_argument_template(tool, include_optional=True, variant=0)
        minimal_example = build_argument_template(tool, include_optional=False, variant=0)
        full_example = build_argument_template(tool, include_optional=True, variant=1)

        examples = []
        if minimal_example:
            examples.append(
                {
                    "scenario": f"Minimal valid request that satisfies the required fields for {tool.tool_name}",
                    "arguments": minimal_example,
                }
            )
        if full_example:
            examples.append(
                {
                    "scenario": f"Richer invocation that uses optional controls for {tool.tool_name}",
                    "arguments": full_example,
                }
            )

        base_skill = GeneratedSkill(
            baseline_name="autoskill_base",
            skill_summary=summary,
            when_to_use=when_to_use,
            when_not_to_use=when_not_to_use,
            argument_template=argument_template,
            examples=examples,
        )
        candidates = build_enhanced_skill_candidates(tool, base_skill)
        if self.ablation_mode == "base_only":
            return base_skill
        if self.ablation_mode in {"semantic_concise", "semantic_dense"}:
            selected = next(candidate["skill"] for candidate in candidates if candidate["label"] == self.ablation_mode)
            selected.method_trace = [
                {
                    "selected_label": self.ablation_mode,
                    "selection_strategy": "forced_ablation_mode",
                }
            ]
            return selected
        return select_best_skill_candidate(tool, candidates)


class OpenAICompatibleBackend(GenerationBackend):
    backend_name = "openai_compatible"

    def __init__(
        self,
        api_url: str,
        model: str,
        api_key: str | None = None,
        timeout_seconds: int = 60,
        prompt_template_id: str = "compact_default",
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.prompt_template_id = prompt_template_id

    def _post_json(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        request = urllib.request.Request(
            url=f"{self.api_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}),
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def generate_skill(self, tool: ToolIR) -> GeneratedSkill:
        prompt = build_generation_prompt(tool, template_id=self.prompt_template_id)
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You generate schema-faithful JSON skill packages for MCP tools.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        response = self._post_json(payload)
        content = response["choices"][0]["message"]["content"]
        skill = parse_generated_skill_output(content, template_id=self.prompt_template_id, tool=tool)
        if not skill.metadata.get("parse_ok"):
            raise ValueError(skill.metadata.get("parse_error") or "Malformed generated skill output")
        return skill


class LocalHFBackend(GenerationBackend):
    backend_name = "local_hf"

    def __init__(
        self,
        model_name_or_path: str,
        device: str | None = None,
        device_map: str | None = None,
        torch_dtype: str | None = None,
        max_new_tokens: int = 768,
        trust_remote_code: bool = False,
        attn_implementation: str | None = None,
        load_in_4bit: bool = False,
        load_in_8bit: bool = False,
        generation_kwargs: Dict[str, Any] | None = None,
        prompt_template_id: str = "compact_default",
    ) -> None:
        self.prompt_template_id = prompt_template_id
        self.runner = LocalHFChatRunner(
            model_name_or_path=model_name_or_path,
            device=device,
            device_map=device_map,
            torch_dtype=torch_dtype,
            max_new_tokens=max_new_tokens,
            trust_remote_code=trust_remote_code,
            attn_implementation=attn_implementation,
            load_in_4bit=load_in_4bit,
            load_in_8bit=load_in_8bit,
            generation_kwargs=generation_kwargs,
        )

    def generate_skill(self, tool: ToolIR) -> GeneratedSkill:
        prompt = build_generation_prompt(tool, template_id=self.prompt_template_id)
        content = self.runner.generate_chat(
            [
                {"role": "system", "content": "You generate schema-faithful JSON skill packages for MCP tools."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        skill = parse_generated_skill_output(content, template_id=self.prompt_template_id, tool=tool)
        if not skill.metadata.get("parse_ok"):
            raise ValueError(skill.metadata.get("parse_error") or "Malformed generated skill output")
        return skill


def _append_generation_backend_trace(
    skill: GeneratedSkill,
    configured_backend: str,
    actual_backend: str,
    used_fallback: bool,
    fallback_reason: str | None = None,
) -> GeneratedSkill:
    skill.method_trace.append(
        {
            "trace_type": "generation_backend",
            "configured_generation_backend": configured_backend,
            "actual_generation_backend": actual_backend,
            "generation_fallback_used": used_fallback,
            "generation_fallback_reason": fallback_reason,
        }
    )
    return skill


def build_backend_from_env() -> GenerationBackend:
    api_url = os.getenv("AUTOSKILL_API_URL")
    model = os.getenv("AUTOSKILL_MODEL")
    api_key = os.getenv("AUTOSKILL_API_KEY")
    if api_url and model:
        return OpenAICompatibleBackend(api_url=api_url, model=model, api_key=api_key)
    return HeuristicBackend()


def build_backend_from_config(config: Dict[str, Any] | None) -> GenerationBackend:
    if not config:
        return build_backend_from_env()

    backend_type = config.get("type", "heuristic")
    prompt_template_id = config.get("prompt_template_id") or config.get("template_id")
    if backend_type == "heuristic":
        return HeuristicBackend(
            ablation_mode=str(config.get("ablation_mode", "selected")),
            prompt_template_id=str(prompt_template_id) if prompt_template_id else None,
        )
    if backend_type == "openai_compatible":
        api_key = config.get("api_key")
        api_key_env = config.get("api_key_env")
        if api_key_env and not api_key:
            api_key = os.getenv(str(api_key_env))
        return OpenAICompatibleBackend(
            api_url=str(config["api_url"]),
            model=str(config["model"]),
            api_key=api_key,
            timeout_seconds=int(config.get("timeout_seconds", 60)),
            prompt_template_id=str(prompt_template_id or "compact_default"),
        )
    if backend_type == "local_hf":
        return LocalHFBackend(
            model_name_or_path=str(config["model_name_or_path"]),
            device=config.get("device"),
            device_map=config.get("device_map"),
            torch_dtype=config.get("torch_dtype"),
            max_new_tokens=int(config.get("max_new_tokens", 768)),
            trust_remote_code=bool(config.get("trust_remote_code", False)),
            attn_implementation=config.get("attn_implementation"),
            load_in_4bit=bool(config.get("load_in_4bit", False)),
            load_in_8bit=bool(config.get("load_in_8bit", False)),
            generation_kwargs=config.get("generation_kwargs"),
            prompt_template_id=str(prompt_template_id or "compact_default"),
        )
    raise ValueError(f"Unsupported generation backend type: {backend_type}")


def safe_generate_skill(tool: ToolIR, backend: GenerationBackend) -> GeneratedSkill:
    try:
        skill = backend.generate_skill(tool)
        return _append_generation_backend_trace(
            skill,
            configured_backend=backend.backend_name,
            actual_backend=backend.backend_name,
            used_fallback=False,
        )
    except (
        ImportError,
        KeyError,
        RuntimeError,
        ValueError,
        TypeError,
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
    ) as exc:
        fallback_skill = HeuristicBackend().generate_skill(tool)
        return _append_generation_backend_trace(
            fallback_skill,
            configured_backend=backend.backend_name,
            actual_backend=HeuristicBackend.backend_name,
            used_fallback=True,
            fallback_reason=f"{type(exc).__name__}: {exc}",
        )

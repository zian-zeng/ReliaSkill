from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Any, Dict

from autoskill.eval_types import EvalPrediction, EvalTask
from autoskill.exposure import render_exposure
from autoskill.ir import GeneratedSkill, ToolIR
from autoskill.json_output import parse_json_object_output
from autoskill.local_model import LocalHFChatRunner
from autoskill.prompting import build_prediction_prompt


def _extract_number(text: str) -> int | None:
    match = re.search(r"\b(\d+)\b", text)
    return int(match.group(1)) if match else None


def _extract_quoted_or_tail(text: str) -> str:
    quoted = re.search(r'"([^"]+)"', text)
    if quoted:
        return quoted.group(1)
    tail = re.search(r"\bfor\b(.+)", text, flags=re.IGNORECASE)
    if tail:
        return tail.group(1).strip(" .")
    return text.strip(" .")


def _extract_path_from_request(text: str) -> str | None:
    patterns = [
        r"\b(?:of|inside|in|under|within)\s+(?:the\s+)?([A-Za-z0-9_./*-]+?)(?:\s+directory\b|\s+folder\b|\s+using\b|\s+with\b|\s+for\b|$)",
        r"\b(?:read|open|show)\s+([A-Za-z0-9_./-]+\.[A-Za-z0-9_*?-]+)\b",
        r"\bcreate\s+(?:the\s+)?directory\s+([A-Za-z0-9_./-]+)",
        r"\bcreate\s+([A-Za-z0-9_./-]+)\s+containing",
        r"\b(?:save|write)\s+.+\s+to\s+([A-Za-z0-9_./-]+)$",
        r"\bensure\s+([A-Za-z0-9_./-]+)\s+exists\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip(" .")
    return None


def _extract_content_from_request(text: str) -> str | None:
    for pattern in (
        r"\bcontaining the text\s+(.+)$",
        r"\bwith content\s+(.+)$",
        r'\b(?:save|write)\s+"([^"]+)"\s+to\s+[A-Za-z0-9_./-]+$',
    ):
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip().strip(".").strip('"')
    return None


def _extract_pattern_from_request(text: str) -> str | None:
    match = re.search(r"\bpattern\s+([A-Za-z0-9_./*?-]+)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip(" .")
    quoted = re.search(r'"([^"]*(?:\*|\?)[^"]*)"', text)
    if quoted:
        return quoted.group(1)
    return None


def _extract_exclude_patterns(text: str) -> list[str]:
    match = re.search(r"\b(?:exclude|ignore|skip)\s+([A-Za-z0-9_./*?\-, ]+)", text, flags=re.IGNORECASE)
    if not match:
        return []
    raw_value = match.group(1).strip(" .")
    parts = re.split(r"\s*(?:,|and)\s*", raw_value)
    return [part.strip(" .") for part in parts if part.strip(" .")]


def _infer_semantic_hint_value(tool: ToolIR, arg_name: str, request: str, skill: GeneratedSkill) -> Any:
    lowered = request.lower()
    semantic_spec = skill.semantic_hints.get(arg_name)

    if isinstance(semantic_spec, dict):
        number = _extract_number(lowered)
        for cue, mapped_value in semantic_spec.items():
            if cue not in lowered:
                continue
            if mapped_value == "__number__" and number is not None:
                return number
            if mapped_value == "__paths__":
                extracted = _extract_exclude_patterns(request)
                if extracted:
                    return extracted
            if mapped_value == "__tail_text__":
                extracted = _extract_content_from_request(request)
                if extracted is not None:
                    return extracted
            if mapped_value == "__quoted_text_to_path__":
                extracted = _extract_content_from_request(request)
                if extracted is not None:
                    return extracted
            if mapped_value not in {"__number__", "__paths__", "__tail_text__", "__quoted_text_to_path__"}:
                return mapped_value

    return None


def _infer_argument_value(arg_name: str, request: str, skill: GeneratedSkill) -> Any:
    lowered = request.lower()
    if arg_name == "city":
        for city in ("new york", "san francisco", "boston", "seattle", "london"):
            if city in lowered:
                return city.title()
        return None
    if arg_name == "unit":
        if "fahrenheit" in lowered or " f " in f" {lowered} ":
            return "F"
        if "celsius" in lowered or " centigrade" in lowered or " c " in f" {lowered} ":
            return "C"
        return skill.argument_template.get("unit")
    if arg_name == "include_forecast":
        return any(token in lowered for token in ("forecast", "next few hours", "outlook"))
    if arg_name == "query":
        return _extract_quoted_or_tail(request)
    if arg_name == "top_k":
        value = _extract_number(lowered)
        return value if value is not None else skill.argument_template.get("top_k")
    if arg_name == "path":
        return _extract_path_from_request(request)
    if arg_name == "head":
        if "first" in lowered:
            return _extract_number(lowered)
        return None
    if arg_name == "tail":
        if "last" in lowered:
            return _extract_number(lowered)
        return None
    if arg_name == "content":
        return _extract_content_from_request(request)
    if arg_name == "pattern":
        return _extract_pattern_from_request(request)
    if arg_name == "excludePatterns":
        extracted = _extract_exclude_patterns(request)
        return extracted if extracted else None
    return skill.argument_template.get(arg_name)


class PredictorBackend(ABC):
    backend_name = "base"

    @abstractmethod
    def predict(self, tool: ToolIR, skill: GeneratedSkill, task: EvalTask) -> EvalPrediction:
        raise NotImplementedError


class HeuristicPredictorBackend(PredictorBackend):
    backend_name = "heuristic"

    def predict(self, tool: ToolIR, skill: GeneratedSkill, task: EvalTask) -> EvalPrediction:
        predicted = {}
        for arg in tool.arguments:
            if arg.default is not None:
                predicted[arg.name] = arg.default

        for arg in tool.arguments:
            value = _infer_argument_value(arg.name, task.user_request, skill)
            if value is None and skill.semantic_hints:
                value = _infer_semantic_hint_value(tool, arg.name, task.user_request, skill)
            if value is None:
                if arg.required and arg.name not in predicted:
                    fallback = skill.argument_template.get(arg.name)
                    if fallback is None:
                        continue
                    predicted[arg.name] = fallback
                    continue
                if not arg.required:
                    continue
            else:
                predicted[arg.name] = value

        if skill.baseline_name == "raw_mcp":
            optional_names = {arg.name for arg in tool.arguments if not arg.required}
            predicted = {
                key: value
                for key, value in predicted.items()
                if key not in optional_names or value not in (None, False)
            }

        return EvalPrediction(
            task_id=task.task_id,
            tool_name=task.tool_name,
            baseline_name=skill.baseline_name,
            predicted_arguments=predicted,
            exposure_text=render_exposure(tool, skill),
        )


class OpenAICompatiblePredictorBackend(PredictorBackend):
    backend_name = "openai_compatible"

    def __init__(
        self,
        api_url: str,
        model: str,
        api_key: str | None = None,
        timeout_seconds: int = 60,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

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

    def predict(self, tool: ToolIR, skill: GeneratedSkill, task: EvalTask) -> EvalPrediction:
        prompt = build_prediction_prompt(tool, skill, task.user_request)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You produce only JSON tool arguments for MCP tool calls."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
        response = self._post_json(payload)
        content = response["choices"][0]["message"]["content"]
        data = parse_json_object_output(content)
        predicted_arguments = dict(data.get("arguments", {}))
        return EvalPrediction(
            task_id=task.task_id,
            tool_name=task.tool_name,
            baseline_name=skill.baseline_name,
            predicted_arguments=predicted_arguments,
            exposure_text=render_exposure(tool, skill),
        )


class LocalHFPredictorBackend(PredictorBackend):
    backend_name = "local_hf"

    def __init__(
        self,
        model_name_or_path: str,
        device: str | None = None,
        device_map: str | None = None,
        torch_dtype: str | None = None,
        max_new_tokens: int = 512,
        trust_remote_code: bool = False,
        attn_implementation: str | None = None,
        load_in_4bit: bool = False,
        load_in_8bit: bool = False,
        generation_kwargs: Dict[str, Any] | None = None,
    ) -> None:
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

    def predict(self, tool: ToolIR, skill: GeneratedSkill, task: EvalTask) -> EvalPrediction:
        prompt = build_prediction_prompt(tool, skill, task.user_request)
        content = self.runner.generate_chat(
            [
                {"role": "system", "content": "You produce only JSON tool arguments for MCP tool calls."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
        data = parse_json_object_output(content)
        predicted_arguments = dict(data.get("arguments", {}))
        return EvalPrediction(
            task_id=task.task_id,
            tool_name=task.tool_name,
            baseline_name=skill.baseline_name,
            predicted_arguments=predicted_arguments,
            exposure_text=render_exposure(tool, skill),
        )


def build_predictor_from_env() -> PredictorBackend:
    api_url = os.getenv("AUTOSKILL_PREDICT_API_URL") or os.getenv("AUTOSKILL_API_URL")
    model = os.getenv("AUTOSKILL_PREDICT_MODEL") or os.getenv("AUTOSKILL_MODEL")
    api_key = os.getenv("AUTOSKILL_PREDICT_API_KEY") or os.getenv("AUTOSKILL_API_KEY")
    if api_url and model:
        return OpenAICompatiblePredictorBackend(api_url=api_url, model=model, api_key=api_key)
    return HeuristicPredictorBackend()


def build_predictor_from_config(config: Dict[str, Any] | None) -> PredictorBackend:
    if not config:
        return build_predictor_from_env()

    backend_type = config.get("type", "heuristic")
    if backend_type == "heuristic":
        return HeuristicPredictorBackend()
    if backend_type == "openai_compatible":
        api_key = config.get("api_key")
        api_key_env = config.get("api_key_env")
        if api_key_env and not api_key:
            api_key = os.getenv(str(api_key_env))
        return OpenAICompatiblePredictorBackend(
            api_url=str(config["api_url"]),
            model=str(config["model"]),
            api_key=api_key,
            timeout_seconds=int(config.get("timeout_seconds", 60)),
        )
    if backend_type == "local_hf":
        return LocalHFPredictorBackend(
            model_name_or_path=str(config["model_name_or_path"]),
            device=config.get("device"),
            device_map=config.get("device_map"),
            torch_dtype=config.get("torch_dtype"),
            max_new_tokens=int(config.get("max_new_tokens", 512)),
            trust_remote_code=bool(config.get("trust_remote_code", False)),
            attn_implementation=config.get("attn_implementation"),
            load_in_4bit=bool(config.get("load_in_4bit", False)),
            load_in_8bit=bool(config.get("load_in_8bit", False)),
            generation_kwargs=config.get("generation_kwargs"),
        )
    raise ValueError(f"Unsupported predictor backend type: {backend_type}")


def safe_predict(tool: ToolIR, skill: GeneratedSkill, task: EvalTask, backend: PredictorBackend) -> EvalPrediction:
    try:
        return backend.predict(tool, skill, task)
    except (ImportError, KeyError, RuntimeError, ValueError, TypeError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return HeuristicPredictorBackend().predict(tool, skill, task)

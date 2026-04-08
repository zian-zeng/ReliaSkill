from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List


class LocalHFChatRunner:
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
        self.model_name_or_path = model_name_or_path
        self.device = device
        self.device_map = device_map
        self.torch_dtype = torch_dtype
        self.max_new_tokens = max_new_tokens
        self.trust_remote_code = trust_remote_code
        self.attn_implementation = attn_implementation
        self.load_in_4bit = load_in_4bit
        self.load_in_8bit = load_in_8bit
        self.generation_kwargs = deepcopy(generation_kwargs) if generation_kwargs else {}
        self._tokenizer = None
        self._model = None

        if self.load_in_4bit and self.load_in_8bit:
            raise ValueError("Only one of load_in_4bit or load_in_8bit can be enabled.")

    def _resolve_torch_dtype(self, torch_module: Any) -> Any:
        if not self.torch_dtype:
            return None
        return getattr(torch_module, self.torch_dtype, None)

    def _load(self) -> None:
        if self._tokenizer is not None and self._model is not None:
            return

        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise ImportError(
                "Local Hugging Face backend requires `transformers` to be installed."
            ) from exc

        try:
            import torch
        except ImportError as exc:
            raise ImportError(
                "Local Hugging Face backend requires `torch` to be installed."
            ) from exc

        self._tokenizer = AutoTokenizer.from_pretrained(
            self.model_name_or_path,
            trust_remote_code=self.trust_remote_code,
        )
        model_kwargs: Dict[str, Any] = {}
        resolved_dtype = self._resolve_torch_dtype(torch)
        if resolved_dtype is not None:
            model_kwargs["torch_dtype"] = resolved_dtype
        if self.attn_implementation:
            model_kwargs["attn_implementation"] = self.attn_implementation
        if self.load_in_4bit:
            model_kwargs["load_in_4bit"] = True
        if self.load_in_8bit:
            model_kwargs["load_in_8bit"] = True

        effective_device_map = self.device_map
        if effective_device_map is None and self.device in {"auto", "cuda"}:
            effective_device_map = self.device
        if effective_device_map:
            model_kwargs["device_map"] = effective_device_map

        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_name_or_path,
            trust_remote_code=self.trust_remote_code,
            **model_kwargs,
        )
        if self.device == "cpu":
            self._model.to("cpu")

    def _render_prompt(self, messages: List[Dict[str, str]]) -> str:
        self._load()
        tokenizer = self._tokenizer
        if hasattr(tokenizer, "apply_chat_template"):
            return tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        parts = []
        for message in messages:
            role = message.get("role", "user").upper()
            content = message.get("content", "")
            parts.append(f"{role}: {content}")
        parts.append("ASSISTANT:")
        return "\n".join(parts)

    def generate_chat(self, messages: List[Dict[str, str]], temperature: float = 0.0) -> str:
        self._load()

        tokenizer = self._tokenizer
        model = self._model
        prompt = self._render_prompt(messages)
        inputs = tokenizer(prompt, return_tensors="pt")
        if hasattr(model, "device"):
            inputs = {key: value.to(model.device) for key, value in inputs.items()}

        generation_kwargs = dict(self.generation_kwargs)
        generation_kwargs.setdefault("max_new_tokens", self.max_new_tokens)
        generation_kwargs.setdefault("do_sample", temperature > 0)
        if temperature > 0:
            generation_kwargs.setdefault("temperature", temperature)
        if tokenizer.eos_token_id is not None:
            generation_kwargs.setdefault("pad_token_id", tokenizer.eos_token_id)

        generated = model.generate(**inputs, **generation_kwargs)
        prompt_length = inputs["input_ids"].shape[1]
        output_ids = generated[0][prompt_length:]
        return tokenizer.decode(output_ids, skip_special_tokens=True).strip()

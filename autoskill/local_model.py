from __future__ import annotations

import gc
from copy import deepcopy
from typing import Any, Dict, List

_GLOBAL_MODEL_CACHE: Dict[str, Any] = {}


def clear_model_cache() -> None:
    """Release cached local HF models between sequential cluster model runs."""
    for entry in list(_GLOBAL_MODEL_CACHE.values()):
        entry.clear()
    _GLOBAL_MODEL_CACHE.clear()
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


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

        cache_key = f"{self.model_name_or_path}_{self.load_in_4bit}_{self.load_in_8bit}_{self.device}_{self.device_map}"
        if cache_key in _GLOBAL_MODEL_CACHE:
            self._tokenizer = _GLOBAL_MODEL_CACHE[cache_key]["tokenizer"]
            self._model = _GLOBAL_MODEL_CACHE[cache_key]["model"]
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
        from transformers import BitsAndBytesConfig
        
        model_kwargs: Dict[str, Any] = {}
        resolved_dtype = self._resolve_torch_dtype(torch)
        if resolved_dtype is not None:
            model_kwargs["torch_dtype"] = resolved_dtype
        if self.attn_implementation:
            model_kwargs["attn_implementation"] = self.attn_implementation
        
        if self.load_in_4bit or self.load_in_8bit:
            model_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=self.load_in_4bit,
                load_in_8bit=self.load_in_8bit,
                bnb_4bit_compute_dtype=resolved_dtype or torch.float16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
            )

        effective_device_map = self.device_map
        if effective_device_map is None and self.device in {"auto", "cuda"}:
            effective_device_map = "auto"
        if effective_device_map:
            model_kwargs["device_map"] = effective_device_map

        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_name_or_path,
            trust_remote_code=self.trust_remote_code,
            **model_kwargs,
        )
        if self.device == "cpu":
            self._model.to("cpu")

        _GLOBAL_MODEL_CACHE[cache_key] = {
            "tokenizer": self._tokenizer,
            "model": self._model,
        }

    def _render_prompt(self, messages: List[Dict[str, str]]) -> str:
        self._load()
        tokenizer = self._tokenizer
        if hasattr(tokenizer, "apply_chat_template"):
            try:
                return tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )
            except Exception as e:
                if "System role not supported" in str(e) or "system" in str(e).lower():
                    new_messages = []
                    system_content = ""
                    for msg in messages:
                        if msg["role"] == "system":
                            system_content += msg["content"] + "\n\n"
                        elif msg["role"] == "user":
                            new_messages.append({"role": "user", "content": system_content + msg["content"]})
                            system_content = ""
                        else:
                            new_messages.append(msg)
                    return tokenizer.apply_chat_template(
                        new_messages,
                        tokenize=False,
                        add_generation_prompt=True,
                    )
                raise e
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
        
        # Memory optimization: Truncate input if it's too long
        max_context = 2048
        if inputs["input_ids"].shape[1] > max_context:
            inputs["input_ids"] = inputs["input_ids"][:, -max_context:]
            if "attention_mask" in inputs:
                inputs["attention_mask"] = inputs["attention_mask"][:, -max_context:]

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

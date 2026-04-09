from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from typing import Any, Dict, List


def load_json_config(path: str | Path) -> Dict[str, Any]:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Experiment config must be a JSON object.")
    return data


def _merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dicts(merged[key], value)
        elif value is not None:
            merged[key] = value
    return merged


def merge_experiment_config(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    return _merge_dicts(base, override)


def _resolve_path(base_dir: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value)
    if not path.is_absolute():
        candidates = [
            (base_dir / path),
            (Path.cwd() / path),
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate.resolve()
        return candidates[1].resolve()
    return path.resolve()


def _preflight_backend(name: str, backend_config: Dict[str, Any] | None) -> Dict[str, Any]:
    backend_config = backend_config or {"type": "heuristic"}
    backend_type = str(backend_config.get("type", "heuristic"))
    errors: List[str] = []
    warnings: List[str] = []

    if backend_type == "heuristic":
        return {"backend_name": name, "backend_type": backend_type, "ready": True, "errors": [], "warnings": []}

    if backend_type == "openai_compatible":
        if not backend_config.get("api_url"):
            errors.append(f"{name}: `api_url` is required for openai_compatible backend.")
        if not backend_config.get("model"):
            errors.append(f"{name}: `model` is required for openai_compatible backend.")
        api_key_env = backend_config.get("api_key_env")
        if api_key_env and not os.getenv(str(api_key_env)) and not backend_config.get("api_key"):
            warnings.append(f"{name}: environment variable `{api_key_env}` is not set.")
        return {
            "backend_name": name,
            "backend_type": backend_type,
            "ready": not errors,
            "errors": errors,
            "warnings": warnings,
        }

    if backend_type == "local_hf":
        if not backend_config.get("model_name_or_path"):
            errors.append(f"{name}: `model_name_or_path` is required for local_hf backend.")
        if backend_config.get("load_in_4bit") and backend_config.get("load_in_8bit"):
            errors.append(f"{name}: only one of `load_in_4bit` or `load_in_8bit` can be enabled.")
        if importlib.util.find_spec("transformers") is None:
            warnings.append(f"{name}: `transformers` is not installed in the current environment.")
        if importlib.util.find_spec("torch") is None:
            warnings.append(f"{name}: `torch` is not installed in the current environment.")
        return {
            "backend_name": name,
            "backend_type": backend_type,
            "ready": not errors,
            "errors": errors,
            "warnings": warnings,
        }

    errors.append(f"{name}: unsupported backend type `{backend_type}`.")
    return {
        "backend_name": name,
        "backend_type": backend_type,
        "ready": False,
        "errors": errors,
        "warnings": warnings,
    }


def validate_experiment_config(config: Dict[str, Any], config_path: str | Path | None = None) -> Dict[str, Any]:
    base_dir = Path(config_path).resolve().parent if config_path else Path.cwd()
    errors: List[str] = []
    warnings: List[str] = []

    required_fields = ["tools_path", "tasks_path", "output_root"]
    for field_name in required_fields:
        if not config.get(field_name):
            errors.append(f"Missing required config field `{field_name}`.")

    resolved_tools = _resolve_path(base_dir, config.get("tools_path"))
    resolved_tasks = _resolve_path(base_dir, config.get("tasks_path"))
    resolved_output = _resolve_path(base_dir, config.get("output_root"))

    if resolved_tools and not resolved_tools.exists():
        errors.append(f"tools_path does not exist: {resolved_tools}")
    if resolved_tasks and not resolved_tasks.exists():
        errors.append(f"tasks_path does not exist: {resolved_tasks}")
    if resolved_output and resolved_output.exists() and not resolved_output.is_dir():
        errors.append(f"output_root exists but is not a directory: {resolved_output}")

    generator_preflight = _preflight_backend("generator", config.get("generator"))
    predictor_preflight = _preflight_backend("predictor", config.get("predictor"))
    errors.extend(generator_preflight["errors"])
    errors.extend(predictor_preflight["errors"])
    warnings.extend(generator_preflight["warnings"])
    warnings.extend(predictor_preflight["warnings"])

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "resolved_paths": {
            "tools_path": str(resolved_tools) if resolved_tools else "",
            "tasks_path": str(resolved_tasks) if resolved_tasks else "",
            "output_root": str(resolved_output) if resolved_output else "",
        },
        "backend_preflight": {
            "generator": generator_preflight,
            "predictor": predictor_preflight,
        },
    }

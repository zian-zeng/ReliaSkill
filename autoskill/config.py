from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from typing import Any, Dict, List

import yaml

from autoskill.conditions import is_reliaskill_v1_family


def load_json_config(path: str | Path) -> Dict[str, Any]:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as f:
        if config_path.suffix.lower() in {".yaml", ".yml"}:
            data = yaml.safe_load(f)
        else:
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
    _check_reliaskill_v1_config(
        config,
        base_dir=base_dir,
        resolved_tasks=resolved_tasks,
        errors=errors,
        warnings=warnings,
    )

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


def _check_reliaskill_v1_config(
    config: Dict[str, Any],
    *,
    base_dir: Path,
    resolved_tasks: Path | None,
    errors: List[str],
    warnings: List[str],
) -> None:
    conditions = {str(item) for item in config.get("conditions") or []}
    if not any(is_reliaskill_v1_family(condition) for condition in conditions):
        return

    shared = config.get("shared_skill_packages")
    if not isinstance(shared, dict) or not shared:
        errors.append("`reliaskill_v1` requires a `shared_skill_packages` block.")
        return

    dev_controls = _resolve_path(base_dir, shared.get("dev_controls_path"))
    if dev_controls is None:
        errors.append("`reliaskill_v1` requires `shared_skill_packages.dev_controls_path` for dev-only selection.")
    elif not dev_controls.exists():
        errors.append(f"shared_skill_packages.dev_controls_path does not exist: {dev_controls}")
    elif resolved_tasks is not None and dev_controls == resolved_tasks:
        errors.append("`reliaskill_v1` dev_controls_path must differ from tasks_path to avoid dev/test leakage.")

    if not shared.get("root"):
        warnings.append("`reliaskill_v1` shared_skill_packages.root is not set; package artifacts may be rebuilt into a run-local path.")
    reliability_predictor = shared.get("reliability_predictor")
    if not isinstance(reliability_predictor, dict):
        errors.append("`reliaskill_v1` requires `shared_skill_packages.reliability_predictor` for dev behavior selection.")
    else:
        reliability_preflight = _preflight_backend("reliaskill_v1.reliability_predictor", reliability_predictor)
        errors.extend(reliability_preflight["errors"])
        warnings.extend(reliability_preflight["warnings"])
    repair_rounds = _int_or_none(shared.get("max_repair_rounds", 0))
    if repair_rounds is None:
        errors.append("`reliaskill_v1` shared_skill_packages.max_repair_rounds must be an integer when provided.")
    elif repair_rounds < 1:
        warnings.append("`reliaskill_v1` max_repair_rounds is less than 1; repair evidence will be absent.")

    skills = config.get("skills") if isinstance(config.get("skills"), dict) else {}
    if not skills.get("multi_candidate_config"):
        errors.append("`reliaskill_v1` requires `skills.multi_candidate_config` for candidate selection.")


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

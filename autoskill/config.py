from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


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

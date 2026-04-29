from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from autoskill.prompting import build_generation_prompt


AUDIT_SCHEMA_VERSION = "reliaskill_audit_v1"


def canonical_json(value: Any) -> str:
    return json.dumps(_to_plain(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def get_git_commit_hash() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path.cwd(),
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except OSError:
        pass
    return "unknown"


def collect_hardware_info() -> Dict[str, Any]:
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
    }


def backend_model_name(config: Dict[str, Any] | None, default: str = "heuristic") -> str:
    config = config or {"type": default}
    if config.get("type") == "local_hf":
        return str(config.get("model_name_or_path", "local_hf"))
    if config.get("type") == "openai_compatible":
        return str(config.get("model", "openai_compatible"))
    return str(config.get("model", config.get("type", default)))


def backend_quantization(config: Dict[str, Any] | None) -> str:
    config = config or {}
    if config.get("load_in_4bit"):
        return "4bit"
    if config.get("load_in_8bit"):
        return "8bit"
    return str(config.get("torch_dtype") or config.get("quantization") or "none")


def build_run_manifest(
    *,
    run_type: str,
    output_root: str | Path,
    config: Dict[str, Any],
    seed: int = 42,
    generator_config: Dict[str, Any] | None = None,
    predictor_config: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    config_hash = stable_hash(config)
    started_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    run_id = f"{run_type}_{started_at.replace(':', '').replace('+', 'Z')}_{config_hash[:12]}_{uuid.uuid4().hex[:8]}"
    return {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "run_id": run_id,
        "run_type": run_type,
        "started_at_utc": started_at,
        "git_commit_hash": get_git_commit_hash(),
        "config_hash": config_hash,
        "seed": int(seed),
        "model_name": {
            "generator": backend_model_name(generator_config),
            "predictor": backend_model_name(predictor_config),
        },
        "quantization": {
            "generator": backend_quantization(generator_config),
            "predictor": backend_quantization(predictor_config),
        },
        "hardware": collect_hardware_info(),
        "config": _to_plain(config),
        "output_root": str(output_root),
        "audit_jsonl": str(Path(output_root) / "audit_records.jsonl"),
        "manifest_path": str(Path(output_root) / "manifest.json"),
    }


def write_manifest(output_root: str | Path, manifest: Dict[str, Any]) -> None:
    out = Path(output_root)
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(json.dumps(_to_plain(manifest), indent=2, ensure_ascii=False), encoding="utf-8")


def write_jsonl(path: str | Path, records: Iterable[Dict[str, Any]]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(canonical_json(record) + "\n")


def append_jsonl(path: str | Path, records: Iterable[Dict[str, Any]]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as f:
        for record in records:
            f.write(canonical_json(record) + "\n")


def generation_audit_record(manifest: Dict[str, Any], tool: Any, skill: Any, validation_report: Any, artifact_path: str | Path) -> Dict[str, Any]:
    prompt = build_generation_prompt(tool)
    skill_payload = _dump_model(skill)
    return _base_record(manifest, "skill_generation") | {
        "tool_name": getattr(tool, "tool_name", ""),
        "condition": getattr(skill, "baseline_name", ""),
        "task_id": None,
        "user_request": None,
        "prompt_template": "build_generation_prompt/v1",
        "raw_prompt": prompt,
        "raw_model_output": json.dumps(skill_payload, ensure_ascii=False, sort_keys=True),
        "parsed_prediction": None,
        "generated_skill": skill_payload,
        "validation_report": _dump_model(validation_report),
        "behavior_report": None,
        "repair_report": None,
        "reliability_score": None,
        "source_artifact_path": str(artifact_path),
    }


def prediction_audit_record(
    manifest: Dict[str, Any],
    score: Dict[str, Any],
    validation_report: Any | None = None,
    behavior_report: Any | None = None,
    repair_report: Any | None = None,
    reliability_score: Any | None = None,
    artifact_path: str | Path | None = None,
) -> Dict[str, Any]:
    metadata = score.get("prediction_metadata", {}) if isinstance(score, dict) else {}
    return _base_record(manifest, "prediction") | {
        "tool_name": score.get("tool_name"),
        "condition": score.get("baseline_name"),
        "task_id": score.get("task_id"),
        "split": score.get("split"),
        "user_request": score.get("user_request"),
        "prompt_template": metadata.get("prompt_template"),
        "raw_prompt": metadata.get("raw_prompt"),
        "raw_model_output": metadata.get("raw_model_output"),
        "parsed_prediction": metadata.get("parsed_prediction", score.get("predicted_arguments")),
        "prediction": score.get("predicted_arguments"),
        "gold_label": score.get("expected_arguments"),
        "validation_report": _dump_model(validation_report),
        "behavior_report": _dump_model(behavior_report),
        "repair_report": _dump_model(repair_report),
        "reliability_score": _dump_model(reliability_score),
        "score": _to_plain(score),
        "source_artifact_path": str(artifact_path) if artifact_path else None,
        "model_name": metadata.get("model_name") or manifest.get("model_name", {}).get("predictor"),
        "quantization": metadata.get("quantization") or manifest.get("quantization", {}).get("predictor"),
    }


def reliability_audit_records(
    manifest: Dict[str, Any],
    *,
    tool_name: str,
    condition: str,
    validation_report: Any,
    behavior_report: Any,
    repair_report: Any,
    reliability_score: Any,
    artifact_path: str | Path,
) -> List[Dict[str, Any]]:
    base_payload = _base_record(manifest, "reliability_artifact") | {
        "tool_name": tool_name,
        "condition": condition,
        "task_id": None,
        "user_request": None,
        "prompt_template": None,
        "raw_prompt": None,
        "raw_model_output": None,
        "parsed_prediction": None,
        "validation_report": _dump_model(validation_report),
        "behavior_report": _dump_model(behavior_report),
        "repair_report": _dump_model(repair_report),
        "reliability_score": _dump_model(reliability_score),
        "source_artifact_path": str(artifact_path),
    }
    records = [base_payload]
    behavior_payload = _dump_model(behavior_report) or {}
    for result in behavior_payload.get("results", []):
        metadata = result.get("prediction_metadata", {}) if isinstance(result, dict) else {}
        records.append(
            _base_record(manifest, "behavior_prediction") | {
                "tool_name": tool_name,
                "condition": condition,
                "task_id": result.get("case_id"),
                "split": result.get("split"),
                "user_request": result.get("user_request"),
                "prompt_template": metadata.get("prompt_template"),
                "raw_prompt": metadata.get("raw_prompt"),
                "raw_model_output": metadata.get("raw_model_output"),
                "parsed_prediction": metadata.get("parsed_prediction", result.get("predicted_arguments")),
                "prediction": result.get("predicted_arguments"),
                "gold_label": result.get("expected_arguments"),
                "validation_report": _dump_model(validation_report),
                "behavior_report": {"result": result, "metrics": behavior_payload.get("metrics", {})},
                "repair_report": _dump_model(repair_report),
                "reliability_score": _dump_model(reliability_score),
                "source_artifact_path": str(artifact_path),
                "model_name": metadata.get("model_name") or manifest.get("model_name", {}).get("predictor"),
                "quantization": metadata.get("quantization") or manifest.get("quantization", {}).get("predictor"),
            }
        )
    return records


def _base_record(manifest: Dict[str, Any], event_type: str) -> Dict[str, Any]:
    return {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "event_type": event_type,
        "run_id": manifest["run_id"],
        "git_commit_hash": manifest["git_commit_hash"],
        "config_hash": manifest["config_hash"],
        "seed": manifest["seed"],
        "model_name": manifest.get("model_name"),
        "quantization": manifest.get("quantization"),
        "hardware": manifest["hardware"],
        "manifest_path": manifest["manifest_path"],
    }


def _dump_model(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return _to_plain(value)


def _to_plain(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return _to_plain(value.model_dump())
    if is_dataclass(value):
        return _to_plain(asdict(value))
    if isinstance(value, dict):
        return {str(key): _to_plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value

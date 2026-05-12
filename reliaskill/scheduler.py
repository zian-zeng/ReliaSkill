from __future__ import annotations

import csv
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

import yaml

from autoskill.benchmark import load_benchmark_tasks
from autoskill.config import load_json_config
from autoskill.experiment import load_tools


DEFAULT_CONDITION_TOKEN_OVERHEAD = {
    "raw_mcp": 900,
    "schema_only": 450,
    "docs_only": 350,
    "generated_skill_base": 300,
    "autoskill_base": 300,
    "skill_ultra_compact": 150,
    "skill_compact": 300,
    "skill_medium": 600,
    "skill_verbose": 1200,
    "generated_docs_verbose": 1200,
    "raw_docs_full": 1600,
    "raw_schema_plus_examples": 950,
    "generated_docs_no_validation": 900,
    "repaired_skill": 450,
    "gated_skill": 475,
    "multi_candidate_skill_k3_validation_select": 350,
    "multi_candidate_skill_k3_behavior_select": 400,
    "multi_candidate_repaired_gated": 450,
    "skill_prompt_compact_default": 300,
    "skill_prompt_boundary_first": 350,
    "skill_prompt_example_rich": 500,
    "skill_prompt_safety_aware": 400,
    "skill_prompt_verbose_docs": 1200,
}


@dataclass
class ModelConfig:
    config_path: str
    model_name: str
    model_path: str
    tokenizer_path: str
    backend: str
    quantization: str
    load_in_4bit: bool
    torch_dtype: str
    device_map: str
    max_new_tokens: int
    temperature: float
    batch_size: int
    max_prompt_tokens: int
    estimated_vram_gb: float
    examples_per_second: float

    def model_dump(self) -> Dict[str, Any]:
        return {
            "config_path": self.config_path,
            "model_name": self.model_name,
            "model_path": self.model_path,
            "tokenizer_path": self.tokenizer_path,
            "backend": self.backend,
            "quantization": self.quantization,
            "load_in_4bit": self.load_in_4bit,
            "torch_dtype": self.torch_dtype,
            "device_map": self.device_map,
            "max_new_tokens": self.max_new_tokens,
            "temperature": self.temperature,
            "batch_size": self.batch_size,
            "max_prompt_tokens": self.max_prompt_tokens,
            "estimated_vram_gb": self.estimated_vram_gb,
            "examples_per_second": self.examples_per_second,
        }


def load_yaml_or_json(path: str | Path) -> Dict[str, Any]:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as f:
        if config_path.suffix.lower() in {".yaml", ".yml"}:
            data = yaml.safe_load(f) or {}
        else:
            data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Config must be a mapping: {config_path}")
    return data


def load_model_config(path_or_mapping: str | Path | Dict[str, Any]) -> ModelConfig:
    if isinstance(path_or_mapping, dict):
        raw = dict(path_or_mapping)
        config_path = str(raw.get("config_path") or "")
    else:
        config_path = str(path_or_mapping)
        raw = load_yaml_or_json(path_or_mapping)
    model_name = str(raw.get("model_name") or raw.get("model") or raw.get("model_name_or_path") or raw.get("model_path") or "unknown_model")
    model_path = str(raw.get("model_path") or raw.get("model_name_or_path") or model_name)
    tokenizer_path = str(raw.get("tokenizer_path") or model_path)
    backend = str(raw.get("backend") or raw.get("type") or "local_hf")
    lower_name = model_name.lower()
    batch_size = raw.get("batch_size")
    if batch_size is None:
        batch_size = 1 if "7b" in lower_name else 2
    return ModelConfig(
        config_path=config_path,
        model_name=model_name,
        model_path=model_path,
        tokenizer_path=tokenizer_path,
        backend=backend,
        quantization=str(raw.get("quantization") or ("4bit" if raw.get("load_in_4bit") else "none")),
        load_in_4bit=bool(raw.get("load_in_4bit", False)),
        torch_dtype=str(raw.get("torch_dtype") or "float16"),
        device_map=str(raw.get("device_map") or "auto"),
        max_new_tokens=int(raw.get("max_new_tokens") or 256),
        temperature=float(raw.get("temperature") if raw.get("temperature") is not None else 0.0),
        batch_size=int(batch_size),
        max_prompt_tokens=int(raw.get("max_prompt_tokens") or 4096),
        estimated_vram_gb=float(raw.get("estimated_vram_gb") or 0.0),
        examples_per_second=float(raw.get("examples_per_second") or raw.get("estimated_examples_per_second") or 0.25),
    )


def plan_experiment_run(
    config_path: str | Path,
    *,
    gpu_budget_gb: float,
    output_report: str | Path = "outputs/reports/run_plan.md",
    output_csv: str | Path = "outputs/tables/run_plan.csv",
    shard_index: int | None = None,
    num_shards: int | None = None,
    strict: bool = False,
) -> Dict[str, Any]:
    config = load_json_config(config_path)
    plan = build_run_plan(
        config,
        config_path=Path(config_path),
        gpu_budget_gb=float(gpu_budget_gb),
        shard_index=shard_index,
        num_shards=num_shards,
        strict=strict,
    )
    write_run_plan_csv(output_csv, plan["runs"])
    Path(output_report).parent.mkdir(parents=True, exist_ok=True)
    Path(output_report).write_text(build_run_plan_markdown(plan), encoding="utf-8")
    plan["output_report"] = str(output_report)
    plan["output_csv"] = str(output_csv)
    return plan


def build_run_plan(
    config: Dict[str, Any],
    *,
    config_path: Path | None = None,
    gpu_budget_gb: float = 12.0,
    shard_index: int | None = None,
    num_shards: int | None = None,
    strict: bool = False,
) -> Dict[str, Any]:
    scheduler_config = dict(config.get("scheduler") or {})
    tools_path = config["tools_path"]
    tasks_path = config["tasks_path"]
    output_root = Path(str(config.get("output_root") or "outputs/experiment"))
    tools = load_tools(tools_path)
    raw_domain_map = _load_tool_domain_map(tools_path)
    tasks = load_benchmark_tasks(tasks_path)
    conditions = [str(item) for item in config.get("conditions") or scheduler_config.get("conditions") or ["generated_skill_base"]]
    tool_names = sorted(tools)
    configured_max_tools = _configured_max_tools(config)
    if configured_max_tools:
        tool_names = tool_names[:configured_max_tools]
    selected_tools = _select_sharded_tools(tool_names, shard_index, num_shards)
    selected_tool_set = set(selected_tools)
    selected_tasks = [task for task in tasks if task.tool_name in selected_tool_set]
    model_configs = _load_models(config, base_dir=config_path.resolve().parent if config_path else Path.cwd())
    examples_per_second_default = float(scheduler_config.get("examples_per_second") or 0.25)
    max_batch_size = int(scheduler_config.get("max_batch_size") or 2)
    prompt_safety_margin = int(scheduler_config.get("prompt_safety_margin_tokens") or 256)
    include_routing = bool(scheduler_config.get("include_routing", False))
    resume = bool(scheduler_config.get("resume", True))
    errors: List[str] = []
    warnings: List[str] = []
    runs: List[Dict[str, Any]] = []
    target_tools = _optional_int(config.get("target_tools"))
    target_domains = _optional_int(config.get("target_domains"))
    if target_tools and len(selected_tools) < target_tools:
        warnings.append(f"Configured target_tools={target_tools}, but current tools_path provides {len(selected_tools)} selected tools.")
    if target_domains:
        observed_domains = _observed_domains(tools, selected_tools, raw_domain_map)
        if len(observed_domains) < target_domains:
            warnings.append(
                f"Configured target_domains={target_domains}, but current tools_path provides {len(observed_domains)} selected domains."
            )

    for model in sorted(model_configs, key=lambda item: item.model_name):
        model_errors, model_warnings = _model_guard_messages(model, gpu_budget_gb=gpu_budget_gb, max_batch_size=max_batch_size)
        errors.extend(model_errors)
        warnings.extend(model_warnings)
        model_eps = model.examples_per_second or examples_per_second_default
        for condition in conditions:
            total_examples = len(selected_tasks)
            completed_examples = _count_completed_predictions(output_root, selected_tasks, condition, resume=resume)
            remaining_examples = max(0, total_examples - completed_examples)
            max_request_tokens = max((_estimate_text_tokens(task.user_request) for task in selected_tasks), default=0)
            condition_overhead = _condition_token_overhead(condition, scheduler_config)
            estimated_prompt_tokens = max_request_tokens + condition_overhead + prompt_safety_margin
            prompt_guard_ok = estimated_prompt_tokens <= model.max_prompt_tokens
            if not prompt_guard_ok:
                message = (
                    f"{model.model_name}/{condition}: estimated prompt tokens {estimated_prompt_tokens} "
                    f"exceed max_prompt_tokens {model.max_prompt_tokens}."
                )
                if strict:
                    errors.append(message)
                else:
                    warnings.append(message)
            token_volume = remaining_examples * (estimated_prompt_tokens + model.max_new_tokens)
            estimated_seconds = remaining_examples / model_eps if model_eps > 0 else math.inf
            runs.append(
                {
                    "model_name": model.model_name,
                    "model_path": model.model_path,
                    "backend": model.backend,
                    "quantization": model.quantization,
                    "estimated_vram_gb": model.estimated_vram_gb,
                    "gpu_budget_gb": gpu_budget_gb,
                    "condition": condition,
                    "shard_index": shard_index if shard_index is not None else "",
                    "num_shards": num_shards if num_shards is not None else "",
                    "num_tools": len(selected_tools),
                    "total_examples": total_examples,
                    "completed_examples": completed_examples,
                    "remaining_examples": remaining_examples,
                    "estimated_model_calls": remaining_examples,
                    "estimated_prompt_tokens_per_call": estimated_prompt_tokens,
                    "max_prompt_tokens": model.max_prompt_tokens,
                    "prompt_guard_ok": prompt_guard_ok,
                    "max_new_tokens": model.max_new_tokens,
                    "estimated_token_volume": token_volume,
                    "batch_size": model.batch_size,
                    "examples_per_second": model_eps,
                    "estimated_runtime_seconds": round(estimated_seconds, 2) if math.isfinite(estimated_seconds) else "",
                    "estimated_runtime_hours": round(estimated_seconds / 3600.0, 4) if math.isfinite(estimated_seconds) else "",
                    "resume_enabled": resume,
                    "routing_enabled": include_routing,
                    "status": "blocked" if model_errors or not prompt_guard_ok else "ready",
                    "plan_note": "run all listed conditions for this model before unloading",
                }
            )

    total_remaining_calls = sum(int(row["estimated_model_calls"]) for row in runs if row["status"] != "blocked")
    total_token_volume = sum(int(row["estimated_token_volume"]) for row in runs if row["status"] != "blocked")
    total_seconds = sum(float(row["estimated_runtime_seconds"] or 0.0) for row in runs if row["status"] != "blocked")
    estimated_disk_gb = _estimate_disk_usage_gb(total_remaining_calls, total_token_volume, scheduler_config)
    grouped_order = _grouped_model_order(runs)
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "config_path": str(config_path) if config_path else "",
        "tools_path": str(tools_path),
        "tasks_path": str(tasks_path),
        "output_root": str(output_root),
        "gpu_budget_gb": gpu_budget_gb,
        "conditions": conditions,
        "models": [model.model_dump() for model in model_configs],
        "num_models": len(model_configs),
        "num_conditions": len(conditions),
        "num_tools": len(selected_tools),
        "num_tasks": len(selected_tasks),
        "shard_index": shard_index,
        "num_shards": num_shards,
        "model_execution_order": grouped_order,
        "total_remaining_model_calls": total_remaining_calls,
        "total_token_volume": total_token_volume,
        "estimated_disk_usage_gb": estimated_disk_gb,
        "estimated_runtime_seconds": round(total_seconds, 2),
        "estimated_runtime_hours": round(total_seconds / 3600.0, 4),
        "runs": runs,
        "dry_run": True,
        "experiment_scale": config.get("experiment_scale", ""),
        "target_tools": config.get("target_tools", ""),
        "target_domains": config.get("target_domains", ""),
        "positives_per_tool": config.get("positives_per_tool", ""),
        "negatives_per_tool": config.get("negatives_per_tool", ""),
        "routing_candidate_sizes": config.get("routing_candidate_sizes", []),
    }


def write_run_plan_csv(path: str | Path, rows: Sequence[Dict[str, Any]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "model_name",
        "backend",
        "quantization",
        "estimated_vram_gb",
        "gpu_budget_gb",
        "condition",
        "shard_index",
        "num_shards",
        "num_tools",
        "total_examples",
        "completed_examples",
        "remaining_examples",
        "estimated_model_calls",
        "estimated_prompt_tokens_per_call",
        "max_prompt_tokens",
        "prompt_guard_ok",
        "max_new_tokens",
        "estimated_token_volume",
        "batch_size",
        "examples_per_second",
        "estimated_runtime_seconds",
        "estimated_runtime_hours",
        "resume_enabled",
        "routing_enabled",
        "status",
        "plan_note",
    ]
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in headers})


def build_run_plan_markdown(plan: Dict[str, Any]) -> str:
    lines = [
        "# ReliaSkill One-GPU Run Plan",
        "",
        f"- Dry run only: `{plan.get('dry_run', True)}`",
        f"- GPU budget: `{plan['gpu_budget_gb']} GB`",
        f"- Tools: `{plan['num_tools']}`",
        f"- Tasks: `{plan['num_tasks']}`",
        f"- Models: `{plan['num_models']}`",
        f"- Conditions: `{plan['num_conditions']}`",
        f"- Remaining model calls: `{plan['total_remaining_model_calls']}`",
        f"- Estimated token volume: `{plan['total_token_volume']}`",
        f"- Estimated disk usage: `{plan.get('estimated_disk_usage_gb', 0.0)} GB`",
        f"- Estimated runtime: `{plan['estimated_runtime_hours']} h`",
        "",
        "## Execution Order",
    ]
    for model_name in plan.get("model_execution_order", []):
        lines.append(f"- Load `{model_name}`, run all planned conditions, then unload before the next model.")
    if plan.get("errors"):
        lines.extend(["", "## Blocking Errors"])
        lines.extend(f"- {error}" for error in plan["errors"])
    if plan.get("warnings"):
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in plan["warnings"])
    lines.extend(
        [
            "",
            "## Runs",
            "| Model | Condition | Remaining Calls | Prompt Tokens | Batch | VRAM GB | Runtime h | Status |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in plan["runs"]:
        lines.append(
            f"| {row['model_name']} | {row['condition']} | {row['remaining_examples']} | "
            f"{row['estimated_prompt_tokens_per_call']} | {row['batch_size']} | "
            f"{row['estimated_vram_gb']} | {row['estimated_runtime_hours']} | {row['status']} |"
        )
    return "\n".join(lines) + "\n"


def _load_models(config: Dict[str, Any], *, base_dir: Path) -> List[ModelConfig]:
    raw_models = config.get("models") or config.get("model_configs") or []
    if not raw_models:
        generator = config.get("predictor") or config.get("generator") or {"backend": "heuristic", "model_name": "heuristic"}
        raw_models = [generator]
    models = []
    for raw in raw_models:
        if isinstance(raw, str):
            path = Path(raw)
            if not path.is_absolute():
                candidates = [base_dir / path, Path.cwd() / path]
                path = next((candidate for candidate in candidates if candidate.exists()), candidates[-1])
            models.append(load_model_config(path))
        elif isinstance(raw, dict):
            if raw.get("config"):
                path = Path(str(raw["config"]))
                if not path.is_absolute():
                    candidates = [base_dir / path, Path.cwd() / path]
                    path = next((candidate for candidate in candidates if candidate.exists()), candidates[-1])
                model = load_model_config(path)
                override = dict(raw)
                override.pop("config", None)
                if override:
                    model_dict = model.model_dump()
                    model_dict.update(override)
                    models.append(load_model_config(model_dict))
                else:
                    models.append(model)
            else:
                models.append(load_model_config(raw))
        else:
            raise ValueError(f"Unsupported model entry: {raw!r}")
    return models


def _select_sharded_tools(tool_names: List[str], shard_index: int | None, num_shards: int | None) -> List[str]:
    if shard_index is None and num_shards is None:
        return tool_names
    if shard_index is None or num_shards is None:
        raise ValueError("shard_index and num_shards must be provided together.")
    if num_shards <= 0:
        raise ValueError("num_shards must be positive.")
    if shard_index < 0 or shard_index >= num_shards:
        raise ValueError("shard_index must be in [0, num_shards).")
    return [name for index, name in enumerate(tool_names) if index % num_shards == shard_index]


def _model_guard_messages(model: ModelConfig, *, gpu_budget_gb: float, max_batch_size: int) -> tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    if model.estimated_vram_gb and model.estimated_vram_gb > gpu_budget_gb:
        errors.append(
            f"{model.model_name}: estimated VRAM {model.estimated_vram_gb} GB exceeds available budget {gpu_budget_gb} GB."
        )
    if model.batch_size > max_batch_size:
        errors.append(f"{model.model_name}: batch_size {model.batch_size} exceeds scheduler max_batch_size {max_batch_size}.")
    if "7b" in model.model_name.lower() and model.batch_size != 1:
        errors.append(f"{model.model_name}: 7B local runs must use batch_size=1 to reduce OOM risk.")
    if model.backend in {"local_hf", "transformers"} and not model.load_in_4bit and "7b" in model.model_name.lower():
        warnings.append(f"{model.model_name}: 7B model is not marked load_in_4bit; this may exceed a 12 GB budget.")
    return errors, warnings


def _count_completed_predictions(output_root: Path, tasks: Iterable[Any], condition: str, *, resume: bool) -> int:
    if not resume:
        return 0
    count = 0
    for task in tasks:
        result_path = output_root / "benchmark" / task.tool_name / condition / f"{task.task_id}.result.json"
        if result_path.exists():
            count += 1
    return count


def _estimate_text_tokens(text: str) -> int:
    return len(re.findall(r"\w+|[^\w\s]", text or ""))


def _condition_token_overhead(condition: str, scheduler_config: Dict[str, Any]) -> int:
    custom = scheduler_config.get("condition_token_overheads") or {}
    if condition in custom:
        return int(custom[condition])
    return int(DEFAULT_CONDITION_TOKEN_OVERHEAD.get(condition, 400))


def _configured_max_tools(config: Dict[str, Any]) -> int | None:
    data_config = config.get("data") if isinstance(config.get("data"), dict) else {}
    for value in (data_config.get("max_tools"), config.get("max_tools")):
        parsed = _optional_int(value)
        if parsed and parsed > 0:
            return parsed
    return None


def _observed_domains(tools: Dict[str, Any], selected_tool_names: Sequence[str], raw_domain_map: Dict[str, str] | None = None) -> set[str]:
    raw_domain_map = raw_domain_map or {}
    domains = set()
    for name in selected_tool_names:
        if raw_domain_map.get(name):
            domains.add(raw_domain_map[name])
            continue
        tool = tools.get(name)
        if tool is None:
            continue
        schema_complexity = getattr(tool, "schema_complexity", {}) or {}
        provenance = getattr(tool, "provenance", {}) or {}
        domain = (
            getattr(tool, "domain", None)
            or schema_complexity.get("domain")
            or provenance.get("domain")
            or provenance.get("source_category")
            or "unknown"
        )
        domains.add(str(domain))
    return domains


def _load_tool_domain_map(path: str | Path) -> Dict[str, str]:
    input_path = Path(path)
    if not input_path.exists():
        return {}
    domains: Dict[str, str] = {}
    try:
        with input_path.open("r", encoding="utf-8") as f:
            if input_path.suffix.lower() == ".json":
                payload = json.load(f)
                records = payload if isinstance(payload, list) else []
            else:
                records = [json.loads(line) for line in f if line.strip()]
    except (OSError, json.JSONDecodeError):
        return {}
    for record in records:
        if not isinstance(record, dict):
            continue
        name = str(record.get("tool_name") or record.get("name") or "")
        meta = record.get("source_metadata") if isinstance(record.get("source_metadata"), dict) else {}
        domain = record.get("domain") or meta.get("domain") or meta.get("source_category")
        if name and domain:
            domains[name] = str(domain)
    return domains


def _optional_int(value: Any) -> int | None:
    try:
        if value in {None, ""}:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _grouped_model_order(runs: Sequence[Dict[str, Any]]) -> List[str]:
    order: List[str] = []
    for row in runs:
        model = str(row["model_name"])
        if model not in order:
            order.append(model)
    return order


def _estimate_disk_usage_gb(total_calls: int, total_token_volume: int, scheduler_config: Dict[str, Any]) -> float:
    bytes_per_call = int(scheduler_config.get("estimated_bytes_per_call") or 4096)
    bytes_per_token = float(scheduler_config.get("estimated_bytes_per_token") or 1.25)
    fixed_overhead_bytes = int(scheduler_config.get("estimated_fixed_output_overhead_bytes") or 50_000_000)
    total_bytes = fixed_overhead_bytes + (total_calls * bytes_per_call) + int(total_token_volume * bytes_per_token)
    return round(total_bytes / (1024 ** 3), 4)

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence

from autoskill.benchmark import load_benchmark_tasks
from autoskill.config import load_json_config
from autoskill.experiment import load_tools
from reliaskill.cluster import (
    _balanced_tasks_for_tools,
    _live_execution_enabled,
    _load_config_models,
    _selected_live_tasks,
    selected_tool_names,
    slugify,
)


@dataclass(frozen=True)
class TaskRef:
    task_id: str
    tool_name: str


@dataclass(frozen=True)
class ProgressPlan:
    config_path: Path
    output_root: Path
    model_slugs: List[str]
    model_names: Dict[str, str]
    conditions: List[str]
    tasks_by_shard: Dict[int, List[TaskRef]]
    benchmark_total: int
    routing_total: int
    live_total: int

    @property
    def total(self) -> int:
        return self.benchmark_total + self.routing_total + self.live_total


def build_progress_plan(
    config_path: str | Path,
    *,
    output_root: str | Path | None = None,
    num_shards: int | None = None,
    models: Sequence[str] | None = None,
    skip_routing: bool = False,
) -> ProgressPlan:
    config_path = Path(config_path)
    config = load_json_config(config_path)
    root = Path(output_root or config.get("output_root") or "outputs/emnlp_acceptance")
    all_tools = load_tools(config["tools_path"])
    full_names = selected_tool_names(config, all_tools)
    full_tasks = _balanced_tasks_for_tools(config, load_benchmark_tasks(config["tasks_path"]), full_names)
    shard_count = int(num_shards or _infer_num_shards(root) or 1)
    tasks_by_shard: Dict[int, List[TaskRef]] = {}
    for shard_index in range(shard_count):
        shard_names = set(selected_tool_names(config, all_tools, shard_index=shard_index, num_shards=shard_count))
        tasks_by_shard[shard_index] = [
            TaskRef(task_id=str(task.task_id), tool_name=str(task.tool_name))
            for task in full_tasks
            if task.tool_name in shard_names
        ]

    model_configs = _load_config_models(config, base_dir=config_path.resolve().parent)
    if models:
        requested = {str(item) for item in models}
        model_configs = [
            model for model in model_configs
            if model.model_name in requested or slugify(model.model_name) in requested or model.config_path in requested
        ]
    model_names = {slugify(model.model_name): model.model_name for model in model_configs}
    conditions = [str(item) for item in config.get("conditions") or []]
    model_count = len(model_configs)
    condition_count = len(conditions)
    benchmark_total = model_count * len(full_tasks) * condition_count
    include_routing = bool((config.get("scheduler") or {}).get("include_routing", False)) and not skip_routing
    routing_total = benchmark_total if include_routing else 0
    live_total = 0
    if _live_execution_enabled(config):
        live_total = model_count * len(_selected_live_tasks(config)) * condition_count
    return ProgressPlan(
        config_path=config_path,
        output_root=root,
        model_slugs=list(model_names),
        model_names=model_names,
        conditions=conditions,
        tasks_by_shard=tasks_by_shard,
        benchmark_total=benchmark_total,
        routing_total=routing_total,
        live_total=live_total,
    )


def scan_progress(plan: ProgressPlan) -> Dict[str, Any]:
    root = plan.output_root
    benchmark_completed, benchmark_ignored = _count_phase_records(
        root / "predictors",
        "benchmark",
        "*.result.json",
        "prediction_records.jsonl",
        plan=plan,
    )
    routing_completed, routing_ignored = _count_phase_records(
        root / "predictors",
        "routing_benchmark",
        "*.routing.json",
        "routing_records.jsonl",
        plan=plan,
    )
    live_completed, live_ignored = _count_phase_records(
        root / "predictors",
        "live_exec",
        "*.live_result.json",
        "live_exec_results.jsonl",
        plan=plan,
        filter_tasks=False,
    )
    states = _load_state_rows(plan)
    if not states:
        states = _infer_state_rows(plan)
    benchmark_visible = min(benchmark_completed, plan.benchmark_total)
    routing_visible = min(routing_completed, plan.routing_total)
    live_visible = min(live_completed, plan.live_total)
    completed = benchmark_visible + routing_visible + live_visible
    return {
        "config_path": str(plan.config_path),
        "output_root": str(root),
        "total": plan.total,
        "completed": completed,
        "benchmark": {"completed": benchmark_visible, "total": plan.benchmark_total},
        "routing": {"completed": routing_visible, "total": plan.routing_total},
        "live": {"completed": live_visible, "total": plan.live_total},
        "ignored_records": {
            "benchmark": benchmark_ignored,
            "routing": routing_ignored,
            "live": live_ignored,
            "total": benchmark_ignored + routing_ignored + live_ignored,
        },
        "current": states,
    }


def _infer_num_shards(root: Path) -> int | None:
    shard_indices = set()
    for shard_dir in (root / "predictors").glob("*/shard_*"):
        try:
            shard_indices.add(int(shard_dir.name.split("_", 1)[1]))
        except (IndexError, ValueError):
            continue
    if not shard_indices:
        return None
    return max(shard_indices) + 1


def _count_phase_records(
    predictors_root: Path,
    phase_dir: str,
    pattern: str,
    jsonl_name: str,
    *,
    plan: ProgressPlan,
    task_ids: set[str] | None = None,
    filter_tasks: bool = True,
) -> tuple[int, int]:
    if not predictors_root.exists():
        return 0, 0
    keys: set[tuple[str, str, str, str, str]] = set()
    for shard_root in sorted(path for path in predictors_root.glob("*/shard_*") if path.is_dir()):
        phase_root = shard_root / phase_dir
        _collect_jsonl_record_keys(phase_root / jsonl_name, phase_dir=phase_dir, model_slug=shard_root.parent.name, keys=keys)
        if phase_root.exists():
            for path in phase_root.glob(f"**/{pattern}"):
                _collect_json_record_key(path, phase_dir=phase_dir, model_slug=shard_root.parent.name, keys=keys)
    allowed_task_ids = task_ids if task_ids is not None else _planned_task_ids(plan) if filter_tasks else None
    included = {
        key
        for key in keys
        if _record_key_matches_plan(key, plan=plan, task_ids=allowed_task_ids)
    }
    return len(included), len(keys) - len(included)


def _collect_jsonl_record_keys(
    path: Path,
    *,
    phase_dir: str,
    model_slug: str,
    keys: set[tuple[str, str, str, str, str]],
) -> None:
    if not path.exists():
        return
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                keys.add(_record_key(record, phase_dir=phase_dir, model_slug=model_slug))
    except OSError:
        return


def _collect_json_record_key(
    path: Path,
    *,
    phase_dir: str,
    model_slug: str,
    keys: set[tuple[str, str, str, str, str]],
) -> None:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    keys.add(_record_key(record, phase_dir=phase_dir, model_slug=model_slug))


def _record_key(record: Dict[str, Any], *, phase_dir: str, model_slug: str) -> tuple[str, str, str, str, str]:
    task_id = str(record.get("live_task_id") or record.get("task_id") or "")
    baseline = str(record.get("baseline_name") or record.get("condition") or "")
    tool_name = str(record.get("tool_name") or record.get("expected_tool_name") or "")
    return (str(record.get("model_slug") or model_slug), phase_dir, task_id, baseline, tool_name)


def _planned_task_ids(plan: ProgressPlan) -> set[str]:
    return {task.task_id for tasks in plan.tasks_by_shard.values() for task in tasks}


def _record_key_matches_plan(
    key: tuple[str, str, str, str, str],
    *,
    plan: ProgressPlan,
    task_ids: set[str] | None,
) -> bool:
    model_slug, _phase_dir, task_id, baseline, _tool_name = key
    if plan.model_slugs and model_slug and model_slug not in set(plan.model_slugs):
        return False
    if baseline and plan.conditions and baseline not in set(plan.conditions):
        return False
    if task_ids is not None and task_id and task_id not in task_ids:
        return False
    return True


def _load_state_rows(plan: ProgressPlan) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for state_path in sorted((plan.output_root / "predictors").glob("*/shard_*/progress/*_state.json")):
        try:
            payload = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        shard_name = state_path.parents[1].name
        model_slug = state_path.parents[2].name
        try:
            shard_index = int(shard_name.split("_", 1)[1])
        except (IndexError, ValueError):
            shard_index = payload.get("shard_index")
        rows.append(
            {
                "model_slug": model_slug,
                "model_name": plan.model_names.get(model_slug, model_slug),
                "shard_index": shard_index,
                "phase": payload.get("phase"),
                "status": payload.get("status"),
                "task_id": payload.get("task_id"),
                "tool_name": payload.get("tool_name"),
                "condition": payload.get("condition"),
                "updated_at": payload.get("updated_at"),
                "source": "heartbeat",
            }
        )
    return rows


def _infer_state_rows(plan: ProgressPlan) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    condition_count = max(1, len(plan.conditions))
    for model_slug in plan.model_slugs:
        model_root = plan.output_root / "predictors" / model_slug
        for shard_index, tasks in plan.tasks_by_shard.items():
            shard_root = model_root / f"shard_{shard_index:02d}"
            benchmark_done = _count_shard_phase_records(
                shard_root,
                "benchmark",
                "*.result.json",
                "prediction_records.jsonl",
                plan=plan,
                tasks=tasks,
            )
            routing_done = _count_shard_phase_records(
                shard_root,
                "routing_benchmark",
                "*.routing.json",
                "routing_records.jsonl",
                plan=plan,
                tasks=tasks,
            )
            phase = "done"
            completed_in_phase = benchmark_done
            phase_total = len(tasks) * condition_count
            if benchmark_done < phase_total:
                phase = "benchmark"
            elif plan.routing_total and routing_done < phase_total:
                phase = "routing"
                completed_in_phase = routing_done
            rows.append(_infer_row(plan, model_slug, shard_index, tasks, phase, completed_in_phase))
    return rows


def _infer_row(
    plan: ProgressPlan,
    model_slug: str,
    shard_index: int,
    tasks: List[TaskRef],
    phase: str,
    completed_in_phase: int,
) -> Dict[str, Any]:
    condition_count = max(1, len(plan.conditions))
    if phase == "done" or not tasks:
        return {
            "model_slug": model_slug,
            "model_name": plan.model_names.get(model_slug, model_slug),
            "shard_index": shard_index,
            "phase": phase,
            "status": "done",
            "task_id": None,
            "tool_name": None,
            "condition": None,
            "updated_at": None,
            "source": "inferred",
        }
    task_index = min(completed_in_phase // condition_count, len(tasks) - 1)
    condition_index = completed_in_phase % condition_count
    task = tasks[task_index]
    return {
        "model_slug": model_slug,
        "model_name": plan.model_names.get(model_slug, model_slug),
        "shard_index": shard_index,
        "phase": phase,
        "status": "next",
        "task_id": task.task_id,
        "tool_name": task.tool_name,
        "condition": plan.conditions[condition_index] if plan.conditions else None,
        "updated_at": None,
        "source": "inferred",
    }


def _count_shard_phase_records(
    shard_root: Path,
    phase_dir: str,
    pattern: str,
    jsonl_name: str,
    *,
    plan: ProgressPlan,
    tasks: Sequence[TaskRef],
) -> int:
    phase_root = shard_root / phase_dir
    keys: set[tuple[str, str, str, str, str]] = set()
    _collect_jsonl_record_keys(phase_root / jsonl_name, phase_dir=phase_dir, model_slug=shard_root.parent.name, keys=keys)
    if phase_root.exists():
        for path in phase_root.glob(f"**/{pattern}"):
            _collect_json_record_key(path, phase_dir=phase_dir, model_slug=shard_root.parent.name, keys=keys)
    task_ids = {task.task_id for task in tasks}
    return sum(1 for key in keys if _record_key_matches_plan(key, plan=plan, task_ids=task_ids))

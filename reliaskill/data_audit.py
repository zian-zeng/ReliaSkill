from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from autoskill.benchmark import load_benchmark_tasks
from autoskill.config import load_json_config
from autoskill.experiment import load_tools


def audit_dataset_integrity(config_path: str | Path) -> Dict[str, Any]:
    config = load_json_config(config_path)
    checks: List[Dict[str, Any]] = []

    tools_path = Path(str(config.get("tools_path") or ""))
    tasks_path = Path(str(config.get("tasks_path") or ""))
    dev_path = _dev_controls_path(config)
    if not tools_path.exists() or not tasks_path.exists():
        _add_check(
            checks,
            "dataset_paths_exist",
            "fail",
            False,
            "Configured tools_path and tasks_path must exist.",
            {"tools_path": str(tools_path), "tasks_path": str(tasks_path)},
        )
        return _report(config_path, config, checks, selected_task_count=0)

    raw_tools = _read_records(tools_path)
    raw_names = [_tool_name(record) for record in raw_tools]
    duplicate_tool_names = _duplicates(raw_names)
    _add_check(
        checks,
        "duplicate_raw_tool_names",
        "fail",
        not duplicate_tool_names,
        "Raw tool file has no duplicate tool names.",
        {"duplicates": duplicate_tool_names[:20], "num_duplicates": len(duplicate_tool_names)},
    )

    tools = load_tools(tools_path)
    selected_tools = _selected_tool_names(config, tools)
    tasks = load_benchmark_tasks(tasks_path)
    raw_test_task_ids = [str(task.task_id) for task in tasks]
    duplicate_raw_test_task_ids = _duplicates(raw_test_task_ids)
    _add_check(
        checks,
        "duplicate_test_task_ids",
        "fail",
        not duplicate_raw_test_task_ids,
        "Test controls have unique task IDs before sampling or balancing.",
        {"duplicates": duplicate_raw_test_task_ids[:20], "num_duplicates": len(duplicate_raw_test_task_ids)},
    )
    selected_tasks = _balanced_tasks_for_tools(config, tasks, selected_tools)
    selected_task_ids = [str(task.task_id) for task in selected_tasks]
    duplicate_task_ids = _duplicates(selected_task_ids)
    _add_check(
        checks,
        "duplicate_selected_test_task_ids",
        "fail",
        not duplicate_task_ids,
        "Selected test controls have unique task IDs.",
        {"duplicates": duplicate_task_ids[:20], "num_duplicates": len(duplicate_task_ids)},
    )

    task_tool_names = {task.tool_name for task in selected_tasks}
    missing_task_tools = sorted(task_tool_names - set(selected_tools))
    _add_check(
        checks,
        "test_control_tools_exist",
        "fail",
        not missing_task_tools,
        "Every selected test control references a selected tool.",
        {"missing_tools": missing_task_tools[:20], "num_missing": len(missing_task_tools)},
    )

    missing_coverage = _missing_coverage(config, selected_tasks, selected_tools)
    _add_check(
        checks,
        "test_control_coverage",
        "fail",
        not missing_coverage,
        "Every retained tool has configured positive and negative test coverage.",
        {"missing_or_undercovered": missing_coverage[:30], "num_undercovered": len(missing_coverage)},
    )

    if dev_path and dev_path.exists():
        dev_tasks = load_benchmark_tasks(dev_path)
        dev_ids = [str(task.task_id) for task in dev_tasks]
        duplicate_dev_ids = _duplicates(dev_ids)
        _add_check(
            checks,
            "duplicate_dev_task_ids",
            "fail",
            not duplicate_dev_ids,
            "Development controls have unique task IDs.",
            {"duplicates": duplicate_dev_ids[:20], "num_duplicates": len(duplicate_dev_ids)},
        )
        leakage = _request_overlap(dev_tasks, selected_tasks)
        _add_check(
            checks,
            "dev_test_request_leakage",
            "fail",
            not leakage,
            "Development and test controls do not reuse identical normalized requests.",
            {"overlap": leakage[:20], "num_overlap": len(leakage)},
        )
        dev_missing_tools = sorted({task.tool_name for task in dev_tasks} - set(tools))
        _add_check(
            checks,
            "dev_control_tools_exist",
            "fail",
            not dev_missing_tools,
            "Development controls for selected tools reference known tools.",
            {"missing_tools": dev_missing_tools[:20], "num_missing": len(dev_missing_tools)},
        )
    elif dev_path:
        _add_check(
            checks,
            "dev_controls_exist",
            "warn",
            False,
            "Configured development controls path was not found; skipped dev/test leakage check.",
            {"dev_controls_path": str(dev_path)},
        )
    else:
        _add_check(checks, "dev_controls_configured", "warn", False, "No development controls path configured.")

    duplicate_requests = _duplicates(_normalized_request(task.user_request) for task in selected_tasks)
    _add_check(
        checks,
        "duplicate_test_requests",
        "warn",
        not duplicate_requests,
        "Selected test controls do not repeat identical request strings.",
        {"duplicates": duplicate_requests[:20], "num_duplicates": len(duplicate_requests)},
    )

    return _report(config_path, config, checks, selected_task_count=len(selected_tasks), selected_tool_count=len(selected_tools))


def expected_sample_size_from_config(config_path: str | Path) -> int:
    report = audit_dataset_integrity(config_path)
    return int(report.get("selected_task_count") or 0)


def write_data_audit_report(report: Dict[str, Any], output_json: str | Path, output_md: str | Path | None = None) -> None:
    json_path = Path(output_json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    if output_md:
        md_path = Path(output_md)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(build_data_audit_markdown(report), encoding="utf-8")


def build_data_audit_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# ReliaSkill Dataset Integrity Audit",
        "",
        f"- Ready: `{'yes' if report['ok'] else 'no'}`",
        f"- Failures: `{report['num_failures']}`",
        f"- Warnings: `{report['num_warnings']}`",
        f"- Selected tools: `{report.get('selected_tool_count', 0)}`",
        f"- Selected controls: `{report.get('selected_task_count', 0)}`",
        "",
        "## Checks",
    ]
    for check in report["checks"]:
        status = "PASS" if check["passed"] else check["severity"].upper()
        lines.append(f"- `{status}` `{check['id']}`: {check['message']}")
        if check.get("details"):
            lines.append(f"  Details: `{json.dumps(check['details'], sort_keys=True)}`")
    return "\n".join(lines) + "\n"


def _report(
    config_path: str | Path,
    config: Dict[str, Any],
    checks: List[Dict[str, Any]],
    *,
    selected_task_count: int,
    selected_tool_count: int = 0,
) -> Dict[str, Any]:
    failures = [check for check in checks if check["severity"] == "fail" and not check["passed"]]
    warnings = [check for check in checks if check["severity"] == "warn" and not check["passed"]]
    return {
        "ok": not failures,
        "config_path": str(config_path),
        "tools_path": str(config.get("tools_path") or ""),
        "tasks_path": str(config.get("tasks_path") or ""),
        "selected_tool_count": selected_tool_count,
        "selected_task_count": selected_task_count,
        "num_checks": len(checks),
        "num_failures": len(failures),
        "num_warnings": len(warnings),
        "checks": checks,
    }


def _add_check(
    checks: List[Dict[str, Any]],
    check_id: str,
    severity: str,
    passed: bool,
    message: str,
    details: Dict[str, Any] | None = None,
) -> None:
    checks.append(
        {
            "id": check_id,
            "severity": severity,
            "passed": bool(passed),
            "message": message,
            "details": details or {},
        }
    )


def _read_records(path: Path) -> List[Dict[str, Any]]:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, list) else []
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                value = json.loads(line)
                if isinstance(value, dict):
                    records.append(value)
    return records


def _tool_name(record: Dict[str, Any]) -> str:
    return str(record.get("tool_name") or record.get("name") or "")


def _selected_tool_names(config: Dict[str, Any], tools: Dict[str, Any]) -> List[str]:
    names = sorted(tools)
    max_tools = _configured_max_tools(config)
    return names[:max_tools] if max_tools else names


def _configured_max_tools(config: Dict[str, Any]) -> int | None:
    data_config = config.get("data") if isinstance(config.get("data"), dict) else {}
    for value in (data_config.get("max_tools"), config.get("max_tools")):
        parsed = _optional_int(value)
        if parsed and parsed > 0:
            return parsed
    return None


def _balanced_tasks_for_tools(config: Dict[str, Any], tasks: Sequence[Any], tool_names: Sequence[str]) -> List[Any]:
    tool_set = set(tool_names)
    controls = config.get("controls") if isinstance(config.get("controls"), dict) else {}
    pos_limit = _optional_int(controls.get("positives_per_tool_total") or config.get("positives_per_tool"))
    neg_limit = _optional_int(controls.get("negatives_per_tool_total") or config.get("negatives_per_tool"))
    filtered = [task for task in tasks if task.tool_name in tool_set]
    if pos_limit is None and neg_limit is None:
        return filtered

    grouped: Dict[str, Dict[str, List[Any]]] = defaultdict(lambda: {"positive": [], "negative": []})
    for task in sorted(filtered, key=lambda item: str(item.task_id)):
        grouped[task.tool_name]["positive" if getattr(task, "should_trigger", True) else "negative"].append(task)

    selected: List[Any] = []
    for tool_name in sorted(tool_set):
        buckets = grouped.get(tool_name, {"positive": [], "negative": []})
        selected.extend(buckets["positive"][:pos_limit] if pos_limit is not None else buckets["positive"])
        selected.extend(buckets["negative"][:neg_limit] if neg_limit is not None else buckets["negative"])
    return sorted(selected, key=lambda item: str(item.task_id))


def _missing_coverage(config: Dict[str, Any], tasks: Sequence[Any], tool_names: Sequence[str]) -> List[Dict[str, Any]]:
    controls = config.get("controls") if isinstance(config.get("controls"), dict) else {}
    required_pos = _optional_int(controls.get("positives_per_tool_total") or config.get("positives_per_tool")) or 0
    required_neg = _optional_int(controls.get("negatives_per_tool_total") or config.get("negatives_per_tool")) or 0
    pos: Counter[str] = Counter()
    neg: Counter[str] = Counter()
    for task in tasks:
        if getattr(task, "should_trigger", True):
            pos[task.tool_name] += 1
        else:
            neg[task.tool_name] += 1
    missing = []
    for tool_name in sorted(tool_names):
        if pos[tool_name] < required_pos or neg[tool_name] < required_neg:
            missing.append({"tool_name": tool_name, "positive": pos[tool_name], "negative": neg[tool_name]})
    return missing


def _dev_controls_path(config: Dict[str, Any]) -> Path | None:
    shared = config.get("shared_skill_packages") if isinstance(config.get("shared_skill_packages"), dict) else {}
    value = shared.get("dev_controls_path") or config.get("dev_controls_path")
    return Path(str(value)) if value else None


def _request_overlap(left: Sequence[Any], right: Sequence[Any]) -> List[str]:
    left_requests = {_normalized_request(task.user_request) for task in left if _normalized_request(task.user_request)}
    right_requests = {_normalized_request(task.user_request) for task in right if _normalized_request(task.user_request)}
    return sorted(left_requests.intersection(right_requests))


def _normalized_request(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _duplicates(values: Iterable[str]) -> List[str]:
    counts = Counter(value for value in values if value)
    return sorted(value for value, count in counts.items() if count > 1)


def _optional_int(value: Any) -> int | None:
    try:
        if value in {None, ""}:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit ReliaSkill dataset integrity for acceptance-scale experiments.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, default=Path("outputs/reports/data_integrity_audit.json"))
    parser.add_argument("--output-md", type=Path, default=Path("outputs/reports/data_integrity_audit.md"))
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = audit_dataset_integrity(args.config)
    write_data_audit_report(report, args.output_json, args.output_md)
    print(json.dumps({"ok": report["ok"], "failures": report["num_failures"], "warnings": report["num_warnings"]}, sort_keys=True))
    return 1 if args.strict and not report["ok"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

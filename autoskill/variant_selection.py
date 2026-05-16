from __future__ import annotations

import hashlib
import json
import shutil
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


HELDOUT_SPLIT_MARKERS = {"test", "heldout", "holdout"}


@dataclass(frozen=True)
class VariantSelectionPolicy:
    structured_joint_weight: float = 1.0
    structured_positive_weight: float = 0.75
    routing_joint_weight: float = 0.75
    routing_tool_weight: float = 0.5
    negative_non_harm_weight: float = 1.0
    harm_penalty: float = 6.0
    tie_epsilon: float = 1e-9


DEFAULT_POLICY = VariantSelectionPolicy()


def load_dev_evidence(
    *,
    prediction_record_paths: Sequence[str | Path] = (),
    routing_record_paths: Sequence[str | Path] = (),
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    records: List[Dict[str, Any]] = []
    inputs: List[Dict[str, Any]] = []
    for path in prediction_record_paths:
        loaded, info = _load_jsonl_dev_only(Path(path), record_type="structured_call")
        records.extend(loaded)
        inputs.append(info)
    for path in routing_record_paths:
        loaded, info = _load_jsonl_dev_only(Path(path), record_type="routing")
        records.extend(loaded)
        inputs.append(info)
    if not records:
        raise ValueError("No dev evidence records were provided.")
    return records, inputs


def select_method_variant(
    records: Sequence[Dict[str, Any]],
    *,
    candidates: Sequence[str] | None = None,
    policy: VariantSelectionPolicy = DEFAULT_POLICY,
    selection_id: str | None = None,
    inputs: Sequence[Dict[str, Any]] = (),
) -> Dict[str, Any]:
    allowed = {str(item) for item in candidates or [] if str(item)}
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for index, record in enumerate(records, start=1):
        _assert_dev_split(record, source="<memory>", line_number=index)
        condition = _condition_name(record)
        if not condition:
            raise ValueError(f"Evidence record {index} does not identify a condition or baseline_name.")
        if allowed and condition not in allowed:
            continue
        grouped[condition].append(dict(record))
    if not grouped:
        suffix = f" among requested candidates {sorted(allowed)}" if allowed else ""
        raise ValueError(f"No dev evidence records were available for selection{suffix}.")

    scored = [_score_candidate(condition, items, policy) for condition, items in sorted(grouped.items())]
    scored.sort(key=lambda item: _selection_sort_key(item, policy))
    selected = scored[0]
    for rank, candidate in enumerate(scored, start=1):
        candidate["rank"] = rank
        candidate["selected"] = candidate["condition"] == selected["condition"]
        if not candidate["selected"]:
            candidate["not_selected_reason"] = _not_selected_reason(candidate, selected, policy)

    return {
        "schema_version": 1,
        "selection_id": selection_id or f"dev_variant_selection_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "selection_policy": asdict(policy),
        "dev_only": True,
        "heldout_controls_used": False,
        "test_controls_used": False,
        "inputs": list(inputs),
        "requested_candidates": sorted(allowed),
        "selected_condition": selected["condition"],
        "selected_score": selected["dev_selection_score"],
        "selected_complexity": selected["complexity"],
        "candidates": scored,
        "not_selected": [
            {
                "condition": item["condition"],
                "reason": item.get("not_selected_reason", ""),
                "score": item["dev_selection_score"],
                "complexity": item["complexity"],
            }
            for item in scored
            if not item.get("selected")
        ],
    }


def write_selection_manifest(manifest: Dict[str, Any], path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"Selection manifest already exists: {destination}")
    destination.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return destination


def apply_selection_manifest(
    *,
    manifest_path: str | Path,
    source_package_root: str | Path,
    output_package_root: str | Path,
    target_condition: str | None = None,
) -> Dict[str, Any]:
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    selected_condition = str(manifest.get("selected_condition") or "")
    if not selected_condition:
        raise ValueError(f"Selection manifest does not contain selected_condition: {manifest_path}")
    target = target_condition or selected_condition
    source_root = Path(source_package_root)
    output_root = Path(output_package_root)
    if not source_root.exists():
        raise FileNotFoundError(f"Source package root is missing: {source_root}")
    if output_root.exists():
        raise FileExistsError(f"Refusing to overwrite existing package output root: {output_root}")

    source_dirs = [path for path in sorted(source_root.iterdir()) if (path / selected_condition).is_dir()]
    if not source_dirs:
        raise FileNotFoundError(
            f"No packages for selected condition {selected_condition!r} under {source_root}."
        )

    copied: List[Dict[str, str]] = []
    for tool_dir in source_dirs:
        source_package = tool_dir / selected_condition
        target_package = output_root / tool_dir.name / target
        shutil.copytree(source_package, target_package)
        applied = {
            "selected_condition": selected_condition,
            "target_condition": target,
            "selection_id": str(manifest.get("selection_id") or ""),
            "source_package": str(source_package),
        }
        (target_package / "variant_selection.json").write_text(json.dumps(applied, indent=2), encoding="utf-8")
        copied.append(
            {
                "tool_dir": tool_dir.name,
                "source_package": str(source_package),
                "target_package": str(target_package),
            }
        )
    applied_manifest = {
        "selection_manifest": manifest,
        "source_package_root": str(source_root),
        "output_package_root": str(output_root),
        "target_condition": target,
        "copied_packages": copied,
    }
    (output_root / "selection_applied_manifest.json").write_text(
        json.dumps(applied_manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return applied_manifest


def _load_jsonl_dev_only(path: Path, *, record_type: str) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Required dev evidence file is missing: {path}")
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            text = line.strip()
            if not text:
                continue
            record = json.loads(text)
            if not isinstance(record, dict):
                raise ValueError(f"Expected JSON object at {path}:{line_number}.")
            _assert_dev_split(record, source=str(path), line_number=line_number)
            item = dict(record)
            item["record_type"] = record_type
            item["_source_path"] = str(path)
            records.append(item)
    return records, {
        "path": str(path),
        "record_type": record_type,
        "sha256": _sha256(path),
        "records": len(records),
    }


def _assert_dev_split(record: Dict[str, Any], *, source: str, line_number: int) -> None:
    split = str(record.get("split") or "").strip().lower()
    if split != "dev" or any(marker in split for marker in HELDOUT_SPLIT_MARKERS):
        raise ValueError(
            "Dev-only variant selection refuses non-dev evidence "
            f"at {source}:{line_number} (split={split!r})."
        )


def _score_candidate(
    condition: str,
    records: Sequence[Dict[str, Any]],
    policy: VariantSelectionPolicy,
) -> Dict[str, Any]:
    structured = [record for record in records if record.get("record_type") == "structured_call"]
    routing = [record for record in records if record.get("record_type") == "routing"]
    positives = [record for record in records if _should_trigger(record)]
    negatives = [record for record in records if not _should_trigger(record)]
    harmful = [record for record in negatives if _is_harmful_activation(record)]

    structured_joint = _mean(_joint_success(record) for record in structured)
    structured_positive = _mean(_joint_success(record) for record in structured if _should_trigger(record))
    routing_joint = _mean(_joint_success(record) for record in routing)
    routing_tool = _mean(_tool_success(record) for record in routing)
    negative_non_harm = _mean(1.0 if not _is_harmful_activation(record) else 0.0 for record in negatives)
    harm_rate = len(harmful) / len(negatives) if negatives else 0.0
    complexity = _mean(value for value in (_complexity(record) for record in records) if value is not None)

    score = (
        policy.structured_joint_weight * structured_joint
        + policy.structured_positive_weight * structured_positive
        + policy.routing_joint_weight * routing_joint
        + policy.routing_tool_weight * routing_tool
        + policy.negative_non_harm_weight * negative_non_harm
        - policy.harm_penalty * harm_rate
    )
    return {
        "condition": condition,
        "record_count": len(records),
        "structured_call_records": len(structured),
        "routing_records": len(routing),
        "positive_records": len(positives),
        "negative_records": len(negatives),
        "harmful_activations": len(harmful),
        "structured_joint_rate": round(structured_joint, 6),
        "structured_positive_success_rate": round(structured_positive, 6),
        "routing_joint_rate": round(routing_joint, 6),
        "routing_tool_accuracy": round(routing_tool, 6),
        "negative_non_harm_rate": round(negative_non_harm, 6),
        "harm_rate": round(harm_rate, 6),
        "complexity": round(complexity, 6),
        "dev_selection_score": round(score, 6),
    }


def _selection_sort_key(candidate: Dict[str, Any], policy: VariantSelectionPolicy) -> tuple[Any, ...]:
    return (
        -float(candidate["dev_selection_score"]),
        float(candidate["harm_rate"]),
        -float(candidate["negative_non_harm_rate"]),
        -float(candidate["structured_positive_success_rate"]),
        float(candidate["complexity"]),
        str(candidate["condition"]),
    )


def _not_selected_reason(
    candidate: Dict[str, Any],
    selected: Dict[str, Any],
    policy: VariantSelectionPolicy,
) -> str:
    score_gap = float(selected["dev_selection_score"]) - float(candidate["dev_selection_score"])
    if score_gap > policy.tie_epsilon:
        return f"lower dev utility score by {score_gap:.6f}"
    if float(candidate["complexity"]) > float(selected["complexity"]):
        return "tie lost to simpler/shorter artifact"
    return "tie lost to deterministic condition-name ordering"


def _condition_name(record: Dict[str, Any]) -> str:
    return str(record.get("baseline_name") or record.get("condition") or record.get("baseline") or "").strip()


def _should_trigger(record: Dict[str, Any]) -> bool:
    if "should_trigger" in record:
        return _as_bool(record.get("should_trigger"), default=True)
    expected = str(record.get("expected_tool_name") or "").strip()
    if expected == "__abstain__":
        return False
    return True


def _triggered(record: Dict[str, Any]) -> bool:
    if "triggered" in record:
        return _as_bool(record.get("triggered"), default=False)
    if "should_call" in record:
        return _as_bool(record.get("should_call"), default=False)
    selected = _selected_tool(record)
    if selected and selected != "__abstain__":
        return True
    return _should_trigger(record)


def _selected_tool(record: Dict[str, Any]) -> str:
    value = record.get("selected_tool_name")
    if value:
        return str(value)
    if record.get("triggered") is False or record.get("should_call") is False:
        return "__abstain__"
    if _should_trigger(record):
        return str(record.get("tool_name") or record.get("gold_tool") or "")
    return "__abstain__"


def _expected_tool(record: Dict[str, Any]) -> str:
    value = record.get("expected_tool_name")
    if value:
        return str(value)
    if not _should_trigger(record):
        return "__abstain__"
    return str(record.get("tool_name") or record.get("gold_tool") or "")


def _tool_success(record: Dict[str, Any]) -> float:
    if "tool_selection_correct" in record:
        return 1.0 if _as_bool(record.get("tool_selection_correct"), default=False) else 0.0
    return 1.0 if _selected_tool(record) == _expected_tool(record) else 0.0


def _argument_success(record: Dict[str, Any]) -> float:
    for key in ("argument_exact_match", "argument_exact_match_given_tool", "exact_match"):
        if key in record:
            return 1.0 if _as_bool(record.get(key), default=False) else 0.0
    if not _should_trigger(record):
        return 1.0 if not _triggered(record) else 0.0
    return 0.0


def _joint_success(record: Dict[str, Any]) -> float:
    if "joint_exact_match" in record:
        return 1.0 if _as_bool(record.get("joint_exact_match"), default=False) else 0.0
    if not _should_trigger(record):
        return 1.0 if not _is_harmful_activation(record) else 0.0
    return 1.0 if _tool_success(record) and _argument_success(record) else 0.0


def _is_harmful_activation(record: Dict[str, Any]) -> bool:
    if _as_bool(record.get("harmful_injection"), default=False) or _as_bool(record.get("skill_induced_harm"), default=False):
        return True
    if _should_trigger(record):
        return False
    selected = _selected_tool(record)
    if not _triggered(record) or selected == "__abstain__":
        return False
    expected = _expected_tool(record)
    return not (expected and expected != "__abstain__" and selected == expected)


def _complexity(record: Dict[str, Any]) -> float | None:
    for key in ("token_overhead_estimate", "token_overhead", "prompt_tokens", "total_tokens", "skill_token_count"):
        if key in record:
            value = _as_float(record.get(key))
            if value is not None:
                return value
    metadata = record.get("prediction_metadata")
    if isinstance(metadata, dict):
        for key in ("token_overhead_estimate", "prompt_tokens", "total_tokens", "skill_token_count"):
            value = _as_float(metadata.get(key))
            if value is not None:
                return value
    method_metadata = record.get("method_metadata")
    if isinstance(method_metadata, dict):
        for key in ("token_overhead_estimate", "skill_token_count", "artifact_token_count"):
            value = _as_float(method_metadata.get(key))
            if value is not None:
                return value
    return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _as_bool(value: Any, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n"}:
            return False
    return default


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _mean(values: Iterable[float]) -> float:
    items = [float(value) for value in values]
    return sum(items) / len(items) if items else 0.0

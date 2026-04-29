from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reliaskill.human_skill_condition import load_tool_records, tool_id_for_record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sample a balanced tool subset for human-written ReliaSkill authoring.")
    parser.add_argument("--tools", default="data/processed_toolir/tools.jsonl")
    parser.add_argument("--controls", nargs="*", default=["data/controls/dev.jsonl", "data/controls/test.jsonl"])
    parser.add_argument("--output", default="data/human_skills/subset.jsonl")
    parser.add_argument("--stats", default="outputs/tables/human_skill_subset_stats.csv")
    parser.add_argument("--target-count", type=int, default=25)
    parser.add_argument("--min-count", type=int, default=20)
    parser.add_argument("--max-count", type=int, default=30)
    parser.add_argument("--min-side-effect-tools", type=int, default=5)
    parser.add_argument("--min-hard-negative-tools", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tools = load_tool_records(args.tools)
    hard_negative_tools = load_hard_negative_tools(args.controls)
    subset = sample_human_skill_subset(
        tools,
        hard_negative_tools=hard_negative_tools,
        target_count=args.target_count,
        min_count=args.min_count,
        max_count=args.max_count,
        min_side_effect_tools=args.min_side_effect_tools,
        min_hard_negative_tools=args.min_hard_negative_tools,
        seed=args.seed,
    )
    write_jsonl(args.output, [subset_record(record, hard_negative_tools) for record in subset])
    write_subset_stats(args.stats, subset, hard_negative_tools)
    print(f"sampled_tools={len(subset)}")
    print(f"subset={args.output}")
    print(f"stats={args.stats}")


def load_hard_negative_tools(paths: Iterable[str | Path]) -> set[str]:
    tools: set[str] = set()
    for path in paths:
        input_path = Path(path)
        if not input_path.exists():
            continue
        with input_path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                if (
                    record.get("control_family") == "negative"
                    and record.get("difficulty") == "hard"
                    and record.get("should_trigger") is False
                ):
                    name = str(record.get("tool_name") or record.get("function") or record.get("negative_target") or "")
                    if name:
                        tools.add(name)
    return tools


def sample_human_skill_subset(
    tools: List[Dict[str, Any]],
    *,
    hard_negative_tools: set[str],
    target_count: int = 25,
    min_count: int = 20,
    max_count: int = 30,
    min_side_effect_tools: int = 5,
    min_hard_negative_tools: int = 5,
    seed: int = 42,
) -> List[Dict[str, Any]]:
    target = min(max(target_count, min_count), max_count, len(tools))
    rng = random.Random(seed)
    buckets: Dict[tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for record in sorted(tools, key=lambda item: str(item.get("tool_name") or "")):
        buckets[(_domain(record), _difficulty(record))].append(record)
    for items in buckets.values():
        rng.shuffle(items)

    selected: List[Dict[str, Any]] = []
    seen: set[str] = set()
    while len(selected) < target:
        progressed = False
        for key in sorted(buckets):
            if len(selected) >= target:
                break
            while buckets[key]:
                candidate = buckets[key].pop(0)
                tool_id = tool_id_for_record(candidate)
                if tool_id not in seen:
                    selected.append(candidate)
                    seen.add(tool_id)
                    progressed = True
                    break
        if not progressed:
            break

    selected = _ensure_requirement(selected, tools, seen, lambda item: _has_side_effect(item), min_side_effect_tools, rng, target)
    selected = _ensure_requirement(
        selected,
        tools,
        {tool_id_for_record(item) for item in selected},
        lambda item: str(item.get("tool_name")) in hard_negative_tools,
        min_hard_negative_tools,
        rng,
        target,
    )
    return sorted(selected[:target], key=lambda item: (_domain(item), _difficulty(item), str(item.get("tool_name") or "")))


def subset_record(record: Dict[str, Any], hard_negative_tools: set[str]) -> Dict[str, Any]:
    meta = record.get("source_metadata") if isinstance(record.get("source_metadata"), dict) else {}
    complexity = record.get("schema_complexity") if isinstance(record.get("schema_complexity"), dict) else {}
    return {
        "tool_id": tool_id_for_record(record),
        "tool_name": record.get("tool_name"),
        "domain": _domain(record),
        "difficulty_tier": _difficulty(record),
        "side_effect_type": complexity.get("side_effect_type") or meta.get("side_effect_type") or "unknown",
        "has_side_effect": _has_side_effect(record),
        "has_hard_negative_controls": str(record.get("tool_name")) in hard_negative_tools,
        "source_type": meta.get("source_type") or meta.get("source_category") or "unknown",
        "source_id": meta.get("source_id") or record.get("server_name") or "unknown",
        "schema_hash": meta.get("schema_hash") or "",
    }


def write_subset_stats(path: str | Path, subset: List[Dict[str, Any]], hard_negative_tools: set[str]) -> None:
    rows = []
    rows.append(_stats_row("all", "all", subset, hard_negative_tools))
    for domain in sorted({_domain(item) for item in subset}):
        rows.append(_stats_row("domain", domain, [item for item in subset if _domain(item) == domain], hard_negative_tools))
    for difficulty in sorted({_difficulty(item) for item in subset}):
        rows.append(_stats_row("difficulty", difficulty, [item for item in subset if _difficulty(item) == difficulty], hard_negative_tools))
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = ["slice_type", "slice_value", "num_tools", "side_effect_tools", "hard_negative_tools", "domains", "difficulties"]
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_jsonl(path: str | Path, rows: Iterable[Dict[str, Any]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def _ensure_requirement(
    selected: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
    seen: set[str],
    predicate,
    minimum: int,
    rng: random.Random,
    target: int,
) -> List[Dict[str, Any]]:
    if sum(1 for item in selected if predicate(item)) >= minimum:
        return selected
    candidates = [item for item in tools if predicate(item) and tool_id_for_record(item) not in seen]
    rng.shuffle(candidates)
    replaceable = [idx for idx, item in enumerate(selected) if not predicate(item)]
    for candidate in candidates:
        if sum(1 for item in selected if predicate(item)) >= minimum:
            break
        if len(selected) < target:
            selected.append(candidate)
            seen.add(tool_id_for_record(candidate))
        elif replaceable:
            idx = replaceable.pop()
            seen.discard(tool_id_for_record(selected[idx]))
            selected[idx] = candidate
            seen.add(tool_id_for_record(candidate))
    return selected


def _stats_row(slice_type: str, slice_value: str, items: List[Dict[str, Any]], hard_negative_tools: set[str]) -> Dict[str, Any]:
    return {
        "slice_type": slice_type,
        "slice_value": slice_value,
        "num_tools": len(items),
        "side_effect_tools": sum(1 for item in items if _has_side_effect(item)),
        "hard_negative_tools": sum(1 for item in items if str(item.get("tool_name")) in hard_negative_tools),
        "domains": len({_domain(item) for item in items}),
        "difficulties": len({_difficulty(item) for item in items}),
    }


def _domain(record: Dict[str, Any]) -> str:
    meta = record.get("source_metadata") if isinstance(record.get("source_metadata"), dict) else {}
    return str(record.get("domain") or meta.get("domain") or "unknown")


def _difficulty(record: Dict[str, Any]) -> str:
    meta = record.get("source_metadata") if isinstance(record.get("source_metadata"), dict) else {}
    return str(record.get("difficulty_tier") or meta.get("difficulty_tier") or "unknown")


def _has_side_effect(record: Dict[str, Any]) -> bool:
    complexity = record.get("schema_complexity") if isinstance(record.get("schema_complexity"), dict) else {}
    meta = record.get("source_metadata") if isinstance(record.get("source_metadata"), dict) else {}
    return bool(complexity.get("has_side_effect") or meta.get("has_side_effect") or complexity.get("side_effect_type") in {"write", "delete", "execute"})


if __name__ == "__main__":
    main()

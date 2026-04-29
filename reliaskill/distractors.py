from __future__ import annotations

import csv
import json
import math
import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

import yaml


DEFAULT_CONFIG = {
    "seed": 42,
    "candidate_set_sizes": [8],
    "distractor_levels": ["easy", "medium", "hard", "adversarial"],
    "include_abstain_candidate": True,
    "use_sentence_transformer": False,
    "sentence_transformer_model": None,
    "outputs": {
        "stats": "outputs/tables/distractor_stats.csv",
    },
}

READ_MARKERS = {"read", "get", "list", "show", "view", "search", "find", "fetch", "query", "inspect"}
WRITE_MARKERS = {"write", "create", "update", "edit", "patch", "save", "set", "add", "upload", "move", "copy"}
OPPOSITE_ACTIONS = (
    ("read", "write"),
    ("search", "fetch"),
    ("create", "update"),
    ("create", "delete"),
    ("list", "create"),
    ("get", "set"),
)


@dataclass(frozen=True)
class ToolProfile:
    tool_id: str
    tool_name: str
    server_name: str
    domain: str
    side_effect_type: str
    description: str
    argument_names: tuple[str, ...]
    text_tokens: frozenset[str]
    name_tokens: frozenset[str]
    embedding: tuple[float, ...] = ()


def load_distractor_config(path: str | Path | None = None) -> Dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    config["outputs"] = dict(DEFAULT_CONFIG["outputs"])
    if path:
        with Path(path).open("r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        if not isinstance(loaded, dict):
            raise ValueError("Distractor config must be a mapping.")
        for key, value in loaded.items():
            if key == "outputs" and isinstance(value, dict):
                config["outputs"].update(value)
            else:
                config[key] = value
    sizes = [int(size) for size in config.get("candidate_set_sizes") or [8]]
    if not sizes or any(size < 2 for size in sizes):
        raise ValueError("candidate_set_sizes must contain integers >= 2.")
    config["candidate_set_sizes"] = sizes
    levels = [str(level) for level in config.get("distractor_levels") or []]
    allowed = {"easy", "medium", "hard", "adversarial"}
    unknown = sorted(set(levels) - allowed)
    if unknown:
        raise ValueError(f"Unsupported distractor levels: {unknown}")
    config["distractor_levels"] = levels or ["easy", "medium", "hard", "adversarial"]
    config["seed"] = int(config.get("seed", 42))
    return config


def load_tool_profiles(path: str | Path) -> Dict[str, ToolProfile]:
    profiles: Dict[str, ToolProfile] = {}
    for item in _read_jsonl_or_json(path):
        if not isinstance(item, dict):
            continue
        tool_name = str(item.get("tool_name") or item.get("name") or "")
        if not tool_name:
            continue
        server_name = str(item.get("server_name") or "")
        metadata = item.get("source_metadata") if isinstance(item.get("source_metadata"), dict) else {}
        domain = str(metadata.get("domain") or item.get("domain") or "unknown")
        side_effect = str(metadata.get("side_effect_type") or _schema_complexity_value(item, "side_effect_type") or "unknown")
        description = str(item.get("tool_purpose") or item.get("description") or item.get("summary") or "")
        args = tuple(str(arg.get("name")) for arg in item.get("arguments", []) if isinstance(arg, dict) and arg.get("name"))
        text = " ".join([tool_name, description, " ".join(args)])
        profile = ToolProfile(
            tool_id=tool_name,
            tool_name=tool_name,
            server_name=server_name,
            domain=domain,
            side_effect_type=side_effect,
            description=description,
            argument_names=args,
            text_tokens=frozenset(_tokenize(text)),
            name_tokens=frozenset(_tokenize(tool_name.replace("_", " "))),
        )
        profiles[profile.tool_id] = profile
    return profiles


def load_controls(path: str | Path) -> List[Dict[str, Any]]:
    return [item for item in _read_jsonl_or_json(path) if isinstance(item, dict)]


def build_routing_examples(
    tools: Dict[str, ToolProfile],
    controls: Sequence[Dict[str, Any]],
    config: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    cfg = dict(DEFAULT_CONFIG)
    cfg["outputs"] = dict(DEFAULT_CONFIG["outputs"])
    if config:
        cfg.update({key: value for key, value in config.items() if key != "outputs"})
        if isinstance(config.get("outputs"), dict):
            cfg["outputs"].update(config["outputs"])
    seed = int(cfg.get("seed", 42))
    sizes = [int(size) for size in cfg.get("candidate_set_sizes") or [8]]
    levels = [str(level) for level in cfg.get("distractor_levels") or ["easy", "medium", "hard", "adversarial"]]
    tools = maybe_add_sentence_transformer_embeddings(tools, cfg)
    examples: List[Dict[str, Any]] = []
    for control_index, control in enumerate(controls):
        target_id = _target_tool_id(control)
        correct_id = str(control.get("gold_tool") or target_id)
        if correct_id == "__abstain__":
            correct_id = "__abstain__"
        anchor_id = correct_id if correct_id in tools else target_id
        if anchor_id not in tools:
            continue
        for size in sizes:
            for level in levels:
                rng = random.Random(seed + (control_index * 1009) + (size * 37) + _level_offset(level))
                candidate_ids, reasons = build_candidate_set(
                    target_id=target_id,
                    correct_id=correct_id,
                    tools=tools,
                    level=level,
                    candidate_set_size=size,
                    rng=rng,
                    include_abstain=bool(cfg.get("include_abstain_candidate", True)),
                )
                examples.append(
                    {
                        "id": f"route_{control.get('control_id') or control.get('id') or control_index}_{level}_{size}",
                        "source_control_id": control.get("control_id") or control.get("id"),
                        "target_tool_id": target_id,
                        "user_request": str(control.get("user_request") or control.get("question") or ""),
                        "candidate_tool_ids": candidate_ids,
                        "correct_tool_id": correct_id,
                        "distractor_level": level,
                        "distractor_generation_reason": reasons,
                        "should_trigger": bool(control.get("should_trigger")),
                        "candidate_set_size": len(candidate_ids),
                        "requested_candidate_set_size": size,
                        "control_family": control.get("control_family"),
                        "control_difficulty": control.get("difficulty"),
                        "negative_category": control.get("negative_category"),
                        "expected_failure_mode": control.get("expected_failure_mode"),
                        "gold_args": control.get("gold_args") if isinstance(control.get("gold_args"), dict) else {},
                        "split": control.get("split"),
                    }
                )
    return examples


def build_candidate_set(
    *,
    target_id: str,
    correct_id: str,
    tools: Dict[str, ToolProfile],
    level: str,
    candidate_set_size: int,
    rng: random.Random,
    include_abstain: bool,
) -> tuple[List[str], List[str]]:
    anchor_id = correct_id if correct_id in tools else target_id
    target = tools.get(target_id) or tools[anchor_id]
    anchor = tools[anchor_id]
    reserved = {candidate for candidate in (target_id, correct_id) if candidate in tools}
    pool = [tool for tool in tools.values() if tool.tool_id not in reserved]
    scored = [(tool, distractor_score(anchor, tool)) for tool in pool]
    selected: List[ToolProfile]
    reasons: List[str]
    if level == "easy":
        candidates = [tool for tool, score in scored if tool.domain != anchor.domain]
        selected = _take_random(candidates, candidate_set_size - 1, rng)
        reasons = ["random_different_domain"]
    elif level == "medium":
        candidates = [tool for tool, score in scored if tool.domain == anchor.domain and score["intent_relation"] != "near_miss"]
        selected = _take_ranked(candidates, anchor, candidate_set_size - 1, rng)
        reasons = ["same_domain_different_intent"]
    elif level == "hard":
        candidates = [tool for tool, score in scored if score["hard_score"] > 0]
        selected = _take_ranked(candidates, anchor, candidate_set_size - 1, rng)
        reasons = ["similar_name_description_or_arguments"]
    elif level == "adversarial":
        candidates = [tool for tool, score in scored if score["intent_relation"] in {"near_miss", "opposite_action"}]
        selected = _take_ranked(candidates, anchor, candidate_set_size - 1, rng)
        reasons = ["near_miss_or_confusing_opposite_action"]
    else:
        selected = []
        reasons = [f"unknown_level:{level}"]

    if len(selected) < candidate_set_size - 1:
        existing = {tool.tool_id for tool in selected} | reserved
        fallback = [tool for tool, _score in scored if tool.tool_id not in existing]
        selected.extend(_take_ranked(fallback, anchor, candidate_set_size - 1 - len(selected), rng))
        reasons.append("fallback_ranked_fill")

    candidate_ids = [tool.tool_id for tool in selected[: max(0, candidate_set_size - 1)]]
    if correct_id != "__abstain__" and correct_id in tools:
        candidate_ids.append(correct_id)
    elif target_id in tools:
        candidate_ids.append(target_id)
    if include_abstain and correct_id == "__abstain__" and "__abstain__" not in candidate_ids:
        candidate_ids.append("__abstain__")
    candidate_ids = _dedupe(candidate_ids)
    while len(candidate_ids) < candidate_set_size:
        existing = set(candidate_ids)
        fill = [tool for tool in tools.values() if tool.tool_id not in existing]
        if not fill:
            break
        candidate_ids.append(rng.choice(fill).tool_id)
    rng.shuffle(candidate_ids)
    return candidate_ids[:candidate_set_size], reasons


def distractor_score(target: ToolProfile, candidate: ToolProfile) -> Dict[str, Any]:
    name_similarity = jaccard(target.name_tokens, candidate.name_tokens)
    text_similarity = jaccard(target.text_tokens, candidate.text_tokens)
    arg_overlap = jaccard(set(target.argument_names), set(candidate.argument_names))
    same_domain = target.domain == candidate.domain
    same_side_effect = target.side_effect_type == candidate.side_effect_type
    opposite = confusing_opposite_action(target, candidate)
    semantic_similarity = cosine_similarity(target.embedding, candidate.embedding) if target.embedding and candidate.embedding else 0.0
    hard_score = (
        (3.0 * name_similarity)
        + (2.0 * text_similarity)
        + (2.0 * arg_overlap)
        + (1.0 * semantic_similarity)
        + (1.0 if same_domain else 0.0)
        + (0.5 if same_side_effect else 0.0)
        + (1.5 if opposite else 0.0)
    )
    if opposite:
        relation = "opposite_action"
    elif name_similarity >= 0.35 or arg_overlap >= 0.35 or (same_domain and text_similarity >= 0.25):
        relation = "near_miss"
    elif same_domain:
        relation = "same_domain"
    else:
        relation = "different_domain"
    return {
        "name_similarity": round(name_similarity, 4),
        "description_similarity": round(text_similarity, 4),
        "arg_overlap": round(arg_overlap, 4),
        "same_domain": same_domain,
        "same_side_effect_type": same_side_effect,
        "confusing_opposite_action": opposite,
        "semantic_similarity": round(semantic_similarity, 4),
        "hard_score": round(hard_score, 4),
        "intent_relation": relation,
    }


def summarize_distractor_examples(examples: Sequence[Dict[str, Any]], tools: Dict[str, ToolProfile]) -> Dict[str, Any]:
    levels = Counter(str(example.get("distractor_level") or "unknown") for example in examples)
    similarities: List[float] = []
    arg_overlaps: List[float] = []
    for example in examples:
        correct = str(example.get("correct_tool_id") or "")
        target = str(example.get("target_tool_id") or "")
        anchor_id = correct if correct in tools else target
        if anchor_id not in tools:
            continue
        anchor = tools[anchor_id]
        for candidate_id in example.get("candidate_tool_ids") or []:
            if candidate_id in {correct, target, "__abstain__"} or candidate_id not in tools:
                continue
            score = distractor_score(anchor, tools[candidate_id])
            similarities.append(float(score["name_similarity"]))
            arg_overlaps.append(float(score["arg_overlap"]))
    return {
        "num_examples": len(examples),
        "avg_candidates": round(sum(len(example.get("candidate_tool_ids") or []) for example in examples) / len(examples), 4) if examples else 0.0,
        "easy_count": levels.get("easy", 0),
        "medium_count": levels.get("medium", 0),
        "hard_count": levels.get("hard", 0),
        "adversarial_count": levels.get("adversarial", 0),
        "avg_name_similarity": round(sum(similarities) / len(similarities), 4) if similarities else 0.0,
        "avg_arg_overlap": round(sum(arg_overlaps) / len(arg_overlaps), 4) if arg_overlaps else 0.0,
    }


def write_routing_examples(path: str | Path, examples: Iterable[Dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for example in examples:
            f.write(json.dumps(example, ensure_ascii=False, sort_keys=True) + "\n")


def write_distractor_stats(path: str | Path, summary: Dict[str, Any]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "num_examples",
        "avg_candidates",
        "easy_count",
        "medium_count",
        "hard_count",
        "adversarial_count",
        "avg_name_similarity",
        "avg_arg_overlap",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow({key: summary.get(key, 0) for key in fieldnames})


def _read_jsonl_or_json(path: str | Path) -> List[Dict[str, Any]]:
    input_path = Path(path)
    if input_path.suffix.lower() == ".jsonl":
        records = []
        with input_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict):
        for key in ("data", "items", "records", "tools"):
            value = raw.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [raw]
    return []


def _schema_complexity_value(item: Dict[str, Any], key: str) -> Any:
    value = item.get("schema_complexity")
    if isinstance(value, dict):
        return value.get(key)
    return None


def _target_tool_id(control: Dict[str, Any]) -> str:
    if control.get("should_trigger"):
        return str(control.get("gold_tool") or control.get("tool_name") or "")
    return str(control.get("negative_target") or control.get("tool_name") or control.get("gold_tool") or "")


def _take_random(candidates: Sequence[ToolProfile], count: int, rng: random.Random) -> List[ToolProfile]:
    items = list(candidates)
    rng.shuffle(items)
    return items[: max(0, count)]


def _take_ranked(candidates: Sequence[ToolProfile], target: ToolProfile, count: int, rng: random.Random) -> List[ToolProfile]:
    jittered = []
    for tool in candidates:
        score = float(distractor_score(target, tool)["hard_score"])
        jittered.append((score, rng.random(), tool.tool_id, tool))
    jittered.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [item[3] for item in jittered[: max(0, count)]]


def _dedupe(items: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _level_offset(level: str) -> int:
    return {"easy": 11, "medium": 23, "hard": 37, "adversarial": 53}.get(level, 0)


def _tokenize(text: str) -> List[str]:
    return [token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 1]


def jaccard(left: set[str] | frozenset[str], right: set[str] | frozenset[str]) -> float:
    if not left and not right:
        return 0.0
    union = set(left).union(right)
    if not union:
        return 0.0
    return len(set(left).intersection(right)) / len(union)


def confusing_opposite_action(target: ToolProfile, candidate: ToolProfile) -> bool:
    target_tokens = set(target.name_tokens) | set(_tokenize(target.description))
    candidate_tokens = set(candidate.name_tokens) | set(_tokenize(candidate.description))
    for left, right in OPPOSITE_ACTIONS:
        if (left in target_tokens and right in candidate_tokens) or (right in target_tokens and left in candidate_tokens):
            return True
    if target.side_effect_type in {"read"} and candidate.side_effect_type in {"write", "delete", "execute", "external_communication"}:
        return True
    if candidate.side_effect_type in {"read"} and target.side_effect_type in {"write", "delete", "execute", "external_communication"}:
        return True
    return False


def maybe_add_sentence_transformer_embeddings(tools: Dict[str, ToolProfile], config: Dict[str, Any]) -> Dict[str, ToolProfile]:
    if not config.get("use_sentence_transformer"):
        return tools
    model_path = config.get("sentence_transformer_model")
    if not model_path or not Path(str(model_path)).exists():
        return tools
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return tools
    model = SentenceTransformer(str(model_path))
    ordered = [tools[key] for key in sorted(tools)]
    texts = [" ".join([tool.tool_name, tool.description, " ".join(tool.argument_names)]) for tool in ordered]
    vectors = model.encode(texts, convert_to_numpy=False, show_progress_bar=False)
    updated: Dict[str, ToolProfile] = {}
    for tool, vector in zip(ordered, vectors):
        values = tuple(float(item) for item in vector)
        updated[tool.tool_id] = ToolProfile(
            tool_id=tool.tool_id,
            tool_name=tool.tool_name,
            server_name=tool.server_name,
            domain=tool.domain,
            side_effect_type=tool.side_effect_type,
            description=tool.description,
            argument_names=tool.argument_names,
            text_tokens=tool.text_tokens,
            name_tokens=tool.name_tokens,
            embedding=values,
        )
    return updated


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)

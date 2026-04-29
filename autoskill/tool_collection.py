from __future__ import annotations

import csv
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import yaml

from autoskill.conversion import canonicalize_mcp_tool_records, load_json_or_jsonl
from autoskill.external_ingest import harvest_reference_mcp_servers
from autoskill.ir import ToolIR
from autoskill.parser import parse_mcp_tool


DEFAULT_OUTPUTS = {
    "raw_tools": "data/raw_mcp/tools.jsonl",
    "toolir": "data/processed_toolir/tools.jsonl",
    "dataset_stats": "outputs/tables/dataset_stats.csv",
    "domain_complexity_stats": "outputs/tables/domain_complexity_stats.csv",
    "tool_difficulty_stats": "outputs/tables/tool_difficulty_stats.csv",
    "dataset_card": "outputs/reports/dataset_card.md",
}

READ_ONLY_MARKERS = (
    "read",
    "list",
    "get",
    "fetch",
    "search",
    "find",
    "query",
    "inspect",
    "show",
    "view",
    "describe",
)
WRITE_MARKERS = ("write", "create", "update", "edit", "patch", "save", "set", "add", "upload", "move", "copy")
DELETE_MARKERS = ("delete", "remove", "drop", "clear", "purge")
EXECUTE_MARKERS = ("execute", "run", "shell", "command", "script", "eval", "code")
COMMUNICATION_MARKERS = ("send", "email", "message", "post", "publish", "notify", "tweet", "slack")
AUTH_MARKERS = ("api key", "oauth", "token", "credential", "login", "auth", "secret", "bearer")
SIDE_EFFECT_TYPES = {"write", "delete", "execute", "external_communication"}

CANONICAL_DOMAINS = {
    "filesystem",
    "search/retrieval",
    "database/sql",
    "calendar/time",
    "git/version-control",
    "issue-tracking",
    "messaging/email mock",
    "web/fetch mock",
    "cloud/storage mock",
    "math/data processing",
    "memory/notes",
    "system/admin mock",
}

DOMAIN_ALIASES = {
    "search": "search/retrieval",
    "retrieval": "search/retrieval",
    "database": "database/sql",
    "sql": "database/sql",
    "calendar": "calendar/time",
    "time": "calendar/time",
    "git": "git/version-control",
    "version-control": "git/version-control",
    "communication": "messaging/email mock",
    "messaging": "messaging/email mock",
    "email": "messaging/email mock",
    "web": "web/fetch mock",
    "fetch": "web/fetch mock",
    "cloud": "cloud/storage mock",
    "storage": "cloud/storage mock",
    "math": "math/data processing",
    "data_science": "math/data processing",
    "data-science": "math/data processing",
    "bfcl_api": "math/data processing",
    "memory": "memory/notes",
    "notes": "memory/notes",
    "system": "system/admin mock",
    "admin": "system/admin mock",
    "browser": "web/fetch mock",
}


def load_collection_config(path: str | Path) -> Dict[str, Any]:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    if not isinstance(config, dict):
        raise ValueError("Tool collection config must be a mapping.")
    outputs = dict(DEFAULT_OUTPUTS)
    outputs.update(config.get("outputs") or {})
    config["outputs"] = outputs
    config.setdefault("seed", 42)
    config.setdefault("max_tools", None)
    config.setdefault("max_tools_per_source", None)
    config.setdefault("max_synthetic_fraction", 1.0)
    config.setdefault("min_domains_required", 0)
    config.setdefault("min_hard_tools_required", 0)
    config.setdefault("min_side_effect_tools_required", 0)
    config.setdefault("sources", [])
    return config


def load_records_from_source(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    source_type = str(source.get("type") or "canonical_json")
    source_id = str(source.get("id") or source.get("path") or source_type)
    path = Path(str(source.get("path", ""))) if source.get("path") else None

    if source_type in {
        "canonical_json",
        "mcp_fixture",
        "real_public_mcp",
        "converted_bfcl",
        "converted_api_style",
        "converted_apibank",
        "converted_api_bank",
        "converted_toolbench",
        "apibank",
    }:
        if not path or not path.exists():
            return []
        return canonicalize_mcp_tool_records(load_json_or_jsonl(path), default_server_name=source.get("server"))

    if source_type == "reference_mcp_repo":
        if not path or not path.exists():
            return []
        return harvest_reference_mcp_servers(path)

    if source_type == "synthetic_mock":
        return _build_synthetic_mock_tools(source)

    raise ValueError(f"Unsupported tool source type: {source_type}")


def collect_tool_records(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    seed = int(config.get("seed", 42))
    random.seed(seed)
    collected: List[Dict[str, Any]] = []
    for source_index, source in enumerate(config.get("sources") or []):
        source_id = str(source.get("id") or f"source_{source_index}")
        source_type = str(source.get("type") or "canonical_json")
        source_domain = str(source.get("domain") or "")
        source_path = str(source.get("path") or "")
        limit = source.get("limit")
        records = load_records_from_source(source)
        records = sorted(records, key=lambda item: (str(item.get("server_name") or ""), str(item.get("name") or "")))
        if isinstance(limit, int) and limit >= 0:
            records = records[:limit]
        for record_index, record in enumerate(records):
            normalized = normalize_raw_tool_record(
                record,
                source_id=source_id,
                source_type=source_type,
                source_domain=source_domain,
                source_path=source_path,
                source_index=source_index,
                record_index=record_index,
                seed=seed,
                synthetic=bool(source.get("synthetic") or source_type == "synthetic_mock"),
            )
            if normalized is not None:
                collected.append(normalized)

    deduped = dedupe_tool_records(collected)
    selected = apply_balance_controls(deduped, config)
    validate_raw_tool_records(selected)
    return selected


def normalize_raw_tool_record(
    record: Dict[str, Any],
    *,
    source_id: str,
    source_type: str,
    source_domain: str,
    source_path: str,
    source_index: int,
    record_index: int,
    seed: int,
    synthetic: bool,
) -> Dict[str, Any] | None:
    name = str(record.get("name") or record.get("tool_name") or "").strip()
    description = str(record.get("description") or record.get("summary") or record.get("title") or "").strip()
    input_schema = record.get("inputSchema") or record.get("input_schema")
    if not name or not description or not isinstance(input_schema, dict):
        return None

    input_schema = normalize_input_schema(input_schema)
    server = str(record.get("server_name") or record.get("server") or source_id)
    explicit_domain = record.get("domain") or source_domain
    domain = canonical_domain(str(explicit_domain)) if explicit_domain else infer_domain(server, name, description, source_id)
    schema_hash = stable_schema_hash(input_schema)
    complexity = compute_schema_complexity(input_schema, description)
    side_effect_type = infer_side_effect_type(name, description, domain)
    has_side_effect = side_effect_type in SIDE_EFFECT_TYPES
    auth_required = infer_auth_required(record, description)
    difficulty_tier = infer_difficulty_tier(
        complexity=complexity,
        side_effect_type=side_effect_type,
        description=description,
        name=name,
    )
    source_pointer = record.get("source_pointer") or record.get("source_file") or source_path
    normalized_name = normalize_tool_name(name)
    source_metadata = {
        "source_id": source_id,
        "source_type": source_type,
        "source_category": source_category(source_type, synthetic),
        "source_file": source_path,
        "source_pointer": str(source_pointer or ""),
        "source_server": server,
        "server": server,
        "tool_name": name,
        "normalized_tool_name": normalized_name,
        "domain": domain,
        "side_effect_type": side_effect_type,
        "has_side_effect": has_side_effect,
        "auth_required": auth_required,
        **complexity,
        "args_count": complexity["num_arguments"],
        "required_args_count": complexity["num_required_arguments"],
        "enum_count": complexity["num_enum_fields"],
        "difficulty_tier": difficulty_tier,
        "schema_hash": schema_hash,
        "synthetic": synthetic,
        "collection_seed": seed,
        "source_order": source_index,
        "record_order": record_index,
    }
    return {
        "server_name": server,
        "name": name,
        "title": record.get("title") or name.replace("_", " ").title(),
        "summary": record.get("summary") or description[:180],
        "description": description,
        "inputSchema": input_schema,
        "outputSchema": record.get("outputSchema") or record.get("output_schema"),
        "source_metadata": source_metadata,
        "domain": domain,
        "side_effect_type": side_effect_type,
        "has_side_effect": has_side_effect,
        "auth_required": auth_required,
        "difficulty_tier": difficulty_tier,
        **complexity,
        "args_count": complexity["num_arguments"],
        "required_args_count": complexity["num_required_arguments"],
        "enum_count": complexity["num_enum_fields"],
    }


def normalize_input_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(schema)
    if normalized.get("type") != "object":
        normalized = {"type": "object", **normalized}
    properties = normalized.get("properties")
    if not isinstance(properties, dict):
        normalized["properties"] = {}
    required = normalized.get("required")
    if not isinstance(required, list):
        normalized["required"] = []
    return normalized


def stable_schema_hash(schema: Dict[str, Any]) -> str:
    payload = json.dumps(schema, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def schema_counts(schema: Dict[str, Any]) -> Tuple[int, int, int]:
    properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    required = schema.get("required") if isinstance(schema.get("required"), list) else []
    return len(properties), len(required), _count_enums(schema)


def compute_schema_complexity(schema: Dict[str, Any], description: str = "") -> Dict[str, Any]:
    properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    required = schema.get("required") if isinstance(schema.get("required"), list) else []
    required_set = {str(item) for item in required}
    num_arguments = len(properties)
    num_required_arguments = sum(1 for name in properties if name in required_set)
    num_optional_arguments = max(0, num_arguments - num_required_arguments)
    num_enum_fields = _count_enums(schema)
    has_nested_object = _has_type(schema, "object", skip_root=True)
    has_array_argument = any(_schema_has_type(prop, "array") for prop in properties.values())
    has_boolean_flag = any(_schema_has_type(prop, "boolean") for prop in properties.values())
    documentation_length = len(" ".join(str(description or "").split()))
    ambiguity_score = ambiguity_score_heuristic(schema, description)
    return {
        "num_arguments": num_arguments,
        "num_required_arguments": num_required_arguments,
        "num_optional_arguments": num_optional_arguments,
        "num_enum_fields": num_enum_fields,
        "has_nested_object": has_nested_object,
        "has_array_argument": has_array_argument,
        "has_boolean_flag": has_boolean_flag,
        "documentation_length": documentation_length,
        "ambiguity_score_heuristic": ambiguity_score,
    }


def _schema_has_type(value: Any, expected_type: str) -> bool:
    if isinstance(value, dict):
        schema_type = value.get("type")
        if schema_type == expected_type or (isinstance(schema_type, list) and expected_type in schema_type):
            return True
        return any(_schema_has_type(child, expected_type) for child in value.values())
    if isinstance(value, list):
        return any(_schema_has_type(child, expected_type) for child in value)
    return False


def _has_type(schema: Dict[str, Any], expected_type: str, *, skip_root: bool = False) -> bool:
    if not skip_root and _schema_has_type(schema, expected_type):
        return True
    properties = schema.get("properties")
    if isinstance(properties, dict):
        return any(_schema_has_type(prop, expected_type) for prop in properties.values())
    return False


def ambiguity_score_heuristic(schema: Dict[str, Any], description: str = "") -> float:
    properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    score = 0.0
    doc_len = len(" ".join(str(description or "").split()))
    if doc_len < 80:
        score += 0.25
    if not properties:
        score += 0.35
    elif any(isinstance(prop, dict) and not prop.get("description") for prop in properties.values()):
        missing = sum(1 for prop in properties.values() if isinstance(prop, dict) and not prop.get("description"))
        score += min(0.35, 0.1 + 0.25 * (missing / len(properties)))
    if schema.get("additionalProperties") is not False:
        score += 0.15
    if _count_enums(schema) == 0 and any(_schema_has_type(prop, "string") for prop in properties.values()):
        score += 0.1
    if len(properties) >= 5:
        score += 0.1
    return round(min(score, 1.0), 4)


def _count_enums(value: Any) -> int:
    if isinstance(value, dict):
        total = 1 if isinstance(value.get("enum"), list) else 0
        return total + sum(_count_enums(child) for child in value.values())
    if isinstance(value, list):
        return sum(_count_enums(child) for child in value)
    return 0


def canonical_domain(domain: str) -> str:
    normalized = " ".join(str(domain or "").strip().lower().replace("_", " ").split())
    slash_normalized = normalized.replace(" / ", "/")
    alias_key = slash_normalized.replace(" ", "_")
    if slash_normalized in CANONICAL_DOMAINS:
        return slash_normalized
    if slash_normalized in DOMAIN_ALIASES:
        return DOMAIN_ALIASES[slash_normalized]
    if alias_key in DOMAIN_ALIASES:
        return DOMAIN_ALIASES[alias_key]
    return str(domain or "general").strip() or "general"


def infer_domain(server: str, name: str, description: str, source_id: str = "") -> str:
    text = f"{source_id} {server} {name} {description}".lower()
    domain_markers = [
        ("filesystem", ("filesystem", "file", "directory", "path", "folder")),
        ("math/data processing", ("tensorflow", "torch", "model", "dataset", "hugging", "fairseq", "inference", "transformers", "dataframe", "csv")),
        ("web/fetch mock", ("browser", "playwright", "page", "screenshot", "http", "url", "fetch", "web")),
        ("search/retrieval", ("search", "query", "retrieval", "rank")),
        ("git/version-control", ("git", "commit", "repository", "branch", "diff", "pull request")),
        ("calendar/time", ("calendar", "event", "schedule", "time", "timezone", "date", "clock")),
        ("memory/notes", ("memory", "note", "entity", "knowledge graph", "relation")),
        ("math/data processing", ("math", "calculate", "factorial", "triangle", "number", "aggregate", "statistics")),
        ("image", ("image", "vision", "photo", "stable diffusion", "pixel")),
        ("audio", ("audio", "speech", "sound", "voice")),
        ("database/sql", ("database", "sql", "table", "record")),
        ("messaging/email mock", ("email", "message", "slack", "notification", "send", "inbox")),
        ("cloud/storage mock", ("bucket", "object storage", "cloud", "blob", "s3")),
        ("issue-tracking", ("issue", "ticket", "bug", "label", "assignee", "milestone")),
        ("system/admin mock", ("system", "admin", "service", "process", "log", "environment")),
    ]
    for domain, markers in domain_markers:
        if any(_has_marker(text, marker) for marker in markers):
            return domain
    if source_id.startswith("bfcl"):
        return "math/data processing"
    return "general"


def normalize_tool_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name or "").lower()).strip("_")


def source_category(source_type: str, synthetic: bool) -> str:
    if synthetic:
        return "safe_synthetic_mcp_like"
    mapping = {
        "mcp_fixture": "local_mcp_fixture_schema",
        "real_public_mcp": "real_public_mcp_schema_local",
        "reference_mcp_repo": "real_public_mcp_schema_local",
        "converted_bfcl": "converted_bfcl_api_style",
        "converted_api_style": "converted_api_style",
        "converted_apibank": "converted_api_bank_style",
        "converted_api_bank": "converted_api_bank_style",
        "apibank": "converted_api_bank_style",
        "converted_toolbench": "converted_toolbench_style",
        "canonical_json": "canonical_local_schema",
    }
    return mapping.get(source_type, source_type)


def infer_side_effect_type(name: str, description: str, domain: str = "") -> str:
    text = f"{domain} {name} {description}".lower()
    if any(_has_marker(text, marker) for marker in DELETE_MARKERS):
        return "delete"
    if any(_has_marker(text, marker) for marker in EXECUTE_MARKERS):
        return "execute"
    if any(_has_marker(text, marker) for marker in COMMUNICATION_MARKERS):
        return "external_communication"
    if any(_has_marker(text, marker) for marker in WRITE_MARKERS):
        return "write"
    if any(_has_marker(text, marker) for marker in READ_ONLY_MARKERS):
        return "read"
    return "unknown"


def infer_difficulty_tier(
    *,
    complexity: Dict[str, Any],
    side_effect_type: str,
    description: str,
    name: str,
) -> str:
    num_arguments = int(complexity.get("num_arguments") or 0)
    num_optional = int(complexity.get("num_optional_arguments") or 0)
    enum_fields = int(complexity.get("num_enum_fields") or 0)
    ambiguity = float(complexity.get("ambiguity_score_heuristic") or 0.0)
    text = f"{name} {description}".lower()
    neighboring_hint = any(marker in text for marker in ("similar", "variant", "mode", "filter", "selector"))
    if (
        bool(complexity.get("has_nested_object"))
        or bool(complexity.get("has_array_argument"))
        or enum_fields > 0
        or side_effect_type in SIDE_EFFECT_TYPES
        or ambiguity >= 0.45
        or neighboring_hint
        or num_arguments > 5
    ):
        return "hard"
    if 3 <= num_arguments <= 5 or num_optional > 0:
        return "medium"
    return "easy"


def infer_auth_required(record: Dict[str, Any], description: str) -> bool:
    explicit = record.get("auth_required")
    if isinstance(explicit, bool):
        return explicit
    notes = " ".join(str(record.get(key) or "") for key in ("auth_or_env_notes", "auth_notes", "source_note"))
    text = f"{description} {notes}".lower()
    return any(_has_marker(text, marker) for marker in AUTH_MARKERS)


def _has_marker(text: str, marker: str) -> bool:
    if " " in marker:
        return marker in text
    return re.search(rf"(?<![a-z0-9]){re.escape(marker)}(?![a-z0-9])", text) is not None


def dedupe_tool_records(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for record in records:
        metadata = record.get("source_metadata") or {}
        key = (
            str(metadata.get("normalized_tool_name") or normalize_tool_name(str(record.get("name") or ""))),
            str(metadata.get("schema_hash") or stable_schema_hash(record.get("inputSchema") or {})),
        )
        deduped.setdefault(key, record)
    return sorted(
        deduped.values(),
        key=lambda item: (
            int((item.get("source_metadata") or {}).get("source_order") or 0),
            int((item.get("source_metadata") or {}).get("record_order") or 0),
            str((item.get("source_metadata") or {}).get("normalized_tool_name") or ""),
        ),
    )


def apply_balance_controls(records: Sequence[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    max_per_source = config.get("max_tools_per_source")
    selected: List[Dict[str, Any]] = []
    by_source: Counter[str] = Counter()
    for record in records:
        source_id = str((record.get("source_metadata") or {}).get("source_id") or "unknown")
        if isinstance(max_per_source, int) and max_per_source > 0 and by_source[source_id] >= max_per_source:
            continue
        selected.append(record)
        by_source[source_id] += 1

    selected = cap_synthetic_fraction(selected, float(config.get("max_synthetic_fraction", 1.0)))
    max_tools = config.get("max_tools")
    if isinstance(max_tools, int) and max_tools > 0:
        selected = selected[:max_tools]
        selected = cap_synthetic_fraction(selected, float(config.get("max_synthetic_fraction", 1.0)))

    validate_balance_requirements(selected, config)
    return selected


def cap_synthetic_fraction(records: Sequence[Dict[str, Any]], max_fraction: float) -> List[Dict[str, Any]]:
    if max_fraction >= 1.0:
        return list(records)
    if max_fraction < 0:
        max_fraction = 0.0
    real_records = [record for record in records if not (record.get("source_metadata") or {}).get("synthetic")]
    synthetic_records = [record for record in records if (record.get("source_metadata") or {}).get("synthetic")]
    if not synthetic_records:
        return list(records)
    if not real_records:
        allowed = 0
    else:
        allowed = int((max_fraction * len(real_records)) / max(1e-9, 1.0 - max_fraction))
    allowed = max(0, min(len(synthetic_records), allowed))
    allowed_ids = {id(record) for record in synthetic_records[:allowed]}
    return [record for record in records if not (record.get("source_metadata") or {}).get("synthetic") or id(record) in allowed_ids]


def validate_balance_requirements(records: Sequence[Dict[str, Any]], config: Dict[str, Any]) -> None:
    min_domains = int(config.get("min_domains_required") or 0)
    min_hard = int(config.get("min_hard_tools_required") or 0)
    min_side_effect = int(config.get("min_side_effect_tools_required") or 0)
    domains = {str(record.get("domain") or "unknown") for record in records}
    hard_count = sum(1 for record in records if str(record.get("difficulty_tier") or "") == "hard")
    side_effect_count = sum(1 for record in records if bool(record.get("has_side_effect")))
    errors: List[str] = []
    if len(domains) < min_domains:
        errors.append(f"requires at least {min_domains} domains, found {len(domains)}")
    if hard_count < min_hard:
        errors.append(f"requires at least {min_hard} hard tools, found {hard_count}")
    if side_effect_count < min_side_effect:
        errors.append(f"requires at least {min_side_effect} side-effect tools, found {side_effect_count}")
    if errors:
        raise ValueError("Dataset balance requirements not met: " + "; ".join(errors))


def validate_raw_tool_records(records: Sequence[Dict[str, Any]]) -> None:
    errors: List[str] = []
    required_metadata = {
        "server",
        "domain",
        "side_effect_type",
        "auth_required",
        "args_count",
        "required_args_count",
        "enum_count",
        "num_arguments",
        "num_required_arguments",
        "num_optional_arguments",
        "num_enum_fields",
        "has_nested_object",
        "has_array_argument",
        "has_boolean_flag",
        "has_side_effect",
        "difficulty_tier",
        "documentation_length",
        "ambiguity_score_heuristic",
        "source_server",
    }
    for index, record in enumerate(records):
        if not record.get("name"):
            errors.append(f"record {index}: missing name")
        if not record.get("description"):
            errors.append(f"record {index}: missing description")
        if not isinstance(record.get("inputSchema"), dict):
            errors.append(f"record {index}: missing inputSchema")
        metadata = record.get("source_metadata")
        if not isinstance(metadata, dict):
            errors.append(f"record {index}: missing source_metadata")
            continue
        missing = sorted(key for key in required_metadata if key not in metadata)
        if missing:
            errors.append(f"record {index}: missing source metadata fields {missing}")
    if errors:
        raise ValueError("Invalid collected tool records:\n" + "\n".join(errors[:20]))


def parse_toolir_records(raw_records: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    parsed: List[Dict[str, Any]] = []
    for index, record in enumerate(raw_records):
        metadata = record.get("source_metadata") or {}
        pointer = metadata.get("source_pointer") or f"raw_mcp#{index}"
        tool: ToolIR = parse_mcp_tool(record, source_pointer=str(pointer))
        payload = tool.model_dump()
        payload["source_metadata"] = metadata
        payload["domain"] = record.get("domain")
        payload["difficulty_tier"] = record.get("difficulty_tier")
        payload["schema_complexity"].update(
            {
                "num_arguments": record.get("num_arguments"),
                "num_required_arguments": record.get("num_required_arguments"),
                "num_optional_arguments": record.get("num_optional_arguments"),
                "num_enum_fields": record.get("num_enum_fields"),
                "has_nested_object": record.get("has_nested_object"),
                "has_array_argument": record.get("has_array_argument"),
                "has_boolean_flag": record.get("has_boolean_flag"),
                "has_side_effect": record.get("has_side_effect"),
                "side_effect_type": record.get("side_effect_type"),
                "auth_required": record.get("auth_required"),
                "documentation_length": record.get("documentation_length"),
                "ambiguity_score_heuristic": record.get("ambiguity_score_heuristic"),
            }
        )
        parsed.append(payload)
    return parsed


def write_jsonl(path: str | Path, records: Iterable[Dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def load_jsonl(path: str | Path) -> List[Dict[str, Any]]:
    input_path = Path(path)
    records: List[Dict[str, Any]] = []
    with input_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def summarize_dataset(raw_records: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    domains = Counter(str(record.get("domain") or "unknown") for record in raw_records)
    sources = Counter(str((record.get("source_metadata") or {}).get("source_id") or "unknown") for record in raw_records)
    servers = Counter(str(record.get("server_name") or "unknown") for record in raw_records)
    side_effects = Counter(str(record.get("side_effect_type") or "unknown") for record in raw_records)
    difficulties = Counter(str(record.get("difficulty_tier") or "unknown") for record in raw_records)
    synthetic_count = sum(1 for record in raw_records if (record.get("source_metadata") or {}).get("synthetic"))
    auth_count = sum(1 for record in raw_records if bool(record.get("auth_required")))
    side_effect_count = sum(1 for record in raw_records if bool(record.get("has_side_effect")))
    args_total = sum(int(record.get("num_arguments") or record.get("args_count") or 0) for record in raw_records)
    required_total = sum(int(record.get("num_required_arguments") or record.get("required_args_count") or 0) for record in raw_records)
    enum_total = sum(int(record.get("num_enum_fields") or record.get("enum_count") or 0) for record in raw_records)
    return {
        "total_tools": len(raw_records),
        "source_count": len(sources),
        "domain_count": len(domains),
        "server_count": len(servers),
        "synthetic_tools": synthetic_count,
        "synthetic_fraction": round(synthetic_count / len(raw_records), 4) if raw_records else 0.0,
        "auth_required_tools": auth_count,
        "side_effect_tools": side_effect_count,
        "avg_args": round(args_total / len(raw_records), 4) if raw_records else 0.0,
        "avg_required_args": round(required_total / len(raw_records), 4) if raw_records else 0.0,
        "enum_total": enum_total,
        "domains": dict(sorted(domains.items())),
        "sources": dict(sorted(sources.items())),
        "servers": dict(sorted(servers.items())),
        "side_effects": dict(sorted(side_effects.items())),
        "difficulties": dict(sorted(difficulties.items())),
    }


def build_dataset_stats_rows(raw_records: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    for record in raw_records:
        metadata = record.get("source_metadata") or {}
        key = (
            str(metadata.get("source_id") or "unknown"),
            str(record.get("domain") or "unknown"),
            str(record.get("side_effect_type") or "unknown"),
        )
        groups[key].append(record)

    rows: List[Dict[str, Any]] = []
    for (source_id, domain, side_effect_type), records in sorted(groups.items()):
        args_total = sum(int(record.get("args_count") or 0) for record in records)
        required_total = sum(int(record.get("required_args_count") or 0) for record in records)
        enum_total = sum(int(record.get("enum_count") or 0) for record in records)
        auth_count = sum(1 for record in records if bool(record.get("auth_required")))
        synthetic_count = sum(1 for record in records if (record.get("source_metadata") or {}).get("synthetic"))
        hard_count = sum(1 for record in records if str(record.get("difficulty_tier") or "") == "hard")
        side_effect_count = sum(1 for record in records if bool(record.get("has_side_effect")))
        rows.append(
            {
                "source_id": source_id,
                "domain": domain,
                "side_effect_type": side_effect_type,
                "tool_count": len(records),
                "server_count": len({record.get("server_name") for record in records}),
                "auth_required_count": auth_count,
                "synthetic_count": synthetic_count,
                "side_effect_count": side_effect_count,
                "hard_count": hard_count,
                "avg_args": round(args_total / len(records), 4) if records else 0.0,
                "avg_required_args": round(required_total / len(records), 4) if records else 0.0,
                "enum_count": enum_total,
            }
        )
    return rows


def write_dataset_stats_csv(path: str | Path, raw_records: Sequence[Dict[str, Any]]) -> None:
    rows = build_dataset_stats_rows(raw_records)
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "source_id",
        "domain",
        "side_effect_type",
        "tool_count",
        "server_count",
        "auth_required_count",
        "synthetic_count",
        "side_effect_count",
        "hard_count",
        "avg_args",
        "avg_required_args",
        "enum_count",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_rows_csv(path: str | Path, rows: Sequence[Dict[str, Any]], fieldnames: Sequence[str]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_domain_complexity_rows(raw_records: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for record in raw_records:
        groups[str(record.get("domain") or "unknown")].append(record)
    rows: List[Dict[str, Any]] = []
    for domain, records in sorted(groups.items()):
        count = len(records)
        rows.append(
            {
                "domain": domain,
                "tool_count": count,
                "avg_num_arguments": round(sum(int(r.get("num_arguments") or 0) for r in records) / count, 4),
                "avg_required_arguments": round(sum(int(r.get("num_required_arguments") or 0) for r in records) / count, 4),
                "enum_tool_count": sum(1 for r in records if int(r.get("num_enum_fields") or 0) > 0),
                "nested_tool_count": sum(1 for r in records if bool(r.get("has_nested_object"))),
                "array_tool_count": sum(1 for r in records if bool(r.get("has_array_argument"))),
                "boolean_flag_tool_count": sum(1 for r in records if bool(r.get("has_boolean_flag"))),
                "side_effect_tool_count": sum(1 for r in records if bool(r.get("has_side_effect"))),
                "auth_required_count": sum(1 for r in records if bool(r.get("auth_required"))),
                "avg_documentation_length": round(sum(int(r.get("documentation_length") or 0) for r in records) / count, 4),
                "avg_ambiguity_score": round(sum(float(r.get("ambiguity_score_heuristic") or 0.0) for r in records) / count, 4),
                "hard_tool_count": sum(1 for r in records if str(r.get("difficulty_tier") or "") == "hard"),
            }
        )
    return rows


def build_tool_difficulty_rows(raw_records: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for record in raw_records:
        groups[(str(record.get("difficulty_tier") or "unknown"), str(record.get("domain") or "unknown"))].append(record)
    rows: List[Dict[str, Any]] = []
    for (difficulty, domain), records in sorted(groups.items()):
        count = len(records)
        rows.append(
            {
                "difficulty_tier": difficulty,
                "domain": domain,
                "tool_count": count,
                "avg_num_arguments": round(sum(int(r.get("num_arguments") or 0) for r in records) / count, 4),
                "side_effect_tool_count": sum(1 for r in records if bool(r.get("has_side_effect"))),
                "enum_tool_count": sum(1 for r in records if int(r.get("num_enum_fields") or 0) > 0),
                "nested_tool_count": sum(1 for r in records if bool(r.get("has_nested_object"))),
                "avg_ambiguity_score": round(sum(float(r.get("ambiguity_score_heuristic") or 0.0) for r in records) / count, 4),
                "synthetic_count": sum(1 for r in records if (r.get("source_metadata") or {}).get("synthetic")),
            }
        )
    return rows


def build_dataset_card(raw_records: Sequence[Dict[str, Any]]) -> str:
    summary = summarize_dataset(raw_records)
    source_lines = [f"- {name}: {count}" for name, count in sorted(summary["sources"].items())]
    domain_lines = [f"- {name}: {count}" for name, count in sorted(summary["domains"].items())]
    side_effect_lines = [f"- {name}: {count}" for name, count in sorted(summary["side_effects"].items())]
    difficulty_lines = [f"- {name}: {count}" for name, count in sorted(summary["difficulties"].items())]
    return "\n".join(
        [
            "# ReliaSkill Tool-Schema Dataset Card",
            "",
            "This dataset contains normalized MCP/tool-schema definitions collected from local MCP fixtures, locally available public MCP server schemas, converted API/BFCL/API-Bank-style/ToolBench-style schemas, and explicitly marked safe synthetic MCP-like tools. Collection is deterministic and does not execute external tools.",
            "",
            "## Summary",
            "",
            f"- Total tools: {summary['total_tools']}",
            f"- Sources: {summary['source_count']}",
            f"- Domains: {summary['domain_count']}",
            f"- Servers: {summary['server_count']}",
            f"- Synthetic mock tools: {summary['synthetic_tools']}",
            f"- Synthetic fraction: {summary['synthetic_fraction']}",
            f"- Auth-required tools: {summary['auth_required_tools']}",
            f"- Side-effect tools: {summary['side_effect_tools']}",
            f"- Average arguments: {summary['avg_args']}",
            f"- Average required arguments: {summary['avg_required_args']}",
            f"- Enum fields: {summary['enum_total']}",
            "",
            "## Sources",
            "",
            *source_lines,
            "",
            "## Domains",
            "",
            *domain_lines,
            "",
            "## Side Effect Types",
            "",
            *side_effect_lines,
            "",
            "## Difficulty Tiers",
            "",
            *difficulty_lines,
            "",
            "## Complexity Features",
            "",
            "Each raw and ToolIR record includes argument counts, enum counts, nested-object and array flags, boolean flag presence, side-effect type, auth requirement, documentation length, ambiguity score heuristic, and difficulty tier.",
            "",
            "## Reproducibility",
            "",
            "- Seed: 42",
            "- Raw output: data/raw_mcp/tools.jsonl",
            "- Parsed ToolIR output: data/processed_toolir/tools.jsonl",
            "- Statistics table: outputs/tables/dataset_stats.csv",
            "- Domain complexity table: outputs/tables/domain_complexity_stats.csv",
            "- Difficulty table: outputs/tables/tool_difficulty_stats.csv",
        ]
    ) + "\n"


def write_dataset_card(path: str | Path, raw_records: Sequence[Dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_dataset_card(raw_records), encoding="utf-8")


def write_collection_outputs(config: Dict[str, Any], raw_records: Sequence[Dict[str, Any]]) -> Dict[str, str]:
    outputs = config.get("outputs") or DEFAULT_OUTPUTS
    toolir_records = parse_toolir_records(raw_records)
    write_jsonl(outputs["raw_tools"], raw_records)
    write_jsonl(outputs["toolir"], toolir_records)
    write_dataset_stats_csv(outputs["dataset_stats"], raw_records)
    write_rows_csv(
        outputs["domain_complexity_stats"],
        build_domain_complexity_rows(raw_records),
        [
            "domain",
            "tool_count",
            "avg_num_arguments",
            "avg_required_arguments",
            "enum_tool_count",
            "nested_tool_count",
            "array_tool_count",
            "boolean_flag_tool_count",
            "side_effect_tool_count",
            "auth_required_count",
            "avg_documentation_length",
            "avg_ambiguity_score",
            "hard_tool_count",
        ],
    )
    write_rows_csv(
        outputs["tool_difficulty_stats"],
        build_tool_difficulty_rows(raw_records),
        [
            "difficulty_tier",
            "domain",
            "tool_count",
            "avg_num_arguments",
            "side_effect_tool_count",
            "enum_tool_count",
            "nested_tool_count",
            "avg_ambiguity_score",
            "synthetic_count",
        ],
    )
    write_dataset_card(outputs["dataset_card"], raw_records)
    return {key: str(value) for key, value in outputs.items()}


def _build_synthetic_mock_tools(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    count = int(source.get("count") or 0)
    domains = [canonical_domain(str(domain)) for domain in list(source.get("domains") or ["synthetic"])]
    seed = int(source.get("seed") or 42)
    random.Random(seed).shuffle(domains)
    records: List[Dict[str, Any]] = []
    for index in range(count):
        domain = domains[index % len(domains)]
        slug = normalize_tool_name(domain)
        variant = index // max(1, len(domains))
        template = _synthetic_domain_template(domain, variant)
        name = f"mock_{slug}_{template['name_suffix']}_{index:03d}"
        records.append(
            {
                "server_name": f"synthetic_{slug}",
                "name": name,
                "title": name.replace("_", " ").title(),
                "description": template["description"],
                "inputSchema": template["inputSchema"],
                "domain": domain,
                "source_pointer": f"synthetic_mock:{domain}:{variant}",
            }
        )
    return records


def _synthetic_domain_template(domain: str, variant: int) -> Dict[str, Any]:
    common_policy = {
        "dry_run": {"type": "boolean", "description": "When true, validate the request without changing the mock system."}
    }
    templates: Dict[str, List[Dict[str, Any]]] = {
        "issue-tracking": [
            {
                "name_suffix": "create_ticket",
                "description": "Synthetic safe mock issue-tracking tool that creates a ticket in an offline benchmark fixture.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_key": {"type": "string", "description": "Mock project key."},
                        "title": {"type": "string", "description": "Ticket title."},
                        "priority": {"type": "string", "enum": ["low", "medium", "high"], "description": "Ticket priority."},
                        "labels": {"type": "array", "items": {"type": "string"}, "description": "Labels to attach."},
                        **common_policy,
                    },
                    "required": ["project_key", "title"],
                },
            },
            {
                "name_suffix": "search_tickets",
                "description": "Synthetic safe mock issue-tracking retrieval tool for searching offline tickets by status and assignee.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search text."},
                        "status": {"type": "string", "enum": ["open", "blocked", "closed"], "description": "Ticket status."},
                        "assignee": {"type": "string", "description": "Mock assignee username."},
                    },
                    "required": ["query"],
                },
            },
        ],
        "messaging/email mock": [
            {
                "name_suffix": "send_email",
                "description": "Synthetic safe mock email tool that records an outbound message without contacting any external service.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "array", "items": {"type": "string"}, "description": "Recipient email addresses."},
                        "subject": {"type": "string", "description": "Message subject."},
                        "body": {"type": "string", "description": "Message body."},
                        "importance": {"type": "string", "enum": ["normal", "high"], "description": "Mock importance flag."},
                        **common_policy,
                    },
                    "required": ["to", "subject", "body"],
                },
            },
            {
                "name_suffix": "search_mail",
                "description": "Synthetic safe mock mailbox search tool over local fixture messages.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Mailbox search query."},
                        "folder": {"type": "string", "enum": ["inbox", "sent", "archive"], "description": "Mailbox folder."},
                        "limit": {"type": "integer", "description": "Maximum mock messages to return."},
                    },
                    "required": ["query"],
                },
            },
        ],
        "cloud/storage mock": [
            {
                "name_suffix": "put_object",
                "description": "Synthetic safe mock cloud-storage write tool for an offline bucket fixture.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bucket": {"type": "string", "description": "Mock bucket name."},
                        "key": {"type": "string", "description": "Object key."},
                        "metadata": {
                            "type": "object",
                            "description": "Object metadata.",
                            "properties": {
                                "content_type": {"type": "string"},
                                "cache_control": {"type": "string"},
                            },
                        },
                        **common_policy,
                    },
                    "required": ["bucket", "key"],
                },
            },
            {
                "name_suffix": "list_objects",
                "description": "Synthetic safe mock cloud-storage retrieval tool for listing fixture objects.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bucket": {"type": "string", "description": "Mock bucket name."},
                        "prefix": {"type": "string", "description": "Object key prefix."},
                        "include_metadata": {"type": "boolean", "description": "Whether to include metadata."},
                    },
                    "required": ["bucket"],
                },
            },
        ],
        "system/admin mock": [
            {
                "name_suffix": "restart_service",
                "description": "Synthetic safe mock system-admin tool that simulates a service restart in an offline fixture.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "service_name": {"type": "string", "description": "Mock service name."},
                        "environment": {"type": "string", "enum": ["dev", "staging"], "description": "Allowed mock environment."},
                        "reason": {"type": "string", "description": "Operational reason."},
                        **common_policy,
                    },
                    "required": ["service_name", "environment", "reason"],
                },
            },
            {
                "name_suffix": "query_logs",
                "description": "Synthetic safe mock system-admin retrieval tool for querying offline service logs.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "service_name": {"type": "string", "description": "Mock service name."},
                        "level": {"type": "string", "enum": ["info", "warning", "error"], "description": "Log level."},
                        "window_minutes": {"type": "integer", "description": "Lookback window."},
                    },
                    "required": ["service_name"],
                },
            },
        ],
    }
    fallback = [
        {
            "name_suffix": "search",
            "description": f"Synthetic safe mock tool for the {domain} domain. This schema is marked synthetic and is intended only for benchmark scale controls.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Mock query text."},
                    "limit": {"type": "integer", "description": "Maximum number of mock results."},
                },
                "required": ["query"],
            },
        },
        {
            "name_suffix": "update",
            "description": f"Synthetic safe mock update tool for the {domain} domain. It only updates an offline fixture record.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "record_id": {"type": "string", "description": "Mock record identifier."},
                    "changes": {"type": "object", "description": "Structured fixture changes.", "properties": {"note": {"type": "string"}}},
                    **common_policy,
                },
                "required": ["record_id", "changes"],
            },
        },
    ]
    options = templates.get(domain, fallback)
    return options[variant % len(options)]

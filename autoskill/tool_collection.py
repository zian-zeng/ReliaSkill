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
    config.setdefault("sources", [])
    return config


def load_records_from_source(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    source_type = str(source.get("type") or "canonical_json")
    source_id = str(source.get("id") or source.get("path") or source_type)
    path = Path(str(source.get("path", ""))) if source.get("path") else None

    if source_type in {"canonical_json", "mcp_fixture", "converted_bfcl", "converted_toolbench", "apibank"}:
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
    max_tools = config.get("max_tools")
    if isinstance(max_tools, int) and max_tools > 0:
        deduped = deduped[:max_tools]
    validate_raw_tool_records(deduped)
    return deduped


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
    domain = source_domain or infer_domain(server, name, description, source_id)
    schema_hash = stable_schema_hash(input_schema)
    args_count, required_args_count, enum_count = schema_counts(input_schema)
    side_effect_type = infer_side_effect_type(name, description, domain)
    auth_required = infer_auth_required(record, description)
    source_pointer = record.get("source_pointer") or record.get("source_file") or source_path
    source_metadata = {
        "source_id": source_id,
        "source_type": source_type,
        "source_file": source_path,
        "source_pointer": str(source_pointer or ""),
        "source_server": server,
        "server": server,
        "tool_name": name,
        "domain": domain,
        "side_effect_type": side_effect_type,
        "auth_required": auth_required,
        "args_count": args_count,
        "required_args_count": required_args_count,
        "enum_count": enum_count,
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
        "auth_required": auth_required,
        "args_count": args_count,
        "required_args_count": required_args_count,
        "enum_count": enum_count,
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


def _count_enums(value: Any) -> int:
    if isinstance(value, dict):
        total = 1 if isinstance(value.get("enum"), list) else 0
        return total + sum(_count_enums(child) for child in value.values())
    if isinstance(value, list):
        return sum(_count_enums(child) for child in value)
    return 0


def infer_domain(server: str, name: str, description: str, source_id: str = "") -> str:
    text = f"{source_id} {server} {name} {description}".lower()
    domain_markers = [
        ("filesystem", ("filesystem", "file", "directory", "path", "folder")),
        ("data_science", ("tensorflow", "torch", "model", "dataset", "hugging", "fairseq", "inference", "transformers")),
        ("browser", ("browser", "playwright", "page", "screenshot")),
        ("search", ("search", "query", "retrieval", "rank")),
        ("git", ("git", "commit", "repository", "branch", "diff")),
        ("time", ("time", "timezone", "date", "clock")),
        ("memory", ("memory", "entity", "knowledge graph", "relation")),
        ("web", ("http", "url", "fetch", "web")),
        ("math", ("math", "calculate", "factorial", "triangle", "number")),
        ("image", ("image", "vision", "photo", "stable diffusion", "pixel")),
        ("audio", ("audio", "speech", "sound", "voice")),
        ("database", ("database", "sql", "table", "record")),
        ("communication", ("email", "message", "slack", "notification", "send")),
        ("calendar", ("calendar", "event", "schedule")),
    ]
    for domain, markers in domain_markers:
        if any(_has_marker(text, marker) for marker in markers):
            return domain
    if source_id.startswith("bfcl"):
        return "bfcl_api"
    return "general"


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
    deduped: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for record in records:
        metadata = record.get("source_metadata") or {}
        key = (
            str(metadata.get("source_server") or record.get("server_name") or ""),
            str(record.get("name") or ""),
            str(metadata.get("schema_hash") or stable_schema_hash(record.get("inputSchema") or {})),
        )
        deduped.setdefault(key, record)
    return sorted(
        deduped.values(),
        key=lambda item: (
            str((item.get("source_metadata") or {}).get("source_id") or ""),
            str(item.get("domain") or ""),
            str(item.get("server_name") or ""),
            str(item.get("name") or ""),
            str((item.get("source_metadata") or {}).get("schema_hash") or ""),
        ),
    )


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
    synthetic_count = sum(1 for record in raw_records if (record.get("source_metadata") or {}).get("synthetic"))
    auth_count = sum(1 for record in raw_records if bool(record.get("auth_required")))
    args_total = sum(int(record.get("args_count") or 0) for record in raw_records)
    required_total = sum(int(record.get("required_args_count") or 0) for record in raw_records)
    enum_total = sum(int(record.get("enum_count") or 0) for record in raw_records)
    return {
        "total_tools": len(raw_records),
        "source_count": len(sources),
        "domain_count": len(domains),
        "server_count": len(servers),
        "synthetic_tools": synthetic_count,
        "auth_required_tools": auth_count,
        "avg_args": round(args_total / len(raw_records), 4) if raw_records else 0.0,
        "avg_required_args": round(required_total / len(raw_records), 4) if raw_records else 0.0,
        "enum_total": enum_total,
        "domains": dict(sorted(domains.items())),
        "sources": dict(sorted(sources.items())),
        "servers": dict(sorted(servers.items())),
        "side_effects": dict(sorted(side_effects.items())),
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
        rows.append(
            {
                "source_id": source_id,
                "domain": domain,
                "side_effect_type": side_effect_type,
                "tool_count": len(records),
                "server_count": len({record.get("server_name") for record in records}),
                "auth_required_count": auth_count,
                "synthetic_count": synthetic_count,
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
        "avg_args",
        "avg_required_args",
        "enum_count",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_dataset_card(raw_records: Sequence[Dict[str, Any]]) -> str:
    summary = summarize_dataset(raw_records)
    source_lines = [f"- {name}: {count}" for name, count in sorted(summary["sources"].items())]
    domain_lines = [f"- {name}: {count}" for name, count in sorted(summary["domains"].items())]
    side_effect_lines = [f"- {name}: {count}" for name, count in sorted(summary["side_effects"].items())]
    return "\n".join(
        [
            "# ReliaSkill Tool-Schema Dataset Card",
            "",
            "This dataset contains normalized MCP/tool-schema definitions collected from local fixtures and locally stored converted benchmark schemas. Collection is deterministic and does not execute external tools.",
            "",
            "## Summary",
            "",
            f"- Total tools: {summary['total_tools']}",
            f"- Sources: {summary['source_count']}",
            f"- Domains: {summary['domain_count']}",
            f"- Servers: {summary['server_count']}",
            f"- Synthetic mock tools: {summary['synthetic_tools']}",
            f"- Auth-required tools: {summary['auth_required_tools']}",
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
            "## Reproducibility",
            "",
            "- Seed: 42",
            "- Raw output: data/raw_mcp/tools.jsonl",
            "- Parsed ToolIR output: data/processed_toolir/tools.jsonl",
            "- Statistics table: outputs/tables/dataset_stats.csv",
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
    write_dataset_card(outputs["dataset_card"], raw_records)
    return {key: str(value) for key, value in outputs.items()}


def _build_synthetic_mock_tools(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    count = int(source.get("count") or 0)
    domains = list(source.get("domains") or ["synthetic"])
    records: List[Dict[str, Any]] = []
    for index in range(count):
        domain = domains[index % len(domains)]
        name = f"mock_{domain}_tool_{index:03d}"
        records.append(
            {
                "server_name": f"synthetic_{domain}",
                "name": name,
                "title": name.replace("_", " ").title(),
                "description": f"Synthetic safe mock tool for the {domain} domain. This schema is marked synthetic and is intended only for benchmark scale controls.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Mock query text."},
                        "limit": {"type": "integer", "description": "Maximum number of mock results."},
                    },
                    "required": ["query"],
                },
            }
        )
    return records

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

from reliaskill.converters.common import (
    SOURCE_NAMES,
    infer_schema_from_signature,
    load_json_or_jsonl,
    make_conversion_record,
    make_mcp_tool,
    schema_from_arguments,
    slugify,
)


def convert_bfcl(input_root: str | Path, *, strict: bool = False) -> Tuple[List[Dict[str, Any]], Counter[str], List[str]]:
    root = _bfcl_root(Path(input_root))
    skipped: Counter[str] = Counter()
    warnings: List[str] = []
    if root is None:
        message = "bfcl: missing data/external/bfcl or BFCL data directory"
        if strict:
            raise FileNotFoundError(message)
        return [], skipped, [message]

    records: List[Dict[str, Any]] = []
    registry: Dict[str, Dict[str, Any]] = {}

    api_dir = root / "api"
    for path in sorted(api_dir.glob("*.json*")) if api_dir.exists() else []:
        for index, item in enumerate(load_json_or_jsonl(path)):
            converted = _convert_api_record(item, source_path=path, record_index=index, split=None)
            if converted is None:
                skipped["missing_api_identity"] += 1
                continue
            registry[_signature_key(converted["original_function_signature"])] = converted
            records.append(converted)

    apibench_dir = root / "apibench"
    for path in sorted(apibench_dir.glob("*.json*")) if apibench_dir.exists() else []:
        split = "test" if "eval" in path.stem.lower() else "train" if "train" in path.stem.lower() else None
        for index, item in enumerate(load_json_or_jsonl(path)):
            converted = _convert_apibench_record(item, source_path=path, record_index=index, split=split, registry=registry)
            if converted is None:
                skipped["missing_gold_or_api_data"] += 1
                continue
            records.append(converted)

    if not records:
        warnings.append(f"bfcl: found {root} but converted no usable records")
    return records, skipped, warnings


def _bfcl_root(input_root: Path) -> Path | None:
    candidates = [
        input_root / "bfcl" / "data",
        input_root / "BFCL" / "data",
        input_root / "data",
        input_root,
    ]
    for candidate in candidates:
        if (candidate / "api").exists() or (candidate / "apibench").exists():
            return candidate
    return None


def _convert_api_record(item: Dict[str, Any], *, source_path: Path, record_index: int, split: str | None) -> Dict[str, Any] | None:
    api_data = item.get("api_data") if isinstance(item.get("api_data"), dict) else item
    api_call = str(item.get("api_call") or api_data.get("api_call") or "").strip()
    api_name = str(api_data.get("api_name") or api_call or "").strip()
    provider = str(item.get("provider") or api_data.get("framework") or "bfcl").strip()
    if not api_call and not api_name:
        return None
    tool_id = _tool_id(provider, api_name, api_call)
    schema = schema_from_arguments(api_data.get("api_arguments"))
    if not schema.get("properties"):
        schema = infer_schema_from_signature(api_call)
    description = _description(api_data, provider, api_call)
    benchmark_id = f"{source_path.as_posix()}#{record_index}"
    mcp_tool = make_mcp_tool(
        tool_id=tool_id,
        source_type="bfcl",
        source_name=SOURCE_NAMES["bfcl"],
        original_benchmark_id=benchmark_id,
        original_tool_name=api_name or api_call,
        original_function_signature=api_call,
        description=description,
        normalized_schema=schema,
        source_path=str(source_path),
        extra_metadata={"split_suggestion": split, "domain": api_data.get("domain"), "framework": provider},
    )
    return make_conversion_record(
        tool_id=tool_id,
        source_type="bfcl",
        source_name=SOURCE_NAMES["bfcl"],
        original_benchmark_id=benchmark_id,
        original_tool_name=api_name or api_call,
        original_function_signature=api_call,
        normalized_schema=schema,
        mcp_tool=mcp_tool,
        split_suggestion=split,
        metadata={"source_path": str(source_path), "domain": api_data.get("domain"), "framework": provider},
    )


def _convert_apibench_record(
    item: Dict[str, Any],
    *,
    source_path: Path,
    record_index: int,
    split: str | None,
    registry: Dict[str, Dict[str, Any]],
) -> Dict[str, Any] | None:
    api_data = item.get("api_data") if isinstance(item.get("api_data"), dict) else {}
    api_call = str(item.get("api_call") or api_data.get("api_call") or "").strip()
    provider = str(item.get("provider") or api_data.get("framework") or "bfcl").strip()
    api_name = str(api_data.get("api_name") or api_call or "").strip()
    instruction = _extract_instruction(str(item.get("code") or item.get("question") or ""))
    if not api_call or not instruction:
        return None

    existing = registry.get(_signature_key(api_call))
    if existing:
        tool_id = existing["tool_id"]
        schema = existing["normalized_schema"]
        original_tool_name = existing["original_tool_name"]
        description = existing["mcp_tool_schema"].get("description") or original_tool_name
    else:
        tool_id = _tool_id(provider, api_name, api_call)
        schema = schema_from_arguments(api_data.get("api_arguments"))
        if not schema.get("properties"):
            schema = infer_schema_from_signature(api_call)
        original_tool_name = api_name or api_call
        description = _description(api_data, provider, api_call)

    benchmark_id = str(item.get("id") or item.get("uuid") or f"{source_path.as_posix()}#{record_index}")
    gold = {"name": tool_id, "original_name": api_call, "arguments": _gold_arguments_from_signature(schema, api_call)}
    mcp_tool = make_mcp_tool(
        tool_id=tool_id,
        source_type="bfcl",
        source_name=SOURCE_NAMES["bfcl"],
        original_benchmark_id=benchmark_id,
        original_tool_name=original_tool_name,
        original_function_signature=api_call,
        description=description,
        normalized_schema=schema,
        source_path=str(source_path),
        extra_metadata={"split_suggestion": split, "domain": api_data.get("domain"), "framework": provider},
    )
    return make_conversion_record(
        tool_id=tool_id,
        source_type="bfcl",
        source_name=SOURCE_NAMES["bfcl"],
        original_benchmark_id=benchmark_id,
        original_tool_name=original_tool_name,
        original_function_signature=api_call,
        normalized_schema=schema,
        natural_language_request=instruction,
        gold_tool_call=gold,
        split_suggestion=split,
        mcp_tool=mcp_tool,
        metadata={"source_path": str(source_path), "domain": api_data.get("domain"), "framework": provider},
    )


def _tool_id(provider: str, api_name: str, api_call: str) -> str:
    return slugify(f"bfcl_{provider}_{api_name or api_call}", max_length=100)


def _signature_key(signature: str) -> str:
    return re.sub(r"\s+", "", signature or "").lower()


def _extract_instruction(code: str) -> str | None:
    match = re.search(r"###Instruction:\s*(.*?)\s*###Output:", code, flags=re.DOTALL)
    if match:
        return " ".join(match.group(1).split())
    text = " ".join(code.split())
    return text or None


def _description(api_data: Dict[str, Any], provider: str, api_call: str) -> str:
    pieces = [
        str(api_data.get("description") or "").strip(),
        f"Framework: {provider}.",
        f"Functionality: {api_data.get('functionality', 'unknown')}.",
        f"Original API call: {api_call}.",
    ]
    return " ".join(piece for piece in pieces if piece)


def _gold_arguments_from_signature(schema: Dict[str, Any], signature: str) -> Dict[str, Any]:
    properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    if not properties:
        return {}
    values: Dict[str, Any] = {}
    for name in properties:
        pattern = rf"{re.escape(name)}\s*=\s*([^,\)]+)"
        match = re.search(pattern, signature)
        if match:
            values[name] = match.group(1).strip().strip("'\"")
    return values

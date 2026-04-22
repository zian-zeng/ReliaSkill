from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


def load_loose_json_records(path: str | Path) -> List[Dict[str, Any]]:
    input_path = Path(path)
    text = input_path.read_text(encoding="utf-8")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        records: List[Dict[str, Any]] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                records.append(value)
        return records

    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    if isinstance(parsed, dict):
        for key in ("data", "items", "tools"):
            value = parsed.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [parsed]
    return []


def _slugify(value: str) -> str:
    lowered = value.lower()
    lowered = re.sub(r"[^a-z0-9]+", "_", lowered)
    return lowered.strip("_")


def _quoted_strings(text: str) -> List[str]:
    return [match.group(2) for match in re.finditer(r"(['\"])(.*?)\1", text, flags=re.DOTALL)]


def _join_string_fragments(text: str) -> str:
    fragments = _quoted_strings(text)
    if fragments:
        return " ".join(fragment.strip() for fragment in fragments if fragment.strip())
    return text.strip()


def _find_matching(text: str, start_index: int, open_char: str, close_char: str) -> int:
    depth = 0
    quote: str | None = None
    escaped = False
    for index in range(start_index, len(text)):
        char = text[index]
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {"'", '"', "`"}:
            quote = char
            continue
        if char == open_char:
            depth += 1
        elif char == close_char:
            depth -= 1
            if depth == 0:
                return index
    raise ValueError(f"Failed to match {open_char}{close_char} block")


def _split_top_level(text: str, delimiter: str = ",") -> List[str]:
    parts: List[str] = []
    start = 0
    paren = 0
    brace = 0
    bracket = 0
    quote: str | None = None
    escaped = False
    for index, char in enumerate(text):
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {"'", '"', "`"}:
            quote = char
            continue
        if char == "(":
            paren += 1
        elif char == ")":
            paren -= 1
        elif char == "{":
            brace += 1
        elif char == "}":
            brace -= 1
        elif char == "[":
            bracket += 1
        elif char == "]":
            bracket -= 1
        elif char == delimiter and paren == 0 and brace == 0 and bracket == 0:
            part = text[start:index].strip()
            if part:
                parts.append(part)
            start = index + 1
    tail = text[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def _split_first_top_level(text: str, delimiter: str = ":") -> Tuple[str, str] | None:
    paren = 0
    brace = 0
    bracket = 0
    quote: str | None = None
    escaped = False
    for index, char in enumerate(text):
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {"'", '"', "`"}:
            quote = char
            continue
        if char == "(":
            paren += 1
        elif char == ")":
            paren -= 1
        elif char == "{":
            brace += 1
        elif char == "}":
            brace -= 1
        elif char == "[":
            bracket += 1
        elif char == "]":
            bracket -= 1
        elif char == delimiter and paren == 0 and brace == 0 and bracket == 0:
            return text[:index].strip(), text[index + 1 :].strip()
    return None


def _remove_method_calls(expr: str, method_names: Iterable[str]) -> str:
    result = expr
    for method_name in method_names:
        pattern = f".{method_name}"
        while True:
            index = result.find(pattern)
            if index < 0:
                break
            end_index = index + len(pattern)
            if end_index < len(result) and result[end_index] == "(":
                close_index = _find_matching(result, end_index, "(", ")")
                result = result[:index] + result[close_index + 1 :]
            elif result[end_index : end_index + 2] == "()":
                result = result[:index] + result[end_index + 2 :]
            else:
                break
    return result


def _parse_ts_schema_expr(expr: str, schema_defs: Dict[str, Dict[str, Any]]) -> Tuple[Dict[str, Any], bool]:
    raw_expr = expr.strip().rstrip(",")
    has_optional = re.search(r"\.optional\s*\(", raw_expr) is not None
    has_default = re.search(r"\.default\s*\(", raw_expr) is not None
    required = not (has_optional or has_default)
    nullable = ".nullable()" in raw_expr
    cleaned = _remove_method_calls(
        raw_expr,
        [
            "describe",
            "default",
            "optional",
            "nullable",
            "min",
            "max",
            "int",
            "nonempty",
            "readonly",
        ],
    ).strip()

    if cleaned.endswith(".shape"):
        cleaned = cleaned[: -len(".shape")].strip()
    if cleaned in schema_defs:
        schema = dict(schema_defs[cleaned])
        if nullable:
            schema["nullable"] = True
        return schema, required

    if cleaned.startswith("z.object("):
        brace_index = cleaned.find("{")
        close_index = _find_matching(cleaned, brace_index, "{", "}")
        schema = _parse_ts_object_schema(cleaned[brace_index + 1 : close_index], schema_defs)
        if nullable:
            schema["nullable"] = True
        return schema, required

    if cleaned.startswith("{") and cleaned.endswith("}"):
        schema = _parse_ts_object_schema(cleaned[1:-1], schema_defs)
        if nullable:
            schema["nullable"] = True
        return schema, required

    if cleaned.startswith("z.array("):
        inner_start = cleaned.find("(")
        inner_end = _find_matching(cleaned, inner_start, "(", ")")
        item_schema, _ = _parse_ts_schema_expr(cleaned[inner_start + 1 : inner_end], schema_defs)
        schema = {"type": "array", "items": item_schema}
        if nullable:
            schema["nullable"] = True
        return schema, required

    if cleaned.startswith("z.enum("):
        bracket_index = cleaned.find("[")
        bracket_end = _find_matching(cleaned, bracket_index, "[", "]")
        enum_values = ast.literal_eval(cleaned[bracket_index : bracket_end + 1])
        schema = {"type": "string", "enum": list(enum_values)}
        if nullable:
            schema["nullable"] = True
        return schema, required

    if cleaned.startswith("z.literal("):
        start = cleaned.find("(")
        end = _find_matching(cleaned, start, "(", ")")
        literal_value = ast.literal_eval(cleaned[start + 1 : end])
        literal_type = "string" if isinstance(literal_value, str) else "number" if isinstance(literal_value, (int, float)) else "boolean"
        schema = {"type": literal_type, "enum": [literal_value]}
        if nullable:
            schema["nullable"] = True
        return schema, required

    if cleaned.startswith("z.string(") or cleaned == "z.string()":
        schema = {"type": "string"}
    elif cleaned.startswith("z.number(") or cleaned == "z.number()":
        schema = {"type": "number"}
    elif cleaned.startswith("z.boolean(") or cleaned == "z.boolean()":
        schema = {"type": "boolean"}
    elif cleaned.startswith("z.any(") or cleaned == "z.any()":
        schema = {}
    else:
        schema = {"type": "string"}

    if nullable:
        schema["nullable"] = True
    return schema, required


def _parse_ts_object_schema(body: str, schema_defs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    properties: Dict[str, Any] = {}
    required: List[str] = []
    for field_text in _split_top_level(body):
        pair = _split_first_top_level(field_text, ":")
        if not pair:
            continue
        raw_name, raw_expr = pair
        field_name = raw_name.strip().strip("'\"`")
        field_schema, is_required = _parse_ts_schema_expr(raw_expr, schema_defs)
        properties[field_name] = field_schema
        if is_required:
            required.append(field_name)
    result: Dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        result["required"] = required
    return result


def _collect_ts_schema_defs(text: str) -> Dict[str, Dict[str, Any]]:
    schema_defs: Dict[str, Dict[str, Any]] = {}
    for match in re.finditer(r"const\s+([A-Za-z0-9_]+)\s*=\s*z\.object\s*\(", text):
        schema_name = match.group(1)
        brace_index = text.find("{", match.end())
        if brace_index < 0:
            continue
        close_index = _find_matching(text, brace_index, "{", "}")
        schema_defs[schema_name] = _parse_ts_object_schema(text[brace_index + 1 : close_index], schema_defs)
    return schema_defs


def _collect_ts_const_expressions(text: str) -> Dict[str, str]:
    consts: Dict[str, str] = {}
    for match in re.finditer(r"const\s+([A-Za-z0-9_]+)\s*=\s*", text):
        name = match.group(1)
        start = match.end()
        semicolon_index = None
        paren = 0
        brace = 0
        bracket = 0
        quote: str | None = None
        escaped = False
        for index in range(start, len(text)):
            char = text[index]
            if quote is not None:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = None
                continue
            if char in {"'", '"', "`"}:
                quote = char
                continue
            if char == "(":
                paren += 1
            elif char == ")":
                paren -= 1
            elif char == "{":
                brace += 1
            elif char == "}":
                brace -= 1
            elif char == "[":
                bracket += 1
            elif char == "]":
                bracket -= 1
            elif char == ";" and paren == 0 and brace == 0 and bracket == 0:
                semicolon_index = index
                break
        if semicolon_index is None:
            continue
        consts[name] = text[start:semicolon_index].strip()
    return consts


def _ts_expr_to_string(expr: str, consts: Dict[str, str]) -> str:
    cleaned = expr.strip()
    if cleaned in consts:
        return _ts_expr_to_string(consts[cleaned], consts)
    return _join_string_fragments(cleaned)


def _ts_config_to_tool_record(name_expr: str, config_expr: str, consts: Dict[str, str], schema_defs: Dict[str, Dict[str, Any]], server_name: str, source_pointer: str) -> Dict[str, Any] | None:
    tool_name = _ts_expr_to_string(name_expr, consts).strip()
    if not tool_name:
        return None

    config_text = consts.get(config_expr.strip(), config_expr.strip())
    if not config_text.startswith("{"):
        return None
    fields: Dict[str, str] = {}
    for field_text in _split_top_level(config_text[1:-1]):
        pair = _split_first_top_level(field_text, ":")
        if not pair:
            continue
        key, value = pair
        fields[key.strip()] = value.strip()

    description = _ts_expr_to_string(fields.get("description", ""), consts)
    title = _ts_expr_to_string(fields.get("title", ""), consts)
    input_expr = fields.get("inputSchema", "{}")
    input_schema, _ = _parse_ts_schema_expr(input_expr, schema_defs)
    return {
        "server_name": server_name,
        "name": tool_name,
        "title": title or tool_name,
        "summary": description,
        "description": description,
        "inputSchema": input_schema,
        "source_pointer": source_pointer,
    }


def harvest_typescript_mcp_tools(paths: Iterable[str | Path]) -> List[Dict[str, Any]]:
    harvested: List[Dict[str, Any]] = []
    for path in paths:
        file_path = Path(path)
        text = file_path.read_text(encoding="utf-8")
        schema_defs = _collect_ts_schema_defs(text)
        consts = _collect_ts_const_expressions(text)
        server_name = file_path.parts[-2]

        for match in re.finditer(r"registerTool\s*\(", text):
            try:
                open_index = text.find("(", match.start())
                end_index = _find_matching(text, open_index, "(", ")")
                call_body = text[open_index + 1 : end_index]
                args = _split_top_level(call_body)
                if len(args) < 2:
                    continue
                record = _ts_config_to_tool_record(
                    name_expr=args[0],
                    config_expr=args[1],
                    consts=consts,
                    schema_defs=schema_defs,
                    server_name=server_name,
                    source_pointer=str(file_path),
                )
                if record is not None:
                    harvested.append(record)
            except ValueError:
                continue
    return harvested


def _resolve_python_type(node: ast.AST) -> Tuple[Dict[str, Any], bool]:
    if isinstance(node, ast.Name):
        mapping = {
            "str": {"type": "string"},
            "int": {"type": "integer"},
            "float": {"type": "number"},
            "bool": {"type": "boolean"},
        }
        return mapping.get(node.id, {"type": "string"}), False
    if isinstance(node, ast.Subscript):
        if isinstance(node.value, ast.Name) and node.value.id in {"list", "List"}:
            item_schema, _ = _resolve_python_type(node.slice)
            return {"type": "array", "items": item_schema}, False
        if isinstance(node.value, ast.Name) and node.value.id == "Optional":
            inner_schema, _ = _resolve_python_type(node.slice)
            inner_schema["nullable"] = True
            return inner_schema, True
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        left_schema, left_nullable = _resolve_python_type(node.left)
        right_schema, right_nullable = _resolve_python_type(node.right)
        if isinstance(node.right, ast.Constant) and node.right.value is None:
            left_schema["nullable"] = True
            return left_schema, True
        if isinstance(node.left, ast.Constant) and node.left.value is None:
            right_schema["nullable"] = True
            return right_schema, True
        left_schema["nullable"] = left_nullable or right_nullable
        return left_schema, left_nullable or right_nullable
    return {"type": "string"}, False


def _ast_to_python_value(node: ast.AST, enums: Dict[str, str], model_schemas: Dict[str, Dict[str, Any]]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Dict):
        return {
            _ast_to_python_value(key, enums, model_schemas): _ast_to_python_value(value, enums, model_schemas)
            for key, value in zip(node.keys, node.values)
            if key is not None
        }
    if isinstance(node, ast.List):
        return [_ast_to_python_value(item, enums, model_schemas) for item in node.elts]
    if isinstance(node, ast.Tuple):
        return [_ast_to_python_value(item, enums, model_schemas) for item in node.elts]
    if isinstance(node, ast.JoinedStr):
        parts: List[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant):
                parts.append(str(value.value))
            elif isinstance(value, ast.FormattedValue):
                rendered = ast.unparse(value.value) if hasattr(ast, "unparse") else "<expr>"
                parts.append(f"<{rendered}>")
        return "".join(parts)
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Attribute) and node.func.attr == "model_json_schema" and isinstance(node.func.value, ast.Name):
            return model_schemas.get(node.func.value.id, {})
        if isinstance(node.func, ast.Name) and node.func.id == "Field":
            for keyword in node.keywords:
                if keyword.arg == "description":
                    return _ast_to_python_value(keyword.value, enums, model_schemas)
            if node.args:
                return _ast_to_python_value(node.args[0], enums, model_schemas)
            return None
    if isinstance(node, ast.Attribute):
        rendered = ast.unparse(node) if hasattr(ast, "unparse") else ""
        if rendered in enums:
            return enums[rendered]
        return rendered
    if isinstance(node, ast.Name):
        if node.id in enums:
            return enums[node.id]
        return node.id
    if hasattr(ast, "unparse"):
        return ast.unparse(node)
    return None


def _collect_python_enums(tree: ast.AST) -> Dict[str, str]:
    enums: Dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        is_enum = any(
            (isinstance(base, ast.Name) and base.id == "Enum")
            or (isinstance(base, ast.Name) and base.id == "str")
            or (isinstance(base, ast.Attribute) and base.attr == "Enum")
            for base in node.bases
        )
        if not is_enum:
            continue
        for statement in node.body:
            if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name):
                target_name = statement.targets[0].id
                value = _ast_to_python_value(statement.value, enums, {})
                if isinstance(value, str):
                    enums[f"{node.name}.{target_name}.value"] = value
                    enums[f"{node.name}.{target_name}"] = value
    return enums


def _collect_pydantic_model_schemas(tree: ast.AST, enums: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
    schemas: Dict[str, Dict[str, Any]] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        is_model = any(
            (isinstance(base, ast.Name) and base.id == "BaseModel")
            or (isinstance(base, ast.Attribute) and base.attr == "BaseModel")
            for base in node.bases
        )
        if not is_model:
            continue
        properties: Dict[str, Any] = {}
        required: List[str] = []
        for statement in node.body:
            if not isinstance(statement, ast.AnnAssign) or not isinstance(statement.target, ast.Name):
                continue
            field_name = statement.target.id
            field_schema, nullable = _resolve_python_type(statement.annotation)
            if statement.value is None:
                required.append(field_name)
            elif isinstance(statement.value, ast.Call) and isinstance(statement.value.func, ast.Name) and statement.value.func.id == "Field":
                description = None
                is_required = False
                if statement.value.args:
                    first_arg = statement.value.args[0]
                    if isinstance(first_arg, ast.Constant) and first_arg.value is Ellipsis:
                        is_required = True
                for keyword in statement.value.keywords:
                    if keyword.arg == "description":
                        description = _ast_to_python_value(keyword.value, enums, schemas)
                if description:
                    field_schema["description"] = description
                if is_required:
                    required.append(field_name)
            elif isinstance(statement.value, ast.Constant) and statement.value.value is None and nullable:
                field_schema["nullable"] = True
            properties[field_name] = field_schema
        schema: Dict[str, Any] = {"type": "object", "properties": properties}
        if required:
            schema["required"] = required
        schemas[node.name] = schema
    return schemas


def harvest_python_mcp_tools(paths: Iterable[str | Path]) -> List[Dict[str, Any]]:
    harvested: List[Dict[str, Any]] = []
    for path in paths:
        file_path = Path(path)
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
        enums = _collect_python_enums(tree)
        model_schemas = _collect_pydantic_model_schemas(tree, enums)
        server_name = file_path.parts[-3] if len(file_path.parts) >= 3 else file_path.stem
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not ((isinstance(node.func, ast.Name) and node.func.id == "Tool") or (isinstance(node.func, ast.Attribute) and node.func.attr == "Tool")):
                continue
            keywords = {keyword.arg: keyword.value for keyword in node.keywords if keyword.arg}
            name = _ast_to_python_value(keywords.get("name"), enums, model_schemas)
            description = _ast_to_python_value(keywords.get("description"), enums, model_schemas)
            input_schema = _ast_to_python_value(keywords.get("inputSchema"), enums, model_schemas)
            if not isinstance(name, str) or not isinstance(description, str) or not isinstance(input_schema, dict):
                continue
            harvested.append(
                {
                    "server_name": server_name,
                    "name": name,
                    "title": name,
                    "summary": description,
                    "description": description,
                    "inputSchema": input_schema,
                    "source_pointer": str(file_path),
                }
            )
    return harvested


def dedupe_tool_records(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped: Dict[Tuple[str | None, str], Dict[str, Any]] = {}
    for record in records:
        key = (record.get("server_name"), str(record.get("name")))
        deduped.setdefault(key, record)
    return list(deduped.values())


def harvest_reference_mcp_servers(repo_root: str | Path) -> List[Dict[str, Any]]:
    root = Path(repo_root)
    ts_paths = [
        root / "src" / "filesystem" / "index.ts",
        root / "src" / "memory" / "index.ts",
        root / "src" / "everything" / "tools" / "echo.ts",
        root / "src" / "everything" / "tools" / "get-annotated-message.ts",
        root / "src" / "everything" / "tools" / "get-env.ts",
        root / "src" / "everything" / "tools" / "get-resource-links.ts",
        root / "src" / "everything" / "tools" / "get-resource-reference.ts",
        root / "src" / "everything" / "tools" / "get-roots-list.ts",
        root / "src" / "everything" / "tools" / "get-structured-content.ts",
        root / "src" / "everything" / "tools" / "get-sum.ts",
        root / "src" / "everything" / "tools" / "get-tiny-image.ts",
        root / "src" / "everything" / "tools" / "gzip-file-as-resource.ts",
        root / "src" / "everything" / "tools" / "simulate-research-query.ts",
        root / "src" / "everything" / "tools" / "toggle-simulated-logging.ts",
        root / "src" / "everything" / "tools" / "toggle-subscriber-updates.ts",
        root / "src" / "everything" / "tools" / "trigger-elicitation-request.ts",
        root / "src" / "everything" / "tools" / "trigger-elicitation-request-async.ts",
        root / "src" / "everything" / "tools" / "trigger-long-running-operation.ts",
        root / "src" / "everything" / "tools" / "trigger-sampling-request.ts",
        root / "src" / "everything" / "tools" / "trigger-sampling-request-async.ts",
    ]
    py_paths = [
        root / "src" / "fetch" / "src" / "mcp_server_fetch" / "server.py",
        root / "src" / "git" / "src" / "mcp_server_git" / "server.py",
        root / "src" / "time" / "src" / "mcp_server_time" / "server.py",
    ]
    records: List[Dict[str, Any]] = []
    records.extend(harvest_typescript_mcp_tools(path for path in ts_paths if path.exists()))
    records.extend(harvest_python_mcp_tools(path for path in py_paths if path.exists()))
    return dedupe_tool_records(records)


def extract_bfcl_instruction(code: str) -> str:
    match = re.search(r"###Instruction:\s*(.*?)\s*###Output:", code, flags=re.DOTALL)
    if match:
        return match.group(1).strip()
    return code.strip()


def make_bfcl_tool_id(provider: str, api_call: str, api_name: str) -> str:
    pieces = [_slugify(provider), _slugify(api_name), _slugify(api_call)]
    import hashlib
    compact = "__".join(piece for piece in pieces if piece)
    if len(compact) > 80:
        h = hashlib.md5(compact.encode()).hexdigest()[:8]
        return f"{compact[:70]}_{h}"
    return compact


def build_bfcl_tool_records(records: Iterable[Dict[str, Any]], server_name: str = "bfcl_huggingface_api") -> List[Dict[str, Any]]:
    tools: Dict[str, Dict[str, Any]] = {}
    for record in records:
        api_data = record.get("api_data", {})
        if not isinstance(api_data, dict):
            continue
        provider = str(record.get("provider") or api_data.get("framework") or "bfcl")
        api_call = str(record.get("api_call") or api_data.get("api_call") or "")
        api_name = str(api_data.get("api_name") or api_call or "")
        if not api_call or not api_name:
            continue
        tool_id = make_bfcl_tool_id(provider, api_call, api_name)
        description_parts = [
            str(api_data.get("description") or "").strip(),
            f"Framework: {api_data.get('framework', provider)}.",
            f"Functionality: {api_data.get('functionality', 'unknown')}.",
            f"API call: {api_call}.",
        ]
        description = " ".join(part for part in description_parts if part)
        tools.setdefault(
            tool_id,
            {
                "server_name": server_name,
                "name": tool_id,
                "title": api_name,
                "summary": str(api_data.get("functionality") or api_name),
                "description": description,
                "inputSchema": {"type": "object", "properties": {}},
                "source_pointer": "bfcl",
            },
        )
    return list(tools.values())


def build_bfcl_routing_tasks(records: Iterable[Dict[str, Any]], split: str) -> List[Dict[str, Any]]:
    tasks: List[Dict[str, Any]] = []
    for index, record in enumerate(records):
        api_data = record.get("api_data", {})
        if not isinstance(api_data, dict):
            continue
        provider = str(record.get("provider") or api_data.get("framework") or "bfcl")
        api_call = str(record.get("api_call") or api_data.get("api_call") or "")
        api_name = str(api_data.get("api_name") or api_call or "")
        if not api_call or not api_name:
            continue
        tool_id = make_bfcl_tool_id(provider, api_call, api_name)
        instruction = extract_bfcl_instruction(str(record.get("code") or ""))
        domain_tag = _slugify(str(api_data.get("domain") or "unknown"))
        framework_tag = _slugify(str(api_data.get("framework") or provider))
        tasks.append(
            {
                "task_id": f"bfcl_{split}_{index}",
                "tool_name": tool_id,
                "user_request": instruction,
                "expected_arguments": {},
                "expected_argument_candidates": [{}],
                "split": split,
                "tags": ["bfcl", framework_tag, domain_tag],
            }
        )
    return tasks

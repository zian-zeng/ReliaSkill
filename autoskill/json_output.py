from __future__ import annotations

import json
import re
from typing import Any, Dict


def _strip_code_fences(text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    return text.strip()


def _extract_balanced_json_object(text: str) -> str:
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in model output.")

    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    raise ValueError("Unbalanced JSON object in model output.")


def parse_json_object_output(text: str) -> Dict[str, Any]:
    cleaned = _strip_code_fences(text)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        value = json.loads(_extract_balanced_json_object(cleaned))

    if not isinstance(value, dict):
        raise ValueError("Model output did not decode to a JSON object.")
    return value

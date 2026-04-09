from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class EvalTask:
    task_id: str
    tool_name: str
    user_request: str
    expected_arguments: Dict[str, Any] = field(default_factory=dict)
    expected_argument_candidates: List[Dict[str, Any]] = field(default_factory=list)
    split: str = "default"
    tags: List[str] = field(default_factory=list)


@dataclass
class EvalPrediction:
    task_id: str
    tool_name: str
    baseline_name: str
    predicted_arguments: Dict[str, Any] = field(default_factory=dict)
    exposure_text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

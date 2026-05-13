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
    should_trigger: bool = True
    expected_tool_name: str | None = None
    negative_target: str | None = None
    negative_category: str | None = None
    difficulty: str | None = None
    domain: str | None = None
    harm_baseline: str | None = None
    split: str = "default"
    tags: List[str] = field(default_factory=list)


@dataclass
class EvalPrediction:
    task_id: str
    tool_name: str
    baseline_name: str
    predicted_arguments: Dict[str, Any] = field(default_factory=dict)
    should_call: bool = True
    abstention_reason: str | None = None
    exposure_text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ArgumentIR:
    name: str
    type: str = "unknown"
    required: bool = False
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None
    description: Optional[str] = None
    items_type: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    required_properties: List[str] = field(default_factory=list)
    nullable: bool = False
    format: Optional[str] = None
    schema_path: Optional[str] = None

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ToolIR:
    tool_name: str
    server_name: Optional[str] = None
    tool_purpose: Optional[str] = None
    input_schema_raw: Dict[str, Any] = field(default_factory=dict)
    arguments: List[ArgumentIR] = field(default_factory=list)
    output_hint: Optional[str] = None
    auth_or_env_notes: Optional[str] = None
    usage_warnings: List[str] = field(default_factory=list)
    doc_snippets: List[str] = field(default_factory=list)
    source_pointer: Optional[str] = None

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GeneratedSkill:
    baseline_name: str = "autoskill_base"
    skill_summary: str = ""
    when_to_use: List[str] = field(default_factory=list)
    when_not_to_use: List[str] = field(default_factory=list)
    argument_template: Dict[str, Any] = field(default_factory=dict)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    semantic_hints: Dict[str, Any] = field(default_factory=dict)
    method_trace: List[Dict[str, Any]] = field(default_factory=list)

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationIssue:
    severity: str
    code: str
    message: str
    location: Optional[str] = None

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationReport:
    valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)

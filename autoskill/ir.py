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
    doc_completeness: float = 0.0
    schema_complexity: Dict[str, Any] = field(default_factory=dict)
    ambiguity_flags: List[str] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)
    side_effect_hints: List[str] = field(default_factory=list)
    safety_hints: List[str] = field(default_factory=list)

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
    metadata: Dict[str, Any] = field(default_factory=dict)

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationIssue:
    severity: str
    code: str
    message: str
    location: Optional[str] = None
    section: Optional[str] = None
    repairable: bool = False
    evidence: Dict[str, Any] = field(default_factory=dict)

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationReport:
    valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BehaviorCase:
    case_id: str
    tool_name: str
    user_request: str
    should_trigger: bool = True
    expected_arguments: Dict[str, Any] = field(default_factory=dict)
    expected_argument_candidates: List[Dict[str, Any]] = field(default_factory=list)
    expected_tool_name: Optional[str] = None
    negative_target: Optional[str] = None
    harm_baseline: Optional[str] = None
    split: str = "default"
    tags: List[str] = field(default_factory=list)

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BehaviorResult:
    case_id: str
    tool_name: str
    should_trigger: bool
    triggered: bool
    user_request: str = ""
    exact_match: bool = False
    argument_validity: float = 0.0
    harmful_injection: bool = False
    predicted_arguments: Dict[str, Any] = field(default_factory=dict)
    expected_arguments: Dict[str, Any] = field(default_factory=dict)
    prediction_latency_ms: float = 0.0
    notes: List[str] = field(default_factory=list)
    prediction_metadata: Dict[str, Any] = field(default_factory=dict)

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BehaviorReport:
    valid: bool
    results: List[BehaviorResult] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RepairAction:
    action_type: str
    section: str
    issue_code: str
    description: str

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RepairReport:
    attempted: bool
    changed: bool
    rounds: int = 0
    actions: List[RepairAction] = field(default_factory=list)
    remaining_issues: List[ValidationIssue] = field(default_factory=list)

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReliabilityScore:
    score: float
    decision: str
    features: Dict[str, Any] = field(default_factory=dict)
    rationale: List[str] = field(default_factory=list)
    threshold: float = 70.0

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)

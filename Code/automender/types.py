from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


class Serializable:
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Finding(Serializable):
    tool: str
    bug_type: str
    path: str
    line_start: int = 0
    line_end: int = 0
    code: str = ""
    function: str = ""
    confidence: float = 1.0
    evidence: str = ""

    @property
    def segment_key(self) -> str:
        scope = self.function or f"{self.line_start}:{self.line_end}"
        return f"{self.bug_type}:{scope}"


@dataclass
class DetectionRun(Serializable):
    tool: str
    status: str
    findings: List[Finding] = field(default_factory=list)
    runtime_seconds: float = 0.0
    raw_artifact: str = ""
    error: str = ""
    paper_eligible: bool = True

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        value["findings"] = [finding.to_dict() for finding in self.findings]
        return value


@dataclass
class ContractSemantics(Serializable):
    path: str
    contracts: List[str] = field(default_factory=list)
    inheritance: Dict[str, List[str]] = field(default_factory=dict)
    state_variables: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    modifiers: List[str] = field(default_factory=list)
    calls: List[str] = field(default_factory=list)
    dangerous_operations: List[str] = field(default_factory=list)


@dataclass
class RepairSample(Serializable):
    sample_id: str
    vulnerable: str
    fixed: str
    bug_types: List[str] = field(default_factory=list)
    expert_labels: List[str] = field(default_factory=list)
    label_source: str = "weak"
    label_confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)
    split: str = "train"


@dataclass
class RepairCandidate(Serializable):
    contract: str
    rationale: str = ""
    raw_output: str = ""
    iteration: int = 0
    parse_ok: bool = True


@dataclass
class QualityBreakdown(Serializable):
    residual_bugs: int
    new_bugs: int
    vulnerability_cost: float
    compile_ok: bool
    behavior_ok: bool
    runtime_valid: bool
    gas_before: Optional[int]
    gas_after: Optional[int]
    gas_increase: float
    token_change: float
    change_cost: float
    valid: bool
    total_cost: float


@dataclass
class RepairResult(Serializable):
    original_path: str
    final_contract: str
    rationale: str
    success: bool
    stop_reason: str
    iterations: int
    best_quality: Optional[QualityBreakdown]
    remaining_findings: List[Finding] = field(default_factory=list)
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    paper_eligible: bool = True

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        if self.best_quality:
            value["best_quality"] = self.best_quality.to_dict()
        value["remaining_findings"] = [f.to_dict() for f in self.remaining_findings]
        return value

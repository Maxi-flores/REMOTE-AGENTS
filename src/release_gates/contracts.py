from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal


GateDecisionType = Literal["pass", "pass_with_warnings", "blocked", "unknown"]
GATE_DECISIONS = {"pass", "pass_with_warnings", "blocked", "unknown"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class GatePolicy:
    policy_id: str
    display_name: str
    minimum_readiness_score: float
    block_on_critical_findings: bool
    block_on_malformed_artifacts: bool
    block_on_missing_artifacts: bool
    block_on_unsupported_versions: bool
    max_warning_count: int
    max_error_count: int
    required_artifacts: List[str]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "display_name": self.display_name,
            "minimum_readiness_score": float(self.minimum_readiness_score),
            "block_on_critical_findings": bool(self.block_on_critical_findings),
            "block_on_malformed_artifacts": bool(self.block_on_malformed_artifacts),
            "block_on_missing_artifacts": bool(self.block_on_missing_artifacts),
            "block_on_unsupported_versions": bool(self.block_on_unsupported_versions),
            "max_warning_count": int(self.max_warning_count),
            "max_error_count": int(self.max_error_count),
            "required_artifacts": list(self.required_artifacts),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class GateDecision:
    decision_id: str
    policy_id: str
    decision: GateDecisionType
    readiness_score: float
    blockers: List[str]
    warnings: List[str]
    evaluated_artifacts: List[Dict[str, Any]]
    advisory_only: bool
    report_id: str | None = None
    created_utc: str = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "policy_id": self.policy_id,
            "report_id": self.report_id,
            "decision": self.decision,
            "readiness_score": float(self.readiness_score),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "evaluated_artifacts": list(self.evaluated_artifacts),
            "created_utc": self.created_utc,
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


def validate_gate_policy_dict(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("GatePolicy must be an object")
    _require_str(payload, "policy_id")
    _require_str(payload, "display_name")
    score = payload.get("minimum_readiness_score")
    if isinstance(score, bool) or not isinstance(score, (int, float)) or score < 0 or score > 100:
        raise ValueError("minimum_readiness_score must be number 0-100")
    for key in (
        "block_on_critical_findings",
        "block_on_malformed_artifacts",
        "block_on_missing_artifacts",
        "block_on_unsupported_versions",
        "advisory_only",
    ):
        if not isinstance(payload.get(key), bool):
            raise ValueError(f"{key} must be bool")
    for key in ("max_warning_count", "max_error_count"):
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{key} must be integer")
    if not isinstance(payload.get("required_artifacts", []), list):
        raise ValueError("required_artifacts must be list")
    if not isinstance(payload.get("metadata", {}), dict):
        raise ValueError("metadata must be dict")


def validate_gate_decision_dict(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("GateDecision must be an object")
    _require_str(payload, "decision_id")
    _require_str(payload, "policy_id")
    decision = _require_str(payload, "decision")
    if decision not in GATE_DECISIONS:
        raise ValueError(f"invalid gate decision: {decision}")
    for key in ("blockers", "warnings", "evaluated_artifacts"):
        if not isinstance(payload.get(key, []), list):
            raise ValueError(f"{key} must be list")
    if not isinstance(payload.get("advisory_only"), bool):
        raise ValueError("advisory_only must be bool")


def _require_str(payload: Dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} required")
    return value


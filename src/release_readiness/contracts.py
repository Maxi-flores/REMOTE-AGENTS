from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal


DriftType = Literal[
    "missing_required_field",
    "unexpected_field",
    "type_mismatch",
    "unsupported_version",
    "deprecated_version",
    "malformed_artifact",
    "missing_artifact",
    "schema_manifest_missing",
    "jsonl_line_invalid",
    "compatibility_warning",
]
Severity = Literal["info", "warning", "error", "critical"]
ReadinessStatus = Literal["ready", "ready_with_warnings", "blocked", "unknown"]

DRIFT_TYPES = {
    "missing_required_field",
    "unexpected_field",
    "type_mismatch",
    "unsupported_version",
    "deprecated_version",
    "malformed_artifact",
    "missing_artifact",
    "schema_manifest_missing",
    "jsonl_line_invalid",
    "compatibility_warning",
}
SEVERITIES = {"info", "warning", "error", "critical"}
READINESS_STATUSES = {"ready", "ready_with_warnings", "blocked", "unknown"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class ContractDriftFinding:
    finding_id: str
    artifact_type: str
    artifact_path: str
    drift_type: DriftType
    severity: Severity
    field_path: str
    expected: Any
    actual: Any
    message: str
    created_utc: str = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "artifact_type": self.artifact_type,
            "artifact_path": self.artifact_path,
            "drift_type": self.drift_type,
            "severity": self.severity,
            "field_path": self.field_path,
            "expected": self.expected,
            "actual": self.actual,
            "message": self.message,
            "created_utc": self.created_utc,
            "metadata": dict(self.metadata),
        }


@dataclass
class ReleaseReadinessReport:
    report_id: str
    generated_utc: str
    scope: str
    readiness_score: float
    readiness_status: ReadinessStatus
    blockers: List[str]
    warnings: List[str]
    findings: List[Dict[str, Any]]
    checked_artifacts: List[Dict[str, Any]]
    summary: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_utc": self.generated_utc,
            "scope": self.scope,
            "readiness_score": float(self.readiness_score),
            "readiness_status": self.readiness_status,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "findings": list(self.findings),
            "checked_artifacts": list(self.checked_artifacts),
            "summary": dict(self.summary),
            "metadata": dict(self.metadata),
        }


def validate_contract_drift_finding_dict(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("ContractDriftFinding must be an object")
    _require_str(payload, "finding_id")
    _require_str(payload, "artifact_type")
    drift_type = _require_str(payload, "drift_type")
    if drift_type not in DRIFT_TYPES:
        raise ValueError(f"invalid drift_type: {drift_type}")
    severity = _require_str(payload, "severity")
    if severity not in SEVERITIES:
        raise ValueError(f"invalid severity: {severity}")
    _require_str(payload, "message")
    if not isinstance(payload.get("metadata", {}), dict):
        raise ValueError("metadata must be an object")


def validate_release_readiness_report_dict(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("ReleaseReadinessReport must be an object")
    _require_str(payload, "report_id")
    _require_str(payload, "generated_utc")
    score = payload.get("readiness_score")
    if isinstance(score, bool) or not isinstance(score, (int, float)) or score < 0 or score > 100:
        raise ValueError("readiness_score must be number 0-100")
    status = _require_str(payload, "readiness_status")
    if status not in READINESS_STATUSES:
        raise ValueError(f"invalid readiness_status: {status}")
    for key in ("blockers", "warnings", "findings", "checked_artifacts"):
        if not isinstance(payload.get(key, []), list):
            raise ValueError(f"{key} must be a list")
    if not isinstance(payload.get("summary", {}), dict):
        raise ValueError("summary must be an object")
    if not isinstance(payload.get("metadata", {}), dict):
        raise ValueError("metadata must be an object")


def _require_str(payload: Dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required")
    return value


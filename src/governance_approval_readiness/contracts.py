from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


APPROVAL_STATUSES = {"ready_for_review", "needs_review", "blocked", "rejected_advisory", "unknown"}
RISK_LEVELS = {"low", "medium", "high", "critical", "unknown"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class GovernanceApprovalReadinessRecord:
    record_id: str
    dossier_id: str
    title: str
    approval_status: str
    readiness_score: int
    risk_level: str
    missing_requirements: List[str]
    approval_recommendation: str
    required_human_review: bool
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "dossier_id": self.dossier_id,
            "title": self.title,
            "approval_status": self.approval_status,
            "readiness_score": int(self.readiness_score),
            "risk_level": self.risk_level,
            "missing_requirements": list(self.missing_requirements),
            "approval_recommendation": self.approval_recommendation,
            "required_human_review": bool(self.required_human_review),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class GovernanceApprovalReadinessReport:
    report_id: str
    generated_utc: str
    source_dossier_report_id: str
    records: List[Dict[str, Any]]
    summary: Dict[str, Any]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_utc": self.generated_utc,
            "source_dossier_report_id": self.source_dossier_report_id,
            "records": list(self.records),
            "summary": dict(self.summary),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


def validate_governance_approval_readiness_record_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "record_id")
    _require_str(payload, "dossier_id")
    _require_str(payload, "title")
    status = _require_str(payload, "approval_status")
    if status not in APPROVAL_STATUSES:
        raise ValueError(f"invalid approval_status: {status}")
    score = payload.get("readiness_score")
    if isinstance(score, bool) or not isinstance(score, int):
        raise ValueError("readiness_score must be integer")
    risk_level = _require_str(payload, "risk_level")
    if risk_level not in RISK_LEVELS:
        raise ValueError(f"invalid risk_level: {risk_level}")
    _require_list(payload, "missing_requirements")
    _require_str(payload, "approval_recommendation")
    _require_bool(payload, "required_human_review")
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def validate_governance_approval_readiness_report_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "report_id")
    _require_str(payload, "generated_utc")
    _require_str(payload, "source_dossier_report_id")
    _require_list(payload, "records")
    for record in payload["records"]:
        if isinstance(record, dict):
            validate_governance_approval_readiness_record_dict(record)
    _require_dict(payload, "summary")
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def _require_str(payload: Dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} required")
    return value


def _require_list(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), list):
        raise ValueError(f"{key} must be list")


def _require_bool(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), bool):
        raise ValueError(f"{key} must be bool")


def _require_dict(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), dict):
        raise ValueError(f"{key} must be dict")


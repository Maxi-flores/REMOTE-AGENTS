from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


CATEGORIES = {"lifecycle", "governance", "release", "memory", "scheduler", "tooling", "repository", "system"}
PRIORITIES = {"P0", "P1", "P2", "P3", "P4"}
REPORT_STATUSES = {"healthy", "warning", "degraded", "blocked", "unknown"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class StrategicMissionCandidate:
    candidate_id: str
    title: str
    description: str
    source_finding_ids: List[str]
    category: str
    priority: str
    risk_reduction_score: int
    effort_score: int
    confidence_score: int
    recommended_repository: str | None
    suggested_instruction: str
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "title": self.title,
            "description": self.description,
            "source_finding_ids": list(self.source_finding_ids),
            "category": self.category,
            "priority": self.priority,
            "risk_reduction_score": int(self.risk_reduction_score),
            "effort_score": int(self.effort_score),
            "confidence_score": int(self.confidence_score),
            "recommended_repository": self.recommended_repository,
            "suggested_instruction": self.suggested_instruction,
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class StrategicMissionReport:
    report_id: str
    generated_utc: str
    overall_status: str
    candidates: List[Dict[str, Any]]
    recommended_sequence: List[str]
    summary: Dict[str, Any]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_utc": self.generated_utc,
            "overall_status": self.overall_status,
            "candidates": list(self.candidates),
            "recommended_sequence": list(self.recommended_sequence),
            "summary": dict(self.summary),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


def validate_strategic_mission_candidate_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "candidate_id")
    _require_str(payload, "title")
    _require_str(payload, "description")
    _require_str(payload, "suggested_instruction")
    category = _require_str(payload, "category")
    if category not in CATEGORIES:
        raise ValueError(f"invalid category: {category}")
    priority = _require_str(payload, "priority")
    if priority not in PRIORITIES:
        raise ValueError(f"invalid priority: {priority}")
    _require_list(payload, "source_finding_ids")
    for key in ("risk_reduction_score", "effort_score", "confidence_score"):
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{key} must be integer")
    if not isinstance(payload.get("advisory_only"), bool):
        raise ValueError("advisory_only must be bool")
    if not isinstance(payload.get("metadata", {}), dict):
        raise ValueError("metadata must be dict")


def validate_strategic_mission_report_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "report_id")
    _require_str(payload, "generated_utc")
    status = _require_str(payload, "overall_status")
    if status not in REPORT_STATUSES:
        raise ValueError(f"invalid overall_status: {status}")
    _require_list(payload, "candidates")
    for candidate in payload.get("candidates", []):
        if isinstance(candidate, dict):
            validate_strategic_mission_candidate_dict(candidate)
    _require_list(payload, "recommended_sequence")
    if not isinstance(payload.get("summary", {}), dict):
        raise ValueError("summary must be dict")
    if not isinstance(payload.get("advisory_only"), bool):
        raise ValueError("advisory_only must be bool")
    if not isinstance(payload.get("metadata", {}), dict):
        raise ValueError("metadata must be dict")


def _require_str(payload: Dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} required")
    return value


def _require_list(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), list):
        raise ValueError(f"{key} must be list")


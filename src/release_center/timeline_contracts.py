from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal


EventType = Literal[
    "readiness_report",
    "gate_decision",
    "scenario_comparison",
    "promotion_recommendation",
    "rollback_precheck",
    "ci_handoff",
    "escalation",
    "milestone",
    "advisory_note",
    "unknown",
]
Severity = Literal["info", "warning", "error", "critical"]
EventStatus = Literal["observed", "ready", "review_required", "blocked", "completed", "unknown"]
MilestoneType = Literal[
    "readiness",
    "gate",
    "scenario",
    "promotion",
    "rollback",
    "ci_handoff",
    "approval",
    "release",
    "incident",
    "governance",
]
MilestoneStatus = Literal["not_started", "in_progress", "ready", "review_required", "blocked", "completed", "unknown"]

EVENT_TYPES = {
    "readiness_report",
    "gate_decision",
    "scenario_comparison",
    "promotion_recommendation",
    "rollback_precheck",
    "ci_handoff",
    "escalation",
    "milestone",
    "advisory_note",
    "unknown",
}
SEVERITIES = {"info", "warning", "error", "critical"}
EVENT_STATUSES = {"observed", "ready", "review_required", "blocked", "completed", "unknown"}
MILESTONE_TYPES = {"readiness", "gate", "scenario", "promotion", "rollback", "ci_handoff", "approval", "release", "incident", "governance"}
MILESTONE_STATUSES = {"not_started", "in_progress", "ready", "review_required", "blocked", "completed", "unknown"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class ReleaseTimelineEvent:
    event_id: str
    event_type: EventType
    title: str
    description: str
    occurred_utc: str
    source_artifact: str
    severity: Severity
    status: EventStatus
    source_id: str | None = None
    related_environment: str | None = None
    related_policy: str | None = None
    related_scenario_pack: str | None = None
    related_profile: str | None = None
    blockers: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "title": self.title,
            "description": self.description,
            "occurred_utc": self.occurred_utc,
            "source_artifact": self.source_artifact,
            "source_id": self.source_id,
            "severity": self.severity,
            "status": self.status,
            "related_environment": self.related_environment,
            "related_policy": self.related_policy,
            "related_scenario_pack": self.related_scenario_pack,
            "related_profile": self.related_profile,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "metadata": dict(self.metadata),
        }


@dataclass
class ReleaseMilestone:
    milestone_id: str
    title: str
    description: str
    milestone_type: MilestoneType
    status: MilestoneStatus
    owner_placeholder: str
    related_event_ids: List[str]
    blockers: List[str]
    warnings: List[str]
    escalation_hints: List[str]
    target_environment: str | None = None
    due_utc: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "milestone_id": self.milestone_id,
            "title": self.title,
            "description": self.description,
            "milestone_type": self.milestone_type,
            "status": self.status,
            "target_environment": self.target_environment,
            "owner_placeholder": self.owner_placeholder,
            "due_utc": self.due_utc,
            "related_event_ids": list(self.related_event_ids),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "escalation_hints": list(self.escalation_hints),
            "metadata": dict(self.metadata),
        }


@dataclass
class ReleaseTimelineReport:
    report_id: str
    generated_utc: str
    release_label: str
    timeline_events: List[Dict[str, Any]]
    milestones: List[Dict[str, Any]]
    summary: Dict[str, Any]
    escalation_hints: List[str]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_utc": self.generated_utc,
            "release_label": self.release_label,
            "timeline_events": list(self.timeline_events),
            "milestones": list(self.milestones),
            "summary": dict(self.summary),
            "escalation_hints": list(self.escalation_hints),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


def validate_release_timeline_event_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "event_id")
    event_type = _require_str(payload, "event_type")
    if event_type not in EVENT_TYPES:
        raise ValueError(f"invalid event_type: {event_type}")
    severity = _require_str(payload, "severity")
    if severity not in SEVERITIES:
        raise ValueError(f"invalid severity: {severity}")
    status = _require_str(payload, "status")
    if status not in EVENT_STATUSES:
        raise ValueError(f"invalid status: {status}")
    for key in ("blockers", "warnings"):
        if not isinstance(payload.get(key, []), list):
            raise ValueError(f"{key} must be list")
    if not isinstance(payload.get("metadata", {}), dict):
        raise ValueError("metadata must be dict")


def validate_release_milestone_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "milestone_id")
    milestone_type = _require_str(payload, "milestone_type")
    if milestone_type not in MILESTONE_TYPES:
        raise ValueError(f"invalid milestone_type: {milestone_type}")
    status = _require_str(payload, "status")
    if status not in MILESTONE_STATUSES:
        raise ValueError(f"invalid milestone status: {status}")
    for key in ("related_event_ids", "blockers", "warnings", "escalation_hints"):
        if not isinstance(payload.get(key, []), list):
            raise ValueError(f"{key} must be list")
    if not isinstance(payload.get("metadata", {}), dict):
        raise ValueError("metadata must be dict")


def validate_release_timeline_report_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "report_id")
    _require_str(payload, "generated_utc")
    _require_str(payload, "release_label")
    for key in ("timeline_events", "milestones", "escalation_hints"):
        if not isinstance(payload.get(key, []), list):
            raise ValueError(f"{key} must be list")
    if not isinstance(payload.get("summary", {}), dict):
        raise ValueError("summary must be dict")
    if not isinstance(payload.get("metadata", {}), dict):
        raise ValueError("metadata must be dict")
    if not isinstance(payload.get("advisory_only"), bool):
        raise ValueError("advisory_only must be bool")


def _require_str(payload: Dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} required")
    return value


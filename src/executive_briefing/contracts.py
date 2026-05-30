from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


SEVERITIES = {"info", "low", "medium", "high", "critical"}
CATEGORIES = {"mission", "scheduler", "tooling", "governance", "memory", "release", "lifecycle", "repository", "system"}
OVERALL_STATUSES = {"healthy", "warning", "degraded", "blocked", "unknown"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class ExecutiveFinding:
    finding_id: str
    severity: str
    category: str
    title: str
    description: str
    recommended_action: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "severity": self.severity,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "recommended_action": self.recommended_action,
        }


@dataclass
class ExecutiveBriefing:
    briefing_id: str
    generated_utc: str
    overall_status: str
    executive_summary: str
    top_risks: List[Dict[str, Any]]
    blocked_items: List[Dict[str, Any]]
    recommended_actions: List[str]
    release_summary: Dict[str, Any]
    lifecycle_summary: Dict[str, Any]
    governance_summary: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "briefing_id": self.briefing_id,
            "generated_utc": self.generated_utc,
            "overall_status": self.overall_status,
            "executive_summary": self.executive_summary,
            "top_risks": list(self.top_risks),
            "blocked_items": list(self.blocked_items),
            "recommended_actions": list(self.recommended_actions),
            "release_summary": dict(self.release_summary),
            "lifecycle_summary": dict(self.lifecycle_summary),
            "governance_summary": dict(self.governance_summary),
            "metadata": dict(self.metadata),
        }


def validate_executive_finding_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "finding_id")
    sev = _require_str(payload, "severity")
    if sev not in SEVERITIES:
        raise ValueError(f"invalid severity: {sev}")
    cat = _require_str(payload, "category")
    if cat not in CATEGORIES:
        raise ValueError(f"invalid category: {cat}")
    _require_str(payload, "title")
    _require_str(payload, "description")
    _require_str(payload, "recommended_action")


def validate_executive_briefing_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "briefing_id")
    _require_str(payload, "generated_utc")
    status = _require_str(payload, "overall_status")
    if status not in OVERALL_STATUSES:
        raise ValueError(f"invalid overall_status: {status}")
    _require_str(payload, "executive_summary")
    for key in ("top_risks", "blocked_items", "recommended_actions"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"{key} must be list")
    for item in payload.get("top_risks", []):
        if isinstance(item, dict):
            validate_executive_finding_dict(item)
    for item in payload.get("blocked_items", []):
        if isinstance(item, dict):
            validate_executive_finding_dict(item)
    for key in ("release_summary", "lifecycle_summary", "governance_summary", "metadata"):
        if not isinstance(payload.get(key, {}), dict):
            raise ValueError(f"{key} must be dict")


def _require_str(payload: Dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} required")
    return value


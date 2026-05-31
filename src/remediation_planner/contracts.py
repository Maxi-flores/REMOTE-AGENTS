from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


CATEGORIES = {"config", "docs", "tests", "runtime", "contracts", "governance", "lifecycle", "release", "observability"}
PRIORITIES = {"P0", "P1", "P2", "P3", "P4"}
STATUSES = {"open", "planned", "deferred", "blocked", "done"}
BATCH_STATUSES = {"planned", "ready", "blocked", "deferred"}
REPORT_STATUSES = {"healthy", "warning", "degraded", "blocked", "unknown"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class RemediationItem:
    item_id: str
    title: str
    description: str
    category: str
    priority: str
    status: str
    repository: str
    source_finding_ids: List[str]
    suggested_action: str
    risk_score: int
    effort_score: int
    confidence_score: int
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "priority": self.priority,
            "status": self.status,
            "repository": self.repository,
            "source_finding_ids": list(self.source_finding_ids),
            "suggested_action": self.suggested_action,
            "risk_score": int(self.risk_score),
            "effort_score": int(self.effort_score),
            "confidence_score": int(self.confidence_score),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class RemediationBatch:
    batch_id: str
    name: str
    priority: str
    status: str
    repository: str
    item_ids: List[str]
    estimated_total_effort: int
    expected_risk_reduction: int
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "name": self.name,
            "priority": self.priority,
            "status": self.status,
            "repository": self.repository,
            "item_ids": list(self.item_ids),
            "estimated_total_effort": int(self.estimated_total_effort),
            "expected_risk_reduction": int(self.expected_risk_reduction),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class RemediationPlanReport:
    report_id: str
    generated_utc: str
    source_report_id: str
    overall_status: str
    items: List[Dict[str, Any]]
    batches: List[Dict[str, Any]]
    recommended_sequence: List[str]
    summary: Dict[str, Any]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_utc": self.generated_utc,
            "source_report_id": self.source_report_id,
            "overall_status": self.overall_status,
            "items": list(self.items),
            "batches": list(self.batches),
            "recommended_sequence": list(self.recommended_sequence),
            "summary": dict(self.summary),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


def validate_remediation_item_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "item_id")
    _require_str(payload, "title")
    _require_str(payload, "description")
    category = _require_str(payload, "category")
    if category not in CATEGORIES:
        raise ValueError(f"invalid category: {category}")
    priority = _require_str(payload, "priority")
    if priority not in PRIORITIES:
        raise ValueError(f"invalid priority: {priority}")
    status = _require_str(payload, "status")
    if status not in STATUSES:
        raise ValueError(f"invalid status: {status}")
    _require_str(payload, "repository")
    _require_list(payload, "source_finding_ids")
    _require_str(payload, "suggested_action")
    for key in ("risk_score", "effort_score", "confidence_score"):
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{key} must be integer")
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def validate_remediation_batch_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "batch_id")
    _require_str(payload, "name")
    priority = _require_str(payload, "priority")
    if priority not in PRIORITIES:
        raise ValueError(f"invalid priority: {priority}")
    status = _require_str(payload, "status")
    if status not in BATCH_STATUSES:
        raise ValueError(f"invalid status: {status}")
    _require_str(payload, "repository")
    _require_list(payload, "item_ids")
    for key in ("estimated_total_effort", "expected_risk_reduction"):
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{key} must be integer")
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def validate_remediation_plan_report_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "report_id")
    _require_str(payload, "generated_utc")
    _require_str(payload, "source_report_id")
    status = _require_str(payload, "overall_status")
    if status not in REPORT_STATUSES:
        raise ValueError(f"invalid overall_status: {status}")
    _require_list(payload, "items")
    for item in payload["items"]:
        if isinstance(item, dict):
            validate_remediation_item_dict(item)
    _require_list(payload, "batches")
    for batch in payload["batches"]:
        if isinstance(batch, dict):
            validate_remediation_batch_dict(batch)
    _require_list(payload, "recommended_sequence")
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


def _require_dict(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), dict):
        raise ValueError(f"{key} must be dict")


def _require_bool(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), bool):
        raise ValueError(f"{key} must be bool")

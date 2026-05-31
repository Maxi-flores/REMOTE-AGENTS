from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


EXECUTION_READINESS = {"ready", "waiting", "blocked", "deferred"}
PRIORITIES = {"P0", "P1", "P2", "P3", "P4"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class WorkQueueItem:
    queue_item_id: str
    source_refined_package_id: str
    title: str
    subsystem: str
    priority: str
    readiness_score: int
    effort_score: int
    risk_score: int
    blocker_count: int
    dependency_refs: List[str]
    recommended_position: int
    execution_readiness: str
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "queue_item_id": self.queue_item_id,
            "source_refined_package_id": self.source_refined_package_id,
            "title": self.title,
            "subsystem": self.subsystem,
            "priority": self.priority,
            "readiness_score": int(self.readiness_score),
            "effort_score": int(self.effort_score),
            "risk_score": int(self.risk_score),
            "blocker_count": int(self.blocker_count),
            "dependency_refs": list(self.dependency_refs),
            "recommended_position": int(self.recommended_position),
            "execution_readiness": self.execution_readiness,
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class WorkQueueReport:
    report_id: str
    generated_utc: str
    queue_items: List[Dict[str, Any]]
    dependency_graph: Dict[str, Any]
    blockers: List[Dict[str, Any]]
    recommended_execution_order: List[str]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_utc": self.generated_utc,
            "queue_items": list(self.queue_items),
            "dependency_graph": dict(self.dependency_graph),
            "blockers": list(self.blockers),
            "recommended_execution_order": list(self.recommended_execution_order),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


def validate_work_queue_item_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "queue_item_id")
    _require_str(payload, "source_refined_package_id")
    _require_str(payload, "title")
    _require_str(payload, "subsystem")
    p = _require_str(payload, "priority")
    if p not in PRIORITIES:
        raise ValueError(f"invalid priority: {p}")
    for key in ("readiness_score", "effort_score", "risk_score", "blocker_count", "recommended_position"):
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{key} must be integer")
    _require_list(payload, "dependency_refs")
    r = _require_str(payload, "execution_readiness")
    if r not in EXECUTION_READINESS:
        raise ValueError(f"invalid execution_readiness: {r}")
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def validate_work_queue_report_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "report_id")
    _require_str(payload, "generated_utc")
    _require_list(payload, "queue_items")
    for item in payload["queue_items"]:
        if isinstance(item, dict):
            validate_work_queue_item_dict(item)
    _require_dict(payload, "dependency_graph")
    _require_list(payload, "blockers")
    _require_list(payload, "recommended_execution_order")
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

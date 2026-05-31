from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


QUEUE_STATUSES = {"approved_manual", "deferred", "needs_changes", "pending_review", "rejected", "unknown"}
PRIORITIES = {"P0", "P1", "P2", "P3", "P4"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class ManualExecutionQueueItem:
    queue_item_id: str
    packet_id: str
    source_dossier_id: str
    decision: str
    queue_status: str
    title: str
    priority: str
    operator_next_step: str
    validation_commands: List[str]
    safety_notes: List[str]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "queue_item_id": self.queue_item_id,
            "packet_id": self.packet_id,
            "source_dossier_id": self.source_dossier_id,
            "decision": self.decision,
            "queue_status": self.queue_status,
            "title": self.title,
            "priority": self.priority,
            "operator_next_step": self.operator_next_step,
            "validation_commands": list(self.validation_commands),
            "safety_notes": list(self.safety_notes),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class ManualExecutionQueueReport:
    report_id: str
    generated_utc: str
    source_decision_report_id: str
    queue_items: List[Dict[str, Any]]
    summary: Dict[str, Any]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_utc": self.generated_utc,
            "source_decision_report_id": self.source_decision_report_id,
            "queue_items": list(self.queue_items),
            "summary": dict(self.summary),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


def validate_manual_execution_queue_item_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "queue_item_id")
    _require_str(payload, "packet_id")
    _require_str(payload, "source_dossier_id")
    _require_str(payload, "decision")
    status = _require_str(payload, "queue_status")
    if status not in QUEUE_STATUSES:
        raise ValueError(f"invalid queue_status: {status}")
    _require_str(payload, "title")
    priority = _require_str(payload, "priority")
    if priority not in PRIORITIES:
        raise ValueError(f"invalid priority: {priority}")
    _require_str(payload, "operator_next_step")
    _require_list(payload, "validation_commands")
    _require_list(payload, "safety_notes")
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def validate_manual_execution_queue_report_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "report_id")
    _require_str(payload, "generated_utc")
    _require_str(payload, "source_decision_report_id")
    _require_list(payload, "queue_items")
    for item in payload["queue_items"]:
        if isinstance(item, dict):
            validate_manual_execution_queue_item_dict(item)
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


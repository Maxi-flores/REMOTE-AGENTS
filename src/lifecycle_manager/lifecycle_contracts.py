from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


LIFECYCLE_STATUSES = {"registered", "validating", "active", "suspended", "retired", "planned", "unknown"}
HEALTH_VALUES = {"healthy", "warning", "degraded", "offline", "unknown"}
AVAILABILITY_VALUES = {"available", "busy", "paused", "disabled", "unknown"}


@dataclass
class AgentLifecycleState:
    agent_id: str
    agent_class: str
    version: str
    status: str
    health: str
    availability: str
    assigned_repositories: List[str]
    current_missions: List[str]
    performance_summary: Dict[str, Any]
    lifecycle_notes: List[str]
    created_utc: str
    updated_utc: str
    last_seen_utc: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_class": self.agent_class,
            "version": self.version,
            "status": self.status,
            "health": self.health,
            "availability": self.availability,
            "last_seen_utc": self.last_seen_utc,
            "assigned_repositories": list(self.assigned_repositories),
            "current_missions": list(self.current_missions),
            "performance_summary": dict(self.performance_summary),
            "lifecycle_notes": list(self.lifecycle_notes),
            "created_utc": self.created_utc,
            "updated_utc": self.updated_utc,
            "metadata": dict(self.metadata),
        }


def validate_lifecycle_state_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "agent_id")
    _require_str(payload, "agent_class")
    _require_str(payload, "version")
    _require_str(payload, "created_utc")
    _require_str(payload, "updated_utc")
    status = _require_str(payload, "status")
    if status not in LIFECYCLE_STATUSES:
        raise ValueError(f"invalid lifecycle status: {status}")
    health = _require_str(payload, "health")
    if health not in HEALTH_VALUES:
        raise ValueError(f"invalid lifecycle health: {health}")
    availability = _require_str(payload, "availability")
    if availability not in AVAILABILITY_VALUES:
        raise ValueError(f"invalid lifecycle availability: {availability}")
    for key in ("assigned_repositories", "current_missions", "lifecycle_notes"):
        if not isinstance(payload.get(key, []), list):
            raise ValueError(f"{key} must be list")
    for key in ("performance_summary", "metadata"):
        if not isinstance(payload.get(key, {}), dict):
            raise ValueError(f"{key} must be dict")


def _require_str(payload: Dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} required")
    return value


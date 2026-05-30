from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


CAPABILITY_STATUSES = {"active", "inactive", "deprecated", "planned", "experimental", "unknown"}
RISK_TIERS = {"low", "medium", "high", "critical"}


@dataclass
class AgentCapabilityProfile:
    capability_profile_id: str
    agent_class: str
    display_name: str
    category: str
    repositories: List[str]
    repository_groups: List[str]
    capabilities: List[str]
    allowed_tools: List[str]
    denied_tools: List[str]
    risk_tier: str
    primary_roles: List[str]
    secondary_roles: List[str]
    health_requirements: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    status: str
    created_utc: str
    updated_utc: str
    crew_family: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capability_profile_id": self.capability_profile_id,
            "agent_class": self.agent_class,
            "display_name": self.display_name,
            "category": self.category,
            "crew_family": self.crew_family,
            "repositories": list(self.repositories),
            "repository_groups": list(self.repository_groups),
            "capabilities": list(self.capabilities),
            "allowed_tools": list(self.allowed_tools),
            "denied_tools": list(self.denied_tools),
            "risk_tier": self.risk_tier,
            "primary_roles": list(self.primary_roles),
            "secondary_roles": list(self.secondary_roles),
            "health_requirements": dict(self.health_requirements),
            "performance_metrics": dict(self.performance_metrics),
            "status": self.status,
            "created_utc": self.created_utc,
            "updated_utc": self.updated_utc,
            "metadata": dict(self.metadata),
        }


def validate_capability_profile_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "capability_profile_id")
    _require_str(payload, "agent_class")
    _require_str(payload, "display_name")
    _require_str(payload, "category")
    _require_str(payload, "created_utc")
    _require_str(payload, "updated_utc")
    status = _require_str(payload, "status")
    if status not in CAPABILITY_STATUSES:
        raise ValueError(f"invalid capability status: {status}")
    risk_tier = _require_str(payload, "risk_tier")
    if risk_tier not in RISK_TIERS:
        raise ValueError(f"invalid risk_tier: {risk_tier}")
    for key in (
        "repositories",
        "repository_groups",
        "capabilities",
        "allowed_tools",
        "denied_tools",
        "primary_roles",
        "secondary_roles",
    ):
        if not isinstance(payload.get(key, []), list):
            raise ValueError(f"{key} must be list")
    for key in ("health_requirements", "performance_metrics", "metadata"):
        if not isinstance(payload.get(key, {}), dict):
            raise ValueError(f"{key} must be dict")


def _require_str(payload: Dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} required")
    return value


from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


STATUSES = {"healthy", "warning", "degraded", "critical", "unknown"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class GovernanceIndexComponent:
    component_id: str
    name: str
    score: int
    weight: int
    status: str
    reasons: List[str]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_id": self.component_id,
            "name": self.name,
            "score": int(self.score),
            "weight": int(self.weight),
            "status": self.status,
            "reasons": list(self.reasons),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class PortfolioGovernanceHealthReport:
    report_id: str
    generated_utc: str
    governance_score: int
    governance_status: str
    components: List[Dict[str, Any]]
    top_reasons: List[str]
    top_recommendations: List[str]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_utc": self.generated_utc,
            "governance_score": int(self.governance_score),
            "governance_status": self.governance_status,
            "components": list(self.components),
            "top_reasons": list(self.top_reasons),
            "top_recommendations": list(self.top_recommendations),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


def validate_governance_index_component_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "component_id")
    _require_str(payload, "name")
    _require_int(payload, "score")
    _require_int(payload, "weight")
    status = _require_str(payload, "status")
    if status not in STATUSES:
        raise ValueError(f"invalid status: {status}")
    _require_list(payload, "reasons")
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def validate_portfolio_governance_health_report_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "report_id")
    _require_str(payload, "generated_utc")
    _require_int(payload, "governance_score")
    status = _require_str(payload, "governance_status")
    if status not in STATUSES:
        raise ValueError(f"invalid governance_status: {status}")
    _require_list(payload, "components")
    for component in payload["components"]:
        if isinstance(component, dict):
            validate_governance_index_component_dict(component)
    _require_list(payload, "top_reasons")
    _require_list(payload, "top_recommendations")
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def _require_str(payload: Dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} required")
    return value


def _require_int(payload: Dict[str, Any], key: str) -> None:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be integer")


def _require_list(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), list):
        raise ValueError(f"{key} must be list")


def _require_dict(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), dict):
        raise ValueError(f"{key} must be dict")


def _require_bool(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), bool):
        raise ValueError(f"{key} must be bool")


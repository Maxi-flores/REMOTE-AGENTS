from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


PRIORITIES = {"P0", "P1", "P2", "P3", "P4"}
HORIZONS = {"near_term", "mid_term", "long_term"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class PortfolioRoadmapItem:
    item_id: str
    source_recommendation_id: str
    repository_id: str
    title: str
    objective: str
    priority: str
    horizon: str
    wave: str
    dependencies: List[str]
    expected_impact: str
    validation_focus: List[str]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "source_recommendation_id": self.source_recommendation_id,
            "repository_id": self.repository_id,
            "title": self.title,
            "objective": self.objective,
            "priority": self.priority,
            "horizon": self.horizon,
            "wave": self.wave,
            "dependencies": list(self.dependencies),
            "expected_impact": self.expected_impact,
            "validation_focus": list(self.validation_focus),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class PortfolioRoadmapWave:
    wave_id: str
    title: str
    horizon: str
    objective: str
    items: List[str]
    readiness_focus: str
    risk_focus: str
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wave_id": self.wave_id,
            "title": self.title,
            "horizon": self.horizon,
            "objective": self.objective,
            "items": list(self.items),
            "readiness_focus": self.readiness_focus,
            "risk_focus": self.risk_focus,
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class PortfolioRoadmapReport:
    report_id: str
    generated_utc: str
    source_critical_path_report_id: str
    roadmap_items: List[Dict[str, Any]]
    waves: List[Dict[str, Any]]
    milestones: List[Dict[str, Any]]
    recommended_sequence: List[str]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_utc": self.generated_utc,
            "source_critical_path_report_id": self.source_critical_path_report_id,
            "roadmap_items": list(self.roadmap_items),
            "waves": list(self.waves),
            "milestones": list(self.milestones),
            "recommended_sequence": list(self.recommended_sequence),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


def validate_portfolio_roadmap_item_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "item_id")
    _require_str(payload, "source_recommendation_id")
    _require_str(payload, "repository_id")
    _require_str(payload, "title")
    _require_str(payload, "objective")
    priority = _require_str(payload, "priority")
    if priority not in PRIORITIES:
        raise ValueError(f"invalid priority: {priority}")
    horizon = _require_str(payload, "horizon")
    if horizon not in HORIZONS:
        raise ValueError(f"invalid horizon: {horizon}")
    _require_str(payload, "wave")
    _require_list(payload, "dependencies")
    _require_str(payload, "expected_impact")
    _require_list(payload, "validation_focus")
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def validate_portfolio_roadmap_wave_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "wave_id")
    _require_str(payload, "title")
    horizon = _require_str(payload, "horizon")
    if horizon not in HORIZONS:
        raise ValueError(f"invalid horizon: {horizon}")
    _require_str(payload, "objective")
    _require_list(payload, "items")
    _require_str(payload, "readiness_focus")
    _require_str(payload, "risk_focus")
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def validate_portfolio_roadmap_report_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "report_id")
    _require_str(payload, "generated_utc")
    _require_str(payload, "source_critical_path_report_id")
    _require_list(payload, "roadmap_items")
    for item in payload["roadmap_items"]:
        if isinstance(item, dict):
            validate_portfolio_roadmap_item_dict(item)
    _require_list(payload, "waves")
    for wave in payload["waves"]:
        if isinstance(wave, dict):
            validate_portfolio_roadmap_wave_dict(wave)
    _require_list(payload, "milestones")
    _require_list(payload, "recommended_sequence")
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


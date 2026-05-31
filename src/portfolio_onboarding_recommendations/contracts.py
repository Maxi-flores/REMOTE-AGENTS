from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


PRIORITIES = {"P0", "P1", "P2", "P3", "P4"}
RISK_LEVELS = {"low", "medium", "high", "critical"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class RepositoryOnboardingRecommendation:
    recommendation_id: str
    repository_id: str
    repository_name: str
    repository_path: str
    onboarding_state: str
    artifact_status: str
    priority: str
    title: str
    recommended_actions: List[str]
    validation_commands: List[str]
    risk_level: str
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "repository_id": self.repository_id,
            "repository_name": self.repository_name,
            "repository_path": self.repository_path,
            "onboarding_state": self.onboarding_state,
            "artifact_status": self.artifact_status,
            "priority": self.priority,
            "title": self.title,
            "recommended_actions": list(self.recommended_actions),
            "validation_commands": list(self.validation_commands),
            "risk_level": self.risk_level,
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class PortfolioOnboardingRecommendationReport:
    report_id: str
    generated_utc: str
    source_bootstrap_report_id: str
    recommendations: List[Dict[str, Any]]
    summary: Dict[str, Any]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_utc": self.generated_utc,
            "source_bootstrap_report_id": self.source_bootstrap_report_id,
            "recommendations": list(self.recommendations),
            "summary": dict(self.summary),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


def validate_repository_onboarding_recommendation_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "recommendation_id")
    _require_str(payload, "repository_id")
    _require_str(payload, "repository_name")
    _require_str(payload, "repository_path")
    _require_str(payload, "onboarding_state")
    _require_str(payload, "artifact_status")
    priority = _require_str(payload, "priority")
    if priority not in PRIORITIES:
        raise ValueError(f"invalid priority: {priority}")
    _require_str(payload, "title")
    _require_list(payload, "recommended_actions")
    _require_list(payload, "validation_commands")
    risk = _require_str(payload, "risk_level")
    if risk not in RISK_LEVELS:
        raise ValueError(f"invalid risk_level: {risk}")
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def validate_portfolio_onboarding_recommendation_report_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "report_id")
    _require_str(payload, "generated_utc")
    _require_str(payload, "source_bootstrap_report_id")
    _require_list(payload, "recommendations")
    for recommendation in payload["recommendations"]:
        if isinstance(recommendation, dict):
            validate_repository_onboarding_recommendation_dict(recommendation)
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


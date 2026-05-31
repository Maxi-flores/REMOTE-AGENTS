from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


PRIORITIES = {"P0", "P1", "P2", "P3", "P4"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class CriticalRepositoryScore:
    repository_id: str
    repository_name: str
    consumer_count: int
    provider_count: int
    dependency_chain_count: int
    propagated_risk_count: int
    readiness_score: int
    influence_score: int
    critical_path_score: int
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository_id": self.repository_id,
            "repository_name": self.repository_name,
            "consumer_count": int(self.consumer_count),
            "provider_count": int(self.provider_count),
            "dependency_chain_count": int(self.dependency_chain_count),
            "propagated_risk_count": int(self.propagated_risk_count),
            "readiness_score": int(self.readiness_score),
            "influence_score": int(self.influence_score),
            "critical_path_score": int(self.critical_path_score),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class CriticalPathRecommendation:
    recommendation_id: str
    repository_id: str
    priority: str
    title: str
    rationale: str
    expected_portfolio_impact: str
    recommended_action: str
    dependency_refs: List[str]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "repository_id": self.repository_id,
            "priority": self.priority,
            "title": self.title,
            "rationale": self.rationale,
            "expected_portfolio_impact": self.expected_portfolio_impact,
            "recommended_action": self.recommended_action,
            "dependency_refs": list(self.dependency_refs),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class PortfolioCriticalPathReport:
    report_id: str
    generated_utc: str
    critical_repository_scores: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    top_critical_repositories: List[str]
    top_dependency_chains: List[List[str]]
    portfolio_leverage_summary: Dict[str, Any]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_utc": self.generated_utc,
            "critical_repository_scores": list(self.critical_repository_scores),
            "recommendations": list(self.recommendations),
            "top_critical_repositories": list(self.top_critical_repositories),
            "top_dependency_chains": list(self.top_dependency_chains),
            "portfolio_leverage_summary": dict(self.portfolio_leverage_summary),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


def validate_critical_repository_score_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "repository_id")
    _require_str(payload, "repository_name")
    for key in (
        "consumer_count",
        "provider_count",
        "dependency_chain_count",
        "propagated_risk_count",
        "readiness_score",
        "influence_score",
        "critical_path_score",
    ):
        _require_int(payload, key)
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def validate_critical_path_recommendation_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "recommendation_id")
    _require_str(payload, "repository_id")
    p = _require_str(payload, "priority")
    if p not in PRIORITIES:
        raise ValueError(f"invalid priority: {p}")
    _require_str(payload, "title")
    _require_str(payload, "rationale")
    _require_str(payload, "expected_portfolio_impact")
    _require_str(payload, "recommended_action")
    _require_list(payload, "dependency_refs")
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def validate_portfolio_critical_path_report_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "report_id")
    _require_str(payload, "generated_utc")
    _require_list(payload, "critical_repository_scores")
    for item in payload["critical_repository_scores"]:
        if isinstance(item, dict):
            validate_critical_repository_score_dict(item)
    _require_list(payload, "recommendations")
    for item in payload["recommendations"]:
        if isinstance(item, dict):
            validate_critical_path_recommendation_dict(item)
    _require_list(payload, "top_critical_repositories")
    _require_list(payload, "top_dependency_chains")
    _require_dict(payload, "portfolio_leverage_summary")
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


from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


REPOSITORY_TYPES = {"agent", "platform", "knowledge", "game", "tooling", "infrastructure", "unknown"}
OVERALL_STATUSES = {"healthy", "warning", "degraded", "critical", "unknown"}
SEVERITIES = {"info", "low", "medium", "high", "critical"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class PortfolioRepository:
    repository_id: str
    repository_name: str
    repository_path: str
    repository_type: str
    enabled: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository_id": self.repository_id,
            "repository_name": self.repository_name,
            "repository_path": self.repository_path,
            "repository_type": self.repository_type,
            "enabled": bool(self.enabled),
            "metadata": dict(self.metadata),
        }


@dataclass
class PortfolioRepositoryStatus:
    repository_id: str
    health_score: int
    remediation_count: int
    queue_count: int
    dossier_count: int
    readiness_score: int
    overall_status: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository_id": self.repository_id,
            "health_score": int(self.health_score),
            "remediation_count": int(self.remediation_count),
            "queue_count": int(self.queue_count),
            "dossier_count": int(self.dossier_count),
            "readiness_score": int(self.readiness_score),
            "overall_status": self.overall_status,
            "metadata": dict(self.metadata),
        }


@dataclass
class PortfolioExecutiveFinding:
    finding_id: str
    severity: str
    category: str
    repository_id: str
    title: str
    description: str
    recommended_action: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "severity": self.severity,
            "category": self.category,
            "repository_id": self.repository_id,
            "title": self.title,
            "description": self.description,
            "recommended_action": self.recommended_action,
            "metadata": dict(self.metadata),
        }


@dataclass
class PortfolioReport:
    report_id: str
    generated_utc: str
    repositories: List[Dict[str, Any]]
    repository_statuses: List[Dict[str, Any]]
    findings: List[Dict[str, Any]]
    portfolio_health_score: int
    portfolio_readiness_score: int
    recommended_execution_order: List[str]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_utc": self.generated_utc,
            "repositories": list(self.repositories),
            "repository_statuses": list(self.repository_statuses),
            "findings": list(self.findings),
            "portfolio_health_score": int(self.portfolio_health_score),
            "portfolio_readiness_score": int(self.portfolio_readiness_score),
            "recommended_execution_order": list(self.recommended_execution_order),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


def validate_portfolio_repository_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "repository_id")
    _require_str(payload, "repository_name")
    _require_str(payload, "repository_path")
    repo_type = _require_str(payload, "repository_type")
    if repo_type not in REPOSITORY_TYPES:
        raise ValueError(f"invalid repository_type: {repo_type}")
    _require_bool(payload, "enabled")
    _require_dict(payload, "metadata")


def validate_portfolio_repository_status_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "repository_id")
    for key in ("health_score", "remediation_count", "queue_count", "dossier_count", "readiness_score"):
        _require_int(payload, key)
    status = _require_str(payload, "overall_status")
    if status not in OVERALL_STATUSES:
        raise ValueError(f"invalid overall_status: {status}")
    _require_dict(payload, "metadata")


def validate_portfolio_executive_finding_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "finding_id")
    sev = _require_str(payload, "severity")
    if sev not in SEVERITIES:
        raise ValueError(f"invalid severity: {sev}")
    _require_str(payload, "category")
    _require_str(payload, "repository_id")
    _require_str(payload, "title")
    _require_str(payload, "description")
    _require_str(payload, "recommended_action")
    _require_dict(payload, "metadata")


def validate_portfolio_report_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "report_id")
    _require_str(payload, "generated_utc")
    _require_list(payload, "repositories")
    for record in payload["repositories"]:
        if isinstance(record, dict):
            validate_portfolio_repository_dict(record)
    _require_list(payload, "repository_statuses")
    for record in payload["repository_statuses"]:
        if isinstance(record, dict):
            validate_portfolio_repository_status_dict(record)
    _require_list(payload, "findings")
    for record in payload["findings"]:
        if isinstance(record, dict):
            validate_portfolio_executive_finding_dict(record)
    _require_int(payload, "portfolio_health_score")
    _require_int(payload, "portfolio_readiness_score")
    _require_list(payload, "recommended_execution_order")
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def _require_str(payload: Dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} required")
    return value


def _require_bool(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), bool):
        raise ValueError(f"{key} must be bool")


def _require_int(payload: Dict[str, Any], key: str) -> None:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be integer")


def _require_dict(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), dict):
        raise ValueError(f"{key} must be dict")


def _require_list(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), list):
        raise ValueError(f"{key} must be list")


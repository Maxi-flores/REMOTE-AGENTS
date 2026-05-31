from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


SEVERITIES = {"info", "low", "medium", "high", "critical"}
CATEGORIES = {
    "dependency_missing",
    "dependency_unknown",
    "dependency_blocked",
    "dependency_risk",
    "dependency_chain",
    "dependency_readiness",
}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class RepositoryDependency:
    repository_id: str
    depends_on: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository_id": self.repository_id,
            "depends_on": list(self.depends_on),
            "metadata": dict(self.metadata),
        }


@dataclass
class DependencyFinding:
    finding_id: str
    severity: str
    repository_id: str
    dependency_repository_id: str
    category: str
    title: str
    description: str
    impact: str
    recommended_action: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "severity": self.severity,
            "repository_id": self.repository_id,
            "dependency_repository_id": self.dependency_repository_id,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "impact": self.impact,
            "recommended_action": self.recommended_action,
            "metadata": dict(self.metadata),
        }


@dataclass
class DependencyGraphReport:
    report_id: str
    generated_utc: str
    dependency_graph: Dict[str, List[str]]
    dependency_chains: List[List[str]]
    findings: List[Dict[str, Any]]
    portfolio_impact: Dict[str, Any]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_utc": self.generated_utc,
            "dependency_graph": dict(self.dependency_graph),
            "dependency_chains": list(self.dependency_chains),
            "findings": list(self.findings),
            "portfolio_impact": dict(self.portfolio_impact),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


def validate_repository_dependency_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "repository_id")
    _require_list(payload, "depends_on")
    _require_dict(payload, "metadata")


def validate_dependency_finding_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "finding_id")
    sev = _require_str(payload, "severity")
    if sev not in SEVERITIES:
        raise ValueError(f"invalid severity: {sev}")
    _require_str(payload, "repository_id")
    _require_str(payload, "dependency_repository_id")
    cat = _require_str(payload, "category")
    if cat not in CATEGORIES:
        raise ValueError(f"invalid category: {cat}")
    _require_str(payload, "title")
    _require_str(payload, "description")
    _require_str(payload, "impact")
    _require_str(payload, "recommended_action")
    _require_dict(payload, "metadata")


def validate_dependency_graph_report_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "report_id")
    _require_str(payload, "generated_utc")
    _require_dict(payload, "dependency_graph")
    _require_list(payload, "dependency_chains")
    _require_list(payload, "findings")
    for finding in payload["findings"]:
        if isinstance(finding, dict):
            validate_dependency_finding_dict(finding)
    _require_dict(payload, "portfolio_impact")
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


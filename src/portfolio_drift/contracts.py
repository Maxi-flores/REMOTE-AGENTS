from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


SEVERITIES = {"info", "low", "medium", "high", "critical"}
DRIFT_TYPES = {
    "missing_registry_reference",
    "missing_dependency_reference",
    "stale_artifact",
    "stale_recommendation",
    "contradictory_status",
    "missing_bootstrap_record",
    "missing_progress_metric",
    "orphaned_roadmap_item",
    "orphaned_critical_path_recommendation",
    "unknown",
}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class PortfolioDriftFinding:
    finding_id: str
    severity: str
    drift_type: str
    source_artifact: str
    target_artifact: str
    repository_id: str
    title: str
    description: str
    recommended_action: str
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "severity": self.severity,
            "drift_type": self.drift_type,
            "source_artifact": self.source_artifact,
            "target_artifact": self.target_artifact,
            "repository_id": self.repository_id,
            "title": self.title,
            "description": self.description,
            "recommended_action": self.recommended_action,
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class PortfolioDriftReport:
    report_id: str
    generated_utc: str
    findings: List[Dict[str, Any]]
    summary: Dict[str, Any]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_utc": self.generated_utc,
            "findings": list(self.findings),
            "summary": dict(self.summary),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


def validate_portfolio_drift_finding_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "finding_id")
    sev = _require_str(payload, "severity")
    if sev not in SEVERITIES:
        raise ValueError(f"invalid severity: {sev}")
    drift_type = _require_str(payload, "drift_type")
    if drift_type not in DRIFT_TYPES:
        raise ValueError(f"invalid drift_type: {drift_type}")
    _require_str(payload, "source_artifact")
    _require_str(payload, "target_artifact")
    _require_str(payload, "repository_id")
    _require_str(payload, "title")
    _require_str(payload, "description")
    _require_str(payload, "recommended_action")
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def validate_portfolio_drift_report_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "report_id")
    _require_str(payload, "generated_utc")
    _require_list(payload, "findings")
    for finding in payload["findings"]:
        if isinstance(finding, dict):
            validate_portfolio_drift_finding_dict(finding)
    _require_dict(payload, "summary")
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


def _require_dict(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), dict):
        raise ValueError(f"{key} must be dict")


def _require_list(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), list):
        raise ValueError(f"{key} must be list")


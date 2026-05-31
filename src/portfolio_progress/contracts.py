from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


TRENDS = {"improving", "stable", "declining", "unknown"}
SEVERITIES = {"info", "low", "medium", "high", "critical"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class PortfolioProgressMetric:
    metric_id: str
    repository_id: str
    metric_name: str
    current_value: float
    previous_value: float | None
    delta: float | None
    trend: str
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "repository_id": self.repository_id,
            "metric_name": self.metric_name,
            "current_value": float(self.current_value),
            "previous_value": None if self.previous_value is None else float(self.previous_value),
            "delta": None if self.delta is None else float(self.delta),
            "trend": self.trend,
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class PortfolioProgressFinding:
    finding_id: str
    severity: str
    repository_id: str
    title: str
    description: str
    trend: str
    recommended_action: str
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "severity": self.severity,
            "repository_id": self.repository_id,
            "title": self.title,
            "description": self.description,
            "trend": self.trend,
            "recommended_action": self.recommended_action,
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class PortfolioProgressReport:
    report_id: str
    generated_utc: str
    metrics: List[Dict[str, Any]]
    findings: List[Dict[str, Any]]
    portfolio_trends: Dict[str, Any]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_utc": self.generated_utc,
            "metrics": list(self.metrics),
            "findings": list(self.findings),
            "portfolio_trends": dict(self.portfolio_trends),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


def validate_portfolio_progress_metric_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "metric_id")
    _require_str(payload, "repository_id")
    _require_str(payload, "metric_name")
    _require_number(payload, "current_value")
    _require_optional_number(payload, "previous_value")
    _require_optional_number(payload, "delta")
    trend = _require_str(payload, "trend")
    if trend not in TRENDS:
        raise ValueError(f"invalid trend: {trend}")
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def validate_portfolio_progress_finding_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "finding_id")
    severity = _require_str(payload, "severity")
    if severity not in SEVERITIES:
        raise ValueError(f"invalid severity: {severity}")
    _require_str(payload, "repository_id")
    _require_str(payload, "title")
    _require_str(payload, "description")
    trend = _require_str(payload, "trend")
    if trend not in TRENDS:
        raise ValueError(f"invalid trend: {trend}")
    _require_str(payload, "recommended_action")
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def validate_portfolio_progress_report_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "report_id")
    _require_str(payload, "generated_utc")
    _require_list(payload, "metrics")
    for metric in payload["metrics"]:
        if isinstance(metric, dict):
            validate_portfolio_progress_metric_dict(metric)
    _require_list(payload, "findings")
    for finding in payload["findings"]:
        if isinstance(finding, dict):
            validate_portfolio_progress_finding_dict(finding)
    _require_dict(payload, "portfolio_trends")
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def _require_str(payload: Dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} required")
    return value


def _require_number(payload: Dict[str, Any], key: str) -> None:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be number")


def _require_optional_number(payload: Dict[str, Any], key: str) -> None:
    value = payload.get(key)
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be number or null")


def _require_bool(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), bool):
        raise ValueError(f"{key} must be bool")


def _require_dict(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), dict):
        raise ValueError(f"{key} must be dict")


def _require_list(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), list):
        raise ValueError(f"{key} must be list")


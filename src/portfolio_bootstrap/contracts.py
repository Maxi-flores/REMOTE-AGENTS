from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


ARTIFACT_STATUSES = {"none", "partial", "complete", "unknown"}
ONBOARDING_STATES = {"discovered", "registered", "assessed", "onboarded"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class RepositoryOnboardingRecord:
    repository_id: str
    repository_name: str
    repository_path: str
    discovered: bool
    artifact_status: str
    readiness_estimate: int
    onboarding_state: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository_id": self.repository_id,
            "repository_name": self.repository_name,
            "repository_path": self.repository_path,
            "discovered": bool(self.discovered),
            "artifact_status": self.artifact_status,
            "readiness_estimate": int(self.readiness_estimate),
            "onboarding_state": self.onboarding_state,
            "metadata": dict(self.metadata),
        }


@dataclass
class PortfolioBootstrapReport:
    report_id: str
    generated_utc: str
    repositories: List[Dict[str, Any]]
    onboarding_records: List[Dict[str, Any]]
    readiness_summary: Dict[str, Any]
    recommendations: List[str]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_utc": self.generated_utc,
            "repositories": list(self.repositories),
            "onboarding_records": list(self.onboarding_records),
            "readiness_summary": dict(self.readiness_summary),
            "recommendations": list(self.recommendations),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


def validate_repository_onboarding_record_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "repository_id")
    _require_str(payload, "repository_name")
    _require_str(payload, "repository_path")
    _require_bool(payload, "discovered")
    artifact_status = _require_str(payload, "artifact_status")
    if artifact_status not in ARTIFACT_STATUSES:
        raise ValueError(f"invalid artifact_status: {artifact_status}")
    _require_int(payload, "readiness_estimate")
    onboarding_state = _require_str(payload, "onboarding_state")
    if onboarding_state not in ONBOARDING_STATES:
        raise ValueError(f"invalid onboarding_state: {onboarding_state}")
    _require_dict(payload, "metadata")


def validate_portfolio_bootstrap_report_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "report_id")
    _require_str(payload, "generated_utc")
    _require_list(payload, "repositories")
    _require_list(payload, "onboarding_records")
    for record in payload["onboarding_records"]:
        if isinstance(record, dict):
            validate_repository_onboarding_record_dict(record)
    _require_dict(payload, "readiness_summary")
    _require_list(payload, "recommendations")
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


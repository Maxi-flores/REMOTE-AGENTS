from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


FINDING_CATEGORIES = {
    "documentation",
    "testing",
    "runtime",
    "config",
    "contracts",
    "governance",
    "lifecycle",
    "release",
    "memory",
    "system",
}
FINDING_SEVERITIES = {"info", "low", "medium", "high", "critical"}
REPORT_STATUSES = {"healthy", "warning", "degraded", "critical", "unknown"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class RepositoryInventory:
    inventory_id: str
    generated_utc: str
    root_path: str
    source_directories: List[str]
    test_files: List[str]
    documentation_files: List[str]
    config_files: List[str]
    package_files: List[str]
    runtime_entrypoints: List[str]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "inventory_id": self.inventory_id,
            "generated_utc": self.generated_utc,
            "root_path": self.root_path,
            "source_directories": list(self.source_directories),
            "test_files": list(self.test_files),
            "documentation_files": list(self.documentation_files),
            "config_files": list(self.config_files),
            "package_files": list(self.package_files),
            "runtime_entrypoints": list(self.runtime_entrypoints),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class RepositoryCoverageFinding:
    finding_id: str
    category: str
    severity: str
    title: str
    description: str
    path_refs: List[str]
    recommended_action: str
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "category": self.category,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "path_refs": list(self.path_refs),
            "recommended_action": self.recommended_action,
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class RepositoryIntelligenceReport:
    report_id: str
    generated_utc: str
    repository_name: str
    overall_status: str
    inventory: Dict[str, Any]
    findings: List[Dict[str, Any]]
    suggested_mission_opportunities: List[str]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_utc": self.generated_utc,
            "repository_name": self.repository_name,
            "overall_status": self.overall_status,
            "inventory": dict(self.inventory),
            "findings": list(self.findings),
            "suggested_mission_opportunities": list(self.suggested_mission_opportunities),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


def validate_repository_inventory_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "inventory_id")
    _require_str(payload, "generated_utc")
    _require_str(payload, "root_path")
    for key in (
        "source_directories",
        "test_files",
        "documentation_files",
        "config_files",
        "package_files",
        "runtime_entrypoints",
    ):
        _require_list(payload, key)
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def validate_repository_coverage_finding_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "finding_id")
    cat = _require_str(payload, "category")
    if cat not in FINDING_CATEGORIES:
        raise ValueError(f"invalid category: {cat}")
    severity = _require_str(payload, "severity")
    if severity not in FINDING_SEVERITIES:
        raise ValueError(f"invalid severity: {severity}")
    _require_str(payload, "title")
    _require_str(payload, "description")
    _require_list(payload, "path_refs")
    _require_str(payload, "recommended_action")
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def validate_repository_intelligence_report_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "report_id")
    _require_str(payload, "generated_utc")
    _require_str(payload, "repository_name")
    status = _require_str(payload, "overall_status")
    if status not in REPORT_STATUSES:
        raise ValueError(f"invalid overall_status: {status}")
    _require_dict(payload, "inventory")
    validate_repository_inventory_dict(payload["inventory"])
    _require_list(payload, "findings")
    for finding in payload.get("findings", []):
        if isinstance(finding, dict):
            validate_repository_coverage_finding_dict(finding)
    _require_list(payload, "suggested_mission_opportunities")
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


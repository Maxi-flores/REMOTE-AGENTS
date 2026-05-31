from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


RISK_LEVELS = {"low", "medium", "high", "critical"}
ESTIMATED_SCOPES = {"tiny", "small", "medium", "large"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class RefinedImplementationPackage:
    refined_package_id: str
    source_package_id: str
    source_batch_id: str
    title: str
    objective: str
    subsystem: str
    change_type: str
    target_files: List[str]
    expected_changes: Dict[str, Any]
    validation_commands: List[str]
    risk_level: str
    estimated_scope: str
    traceability_refs: List[str]
    codex_prompt: Dict[str, Any]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "refined_package_id": self.refined_package_id,
            "source_package_id": self.source_package_id,
            "source_batch_id": self.source_batch_id,
            "title": self.title,
            "objective": self.objective,
            "subsystem": self.subsystem,
            "change_type": self.change_type,
            "target_files": list(self.target_files),
            "expected_changes": dict(self.expected_changes),
            "validation_commands": list(self.validation_commands),
            "risk_level": self.risk_level,
            "estimated_scope": self.estimated_scope,
            "traceability_refs": list(self.traceability_refs),
            "codex_prompt": dict(self.codex_prompt),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class RefinementReport:
    report_id: str
    generated_utc: str
    source_handoff_report_id: str
    refined_packages: List[Dict[str, Any]]
    split_summary: Dict[str, Any]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_utc": self.generated_utc,
            "source_handoff_report_id": self.source_handoff_report_id,
            "refined_packages": list(self.refined_packages),
            "split_summary": dict(self.split_summary),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


def validate_refined_implementation_package_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "refined_package_id")
    _require_str(payload, "source_package_id")
    _require_str(payload, "source_batch_id")
    _require_str(payload, "title")
    _require_str(payload, "objective")
    _require_str(payload, "subsystem")
    _require_str(payload, "change_type")
    _require_list(payload, "target_files")
    _require_dict(payload, "expected_changes")
    _require_list(payload, "validation_commands")
    risk = _require_str(payload, "risk_level")
    if risk not in RISK_LEVELS:
        raise ValueError(f"invalid risk_level: {risk}")
    scope = _require_str(payload, "estimated_scope")
    if scope not in ESTIMATED_SCOPES:
        raise ValueError(f"invalid estimated_scope: {scope}")
    _require_list(payload, "traceability_refs")
    _require_dict(payload, "codex_prompt")
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def validate_refinement_report_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "report_id")
    _require_str(payload, "generated_utc")
    _require_str(payload, "source_handoff_report_id")
    _require_list(payload, "refined_packages")
    for package in payload["refined_packages"]:
        if isinstance(package, dict):
            validate_refined_implementation_package_dict(package)
    _require_dict(payload, "split_summary")
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

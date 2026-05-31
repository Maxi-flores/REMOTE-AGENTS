from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


EXECUTION_RISKS = {"low", "medium", "high", "critical"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class ExecutionDossier:
    dossier_id: str
    generated_utc: str
    source_queue_item_id: str
    source_package_id: str
    title: str
    objective: str
    subsystem: str
    target_files: List[str]
    expected_changes: Dict[str, Any]
    validation_commands: List[str]
    rollback_guidance: List[str]
    review_checklist: List[str]
    execution_readiness_score: int
    execution_risk: str
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dossier_id": self.dossier_id,
            "generated_utc": self.generated_utc,
            "source_queue_item_id": self.source_queue_item_id,
            "source_package_id": self.source_package_id,
            "title": self.title,
            "objective": self.objective,
            "subsystem": self.subsystem,
            "target_files": list(self.target_files),
            "expected_changes": dict(self.expected_changes),
            "validation_commands": list(self.validation_commands),
            "rollback_guidance": list(self.rollback_guidance),
            "review_checklist": list(self.review_checklist),
            "execution_readiness_score": int(self.execution_readiness_score),
            "execution_risk": self.execution_risk,
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class ExecutionPacket:
    packet_id: str
    dossier_id: str
    codex_prompt: str
    execution_summary: str
    validation_summary: str
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "dossier_id": self.dossier_id,
            "codex_prompt": self.codex_prompt,
            "execution_summary": self.execution_summary,
            "validation_summary": self.validation_summary,
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class ExecutionDossierReport:
    report_id: str
    generated_utc: str
    dossiers: List[Dict[str, Any]]
    execution_packets: List[Dict[str, Any]]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_utc": self.generated_utc,
            "dossiers": list(self.dossiers),
            "execution_packets": list(self.execution_packets),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


def validate_execution_dossier_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "dossier_id")
    _require_str(payload, "generated_utc")
    _require_str(payload, "source_queue_item_id")
    _require_str(payload, "source_package_id")
    _require_str(payload, "title")
    _require_str(payload, "objective")
    _require_str(payload, "subsystem")
    _require_list(payload, "target_files")
    _require_dict(payload, "expected_changes")
    _require_list(payload, "validation_commands")
    _require_list(payload, "rollback_guidance")
    _require_list(payload, "review_checklist")
    score = payload.get("execution_readiness_score")
    if isinstance(score, bool) or not isinstance(score, int):
        raise ValueError("execution_readiness_score must be integer")
    risk = _require_str(payload, "execution_risk")
    if risk not in EXECUTION_RISKS:
        raise ValueError(f"invalid execution_risk: {risk}")
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def validate_execution_packet_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "packet_id")
    _require_str(payload, "dossier_id")
    _require_str(payload, "codex_prompt")
    _require_str(payload, "execution_summary")
    _require_str(payload, "validation_summary")
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def validate_execution_dossier_report_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "report_id")
    _require_str(payload, "generated_utc")
    _require_list(payload, "dossiers")
    for dossier in payload["dossiers"]:
        if isinstance(dossier, dict):
            validate_execution_dossier_dict(dossier)
    _require_list(payload, "execution_packets")
    for packet in payload["execution_packets"]:
        if isinstance(packet, dict):
            validate_execution_packet_dict(packet)
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

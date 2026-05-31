from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


APPROVAL_STATUSES = {"ready_for_review", "needs_review", "blocked", "rejected_advisory", "unknown"}
ALLOWED_DECISIONS = {"approve_for_manual_execution", "request_changes", "reject", "defer"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class HumanDecisionTemplate:
    allowed_decisions: List[str]
    required_reviewer: str
    decision_notes_placeholder: str
    decision_timestamp_placeholder: str
    safety_acknowledgements: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed_decisions": list(self.allowed_decisions),
            "required_reviewer": self.required_reviewer,
            "decision_notes_placeholder": self.decision_notes_placeholder,
            "decision_timestamp_placeholder": self.decision_timestamp_placeholder,
            "safety_acknowledgements": list(self.safety_acknowledgements),
        }


@dataclass
class GovernanceApprovalPacket:
    packet_id: str
    source_readiness_record_id: str
    source_dossier_id: str
    title: str
    approval_status: str
    readiness_score: int
    risk_level: str
    review_summary: str
    target_artifacts: List[str]
    validation_commands: List[str]
    rollback_guidance: List[str]
    human_decision_template: Dict[str, Any]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "source_readiness_record_id": self.source_readiness_record_id,
            "source_dossier_id": self.source_dossier_id,
            "title": self.title,
            "approval_status": self.approval_status,
            "readiness_score": int(self.readiness_score),
            "risk_level": self.risk_level,
            "review_summary": self.review_summary,
            "target_artifacts": list(self.target_artifacts),
            "validation_commands": list(self.validation_commands),
            "rollback_guidance": list(self.rollback_guidance),
            "human_decision_template": dict(self.human_decision_template),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class GovernanceApprovalPacketReport:
    report_id: str
    generated_utc: str
    source_readiness_report_id: str
    packets: List[Dict[str, Any]]
    summary: Dict[str, Any]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_utc": self.generated_utc,
            "source_readiness_report_id": self.source_readiness_report_id,
            "packets": list(self.packets),
            "summary": dict(self.summary),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


def validate_human_decision_template_dict(payload: Dict[str, Any]) -> None:
    _require_list(payload, "allowed_decisions")
    for decision in payload["allowed_decisions"]:
        if decision not in ALLOWED_DECISIONS:
            raise ValueError(f"invalid allowed decision: {decision}")
    if not isinstance(payload.get("required_reviewer"), str):
        raise ValueError("required_reviewer must be string")
    if not isinstance(payload.get("decision_notes_placeholder"), str):
        raise ValueError("decision_notes_placeholder must be string")
    if not isinstance(payload.get("decision_timestamp_placeholder"), str):
        raise ValueError("decision_timestamp_placeholder must be string")
    _require_list(payload, "safety_acknowledgements")


def validate_governance_approval_packet_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "packet_id")
    _require_str(payload, "source_readiness_record_id")
    _require_str(payload, "source_dossier_id")
    _require_str(payload, "title")
    status = _require_str(payload, "approval_status")
    if status not in APPROVAL_STATUSES:
        raise ValueError(f"invalid approval_status: {status}")
    score = payload.get("readiness_score")
    if isinstance(score, bool) or not isinstance(score, int):
        raise ValueError("readiness_score must be integer")
    _require_str(payload, "risk_level")
    _require_str(payload, "review_summary")
    _require_list(payload, "target_artifacts")
    _require_list(payload, "validation_commands")
    _require_list(payload, "rollback_guidance")
    hdt = payload.get("human_decision_template")
    if not isinstance(hdt, dict):
        raise ValueError("human_decision_template must be dict")
    validate_human_decision_template_dict(hdt)
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def validate_governance_approval_packet_report_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "report_id")
    _require_str(payload, "generated_utc")
    _require_str(payload, "source_readiness_report_id")
    _require_list(payload, "packets")
    for packet in payload["packets"]:
        if isinstance(packet, dict):
            validate_governance_approval_packet_dict(packet)
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


def _require_bool(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), bool):
        raise ValueError(f"{key} must be bool")


def _require_dict(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), dict):
        raise ValueError(f"{key} must be dict")

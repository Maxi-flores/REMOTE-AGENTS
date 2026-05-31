from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


ALLOWED_DECISIONS = {"approve_for_manual_execution", "request_changes", "reject", "defer"}
REQUIRED_APPROVAL_ACKS = {
    "runtime_paths_reviewed",
    "queue_mutation_forbidden_acknowledged",
    "validation_commands_reviewed",
    "rollback_guidance_reviewed",
    "manual_execution_only_acknowledged",
}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class GovernanceHumanDecisionRecord:
    decision_id: str
    packet_id: str
    source_dossier_id: str
    decision: str
    reviewer: str
    decision_notes: str
    decided_utc: str
    safety_acknowledgements: List[str]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "packet_id": self.packet_id,
            "source_dossier_id": self.source_dossier_id,
            "decision": self.decision,
            "reviewer": self.reviewer,
            "decision_notes": self.decision_notes,
            "decided_utc": self.decided_utc,
            "safety_acknowledgements": list(self.safety_acknowledgements),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class GovernanceDecisionSummaryReport:
    report_id: str
    generated_utc: str
    source_packet_report_id: str
    decisions: List[Dict[str, Any]]
    pending_packet_ids: List[str]
    approved_packet_ids: List[str]
    request_changes_packet_ids: List[str]
    rejected_packet_ids: List[str]
    deferred_packet_ids: List[str]
    summary: Dict[str, Any]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_utc": self.generated_utc,
            "source_packet_report_id": self.source_packet_report_id,
            "decisions": list(self.decisions),
            "pending_packet_ids": list(self.pending_packet_ids),
            "approved_packet_ids": list(self.approved_packet_ids),
            "request_changes_packet_ids": list(self.request_changes_packet_ids),
            "rejected_packet_ids": list(self.rejected_packet_ids),
            "deferred_packet_ids": list(self.deferred_packet_ids),
            "summary": dict(self.summary),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


def validate_governance_human_decision_record_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "decision_id")
    _require_str(payload, "packet_id")
    _require_str(payload, "source_dossier_id")
    decision = _require_str(payload, "decision")
    if decision not in ALLOWED_DECISIONS:
        raise ValueError(f"invalid decision: {decision}")
    _require_str(payload, "reviewer")
    _require_str(payload, "decision_notes")
    _require_str(payload, "decided_utc")
    _require_list(payload, "safety_acknowledgements")
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")
    _validate_decision_requirements(payload)


def validate_governance_decision_summary_report_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "report_id")
    _require_str(payload, "generated_utc")
    _require_str(payload, "source_packet_report_id")
    _require_list(payload, "decisions")
    for decision in payload["decisions"]:
        if isinstance(decision, dict):
            validate_governance_human_decision_record_dict(decision)
    _require_list(payload, "pending_packet_ids")
    _require_list(payload, "approved_packet_ids")
    _require_list(payload, "request_changes_packet_ids")
    _require_list(payload, "rejected_packet_ids")
    _require_list(payload, "deferred_packet_ids")
    _require_dict(payload, "summary")
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def _validate_decision_requirements(payload: Dict[str, Any]) -> None:
    decision = str(payload.get("decision") or "")
    if decision == "approve_for_manual_execution":
        acks = payload.get("safety_acknowledgements")
        ack_set = {str(a) for a in acks if isinstance(a, str)} if isinstance(acks, list) else set()
        missing = sorted(REQUIRED_APPROVAL_ACKS - ack_set)
        if missing:
            raise ValueError(f"missing required acknowledgements: {', '.join(missing)}")


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


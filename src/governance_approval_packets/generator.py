from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from governance_approval_packets.contracts import (
    GovernanceApprovalPacket,
    GovernanceApprovalPacketReport,
    HumanDecisionTemplate,
    new_id,
    utc_now,
    validate_governance_approval_packet_report_dict,
)


def load_json(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def generate_governance_approval_packet_report(
    *,
    readiness_report: Dict[str, Any] | None = None,
    dossier_report: Dict[str, Any] | None = None,
    readiness_report_path: str | Path | None = None,
    dossier_report_path: str | Path | None = None,
    base_dir: str | Path = ".",
) -> Dict[str, Any]:
    root = Path(base_dir)
    if readiness_report is None:
        readiness_report = load_json(
            Path(readiness_report_path) if readiness_report_path else root / ".control_plane" / "governance_approval_readiness" / "latest.json"
        )
    if dossier_report is None:
        dossier_report = load_json(
            Path(dossier_report_path) if dossier_report_path else root / ".control_plane" / "governance_recovery_dossiers" / "latest.json"
        )
    records = readiness_report.get("records") if isinstance(readiness_report.get("records"), list) else []
    dossiers = dossier_report.get("dossiers") if isinstance(dossier_report.get("dossiers"), list) else []
    dossier_by_id = {str(d.get("dossier_id") or ""): d for d in dossiers if isinstance(d, dict)}
    dossier_by_title = {str(d.get("title") or ""): d for d in dossiers if isinstance(d, dict)}

    packets: List[Dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        status = str(record.get("approval_status") or "unknown")
        if status not in {"ready_for_review", "needs_review"}:
            continue
        dossier = dossier_by_id.get(str(record.get("dossier_id") or ""), {})
        if not dossier:
            dossier = dossier_by_title.get(str(record.get("title") or ""), {})
        packets.append(_build_packet(record, dossier))

    report = GovernanceApprovalPacketReport(
        report_id=new_id("governance_approval_packet_report"),
        generated_utc=utc_now(),
        source_readiness_report_id=str(readiness_report.get("report_id") or "missing_readiness_report"),
        packets=packets,
        summary=_summary(packets, records),
        advisory_only=True,
        metadata={
            "advisory_only": True,
            "runtime_unchanged": True,
            "queue_mutation": False,
            "source_readiness_report_path": str(readiness_report_path or root / ".control_plane" / "governance_approval_readiness" / "latest.json"),
            "source_dossier_report_path": str(dossier_report_path or root / ".control_plane" / "governance_recovery_dossiers" / "latest.json"),
        },
    ).to_dict()
    validate_governance_approval_packet_report_dict(report)
    return report


def _build_packet(record: Dict[str, Any], dossier: Dict[str, Any]) -> Dict[str, Any]:
    title = str(record.get("title") or dossier.get("title") or "Governance approval packet")
    risk_level = str(record.get("risk_level") or "unknown")
    status = str(record.get("approval_status") or "unknown")
    missing = record.get("missing_requirements")
    missing_items = [str(item) for item in missing if isinstance(item, str)] if isinstance(missing, list) else []
    review_summary = (
        "Human-review approval packet only. This does NOT grant approval and does NOT execute anything. "
        f"Status: {status}. Risk: {risk_level}. "
        + (f"Missing requirements: {', '.join(missing_items)}." if missing_items else "No missing requirements detected.")
    )
    template = HumanDecisionTemplate(
        allowed_decisions=[
            "approve_for_manual_execution",
            "request_changes",
            "reject",
            "defer",
        ],
        required_reviewer="",
        decision_notes_placeholder="",
        decision_timestamp_placeholder="",
        safety_acknowledgements=[
            "I understand this packet does not execute anything.",
            "I understand runtime paths are forbidden.",
            "I understand queue mutation is forbidden.",
            "I reviewed validation commands.",
        ],
    ).to_dict()
    return GovernanceApprovalPacket(
        packet_id=new_id("governance_approval_packet"),
        source_readiness_record_id=str(record.get("record_id") or ""),
        source_dossier_id=str(record.get("dossier_id") or ""),
        title=title,
        approval_status=status,
        readiness_score=int(record.get("readiness_score") or 0),
        risk_level=risk_level,
        review_summary=review_summary,
        target_artifacts=[str(a) for a in dossier.get("target_artifacts", []) if isinstance(a, str)] if isinstance(dossier, dict) else [],
        validation_commands=[str(c) for c in dossier.get("validation_commands", []) if isinstance(c, str)] if isinstance(dossier, dict) else [],
        rollback_guidance=[str(r) for r in dossier.get("rollback_guidance", []) if isinstance(r, str)] if isinstance(dossier, dict) else [],
        human_decision_template=template,
        advisory_only=True,
        metadata={
            "advisory_only": True,
            "required_human_review": bool(record.get("required_human_review") is True),
            "approval_recommendation": str(record.get("approval_recommendation") or ""),
        },
    ).to_dict()


def _summary(packets: List[Dict[str, Any]], records: List[Dict[str, Any]]) -> Dict[str, Any]:
    ready = 0
    review = 0
    for packet in packets:
        if not isinstance(packet, dict):
            continue
        status = str(packet.get("approval_status") or "unknown")
        if status == "ready_for_review":
            ready += 1
        elif status == "needs_review":
            review += 1
    skipped = 0
    for record in records:
        if not isinstance(record, dict):
            continue
        status = str(record.get("approval_status") or "unknown")
        if status in {"blocked", "rejected_advisory"}:
            skipped += 1
    return {
        "packets_generated": len(packets),
        "ready_for_review_packets": ready,
        "needs_review_packets": review,
        "skipped_blocked_or_rejected": skipped,
    }

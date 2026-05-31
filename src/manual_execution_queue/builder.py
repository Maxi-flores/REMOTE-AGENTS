from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from manual_execution_queue.contracts import (
    ManualExecutionQueueItem,
    ManualExecutionQueueReport,
    new_id,
    utc_now,
    validate_manual_execution_queue_report_dict,
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


def generate_manual_execution_queue_report(
    *,
    decision_report: Dict[str, Any] | None = None,
    packet_report: Dict[str, Any] | None = None,
    decision_report_path: str | Path | None = None,
    packet_report_path: str | Path | None = None,
    base_dir: str | Path = ".",
) -> Dict[str, Any]:
    root = Path(base_dir)
    if decision_report is None:
        decision_report = load_json(Path(decision_report_path) if decision_report_path else root / ".control_plane" / "governance_decisions" / "latest.json")
    if packet_report is None:
        packet_report = load_json(Path(packet_report_path) if packet_report_path else root / ".control_plane" / "governance_approval_packets" / "latest.json")

    packets = packet_report.get("packets") if isinstance(packet_report.get("packets"), list) else []
    decisions = decision_report.get("decisions") if isinstance(decision_report.get("decisions"), list) else []
    by_packet: Dict[str, Dict[str, Any]] = {}
    for decision in decisions:
        if not isinstance(decision, dict):
            continue
        packet_id = str(decision.get("packet_id") or "")
        if packet_id:
            by_packet[packet_id] = decision

    queue_items: List[Dict[str, Any]] = []
    for packet in packets:
        if not isinstance(packet, dict):
            continue
        packet_id = str(packet.get("packet_id") or "")
        if not packet_id:
            continue
        decision = by_packet.get(packet_id, {})
        queue_items.append(_build_queue_item(packet, decision))

    queue_items = sorted(queue_items, key=lambda item: (_priority_order(str(item.get("priority") or "P4")), str(item.get("title") or "")))
    report = ManualExecutionQueueReport(
        report_id=new_id("manual_execution_queue_report"),
        generated_utc=utc_now(),
        source_decision_report_id=str(decision_report.get("report_id") or "missing_decision_report"),
        queue_items=queue_items,
        summary=_summary(queue_items),
        advisory_only=True,
        metadata={
            "advisory_only": True,
            "runtime_unchanged": True,
            "queue_mutation": False,
            "source_decision_report_path": str(decision_report_path or root / ".control_plane" / "governance_decisions" / "latest.json"),
            "source_packet_report_path": str(packet_report_path or root / ".control_plane" / "governance_approval_packets" / "latest.json"),
        },
    ).to_dict()
    validate_manual_execution_queue_report_dict(report)
    return report


def _build_queue_item(packet: Dict[str, Any], decision_record: Dict[str, Any]) -> Dict[str, Any]:
    decision = str(decision_record.get("decision") or "pending_review")
    status, priority, next_step = _state_from_decision(decision)
    safety_notes = [
        "This queue does not execute anything.",
        "This queue does not mutate .platform_queue.",
        "This queue does not grant runtime approval.",
    ]
    return ManualExecutionQueueItem(
        queue_item_id=new_id("manual_execution_queue_item"),
        packet_id=str(packet.get("packet_id") or ""),
        source_dossier_id=str(packet.get("source_dossier_id") or ""),
        decision=decision,
        queue_status=status,
        title=str(packet.get("title") or "Governance packet"),
        priority=priority,
        operator_next_step=next_step,
        validation_commands=[str(c) for c in packet.get("validation_commands", []) if isinstance(c, str)] if isinstance(packet.get("validation_commands"), list) else [],
        safety_notes=safety_notes,
        advisory_only=True,
        metadata={
            "approval_status": str(packet.get("approval_status") or "unknown"),
            "risk_level": str(packet.get("risk_level") or "unknown"),
            "reviewer": str(decision_record.get("reviewer") or ""),
        },
    ).to_dict()


def _state_from_decision(decision: str) -> tuple[str, str, str]:
    if decision == "approve_for_manual_execution":
        return ("approved_manual", "P1", "Prepare manual execution using packet/dossier instructions.")
    if decision == "defer":
        return ("deferred", "P3", "Revisit when blocking review condition is resolved.")
    if decision == "request_changes":
        return ("needs_changes", "P2", "Revise approval packet/dossier before review.")
    if decision == "reject":
        return ("rejected", "P4", "Archive or redesign recovery action.")
    if decision in {"pending_review", ""}:
        return ("pending_review", "P2", "Review approval packet and record decision.")
    return ("unknown", "P4", "Review packet/decision state for manual triage.")


def _priority_order(priority: str) -> int:
    return {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}.get(priority, 4)


def _summary(queue_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    out = {
        "approved_manual": 0,
        "pending_review": 0,
        "deferred": 0,
        "needs_changes": 0,
        "rejected": 0,
        "unknown": 0,
        "total_items": len(queue_items),
    }
    for item in queue_items:
        status = str(item.get("queue_status") or "unknown")
        out[status] = int(out.get(status, 0)) + 1
    return out


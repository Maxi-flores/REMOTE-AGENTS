from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

from governance_decisions.contracts import (
    GovernanceDecisionSummaryReport,
    new_id,
    utc_now,
    validate_governance_decision_summary_report_dict,
)
from governance_decisions.store import load_decisions


def load_json(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def generate_governance_decision_summary_report(
    *,
    packet_report: Dict[str, Any] | None = None,
    packet_report_path: str | Path | None = None,
    decisions_state: Dict[str, Any] | None = None,
    decisions_path: str | Path | None = None,
    base_dir: str | Path = ".",
) -> Dict[str, Any]:
    root = Path(base_dir)
    if packet_report is None:
        packet_report = load_json(
            Path(packet_report_path) if packet_report_path else root / ".control_plane" / "governance_approval_packets" / "latest.json"
        )
    if decisions_state is None:
        decisions_state = load_decisions(
            Path(decisions_path) if decisions_path else root / ".control_plane" / "governance_decisions" / "decisions.json"
        )
    packets = packet_report.get("packets") if isinstance(packet_report.get("packets"), list) else []
    decisions = decisions_state.get("decisions") if isinstance(decisions_state.get("decisions"), list) else []
    by_packet: Dict[str, Dict[str, Any]] = {}
    for record in decisions:
        if not isinstance(record, dict):
            continue
        pid = str(record.get("packet_id") or "")
        if pid:
            by_packet[pid] = record

    pending: List[str] = []
    approved: List[str] = []
    req_changes: List[str] = []
    rejected: List[str] = []
    deferred: List[str] = []

    for packet in packets:
        if not isinstance(packet, dict):
            continue
        packet_id = str(packet.get("packet_id") or "")
        if not packet_id:
            continue
        record = by_packet.get(packet_id)
        if not record:
            pending.append(packet_id)
            continue
        decision = str(record.get("decision") or "")
        if decision == "approve_for_manual_execution":
            approved.append(packet_id)
        elif decision == "request_changes":
            req_changes.append(packet_id)
        elif decision == "reject":
            rejected.append(packet_id)
        elif decision == "defer":
            deferred.append(packet_id)
        else:
            pending.append(packet_id)

    report = GovernanceDecisionSummaryReport(
        report_id=new_id("governance_decision_summary_report"),
        generated_utc=utc_now(),
        source_packet_report_id=str(packet_report.get("report_id") or "missing_packet_report"),
        decisions=[d for d in decisions if isinstance(d, dict)],
        pending_packet_ids=pending,
        approved_packet_ids=approved,
        request_changes_packet_ids=req_changes,
        rejected_packet_ids=rejected,
        deferred_packet_ids=deferred,
        summary={
            "total_packets": len([p for p in packets if isinstance(p, dict)]),
            "pending": len(pending),
            "approved": len(approved),
            "request_changes": len(req_changes),
            "rejected": len(rejected),
            "deferred": len(deferred),
        },
        advisory_only=True,
        metadata={
            "advisory_only": True,
            "runtime_unchanged": True,
            "queue_mutation": False,
            "source_packet_report_path": str(packet_report_path or root / ".control_plane" / "governance_approval_packets" / "latest.json"),
            "source_decisions_path": str(decisions_path or root / ".control_plane" / "governance_decisions" / "decisions.json"),
        },
    ).to_dict()
    validate_governance_decision_summary_report_dict(report)
    return report


def write_governance_decision_summary_report(
    report: Dict[str, Any],
    path: str | Path = ".control_plane/governance_decisions/latest.json",
) -> Path:
    out = Path(path)
    _require_path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(f".{out.name}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp, out)
    return out


def write_timestamped_governance_decision_summary_report(
    report: Dict[str, Any],
    directory: str | Path = ".control_plane/governance_decisions",
) -> Path:
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return write_governance_decision_summary_report(report, path=Path(directory) / f"report_{ts}.json")


def append_governance_decision_summary_report_jsonl(
    report: Dict[str, Any],
    path: str | Path = ".control_plane/governance_decisions/history.jsonl",
) -> Path:
    out = Path(path)
    _require_path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(report, sort_keys=True))
        handle.write("\n")
    return out


def _require_path(path: Path) -> None:
    normalized = str(path).replace("\\", "/")
    if "/.control_plane/governance_decisions/" not in f"/{normalized}":
        raise ValueError("path must be under .control_plane/governance_decisions/")


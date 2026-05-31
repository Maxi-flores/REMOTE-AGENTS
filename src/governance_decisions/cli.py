from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Sequence, TextIO

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from governance_decisions.contracts import GovernanceHumanDecisionRecord, new_id, utc_now
from governance_decisions.reports import (
    generate_governance_decision_summary_report,
    load_json,
    append_governance_decision_summary_report_jsonl,
    write_governance_decision_summary_report,
    write_timestamped_governance_decision_summary_report,
)
from governance_decisions.store import append_decision


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Governance Human Decision Records CLI.")
    parser.add_argument("--print", action="store_true", dest="print_report")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--export-jsonl", action="store_true")
    parser.add_argument("--base-dir", default=".")
    parser.add_argument("--record-decision", action="store_true")
    parser.add_argument("--packet-id")
    parser.add_argument("--decision")
    parser.add_argument("--reviewer")
    parser.add_argument("--notes")
    parser.add_argument("--ack", action="append", default=[])
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None, stderr: TextIO | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    root = Path(args.base_dir)

    if args.record_decision:
        try:
            ok, message = _record_decision(args, root)
        except ValueError as exc:
            err.write(str(exc) + "\n")
            return 1
        if not ok:
            err.write(message + "\n")
            return 1
        out.write(message + "\n")

    report = generate_governance_decision_summary_report(base_dir=root)
    if args.export:
        write_governance_decision_summary_report(report, path=root / ".control_plane" / "governance_decisions" / "latest.json")
        write_timestamped_governance_decision_summary_report(report, directory=root / ".control_plane" / "governance_decisions")
    if args.export_jsonl:
        append_governance_decision_summary_report_jsonl(report, path=root / ".control_plane" / "governance_decisions" / "history.jsonl")
    if args.print_report or not (args.export or args.export_jsonl):
        summary = report.get("summary", {}) if isinstance(report.get("summary"), dict) else {}
        out.write("Governance Decision Summary\n\n")
        out.write(f"Approved for manual execution: {summary.get('approved', 0)}\n")
        out.write(f"Pending: {summary.get('pending', 0)}\n")
        out.write(f"Deferred: {summary.get('deferred', 0)}\n")
        out.write(f"Request changes: {summary.get('request_changes', 0)}\n")
        out.write(f"Rejected: {summary.get('rejected', 0)}\n\n")
        out.write(json.dumps(report, indent=2, sort_keys=True))
        out.write("\n")
    return 0


def _record_decision(args: argparse.Namespace, root: Path) -> tuple[bool, str]:
    packet_id = str(args.packet_id or "").strip()
    decision = str(args.decision or "").strip()
    reviewer = str(args.reviewer or "").strip()
    notes = str(args.notes or "").strip()
    if not packet_id or not decision or not reviewer or not notes:
        return False, "record-decision requires --packet-id, --decision, --reviewer, and --notes"
    packet_report = load_json(root / ".control_plane" / "governance_approval_packets" / "latest.json")
    packets = packet_report.get("packets") if isinstance(packet_report.get("packets"), list) else []
    packet = _find_packet(packets, packet_id)
    if not packet:
        return False, f"packet not found: {packet_id}"
    record = GovernanceHumanDecisionRecord(
        decision_id=new_id("governance_decision"),
        packet_id=packet_id,
        source_dossier_id=str(packet.get("source_dossier_id") or ""),
        decision=decision,
        reviewer=reviewer,
        decision_notes=notes,
        decided_utc=utc_now(),
        safety_acknowledgements=[str(a) for a in (args.ack or []) if isinstance(a, str)],
        advisory_only=True,
        metadata={
            "advisory_only": True,
            "manual_recorded_via_cli": True,
            "runtime_unchanged": True,
            "queue_mutation": False,
        },
    ).to_dict()
    append_decision(record, path=root / ".control_plane" / "governance_decisions" / "decisions.json")
    return True, f"recorded decision for packet_id={packet_id}"


def _find_packet(packets: list[Dict[str, Any]], packet_id: str) -> Dict[str, Any]:
    for packet in packets:
        if not isinstance(packet, dict):
            continue
        if str(packet.get("packet_id") or "") == packet_id:
            return packet
    return {}


if __name__ == "__main__":
    raise SystemExit(main())

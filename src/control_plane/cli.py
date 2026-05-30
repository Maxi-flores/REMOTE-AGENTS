from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence, TextIO

from control_plane.bootstrap import bootstrap_advisory_artifacts
from control_plane.orchestrator import create_orchestration_request, run_orchestration
from control_plane.orchestrator_reports import (
    append_orchestration_report_jsonl,
    write_orchestration_report,
)
from control_plane.snapshot import (
    build_control_plane_snapshot,
    export_control_plane_snapshot,
    export_control_plane_snapshot_jsonl,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only control-plane snapshot exporter.")
    parser.add_argument("--print", action="store_true", dest="print_snapshot", help="Print snapshot JSON to stdout.")
    parser.add_argument("--export", action="store_true", help="Write .control_plane/snapshot.json.")
    parser.add_argument("--export-jsonl", action="store_true", help="Append .control_plane/snapshots.jsonl.")
    parser.add_argument("--run-orchestration", action="store_true", help="Run advisory CPOL orchestration report generation.")
    parser.add_argument("--bootstrap-artifacts", action="store_true", help="Create minimal advisory artifacts for CPOL.")
    parser.add_argument("--mission-id", help="Optional mission id for orchestration context.")
    parser.add_argument("--trigger-source", default="manual", help="Orchestration trigger source.")
    parser.add_argument("--base-dir", default=".", help="Workspace root to read runtime state from.")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    out = stdout or sys.stdout

    did_work = False
    base_dir = Path(args.base_dir)
    if args.bootstrap_artifacts:
        result = bootstrap_advisory_artifacts(base_dir=base_dir)
        if args.print_snapshot:
            out.write(json.dumps({"bootstrap": result}, indent=2, sort_keys=True))
            out.write("\n")
        did_work = True

    if args.run_orchestration:
        request = create_orchestration_request(
            trigger_source=str(args.trigger_source or "manual"),
            mission_id=args.mission_id if isinstance(args.mission_id, str) and args.mission_id.strip() else None,
        )
        report = run_orchestration(request, base_dir=base_dir)
        if args.export:
            write_orchestration_report(
                report,
                path=base_dir / ".control_plane" / "orchestration" / "orchestration_report.json",
            )
        if args.export_jsonl:
            append_orchestration_report_jsonl(
                report,
                path=base_dir / ".control_plane" / "orchestration" / "orchestration_reports.jsonl",
            )
        if args.print_snapshot or not (args.export or args.export_jsonl):
            out.write(json.dumps(report, indent=2, sort_keys=True))
            out.write("\n")
        did_work = True
        return 0

    if args.print_snapshot:
        snapshot = build_control_plane_snapshot(base_dir=base_dir)
        out.write(json.dumps(snapshot, indent=2, sort_keys=True))
        out.write("\n")
        did_work = True
    if args.export:
        export_control_plane_snapshot(path=base_dir / ".control_plane" / "snapshot.json", base_dir=base_dir)
        did_work = True
    if args.export_jsonl:
        export_control_plane_snapshot_jsonl(path=base_dir / ".control_plane" / "snapshots.jsonl", base_dir=base_dir)
        did_work = True
    if not did_work:
        parser.print_help(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

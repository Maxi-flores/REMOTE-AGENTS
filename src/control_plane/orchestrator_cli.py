from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict
from typing import Sequence, TextIO

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from control_plane.bootstrap import bootstrap_advisory_artifacts
from control_plane.orchestrator import create_orchestration_request, run_orchestration
from control_plane.orchestrator_reports import (
    append_orchestration_report_jsonl,
    write_orchestration_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Advisory Control Plane Orchestration Layer (CPOL) CLI.")
    parser.add_argument("--print", action="store_true", dest="print_report")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--export-jsonl", action="store_true")
    parser.add_argument("--mission-id")
    parser.add_argument("--trigger-source", default="manual")
    parser.add_argument("--base-dir", default=".")
    parser.add_argument("--bootstrap-artifacts", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    out = stdout or sys.stdout
    base_dir = Path(args.base_dir)

    if args.bootstrap_artifacts:
        result = bootstrap_advisory_artifacts(base_dir=base_dir)
        out.write(json.dumps({"bootstrap": result}, indent=2, sort_keys=True))
        out.write("\n")
        return 0

    request = create_orchestration_request(
        trigger_source=str(args.trigger_source or "manual"),
        mission_id=args.mission_id if isinstance(args.mission_id, str) and args.mission_id.strip() else None,
    )
    report = run_orchestration(request, base_dir=base_dir)

    payload: Dict[str, Any]
    if args.export:
        path = write_orchestration_report(
            report,
            path=base_dir / ".control_plane" / "orchestration" / "orchestration_report.json",
        )
        payload = {"report": report, "report_path": str(path)}
    elif args.export_jsonl:
        path = append_orchestration_report_jsonl(
            report,
            path=base_dir / ".control_plane" / "orchestration" / "orchestration_reports.jsonl",
        )
        payload = {"report": report, "report_path": str(path)}
    else:
        payload = {"report": report}

    if args.print_report or not (args.export or args.export_jsonl):
        out.write(json.dumps(payload, indent=2, sort_keys=True))
        out.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

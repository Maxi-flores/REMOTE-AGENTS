from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence, TextIO

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from governance_approval_readiness.evaluator import generate_governance_approval_readiness_report
from governance_approval_readiness.reports import (
    append_governance_approval_readiness_report_jsonl,
    write_governance_approval_readiness_report,
    write_timestamped_governance_approval_readiness_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Governance Approval Readiness CLI.")
    parser.add_argument("--print", action="store_true", dest="print_report")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--export-jsonl", action="store_true")
    parser.add_argument("--base-dir", default=".")
    parser.add_argument("--from-dossier-report")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = stdout or sys.stdout
    base_dir = Path(args.base_dir)
    report = generate_governance_approval_readiness_report(
        base_dir=base_dir,
        dossier_report_path=args.from_dossier_report,
    )
    if args.export:
        write_governance_approval_readiness_report(
            report,
            path=base_dir / ".control_plane" / "governance_approval_readiness" / "latest.json",
        )
        write_timestamped_governance_approval_readiness_report(
            report,
            directory=base_dir / ".control_plane" / "governance_approval_readiness",
        )
    if args.export_jsonl:
        append_governance_approval_readiness_report_jsonl(
            report,
            path=base_dir / ".control_plane" / "governance_approval_readiness" / "history.jsonl",
        )
    if args.print_report or not (args.export or args.export_jsonl):
        summary = report.get("summary", {}) if isinstance(report.get("summary"), dict) else {}
        out.write("Governance Approval Readiness\n\n")
        out.write(f"ready_for_review: {summary.get('ready_for_review', 0)}\n")
        out.write(f"needs_review: {summary.get('needs_review', 0)}\n")
        out.write(f"blocked: {summary.get('blocked', 0)}\n")
        out.write(f"rejected_advisory: {summary.get('rejected_advisory', 0)}\n\n")
        out.write(json.dumps(report, indent=2, sort_keys=True))
        out.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


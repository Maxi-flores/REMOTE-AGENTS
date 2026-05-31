from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence, TextIO

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from remediation_planner.generator import generate_remediation_plan_report
from remediation_planner.reports import (
    append_remediation_plan_report_jsonl,
    write_remediation_plan_report,
    write_timestamped_remediation_plan_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Repository Remediation Planner (RRP) CLI.")
    parser.add_argument("--print", action="store_true", dest="print_report")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--export-jsonl", action="store_true")
    parser.add_argument("--from-rie-report")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--base-dir", default=".")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    out = stdout or sys.stdout
    base_dir = Path(args.base_dir)

    report = generate_remediation_plan_report(
        rie_report_path=args.from_rie_report,
        base_dir=base_dir,
        limit=args.limit,
    )

    if args.export:
        write_remediation_plan_report(
            report,
            path=base_dir / ".control_plane" / "remediation_plans" / "remediation_plan_report.json",
        )
        write_timestamped_remediation_plan_report(
            report,
            directory=base_dir / ".control_plane" / "remediation_plans",
        )
    if args.export_jsonl:
        append_remediation_plan_report_jsonl(
            report,
            path=base_dir / ".control_plane" / "remediation_plans" / "remediation_plan_reports.jsonl",
        )

    if args.print_report or not (args.export or args.export_jsonl):
        out.write("Repository Remediation Plan\n\n")
        for item in report.get("items", []):
            if not isinstance(item, dict):
                continue
            out.write(f"{item.get('priority', 'P4')}: {item.get('title', 'Untitled')}\n")
        out.write("\n")
        out.write(json.dumps(report, indent=2, sort_keys=True))
        out.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

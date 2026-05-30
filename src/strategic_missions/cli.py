from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence, TextIO

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from strategic_missions.generator import generate_strategic_mission_report, render_strategic_mission_report_text
from strategic_missions.reports import append_strategic_mission_report_jsonl, write_strategic_mission_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Strategic Mission Generation Engine (SMGE) CLI.")
    parser.add_argument("--print", action="store_true", dest="print_report")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--export-jsonl", action="store_true")
    parser.add_argument("--from-briefing")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--base-dir", default=".")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    out = stdout or sys.stdout
    base_dir = Path(args.base_dir)

    report = generate_strategic_mission_report(
        briefing_path=args.from_briefing,
        base_dir=base_dir,
        limit=args.limit,
    )

    if args.export:
        write_strategic_mission_report(
            report,
            path=base_dir / ".control_plane" / "strategic_missions" / "strategic_mission_report.json",
        )
    if args.export_jsonl:
        append_strategic_mission_report_jsonl(
            report,
            path=base_dir / ".control_plane" / "strategic_missions" / "strategic_mission_reports.jsonl",
        )

    if args.print_report or not (args.export or args.export_jsonl):
        out.write(render_strategic_mission_report_text(report))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


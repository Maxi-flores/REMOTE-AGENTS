from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence, TextIO

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from executive_briefing.briefing_builder import build_executive_briefing, render_briefing_text
from executive_briefing.reports import append_executive_briefing_report_jsonl, write_executive_briefing_report
from lifecycle_manager.bootstrap import seed_lifecycle_capabilities


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Advisory Executive Mission Briefing Layer (EMBL) CLI.")
    parser.add_argument("--print", action="store_true", dest="print_briefing")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--export-jsonl", action="store_true")
    parser.add_argument("--from-orchestration-report", help="Optional orchestration report path override.")
    parser.add_argument("--from-control-plane", default=".", help="Base workspace directory containing advisory artifacts.")
    parser.add_argument("--seed-lifecycle", action="store_true", help="Seed advisory lifecycle capability and state entries.")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    out = stdout or sys.stdout
    base_dir = Path(args.from_control_plane)
    if args.seed_lifecycle:
        seed_summary = seed_lifecycle_capabilities(base_dir=base_dir)
        out.write(json.dumps({"lifecycle_seed": seed_summary}, indent=2, sort_keys=True))
        out.write("\n")
        return 0

    briefing = build_executive_briefing(
        base_dir=base_dir,
        orchestration_report_path=args.from_orchestration_report,
    )

    if args.export:
        write_executive_briefing_report(briefing, path=base_dir / ".control_plane" / "executive" / "executive_briefing.json")
    if args.export_jsonl:
        append_executive_briefing_report_jsonl(
            briefing,
            path=base_dir / ".control_plane" / "executive" / "executive_briefings.jsonl",
        )

    if args.print_briefing or not (args.export or args.export_jsonl):
        out.write(render_briefing_text(briefing))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

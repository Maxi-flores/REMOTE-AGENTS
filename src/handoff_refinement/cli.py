from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence, TextIO

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from handoff_refinement.refiner import generate_refinement_report
from handoff_refinement.reports import (
    append_refinement_report_jsonl,
    write_refinement_report,
    write_timestamped_refinement_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Handoff Package Refinement Engine (HPRE) CLI.")
    parser.add_argument("--print", action="store_true", dest="print_report")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--export-jsonl", action="store_true")
    parser.add_argument("--from-handoff-report")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--base-dir", default=".")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = stdout or sys.stdout
    base_dir = Path(args.base_dir)
    report = generate_refinement_report(
        handoff_report_path=args.from_handoff_report,
        base_dir=base_dir,
        limit=args.limit,
    )
    if args.export:
        write_refinement_report(report, path=base_dir / ".control_plane" / "handoff_refinements" / "latest.json")
        write_timestamped_refinement_report(report, directory=base_dir / ".control_plane" / "handoff_refinements")
    if args.export_jsonl:
        append_refinement_report_jsonl(report, path=base_dir / ".control_plane" / "handoff_refinements" / "history.jsonl")
    if args.print_report or not (args.export or args.export_jsonl):
        out.write("Refined Implementation Packages\n\n")
        for package in report.get("refined_packages", []):
            if isinstance(package, dict):
                out.write(f"- {package.get('title', 'Untitled')}\n")
        out.write("\n")
        out.write(json.dumps(report, indent=2, sort_keys=True))
        out.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence, TextIO

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from repository_intelligence.analyzer import analyze_repository_intelligence
from repository_intelligence.reports import (
    append_repository_intelligence_report_jsonl,
    write_repository_intelligence_report,
    write_timestamped_repository_intelligence_report,
)
from repository_intelligence.scanner import build_repository_inventory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Repository Intelligence Engine (RIE) CLI.")
    parser.add_argument("--print", action="store_true", dest="print_report")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--export-jsonl", action="store_true")
    parser.add_argument("--base-dir", default=".")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    out = stdout or sys.stdout
    base_dir = Path(args.base_dir)

    inventory = build_repository_inventory(base_dir=base_dir)
    report = analyze_repository_intelligence(inventory, repository_name=base_dir.resolve().name)

    if args.export:
        write_repository_intelligence_report(
            report,
            path=base_dir / ".control_plane" / "repository_intelligence" / "repository_intelligence_report.json",
        )
        write_timestamped_repository_intelligence_report(
            report,
            directory=base_dir / ".control_plane" / "repository_intelligence",
        )
    if args.export_jsonl:
        append_repository_intelligence_report_jsonl(
            report,
            path=base_dir / ".control_plane" / "repository_intelligence" / "repository_intelligence_reports.jsonl",
        )

    if args.print_report or not (args.export or args.export_jsonl):
        out.write(json.dumps(report, indent=2, sort_keys=True))
        out.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


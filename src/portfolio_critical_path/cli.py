from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence, TextIO

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from portfolio_critical_path.analyzer import generate_portfolio_critical_path_report
from portfolio_critical_path.reports import (
    append_portfolio_critical_path_report_jsonl,
    write_portfolio_critical_path_report,
    write_timestamped_portfolio_critical_path_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Portfolio Critical Path Intelligence (PCPI) CLI.")
    parser.add_argument("--print", action="store_true", dest="print_report")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--export-jsonl", action="store_true")
    parser.add_argument("--base-dir", default=".")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = stdout or sys.stdout
    base_dir = Path(args.base_dir)
    report = generate_portfolio_critical_path_report(base_dir=base_dir)
    if args.export:
        write_portfolio_critical_path_report(report, path=base_dir / ".control_plane" / "portfolio_critical_path" / "latest.json")
        write_timestamped_portfolio_critical_path_report(report, directory=base_dir / ".control_plane" / "portfolio_critical_path")
    if args.export_jsonl:
        append_portfolio_critical_path_report_jsonl(report, path=base_dir / ".control_plane" / "portfolio_critical_path" / "history.jsonl")
    if args.print_report or not (args.export or args.export_jsonl):
        out.write("Portfolio Critical Path\n\n")
        out.write("Top Critical Repositories:\n")
        for idx, rid in enumerate(report.get("top_critical_repositories", []), start=1):
            out.write(f"{idx}. {rid}\n")
        out.write("\nTop Recommendations:\n")
        for rec in report.get("recommendations", []):
            if not isinstance(rec, dict):
                continue
            out.write(f"{rec.get('priority', 'P4')} {rec.get('title', '')}\n")
        out.write("\n")
        out.write(json.dumps(report, indent=2, sort_keys=True))
        out.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


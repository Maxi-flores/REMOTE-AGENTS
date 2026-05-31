from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence, TextIO

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from portfolio_progress.analyzer import generate_portfolio_progress_report
from portfolio_progress.reports import (
    append_portfolio_progress_report_jsonl,
    write_portfolio_progress_report,
    write_timestamped_portfolio_progress_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Portfolio Progress Intelligence Layer (PPIL) CLI.")
    parser.add_argument("--print", action="store_true", dest="print_report")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--export-jsonl", action="store_true")
    parser.add_argument("--base-dir", default=".")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = stdout or sys.stdout
    base_dir = Path(args.base_dir)
    report = generate_portfolio_progress_report(base_dir=base_dir)
    if args.export:
        write_portfolio_progress_report(report, path=base_dir / ".control_plane" / "portfolio_progress" / "latest.json")
        write_timestamped_portfolio_progress_report(report, directory=base_dir / ".control_plane" / "portfolio_progress")
    if args.export_jsonl:
        append_portfolio_progress_report_jsonl(report, path=base_dir / ".control_plane" / "portfolio_progress" / "history.jsonl")
    if args.print_report or not (args.export or args.export_jsonl):
        out.write("Portfolio Progress Summary\n\n")
        for metric in report.get("metrics", []):
            if not isinstance(metric, dict):
                continue
            if str(metric.get("repository_id") or "") != "portfolio":
                continue
            out.write(
                f"{metric.get('metric_name')}: "
                f"{metric.get('previous_value')} -> {metric.get('current_value')} "
                f"({metric.get('trend')})\n"
            )
        out.write("\n")
        out.write(json.dumps(report, indent=2, sort_keys=True))
        out.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


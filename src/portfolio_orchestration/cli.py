from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence, TextIO

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from portfolio_orchestration.aggregator import generate_portfolio_report
from portfolio_orchestration.reports import (
    append_portfolio_report_jsonl,
    write_portfolio_report,
    write_timestamped_portfolio_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Portfolio Orchestration Layer (POL) CLI.")
    parser.add_argument("--print", action="store_true", dest="print_report")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--export-jsonl", action="store_true")
    parser.add_argument("--registry")
    parser.add_argument("--base-dir", default=".")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = stdout or sys.stdout
    base_dir = Path(args.base_dir)
    report = generate_portfolio_report(base_dir=base_dir, registry_path=args.registry)
    if args.export:
        write_portfolio_report(report, path=base_dir / ".control_plane" / "portfolio" / "latest.json")
        write_timestamped_portfolio_report(report, directory=base_dir / ".control_plane" / "portfolio")
    if args.export_jsonl:
        append_portfolio_report_jsonl(report, path=base_dir / ".control_plane" / "portfolio" / "history.jsonl")
    if args.print_report or not (args.export or args.export_jsonl):
        out.write("Portfolio Status Report\n\n")
        out.write(
            f"Portfolio Health: {report.get('portfolio_health_score', 0)} | "
            f"Portfolio Readiness: {report.get('portfolio_readiness_score', 0)}\n"
        )
        for status in report.get("repository_statuses", []):
            if not isinstance(status, dict):
                continue
            out.write(
                f"- {status.get('repository_id', 'unknown')} | "
                f"Health: {status.get('health_score', 0)} | "
                f"Readiness: {status.get('readiness_score', 0)} | "
                f"Status: {status.get('overall_status', 'unknown')}\n"
            )
        out.write("\n")
        out.write(json.dumps(report, indent=2, sort_keys=True))
        out.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


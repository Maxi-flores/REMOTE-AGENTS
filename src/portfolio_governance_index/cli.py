from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence, TextIO

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from portfolio_governance_index.analyzer import generate_portfolio_governance_health_report
from portfolio_governance_index.reports import (
    append_portfolio_governance_health_report_jsonl,
    write_portfolio_governance_health_report,
    write_timestamped_portfolio_governance_health_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Portfolio Governance Health Index (PGHI) CLI.")
    parser.add_argument("--print", action="store_true", dest="print_report")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--export-jsonl", action="store_true")
    parser.add_argument("--base-dir", default=".")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = stdout or sys.stdout
    base_dir = Path(args.base_dir)
    report = generate_portfolio_governance_health_report(base_dir=base_dir)
    if args.export:
        write_portfolio_governance_health_report(report, path=base_dir / ".control_plane" / "portfolio_governance_index" / "latest.json")
        write_timestamped_portfolio_governance_health_report(report, directory=base_dir / ".control_plane" / "portfolio_governance_index")
    if args.export_jsonl:
        append_portfolio_governance_health_report_jsonl(report, path=base_dir / ".control_plane" / "portfolio_governance_index" / "history.jsonl")
    if args.print_report or not (args.export or args.export_jsonl):
        out.write("Portfolio Governance Health Index\n\n")
        out.write(f"Governance Score: {report.get('governance_score', 0)} / 100\n")
        out.write(f"Status: {report.get('governance_status', 'unknown')}\n\n")
        out.write("Components:\n")
        for component in report.get("components", []):
            if not isinstance(component, dict):
                continue
            out.write(f"- {component.get('name', '')}: {component.get('score', 0)} ({component.get('status', 'unknown')})\n")
        out.write("\n")
        out.write(json.dumps(report, indent=2, sort_keys=True))
        out.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


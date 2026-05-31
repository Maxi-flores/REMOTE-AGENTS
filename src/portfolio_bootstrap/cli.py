from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence, TextIO

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from portfolio_bootstrap.onboarding import generate_portfolio_bootstrap_report
from portfolio_bootstrap.reports import (
    append_portfolio_bootstrap_report_jsonl,
    write_portfolio_bootstrap_report,
    write_timestamped_portfolio_bootstrap_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Portfolio Artifact Bootstrap Layer (PABL) CLI.")
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
    report = generate_portfolio_bootstrap_report(base_dir=base_dir, registry_path=args.registry)
    if args.export:
        write_portfolio_bootstrap_report(report, path=base_dir / ".control_plane" / "portfolio_bootstrap" / "latest.json")
        write_timestamped_portfolio_bootstrap_report(report, directory=base_dir / ".control_plane" / "portfolio_bootstrap")
    if args.export_jsonl:
        append_portfolio_bootstrap_report_jsonl(report, path=base_dir / ".control_plane" / "portfolio_bootstrap" / "history.jsonl")
    if args.print_report or not (args.export or args.export_jsonl):
        out.write("Portfolio Bootstrap Summary\n\n")
        for record in report.get("onboarding_records", []):
            if not isinstance(record, dict):
                continue
            out.write(
                f"{record.get('repository_name', 'unknown')}\n"
                f"Status: {record.get('onboarding_state', 'unknown')}\n"
                f"Artifacts: {record.get('artifact_status', 'unknown')}\n\n"
            )
        out.write("Recommendations:\n")
        for idx, rec in enumerate(report.get("recommendations", []), start=1):
            if isinstance(rec, str):
                out.write(f"{idx}. {rec}\n")
        out.write("\n")
        out.write(json.dumps(report, indent=2, sort_keys=True))
        out.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


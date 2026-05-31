from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence, TextIO

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from portfolio_onboarding_recommendations.generator import generate_portfolio_onboarding_recommendation_report
from portfolio_onboarding_recommendations.reports import (
    append_portfolio_onboarding_recommendation_report_jsonl,
    write_portfolio_onboarding_recommendation_report,
    write_timestamped_portfolio_onboarding_recommendation_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Portfolio Repository Onboarding Recommendations (PROR) CLI.")
    parser.add_argument("--print", action="store_true", dest="print_report")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--export-jsonl", action="store_true")
    parser.add_argument("--from-bootstrap-report")
    parser.add_argument("--base-dir", default=".")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = stdout or sys.stdout
    base_dir = Path(args.base_dir)
    report = generate_portfolio_onboarding_recommendation_report(
        base_dir=base_dir,
        bootstrap_report_path=args.from_bootstrap_report,
    )
    if args.export:
        write_portfolio_onboarding_recommendation_report(report, path=base_dir / ".control_plane" / "portfolio_onboarding_recommendations" / "latest.json")
        write_timestamped_portfolio_onboarding_recommendation_report(report, directory=base_dir / ".control_plane" / "portfolio_onboarding_recommendations")
    if args.export_jsonl:
        append_portfolio_onboarding_recommendation_report_jsonl(report, path=base_dir / ".control_plane" / "portfolio_onboarding_recommendations" / "history.jsonl")
    if args.print_report or not (args.export or args.export_jsonl):
        out.write("Portfolio Onboarding Recommendations\n\n")
        for item in report.get("recommendations", []):
            if not isinstance(item, dict):
                continue
            out.write(f"{item.get('priority', 'P4')} {item.get('repository_name', 'unknown')}\n")
            out.write(f"{item.get('title', '')}\n")
            out.write("Recommended actions:\n")
            for action in item.get("recommended_actions", []):
                if isinstance(action, str):
                    out.write(f"- {action}\n")
            out.write("\n")
        out.write(json.dumps(report, indent=2, sort_keys=True))
        out.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence, TextIO

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from portfolio_dependencies.analyzer import generate_dependency_graph_report
from portfolio_dependencies.reports import (
    append_dependency_graph_report_jsonl,
    write_dependency_graph_report,
    write_timestamped_dependency_graph_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Portfolio Dependency Intelligence Layer (PDIL) CLI.")
    parser.add_argument("--print", action="store_true", dest="print_report")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--export-jsonl", action="store_true")
    parser.add_argument("--base-dir", default=".")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = stdout or sys.stdout
    base_dir = Path(args.base_dir)
    report = generate_dependency_graph_report(base_dir=base_dir)
    if args.export:
        write_dependency_graph_report(report, path=base_dir / ".control_plane" / "portfolio_dependencies" / "latest.json")
        write_timestamped_dependency_graph_report(report, directory=base_dir / ".control_plane" / "portfolio_dependencies")
    if args.export_jsonl:
        append_dependency_graph_report_jsonl(report, path=base_dir / ".control_plane" / "portfolio_dependencies" / "history.jsonl")
    if args.print_report or not (args.export or args.export_jsonl):
        out.write("Portfolio Dependency Summary\n\n")
        for repo, deps in sorted((report.get("dependency_graph") or {}).items()):
            out.write(f"{repo}\n")
            out.write("depends on:\n")
            for dep in deps:
                out.write(f"- {dep}\n")
            out.write("\n")
        out.write("Findings:\n")
        for finding in report.get("findings", []):
            if not isinstance(finding, dict):
                continue
            out.write(f"- [{finding.get('severity', 'info')}] {finding.get('title', '')}\n")
        out.write("\n")
        out.write(json.dumps(report, indent=2, sort_keys=True))
        out.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


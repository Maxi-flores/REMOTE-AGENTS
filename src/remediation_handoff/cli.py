from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence, TextIO

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from remediation_handoff.generator import generate_implementation_package_report
from remediation_handoff.reports import (
    append_implementation_package_report_jsonl,
    write_implementation_package_report,
    write_timestamped_implementation_package_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Remediation Batch Handoff Engine (RBHE) CLI.")
    parser.add_argument("--print", action="store_true", dest="print_report")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--export-jsonl", action="store_true")
    parser.add_argument("--from-remediation-report")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--base-dir", default=".")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    out = stdout or sys.stdout
    base_dir = Path(args.base_dir)

    report = generate_implementation_package_report(
        remediation_report_path=args.from_remediation_report,
        base_dir=base_dir,
        limit=args.limit,
    )
    if args.export:
        write_implementation_package_report(report, path=base_dir / ".control_plane" / "remediation_handoffs" / "latest.json")
        write_timestamped_implementation_package_report(report, directory=base_dir / ".control_plane" / "remediation_handoffs")
    if args.export_jsonl:
        append_implementation_package_report_jsonl(
            report, path=base_dir / ".control_plane" / "remediation_handoffs" / "history.jsonl"
        )

    if args.print_report or not (args.export or args.export_jsonl):
        out.write("Implementation Packages\n\n")
        for package in report.get("packages", []):
            if not isinstance(package, dict):
                continue
            out.write(f"- {package.get('title', 'Untitled')}\n")
        out.write("\n")
        out.write(json.dumps(report, indent=2, sort_keys=True))
        out.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

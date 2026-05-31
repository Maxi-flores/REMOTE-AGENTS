from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence, TextIO

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from governance_recovery.analyzer import generate_governance_recovery_plan_report
from governance_recovery.reports import (
    append_governance_recovery_report_jsonl,
    write_governance_recovery_report,
    write_timestamped_governance_recovery_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Governance Recovery Plan Engine (GRPE) CLI.")
    parser.add_argument("--print", action="store_true", dest="print_report")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--export-jsonl", action="store_true")
    parser.add_argument("--base-dir", default=".")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = stdout or sys.stdout
    base_dir = Path(args.base_dir)
    report = generate_governance_recovery_plan_report(base_dir=base_dir)
    if args.export:
        write_governance_recovery_report(report, path=base_dir / ".control_plane" / "governance_recovery" / "latest.json")
        write_timestamped_governance_recovery_report(report, directory=base_dir / ".control_plane" / "governance_recovery")
    if args.export_jsonl:
        append_governance_recovery_report_jsonl(report, path=base_dir / ".control_plane" / "governance_recovery" / "history.jsonl")
    if args.print_report or not (args.export or args.export_jsonl):
        out.write("Governance Recovery Plan\n\n")
        out.write(f"Current Score: {report.get('current_governance_score', 0)} / 100\n")
        out.write(f"Target Score: {report.get('target_governance_score', 0)} / 100\n\n")
        for wave in report.get("waves", []):
            if not isinstance(wave, dict):
                continue
            out.write(f"{wave.get('title', '')} | Impact +{wave.get('expected_score_impact', 0)}\n")
        out.write("\n")
        out.write(json.dumps(report, indent=2, sort_keys=True))
        out.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


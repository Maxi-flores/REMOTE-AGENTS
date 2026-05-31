from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence, TextIO

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from execution_dossier.generator import generate_execution_dossier_report
from execution_dossier.reports import (
    append_execution_dossier_report_jsonl,
    write_execution_dossier_report,
    write_timestamped_execution_dossier_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Execution Readiness Dossier Engine (ERDE) CLI.")
    parser.add_argument("--print", action="store_true", dest="print_report")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--export-jsonl", action="store_true")
    parser.add_argument("--from-work-queue")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--base-dir", default=".")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = stdout or sys.stdout
    base_dir = Path(args.base_dir)
    report = generate_execution_dossier_report(
        work_queue_path=args.from_work_queue,
        base_dir=base_dir,
        limit=args.limit,
    )
    if args.export:
        write_execution_dossier_report(report, path=base_dir / ".control_plane" / "execution_dossiers" / "latest.json")
        write_timestamped_execution_dossier_report(report, directory=base_dir / ".control_plane" / "execution_dossiers")
    if args.export_jsonl:
        append_execution_dossier_report_jsonl(report, path=base_dir / ".control_plane" / "execution_dossiers" / "history.jsonl")
    if args.print_report or not (args.export or args.export_jsonl):
        out.write("Execution Dossiers\n\n")
        for dossier in report.get("dossiers", []):
            if not isinstance(dossier, dict):
                continue
            out.write(
                f"- {dossier.get('title', 'Untitled')} | "
                f"Readiness: {dossier.get('execution_readiness_score', 0)} | "
                f"Risk: {dossier.get('execution_risk', 'unknown')}\n"
            )
        out.write("\n")
        out.write(json.dumps(report, indent=2, sort_keys=True))
        out.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

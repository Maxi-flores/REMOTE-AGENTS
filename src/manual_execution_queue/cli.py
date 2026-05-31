from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence, TextIO

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from manual_execution_queue.builder import generate_manual_execution_queue_report
from manual_execution_queue.reports import (
    append_manual_execution_queue_report_jsonl,
    write_manual_execution_queue_report,
    write_timestamped_manual_execution_queue_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manual Execution Handoff Queue CLI.")
    parser.add_argument("--print", action="store_true", dest="print_report")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--export-jsonl", action="store_true")
    parser.add_argument("--base-dir", default=".")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = stdout or sys.stdout
    root = Path(args.base_dir)
    report = generate_manual_execution_queue_report(base_dir=root)
    if args.export:
        write_manual_execution_queue_report(report, path=root / ".control_plane" / "manual_execution_queue" / "latest.json")
        write_timestamped_manual_execution_queue_report(report, directory=root / ".control_plane" / "manual_execution_queue")
    if args.export_jsonl:
        append_manual_execution_queue_report_jsonl(report, path=root / ".control_plane" / "manual_execution_queue" / "history.jsonl")
    if args.print_report or not (args.export or args.export_jsonl):
        summary = report.get("summary", {}) if isinstance(report.get("summary"), dict) else {}
        out.write("Manual Execution Handoff Queue\n\n")
        out.write(f"Approved Manual: {summary.get('approved_manual', 0)}\n")
        out.write(f"Pending Review: {summary.get('pending_review', 0)}\n")
        out.write(f"Deferred: {summary.get('deferred', 0)}\n")
        out.write(f"Needs Changes: {summary.get('needs_changes', 0)}\n")
        out.write(f"Rejected: {summary.get('rejected', 0)}\n\n")
        out.write(json.dumps(report, indent=2, sort_keys=True))
        out.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence, TextIO

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from work_queue_manager.planner import generate_work_queue_report
from work_queue_manager.reports import (
    append_work_queue_report_jsonl,
    write_timestamped_work_queue_report,
    write_work_queue_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Autonomous Work Queue Manager (AWQM) CLI.")
    parser.add_argument("--print", action="store_true", dest="print_report")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--export-jsonl", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--base-dir", default=".")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = stdout or sys.stdout
    base_dir = Path(args.base_dir)
    report = generate_work_queue_report(base_dir=base_dir, limit=args.limit)

    if args.export:
        write_work_queue_report(report, path=base_dir / ".control_plane" / "work_queue" / "latest.json")
        write_timestamped_work_queue_report(report, directory=base_dir / ".control_plane" / "work_queue")
    if args.export_jsonl:
        append_work_queue_report_jsonl(report, path=base_dir / ".control_plane" / "work_queue" / "history.jsonl")

    if args.print_report or not (args.export or args.export_jsonl):
        out.write("Work Queue\n\n")
        for item in report.get("queue_items", []):
            if not isinstance(item, dict):
                continue
            out.write(
                f"{item.get('priority', 'P4')} {item.get('title', 'Untitled')} | "
                f"Readiness: {item.get('readiness_score', 0)} | "
                f"Status: {item.get('execution_readiness', 'unknown')}\n"
            )
        out.write("\n")
        out.write(json.dumps(report, indent=2, sort_keys=True))
        out.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence, TextIO

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from portfolio_roadmap.planner import generate_portfolio_roadmap_report
from portfolio_roadmap.reports import (
    append_portfolio_roadmap_report_jsonl,
    write_portfolio_roadmap_report,
    write_timestamped_portfolio_roadmap_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Portfolio Strategic Execution Roadmap Layer (PSERL) CLI.")
    parser.add_argument("--print", action="store_true", dest="print_report")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--export-jsonl", action="store_true")
    parser.add_argument("--base-dir", default=".")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = stdout or sys.stdout
    base_dir = Path(args.base_dir)
    report = generate_portfolio_roadmap_report(base_dir=base_dir)
    if args.export:
        write_portfolio_roadmap_report(report, path=base_dir / ".control_plane" / "portfolio_roadmap" / "latest.json")
        write_timestamped_portfolio_roadmap_report(report, directory=base_dir / ".control_plane" / "portfolio_roadmap")
    if args.export_jsonl:
        append_portfolio_roadmap_report_jsonl(report, path=base_dir / ".control_plane" / "portfolio_roadmap" / "history.jsonl")
    if args.print_report or not (args.export or args.export_jsonl):
        out.write("Portfolio Strategic Roadmap\n\n")
        wave_titles = {str(w.get("wave_id")): str(w.get("title")) for w in report.get("waves", []) if isinstance(w, dict)}
        grouped: dict[str, list[dict]] = {}
        for item in report.get("roadmap_items", []):
            if not isinstance(item, dict):
                continue
            grouped.setdefault(str(item.get("wave") or "wave_3"), []).append(item)
        for wave_id in ("wave_1", "wave_2", "wave_3"):
            title = wave_titles.get(wave_id, wave_id)
            out.write(f"{title}:\n")
            for item in grouped.get(wave_id, []):
                out.write(f"* {item.get('title', 'Untitled')} ({item.get('priority', 'P4')})\n")
            out.write("\n")
        out.write(json.dumps(report, indent=2, sort_keys=True))
        out.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


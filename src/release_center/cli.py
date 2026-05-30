from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence, TextIO

from release_center.reports import (
    append_release_timeline_report_jsonl,
    build_release_timeline_report,
    write_release_timeline_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Advisory Release Center timeline CLI.")
    parser.add_argument("--print", action="store_true", dest="print_report")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--export-jsonl", action="store_true")
    parser.add_argument("--label", default="local-release")
    parser.add_argument("--base-dir", default=".")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    out = stdout or sys.stdout
    base = Path(args.base_dir)
    cwd = Path.cwd()
    try:
        # Keep report building relative to the requested base directory.
        import os

        os.chdir(base)
        report = build_release_timeline_report(release_label=args.label)
    finally:
        import os

        os.chdir(cwd)

    if args.export:
        path = write_release_timeline_report(report, path=base / ".release_reports" / "release_timeline.json")
        payload = {"report": report, "report_path": str(path)}
    elif args.export_jsonl:
        path = append_release_timeline_report_jsonl(
            report, path=base / ".release_reports" / "release_timeline.jsonl"
        )
        payload = {"report": report, "report_path": str(path)}
    else:
        payload = {"report": report}

    if args.print_report or not (args.export or args.export_jsonl):
        out.write(json.dumps(payload, indent=2, sort_keys=True))
        out.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence, TextIO

from release_readiness.drift import (
    analyze_control_plane_snapshot,
    analyze_sentient_ui_view_model,
)
from release_readiness.reports import (
    append_release_readiness_report_jsonl,
    build_full_release_readiness_report,
    write_release_readiness_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Release readiness drift analyzer and report exporter.")
    parser.add_argument("--print", action="store_true", dest="print_report")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--export-jsonl", action="store_true")
    parser.add_argument("--check-file", type=str, default=None)
    parser.add_argument("--artifact-type", type=str, default=None)
    parser.add_argument("--base-dir", type=str, default=".")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    out = stdout or sys.stdout
    base = Path(args.base_dir)

    result: dict | None = None
    if args.check_file:
        if not args.artifact_type:
            raise ValueError("--artifact-type is required with --check-file")
        if args.artifact_type == "control_plane_snapshot":
            findings = analyze_control_plane_snapshot(args.check_file)
        elif args.artifact_type == "sentient_ui_view_model":
            findings = analyze_sentient_ui_view_model(args.check_file)
        else:
            findings = []
        result = {"findings": findings, "artifact_type": args.artifact_type, "artifact_path": args.check_file}
    elif args.export:
        result = write_release_readiness_report(base / ".release_reports" / "release_readiness.json", base_dir=base)
    elif args.export_jsonl:
        result = append_release_readiness_report_jsonl(
            base / ".release_reports" / "release_readiness.jsonl",
            base_dir=base,
        )
    elif args.print_report:
        result = build_full_release_readiness_report(base_dir=base)
    else:
        parser.print_help(out)
        return 0

    out.write(json.dumps(result, indent=2, sort_keys=True))
    out.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


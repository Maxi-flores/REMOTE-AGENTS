from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence, TextIO

from schema_versioning.checker import check_artifact_file, check_jsonl_artifact_file
from schema_versioning.migration_planner import plan_artifact_file_migration, write_migration_dry_run_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Schema versioning compatibility checker and migration dry-run planner.")
    parser.add_argument("--check-control-plane", action="store_true")
    parser.add_argument("--check-sentient-ui", action="store_true")
    parser.add_argument("--check-file", type=str, default=None)
    parser.add_argument("--artifact-type", type=str, default=None)
    parser.add_argument("--plan-migration", type=str, default=None)
    parser.add_argument("--target-version", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--base-dir", type=str, default=".")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    out = stdout or sys.stdout
    base = Path(args.base_dir)

    result: dict | None = None
    if args.check_control_plane:
        result = check_artifact_file(base / ".control_plane" / "snapshot.json", artifact_type="control_plane_snapshot")
    elif args.check_sentient_ui:
        result = check_artifact_file(base / ".sentient_ui" / "view_model.json", artifact_type="sentient_ui_view_model")
    elif args.check_file:
        if not args.artifact_type:
            raise ValueError("--artifact-type is required with --check-file")
        path = Path(args.check_file)
        if args.artifact_type.endswith("_jsonl"):
            result = check_jsonl_artifact_file(path, args.artifact_type)
        else:
            result = check_artifact_file(path, artifact_type=args.artifact_type)
    elif args.plan_migration:
        if not args.artifact_type:
            raise ValueError("--artifact-type is required with --plan-migration")
        plan = plan_artifact_file_migration(args.plan_migration, args.artifact_type, target_version=args.target_version)
        result = {"plan": plan}
        if args.dry_run:
            report_path = write_migration_dry_run_report(plan, output_dir=base / ".schema_migrations")
            result["dry_run_report_path"] = str(report_path)
    else:
        parser.print_help(out)
        return 0

    out.write(json.dumps(result, indent=2, sort_keys=True))
    out.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


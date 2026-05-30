from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence, TextIO

from sentient_ui.exporter import build_and_export_view_model, export_view_model_jsonl
from sentient_ui.snapshot_reader import read_latest_snapshot, read_snapshot_history
from sentient_ui.view_models import build_sentient_view_model


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sentient UI view model adapter CLI.")
    parser.add_argument("--print", action="store_true", dest="print_view_model", help="Print view model JSON to stdout.")
    parser.add_argument("--export", action="store_true", help="Write .sentient_ui/view_model.json.")
    parser.add_argument("--export-jsonl", action="store_true", help="Append .sentient_ui/view_models.jsonl.")
    parser.add_argument("--base-dir", default=".", help="Workspace root containing .control_plane and .sentient_ui.")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    out = stdout or sys.stdout
    base_dir = Path(args.base_dir)

    did_work = False
    snapshot_path = base_dir / ".control_plane" / "snapshot.json"
    history_path = base_dir / ".control_plane" / "snapshots.jsonl"
    if args.print_view_model:
        snapshot = read_latest_snapshot(snapshot_path)
        history = read_snapshot_history(history_path)
        model = build_sentient_view_model(snapshot, history=history)
        out.write(json.dumps(model, indent=2, sort_keys=True))
        out.write("\n")
        did_work = True
    if args.export:
        build_and_export_view_model(
            snapshot_path=snapshot_path,
            history_path=history_path,
            output_path=base_dir / ".sentient_ui" / "view_model.json",
        )
        did_work = True
    if args.export_jsonl:
        export_view_model_jsonl(
            snapshot_path=snapshot_path,
            history_path=history_path,
            output_path=base_dir / ".sentient_ui" / "view_models.jsonl",
        )
        did_work = True
    if not did_work:
        parser.print_help(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


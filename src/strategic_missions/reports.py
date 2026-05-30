from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict


def write_strategic_mission_report(
    report: Dict[str, Any],
    path: str | Path = ".control_plane/strategic_missions/strategic_mission_report.json",
) -> Path:
    out_path = Path(path)
    _require_strategic_missions_path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_name(f".{out_path.name}.tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp_path, out_path)
    return out_path


def append_strategic_mission_report_jsonl(
    report: Dict[str, Any],
    path: str | Path = ".control_plane/strategic_missions/strategic_mission_reports.jsonl",
) -> Path:
    out_path = Path(path)
    _require_strategic_missions_path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(report, sort_keys=True))
        handle.write("\n")
    return out_path


def _require_strategic_missions_path(path: Path) -> None:
    normalized = str(path).replace("\\", "/")
    if "/.control_plane/strategic_missions/" not in f"/{normalized}":
        raise ValueError("path must be under .control_plane/strategic_missions/")


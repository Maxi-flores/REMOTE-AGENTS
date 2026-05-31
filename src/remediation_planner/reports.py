from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict


def write_remediation_plan_report(
    report: Dict[str, Any],
    path: str | Path = ".control_plane/remediation_plans/remediation_plan_report.json",
) -> Path:
    out_path = Path(path)
    _require_path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_name(f".{out_path.name}.tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp_path, out_path)
    return out_path


def write_timestamped_remediation_plan_report(
    report: Dict[str, Any],
    directory: str | Path = ".control_plane/remediation_plans",
) -> Path:
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return write_remediation_plan_report(report, path=Path(directory) / f"remediation_plan_report_{timestamp}.json")


def append_remediation_plan_report_jsonl(
    report: Dict[str, Any],
    path: str | Path = ".control_plane/remediation_plans/remediation_plan_reports.jsonl",
) -> Path:
    out_path = Path(path)
    _require_path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(report, sort_keys=True))
        handle.write("\n")
    return out_path


def _require_path(path: Path) -> None:
    normalized = str(path).replace("\\", "/")
    if "/.control_plane/remediation_plans/" not in f"/{normalized}":
        raise ValueError("path must be under .control_plane/remediation_plans/")

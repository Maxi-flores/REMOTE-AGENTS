from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict


def write_repository_intelligence_report(
    report: Dict[str, Any],
    path: str | Path = ".control_plane/repository_intelligence/repository_intelligence_report.json",
) -> Path:
    out_path = Path(path)
    _require_intel_path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_name(f".{out_path.name}.tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp_path, out_path)
    return out_path


def write_timestamped_repository_intelligence_report(
    report: Dict[str, Any],
    directory: str | Path = ".control_plane/repository_intelligence",
) -> Path:
    dir_path = Path(directory)
    _require_intel_path(dir_path / "placeholder.json")
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return write_repository_intelligence_report(report, path=dir_path / f"repository_intelligence_report_{timestamp}.json")


def append_repository_intelligence_report_jsonl(
    report: Dict[str, Any],
    path: str | Path = ".control_plane/repository_intelligence/repository_intelligence_reports.jsonl",
) -> Path:
    out_path = Path(path)
    _require_intel_path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(report, sort_keys=True))
        handle.write("\n")
    return out_path


def _require_intel_path(path: Path) -> None:
    normalized = str(path).replace("\\", "/")
    if "/.control_plane/repository_intelligence/" not in f"/{normalized}":
        raise ValueError("path must be under .control_plane/repository_intelligence/")


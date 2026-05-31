from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict


def write_manual_execution_queue_report(
    report: Dict[str, Any],
    path: str | Path = ".control_plane/manual_execution_queue/latest.json",
) -> Path:
    out = Path(path)
    _require_path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(f".{out.name}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp, out)
    return out


def write_timestamped_manual_execution_queue_report(
    report: Dict[str, Any],
    directory: str | Path = ".control_plane/manual_execution_queue",
) -> Path:
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return write_manual_execution_queue_report(report, path=Path(directory) / f"report_{ts}.json")


def append_manual_execution_queue_report_jsonl(
    report: Dict[str, Any],
    path: str | Path = ".control_plane/manual_execution_queue/history.jsonl",
) -> Path:
    out = Path(path)
    _require_path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(report, sort_keys=True))
        handle.write("\n")
    return out


def _require_path(path: Path) -> None:
    normalized = str(path).replace("\\", "/")
    if "/.control_plane/manual_execution_queue/" not in f"/{normalized}":
        raise ValueError("path must be under .control_plane/manual_execution_queue/")


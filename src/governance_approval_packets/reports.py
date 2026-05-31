from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict


def write_governance_approval_packet_report(
    report: Dict[str, Any],
    path: str | Path = ".control_plane/governance_approval_packets/latest.json",
) -> Path:
    out_path = Path(path)
    _require_path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_name(f".{out_path.name}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp, out_path)
    return out_path


def write_timestamped_governance_approval_packet_report(
    report: Dict[str, Any],
    directory: str | Path = ".control_plane/governance_approval_packets",
) -> Path:
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return write_governance_approval_packet_report(report, path=Path(directory) / f"report_{timestamp}.json")


def append_governance_approval_packet_report_jsonl(
    report: Dict[str, Any],
    path: str | Path = ".control_plane/governance_approval_packets/history.jsonl",
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
    if "/.control_plane/governance_approval_packets/" not in f"/{normalized}":
        raise ValueError("path must be under .control_plane/governance_approval_packets/")


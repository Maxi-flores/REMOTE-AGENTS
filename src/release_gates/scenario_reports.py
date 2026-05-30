from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict


def build_scenario_report(
    result: Dict[str, Any],
    report: Dict[str, Any] | None = None,
    scenario_pack: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return {
        "comparison": result,
        "readiness_report_summary": {
            "report_id": (report or {}).get("report_id"),
            "readiness_score": (report or {}).get("readiness_score"),
            "readiness_status": (report or {}).get("readiness_status"),
        },
        "scenario_pack_summary": {
            "scenario_pack_id": (scenario_pack or {}).get("scenario_pack_id"),
            "comparison_strategy": (scenario_pack or {}).get("comparison_strategy"),
            "policy_names": (scenario_pack or {}).get("policy_names", []),
            "advisory_only": (scenario_pack or {}).get("advisory_only", True),
        },
        "metadata": {"advisory_only": True},
    }


def write_scenario_report(
    report: Dict[str, Any],
    path: str | Path = ".release_reports/scenario_comparison.json",
) -> Path:
    out_path = Path(path)
    _require_release_reports_path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_name(f".{out_path.name}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp, out_path)
    return out_path


def append_scenario_report_jsonl(
    report: Dict[str, Any],
    path: str | Path = ".release_reports/scenario_comparisons.jsonl",
) -> Path:
    out_path = Path(path)
    _require_release_reports_path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(report, sort_keys=True))
        handle.write("\n")
    return out_path


def _require_release_reports_path(path: Path) -> None:
    normalized = str(path).replace("\\", "/")
    if "/.release_reports/" not in f"/{normalized}":
        raise ValueError("path must be under .release_reports/")


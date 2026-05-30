from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List


def build_promotion_report(
    recommendations: List[Dict[str, Any]],
    scenario_report: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return {
        "recommendations": list(recommendations),
        "scenario_report_summary": {
            "comparison_id": ((scenario_report or {}).get("comparison") or {}).get("comparison_id")
            if isinstance((scenario_report or {}).get("comparison"), dict)
            else None,
            "scenario_pack_id": ((scenario_report or {}).get("scenario_pack_summary") or {}).get("scenario_pack_id")
            if isinstance((scenario_report or {}).get("scenario_pack_summary"), dict)
            else None,
        },
        "metadata": {"advisory_only": True},
    }


def write_promotion_report(
    report: Dict[str, Any],
    path: str | Path = ".release_reports/promotion_recommendations.json",
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


def append_promotion_report_jsonl(
    report: Dict[str, Any],
    path: str | Path = ".release_reports/promotion_recommendations.jsonl",
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


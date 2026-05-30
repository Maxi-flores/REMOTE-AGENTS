from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from release_readiness.drift import (
    analyze_control_plane_jsonl,
    analyze_control_plane_snapshot,
    analyze_schema_manifest,
    analyze_sentient_ui_jsonl,
    analyze_sentient_ui_view_model,
)
from release_readiness.scoring import build_release_readiness_report
from schema_versioning.checker import CONTROL_MANIFEST, UI_MANIFEST


def build_full_release_readiness_report(base_dir: str | Path = ".") -> Dict[str, Any]:
    root = Path(base_dir)
    findings: List[Dict[str, Any]] = []
    checked_artifacts: List[Dict[str, Any]] = []

    control_snapshot = root / ".control_plane" / "snapshot.json"
    control_jsonl = root / ".control_plane" / "snapshots.jsonl"
    ui_snapshot = root / ".sentient_ui" / "view_model.json"
    ui_jsonl = root / ".sentient_ui" / "view_models.jsonl"

    findings.extend(analyze_control_plane_snapshot(control_snapshot))
    checked_artifacts.append({"artifact_type": "control_plane_snapshot", "artifact_path": str(control_snapshot)})
    findings.extend(analyze_control_plane_jsonl(control_jsonl))
    checked_artifacts.append({"artifact_type": "control_plane_snapshot_jsonl", "artifact_path": str(control_jsonl)})
    findings.extend(analyze_sentient_ui_view_model(ui_snapshot))
    checked_artifacts.append({"artifact_type": "sentient_ui_view_model", "artifact_path": str(ui_snapshot)})
    findings.extend(analyze_sentient_ui_jsonl(ui_jsonl))
    checked_artifacts.append({"artifact_type": "sentient_ui_view_model_jsonl", "artifact_path": str(ui_jsonl)})
    findings.extend(analyze_schema_manifest(CONTROL_MANIFEST))
    checked_artifacts.append({"artifact_type": "schema_manifest", "artifact_path": str(CONTROL_MANIFEST)})
    findings.extend(analyze_schema_manifest(UI_MANIFEST))
    checked_artifacts.append({"artifact_type": "schema_manifest", "artifact_path": str(UI_MANIFEST)})

    return build_release_readiness_report(
        scope="sentient-control-plane",
        findings=findings,
        checked_artifacts=checked_artifacts,
    )


def write_release_readiness_report(
    path: str | Path = ".release_reports/release_readiness.json",
    *,
    base_dir: str | Path = ".",
) -> Dict[str, Any]:
    out_path = Path(path)
    _require_release_reports_path(out_path)
    report = build_full_release_readiness_report(base_dir=base_dir)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_name(f".{out_path.name}.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, out_path)
    return report


def append_release_readiness_report_jsonl(
    path: str | Path = ".release_reports/release_readiness.jsonl",
    *,
    base_dir: str | Path = ".",
) -> Dict[str, Any]:
    out_path = Path(path)
    _require_release_reports_path(out_path)
    report = build_full_release_readiness_report(base_dir=base_dir)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(report, sort_keys=True))
        f.write("\n")
    return report


def _require_release_reports_path(path: Path) -> None:
    normalized = str(path).replace("\\", "/")
    if "/.release_reports/" not in f"/{normalized}":
        raise ValueError("path must be under .release_reports/")


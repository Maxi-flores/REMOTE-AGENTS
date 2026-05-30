from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from release_center.artifact_readers import (
    read_gate_trace,
    read_latest_readiness_report,
    read_promotion_recommendations,
    read_scenario_comparison,
)
from release_center.milestones import build_release_milestones, summarize_release_milestones
from release_center.timeline_contracts import ReleaseTimelineReport, new_id, utc_now
from release_center.timeline_synthesizer import synthesize_release_timeline


def build_release_timeline_report(release_label: str = "local-release") -> Dict[str, Any]:
    readiness = read_latest_readiness_report()
    gate = read_gate_trace()
    scenario = read_scenario_comparison()
    promotions = read_promotion_recommendations()
    events = synthesize_release_timeline(
        readiness_report=readiness,
        gate_trace=gate,
        scenario_comparison=scenario,
        promotion_report=promotions,
    )
    milestones = build_release_milestones(events)
    milestone_summary = summarize_release_milestones(milestones)
    summary = {
        "event_count": len(events),
        "milestone_count": len(milestones),
        "blocked_milestones": milestone_summary.get("blocked_count", 0),
        "status_counts": milestone_summary.get("status_counts", {}),
    }
    report = ReleaseTimelineReport(
        report_id=new_id("release_timeline"),
        generated_utc=utc_now(),
        release_label=release_label,
        timeline_events=events,
        milestones=milestones,
        summary=summary,
        escalation_hints=milestone_summary.get("escalation_hints", []),
        advisory_only=True,
        metadata={"advisory_only": True},
    )
    return report.to_dict()


def write_release_timeline_report(
    report: Dict[str, Any],
    path: str | Path = ".release_reports/release_timeline.json",
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


def append_release_timeline_report_jsonl(
    report: Dict[str, Any],
    path: str | Path = ".release_reports/release_timeline.jsonl",
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


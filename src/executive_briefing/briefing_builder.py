from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from executive_briefing.analyzer import analyze_artifacts, load_json_file
from executive_briefing.contracts import ExecutiveBriefing, new_id, utc_now, validate_executive_briefing_dict


def build_executive_briefing(
    *,
    base_dir: str | Path = ".",
    orchestration_report_path: str | Path | None = None,
) -> Dict[str, Any]:
    root = Path(base_dir)
    orchestration_path = Path(orchestration_report_path) if orchestration_report_path else root / ".control_plane" / "orchestration" / "orchestration_report.json"
    cp_snapshot_path = root / ".control_plane" / "snapshot.json"
    readiness_path = root / ".release_reports" / "release_readiness.json"
    gate_trace_path = root / ".release_reports" / "gate_trace.json"
    timeline_path = root / ".release_reports" / "release_timeline.json"
    lifecycle_path = root / ".lifecycle" / "agents.json"
    sentient_path = root / ".sentient_ui" / "view_model.json"

    analyzed = analyze_artifacts(
        orchestration_report=load_json_file(orchestration_path),
        control_plane_snapshot=load_json_file(cp_snapshot_path),
        release_readiness_report=load_json_file(readiness_path),
        gate_trace=load_json_file(gate_trace_path),
        release_timeline=load_json_file(timeline_path),
        lifecycle_state=load_json_file(lifecycle_path),
        sentient_view_model=load_json_file(sentient_path),
    )

    overall_status = _overall_status(analyzed)
    briefing = ExecutiveBriefing(
        briefing_id=new_id("executive_briefing"),
        generated_utc=utc_now(),
        overall_status=overall_status,
        executive_summary=_summary_text(overall_status, analyzed),
        top_risks=list(analyzed.get("top_risks", [])),
        blocked_items=list(analyzed.get("blocked_items", [])),
        recommended_actions=list(analyzed.get("recommended_actions", [])),
        release_summary=dict(analyzed.get("release_summary", {})),
        lifecycle_summary=dict(analyzed.get("lifecycle_summary", {})),
        governance_summary=dict(analyzed.get("governance_summary", {})),
        metadata={
            "advisory_only": True,
            "source_artifacts": {
                "orchestration_report": str(orchestration_path),
                "control_plane_snapshot": str(cp_snapshot_path),
                "release_readiness_report": str(readiness_path),
                "gate_trace": str(gate_trace_path),
                "release_timeline": str(timeline_path),
                "lifecycle_state": str(lifecycle_path),
                "sentient_view_model": str(sentient_path),
            },
        },
    ).to_dict()
    validate_executive_briefing_dict(briefing)
    return briefing


def render_briefing_text(briefing: Dict[str, Any]) -> str:
    risks = briefing.get("top_risks", []) if isinstance(briefing.get("top_risks"), list) else []
    blocked = briefing.get("blocked_items", []) if isinstance(briefing.get("blocked_items"), list) else []
    actions = briefing.get("recommended_actions", []) if isinstance(briefing.get("recommended_actions"), list) else []
    lines = [
        f"System Status: {briefing.get('overall_status', 'unknown').capitalize()}",
        "",
        f"Executive Summary: {briefing.get('executive_summary', '')}",
        "",
        "Top Risks:",
    ]
    if risks:
        for item in risks[:5]:
            if isinstance(item, dict):
                lines.append(f"- [{item.get('severity', 'info')}] {item.get('title', 'Untitled risk')}")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("Blocked Items:")
    if blocked:
        for item in blocked[:5]:
            if isinstance(item, dict):
                lines.append(f"- {item.get('title', 'Blocked issue')}")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("Recommended Actions:")
    if actions:
        for action in actions[:8]:
            lines.append(f"- {action}")
    else:
        lines.append("- No actions recommended")
    return "\n".join(lines).strip() + "\n"


def _overall_status(analyzed: Dict[str, Any]) -> str:
    blocked = analyzed.get("blocked_items", [])
    risks = analyzed.get("top_risks", [])
    if isinstance(blocked, list) and blocked:
        return "blocked"
    if isinstance(risks, list) and any(isinstance(x, dict) and x.get("severity") in {"high", "critical"} for x in risks):
        return "degraded"
    if isinstance(risks, list) and risks:
        return "warning"
    return "healthy"


def _summary_text(overall_status: str, analyzed: Dict[str, Any]) -> str:
    risk_count = len(analyzed.get("top_risks", [])) if isinstance(analyzed.get("top_risks"), list) else 0
    blocked_count = len(analyzed.get("blocked_items", [])) if isinstance(analyzed.get("blocked_items"), list) else 0
    release = analyzed.get("release_summary", {}) if isinstance(analyzed.get("release_summary"), dict) else {}
    readiness = release.get("readiness_status", "unknown")
    score = release.get("readiness_score", 0)
    return (
        f"Advisory executive briefing status is {overall_status}. "
        f"Detected {risk_count} risk item(s), {blocked_count} blocked item(s), "
        f"release readiness is '{readiness}' (score={score})."
    )


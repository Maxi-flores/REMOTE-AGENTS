from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from executive_briefing.contracts import ExecutiveFinding, new_id


def load_json_file(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def analyze_artifacts(
    *,
    orchestration_report: Dict[str, Any] | None = None,
    control_plane_snapshot: Dict[str, Any] | None = None,
    release_readiness_report: Dict[str, Any] | None = None,
    gate_trace: Dict[str, Any] | None = None,
    release_timeline: Dict[str, Any] | None = None,
    lifecycle_state: Dict[str, Any] | None = None,
    sentient_view_model: Dict[str, Any] | None = None,
    repository_intelligence_report: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    if repository_intelligence_report is None:
        repository_intelligence_report = load_json_file(".control_plane/repository_intelligence/repository_intelligence_report.json")
    findings: List[Dict[str, Any]] = []
    findings.extend(_from_orchestration(orchestration_report or {}))
    findings.extend(_from_release_readiness(release_readiness_report or {}))
    findings.extend(_from_gate_trace(gate_trace or {}))
    findings.extend(_from_release_timeline(release_timeline or {}))
    findings.extend(_from_lifecycle_state(lifecycle_state or {}))
    findings.extend(_from_governance_snapshot(control_plane_snapshot or {}))
    findings.extend(_from_sentient_view_model(sentient_view_model or {}))
    findings.extend(_from_repository_intelligence(repository_intelligence_report or {}))

    blockers = [f for f in findings if f.get("severity") == "critical"]
    risks = [f for f in findings if f.get("severity") in {"high", "critical", "medium"}]
    actions = _dedupe([str(f.get("recommended_action")) for f in findings if isinstance(f, dict)])

    release_summary = _release_summary(release_readiness_report or {}, gate_trace or {}, release_timeline or {})
    lifecycle_summary = _lifecycle_summary(lifecycle_state or {})
    governance_summary = _governance_summary(control_plane_snapshot or {})

    return {
        "findings": findings,
        "blocked_items": blockers,
        "top_risks": risks[:10],
        "recommended_actions": actions[:12],
        "release_summary": release_summary,
        "lifecycle_summary": lifecycle_summary,
        "governance_summary": governance_summary,
    }


def _from_orchestration(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict):
        return []
    findings: List[Dict[str, Any]] = []
    for stage in report.get("stage_results", []) if isinstance(report.get("stage_results"), list) else []:
        if not isinstance(stage, dict):
            continue
        name = str(stage.get("stage_name") or "unknown")
        status = str(stage.get("status") or "unknown")
        if status == "ok":
            continue
        if status in {"blocked", "error"}:
            severity = "critical"
        elif status == "warning":
            severity = "high"
        else:
            severity = "medium"
        findings.append(
            ExecutiveFinding(
                finding_id=new_id("finding_stage"),
                severity=severity,
                category=_map_stage_category(name),
                title=f"CPOL stage '{name}' is {status}",
                description=f"Stage '{name}' reported status '{status}'.",
                recommended_action=f"Review advisory inputs and stage health for '{name}'.",
            ).to_dict()
        )
    return findings


def _from_release_readiness(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    findings: List[Dict[str, Any]] = []
    status = str(report.get("readiness_status") or "unknown")
    score = report.get("readiness_score", 0)
    if status in {"blocked", "unknown"}:
        findings.append(
            ExecutiveFinding(
                finding_id=new_id("finding_release"),
                severity="critical" if status == "blocked" else "high",
                category="release",
                title=f"Release readiness is {status}",
                description=f"Release readiness status '{status}' with score {score}.",
                recommended_action="Run release-readiness analysis and resolve blocking findings.",
            ).to_dict()
        )
    elif isinstance(score, (int, float)) and score < 80:
        findings.append(
            ExecutiveFinding(
                finding_id=new_id("finding_release"),
                severity="high",
                category="release",
                title="Release readiness score below target",
                description=f"Readiness score is {score}, below advisory target 80.",
                recommended_action="Address readiness findings and rerun readiness report.",
            ).to_dict()
        )
    return findings


def _from_gate_trace(trace: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(trace, dict) or not trace:
        return []
    decision = trace.get("decision")
    if not isinstance(decision, dict):
        return []
    verdict = str(decision.get("decision") or "unknown")
    if verdict in {"pass", "pass_with_warnings"}:
        return []
    sev = "critical" if verdict == "blocked" else "medium"
    return [
        ExecutiveFinding(
            finding_id=new_id("finding_gate"),
            severity=sev,
            category="release",
            title=f"Release gate decision is {verdict}",
            description=f"Advisory gate decision returned '{verdict}'.",
            recommended_action="Review gate blockers and policy thresholds.",
        ).to_dict()
    ]


def _from_release_timeline(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    findings: List[Dict[str, Any]] = []
    hints = report.get("escalation_hints", [])
    if isinstance(hints, list):
        for hint in hints[:3]:
            if isinstance(hint, str) and hint.strip():
                findings.append(
                    ExecutiveFinding(
                        finding_id=new_id("finding_timeline"),
                        severity="high",
                        category="release",
                        title="Release center escalation hint",
                        description=hint.strip(),
                        recommended_action="Review release timeline milestones and clear escalation conditions.",
                    ).to_dict()
                )
    return findings


def _from_lifecycle_state(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(state, dict) or not state:
        return []
    findings: List[Dict[str, Any]] = []
    profiles = state.get("capability_profiles")
    lifecycles = state.get("lifecycle_states")
    profile_count = len(profiles) if isinstance(profiles, dict) else 0
    lifecycle_count = len(lifecycles) if isinstance(lifecycles, dict) else 0
    if profile_count == 0:
        findings.append(
            ExecutiveFinding(
                finding_id=new_id("finding_lifecycle"),
                severity="high",
                category="lifecycle",
                title="No capability profiles present",
                description="Lifecycle capability registry has zero capability profiles.",
                recommended_action="Create lifecycle capability profiles for active agent classes.",
            ).to_dict()
        )
    if lifecycle_count == 0:
        findings.append(
            ExecutiveFinding(
                finding_id=new_id("finding_lifecycle"),
                severity="medium",
                category="lifecycle",
                title="No registered lifecycle states",
                description="No lifecycle agent state records were found.",
                recommended_action="Register advisory lifecycle state entries for active agents.",
            ).to_dict()
        )
    return findings


def _from_governance_snapshot(snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(snapshot, dict) or not snapshot:
        return []
    repo = snapshot.get("repositories")
    metrics = repo.get("metrics") if isinstance(repo, dict) and isinstance(repo.get("metrics"), dict) else {}
    warnings = int(metrics.get("governance_warnings", 0) or 0) if isinstance(metrics, dict) else 0
    errors = int(metrics.get("governance_errors", 0) or 0) if isinstance(metrics, dict) else 0
    findings: List[Dict[str, Any]] = []
    if errors > 0:
        findings.append(
            ExecutiveFinding(
                finding_id=new_id("finding_gov"),
                severity="critical",
                category="governance",
                title="Governance errors detected",
                description=f"Control-plane repository section reports {errors} governance errors.",
                recommended_action="Review governance audit records and clear error conditions.",
            ).to_dict()
        )
    elif warnings > 0:
        findings.append(
            ExecutiveFinding(
                finding_id=new_id("finding_gov"),
                severity="medium",
                category="governance",
                title="Governance warnings detected",
                description=f"Control-plane repository section reports {warnings} governance warnings.",
                recommended_action="Review governance warnings and plan remediations.",
            ).to_dict()
        )
    return findings


def _from_sentient_view_model(view_model: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(view_model, dict) or not view_model:
        return []
    alerts = view_model.get("alerts")
    if not isinstance(alerts, list):
        return []
    if len(alerts) == 0:
        return []
    return [
        ExecutiveFinding(
            finding_id=new_id("finding_ui"),
            severity="low",
            category="system",
            title="Sentient UI alerts present",
            description=f"Sentient UI view model includes {len(alerts)} alert entries.",
            recommended_action="Review dashboard alerts and verify advisory status alignment.",
        ).to_dict()
    ]


def _from_repository_intelligence(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    findings = report.get("findings")
    if not isinstance(findings, list):
        return []
    out: List[Dict[str, Any]] = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        severity = str(finding.get("severity") or "info").lower()
        if severity not in {"high", "critical"}:
            continue
        out.append(
            ExecutiveFinding(
                finding_id=new_id("finding_repo_intel"),
                severity="high" if severity == "high" else "critical",
                category="repository",
                title=str(finding.get("title") or "Repository intelligence risk"),
                description=str(finding.get("description") or "High-severity repository intelligence finding."),
                recommended_action=str(
                    finding.get("recommended_action")
                    or "Review repository intelligence findings and schedule remediation missions."
                ),
            ).to_dict()
        )
    return out


def _release_summary(readiness: Dict[str, Any], gate_trace: Dict[str, Any], timeline: Dict[str, Any]) -> Dict[str, Any]:
    decision = {}
    if isinstance(gate_trace.get("decision"), dict):
        decision = dict(gate_trace["decision"])
    return {
        "readiness_status": readiness.get("readiness_status", "unknown"),
        "readiness_score": readiness.get("readiness_score", 0),
        "gate_decision": decision.get("decision", "unknown"),
        "timeline_milestones": len(timeline.get("milestones", [])) if isinstance(timeline.get("milestones"), list) else 0,
    }


def _lifecycle_summary(state: Dict[str, Any]) -> Dict[str, Any]:
    profiles = state.get("capability_profiles")
    lifecycle = state.get("lifecycle_states")
    return {
        "capability_profiles": len(profiles) if isinstance(profiles, dict) else 0,
        "lifecycle_states": len(lifecycle) if isinstance(lifecycle, dict) else 0,
    }


def _governance_summary(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    repo = snapshot.get("repositories") if isinstance(snapshot.get("repositories"), dict) else {}
    metrics = repo.get("metrics") if isinstance(repo.get("metrics"), dict) else {}
    return {
        "repository_count": metrics.get("canonical_repositories", 0),
        "governance_profiles": metrics.get("governance_profiles", 0),
        "health_snapshots": metrics.get("health_snapshots", 0),
        "audit_records": metrics.get("audit_records", 0),
    }


def _dedupe(items: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _map_stage_category(stage_name: str) -> str:
    mapping = {
        "mission": "mission",
        "scheduler": "scheduler",
        "tool_router": "tooling",
        "governance": "governance",
        "memory_graph": "memory",
        "release_readiness": "release",
        "release_gates": "release",
        "release_center": "release",
        "lifecycle": "lifecycle",
        "snapshot": "system",
        "sentient_ui": "system",
    }
    return mapping.get(stage_name, "system")


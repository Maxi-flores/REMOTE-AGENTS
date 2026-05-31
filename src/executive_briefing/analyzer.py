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
    remediation_plan_report: Dict[str, Any] | None = None,
    remediation_handoff_report: Dict[str, Any] | None = None,
    handoff_refinement_report: Dict[str, Any] | None = None,
    work_queue_report: Dict[str, Any] | None = None,
    execution_dossier_report: Dict[str, Any] | None = None,
    portfolio_report: Dict[str, Any] | None = None,
    portfolio_bootstrap_report: Dict[str, Any] | None = None,
    portfolio_onboarding_recommendation_report: Dict[str, Any] | None = None,
    portfolio_dependency_report: Dict[str, Any] | None = None,
    portfolio_critical_path_report: Dict[str, Any] | None = None,
    portfolio_roadmap_report: Dict[str, Any] | None = None,
    portfolio_progress_report: Dict[str, Any] | None = None,
    portfolio_drift_report: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    if repository_intelligence_report is None:
        repository_intelligence_report = load_json_file(".control_plane/repository_intelligence/repository_intelligence_report.json")
    if remediation_plan_report is None:
        remediation_plan_report = load_json_file(".control_plane/remediation_plans/remediation_plan_report.json")
    if remediation_handoff_report is None:
        remediation_handoff_report = load_json_file(".control_plane/remediation_handoffs/latest.json")
    if handoff_refinement_report is None:
        handoff_refinement_report = load_json_file(".control_plane/handoff_refinements/latest.json")
    if work_queue_report is None:
        work_queue_report = load_json_file(".control_plane/work_queue/latest.json")
    if execution_dossier_report is None:
        execution_dossier_report = load_json_file(".control_plane/execution_dossiers/latest.json")
    if portfolio_report is None:
        portfolio_report = load_json_file(".control_plane/portfolio/latest.json")
    if portfolio_bootstrap_report is None:
        portfolio_bootstrap_report = load_json_file(".control_plane/portfolio_bootstrap/latest.json")
    if portfolio_onboarding_recommendation_report is None:
        portfolio_onboarding_recommendation_report = load_json_file(".control_plane/portfolio_onboarding_recommendations/latest.json")
    if portfolio_dependency_report is None:
        portfolio_dependency_report = load_json_file(".control_plane/portfolio_dependencies/latest.json")
    if portfolio_critical_path_report is None:
        portfolio_critical_path_report = load_json_file(".control_plane/portfolio_critical_path/latest.json")
    if portfolio_roadmap_report is None:
        portfolio_roadmap_report = load_json_file(".control_plane/portfolio_roadmap/latest.json")
    if portfolio_progress_report is None:
        portfolio_progress_report = load_json_file(".control_plane/portfolio_progress/latest.json")
    if portfolio_drift_report is None:
        portfolio_drift_report = load_json_file(".control_plane/portfolio_drift/latest.json")
    findings: List[Dict[str, Any]] = []
    findings.extend(_from_orchestration(orchestration_report or {}))
    findings.extend(_from_release_readiness(release_readiness_report or {}))
    findings.extend(_from_gate_trace(gate_trace or {}))
    findings.extend(_from_release_timeline(release_timeline or {}))
    findings.extend(_from_lifecycle_state(lifecycle_state or {}))
    findings.extend(_from_governance_snapshot(control_plane_snapshot or {}))
    findings.extend(_from_sentient_view_model(sentient_view_model or {}))
    findings.extend(_from_repository_intelligence(repository_intelligence_report or {}))
    findings.extend(_from_remediation_plan(remediation_plan_report or {}))
    findings.extend(_from_remediation_handoffs(remediation_handoff_report or {}, remediation_plan_report or {}))
    findings.extend(_from_handoff_refinements(handoff_refinement_report or {}))
    findings.extend(_from_work_queue(work_queue_report or {}))
    findings.extend(_from_execution_dossiers(execution_dossier_report or {}))
    findings.extend(_from_portfolio_report(portfolio_report or {}))
    findings.extend(_from_portfolio_bootstrap(portfolio_bootstrap_report or {}))
    findings.extend(_from_portfolio_onboarding_recommendations(portfolio_onboarding_recommendation_report or {}))
    findings.extend(_from_portfolio_dependencies(portfolio_dependency_report or {}))
    findings.extend(_from_portfolio_critical_path(portfolio_critical_path_report or {}))
    findings.extend(_from_portfolio_roadmap(portfolio_roadmap_report or {}))
    findings.extend(_from_portfolio_progress(portfolio_progress_report or {}))
    findings.extend(_from_portfolio_drift(portfolio_drift_report or {}))

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


def _from_remediation_plan(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    items = report.get("items")
    if not isinstance(items, list):
        return []
    high_or_critical = [
        item for item in items if isinstance(item, dict) and str(item.get("priority") or "P4") in {"P0", "P1"}
    ]
    if not high_or_critical:
        return []
    return [
        ExecutiveFinding(
            finding_id=new_id("finding_remediation"),
            severity="high",
            category="repository",
            title="High-priority remediation backlog present",
            description=f"Remediation planner reports {len(high_or_critical)} P0/P1 item(s).",
            recommended_action="Prioritize high-risk remediation batches and convert them into tracked strategic missions.",
        ).to_dict()
    ]


def _from_remediation_handoffs(
    handoff_report: Dict[str, Any],
    remediation_plan_report: Dict[str, Any],
) -> List[Dict[str, Any]]:
    if not isinstance(handoff_report, dict) or not handoff_report:
        return []
    packages = handoff_report.get("packages")
    if not isinstance(packages, list):
        return []
    planned_batches = remediation_plan_report.get("batches", []) if isinstance(remediation_plan_report, dict) else []
    package_count = len([pkg for pkg in packages if isinstance(pkg, dict)])
    findings: List[Dict[str, Any]] = [
        ExecutiveFinding(
            finding_id=new_id("finding_handoff"),
            severity="low",
            category="repository",
            title="Remediation handoff packages generated",
            description=f"{package_count} implementation package(s) are available for human review.",
            recommended_action="Select reviewed packages for manual execution planning.",
        ).to_dict()
    ]
    if isinstance(planned_batches, list) and package_count < len(planned_batches):
        findings.append(
            ExecutiveFinding(
                finding_id=new_id("finding_handoff"),
                severity="medium",
                category="repository",
                title="Remediation handoff coverage incomplete",
                description=f"Generated packages ({package_count}) are fewer than remediation batches ({len(planned_batches)}).",
                recommended_action="Generate additional handoff packages for remaining remediation batches.",
            ).to_dict()
        )
    return findings


def _from_handoff_refinements(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    summary = report.get("split_summary")
    packages = report.get("refined_packages")
    if not isinstance(summary, dict) or not isinstance(packages, list):
        return []
    findings: List[Dict[str, Any]] = []
    delta = int(summary.get("split_delta", 0) or 0)
    high_risk = int(summary.get("high_risk_refined_count", 0) or 0)
    if delta > 0:
        findings.append(
            ExecutiveFinding(
                finding_id=new_id("finding_refinement"),
                severity="low",
                category="repository",
                title="Broad handoff packages were refined",
                description=f"Refinement increased package count by {delta}, indicating safer scope partitioning.",
                recommended_action="Prioritize refined packages for manual execution planning.",
            ).to_dict()
        )
    if high_risk > 0:
        findings.append(
            ExecutiveFinding(
                finding_id=new_id("finding_refinement"),
                severity="medium",
                category="repository",
                title="High-risk refined handoff packages remain",
                description=f"{high_risk} refined package(s) still carry high/critical risk levels.",
                recommended_action="Split remaining high-risk refined packages further before execution.",
            ).to_dict()
        )
    return findings


def _from_work_queue(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    items = report.get("queue_items")
    if not isinstance(items, list):
        return []
    ready = 0
    blocked = 0
    deferred = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        state = str(item.get("execution_readiness") or "waiting")
        if state == "ready":
            ready += 1
        elif state == "blocked":
            blocked += 1
        elif state == "deferred":
            deferred += 1
    findings: List[Dict[str, Any]] = []
    if blocked > 0:
        findings.append(
            ExecutiveFinding(
                finding_id=new_id("finding_work_queue"),
                severity="high",
                category="repository",
                title="Blocked work queue items detected",
                description=f"{blocked} work queue item(s) are blocked by dependency or readiness constraints.",
                recommended_action="Resolve blockers and promote blocked queue items to waiting/ready state.",
            ).to_dict()
        )
    if ready > 0:
        findings.append(
            ExecutiveFinding(
                finding_id=new_id("finding_work_queue"),
                severity="low",
                category="repository",
                title="Ready work queue items available",
                description=f"{ready} work queue item(s) are ready for manual execution planning.",
                recommended_action="Prioritize ready queue items in strategic mission planning.",
            ).to_dict()
        )
    if deferred > 0:
        findings.append(
            ExecutiveFinding(
                finding_id=new_id("finding_work_queue"),
                severity="medium",
                category="repository",
                title="Deferred work queue items present",
                description=f"{deferred} work queue item(s) are deferred due to low readiness scores.",
                recommended_action="Re-evaluate deferred items after prerequisite work is complete.",
            ).to_dict()
        )
    return findings


def _from_execution_dossiers(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    dossiers = report.get("dossiers")
    if not isinstance(dossiers, list):
        return []
    ready = 0
    high_risk = 0
    dist = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for dossier in dossiers:
        if not isinstance(dossier, dict):
            continue
        if int(dossier.get("execution_readiness_score") or 0) >= 85:
            ready += 1
        risk = str(dossier.get("execution_risk") or "medium").lower()
        if risk in dist:
            dist[risk] += 1
        if risk in {"high", "critical"}:
            high_risk += 1
    findings: List[Dict[str, Any]] = []
    if ready > 0:
        findings.append(
            ExecutiveFinding(
                finding_id=new_id("finding_dossier"),
                severity="low",
                category="repository",
                title="Execution-ready dossiers available",
                description=f"{ready} dossier(s) are immediately ready for human approval and manual execution.",
                recommended_action="Prioritize execution-ready dossiers in next delivery cycle.",
            ).to_dict()
        )
    if high_risk > 0:
        findings.append(
            ExecutiveFinding(
                finding_id=new_id("finding_dossier"),
                severity="medium",
                category="repository",
                title="High-risk execution dossiers present",
                description=f"{high_risk} dossier(s) are classified as high/critical execution risk.",
                recommended_action="Review high-risk dossiers with extra scrutiny before approval.",
            ).to_dict()
        )
    return findings


def _from_portfolio_report(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    findings: List[Dict[str, Any]] = []
    health = int(report.get("portfolio_health_score") or 0)
    readiness = int(report.get("portfolio_readiness_score") or 0)
    repo_statuses = report.get("repository_statuses")
    repo_count = len(repo_statuses) if isinstance(repo_statuses, list) else 0
    if repo_count > 0:
        sev = "medium" if health < 70 or readiness < 70 else "low"
        findings.append(
            ExecutiveFinding(
                finding_id=new_id("finding_portfolio"),
                severity=sev,
                category="system",
                title="Portfolio orchestration summary available",
                description=f"Portfolio report covers {repo_count} repositories with health {health} and readiness {readiness}.",
                recommended_action="Use portfolio recommended execution order to prioritize cross-repository advisory work.",
            ).to_dict()
        )
    portfolio_findings = report.get("findings")
    if isinstance(portfolio_findings, list) and portfolio_findings:
        critical = 0
        for finding in portfolio_findings:
            if isinstance(finding, dict) and str(finding.get("severity") or "").lower() in {"high", "critical"}:
                critical += 1
        if critical > 0:
            findings.append(
                ExecutiveFinding(
                    finding_id=new_id("finding_portfolio"),
                    severity="medium",
                    category="repository",
                    title="Portfolio high-severity findings detected",
                    description=f"Portfolio report includes {critical} high/critical cross-repository finding(s).",
                    recommended_action="Address top cross-repository risks in strategic mission planning.",
                ).to_dict()
            )
    return findings


def _from_portfolio_bootstrap(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    summary = report.get("readiness_summary")
    if not isinstance(summary, dict):
        return []
    avg = int(summary.get("average_readiness_estimate") or 0)
    repo_count = int(summary.get("repository_count") or 0)
    if repo_count <= 0:
        return []
    severity = "low" if avg >= 70 else ("medium" if avg >= 45 else "high")
    return [
        ExecutiveFinding(
            finding_id=new_id("finding_portfolio_bootstrap"),
            severity=severity,
            category="repository",
            title="Portfolio onboarding readiness summary available",
            description=f"Portfolio bootstrap assessed {repo_count} repositories with average onboarding readiness {avg}.",
            recommended_action="Use onboarding recommendations to raise repository advisory readiness and artifact coverage.",
        ).to_dict()
    ]


def _from_portfolio_onboarding_recommendations(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    recommendations = report.get("recommendations")
    if not isinstance(recommendations, list):
        return []
    high = 0
    for item in recommendations:
        if not isinstance(item, dict):
            continue
        if str(item.get("priority") or "P4") in {"P0", "P1"}:
            high += 1
    if high <= 0:
        return []
    return [
        ExecutiveFinding(
            finding_id=new_id("finding_portfolio_onboarding"),
            severity="medium",
            category="repository",
            title="High-priority portfolio onboarding recommendations present",
            description=f"{high} onboarding recommendation(s) are marked P0/P1.",
            recommended_action="Address repository path/discovery and advisory baseline onboarding recommendations first.",
        ).to_dict()
    ]


def _from_portfolio_dependencies(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    findings = report.get("findings")
    if not isinstance(findings, list):
        return []
    high = 0
    for item in findings:
        if not isinstance(item, dict):
            continue
        if str(item.get("severity") or "").lower() in {"high", "critical"}:
            high += 1
    if high <= 0:
        return []
    return [
        ExecutiveFinding(
            finding_id=new_id("finding_portfolio_dependency"),
            severity="high",
            category="repository",
            title="High-severity dependency findings detected",
            description=f"Portfolio dependency intelligence reported {high} high/critical finding(s).",
            recommended_action="Resolve upstream dependency blockers and unknown dependencies before dependent execution planning.",
        ).to_dict()
    ]


def _from_portfolio_critical_path(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    recs = report.get("recommendations")
    if not isinstance(recs, list) or not recs:
        return []
    p0p1 = 0
    for rec in recs:
        if isinstance(rec, dict) and str(rec.get("priority") or "").upper() in {"P0", "P1"}:
            p0p1 += 1
    if p0p1 <= 0:
        return []
    return [
        ExecutiveFinding(
            finding_id=new_id("finding_portfolio_critical_path"),
            severity="high",
            category="repository",
            title="High-leverage critical path actions identified",
            description=f"{p0p1} critical-path recommendation(s) are marked P0/P1.",
            recommended_action="Sequence immediate remediation on top critical repositories to maximize portfolio improvement.",
        ).to_dict()
    ]


def _from_portfolio_roadmap(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    items = report.get("roadmap_items")
    waves = report.get("waves")
    if not isinstance(items, list) or not isinstance(waves, list):
        return []
    near_term = [
        item for item in items if isinstance(item, dict) and str(item.get("horizon") or "").lower() == "near_term"
    ]
    if not near_term:
        return []
    return [
        ExecutiveFinding(
            finding_id=new_id("finding_portfolio_roadmap"),
            severity="medium",
            category="repository",
            title="Near-term strategic roadmap wave is populated",
            description=f"Portfolio roadmap includes {len(near_term)} near-term item(s) across {len(waves)} wave(s).",
            recommended_action="Use near-term roadmap wave to align next advisory mission planning cycle.",
        ).to_dict()
    ]


def _from_portfolio_progress(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    trends = report.get("portfolio_trends")
    findings = report.get("findings")
    if not isinstance(trends, dict):
        return []
    overall = str(trends.get("overall_trend") or "unknown")
    out: List[Dict[str, Any]] = []
    if overall == "declining":
        out.append(
            ExecutiveFinding(
                finding_id=new_id("finding_portfolio_progress"),
                severity="high",
                category="repository",
                title="Portfolio progress trend is declining",
                description="Portfolio progress intelligence indicates declining aggregate trend.",
                recommended_action="Prioritize declining trend remediation before expanding roadmap scope.",
            ).to_dict()
        )
    if isinstance(findings, list):
        declining_count = 0
        for finding in findings:
            if isinstance(finding, dict) and str(finding.get("trend") or "") == "declining":
                declining_count += 1
        if declining_count > 0:
            out.append(
                ExecutiveFinding(
                    finding_id=new_id("finding_portfolio_progress"),
                    severity="medium",
                    category="repository",
                    title="Declining progress findings detected",
                    description=f"Portfolio progress report contains {declining_count} declining trend finding(s).",
                    recommended_action="Review declining progress findings and create targeted follow-up missions.",
                ).to_dict()
            )
    return out


def _from_portfolio_drift(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    findings = report.get("findings")
    if not isinstance(findings, list):
        return []
    high = 0
    critical = 0
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        sev = str(finding.get("severity") or "").lower()
        if sev == "high":
            high += 1
        elif sev == "critical":
            critical += 1
    if high + critical == 0:
        return []
    severity = "critical" if critical > 0 else "high"
    return [
        ExecutiveFinding(
            finding_id=new_id("finding_portfolio_drift"),
            severity=severity,
            category="repository",
            title="High-severity portfolio drift findings detected",
            description=f"Portfolio drift report contains {high} high and {critical} critical finding(s).",
            recommended_action="Reconcile drift findings before trusting downstream portfolio planning outputs.",
        ).to_dict()
    ]


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


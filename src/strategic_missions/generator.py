from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from strategic_missions.contracts import StrategicMissionCandidate, StrategicMissionReport, new_id, utc_now, validate_strategic_mission_report_dict
from strategic_missions.scoring import derive_priority, rank_candidate, score_finding


def load_executive_briefing(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def generate_strategic_mission_report(
    *,
    briefing: Dict[str, Any] | None = None,
    briefing_path: str | Path | None = None,
    base_dir: str | Path = ".",
    limit: int | None = None,
    governance_recovery_dossier_report: Dict[str, Any] | None = None,
    governance_approval_readiness_report: Dict[str, Any] | None = None,
    governance_approval_packet_report: Dict[str, Any] | None = None,
    governance_decision_report: Dict[str, Any] | None = None,
    manual_execution_queue_report: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    root = Path(base_dir)
    repo_intel = load_executive_briefing(root / ".control_plane" / "repository_intelligence" / "repository_intelligence_report.json")
    remediation_plan = load_executive_briefing(root / ".control_plane" / "remediation_plans" / "remediation_plan_report.json")
    remediation_handoff = load_executive_briefing(root / ".control_plane" / "remediation_handoffs" / "latest.json")
    handoff_refinement = load_executive_briefing(root / ".control_plane" / "handoff_refinements" / "latest.json")
    work_queue = load_executive_briefing(root / ".control_plane" / "work_queue" / "latest.json")
    execution_dossiers = load_executive_briefing(root / ".control_plane" / "execution_dossiers" / "latest.json")
    portfolio_report = load_executive_briefing(root / ".control_plane" / "portfolio" / "latest.json")
    portfolio_bootstrap = load_executive_briefing(root / ".control_plane" / "portfolio_bootstrap" / "latest.json")
    portfolio_onboarding_recommendations = load_executive_briefing(root / ".control_plane" / "portfolio_onboarding_recommendations" / "latest.json")
    portfolio_dependencies = load_executive_briefing(root / ".control_plane" / "portfolio_dependencies" / "latest.json")
    portfolio_critical_path = load_executive_briefing(root / ".control_plane" / "portfolio_critical_path" / "latest.json")
    portfolio_roadmap = load_executive_briefing(root / ".control_plane" / "portfolio_roadmap" / "latest.json")
    portfolio_progress = load_executive_briefing(root / ".control_plane" / "portfolio_progress" / "latest.json")
    portfolio_drift = load_executive_briefing(root / ".control_plane" / "portfolio_drift" / "latest.json")
    portfolio_governance_index = load_executive_briefing(root / ".control_plane" / "portfolio_governance_index" / "latest.json")
    governance_recovery = load_executive_briefing(root / ".control_plane" / "governance_recovery" / "latest.json")
    governance_approval_packets = load_executive_briefing(root / ".control_plane" / "governance_approval_packets" / "latest.json")
    governance_decisions = load_executive_briefing(root / ".control_plane" / "governance_decisions" / "latest.json")
    manual_execution_queue = load_executive_briefing(root / ".control_plane" / "manual_execution_queue" / "latest.json")
    if governance_approval_readiness_report is None:
        governance_approval_readiness = load_executive_briefing(root / ".control_plane" / "governance_approval_readiness" / "latest.json")
    else:
        governance_approval_readiness = governance_approval_readiness_report
    if governance_recovery_dossier_report is None:
        governance_recovery_dossiers = load_executive_briefing(root / ".control_plane" / "governance_recovery_dossiers" / "latest.json")
    else:
        governance_recovery_dossiers = governance_recovery_dossier_report
    if governance_approval_packet_report is None:
        governance_approval_packets_local = governance_approval_packets
    else:
        governance_approval_packets_local = governance_approval_packet_report
    if governance_decision_report is None:
        governance_decisions_local = governance_decisions
    else:
        governance_decisions_local = governance_decision_report
    if manual_execution_queue_report is None:
        manual_execution_queue_local = manual_execution_queue
    else:
        manual_execution_queue_local = manual_execution_queue_report
    if briefing is None:
        source_path = Path(briefing_path) if briefing_path else (root / ".control_plane" / "executive" / "executive_briefing.json")
        briefing = load_executive_briefing(source_path)
    else:
        source_path = Path(briefing_path) if briefing_path else None

    candidates = _candidates_from_briefing(
        briefing or {},
        repository_intelligence_report=repo_intel,
        remediation_plan_report=remediation_plan,
        remediation_handoff_report=remediation_handoff,
        handoff_refinement_report=handoff_refinement,
        work_queue_report=work_queue,
        execution_dossier_report=execution_dossiers,
        portfolio_report=portfolio_report,
        portfolio_bootstrap_report=portfolio_bootstrap,
        portfolio_onboarding_recommendation_report=portfolio_onboarding_recommendations,
        portfolio_dependency_report=portfolio_dependencies,
        portfolio_critical_path_report=portfolio_critical_path,
        portfolio_roadmap_report=portfolio_roadmap,
        portfolio_progress_report=portfolio_progress,
        portfolio_drift_report=portfolio_drift,
        portfolio_governance_index_report=portfolio_governance_index,
        governance_recovery_report=governance_recovery,
        governance_recovery_dossier_report=governance_recovery_dossiers,
        governance_approval_readiness_report=governance_approval_readiness,
        governance_approval_packet_report=governance_approval_packets_local,
        governance_decision_report=governance_decisions_local,
        manual_execution_queue_report=manual_execution_queue_local,
    )
    if limit is not None and isinstance(limit, int) and limit > 0:
        candidates = candidates[:limit]

    sequence = [c["candidate_id"] for c in candidates]
    summary = {
        "candidate_count": len(candidates),
        "priorities": _priority_counts(candidates),
        "categories": _category_counts(candidates),
        "source_overall_status": str((briefing or {}).get("overall_status") or "unknown"),
    }
    report = StrategicMissionReport(
        report_id=new_id("strategic_mission_report"),
        generated_utc=utc_now(),
        overall_status=_overall_status(candidates),
        candidates=candidates,
        recommended_sequence=sequence,
        summary=summary,
        advisory_only=True,
        metadata={
            "advisory_only": True,
            "source_briefing_path": str(source_path) if source_path else None,
            "base_dir": str(root),
            "auto_enqueue": False,
            "queue_mutation": False,
        },
    ).to_dict()
    validate_strategic_mission_report_dict(report)
    return report


def render_strategic_mission_report_text(report: Dict[str, Any]) -> str:
    lines = ["Strategic Mission Recommendations", ""]
    candidates = report.get("candidates", []) if isinstance(report.get("candidates"), list) else []
    if not candidates:
        lines.append("No recommendations available.")
    else:
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            lines.append(f"{candidate.get('priority', 'P4')}: {candidate.get('title', 'Untitled')}")
    return "\n".join(lines).strip() + "\n"


def _candidates_from_briefing(
    briefing: Dict[str, Any],
    *,
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
    portfolio_governance_index_report: Dict[str, Any] | None = None,
    governance_recovery_report: Dict[str, Any] | None = None,
    governance_recovery_dossier_report: Dict[str, Any] | None = None,
    governance_approval_readiness_report: Dict[str, Any] | None = None,
    governance_approval_packet_report: Dict[str, Any] | None = None,
    governance_decision_report: Dict[str, Any] | None = None,
    manual_execution_queue_report: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    if not isinstance(briefing, dict):
        return _maintenance_candidates()
    findings = briefing.get("top_risks")
    actions = briefing.get("recommended_actions")
    repo_candidates = _candidates_from_repo_intel(repository_intelligence_report or {})
    remediation_candidates = _candidates_from_remediation(remediation_plan_report or {})
    dossier_candidates = _candidates_from_execution_dossiers(execution_dossier_report or {})
    queue_candidates = _candidates_from_work_queue(work_queue_report or {})
    portfolio_candidates = _candidates_from_portfolio(portfolio_report or {})
    bootstrap_candidates = _candidates_from_portfolio_bootstrap(portfolio_bootstrap_report or {})
    onboarding_recommendation_candidates = _candidates_from_portfolio_onboarding_recommendations(portfolio_onboarding_recommendation_report or {})
    dependency_candidates = _candidates_from_portfolio_dependencies(portfolio_dependency_report or {})
    critical_path_candidates = _candidates_from_portfolio_critical_path(portfolio_critical_path_report or {})
    roadmap_candidates = _candidates_from_portfolio_roadmap(portfolio_roadmap_report or {})
    progress_candidates = _candidates_from_portfolio_progress(portfolio_progress_report or {})
    drift_candidates = _candidates_from_portfolio_drift(portfolio_drift_report or {})
    governance_index_candidates = _candidates_from_portfolio_governance_index(portfolio_governance_index_report or {})
    governance_recovery_candidates = _candidates_from_governance_recovery(governance_recovery_report or {})
    governance_recovery_dossier_candidates = _candidates_from_governance_recovery_dossiers(governance_recovery_dossier_report or {})
    governance_approval_candidates = _candidates_from_governance_approval_readiness(governance_approval_readiness_report or {})
    governance_approval_packet_candidates = _candidates_from_governance_approval_packets(governance_approval_packet_report or {})
    governance_decision_candidates = _candidates_from_governance_decisions(governance_decision_report or {})
    manual_execution_queue_candidates = _candidates_from_manual_execution_queue(manual_execution_queue_report or {})
    refinement_candidates = _candidates_from_refinements(handoff_refinement_report or {})
    handoff_candidates = refinement_candidates if refinement_candidates else _candidates_from_handoffs(remediation_handoff_report or {})
    if isinstance(findings, list) and findings:
        base = [_candidate_from_finding(f, actions) for f in findings if isinstance(f, dict)]
        return _rank_candidates(base + dossier_candidates + queue_candidates + repo_candidates + remediation_candidates + handoff_candidates + portfolio_candidates + bootstrap_candidates + onboarding_recommendation_candidates + dependency_candidates + critical_path_candidates + roadmap_candidates + progress_candidates + drift_candidates + governance_index_candidates + governance_recovery_candidates + governance_recovery_dossier_candidates + governance_approval_candidates + governance_approval_packet_candidates + governance_decision_candidates + manual_execution_queue_candidates)
    # healthy/no-risks => maintenance continuity recommendations
    return _rank_candidates(_maintenance_candidates() + dossier_candidates + queue_candidates + repo_candidates + remediation_candidates + handoff_candidates + portfolio_candidates + bootstrap_candidates + onboarding_recommendation_candidates + dependency_candidates + critical_path_candidates + roadmap_candidates + progress_candidates + drift_candidates + governance_index_candidates + governance_recovery_candidates + governance_recovery_dossier_candidates + governance_approval_candidates + governance_approval_packet_candidates + governance_decision_candidates + manual_execution_queue_candidates)


def _candidate_from_finding(finding: Dict[str, Any], actions: Any) -> Dict[str, Any]:
    finding_id = str(finding.get("finding_id") or new_id("finding_ref"))
    title = str(finding.get("title") or "Resolve advisory finding")
    category = _safe_category(str(finding.get("category") or "system"))
    scores = score_finding(finding)
    priority = derive_priority(**scores)
    repo = _repo_hint_from_text(f"{finding.get('title', '')} {finding.get('description', '')}")
    suggested_instruction = _suggested_instruction(title=title, category=category, actions=actions)
    candidate = StrategicMissionCandidate(
        candidate_id=new_id("strategic_mission"),
        title=title,
        description=str(finding.get("description") or title),
        source_finding_ids=[finding_id],
        category=category,
        priority=priority,
        risk_reduction_score=scores["risk_reduction_score"],
        effort_score=scores["effort_score"],
        confidence_score=scores["confidence_score"],
        recommended_repository=repo,
        suggested_instruction=suggested_instruction,
        advisory_only=True,
        metadata={"source": "executive_briefing", "severity": finding.get("severity", "info")},
    ).to_dict()
    return candidate


def _maintenance_candidates() -> List[Dict[str, Any]]:
    templates = [
        {
            "title": "Lifecycle continuity refresh",
            "description": "Review lifecycle capability coverage and refresh advisory lifecycle health summaries.",
            "category": "lifecycle",
            "suggested_instruction": "Run lifecycle coverage review and summarize any drift in advisory capability profiles.",
            "risk_reduction_score": 50,
            "effort_score": 30,
            "confidence_score": 85,
        },
        {
            "title": "Release readiness continuity baseline",
            "description": "Regenerate release readiness artifacts and verify advisory report continuity.",
            "category": "release",
            "suggested_instruction": "Regenerate release readiness report and document any advisory drift findings.",
            "risk_reduction_score": 55,
            "effort_score": 35,
            "confidence_score": 85,
        },
        {
            "title": "Memory graph ingestion coverage sweep",
            "description": "Audit optional mission-to-memory-graph ingestion coverage and note gaps.",
            "category": "memory",
            "suggested_instruction": "Audit memory graph ingestion paths and summarize uncovered mission metadata.",
            "risk_reduction_score": 45,
            "effort_score": 40,
            "confidence_score": 80,
        },
    ]
    out: List[Dict[str, Any]] = []
    for item in templates:
        priority = derive_priority(
            risk_reduction_score=int(item["risk_reduction_score"]),
            effort_score=int(item["effort_score"]),
            confidence_score=int(item["confidence_score"]),
        )
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title=str(item["title"]),
                description=str(item["description"]),
                source_finding_ids=[],
                category=str(item["category"]),
                priority=priority,
                risk_reduction_score=int(item["risk_reduction_score"]),
                effort_score=int(item["effort_score"]),
                confidence_score=int(item["confidence_score"]),
                recommended_repository=None,
                suggested_instruction=str(item["suggested_instruction"]),
                advisory_only=True,
                metadata={"source": "healthy_continuity"},
            ).to_dict()
        )
    return out


def _candidates_from_repo_intel(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    findings = report.get("findings")
    if not isinstance(findings, list):
        return []
    out: List[Dict[str, Any]] = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        sev = str(finding.get("severity") or "info").lower()
        if sev not in {"high", "critical", "medium"}:
            continue
        category = _safe_category(str(finding.get("category") or "repository"))
        scores = score_finding({"severity": sev, "category": category})
        priority = derive_priority(**scores)
        title = str(finding.get("title") or "Repository intelligence improvement")
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title=title,
                description=str(finding.get("description") or title),
                source_finding_ids=[str(finding.get("finding_id") or new_id("finding_ref"))],
                category=category,
                priority=priority,
                risk_reduction_score=scores["risk_reduction_score"],
                effort_score=scores["effort_score"],
                confidence_score=scores["confidence_score"],
                recommended_repository=_repo_hint_from_paths(finding.get("path_refs")),
                suggested_instruction=str(
                    finding.get("recommended_action")
                    or f"Address repository intelligence finding: {title}."
                ),
                advisory_only=True,
                metadata={"source": "repository_intelligence", "severity": sev},
            ).to_dict()
        )
    return out


def _candidates_from_remediation(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    batches = report.get("batches")
    if not isinstance(batches, list):
        return []
    out: List[Dict[str, Any]] = []
    for batch in batches[:3]:
        if not isinstance(batch, dict):
            continue
        priority = str(batch.get("priority") or "P4")
        if priority not in {"P0", "P1", "P2"}:
            continue
        title = str(batch.get("name") or "Remediation batch")
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title=f"Execute advisory {title}",
                description=f"Convert remediation batch '{title}' into tracked strategic mission work.",
                source_finding_ids=[str(batch.get("batch_id") or new_id("batch_ref"))],
                category="repository",
                priority=priority,
                risk_reduction_score=min(95, int(batch.get("expected_risk_reduction") or 60)),
                effort_score=min(90, int(batch.get("estimated_total_effort") or 45)),
                confidence_score=85,
                recommended_repository=(str(batch.get("repository") or "").strip() or None),
                suggested_instruction=f"Create advisory mission for remediation batch '{title}' and track items: {', '.join(batch.get('item_ids', [])[:5])}.",
                advisory_only=True,
                metadata={"source": "remediation_plan"},
            ).to_dict()
        )
    return out


def _candidates_from_handoffs(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    packages = report.get("packages")
    if not isinstance(packages, list):
        return []
    out: List[Dict[str, Any]] = []
    for package in packages[:3]:
        if not isinstance(package, dict):
            continue
        source_batch = str(package.get("source_batch_id") or "")
        title = str(package.get("title") or "Implementation package")
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title=f"Review and execute package: {title}",
                description="Move a prepared implementation package through human review and manual execution.",
                source_finding_ids=[source_batch] if source_batch else [],
                category="repository",
                priority="P2",
                risk_reduction_score=70,
                effort_score=45,
                confidence_score=85,
                recommended_repository=str((package.get("metadata") or {}).get("repository") or "").strip() or None,
                suggested_instruction=f"Review implementation package '{title}', validate scope, then execute manually after approval.",
                advisory_only=True,
                metadata={"source": "remediation_handoff"},
            ).to_dict()
        )
    return out


def _candidates_from_refinements(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    packages = report.get("refined_packages")
    if not isinstance(packages, list):
        return []
    out: List[Dict[str, Any]] = []
    for package in packages[:5]:
        if not isinstance(package, dict):
            continue
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title=f"Review refined package: {str(package.get('title') or 'Untitled')}",
                description="Use a focused refined package for safer manual implementation planning.",
                source_finding_ids=[str(package.get("refined_package_id") or new_id("ref_pkg_ref"))],
                category="repository",
                priority="P2",
                risk_reduction_score=70,
                effort_score=35,
                confidence_score=90,
                recommended_repository=str((package.get("metadata") or {}).get("repository") or "").strip() or None,
                suggested_instruction=f"Review refined package '{str(package.get('title') or '')}' and execute after manual approval.",
                advisory_only=True,
                metadata={"source": "handoff_refinement"},
            ).to_dict()
        )
    return out


def _candidates_from_work_queue(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    items = report.get("queue_items")
    if not isinstance(items, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in items[:5]:
        if not isinstance(item, dict):
            continue
        readiness = int(item.get("readiness_score") or 0)
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title=f"Execute queue item: {str(item.get('title') or 'Untitled')}",
                description="Queue-driven recommendation from autonomous work queue planning.",
                source_finding_ids=[str(item.get("queue_item_id") or new_id("queue_ref"))],
                category="repository",
                priority=str(item.get("priority") or ("P1" if readiness >= 85 else "P2")),
                risk_reduction_score=min(95, readiness),
                effort_score=int(item.get("effort_score") or 45),
                confidence_score=90,
                recommended_repository=None,
                suggested_instruction=f"Execute advisory queue item '{str(item.get('title') or '')}' in recommended position {int(item.get('recommended_position') or 0)}.",
                advisory_only=True,
                metadata={"source": "work_queue_manager", "execution_readiness": str(item.get("execution_readiness") or "unknown")},
            ).to_dict()
        )
    return out


def _candidates_from_execution_dossiers(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    dossiers = report.get("dossiers")
    if not isinstance(dossiers, list):
        return []
    out: List[Dict[str, Any]] = []
    for dossier in dossiers[:5]:
        if not isinstance(dossier, dict):
            continue
        score = int(dossier.get("execution_readiness_score") or 0)
        if score < 60:
            continue
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title=f"Execute ready dossier: {str(dossier.get('title') or 'Untitled')}",
                description="Execution-dossier-driven recommendation for manual approved implementation.",
                source_finding_ids=[str(dossier.get("dossier_id") or new_id("dossier_ref"))],
                category="repository",
                priority="P1" if score >= 85 else "P2",
                risk_reduction_score=min(95, score),
                effort_score=30,
                confidence_score=92,
                recommended_repository=None,
                suggested_instruction=f"Use execution dossier '{str(dossier.get('title') or '')}' as the primary implementation packet.",
                advisory_only=True,
                metadata={"source": "execution_dossier", "execution_risk": str(dossier.get("execution_risk") or "unknown")},
            ).to_dict()
        )
    return out


def _candidates_from_portfolio(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    order = report.get("recommended_execution_order")
    if not isinstance(order, list):
        return []
    out: List[Dict[str, Any]] = []
    for repo_id in order[:5]:
        if not isinstance(repo_id, str) or not repo_id.strip():
            continue
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title=f"Portfolio priority: {repo_id}",
                description="Cross-repository portfolio orchestration recommendation.",
                source_finding_ids=[str(report.get("report_id") or new_id("portfolio_report_ref"))],
                category="system",
                priority="P2",
                risk_reduction_score=min(90, int(report.get("portfolio_health_score") or 50)),
                effort_score=40,
                confidence_score=88,
                recommended_repository=repo_id,
                suggested_instruction=f"Prioritize advisory mission planning for repository '{repo_id}' based on portfolio execution order.",
                advisory_only=True,
                metadata={"source": "portfolio_orchestration"},
            ).to_dict()
        )
    return out


def _candidates_from_portfolio_bootstrap(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    recommendations = report.get("recommendations")
    if not isinstance(recommendations, list):
        return []
    out: List[Dict[str, Any]] = []
    for rec in recommendations[:5]:
        if not isinstance(rec, str) or not rec.strip():
            continue
        repo = _repo_hint_from_text(rec)
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title=f"Portfolio onboarding: {rec}",
                description="Onboarding recommendation from portfolio artifact bootstrap.",
                source_finding_ids=[str(report.get("report_id") or new_id("portfolio_bootstrap_report_ref"))],
                category="system",
                priority="P2",
                risk_reduction_score=65,
                effort_score=35,
                confidence_score=90,
                recommended_repository=repo,
                suggested_instruction=rec,
                advisory_only=True,
                metadata={"source": "portfolio_bootstrap"},
            ).to_dict()
        )
    return out


def _candidates_from_portfolio_onboarding_recommendations(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    recommendations = report.get("recommendations")
    if not isinstance(recommendations, list):
        return []
    out: List[Dict[str, Any]] = []
    for rec in recommendations[:5]:
        if not isinstance(rec, dict):
            continue
        action = ""
        rec_actions = rec.get("recommended_actions")
        if isinstance(rec_actions, list):
            for item in rec_actions:
                if isinstance(item, str) and item.strip():
                    action = item.strip()
                    break
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title=f"Portfolio onboarding recommendation: {str(rec.get('repository_name') or rec.get('repository_id') or 'repository')}",
                description=str(rec.get("title") or "Portfolio onboarding recommendation"),
                source_finding_ids=[str(rec.get("recommendation_id") or new_id("onboarding_recommendation_ref"))],
                category="system",
                priority=str(rec.get("priority") or "P3"),
                risk_reduction_score=70 if str(rec.get("priority") or "P3") in {"P0", "P1"} else 55,
                effort_score=35,
                confidence_score=92,
                recommended_repository=str(rec.get("repository_id") or "").strip() or None,
                suggested_instruction=action or str(rec.get("title") or "Apply onboarding recommendation"),
                advisory_only=True,
                metadata={"source": "portfolio_onboarding_recommendations"},
            ).to_dict()
        )
    return out


def _candidates_from_portfolio_dependencies(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    findings = report.get("findings")
    if not isinstance(findings, list):
        return []
    out: List[Dict[str, Any]] = []
    for finding in findings[:5]:
        if not isinstance(finding, dict):
            continue
        sev = str(finding.get("severity") or "info").lower()
        if sev not in {"high", "critical", "medium"}:
            continue
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title=f"Dependency risk: {str(finding.get('repository_id') or 'repository')}",
                description=str(finding.get("title") or "Portfolio dependency finding"),
                source_finding_ids=[str(finding.get("finding_id") or new_id("dependency_finding_ref"))],
                category="system",
                priority="P1" if sev in {"high", "critical"} else "P2",
                risk_reduction_score=75 if sev in {"high", "critical"} else 60,
                effort_score=40,
                confidence_score=88,
                recommended_repository=str(finding.get("repository_id") or "").strip() or None,
                suggested_instruction=str(finding.get("recommended_action") or "Resolve dependency blocker."),
                advisory_only=True,
                metadata={"source": "portfolio_dependencies", "severity": sev},
            ).to_dict()
        )
    return out


def _candidates_from_portfolio_critical_path(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    recs = report.get("recommendations")
    if not isinstance(recs, list):
        return []
    out: List[Dict[str, Any]] = []
    for rec in recs[:5]:
        if not isinstance(rec, dict):
            continue
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title=f"Critical path: {str(rec.get('repository_id') or 'repository')}",
                description=str(rec.get("title") or "Critical path recommendation"),
                source_finding_ids=[str(rec.get("recommendation_id") or new_id("critical_path_rec_ref"))],
                category="system",
                priority=str(rec.get("priority") or "P3"),
                risk_reduction_score=80,
                effort_score=45,
                confidence_score=90,
                recommended_repository=str(rec.get("repository_id") or "").strip() or None,
                suggested_instruction=str(rec.get("recommended_action") or "Apply critical path recommendation."),
                advisory_only=True,
                metadata={"source": "portfolio_critical_path"},
            ).to_dict()
        )
    return out


def _candidates_from_portfolio_roadmap(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    items = report.get("roadmap_items")
    if not isinstance(items, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in items[:5]:
        if not isinstance(item, dict):
            continue
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title=f"Roadmap wave action: {str(item.get('repository_id') or 'repository')}",
                description=str(item.get("title") or "Portfolio roadmap item"),
                source_finding_ids=[str(item.get("source_recommendation_id") or new_id("roadmap_item_ref"))],
                category="system",
                priority=str(item.get("priority") or "P3"),
                risk_reduction_score=75,
                effort_score=40,
                confidence_score=90,
                recommended_repository=str(item.get("repository_id") or "").strip() or None,
                suggested_instruction=str(item.get("objective") or "Apply portfolio roadmap recommendation."),
                advisory_only=True,
                metadata={"source": "portfolio_roadmap", "wave": str(item.get("wave") or "wave_3")},
            ).to_dict()
        )
    return out


def _candidates_from_portfolio_progress(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    findings = report.get("findings")
    if not isinstance(findings, list):
        return []
    out: List[Dict[str, Any]] = []
    for finding in findings[:5]:
        if not isinstance(finding, dict):
            continue
        trend = str(finding.get("trend") or "unknown")
        if trend != "declining":
            continue
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title=f"Progress trend recovery: {str(finding.get('repository_id') or 'portfolio')}",
                description=str(finding.get("title") or "Declining portfolio progress trend"),
                source_finding_ids=[str(finding.get("finding_id") or new_id("progress_finding_ref"))],
                category="system",
                priority="P1" if str(finding.get("repository_id") or "") == "portfolio" else "P2",
                risk_reduction_score=75,
                effort_score=35,
                confidence_score=90,
                recommended_repository=str(finding.get("repository_id") or "").strip() or None,
                suggested_instruction=str(finding.get("recommended_action") or "Address declining progress trend."),
                advisory_only=True,
                metadata={"source": "portfolio_progress", "trend": trend},
            ).to_dict()
        )
    return out


def _candidates_from_portfolio_drift(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    findings = report.get("findings")
    if not isinstance(findings, list):
        return []
    out: List[Dict[str, Any]] = []
    for finding in findings[:5]:
        if not isinstance(finding, dict):
            continue
        sev = str(finding.get("severity") or "low").lower()
        if sev not in {"medium", "high", "critical"}:
            continue
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title=f"Drift remediation: {str(finding.get('repository_id') or 'portfolio')}",
                description=str(finding.get("title") or "Portfolio drift finding"),
                source_finding_ids=[str(finding.get("finding_id") or new_id("drift_finding_ref"))],
                category="system",
                priority="P1" if sev in {"high", "critical"} else "P2",
                risk_reduction_score=80 if sev in {"high", "critical"} else 65,
                effort_score=35,
                confidence_score=90,
                recommended_repository=str(finding.get("repository_id") or "").strip() or None,
                suggested_instruction=str(finding.get("recommended_action") or "Resolve portfolio drift finding."),
                advisory_only=True,
                metadata={"source": "portfolio_drift", "severity": sev},
            ).to_dict()
        )
    return out


def _candidates_from_portfolio_governance_index(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    score = int(report.get("governance_score") or 0)
    status = str(report.get("governance_status") or "unknown")
    if status in {"healthy", "unknown"} and score >= 85:
        return []
    priority = "P1" if status in {"critical", "degraded"} else "P2"
    return [
        StrategicMissionCandidate(
            candidate_id=new_id("strategic_mission"),
            title="Governance index improvement mission",
            description=f"Governance index status is {status} with score {score}.",
            source_finding_ids=[str(report.get("report_id") or new_id("governance_index_ref"))],
            category="system",
            priority=priority,
            risk_reduction_score=80 if priority == "P1" else 65,
            effort_score=40,
            confidence_score=92,
            recommended_repository="portfolio",
            suggested_instruction="Address top governance index reasons and execute highest-impact recommendations first.",
            advisory_only=True,
            metadata={"source": "portfolio_governance_index", "governance_status": status, "governance_score": score},
        ).to_dict()
    ]


def _candidates_from_governance_recovery(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    actions = report.get("actions")
    if not isinstance(actions, list):
        return []
    out: List[Dict[str, Any]] = []
    for action in actions[:5]:
        if not isinstance(action, dict):
            continue
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title=f"Recovery action: {str(action.get('title') or 'Governance recovery')}",
                description=str(action.get("description") or "Governance recovery action"),
                source_finding_ids=[str(action.get("action_id") or new_id("recovery_action_ref"))],
                category="system",
                priority=str(action.get("priority") or "P2"),
                risk_reduction_score=min(95, int(action.get("expected_score_impact") or 5) * 5),
                effort_score=35,
                confidence_score=92,
                recommended_repository="portfolio",
                suggested_instruction=str(action.get("description") or "Execute governance recovery action manually."),
                advisory_only=True,
                metadata={"source": "governance_recovery", "target_component": str(action.get("target_component") or "")},
            ).to_dict()
        )
    return out


def _candidates_from_governance_recovery_dossiers(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    dossiers = report.get("dossiers")
    if not isinstance(dossiers, list):
        return []
    out: List[Dict[str, Any]] = []
    for dossier in dossiers[:5]:
        if not isinstance(dossier, dict):
            continue
        risk = str(dossier.get("execution_risk") or "low")
        priority = "P1" if risk in {"high", "critical"} else "P2"
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title=f"Execute recovery dossier: {str(dossier.get('title') or 'Governance recovery dossier')}",
                description=str(dossier.get("objective") or "Governance recovery execution dossier."),
                source_finding_ids=[str(dossier.get("source_action_id") or new_id("dossier_action_ref"))],
                category="system",
                priority=priority,
                risk_reduction_score=80 if priority == "P1" else 65,
                effort_score=35,
                confidence_score=92,
                recommended_repository="portfolio",
                suggested_instruction=f"Review and manually execute governance recovery dossier '{str(dossier.get('title') or '')}'.",
                advisory_only=True,
                metadata={"source": "governance_recovery_dossiers", "execution_risk": risk},
            ).to_dict()
        )
    return out


def _candidates_from_governance_approval_readiness(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    records = report.get("records")
    if not isinstance(records, list):
        return []
    out: List[Dict[str, Any]] = []
    for record in records[:5]:
        if not isinstance(record, dict):
            continue
        status = str(record.get("approval_status") or "unknown")
        if status not in {"blocked", "needs_review", "rejected_advisory"}:
            continue
        priority = "P1" if status in {"blocked", "rejected_advisory"} else "P2"
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title=f"Clear approval readiness issue: {str(record.get('title') or 'Governance dossier')}",
                description=str(record.get("approval_recommendation") or "Resolve governance approval readiness gaps."),
                source_finding_ids=[str(record.get("record_id") or new_id("approval_readiness_ref"))],
                category="governance",
                priority=priority,
                risk_reduction_score=80 if priority == "P1" else 65,
                effort_score=30,
                confidence_score=92,
                recommended_repository="portfolio",
                suggested_instruction=str(record.get("approval_recommendation") or "Resolve advisory approval readiness issue."),
                advisory_only=True,
                metadata={"source": "governance_approval_readiness", "approval_status": status},
            ).to_dict()
        )
    return out


def _candidates_from_governance_approval_packets(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    packets = report.get("packets")
    if not isinstance(packets, list):
        return []
    out: List[Dict[str, Any]] = []
    for packet in packets[:5]:
        if not isinstance(packet, dict):
            continue
        status = str(packet.get("approval_status") or "unknown")
        if status not in {"ready_for_review", "needs_review"}:
            continue
        priority = "P2" if status == "needs_review" else "P3"
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title=f"Review governance approval packet: {str(packet.get('title') or 'Governance packet')}",
                description=str(packet.get("review_summary") or "Perform human review of governance approval packet."),
                source_finding_ids=[str(packet.get("packet_id") or new_id("approval_packet_ref"))],
                category="governance",
                priority=priority,
                risk_reduction_score=60 if status == "needs_review" else 45,
                effort_score=20,
                confidence_score=95,
                recommended_repository="portfolio",
                suggested_instruction="Complete human decision template and record manual review outcome.",
                advisory_only=True,
                metadata={"source": "governance_approval_packets", "approval_status": status},
            ).to_dict()
        )
    return out


def _candidates_from_governance_decisions(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    out: List[Dict[str, Any]] = []
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    pending = int(summary.get("pending", 0) or 0)
    req_changes = int(summary.get("request_changes", 0) or 0)
    approved = int(summary.get("approved", 0) or 0)
    if pending > 0:
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title="Review pending governance decision packets",
                description=f"{pending} approval packet(s) are still pending human decision.",
                source_finding_ids=[str(report.get("report_id") or new_id("governance_decision_report_ref"))],
                category="governance",
                priority="P2",
                risk_reduction_score=65,
                effort_score=25,
                confidence_score=95,
                recommended_repository="portfolio",
                suggested_instruction="Complete pending governance packet decisions before manual execution planning.",
                advisory_only=True,
                metadata={"source": "governance_decisions", "decision_state": "pending"},
            ).to_dict()
        )
    if req_changes > 0:
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title="Address governance packets marked request_changes",
                description=f"{req_changes} packet(s) are marked request_changes.",
                source_finding_ids=[str(report.get("report_id") or new_id("governance_decision_report_ref"))],
                category="governance",
                priority="P1",
                risk_reduction_score=75,
                effort_score=30,
                confidence_score=95,
                recommended_repository="portfolio",
                suggested_instruction="Resolve requested packet changes and re-submit for human governance review.",
                advisory_only=True,
                metadata={"source": "governance_decisions", "decision_state": "request_changes"},
            ).to_dict()
        )
    if approved > 0:
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title="Plan manual execution for approved governance packets",
                description=f"{approved} packet(s) are approved for manual execution planning.",
                source_finding_ids=[str(report.get("report_id") or new_id("governance_decision_report_ref"))],
                category="governance",
                priority="P3",
                risk_reduction_score=50,
                effort_score=20,
                confidence_score=95,
                recommended_repository="portfolio",
                suggested_instruction="Prepare manual execution plans for approved packets without automation.",
                advisory_only=True,
                metadata={"source": "governance_decisions", "decision_state": "approved"},
            ).to_dict()
        )
    return out


def _candidates_from_manual_execution_queue(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    out: List[Dict[str, Any]] = []
    pending = int(summary.get("pending_review", 0) or 0)
    deferred = int(summary.get("deferred", 0) or 0)
    needs_changes = int(summary.get("needs_changes", 0) or 0)
    approved = int(summary.get("approved_manual", 0) or 0)
    report_id = str(report.get("report_id") or new_id("manual_execution_queue_report_ref"))
    if pending > 0:
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title="Review pending manual execution handoff queue items",
                description=f"{pending} queue item(s) are pending governance review.",
                source_finding_ids=[report_id],
                category="governance",
                priority="P2",
                risk_reduction_score=65,
                effort_score=25,
                confidence_score=95,
                recommended_repository="portfolio",
                suggested_instruction="Review pending manual handoff queue items and record governance decisions.",
                advisory_only=True,
                metadata={"source": "manual_execution_queue"},
            ).to_dict()
        )
    if needs_changes > 0:
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title="Resolve manual execution queue items needing changes",
                description=f"{needs_changes} queue item(s) need packet/dossier updates before manual handoff.",
                source_finding_ids=[report_id],
                category="governance",
                priority="P1",
                risk_reduction_score=75,
                effort_score=30,
                confidence_score=95,
                recommended_repository="portfolio",
                suggested_instruction="Revise packet/dossier content for items flagged as needs_changes.",
                advisory_only=True,
                metadata={"source": "manual_execution_queue"},
            ).to_dict()
        )
    if deferred > 0:
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title="Revisit deferred manual execution queue items",
                description=f"{deferred} queue item(s) are deferred awaiting conditions.",
                source_finding_ids=[report_id],
                category="governance",
                priority="P3",
                risk_reduction_score=45,
                effort_score=20,
                confidence_score=95,
                recommended_repository="portfolio",
                suggested_instruction="Track deferred conditions and revisit when blockers are resolved.",
                advisory_only=True,
                metadata={"source": "manual_execution_queue"},
            ).to_dict()
        )
    if approved > 0:
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title="Prepare approved manual execution handoff packages",
                description=f"{approved} queue item(s) are approved for manual handoff preparation.",
                source_finding_ids=[report_id],
                category="governance",
                priority="P2",
                risk_reduction_score=55,
                effort_score=20,
                confidence_score=95,
                recommended_repository="portfolio",
                suggested_instruction="Prepare operator-facing manual execution handoff instructions for approved items.",
                advisory_only=True,
                metadata={"source": "manual_execution_queue"},
            ).to_dict()
        )
    return out


def _suggested_instruction(*, title: str, category: str, actions: Any) -> str:
    action_hint = ""
    if isinstance(actions, list):
        for action in actions:
            if isinstance(action, str) and action.strip():
                action_hint = action.strip()
                break
    if action_hint:
        return f"{action_hint} (Strategic focus: {category}; context: {title})"
    return f"Address strategic {category} finding: {title}."


def _safe_category(value: str) -> str:
    value = value.strip().lower()
    allowed = {"lifecycle", "governance", "release", "memory", "scheduler", "tooling", "repository", "system"}
    if value in allowed:
        return value
    if value == "mission":
        return "system"
    return "system"


def _repo_hint_from_text(text: str) -> str | None:
    # deterministic light heuristic only
    lowered = text.lower()
    for repo in ("powerframe", "powerstarter", "conceptshop", "therockettree", "pf-wai"):
        if repo in lowered:
            return repo
    return None


def _repo_hint_from_paths(path_refs: Any) -> str | None:
    if not isinstance(path_refs, list):
        return None
    joined = " ".join(str(p) for p in path_refs if isinstance(p, str)).lower()
    return _repo_hint_from_text(joined)


def _rank_candidates(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        candidates,
        key=lambda c: (
            _priority_order(str(c.get("priority") or "P4")),
            -rank_candidate(c),
            str(c.get("title") or ""),
        ),
    )


def _priority_order(priority: str) -> int:
    order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}
    return order.get(priority, 4)


def _priority_counts(candidates: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for c in candidates:
        p = str(c.get("priority") or "P4")
        counts[p] = counts.get(p, 0) + 1
    return counts


def _category_counts(candidates: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for c in candidates:
        cat = str(c.get("category") or "system")
        counts[cat] = counts.get(cat, 0) + 1
    return counts


def _overall_status(candidates: List[Dict[str, Any]]) -> str:
    if not candidates:
        return "healthy"
    if any(str(c.get("priority")) == "P0" for c in candidates):
        return "blocked"
    if any(str(c.get("priority")) == "P1" for c in candidates):
        return "degraded"
    if any(str(c.get("priority")) == "P2" for c in candidates):
        return "warning"
    return "healthy"

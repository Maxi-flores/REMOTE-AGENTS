from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from portfolio_critical_path.contracts import (
    CriticalPathRecommendation,
    CriticalRepositoryScore,
    PortfolioCriticalPathReport,
    new_id,
    utc_now,
    validate_portfolio_critical_path_report_dict,
)
from portfolio_critical_path.scoring import (
    compute_critical_path_score,
    compute_influence_score,
    onboarding_priority_weight,
    recommendation_priority,
)
from portfolio_orchestration.registry import load_portfolio_registry


def load_json(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def generate_portfolio_critical_path_report(*, base_dir: str | Path = ".") -> Dict[str, Any]:
    root = Path(base_dir)
    repos = [r for r in load_portfolio_registry(base_dir=root) if isinstance(r, dict)]
    dep = load_json(root / ".control_plane" / "portfolio_dependencies" / "latest.json")
    portfolio = load_json(root / ".control_plane" / "portfolio" / "latest.json")
    onboarding = load_json(root / ".control_plane" / "portfolio_onboarding_recommendations" / "latest.json")

    dep_graph = dep.get("dependency_graph") if isinstance(dep.get("dependency_graph"), dict) else {}
    dep_chains = dep.get("dependency_chains") if isinstance(dep.get("dependency_chains"), list) else []
    dep_findings = dep.get("findings") if isinstance(dep.get("findings"), list) else []
    status_map = _status_map(portfolio)
    onboarding_map = _onboarding_priority_map(onboarding)
    consumers = _consumers_map(dep_graph)

    scores: List[Dict[str, Any]] = []
    recommendations: List[Dict[str, Any]] = []
    for repo in repos:
        rid = str(repo.get("repository_id") or "")
        if not rid:
            continue
        readiness = int((status_map.get(rid) or {}).get("readiness_score") or 0)
        consumer_count = len(consumers.get(rid, []))
        provider_count = len(dep_graph.get(rid, [])) if isinstance(dep_graph.get(rid), list) else 0
        chain_count = sum(1 for chain in dep_chains if isinstance(chain, list) and rid in chain)
        propagated_risk_count = _propagated_risk_count(dep_findings, rid)
        influence = compute_influence_score(
            consumer_count=consumer_count,
            provider_count=provider_count,
            dependency_chain_count=chain_count,
            propagated_risk_count=propagated_risk_count,
            readiness_score=readiness,
        )
        high_dep_findings = _high_dep_findings_for_repo(dep_findings, rid)
        cp_score = compute_critical_path_score(
            influence_score=influence,
            readiness_score=readiness,
            downstream_consumers=consumer_count,
            high_severity_dependency_findings=high_dep_findings,
            onboarding_priority_weight=onboarding_priority_weight(onboarding_map.get(rid, "P4")),
        )
        score_record = CriticalRepositoryScore(
            repository_id=rid,
            repository_name=str(repo.get("repository_name") or rid),
            consumer_count=consumer_count,
            provider_count=provider_count,
            dependency_chain_count=chain_count,
            propagated_risk_count=propagated_risk_count,
            readiness_score=readiness,
            influence_score=influence,
            critical_path_score=cp_score,
            advisory_only=True,
            metadata={},
        ).to_dict()
        scores.append(score_record)
        recommendations.append(_recommendation_for_score(score_record, dep_graph.get(rid) if isinstance(dep_graph.get(rid), list) else []))

    scores.sort(key=lambda s: (-int(s.get("critical_path_score") or 0), str(s.get("repository_id") or "")))
    recommendations.sort(key=lambda r: (_priority_order(str(r.get("priority") or "P4")), str(r.get("repository_id") or "")))
    top_repos = [str(s.get("repository_id")) for s in scores[:5]]
    top_chains = [c for c in dep_chains[:5] if isinstance(c, list)]
    report = PortfolioCriticalPathReport(
        report_id=new_id("portfolio_critical_path_report"),
        generated_utc=utc_now(),
        critical_repository_scores=scores,
        recommendations=recommendations,
        top_critical_repositories=top_repos,
        top_dependency_chains=top_chains,
        portfolio_leverage_summary={
            "repository_count": len(scores),
            "recommendation_count": len(recommendations),
            "average_critical_path_score": int(sum(int(s.get("critical_path_score") or 0) for s in scores) / len(scores)) if scores else 0,
        },
        advisory_only=True,
        metadata={"advisory_only": True, "runtime_unchanged": True, "queue_mutation": False},
    ).to_dict()
    validate_portfolio_critical_path_report_dict(report)
    return report


def _status_map(report: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    statuses = report.get("repository_statuses")
    if not isinstance(statuses, list):
        return {}
    return {str(s.get("repository_id")): s for s in statuses if isinstance(s, dict) and str(s.get("repository_id") or "").strip()}


def _onboarding_priority_map(report: Dict[str, Any]) -> Dict[str, str]:
    recs = report.get("recommendations")
    if not isinstance(recs, list):
        return {}
    return {str(r.get("repository_id")): str(r.get("priority") or "P4") for r in recs if isinstance(r, dict) and str(r.get("repository_id") or "").strip()}


def _consumers_map(graph: Dict[str, Any]) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    for repo, deps in graph.items():
        if not isinstance(deps, list):
            continue
        out.setdefault(str(repo), [])
        for dep in deps:
            key = str(dep)
            out.setdefault(key, []).append(str(repo))
    for key in list(out.keys()):
        out[key] = sorted(set(out[key]))
    return out


def _propagated_risk_count(findings: List[Any], repository_id: str) -> int:
    count = 0
    for f in findings:
        if not isinstance(f, dict):
            continue
        if str(f.get("repository_id") or "") == repository_id:
            sev = str(f.get("severity") or "info").lower()
            if sev in {"high", "critical", "medium"}:
                count += 1
    return count


def _high_dep_findings_for_repo(findings: List[Any], repository_id: str) -> int:
    return sum(
        1
        for f in findings
        if isinstance(f, dict)
        and str(f.get("repository_id") or "") == repository_id
        and str(f.get("severity") or "").lower() in {"high", "critical"}
    )


def _recommendation_for_score(score: Dict[str, Any], deps: List[str]) -> Dict[str, Any]:
    rid = str(score.get("repository_id") or "unknown")
    cp = int(score.get("critical_path_score") or 0)
    priority = recommendation_priority(cp)
    title = f"Critical path action for {rid}"
    rationale = f"Critical path score {cp}, influence {int(score.get('influence_score') or 0)}, readiness {int(score.get('readiness_score') or 0)}."
    impact = "Improves downstream dependency confidence and portfolio leverage." if int(score.get("consumer_count") or 0) > 0 else "Improves repository readiness posture."
    action = f"Prioritize onboarding/readiness blockers for {rid} before dependent portfolio execution."
    return CriticalPathRecommendation(
        recommendation_id=new_id("critical_path_recommendation"),
        repository_id=rid,
        priority=priority,
        title=title,
        rationale=rationale,
        expected_portfolio_impact=impact,
        recommended_action=action,
        dependency_refs=[str(d) for d in deps],
        advisory_only=True,
        metadata={},
    ).to_dict()


def _priority_order(priority: str) -> int:
    return {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}.get(priority, 4)


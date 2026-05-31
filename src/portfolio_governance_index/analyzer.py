from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from portfolio_governance_index.contracts import (
    PortfolioGovernanceHealthReport,
    new_id,
    utc_now,
    validate_portfolio_governance_health_report_dict,
)
from portfolio_governance_index.scorer import component, governance_status, weighted_governance_score


def load_json(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def generate_portfolio_governance_health_report(*, base_dir: str | Path = ".") -> Dict[str, Any]:
    root = Path(base_dir)
    portfolio = load_json(root / ".control_plane" / "portfolio" / "latest.json")
    bootstrap = load_json(root / ".control_plane" / "portfolio_bootstrap" / "latest.json")
    onboarding = load_json(root / ".control_plane" / "portfolio_onboarding_recommendations" / "latest.json")
    deps = load_json(root / ".control_plane" / "portfolio_dependencies" / "latest.json")
    critical_path = load_json(root / ".control_plane" / "portfolio_critical_path" / "latest.json")
    roadmap = load_json(root / ".control_plane" / "portfolio_roadmap" / "latest.json")
    progress = load_json(root / ".control_plane" / "portfolio_progress" / "latest.json")
    drift = load_json(root / ".control_plane" / "portfolio_drift" / "latest.json")
    recovery = load_json(root / ".control_plane" / "governance_recovery" / "latest.json")

    components: List[Dict[str, Any]] = []
    unknowns = 0

    health_score = _int_or_none(portfolio.get("portfolio_health_score"))
    if health_score is None:
        components.append(component(name="Portfolio Health", score=50, reasons=["Portfolio health score unavailable."], status="unknown"))
        unknowns += 1
    else:
        components.append(component(name="Portfolio Health", score=health_score, reasons=[f"Portfolio health score is {health_score}."]))

    readiness_score = _int_or_none(portfolio.get("portfolio_readiness_score"))
    if readiness_score is None:
        components.append(component(name="Portfolio Readiness", score=50, reasons=["Portfolio readiness score unavailable."], status="unknown"))
        unknowns += 1
    else:
        components.append(component(name="Portfolio Readiness", score=readiness_score, reasons=[f"Portfolio readiness score is {readiness_score}."]))

    onboarding_avg = _int_or_none((bootstrap.get("readiness_summary") or {}).get("average_readiness_estimate")) if isinstance(bootstrap.get("readiness_summary"), dict) else None
    if onboarding_avg is None:
        components.append(component(name="Onboarding Coverage", score=50, reasons=["Bootstrap onboarding readiness unavailable."], status="unknown"))
        unknowns += 1
    else:
        none_count = _count_bootstrap_none(bootstrap)
        adjusted = max(0, min(100, onboarding_avg - min(40, none_count * 5)))
        components.append(component(name="Onboarding Coverage", score=adjusted, reasons=[f"Average onboarding readiness is {onboarding_avg}.", f"{none_count} repository(ies) have artifact_status=none."]))

    dep_high = _count_dependency_high(deps)
    dep_total = _count_list(deps.get("findings"))
    if dep_total == 0 and not deps:
        components.append(component(name="Dependency Risk", score=50, reasons=["Dependency report unavailable."], status="unknown"))
        unknowns += 1
    else:
        dep_score = max(0, 100 - min(100, dep_high * 10))
        components.append(component(name="Dependency Risk", score=dep_score, reasons=[f"Dependency findings: total={dep_total}, high_or_critical={dep_high}."]))

    cp_recs = _count_list(critical_path.get("recommendations"))
    cp_p1 = _count_priority(critical_path, {"P0", "P1"})
    if cp_recs == 0 and not critical_path:
        components.append(component(name="Critical Path Risk", score=50, reasons=["Critical-path report unavailable."], status="unknown"))
        unknowns += 1
    else:
        cp_score = max(0, 100 - min(100, cp_p1 * 15))
        components.append(component(name="Critical Path Risk", score=cp_score, reasons=[f"Critical-path recommendations={cp_recs}, P0/P1={cp_p1}."]))

    waves = roadmap.get("waves") if isinstance(roadmap.get("waves"), list) else []
    if not waves and not roadmap:
        components.append(component(name="Roadmap Completeness", score=50, reasons=["Roadmap report unavailable."], status="unknown"))
        unknowns += 1
    else:
        non_empty = sum(1 for w in waves if isinstance(w, dict) and _count_list(w.get("items")) > 0)
        roadmap_score = int(min(100, non_empty * 34))
        components.append(component(name="Roadmap Completeness", score=roadmap_score, reasons=[f"{non_empty} roadmap wave(s) contain actionable items."]))

    progress_trends = (progress.get("portfolio_trends") or {}).get("trend_counts") if isinstance(progress.get("portfolio_trends"), dict) else None
    if not isinstance(progress_trends, dict):
        components.append(component(name="Progress Trend", score=50, reasons=["Progress trend summary unavailable."], status="unknown"))
        unknowns += 1
    else:
        improving = int(progress_trends.get("improving") or 0)
        declining = int(progress_trends.get("declining") or 0)
        stable = int(progress_trends.get("stable") or 0)
        trend_score = max(0, min(100, 60 + (improving * 8) - (declining * 12) + min(20, stable * 2)))
        components.append(component(name="Progress Trend", score=trend_score, reasons=[f"Progress trends: improving={improving}, stable={stable}, declining={declining}."]))

    drift_summary = drift.get("summary") if isinstance(drift.get("summary"), dict) else None
    if not isinstance(drift_summary, dict):
        components.append(component(name="Drift Health", score=50, reasons=["Drift report unavailable."], status="unknown"))
        unknowns += 1
    else:
        sev = drift_summary.get("severity_counts") if isinstance(drift_summary.get("severity_counts"), dict) else {}
        high = int(sev.get("high") or 0) + int(sev.get("critical") or 0)
        low = int(sev.get("low") or 0) + int(sev.get("medium") or 0)
        drift_score = max(0, 100 - min(100, high * 30 + low * 8))
        components.append(component(name="Drift Health", score=drift_score, reasons=[f"Drift findings: high_or_critical={high}, low_or_medium={low}."]))

    governance_score = weighted_governance_score(components)
    status = governance_status(governance_score, unknowns)
    top_reasons = _top_reasons(components, limit=6)
    top_recommendations = _top_recommendations(components, readiness_score, dep_high, cp_p1, _count_bootstrap_none(bootstrap))

    report = PortfolioGovernanceHealthReport(
        report_id=new_id("portfolio_governance_health_report"),
        generated_utc=utc_now(),
        governance_score=governance_score,
        governance_status=status,
        components=components,
        top_reasons=top_reasons,
        top_recommendations=top_recommendations,
        advisory_only=True,
        metadata={
            "advisory_only": True,
            "runtime_unchanged": True,
            "queue_mutation": False,
            "source_artifacts": {
                "portfolio": str(root / ".control_plane" / "portfolio" / "latest.json"),
                "bootstrap": str(root / ".control_plane" / "portfolio_bootstrap" / "latest.json"),
                "onboarding": str(root / ".control_plane" / "portfolio_onboarding_recommendations" / "latest.json"),
                "dependencies": str(root / ".control_plane" / "portfolio_dependencies" / "latest.json"),
                "critical_path": str(root / ".control_plane" / "portfolio_critical_path" / "latest.json"),
                "roadmap": str(root / ".control_plane" / "portfolio_roadmap" / "latest.json"),
                "progress": str(root / ".control_plane" / "portfolio_progress" / "latest.json"),
                "drift": str(root / ".control_plane" / "portfolio_drift" / "latest.json"),
                "governance_recovery": str(root / ".control_plane" / "governance_recovery" / "latest.json"),
            },
            "recovery_summary": {
                "action_count": _count_list(recovery.get("actions")),
                "wave_count": _count_list(recovery.get("waves")),
                "target_governance_score": int(recovery.get("target_governance_score") or 0),
            } if recovery else {},
        },
    ).to_dict()
    validate_portfolio_governance_health_report_dict(report)
    return report


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    return None


def _count_list(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _count_bootstrap_none(bootstrap: Dict[str, Any]) -> int:
    records = bootstrap.get("onboarding_records")
    if not isinstance(records, list):
        return 0
    return sum(1 for r in records if isinstance(r, dict) and str(r.get("artifact_status") or "").lower() == "none")


def _count_dependency_high(deps: Dict[str, Any]) -> int:
    findings = deps.get("findings")
    if not isinstance(findings, list):
        return 0
    return sum(1 for f in findings if isinstance(f, dict) and str(f.get("severity") or "").lower() in {"high", "critical"})


def _count_priority(critical_path: Dict[str, Any], priorities: set[str]) -> int:
    recs = critical_path.get("recommendations")
    if not isinstance(recs, list):
        return 0
    return sum(1 for r in recs if isinstance(r, dict) and str(r.get("priority") or "") in priorities)


def _top_reasons(components: List[Dict[str, Any]], *, limit: int) -> List[str]:
    ordered = sorted(
        [c for c in components if isinstance(c, dict)],
        key=lambda c: int(c.get("score") or 0),
    )
    reasons: List[str] = []
    for component in ordered:
        name = str(component.get("name") or "Component")
        score = int(component.get("score") or 0)
        reasons.append(f"{name} score is {score}.")
        if len(reasons) >= limit:
            break
    return reasons


def _top_recommendations(
    components: List[Dict[str, Any]],
    readiness_score: int | None,
    dep_high: int,
    cp_p1: int,
    onboarding_none: int,
) -> List[str]:
    recommendations: List[str] = []
    if readiness_score is not None and readiness_score < 50:
        recommendations.append("Raise portfolio readiness by closing top onboarding and dependency blockers.")
    if onboarding_none > 0:
        recommendations.append("Complete onboarding for repositories with artifact_status=none.")
    if dep_high > 0:
        recommendations.append("Reduce high/critical dependency findings before dependent rollout.")
    if cp_p1 > 0:
        recommendations.append("Resolve P0/P1 critical-path recommendations in near-term roadmap waves.")
    low_components = [c for c in components if isinstance(c, dict) and int(c.get("score") or 0) < 70]
    if low_components:
        recommendations.append("Refresh portfolio, roadmap, progress, and drift artifacts after remediation updates.")
    if not recommendations:
        recommendations.append("Maintain current advisory governance cadence and continue periodic refresh.")
    return recommendations[:6]

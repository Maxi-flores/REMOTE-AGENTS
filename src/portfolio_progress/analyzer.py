from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from portfolio_progress.contracts import (
    PortfolioProgressFinding,
    PortfolioProgressMetric,
    PortfolioProgressReport,
    new_id,
    utc_now,
    validate_portfolio_progress_report_dict,
)
from portfolio_progress.tracker import (
    compute_delta,
    compute_trend,
    count_dependency_findings,
    critical_path_score_map,
    load_latest_and_previous,
    onboarding_average_readiness,
    onboarding_readiness_map,
    onboarding_unknown_count,
    repository_status_map,
)


def generate_portfolio_progress_report(*, base_dir: str | Path = ".") -> Dict[str, Any]:
    root = Path(base_dir)
    portfolio_cur, portfolio_prev = load_latest_and_previous(root / ".control_plane" / "portfolio")
    roadmap_cur, roadmap_prev = load_latest_and_previous(root / ".control_plane" / "portfolio_roadmap")
    onboarding_cur, onboarding_prev = load_latest_and_previous(root / ".control_plane" / "portfolio_bootstrap")
    dep_cur, dep_prev = load_latest_and_previous(root / ".control_plane" / "portfolio_dependencies")
    cp_cur, cp_prev = load_latest_and_previous(root / ".control_plane" / "portfolio_critical_path")
    drift_cur, drift_prev = load_latest_and_previous(root / ".control_plane" / "portfolio_drift")

    metrics: List[Dict[str, Any]] = []

    metrics.extend(
        [
            _metric("portfolio", "portfolio_health_score", portfolio_cur.get("portfolio_health_score"), portfolio_prev.get("portfolio_health_score")),
            _metric("portfolio", "portfolio_readiness_score", portfolio_cur.get("portfolio_readiness_score"), portfolio_prev.get("portfolio_readiness_score")),
            _metric("portfolio", "onboarding_average_readiness", onboarding_average_readiness(onboarding_cur), onboarding_average_readiness(onboarding_prev)),
            _metric("portfolio", "onboarding_unknown_count", onboarding_unknown_count(onboarding_cur), onboarding_unknown_count(onboarding_prev)),
            _metric("portfolio", "dependency_finding_count", count_dependency_findings(dep_cur), count_dependency_findings(dep_prev)),
            _metric(
                "portfolio",
                "dependency_high_count",
                count_dependency_findings(dep_cur, severity=("high", "critical")),
                count_dependency_findings(dep_prev, severity=("high", "critical")),
            ),
            _metric(
                "portfolio",
                "critical_path_recommendation_count",
                _list_count(cp_cur.get("recommendations")),
                _list_count(cp_prev.get("recommendations")),
            ),
            _metric("portfolio", "roadmap_item_count", _list_count(roadmap_cur.get("roadmap_items")), _list_count(roadmap_prev.get("roadmap_items"))),
            _metric("portfolio", "roadmap_wave_count", _list_count(roadmap_cur.get("waves")), _list_count(roadmap_prev.get("waves"))),
            _metric("portfolio", "drift_finding_count", _list_count(drift_cur.get("findings")), _list_count(drift_prev.get("findings"))),
        ]
    )

    status_cur = repository_status_map(portfolio_cur)
    status_prev = repository_status_map(portfolio_prev)
    onboarding_cur_map = onboarding_readiness_map(onboarding_cur)
    onboarding_prev_map = onboarding_readiness_map(onboarding_prev)
    cp_cur_map = critical_path_score_map(cp_cur)
    cp_prev_map = critical_path_score_map(cp_prev)
    repo_ids = sorted(set(status_cur.keys()) | set(status_prev.keys()) | set(onboarding_cur_map.keys()) | set(cp_cur_map.keys()))
    for rid in repo_ids:
        cur_status = status_cur.get(rid, {})
        prev_status = status_prev.get(rid, {})
        metrics.append(_metric(rid, "repository_health_score", cur_status.get("health_score"), prev_status.get("health_score")))
        metrics.append(_metric(rid, "repository_readiness_score", cur_status.get("readiness_score"), prev_status.get("readiness_score")))
        metrics.append(_metric(rid, "repository_onboarding_readiness", onboarding_cur_map.get(rid), onboarding_prev_map.get(rid)))
        metrics.append(
            _metric(
                rid,
                "repository_dependency_findings",
                count_dependency_findings(dep_cur, repository_id=rid),
                count_dependency_findings(dep_prev, repository_id=rid),
            )
        )
        metrics.append(_metric(rid, "repository_critical_path_score", cp_cur_map.get(rid), cp_prev_map.get(rid)))

    findings = _findings_from_metrics(metrics)
    report = PortfolioProgressReport(
        report_id=new_id("portfolio_progress_report"),
        generated_utc=utc_now(),
        metrics=metrics,
        findings=findings,
        portfolio_trends=_portfolio_trend_summary(metrics),
        advisory_only=True,
        metadata={
            "advisory_only": True,
            "runtime_unchanged": True,
            "queue_mutation": False,
            "source_artifacts": {
                "portfolio_latest": str(root / ".control_plane" / "portfolio" / "latest.json"),
                "portfolio_roadmap_latest": str(root / ".control_plane" / "portfolio_roadmap" / "latest.json"),
                "portfolio_bootstrap_latest": str(root / ".control_plane" / "portfolio_bootstrap" / "latest.json"),
                "portfolio_dependencies_latest": str(root / ".control_plane" / "portfolio_dependencies" / "latest.json"),
                "portfolio_critical_path_latest": str(root / ".control_plane" / "portfolio_critical_path" / "latest.json"),
                "portfolio_drift_latest": str(root / ".control_plane" / "portfolio_drift" / "latest.json"),
            },
        },
    ).to_dict()
    validate_portfolio_progress_report_dict(report)
    return report


def _metric(repository_id: str, name: str, current: Any, previous: Any) -> Dict[str, Any]:
    current_v = _as_number(current)
    previous_v = _as_number(previous)
    delta = compute_delta(current_v, previous_v)
    trend = compute_trend(name, current_v, previous_v)
    return PortfolioProgressMetric(
        metric_id=new_id("portfolio_progress_metric"),
        repository_id=repository_id,
        metric_name=name,
        current_value=current_v if current_v is not None else 0.0,
        previous_value=previous_v,
        delta=delta,
        trend=trend,
        advisory_only=True,
        metadata={},
    ).to_dict()


def _findings_from_metrics(metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for metric in metrics:
        if not isinstance(metric, dict):
            continue
        trend = str(metric.get("trend") or "unknown")
        if trend not in {"declining", "unknown"}:
            continue
        rid = str(metric.get("repository_id") or "portfolio")
        name = str(metric.get("metric_name") or "metric")
        current = metric.get("current_value")
        previous = metric.get("previous_value")
        if trend == "unknown":
            severity = "low"
            title = f"Insufficient history for {name}"
            description = f"Current value {current}; previous value is unavailable."
            action = "Export another portfolio cycle to establish progress trend history."
        else:
            severity = "high" if rid == "portfolio" else "medium"
            title = f"Declining trend in {name}"
            description = f"Metric changed from {previous} to {current}."
            action = f"Investigate decline and prioritize remediation for {rid} {name}."
        findings.append(
            PortfolioProgressFinding(
                finding_id=new_id("portfolio_progress_finding"),
                severity=severity,
                repository_id=rid,
                title=title,
                description=description,
                trend=trend,
                recommended_action=action,
                advisory_only=True,
                metadata={"metric_name": name},
            ).to_dict()
        )
    return findings


def _portfolio_trend_summary(metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
    portfolio_metrics = [m for m in metrics if isinstance(m, dict) and str(m.get("repository_id") or "") == "portfolio"]
    counts = {"improving": 0, "stable": 0, "declining": 0, "unknown": 0}
    for metric in portfolio_metrics:
        trend = str(metric.get("trend") or "unknown")
        if trend in counts:
            counts[trend] += 1
    return {
        "portfolio_metric_count": len(portfolio_metrics),
        "trend_counts": counts,
        "overall_trend": _overall_from_counts(counts),
    }


def _overall_from_counts(counts: Dict[str, int]) -> str:
    if counts.get("declining", 0) > 0:
        return "declining"
    if counts.get("improving", 0) > 0 and counts.get("unknown", 0) == 0:
        return "improving"
    if counts.get("stable", 0) > 0:
        return "stable"
    return "unknown"


def _list_count(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _as_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None

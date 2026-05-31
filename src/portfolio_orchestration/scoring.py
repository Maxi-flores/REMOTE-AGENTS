from __future__ import annotations

from typing import Any, Dict, List, Tuple


def score_repository_status(
    *,
    remediation_count: int,
    queue_count: int,
    dossier_count: int,
    readiness_score: int,
    intelligence_finding_count: int,
    high_risk_dossier_count: int,
) -> Tuple[int, int, str]:
    health = 100
    readiness = max(0, min(100, int(readiness_score)))

    health -= min(40, remediation_count * 4)
    health -= min(20, intelligence_finding_count * 6)
    health -= min(20, high_risk_dossier_count * 7)
    if queue_count > 0 and dossier_count == 0:
        health -= 15
    if queue_count == 0 and remediation_count > 0:
        health -= 10
    if readiness < 50:
        health -= 10
    health = max(0, min(100, health))

    status = status_from_scores(health, readiness)
    return health, readiness, status


def status_from_scores(health: int, readiness: int) -> str:
    if health >= 85 and readiness >= 80:
        return "healthy"
    if health >= 70 and readiness >= 60:
        return "warning"
    if health >= 45 and readiness >= 40:
        return "degraded"
    if health >= 0:
        return "critical"
    return "unknown"


def score_portfolio(statuses: List[Dict[str, Any]]) -> Tuple[int, int]:
    if not statuses:
        return 0, 0
    health_vals = [int(s.get("health_score") or 0) for s in statuses if isinstance(s, dict)]
    readiness_vals = [int(s.get("readiness_score") or 0) for s in statuses if isinstance(s, dict)]
    if not health_vals or not readiness_vals:
        return 0, 0
    return int(sum(health_vals) / len(health_vals)), int(sum(readiness_vals) / len(readiness_vals))


def execution_order(statuses: List[Dict[str, Any]]) -> List[str]:
    # Higher readiness first, then more remediation pressure.
    ranked = sorted(
        [s for s in statuses if isinstance(s, dict)],
        key=lambda s: (
            -int(s.get("readiness_score") or 0),
            -int(s.get("remediation_count") or 0),
            str(s.get("repository_id") or ""),
        ),
    )
    return [str(s.get("repository_id") or "") for s in ranked if str(s.get("repository_id") or "").strip()]


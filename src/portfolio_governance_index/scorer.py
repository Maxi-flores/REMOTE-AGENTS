from __future__ import annotations

from typing import Any, Dict, List

from portfolio_governance_index.contracts import GovernanceIndexComponent, new_id


WEIGHTS = {
    "Portfolio Health": 20,
    "Portfolio Readiness": 20,
    "Onboarding Coverage": 15,
    "Dependency Risk": 15,
    "Critical Path Risk": 10,
    "Roadmap Completeness": 10,
    "Progress Trend": 5,
    "Drift Health": 5,
}


def status_for_score(score: int) -> str:
    if score >= 85:
        return "healthy"
    if score >= 70:
        return "warning"
    if score >= 50:
        return "degraded"
    return "critical"


def governance_status(score: int, unknown_components: int) -> str:
    if unknown_components >= 5:
        return "unknown"
    return status_for_score(score)


def weighted_governance_score(components: List[Dict[str, Any]]) -> int:
    total_weight = 0
    weighted = 0.0
    for component in components:
        if not isinstance(component, dict):
            continue
        score = int(component.get("score") or 0)
        weight = int(component.get("weight") or 0)
        total_weight += weight
        weighted += score * weight
    if total_weight <= 0:
        return 0
    return int(round(weighted / total_weight))


def component(
    *,
    name: str,
    score: int,
    reasons: List[str],
    metadata: Dict[str, Any] | None = None,
    status: str | None = None,
) -> Dict[str, Any]:
    resolved_status = status or status_for_score(int(score))
    if resolved_status == "unknown":
        score = 50
    return GovernanceIndexComponent(
        component_id=new_id("governance_component"),
        name=name,
        score=max(0, min(100, int(score))),
        weight=int(WEIGHTS.get(name, 0)),
        status=resolved_status,
        reasons=list(reasons),
        advisory_only=True,
        metadata=dict(metadata or {}),
    ).to_dict()


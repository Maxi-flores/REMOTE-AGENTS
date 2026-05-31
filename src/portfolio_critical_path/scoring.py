from __future__ import annotations


def clamp_score(value: int) -> int:
    return max(0, min(100, int(value)))


def compute_influence_score(
    *,
    consumer_count: int,
    provider_count: int,
    dependency_chain_count: int,
    propagated_risk_count: int,
    readiness_score: int,
) -> int:
    # Deterministic weighted formula:
    # consumer/provider/chains/risk increase influence; low readiness slightly increases governance urgency.
    score = (
        min(30, consumer_count * 6)
        + min(20, provider_count * 4)
        + min(20, dependency_chain_count * 3)
        + min(20, propagated_risk_count * 4)
        + min(10, max(0, (100 - readiness_score) // 10))
    )
    return clamp_score(score)


def compute_critical_path_score(
    *,
    influence_score: int,
    readiness_score: int,
    downstream_consumers: int,
    high_severity_dependency_findings: int,
    onboarding_priority_weight: int,
) -> int:
    # Deterministic weighted formula:
    # base influence + readiness deficit + downstream blast radius + severity + onboarding urgency.
    readiness_deficit = max(0, 100 - readiness_score)
    score = (
        int(influence_score * 0.45)
        + int(readiness_deficit * 0.25)
        + min(15, downstream_consumers * 4)
        + min(10, high_severity_dependency_findings * 3)
        + onboarding_priority_weight
    )
    return clamp_score(score)


def onboarding_priority_weight(priority: str) -> int:
    p = (priority or "P4").upper()
    return {"P0": 10, "P1": 8, "P2": 5, "P3": 2, "P4": 0}.get(p, 0)


def recommendation_priority(critical_path_score: int) -> str:
    if critical_path_score >= 90:
        return "P0"
    if critical_path_score >= 75:
        return "P1"
    if critical_path_score >= 60:
        return "P2"
    if critical_path_score >= 40:
        return "P3"
    return "P4"


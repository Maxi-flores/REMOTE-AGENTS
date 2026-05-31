from __future__ import annotations

from typing import Any, Dict, List


def compute_effort_score(pkg: Dict[str, Any]) -> int:
    files = _len_list(pkg.get("target_files"))
    commands = _len_list(pkg.get("validation_commands"))
    scope = str(pkg.get("estimated_scope") or "").lower()
    base = {"tiny": 15, "small": 30, "medium": 50, "large": 70}.get(scope, 40)
    return min(100, base + (files * 5) + (commands * 3))


def compute_risk_score(pkg: Dict[str, Any]) -> int:
    risk_level = str(pkg.get("risk_level") or "medium").lower()
    return {"low": 20, "medium": 45, "high": 70, "critical": 90}.get(risk_level, 45)


def compute_readiness_score(*, risk_score: int, dependency_count: int, blocker_count: int, effort_score: int, subsystem_concentration: int) -> int:
    score = 100
    score -= int(risk_score * 0.35)
    score -= dependency_count * 8
    score -= blocker_count * 20
    score -= int(effort_score * 0.15)
    if subsystem_concentration > 3:
        score -= 5
    if score < 0:
        return 0
    if score > 100:
        return 100
    return int(score)


def execution_readiness_from_score(score: int) -> str:
    if score >= 85:
        return "ready"
    if score >= 60:
        return "waiting"
    if score >= 35:
        return "blocked"
    return "deferred"


def _len_list(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0

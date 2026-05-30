from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List


def calculate_agent_health(agent_state: Dict[str, Any], capability_profile: Dict[str, Any] | None = None) -> Dict[str, Any]:
    status = str(agent_state.get("status", "unknown"))
    health = str(agent_state.get("health", "unknown"))
    availability = str(agent_state.get("availability", "unknown"))
    score = 50
    if status == "active":
        score += 20
    if health == "healthy":
        score += 20
    elif health in {"warning", "degraded"}:
        score += 5
    if availability == "available":
        score += 10
    if capability_profile and str(capability_profile.get("status")) in {"deprecated", "inactive", "planned"}:
        score -= 20
    return {
        "agent_id": agent_state.get("agent_id"),
        "agent_class": agent_state.get("agent_class"),
        "score": max(0, min(100, score)),
        "status": status,
        "health": health,
        "availability": availability,
    }


def calculate_repository_coverage(repository_name: str, capability_profiles: List[Dict[str, Any]]) -> Dict[str, Any]:
    primary = []
    twin = []
    for profile in capability_profiles:
        if not isinstance(profile, dict):
            continue
        repos = profile.get("repositories", [])
        if not (isinstance(repos, list) and repository_name in repos):
            continue
        agent_class = str(profile.get("agent_class", "unknown"))
        if isinstance(profile.get("primary_roles"), list) and profile.get("primary_roles"):
            primary.append(agent_class)
        if isinstance(profile.get("secondary_roles"), list) and profile.get("secondary_roles"):
            twin.append(agent_class)
    return {
        "repository_name": repository_name,
        "primary_coverage": sorted(set(primary)),
        "twin_coverage": sorted(set(twin)),
    }


def detect_capability_gaps(repositories_registry: Dict[str, Any], capability_profiles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    repos = repositories_registry.get("repositories", []) if isinstance(repositories_registry.get("repositories"), list) else []
    gaps = []
    for repo in repos:
        if not isinstance(repo, dict):
            continue
        name = str(repo.get("name", "")).strip()
        if not name:
            continue
        coverage = calculate_repository_coverage(name, capability_profiles)
        if not coverage["primary_coverage"] or not coverage["twin_coverage"]:
            gaps.append(
                {
                    "repository_name": name,
                    "missing_primary": len(coverage["primary_coverage"]) == 0,
                    "missing_twin": len(coverage["twin_coverage"]) == 0,
                }
            )
    return gaps


def detect_single_points_of_failure(capability_profiles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    risks = []
    repo_to_agents: Dict[str, List[str]] = {}
    for profile in capability_profiles:
        if not isinstance(profile, dict):
            continue
        agent_class = str(profile.get("agent_class", "unknown"))
        for repo in profile.get("repositories", []) if isinstance(profile.get("repositories"), list) else []:
            repo_to_agents.setdefault(str(repo), []).append(agent_class)
    for repo, agents in repo_to_agents.items():
        uniq = sorted(set(agents))
        if len(uniq) <= 1:
            risks.append({"repository_name": repo, "agent_classes": uniq, "risk": "single_point_of_failure"})
    return risks


def summarize_lifecycle_health(
    lifecycle_states: List[Dict[str, Any]],
    capability_profiles: List[Dict[str, Any]],
) -> Dict[str, Any]:
    health_counts = Counter(
        str(state.get("health", "unknown")) for state in lifecycle_states if isinstance(state, dict)
    )
    availability_counts = Counter(
        str(state.get("availability", "unknown")) for state in lifecycle_states if isinstance(state, dict)
    )
    profile_status_counts = Counter(
        str(profile.get("status", "unknown")) for profile in capability_profiles if isinstance(profile, dict)
    )
    inactive_assigned = []
    for profile in capability_profiles:
        if not isinstance(profile, dict):
            continue
        if str(profile.get("status")) in {"planned", "deprecated", "inactive"} and profile.get("repositories"):
            inactive_assigned.append(str(profile.get("agent_class", "unknown")))
    return {
        "health_counts": dict(health_counts),
        "availability_counts": dict(availability_counts),
        "profile_status_counts": dict(profile_status_counts),
        "inactive_or_planned_assigned_agents": sorted(set(inactive_assigned)),
    }

